from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


class ModelMixin:
    @classmethod
    def model_validate(cls, payload: dict):
        return cls(**payload)

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass
class SourceEntry(ModelMixin):
    id: str
    category: Literal["course", "program", "policy"]
    url: str
    note: str
    accessed_on: str


@dataclass
class RawDocument(ModelMixin):
    source_id: str
    category: Literal["course", "program", "policy"]
    url: str
    title: str
    headings: list[str] = field(default_factory=list)
    text: str = ""


@dataclass
class ChunkRecord(ModelMixin):
    chunk_id: str
    source_id: str
    category: Literal["course", "program", "policy"]
    url: str
    title: str
    heading: str
    text: str


@dataclass
class CourseRule(ModelMixin):
    course_code: str
    title: str
    url: str
    prerequisite_text: str | None = None
    corequisite_text: str | None = None
    credit_hours: int | None = None


@dataclass
class ProgramRequirement(ModelMixin):
    program_name: str
    url: str
    heading: str
    text: str
    course_codes: list[str] = field(default_factory=list)


@dataclass
class StudentCourse(ModelMixin):
    course_code: str
    grade: str | None = None


@dataclass
class PrereqDecision(ModelMixin):
    decision: Literal["Eligible", "Not eligible", "Need more info"]
    reason: str
    next_step: str
    citations: list[str]
    missing_items: list[str] = field(default_factory=list)


@dataclass
class PlannedCourse(ModelMixin):
    course_code: str
    why: str
    citations: list[str]


@dataclass
class PlanResult(ModelMixin):
    answer: str
    courses: list[PlannedCourse]
    citations: list[str]
    clarifying_questions: list[str]
    assumptions: list[str]


@dataclass
class QueryAnswer(ModelMixin):
    answer: str
    why: str
    citations: list[str]
    clarifying_questions: list[str]
    assumptions: list[str]
