import threading
import time

from local_service.app.schemas import JobRequest
from local_service.engine.registry import MODELS
from local_service.jobs.queue import Jobs
from local_service.storage.database import Database


class BlockingRuntime:
    device, warning = "cpu", None

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.seen = []

    def load(self, model, device):
        pass

    def translate(self, text, model, glossary):
        self.entered.set()
        self.release.wait(3)
        self.seen.append((text, model.id, glossary))
        return {"text": "Dịch " + text, "warning": None}


def request(version, ids):
    return JobRequest(version=version, model="HachimiMT-60", units=[{"id": id, "text": id} for id in ids])


def wait_complete(jobs, ids):
    for _ in range(200):
        if all(jobs.read(id)["state"] in ("complete", "cancelled") for id in ids):
            return
        time.sleep(.01)
    raise AssertionError("Jobs did not complete")


def test_cancel_drops_inflight_result_and_glossary_snapshot(tmp_path):
    db = Database(tmp_path / "jobs.db")
    runtime = BlockingRuntime()
    jobs = Jobs(runtime, db)
    glossary = [{"source": "张三", "target": "Trương Tam", "enabled": True}]
    try:
        id = jobs.create(request("tab1", ["a", "b"]), MODELS["HachimiMT-60"], glossary)["id"]
        assert runtime.entered.wait(1)
        glossary[0]["target"] = "Đã sửa"
        jobs.cancel(id)
        runtime.release.set()
        wait_complete(jobs, [id])
        jobs.close()
        assert jobs.read(id)["results"] == []
        assert runtime.seen[0][2][0]["target"] == "Trương Tam"
    finally:
        runtime.release.set()
        jobs.close()
        db.close()


def test_round_robin_priorities_versions_and_model_isolation(tmp_path):
    db = Database(tmp_path / "jobs.db")
    runtime = BlockingRuntime()
    jobs = Jobs(runtime, db)
    try:
        a = jobs.create(request("tab1", ["a1", "a2", "a3"]), MODELS["HachimiMT-60"], [])["id"]
        assert runtime.entered.wait(1)
        b = jobs.create(request("tab2", ["b1"]), MODELS["MoxhiMT-60"], [])["id"]
        jobs.prioritize(a, ["a3", "a2"])
        runtime.release.set()
        wait_complete(jobs, [a, b])
        assert [row[0] for row in runtime.seen] == ["a1", "b1", "a3", "a2"]
        assert jobs.read(a)["version"] == "tab1"
        assert jobs.read(b)["version"] == "tab2"
        assert runtime.seen[1][1] == "MoxhiMT-60"
    finally:
        runtime.release.set()
        jobs.close()
        db.close()
