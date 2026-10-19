import pytest

from local_service.engine.registry import MODELS
from local_service.glossary.protection import normalize, protect, restore, validate_entries
from local_service.storage.database import Database, cache_key


def entry(source="张三", target="Trương Tam", enabled=True):
    return dict(source=source, target=target, enabled=enabled)


def test_normalization_overlap_unicode():
    text = normalize("張三丰和張三，說：你好！")
    source, markers = protect(text, [entry("张三丰", "Trương Tam Phong"), entry()])
    assert "张" not in source
    assert list(markers.values()) == ["Trương Tam Phong", "Trương Tam"]
    assert restore(source, markers) == "Trương Tam Phong和Trương Tam，说：你好！"
    assert normalize("e\u0301") == "é"


@pytest.mark.parametrize("entries", [[entry(" ")], [entry(target="")],
                                    [entry(), entry("張三", "Khác")], [entry("ZXQ0000QXZ")]])
def test_invalid_entries(entries):
    with pytest.raises(ValueError):
        validate_entries(entries)


def test_disabled_and_marker_failures():
    assert protect("张三", [entry(enabled=False)]) == ("张三", {})
    source, markers = protect("张三", [entry()])
    assert restore(source, markers) == "Trương Tam"
    for output in ["mất marker", source + source, "ZXQ000QXZ", "ZX Q0000 QXZ"]:
        with pytest.raises(ValueError):
            restore(output, markers)


def test_cache_isolation_lru_delete_and_glossary(tmp_path):
    db = Database(tmp_path / "có dấu" / "test.db", cap=260)
    glossary = dict(id="1", name="Truyện", entries=[entry()])
    db.save_glossary(glossary)
    model = MODELS["HachimiMT-60"]
    keys = {cache_key("原文", model, device, entries) for device in ["cpu", "cuda"]
            for entries in [[], [entry()], [entry(target="Khác")]]}
    assert len(keys) == 6
    assert cache_key("原文", model, "cpu", []) != cache_key("原文", MODELS["MoxhiMT-60"], "cpu", [])
    for n in range(10):
        db.put(str(n), {"text": "a" * 80})
    assert db.get("0") is None
    assert db.get("9") is not None
    db.clear_cache()
    assert db.get("9") is None
    assert db.glossaries() == [glossary]
    db.close()
    db = Database(tmp_path / "có dấu" / "test.db")
    assert db.glossaries() == [glossary]
    db.delete_glossary("1")
    assert db.glossaries() == []
    db.close()
