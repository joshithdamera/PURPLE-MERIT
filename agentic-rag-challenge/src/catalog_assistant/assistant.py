from __future__ import annotations

from catalog_assistant.catalog import parse_course_rules, parse_program_requirements
from catalog_assistant.models import PlanResult, PrereqDecision, QueryAnswer, RawDocument, StudentCourse
from catalog_assistant.planner import build_term_plan
from catalog_assistant.prereq import evaluate_prerequisites
from catalog_assistant.qa import answer_catalog_question


class CatalogAssistant:
    def __init__(self, docs: list[RawDocument]) -> None:
        self.docs = docs
        self.course_rules = parse_course_rules(docs)
        self.requirements = parse_program_requirements(docs)

    def answer_prereq(self, target_course: str, completed_courses: list[StudentCourse]) -> PrereqDecision:
        code = target_course.replace(" ", "").upper()
        rule = self.course_rules.get(code)
        if not rule:
            return PrereqDecision(
                decision="Need more info",
                reason="I could not find that course in the indexed catalog documents.",
                next_step="Verify the course code or add the course page to the source manifest.",
                citations=[],
            )
        return evaluate_prerequisites(rule, completed_courses)

    def plan_term(
        self,
        major: str | None,
        catalog_year: str | None,
        target_term: str,
        max_credits: int | None,
        completed_courses: list[StudentCourse],
    ) -> PlanResult:
        return build_term_plan(
            major=major,
            catalog_year=catalog_year,
            target_term=target_term,
            max_credits=max_credits,
            completed_courses=completed_courses,
            course_rules=self.course_rules,
            requirements=self.requirements,
        )

    def answer_question(self, question: str) -> QueryAnswer:
        return answer_catalog_question(question)
