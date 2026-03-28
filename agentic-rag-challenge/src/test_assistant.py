from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from orchestration import CoursePlanningAssistant


class CoursePlanningAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assistant = CoursePlanningAssistant.from_artifacts()

    def test_simple_prerequisite_eligibility(self) -> None:
        result = self.assistant.check_eligibility(
            question="Can I take COMPSCI 170 if I've completed COMPSCI 61B and COMPSCI 70?",
            student_courses=["COMPSCI 61B", "COMPSCI 70"],
            target_course="COMPSCI 170",
        )
        self.assertIn("Eligible", result["raw_response"])
        self.assertTrue(result["citations"])

    def test_safe_abstention_for_live_schedule(self) -> None:
        result = self.assistant.answer_question("Is COMPSCI 161 offered next semester?")
        self.assertIn("don't have that information", result["formatted_response"].lower())
        self.assertEqual(result["citations"], [])

    def test_program_requirement_answer_is_cited(self) -> None:
        result = self.assistant.answer_question("What breadth requirements do computer science students need to satisfy?")
        self.assertIn("breadth", result["formatted_response"].lower())
        self.assertTrue(result["citations"])

    def test_min_grade_requirement_is_enforced(self) -> None:
        result = self.assistant.check_eligibility(
            question="Can I take COMPSCI C187 if I completed COMPSCI C100 with a D?",
            student_courses=["COMPSCI C100:D"],
            target_course="COMPSCI C187",
        )
        self.assertIn("Not Eligible", result["raw_response"])
        self.assertIn("C-", result["formatted_response"])

    def test_corequisite_rule_returns_need_more_info(self) -> None:
        result = self.assistant.check_eligibility(
            question="If I have COMPSCI 61C, can I take COMPSCI 186 concurrently with COMPSCI 47C?",
            student_courses=["COMPSCI 61C"],
            target_course="COMPSCI 186",
        )
        self.assertIn("Need More Info", result["raw_response"])
        self.assertIn("co-requisite", result["formatted_response"].lower())

    def test_instructor_consent_exception_is_safe(self) -> None:
        result = self.assistant.check_eligibility(
            question="Can instructor consent let me take COMPSCI 189 without MATH 54?",
            student_courses=["MATH 53", "COMPSCI 70"],
            target_course="COMPSCI 189",
        )
        self.assertIn("Need More Info", result["raw_response"])
        self.assertIn("instructor consent", result["formatted_response"].lower())

    def test_alias_lookup_handles_cs_prefix(self) -> None:
        result = self.assistant.answer_question("What do I need before taking CS 170?")
        self.assertIn("COMPSCI 170", result["formatted_response"])
        self.assertTrue(result["citations"])


if __name__ == "__main__":
    unittest.main()
