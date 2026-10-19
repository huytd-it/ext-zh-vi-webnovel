import argparse
import json
import os
import platform
from pathlib import Path

_dll_handles = []


def prepare_gpu_libraries():
    if os.name == "nt":
        directory = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "NovelLocal" / "cuda"
        if directory.is_dir():
            _dll_handles.append(os.add_dll_directory(str(directory)))


def main():
    prepare_gpu_libraries()
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--diagnostic-output", type=Path)
    parser.add_argument("--serve", action="store_true", help="Headless development/smoke-test server")
    args = parser.parse_args()
    if args.diagnose:
        import ctranslate2
        import opencc
        import sentencepiece
        import tokenizers
        import tkinter
        import secrets
        from local_service.app.api import create_app
        from local_service.storage.database import Database
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(prefix="novel-local-") as directory:
            db = Database(Path(directory) / "kiểm thử" / "data.sqlite3")
            db.put("probe", {"text": "Tiếng Việt"})
            assert db.get("probe")["text"] == "Tiếng Việt"
            db.clear_cache()
            db.close()
            api = create_app(Path(directory) / "api", secrets.token_urlsafe(32))
            api.state.jobs.close()
            api.state.db.close()
        report = {"platform": platform.platform(), "architecture": platform.machine(),
                  "ct2": ctranslate2.__version__, "cpu_types": sorted(ctranslate2.get_supported_compute_types("cpu")),
                  "cuda_devices": ctranslate2.get_cuda_device_count(), "sqlite": "ok",
                  "opencc": opencc.OpenCC("t2s").convert("漢字"),
                  "sentencepiece": sentencepiece.__version__, "tokenizers": tokenizers.__version__}
        report["api_import"] = "ok"
        report["tcl"] = tkinter.Tcl().eval("info patchlevel")
        output = json.dumps(report, indent=2, ensure_ascii=False)
        if args.diagnostic_output:
            args.diagnostic_output.write_text(output, encoding="utf-8")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=True))
    elif args.serve:
        import uvicorn
        from local_service.app.api import PORT, create_app
        token = os.environ["NOVEL_LOCAL_TOKEN"]
        data = Path(os.environ["NOVEL_LOCAL_DATA"])
        uvicorn.run(create_app(data, token), host="127.0.0.1", port=PORT, access_log=False,
                    log_config=None, log_level="critical", limit_concurrency=32, timeout_keep_alive=5)
    else:
        from local_service.launcher.main import main as launch
        launch()


if __name__ == "__main__":
    main()
