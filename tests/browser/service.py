"""Browser integration test double. Not shipped and never used by the launcher."""
import os
from pathlib import Path

import uvicorn

from local_service.app.api import create_app
from local_service.engine.registry import MODELS


class TestRuntime:
    device = "cpu"
    warning = None
    load_seconds = 0

    def __init__(self, downloads):
        pass

    def load(self, model, requested):
        self.warning = "Test double · không phải suy luận model thật"

    def translate(self, text, model, glossary):
        import time
        time.sleep(.025)
        return {"text": "Bản dịch kiểm thử.", "warning": None}


if __name__ == "__main__":
    data = Path(os.environ["NOVEL_TEST_DATA"])
    model = MODELS["HachimiMT-60"]
    path = data / "models" / model.id / model.revision / model.subdir
    path.mkdir(parents=True)
    (path / "verified.json").write_text("{}")
    uvicorn.run(create_app(data, os.environ["NOVEL_TEST_TOKEN"], TestRuntime),
                host="127.0.0.1", port=17865, access_log=False, log_level="critical")
