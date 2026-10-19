from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from local_service.glossary.protection import validate_entries


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entry(Strict):
    source: str = Field(min_length=1, max_length=200)
    target: str = Field(min_length=1, max_length=300)
    enabled: bool = True


class Glossary(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9-]{1,64}$")
    name: str = Field(min_length=1, max_length=100)
    entries: list[Entry] = Field(max_length=2000)

    @model_validator(mode="after")
    def valid_entries(self):
        if not self.name.strip():
            raise ValueError("Tên bộ không được rỗng")
        validate_entries([e.model_dump() for e in self.entries])
        return self


class Unit(Strict):
    id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=16000)


class JobRequest(Strict):
    version: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=64)
    glossary_id: str | None = Field(default=None, max_length=64)
    glossary_entries: list[Entry] | None = Field(default=None, max_length=2000)
    device: Literal["cpu", "cuda"] = "cpu"
    units: list[Unit] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def size(self):
        if self.glossary_entries is not None:
            validate_entries([e.model_dump() for e in self.glossary_entries])
        if len({u.id for u in self.units}) != len(self.units):
            raise ValueError("ID đoạn trùng")
        if sum(len(u.text) for u in self.units) > 64000:
            raise ValueError("Batch quá lớn")
        return self


class DownloadRequest(Strict):
    confirmed: Literal[True]
    bytes: int = Field(gt=0, le=4_000_000_000)


class Priorities(Strict):
    ids: list[str] = Field(max_length=32)
