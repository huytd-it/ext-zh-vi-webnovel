from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Model:
    id: str
    repo: str
    revision: str
    subdir: str
    license: str | None
    input_tokens: int
    output_tokens: int
    beam: int = 4
    repetition_penalty: float = 1.0
    no_repeat_ngram_size: int = 0

    def public(self):
        return asdict(self) | {"blocked": self.license is None}


MODELS = {
    m.id: m for m in [
        Model("HachimiMT-60", "ngocdang83/HachimiMT-60-zh-vi",
              "50cd988cefa7773c2663337e54829df8bb036659", "ct2-int8_float32", "CC-BY-4.0",
              160, 400, repetition_penalty=1.2, no_repeat_ngram_size=2),
        Model("MoxhiMT-60", "DanVP/MoxhiMT-60", "a68cc65218ddea2adac1ce508512953306936c51",
              "ct2-int8", "Apache-2.0", 160, 512),
        Model("HirashibaMT-Medium", "ngungodan/hirashiba-mt-medium-ct2",
              "239b98c59cb50c0e3660dcfc0fa62b4b0c471174", "ct2-int8_float32", None, 96, 128),
    ]
}
