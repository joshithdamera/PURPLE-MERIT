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


if __name__ == "__main__":
    unittest.main()
