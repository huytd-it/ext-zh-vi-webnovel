import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from local_service.app.schemas import DownloadRequest, Glossary, JobRequest, Priorities
from local_service.engine.downloads import Downloads
from local_service.engine.registry import MODELS
from local_service.engine.runtime import Runtime
from local_service.jobs.queue import Jobs
from local_service.storage.database import Database

PORT = 17865
ORIGIN = re.compile(r"^chrome-extension://[a-p]{32}$")
MAX_BODY = 512 * 1024


class Boundary:
    """ASGI guard before body parsing; covers chunked requests too."""

    def __init__(self, app, token):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        host = headers.get(b"host", b"").decode()
        origin = headers.get(b"origin", b"").decode()
        allowed_origin = bool(ORIGIN.fullmatch(origin))

        async def reject(status, text):
            return await JSONResponse({"detail": text}, status_code=status)(scope, receive, send)

        if host != f"127.0.0.1:{PORT}":
            return await reject(403, "Host không hợp lệ")
        if origin and not allowed_origin:
            return await reject(403, "Origin không hợp lệ")
        cors = [(b"access-control-allow-origin", origin.encode()), (b"vary", b"Origin")]
        if scope["method"] == "OPTIONS":
            if not allowed_origin:
                return await reject(403, "Origin không hợp lệ")
            response = JSONResponse(None, headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "Authorization,Content-Type",
                "Access-Control-Allow-Private-Network": "true",
                "Vary": "Origin",
            })
            return await response(scope, receive, send)
        auth = headers.get(b"authorization", b"").decode()
        if not secrets.compare_digest(auth, f"Bearer {self.token}"):
            return await reject(401, "Cần ghép nối chương trình local")
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY:
                return await reject(413, "Payload quá lớn")
            if not message.get("more_body"):
                break

        async def replay():
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        async def cors_send(message):
            if message["type"] == "http.response.start" and allowed_origin:
                message["headers"] = list(message.get("headers", [])) + cors
            await send(message)

        await self.app(scope, replay, cors_send)


def create_app(data: Path, token: str, runtime_factory=Runtime):
    db = Database(data / "data.sqlite3")
    downloads = Downloads(data / "models")
    runtime = runtime_factory(downloads)
    jobs = Jobs(runtime, db)

    @asynccontextmanager
    async def lifespan(app):
        yield
        jobs.close()
        if not jobs.thread.is_alive():
            db.close()

    app = FastAPI(title="Novel Local", version="1", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Boundary, token=token)
    app.state.db, app.state.jobs = db, jobs

    @app.exception_handler(ValueError)
    async def bad_value(request: Request, error: ValueError):
        return JSONResponse({"detail": str(error)}, status_code=400)

    @app.exception_handler(KeyError)
    async def missing(request: Request, error: KeyError):
        return JSONResponse({"detail": "Không tìm thấy tài nguyên; lượt có thể đã hết hạn."}, status_code=404)

    @app.get("/v1/health")
    def health():
        return {"api": 1, "engine": "CTranslate2", "device": runtime.device,
                "warning": runtime.warning, "load_seconds": runtime.load_seconds,
                "capabilities": ["cpu", "cuda-request", "glossary", "disk-cache"],
                "limits": {"units": 32, "text": 64000, "active_jobs": 16}}

    @app.get("/v1/models")
    def models():
        return [m.public() | {"ready": downloads.ready(m), "download": downloads.states.get(m.id)}
                for m in MODELS.values()]

    @app.get("/v1/models/{id}/download-info")
    def download_info(id: str):
        try:
            description = downloads.describe(MODELS[id])
            return {k: description[k] for k in ("revision", "bytes")}
        except (ValueError, KeyError):
            raise
        except Exception:
            raise HTTPException(502, "Không lấy được dung lượng; kiểm tra kết nối Internet.") from None

    @app.post("/v1/models/{id}/download")
    def download(id: str, request: DownloadRequest):
        model = MODELS[id]
        if model.license is None:
            raise ValueError("Chưa xác minh giấy phép Hirashiba.")
        with jobs.lock:
            if any(j["state"] in ("queued", "running") for j in jobs.jobs.values()):
                raise ValueError("Dừng/chờ các lượt dịch trước khi tải model.")
            downloads.start(model, request.bytes)
            runtime.key = None
        return {"state": "downloading"}

    @app.get("/v1/glossaries")
    def glossaries():
        return db.glossaries()

    @app.put("/v1/glossaries/{id}")
    def save_glossary(id: str, body: Glossary):
        if id != body.id:
            raise ValueError("ID không khớp")
        db.save_glossary(body.model_dump())
        return body

    @app.delete("/v1/glossaries/{id}")
    def delete_glossary(id: str):
        db.delete_glossary(id)
        return {"ok": True}

    @app.delete("/v1/cache")
    def clear_cache():
        db.clear_cache()
        return {"ok": True}

    @app.post("/v1/jobs", status_code=201)
    def create_job(body: JobRequest):
        model = MODELS[body.model]
        if downloads.states.get(model.id, {}).get("state") == "downloading":
            raise ValueError("Model đang tải, vui lòng chờ.")
        if model.license is None or not downloads.ready(model):
            raise ValueError("Model chưa sẵn sàng hoặc chưa xác minh giấy phép.")
        glossary = [e.model_dump() for e in body.glossary_entries] if body.glossary_entries else []
        if body.glossary_id:
            selected = next((g for g in db.glossaries() if g["id"] == body.glossary_id), None)
            if selected is None:
                raise ValueError("Bộ glossary không còn tồn tại")
            glossary = selected["entries"]
        return jobs.create(body, model, glossary)

    @app.get("/v1/jobs/{id}")
    def read_job(id: str):
        return jobs.read(id)

    @app.delete("/v1/jobs/{id}")
    def cancel_job(id: str):
        jobs.cancel(id)
        return {"ok": True}

    @app.put("/v1/jobs/{id}/priorities")
    def priorities(id: str, body: Priorities):
        jobs.prioritize(id, body.ids)
        return {"ok": True}

    return app
