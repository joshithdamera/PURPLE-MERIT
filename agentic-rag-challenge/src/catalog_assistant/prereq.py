from __future__ import annotations

import re
from dataclasses import dataclass

from catalog_assistant.models import CourseRule, PrereqDecision, StudentCourse
from catalog_assistant.utils import extract_course_codes, normalize_course_code


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
    "P": 5,
}


@dataclass
class ExprNode:
    op: str
    value: str | None = None
    left: "ExprNode | None" = None
    right: "ExprNode | None" = None


def tokenize_prereq(text: str) -> list[str]:
    normalized = text.upper()
    normalized = normalized.replace(",", " ")
    normalized = normalized.replace(";", " ")
    normalized = normalized.replace("/", " / ")
    tokens = re.findall(r"[A-Z]{2,4}\s?\d{4}[A-Z]?|\(|\)|AND|OR", normalized)
    return tokens


def parse_expression(tokens: list[str]) -> ExprNode | None:
    if not tokens:
        return None

    precedence = {"OR": 1, "AND": 2}
    output: list[ExprNode] = []
    operators: list[str] = []

    def collapse() -> None:
        op = operators.pop()
        right = output.pop()
        left = output.pop()
        output.append(ExprNode(op=op, left=left, right=right))

    for token in tokens:
        if re.fullmatch(r"[A-Z]{2,4}\s?\d{4}[A-Z]?", token):
            output.append(ExprNode(op="COURSE", value=normalize_course_code(token)))
            continue
        if token in {"AND", "OR"}:
            while operators and operators[-1] in precedence and precedence[operators[-1]] >= precedence[token]:
                collapse()
            operators.append(token)
            continue
        if token == "(":
            operators.append(token)
            continue
        if token == ")":
            while operators and operators[-1] != "(":
                collapse()
            if operators and operators[-1] == "(":
                operators.pop()
    while operators:
        collapse()
    return output[0] if output else None


def extract_min_grade(text: str) -> str | None:
    match = re.search(r"GRADE OF ([ABCDF][+-]?)(?: OR BETTER)?", text.upper())
    if match:
        return match.group(1)
    return None


def grade_meets(actual: str | None, minimum: str | None) -> bool:
    if minimum is None:
        return actual is not None
    if actual is None:
        return False
    return GRADE_ORDER.get(actual.upper(), -1) >= GRADE_ORDER.get(minimum.upper(), 99)


def evaluate_expr(node: ExprNode | None, completed: dict[str, str | None], min_grade: str | None) -> tuple[bool, list[str]]:
    if node is None:
        return True, []
    if node.op == "COURSE":
        code = node.value or ""
        if grade_meets(completed.get(code), min_grade):
            return True, []
        return False, [code]
    left_ok, left_missing = evaluate_expr(node.left, completed, min_grade)
    right_ok, right_missing = evaluate_expr(node.right, completed, min_grade)
    if node.op == "AND":
        return left_ok and right_ok, left_missing + right_missing
    if node.op == "OR":
        return (left_ok or right_ok), ([] if (left_ok or right_ok) else left_missing + right_missing)
    return False, left_missing + right_missing


def evaluate_prerequisites(rule: CourseRule, completed_courses: list[StudentCourse]) -> PrereqDecision:
    completed = {normalize_course_code(item.course_code): item.grade for item in completed_courses}
    prereq_text = rule.prerequisite_text or ""
    if not prereq_text.strip():
        citations = [f"{rule.url} ({rule.course_code} catalog page)"]
        return PrereqDecision(
            decision="Eligible",
            reason="No prerequisite text was found for this course.",
            next_step="You can proceed to normal enrollment checks.",
            citations=citations,
        )

    tokens = tokenize_prereq(prereq_text)
    expr = parse_expression(tokens)
    min_grade = extract_min_grade(prereq_text)
    ok, missing = evaluate_expr(expr, completed, min_grade)
    citations = [f"{rule.url} (Prerequisite section)"]
    if ok:
        return PrereqDecision(
            decision="Eligible",
            reason=f"Completed courses satisfy the stated prerequisite expression: {prereq_text}",
            next_step="Confirm any advisor or instructor-consent restrictions before enrollment.",
            citations=citations,
        )

    coreq_note = ""
    if rule.corequisite_text:
        coreq_codes = extract_course_codes(rule.corequisite_text)
        coreq_note = f" Corequisite noted: {'/'.join(coreq_codes) if coreq_codes else rule.corequisite_text}"
    return PrereqDecision(
        decision="Not eligible",
        reason=f"The catalog prerequisite text is not fully satisfied: {prereq_text}.{coreq_note}".strip(),
        next_step=f"Take or complete {', '.join(sorted(set(missing)))} before attempting {rule.course_code}.",
        citations=citations + ([f"{rule.url} (Corequisite section)"] if rule.corequisite_text else []),
        missing_items=sorted(set(missing)),
    )

