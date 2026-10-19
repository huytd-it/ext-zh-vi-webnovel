import time

import pytest
from fastapi.testclient import TestClient

from local_service.app.api import MAX_BODY, create_app
from local_service.engine.registry import MODELS

TOKEN = "test-token-with-at-least-32-characters"
ORIGIN = "chrome-extension://" + "a" * 32


class FakeRuntime:
    def __init__(self, downloads):
        self.device, self.warning, self.load_seconds = "cpu", None, 0

    def load(self, model, requested):
        if requested == "cuda":
            self.warning = "CPU fallback (test double)"

    def translate(self, text, model, glossary):
        return {"text": "Bản dịch kiểm thử", "warning": None}


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path, TOKEN, FakeRuntime)
    model = MODELS["HachimiMT-60"]
    directory = tmp_path / "models" / model.id / model.revision / model.subdir
    directory.mkdir(parents=True)
    (directory / "verified.json").write_text("{}")
    with TestClient(app, base_url="http://127.0.0.1:17865",
                    headers={"Authorization": f"Bearer {TOKEN}", "Origin": ORIGIN}) as client:
        yield client


def test_auth_origin_host_and_cors(client):
    assert client.get("/v1/health").status_code == 200
    assert client.get("/v1/health", headers={"Authorization": ""}).status_code == 401
    assert client.get("/v1/health", headers={"Origin": "https://evil.test"}).status_code == 403
    assert client.get("/v1/health", headers={"Origin": "null"}).status_code == 403
    assert client.get("/v1/health", headers={"Host": "evil.test:17865"}).status_code == 403
    assert client.get("/v1/health").headers["access-control-allow-origin"] == ORIGIN
    preflight = client.options("/v1/jobs", headers={"Authorization": "",
                                                   "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 200
    assert "*" not in preflight.headers["access-control-allow-origin"]


def test_payload_and_private_endpoints(client):
    assert client.post("/v1/jobs", content="x" * (MAX_BODY + 1)).status_code == 413
    assert client.post("/v1/jobs", json={"version": "1", "model": "HachimiMT-60", "url": "http://evil"}).status_code == 422
    assert client.get("/docs").status_code == 404
    assert client.get("/v1/models/HirashibaMT-Medium/download-info").status_code == 400
    assert client.post("/v1/models/HirashibaMT-Medium/download", json={"confirmed": True, "bytes": 1}).status_code == 400
    assert client.post("/v1/models/HachimiMT-60/download", json={"confirmed": False, "bytes": 1}).status_code == 422


def test_glossary_crud_validation_cache(client):
    body = {"id": "test", "name": "Truyện", "entries": [{"source": "張三", "target": "Trương Tam", "enabled": True}]}
    assert client.put("/v1/glossaries/test", json=body).status_code == 200
    assert client.get("/v1/glossaries").json() == [body]
    body["entries"].append({"source": "张三", "target": "Khác", "enabled": True})
    assert client.put("/v1/glossaries/test", json=body).status_code == 422
    assert client.delete("/v1/cache").status_code == 200
    assert len(client.get("/v1/glossaries").json()) == 1
    client.delete("/v1/glossaries/test")
    assert client.get("/v1/glossaries").json() == []


def test_job_survives_client_poll_gap_and_cpu_fallback(client):
    body = {"version": "page-1", "model": "HachimiMT-60", "device": "cuda",
            "glossary_entries": [], "units": [{"id": "a", "text": "中文"}, {"id": "b", "text": "小说"}]}
    response = client.post("/v1/jobs", json=body)
    assert response.status_code == 201
    id = response.json()["id"]
    for _ in range(100):
        job = client.get(f"/v1/jobs/{id}").json()
        if job["state"] == "complete":
            break
        time.sleep(.01)
    assert job["version"] == "page-1"
    assert len(job["results"]) == 2
    assert job["device"] == "cpu"
    assert job["warning"]
    assert client.delete(f"/v1/jobs/{id}").json() == {"ok": True}
    assert client.get(f"/v1/jobs/{id}").json()["state"] == "cancelled"
    assert client.get("/v1/jobs/missing").status_code == 404
