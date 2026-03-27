from __future__ import annotations

import re

from catalog_assistant.models import CourseRule, ProgramRequirement, RawDocument
from catalog_assistant.utils import extract_course_codes, normalize_course_code


def _extract_course_title(doc: RawDocument) -> tuple[str, str]:
    title = doc.title
    match = re.search(r"\b([A-Z]{2,4}\s?\d{4}[A-Z]?)\b", title.upper())
    if match:
        code = normalize_course_code(match.group(1))
        return code, title
    codes = extract_course_codes(doc.text)
    code = codes[0] if codes else doc.source_id.upper()
    return code, title


def _extract_field(text: str, label: str) -> str | None:
    pattern = rf"{label}[:.]?\s*(.+?)(?=\n[A-Z][A-Za-z ]+[:.]|\Z)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return " ".join(match.group(1).split())
    return None


def _extract_credit_hours(text: str) -> int | None:
    match = re.search(r"(\d)\s+(?:semester )?credit hours", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def parse_course_rules(docs: list[RawDocument]) -> dict[str, CourseRule]:
    rules: dict[str, CourseRule] = {}
    for doc in docs:
        if doc.category != "course":
            continue
        code, title = _extract_course_title(doc)
        rules[code] = CourseRule(
            course_code=code,
            title=title,
            url=doc.url,
            prerequisite_text=_extract_field(doc.text, "Prerequisite"),
            corequisite_text=_extract_field(doc.text, "Corequisite"),
            credit_hours=_extract_credit_hours(doc.text),
        )
    return rules


def parse_program_requirements(docs: list[RawDocument]) -> list[ProgramRequirement]:
    requirements: list[ProgramRequirement] = []
    for doc in docs:
        if doc.category != "program":
            continue
        for heading in doc.headings or [doc.title]:
            codes = extract_course_codes(doc.text)
            requirements.append(
                ProgramRequirement(
                    program_name=doc.title,
                    url=doc.url,
                    heading=heading,
                    text=doc.text,
                    course_codes=codes,
                )
            )
    return requirements

