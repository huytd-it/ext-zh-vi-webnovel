import re
import time

import ctranslate2
import sentencepiece as spm
from tokenizers import Tokenizer

from local_service.glossary.protection import normalize, protect, restore


class Runtime:
    """Single queue worker owns this runtime; only one model resident at a time."""

    def __init__(self, downloads):
        self.downloads = downloads
        self.key = None
        self.translator = None
        self.device = "cpu"
        self.warning = None
        self.load_seconds = 0

    def load(self, model, requested):
        key = (model.id, model.revision, requested)
        if key == self.key:
            return
        if not self.downloads.ready(model):
            raise ValueError("Model chưa tải hoặc chưa xác minh hoàn chỉnh.")
        started = time.perf_counter()
        self.translator = None
        self.key = None
        self.device = "cpu"
        self.warning = None
        directory = self.downloads.directory(model)
        self.downloads.verify(model)
        if (directory / "source.spm").exists():
            self.source = spm.SentencePieceProcessor(model_file=str(directory / "source.spm"))
            self.target = spm.SentencePieceProcessor(model_file=str(directory / "target.spm"))
            self.fast = None
        else:
            self.fast = Tokenizer.from_file(str(directory / "tokenizer.json"))
            self.fast.no_truncation()
        if requested == "cuda":
            try:
                self.translator = ctranslate2.Translator(str(directory), device="cuda", compute_type="float32")
                # cuBLAS can fail lazily at first inference even after the constructor succeeds.
                self.translator.translate_batch([self.encode("你好。") + ["</s>"]],
                                                beam_size=1, max_decoding_length=8)
                self.device = "cuda"
            except (RuntimeError, ValueError):
                self.translator = None
                self.warning = "Không nạp được CUDA; đang chạy CPU. Kiểm tra NVIDIA và gói CUDA."
        if self.translator is None:
            self.translator = ctranslate2.Translator(str(directory), device="cpu", compute_type="int8",
                                                    intra_threads=4)
        self.key = key
        self.load_seconds = time.perf_counter() - started

    def encode(self, text):
        if self.fast:
            return [t for t in self.fast.encode(text, add_special_tokens=False).tokens
                    if t not in ("<pad>", "<s>", "</s>")]
        return self.source.encode(text, out_type=str)

    def decode(self, tokens):
        tokens = [t for t in tokens if t not in ("<pad>", "<s>", "</s>")]
        if self.fast:
            ids = [self.fast.token_to_id(t) for t in tokens]
            if None in ids:
                raise ValueError("Tokenizer không khớp weights")
            return self.fast.decode(ids, skip_special_tokens=True)
        return self.target.decode(tokens)

    def chunks(self, text, limit):
        # Split on sentence boundaries first, then binary-search a character boundary.
        # Token-piece slicing can split UTF-8 byte pieces; never truncate encoded inputs.
        pending = ""
        for sentence in re.split(r"(?<=[。！？!?；;\n])", text):
            if pending and len(self.encode(pending + sentence)) > limit:
                yield pending
                pending = ""
            while len(self.encode(sentence)) > limit:
                lo, hi = 1, len(sentence)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if len(self.encode(sentence[:mid])) <= limit:
                        lo = mid
                    else:
                        hi = mid - 1
                yield sentence[:lo]
                sentence = sentence[lo:]
            pending += sentence
        if pending:
            yield pending

    def plain(self, text, model):
        if not text.strip():
            return text
        if "\n" in text:
            return "".join(part if not part.strip() else self.plain(part, model)
                           for part in re.split(r"(\r?\n+)", text))
        outputs = []
        for chunk in self.chunks(text, model.input_tokens - 1):
            result = self.translator.translate_batch(
                [self.encode(chunk) + ["</s>"]], beam_size=model.beam,
                max_input_length=0, max_decoding_length=model.output_tokens,
                repetition_penalty=model.repetition_penalty,
                no_repeat_ngram_size=model.no_repeat_ngram_size,
                return_end_token=True,
            )[0].hypotheses[0]
            if "</s>" not in result and len(result) >= model.output_tokens:
                if len(chunk) < 2:
                    raise ValueError("Model chạm giới hạn output")
                middle = len(chunk) // 2
                outputs.extend([self.plain(chunk[:middle], model), self.plain(chunk[middle:], model)])
            else:
                decoded = self.decode(result).strip()
                if not decoded:
                    raise ValueError("Model trả về kết quả rỗng")
                outputs.append(decoded)
        return " ".join(outputs)

    def translate(self, text, model, glossary):
        source = normalize(text)
        try:
            protected, markers = protect(source, glossary)
            output = restore(self.plain(protected, model), markers)
            return {"text": output, "warning": None}
        except ValueError:
            if not any(e["enabled"] for e in glossary):
                raise
            output = restore(self.plain(source, model), {})
            return {"text": output, "warning": "glossary_fallback"}
