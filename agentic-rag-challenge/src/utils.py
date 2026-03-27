from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CATALOG_SOURCES_DIR = DATA_DIR / "catalog_sources"
FAISS_DIR = PROJECT_ROOT / "faiss_catalog_index"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"


@dataclass
class CourseRecord:
    course_code: str
    title: str
    units: str
    prerequisites: list[str]
    co_requisites: list[str]
    description: str
    notes: str
    source_url: str
    source_type: str
    catalog_year: str
    accessed_date: str
    min_grade: str | None = None
    sequence_rank: int = 999
    tags: list[str] = field(default_factory=list)


@dataclass
class RequirementRecord:
    requirement_id: str
    program: str
    section: str
    content: str
    source_url: str
    source_type: str
    catalog_year: str
    accessed_date: str


@dataclass
class PolicyRecord:
    policy_id: str
    title: str
    category: str
    content: str
    source_url: str
    source_type: str
    catalog_year: str
    accessed_date: str


def ensure_directories() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_jsonl(path: str | Path) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def is_placeholder_record(row: dict) -> bool:
    return any(key in row for key in ("_meta", "_schema", "_comment"))


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def parse_completed_courses(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


COURSE_CODE_RE = re.compile(r"\b(?:COMPSCI|MATH|EECS|DATA|STAT|PHYSICS|ENGIN)\s?[A-Z]?\d+[A-Z]{0,2}\b")
GRADE_ORDER = {
    "A+": 12,
    "A": 11,
    "A-": 10,
    "B+": 9,
    "B": 8,
    "B-": 7,
    "C+": 6,
    "C": 5,
    "C-": 4,
    "D+": 3,
    "D": 2,
    "D-": 1,
    "F": 0,
    "P": 4,
}


def normalize_course_code(value: str) -> str:
    text = value.upper().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_course_codes(text: str) -> list[str]:
    seen: list[str] = []
    for match in COURSE_CODE_RE.findall(text.upper()):
        normalized = normalize_course_code(match)
        if normalized not in seen:
            seen.append(normalized)
    return seen


def parse_completed_with_grades(entries: list[str]) -> dict[str, str | None]:
    completed: dict[str, str | None] = {}
    for entry in entries:
        raw = entry.strip()
        if not raw:
            continue
        if ":" in raw:
            code, grade = raw.split(":", 1)
            completed[normalize_course_code(code)] = grade.strip().upper()
        else:
            completed[normalize_course_code(raw)] = None
    return completed


def grade_meets(actual: str | None, minimum: str | None) -> bool:
    if minimum is None:
        return True
    if actual is None:
        return False
    return GRADE_ORDER.get(actual.upper(), -1) >= GRADE_ORDER.get(minimum.upper(), 99)


def load_course_records(path: str | Path = PROCESSED_DIR / "courses.jsonl") -> dict[str, CourseRecord]:
    records: dict[str, CourseRecord] = {}
    for row in load_jsonl(path):
        if is_placeholder_record(row):
            continue
        record = CourseRecord(
            course_code=normalize_course_code(row["course_code"]),
            title=row["title"],
            units=str(row["units"]),
            prerequisites=row.get("prerequisites", []),
            co_requisites=row.get("co_requisites", []),
            description=row.get("description", ""),
            notes=row.get("notes", ""),
            source_url=row["source_url"],
            source_type=row.get("source_type", "course"),
            catalog_year=row["catalog_year"],
            accessed_date=row["accessed_date"],
            min_grade=row.get("min_grade"),
            sequence_rank=row.get("sequence_rank", 999),
            tags=row.get("tags", []),
        )
        records[record.course_code] = record
    return records


def load_requirement_records(path: str | Path = PROCESSED_DIR / "requirements.jsonl") -> list[RequirementRecord]:
    records: list[RequirementRecord] = []
    for row in load_jsonl(path):
        if is_placeholder_record(row):
            continue
        records.append(
            RequirementRecord(
                requirement_id=row["requirement_id"],
                program=row["program"],
                section=row["section"],
                content=row["content"],
                source_url=row["source_url"],
                source_type=row.get("source_type", "requirement"),
                catalog_year=row["catalog_year"],
                accessed_date=row["accessed_date"],
            )
        )
    return records


def load_policy_records(path: str | Path = PROCESSED_DIR / "policies.jsonl") -> list[PolicyRecord]:
    records: list[PolicyRecord] = []
    for row in load_jsonl(path):
        if is_placeholder_record(row):
            continue
        records.append(
            PolicyRecord(
                policy_id=row["policy_id"],
                title=row["title"],
                category=row["category"],
                content=row["content"],
                source_url=row["source_url"],
                source_type=row.get("source_type", "policy"),
                catalog_year=row["catalog_year"],
                accessed_date=row["accessed_date"],
            )
        )
    return records


def course_citation(record: CourseRecord, section: str = "Rules & Requirements") -> str:
    return f"[Source: {record.source_url}, {record.course_code} {section}, accessed {record.accessed_date}]"


def requirement_citation(record: RequirementRecord) -> str:
    return f"[Source: {record.source_url}, {record.section}, accessed {record.accessed_date}]"


def policy_citation(record: PolicyRecord) -> str:
    return f"[Source: {record.source_url}, {record.title}, accessed {record.accessed_date}]"
