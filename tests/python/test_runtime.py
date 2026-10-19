import json

import pytest

from local_service.engine.downloads import Downloads
from local_service.engine.registry import MODELS
from local_service.engine.runtime import Runtime


def test_chunker_never_loses_tail_or_splits_surrogates():
    runtime = Runtime(None)
    runtime.encode = lambda text: list(text)
    for source in ["长句。" * 100, "一" * 500, "第一句！第二句？\n第三句。", "𠀀" * 120]:
        chunks = list(runtime.chunks(source, 12))
        assert "".join(chunks) == source
        assert all(len(chunk) <= 12 for chunk in chunks)


def test_glossary_marker_retry():
    runtime = Runtime(None)
    calls = []

    def plain(text, model):
        calls.append(text)
        return "marker lost" if len(calls) == 1 else "Trương Tam bước đi"

    runtime.plain = plain
    result = runtime.translate("張三走了", MODELS["HachimiMT-60"],
                               [{"source": "张三", "target": "Trương Tam", "enabled": True}])
    assert result == {"text": "Trương Tam bước đi", "warning": "glossary_fallback"}
    assert len(calls) == 2
    assert calls[1] == "张三走了"


def test_plain_preserves_newline_boundaries():
    runtime = Runtime(None)
    runtime.encode = lambda text: list(text)
    runtime.decode = lambda tokens: "Bản dịch"

    class Translator:
        def translate_batch(self, *args, **kwargs):
            return [type("Result", (), {"hypotheses": [["test", "</s>"]]})()]

    runtime.translator = Translator()
    assert runtime.plain("第一行\n第二行\n\n第三行", MODELS["HachimiMT-60"]) == "Bản dịch\nBản dịch\n\nBản dịch"


def test_download_integrity(tmp_path):
    import hashlib
    downloads = Downloads(tmp_path)
    model = MODELS["HachimiMT-60"]
    directory = downloads.directory(model)
    directory.mkdir(parents=True)
    payload = b"weights-test-only"
    (directory / "model.bin").write_bytes(payload)
    description = {"revision": model.revision, "files": [{"rfilename": "ct2-int8_float32/model.bin",
                    "size": len(payload), "lfs": {"sha256": hashlib.sha256(payload).hexdigest()}}]}
    (directory / "verified.json").write_text(json.dumps(description))
    downloads.verify(model)
    (directory / "model.bin").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        downloads.verify(model)
