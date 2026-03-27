from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, TypeVar


T = TypeVar("T")

COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4}\s?\d{4}[A-Z]?)\b")


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    path = root_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifacts_dir() -> Path:
    path = root_dir() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_course_code(value: str) -> str:
    value = value.upper().strip()
    value = re.sub(r"\s+", "", value)
    return value


def extract_course_codes(text: str) -> list[str]:
    seen: list[str] = []
    for match in COURSE_CODE_RE.findall(text.upper()):
        code = normalize_course_code(match)
        if code not in seen:
            seen.append(code)
    return seen


def dump_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

