from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from orchestration import CoursePlanningAssistant  # noqa: E402


TEST_QUERIES_PATH = ROOT / "evaluation" / "test_queries.jsonl"
RESULTS_PATH = ROOT / "evaluation" / "results.json"
REQUIRED_SECTIONS = [
    "Answer / Plan:",
    "Why (requirements/prereqs satisfied):",
    "Citations:",
    "Clarifying questions (if needed):",
    "Assumptions / Not in catalog:",
]


def load_test_queries(path: Path = TEST_QUERIES_PATH) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def response_has_required_format(text: str) -> bool:
    return all(section in text for section in REQUIRED_SECTIONS)


def matches_keywords(text: str, expected_keywords: list[str]) -> bool:
    lowered = text.lower()
    return all(keyword.lower() in lowered for keyword in expected_keywords)


def run_single_query(assistant: CoursePlanningAssistant, query: dict) -> dict:
    category = query["category"]
    if category in {"simple_prerequisite", "chain_reasoning"}:
        result = assistant.check_eligibility(
            student_courses=query["student_profile"].get("completed_courses", []),
            target_course=query["student_profile"].get("target_course", ""),
            question=query["query"],
        )
        decision_correct = query["expected_decision"].lower() in result["raw_response"].lower()
        expected_citations = query.get("expected_citations", 1)
        citation_present = len(result["citations"]) >= expected_citations and (expected_citations == 0 or "[C" in result["formatted_response"])
        format_ok = response_has_required_format(result["formatted_response"])
        return {
            "category": category,
            "query_id": query["id"],
            "query": query["query"],
            "correct": decision_correct,
            "citation_present": citation_present,
            "format_ok": format_ok,
            "response": result["formatted_response"],
        }

    if category == "program_requirements":
        result = assistant.answer_question(query["query"])
        correct = matches_keywords(result["formatted_response"], query.get("expected_keywords", []))
        expected_citations = query.get("expected_citations", 1)
        return {
            "category": category,
            "query_id": query["id"],
            "query": query["query"],
            "correct": correct,
            "citation_present": len(result["citations"]) >= expected_citations and (expected_citations == 0 or "[C" in result["formatted_response"]),
            "format_ok": response_has_required_format(result["formatted_response"]),
            "response": result["formatted_response"],
        }

    result = assistant.answer_question(query["query"])
    abstained = "don't have that information" in result["formatted_response"].lower() or "not in catalog" in result["formatted_response"].lower()
    expected_citations = query.get("expected_citations", 0)
    return {
        "category": category,
        "query_id": query["id"],
        "query": query["query"],
        "correct": abstained,
        "citation_present": len(result["citations"]) >= expected_citations and (expected_citations == 0 or "[C" in result["formatted_response"]),
        "format_ok": response_has_required_format(result["formatted_response"]),
        "response": result["formatted_response"],
    }


def run_evaluation() -> dict:
    assistant = CoursePlanningAssistant.from_artifacts()
    queries = load_test_queries()
    rows = [run_single_query(assistant, query) for query in queries]

    by_category = {
        "simple_prerequisite": [row for row in rows if row["category"] == "simple_prerequisite"],
        "chain_reasoning": [row for row in rows if row["category"] == "chain_reasoning"],
        "program_requirements": [row for row in rows if row["category"] == "program_requirements"],
        "safe_abstention": [row for row in rows if row["category"] == "safe_abstention"],
    }

    def score(bucket: list[dict]) -> float:
        return round((sum(1 for row in bucket if row["correct"]) / len(bucket)) * 100, 2) if bucket else 0.0

    citation_coverage = round((sum(1 for row in rows if row["citation_present"]) / len(rows)) * 100, 2) if rows else 0.0
    format_compliance = round((sum(1 for row in rows if row["format_ok"]) / len(rows)) * 100, 2) if rows else 0.0

    metrics = {
        "citation_coverage": citation_coverage,
        "eligibility_accuracy": score(by_category["simple_prerequisite"]),
        "chain_accuracy": score(by_category["chain_reasoning"]),
        "program_accuracy": score(by_category["program_requirements"]),
        "abstention_accuracy": score(by_category["safe_abstention"]),
        "format_compliance": format_compliance,
    }
    weighted_score = round(
        (metrics["citation_coverage"] * 0.20)
        + (metrics["eligibility_accuracy"] * 0.25)
        + (metrics["chain_accuracy"] * 0.20)
        + (metrics["program_accuracy"] * 0.15)
        + (metrics["abstention_accuracy"] * 0.10)
        + (metrics["format_compliance"] * 0.10),
        2,
    )

    report = {
        "total_queries": len(rows),
        "metrics": metrics,
        "weighted_score": weighted_score,
        "grading_note": "This script provides an automated proxy for the rubric. Manual review is still recommended for nuanced chain reasoning and citation specificity.",
        "results": rows,
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_evaluation()
    print(json.dumps(report["metrics"], indent=2))
    print(f"Weighted score: {report['weighted_score']}")


if __name__ == "__main__":
    main()
