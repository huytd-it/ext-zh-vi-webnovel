"""Collect installed runtime dependency notices, excluding dev/test distributions."""
import importlib.metadata as metadata
import json
import shutil
import sys
import tomllib
from pathlib import Path

import httpx

from packaging.requirements import Requirement

root = Path(__file__).resolve().parents[1]
project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
pending = list(project["dependencies"])
seen = set()
inventory = []
target = root / "dist" / "NovelLocal" / "THIRD_PARTY_LICENSES"
target.mkdir(parents=True, exist_ok=True)
known_sources = {
    ("ctranslate2", "4.8.3"): "https://raw.githubusercontent.com/OpenNMT/CTranslate2/v4.8.3/LICENSE",
    ("sentencepiece", "0.2.2"): "https://raw.githubusercontent.com/google/sentencepiece/v0.2.2/LICENSE",
    ("tokenizers", "0.21.1"): "https://raw.githubusercontent.com/huggingface/tokenizers/v0.21.1/LICENSE",
    ("tqdm", "4.70.1"): "https://raw.githubusercontent.com/tqdm/tqdm/v4.70.1/LICENCE",
}
while pending:
    requirement = Requirement(pending.pop())
    if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
        continue
    name = requirement.name.lower().replace("_", "-")
    if name in seen:
        continue
    seen.add(name)
    distribution = metadata.distribution(name)
    pending.extend(distribution.requires or [])
    copied = []
    for file in distribution.files or []:
        if "dist-info" in str(file) and any(word in file.name.lower() for word in ["license", "copying", "notice"]):
            source = Path(distribution.locate_file(file))
            dest = target / name / file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            copied.append(str(dest.relative_to(target)))
    source_url = known_sources.get((name, distribution.version))
    if not copied and source_url and "--fetch-missing" in sys.argv:
        response = httpx.get(source_url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        dest = target / name / "LICENSE.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        copied.append(str(dest.relative_to(target)))
    inventory.append({"name": name, "version": distribution.version,
                      "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License"),
                      "files": copied, "source_url": source_url})
(target / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Collected notices for {len(inventory)} runtime distributions. Review inventory before release.")
