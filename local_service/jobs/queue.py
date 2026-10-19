import copy
import threading
import time
import uuid
from collections import deque

from local_service.storage.database import cache_key


class Jobs:
    def __init__(self, runtime, db):
        self.runtime, self.db = runtime, db
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.closed = False
        self.jobs = {}
        self.pending = deque()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def create(self, request, model, glossary):
        with self.lock:
            now = time.monotonic()
            for id in list(self.jobs):
                job = self.jobs[id]
                if now - job["updated"] > 1800 and job["state"] not in ("queued", "running"):
                    del self.jobs[id]
            if len(self.jobs) >= 128 or sum(j["state"] in ("queued", "running")
                                           for j in self.jobs.values()) >= 16:
                raise ValueError("Hàng đợi đầy; chờ hoặc dừng lượt khác.")
            id = uuid.uuid4().hex
            job = {"id": id, "version": request.version, "state": "queued", "results": [],
                   "total": len(request.units), "updated": now, "device": None, "warning": None,
                   "model": model.id, "glossary": copy.deepcopy(glossary),
                   "request": request, "model_spec": model, "remaining": list(request.units)}
            self.jobs[id] = job
            self.pending.append(id)
            self.wake.set()
            return self.read(id)

    def read(self, id):
        with self.lock:
            job = self.jobs[id]
            return copy.deepcopy({k: v for k, v in job.items()
                                  if k not in ("request", "model_spec", "remaining", "updated")})

    def cancel(self, id):
        with self.lock:
            self.jobs[id]["state"] = "cancelled"
            self.jobs[id]["updated"] = time.monotonic()

    def prioritize(self, id, priorities):
        with self.lock:
            ranks = {value: n for n, value in enumerate(priorities)}
            self.jobs[id]["remaining"].sort(key=lambda u: ranks.get(u.id, len(ranks)))

    def _worker(self):
        while not self.closed:
            self.wake.wait(1)
            with self.lock:
                if not self.pending:
                    self.wake.clear()
                    continue
                id = self.pending.popleft()
                job = self.jobs[id]
                if job["state"] == "cancelled":
                    continue
                job["state"] = "running"
                unit = job["remaining"].pop(0)
            try:
                model, request = job["model_spec"], job["request"]
                self.runtime.load(model, request.device)
                key = cache_key(unit.text, model, self.runtime.device, job["glossary"])
                value = self.db.get(key)
                if value is None:
                    value = self.runtime.translate(unit.text, model, job["glossary"])
                    self.db.put(key, value)
                result = {"id": unit.id, **value}
                with self.lock:
                    job["device"] = self.runtime.device
                    job["warning"] = self.runtime.warning
            except Exception:
                # No exception repr: runtime exceptions can contain source text or local paths.
                result = {"id": unit.id, "error": "Không dịch được đoạn. Kiểm tra model và thử Dịch lại."}
            with self.lock:
                if job["state"] != "cancelled":
                    job["results"].append(result)
                    job["updated"] = time.monotonic()
                    if job["remaining"]:
                        self.pending.append(id)  # Round-robin: a long tab cannot starve another tab.
                    else:
                        job["state"] = "complete"

    def close(self):
        self.closed = True
        self.wake.set()
        self.thread.join(timeout=5)
