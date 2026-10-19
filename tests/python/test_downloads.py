import hashlib
import time
from pathlib import Path

import httpx

from local_service.engine.downloads import Downloads
from local_service.engine.registry import MODELS


def test_download_confirmation_revision_hash_and_retry(tmp_path, monkeypatch):
    model = MODELS["MoxhiMT-60"]
    payloads = {name: name.encode() for name in ["model.bin", "config.json", "shared_vocabulary.json", "source.spm", "target.spm"]}
    files = [{"rfilename": f"{model.subdir}/{name}", "size": len(body),
              "lfs": {"sha256": hashlib.sha256(body).hexdigest()}}
             for name, body in payloads.items()]
    corrupt = True

    def handler(request):
        if "/api/" in request.url.path:
            return httpx.Response(200, json={"sha": model.revision, "siblings": files})
        name = Path(request.url.path).name
        return httpx.Response(200, content=b"corrupt" if corrupt and name == "model.bin" else payloads[name])

    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    downloads = Downloads(tmp_path)
    info = downloads.describe(model)
    assert info["bytes"] == sum(len(b) for b in payloads.values())
    downloads.start(model, info["bytes"])
    for _ in range(100):
        if downloads.states[model.id]["state"] != "downloading":
            break
        time.sleep(.01)
    assert downloads.states[model.id]["state"] == "error"
    assert not downloads.ready(model)
    corrupt = False
    downloads.start(model, info["bytes"])
    for _ in range(100):
        if downloads.states[model.id]["state"] != "downloading":
            break
        time.sleep(.01)
    assert downloads.ready(model)
    assert downloads.states[model.id]["done"] == info["bytes"]
    downloads.verify(model)
