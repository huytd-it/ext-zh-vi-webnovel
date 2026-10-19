from local_service.engine.registry import MODELS
from local_service.engine.runtime import Runtime


def test_lazy_cuda_failure_falls_back_to_cpu(tmp_path, monkeypatch):
    class Downloads:
        def ready(self, model):
            return True

        def verify(self, model):
            pass

        def directory(self, model):
            return tmp_path

    class FastTokenizer:
        def no_truncation(self):
            pass

        def encode(self, text, add_special_tokens=False):
            return type("Encoding", (), {"tokens": ["test"]})()

    calls = []

    class Translator:
        def __init__(self, path, device, **kwargs):
            self.device = device
            calls.append(device)

        def translate_batch(self, *args, **kwargs):
            if self.device == "cuda":
                raise RuntimeError("test double: cuBLAS not installed")

    monkeypatch.setattr("local_service.engine.runtime.Tokenizer.from_file", lambda path: FastTokenizer())
    monkeypatch.setattr("local_service.engine.runtime.ctranslate2.Translator", Translator)
    runtime = Runtime(Downloads())
    runtime.load(MODELS["HachimiMT-60"], "cuda")
    assert calls == ["cuda", "cpu"]
    assert runtime.device == "cpu"
    assert runtime.warning
    assert runtime.translator.device == "cpu"
