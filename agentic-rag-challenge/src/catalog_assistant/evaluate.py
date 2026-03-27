from __future__ import annotations

import json

from catalog_assistant.assistant import CatalogAssistant
from catalog_assistant.models import RawDocument, StudentCourse
from catalog_assistant.qa import answer_catalog_question
from catalog_assistant.utils import artifacts_dir, data_dir, dump_json


def _load_docs() -> list[RawDocument]:
    path = artifacts_dir() / "documents.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [RawDocument.model_validate(item) for item in payload]


def _load_eval_set() -> list[dict]:
    path = data_dir() / "evaluation_queries.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_completed(entries: list[str]) -> list[StudentCourse]:
    parsed: list[StudentCourse] = []
    for entry in entries:
        if ":" in entry:
            code, grade = entry.split(":", 1)
            parsed.append(StudentCourse(course_code=code, grade=grade))
        else:
            parsed.append(StudentCourse(course_code=entry))
    return parsed


def run_evaluation() -> dict:
    docs = _load_docs()
    assistant = CatalogAssistant(docs)
    rows: list[dict] = []
    citations_present = 0
    prereq_total = 0
    prereq_correct = 0
    abstain_total = 0
    abstain_correct = 0

    for item in _load_eval_set():
        task = item["task"]
        if task == "prereq":
            result = assistant.answer_prereq(item["target_course"], _parse_completed(item.get("completed", [])))
            answer_payload = result.model_dump()
            if result.citations:
                citations_present += 1
            prereq_total += 1
            if result.decision == item["expected_decision"]:
                prereq_correct += 1
        elif task == "plan":
            result = assistant.plan_term(
                major=item.get("major"),
                catalog_year=item.get("catalog_year"),
                target_term=item.get("target_term", "Fall"),
                max_credits=item.get("max_credits"),
                completed_courses=_parse_completed(item.get("completed", [])),
            )
            answer_payload = result.model_dump()
            if result.citations:
                citations_present += 1
        else:
            result = answer_catalog_question(item["question"])
            answer_payload = result.model_dump()
            if result.citations:
                citations_present += 1
            if item.get("expected_mode") == "abstain":
                abstain_total += 1
                if result.answer.startswith("I don't have that information"):
                    abstain_correct += 1

        rows.append({"id": item["id"], "task": task, "result": answer_payload})

    metrics = {
        "citation_coverage_rate": round((citations_present / len(rows)) * 100, 2) if rows else 0.0,
        "eligibility_correctness": round((prereq_correct / prereq_total) * 100, 2) if prereq_total else 0.0,
        "abstention_accuracy": round((abstain_correct / abstain_total) * 100, 2) if abstain_total else 0.0,
        "rubric": {
            "prerequisite_checks": "Correct if the eligibility label matches the expected decision from the catalog prerequisite text.",
            "citation_coverage": "A response counts as covered if it includes at least one source citation.",
            "abstention": "Correct if the assistant explicitly says the information is not in the provided catalog/policies.",
        },
    }

    report = {"metrics": metrics, "results": rows}
    dump_json(artifacts_dir() / "evaluation_report.json", report)
    return report
