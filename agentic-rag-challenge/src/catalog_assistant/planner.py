from __future__ import annotations

import re
from collections import defaultdict

from catalog_assistant.models import CourseRule, PlanResult, PlannedCourse, ProgramRequirement, StudentCourse
from catalog_assistant.prereq import evaluate_prerequisites
from catalog_assistant.utils import extract_course_codes, normalize_course_code


def clarify_for_plan(
    major: str | None,
    catalog_year: str | None,
    completed_courses: list[StudentCourse],
    max_credits: int | None,
) -> list[str]:
    questions: list[str] = []
    if not major:
        questions.append("Which major or program should I plan for?")
    if not catalog_year:
        questions.append("Which catalog year applies to you?")
    if not completed_courses:
        questions.append("Which courses have you completed, and what grades did you earn where prerequisites require minimum grades?")
    if max_credits is None:
        questions.append("What is your maximum credit load for the next term?")
    return questions[:5]


def _requirement_map(requirements: list[ProgramRequirement], major: str) -> dict[str, list[ProgramRequirement]]:
    matched = [item for item in requirements if major.lower() in item.program_name.lower()]
    grouped: dict[str, list[ProgramRequirement]] = defaultdict(list)
    for item in matched:
        grouped[item.heading].append(item)
    return grouped


def build_term_plan(
    major: str | None,
    catalog_year: str | None,
    target_term: str,
    max_credits: int | None,
    completed_courses: list[StudentCourse],
    course_rules: dict[str, CourseRule],
    requirements: list[ProgramRequirement],
) -> PlanResult:
    clarifying_questions = clarify_for_plan(major, catalog_year, completed_courses, max_credits)
    if clarifying_questions:
        return PlanResult(
            answer="I need a few details before I can produce a grounded term plan.",
            courses=[],
            citations=[],
            clarifying_questions=clarifying_questions,
            assumptions=[],
        )

    assert major is not None
    assert max_credits is not None

    completed_set = {normalize_course_code(item.course_code) for item in completed_courses}
    requirement_groups = _requirement_map(requirements, major)
    candidate_codes: list[tuple[str, str, str]] = []
    for heading, items in requirement_groups.items():
        for item in items:
            for code in item.course_codes:
                if code not in completed_set:
                    candidate_codes.append((code, heading, item.url))

    seen: set[str] = set()
    deduped_candidates: list[tuple[str, str, str]] = []
    for code, heading, url in candidate_codes:
        if code in seen:
            continue
        seen.add(code)
        deduped_candidates.append((code, heading, url))

    def sort_key(item: tuple[str, str, str]) -> tuple[int, str]:
        match = re.search(r"(\d{4})", item[0])
        course_number = int(match.group(1)) if match else 9999
        return (course_number, item[0])

    planned: list[PlannedCourse] = []
    used_credits = 0
    aggregated_citations: list[str] = []
    for code, heading, program_url in sorted(deduped_candidates, key=sort_key):
        rule = course_rules.get(code)
        if not rule:
            continue
        decision = evaluate_prerequisites(rule, completed_courses)
        if decision.decision != "Eligible":
            continue
        course_credits = rule.credit_hours or 3
        if used_credits + course_credits > max_credits:
            break
        why = f"{code} fits the {heading} requirement and its catalog prerequisites are satisfied from your completed work."
        citations = [f"{program_url} ({heading})"] + decision.citations
        planned.append(PlannedCourse(course_code=code, why=why, citations=citations))
        aggregated_citations.extend(citations)
        used_credits += course_credits

    assumptions = [
        f"Term selected: {target_term}. I did not find authoritative term-by-term offering data in the catalog alone.",
        "If transfer equivalencies or waivers apply, an advisor should confirm them against your degree audit.",
    ]
    answer = "Suggested next-term plan based on catalog requirements and satisfied prerequisites."
    return PlanResult(
        answer=answer,
        courses=planned,
        citations=sorted(set(aggregated_citations)),
        clarifying_questions=[],
        assumptions=assumptions,
    )

