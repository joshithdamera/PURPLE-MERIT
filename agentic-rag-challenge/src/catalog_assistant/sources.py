from __future__ import annotations

from pathlib import Path

from catalog_assistant.models import SourceEntry
from catalog_assistant.utils import data_dir


def source_manifest_path() -> Path:
    return data_dir() / "sources.json"


def load_sources() -> list[SourceEntry]:
    payload = source_manifest_path().read_text(encoding="utf-8")
    import json

    return [SourceEntry.model_validate(item) for item in json.loads(payload)]

