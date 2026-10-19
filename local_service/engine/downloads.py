import hashlib
import json
import threading
from pathlib import Path

import httpx


class Downloads:
    def __init__(self, root: Path):
        self.root = root
        self.states = {}
        self.lock = threading.Lock()

    def directory(self, model):
        return self.root / model.id / model.revision / model.subdir

    def ready(self, model):
        return (self.directory(model) / "verified.json").is_file()

    def verify(self, model):
        directory = self.directory(model)
        description = json.loads((directory / "verified.json").read_text(encoding="utf-8"))
        if description["revision"] != model.revision:
            raise ValueError("Revision local không khớp")
        for file in description["files"]:
            path = directory / Path(file["rfilename"]).name
            sha = hashlib.sha256()
            git_sha = hashlib.sha1(f"blob {file['size']}\0".encode())
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    sha.update(chunk)
                    git_sha.update(chunk)
            expected = file.get("lfs", {}).get("sha256")
            valid = sha.hexdigest() == expected if expected else git_sha.hexdigest() == file["blobId"]
            if path.stat().st_size != file["size"] or not valid:
                raise ValueError("Model local hỏng; cần tải lại")

    def describe(self, model):
        if model.license is None:
            raise ValueError("Chưa rõ giấy phép Hirashiba; không được tải/phân phối trong bản này.")
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(f"https://huggingface.co/api/models/{model.repo}/revision/{model.revision}",
                                  params={"blobs": "true"})
            response.raise_for_status()
        data = response.json()
        if data["sha"] != model.revision:
            raise ValueError("Revision không khớp")
        files = [f for f in data["siblings"] if f["rfilename"].startswith(model.subdir + "/")]
        names = {Path(f["rfilename"]).name for f in files}
        if not {"model.bin", "config.json", "shared_vocabulary.json"} <= names:
            raise ValueError("Thiếu file engine")
        if not ({"source.spm", "target.spm"} <= names or "tokenizer.json" in names):
            raise ValueError("Thiếu tokenizer")
        return {"revision": model.revision, "bytes": sum(f["size"] for f in files), "files": files}

    def start(self, model, expected_bytes):
        with self.lock:
            if any(s["state"] == "downloading" for s in self.states.values()):
                raise ValueError("Đang có model tải; vui lòng chờ.")
            self.states[model.id] = {"state": "downloading", "done": 0, "total": expected_bytes}
        threading.Thread(target=self._run, args=(model, expected_bytes), daemon=True).start()

    def _run(self, model, expected_bytes):
        state = self.states[model.id]
        try:
            description = self.describe(model)
            if description["bytes"] != expected_bytes:
                raise ValueError("Dung lượng thay đổi; cần xác nhận lại.")
            directory = self.directory(model)
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "verified.json").unlink(missing_ok=True)
            with httpx.Client(timeout=90, follow_redirects=True) as client:
                for file in description["files"]:
                    name = Path(file["rfilename"]).name
                    part = directory / (name + ".part")
                    sha = hashlib.sha256()
                    git_sha = hashlib.sha1(f"blob {file['size']}\0".encode())
                    count = 0
                    url = f"https://huggingface.co/{model.repo}/resolve/{model.revision}/{file['rfilename']}"
                    with client.stream("GET", url) as response, part.open("wb") as out:
                        response.raise_for_status()
                        for chunk in response.iter_bytes():
                            out.write(chunk)
                            sha.update(chunk)
                            git_sha.update(chunk)
                            count += len(chunk)
                            state["done"] += len(chunk)
                    expected = file.get("lfs", {}).get("sha256")
                    valid_hash = sha.hexdigest() == expected if expected else git_sha.hexdigest() == file["blobId"]
                    if count != file["size"] or not valid_hash:
                        raise ValueError("Kiểm tra toàn vẹn file thất bại")
                    part.replace(directory / name)
            (directory / "verified.json").write_text(json.dumps(description), encoding="utf-8")
            state["state"] = "ready"
        except Exception:
            state.update(state="error", error="Tải/kiểm tra model thất bại. Kiểm tra mạng, dung lượng và tải lại.")
