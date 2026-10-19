"""Offline benchmark: never downloads weights and never sends sample text over a network."""
import argparse
import json
import platform
import time
from pathlib import Path

from local_service.engine.downloads import Downloads
from local_service.engine.registry import MODELS
from local_service.engine.runtime import Runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path, help="NovelLocal data directory")
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    model = MODELS[args.model]
    if model.license is None:
        parser.error("Hirashiba chưa qua cổng giấy phép; không nạp trong bản phân phối này.")
    downloads = Downloads(args.data / "models")
    if not downloads.ready(model):
        parser.error("Chưa có model đã xác nhận tải và xác minh hoàn chỉnh. Không tự tải trong benchmark.")
    runtime = Runtime(downloads)
    started = time.perf_counter()
    runtime.load(model, args.device)
    load = time.perf_counter() - started
    samples = ["他抬头看向远处的山门。", "张三走过青山，清风拂面。他知道新的旅程已经开始。",
               "他必须抓紧时间。朋友还在前面等着他，而城门就要关闭了。" * 12]
    results = []
    for index, text in enumerate(samples):
        durations = []
        for _ in range(3):
            started = time.perf_counter()
            value = runtime.translate(text, model, [])
            durations.append(time.perf_counter() - started)
        results.append({"sample": index, "source": text, "translation": value["text"],
                        "first_seconds": durations[0], "warm_seconds": durations[1:]})
    report = {"platform": platform.platform(), "cpu": platform.processor(),
              "model": model.public(), "requested": args.device, "actual_device": runtime.device,
              "device_warning": runtime.warning, "load_seconds_including_hash_check": load,
              "download_seconds": None, "viewport_seconds": None, "whole_page_seconds": None,
              "note": "Engine-only, offline. Download/DOM viewport/page require separate browser measurements.",
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
