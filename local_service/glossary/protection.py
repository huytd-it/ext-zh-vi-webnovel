import re
import unicodedata

from opencc import OpenCC

_converter = OpenCC("t2s")
MARKER = re.compile(r"ZXQ[A-Z0-9]*QXZ", re.IGNORECASE)


def normalize(value):
    return _converter.convert(unicodedata.normalize("NFC", value))


def validate_entries(entries):
    seen = set()
    for entry in entries:
        key = normalize(entry["source"]).strip()
        if not key or not entry["target"].strip() or MARKER.search(key + entry["target"]):
            raise ValueError("Thuật ngữ rỗng hoặc chứa marker dành riêng.")
        if key in seen:
            raise ValueError("Nguồn thuật ngữ trùng hoặc xung đột sau chuẩn hóa.")
        seen.add(key)


def protect(text, entries):
    active = {normalize(e["source"]).strip(): e["target"].strip() for e in entries if e["enabled"]}
    if not active or MARKER.search(text):
        return text, {}
    pattern = re.compile("|".join(re.escape(k) for k in sorted(active, key=len, reverse=True)))
    markers = {}

    def replace(match):
        if len(markers) >= 128:
            raise ValueError("Quá giới hạn marker; cần fallback")
        marker = f"ZXQ{len(markers):04d}QXZ"
        markers[marker] = active[match.group()]
        return marker

    return pattern.sub(replace, text), markers


def restore(text, markers):
    if any(text.count(marker) != 1 for marker in markers):
        raise ValueError("Marker thiếu hoặc trùng")
    for marker, target in markers.items():
        text = text.replace(marker, target)
    # Also detect corrupted marker fragments, never leak them to the page.
    if re.search(r"Z\s*X\s*Q|Q\s*X\s*Z", text, re.IGNORECASE):
        raise ValueError("Marker bị méo")
    return text
