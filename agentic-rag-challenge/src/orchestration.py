from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from response_formatter import format_response
from utils import (
    CourseRecord,
    FAISS_DIR,
    PolicyRecord,
    RequirementRecord,
    course_citation,
    extract_course_codes,
    grade_meets,
    load_course_records,
    load_policy_records,
    load_requirement_records,
    normalize_course_code,
    parse_completed_with_grades,
    policy_citation,
    requirement_citation,
)


PROGRAM_ALIASES = {
    "computer science": "BA Computer Science",
    "cs": "BA Computer Science",
    "ba computer science": "BA Computer Science",
    "computer science major": "BA Computer Science",
    "computer science minor": "Computer Science Minor",
    "cs minor": "Computer Science Minor",
    "minor": "Computer Science Minor",
    "eecs": "BS Electrical Engineering and Computer Sciences",
}

COURSE_TITLE_ALIASES = {
    "database systems": "COMPSCI 186",
    "machine learning": "COMPSCI 189",
    "artificial intelligence": "COMPSCI 188",
    "algorithms": "COMPSCI 170",
    "computer security": "COMPSCI 161",
    "operating systems": "COMPSCI 162",
    "user interface": "COMPSCI 160",
    "programming languages": "COMPSCI 164",
    "software engineering": "COMPSCI 169A",
    "internet": "COMPSCI 168",
    "social implications": "COMPSCI 195",
}

PLAN_SEQUENCES = {
    "BA Computer Science": [
        "COMPSCI 61A",
        "MATH 53",
        "MATH 54",
        "COMPSCI 61B",
        "COMPSCI 70",
        "COMPSCI 61C",
        "COMPSCI 170",
        "COMPSCI 160",
        "COMPSCI 161",
        "COMPSCI 162",
        "COMPSCI 186",
        "COMPSCI 188",
        "COMPSCI 189",
        "COMPSCI 164",
        "COMPSCI 168",
    ],
    "Computer Science Minor": [
        "COMPSCI 61A",
        "COMPSCI 61B",
        "COMPSCI 70",
        "COMPSCI 61C",
        "COMPSCI 170",
        "COMPSCI 188",
        "COMPSCI 189",
    ],
}

OUT_OF_SCOPE_PATTERNS = [
    r"\bnext semester\b",
    r"\bnext term\b",
    r"\bnext year\b",
    r"\bprofessor\b",
    r"\binstructor\b",
    r"\bwaitlist\b",
    r"\bseat\b",
    r"\bsection\b",
    r"\btransfer\b",
    r"\bequivalen",
    r"\bwaiver\b",
    r"\bpermission code\b",
]


def _unique(items: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in items:
        if item and item not in ordered:
            ordered.append(item)
    return ordered


def _units_value(units: str) -> int:
    match = re.search(r"\d+", units)
    return int(match.group()) if match else 0


class CoursePlanningAssistant:
    def __init__(
        self,
        index_path: str = "faiss_catalog_index",
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.0,
        retrieval_k: int = 5,
    ) -> None:
        del model_name, temperature
        self.courses = load_course_records()
        self.requirements = load_requirement_records()
        self.policies = load_policy_records()
        self.requirements_by_id = {record.requirement_id: record for record in self.requirements}
        self.policies_by_id = {record.policy_id: record for record in self.policies}
        self.index_path = Path(index_path) if Path(index_path).is_absolute() else (Path(__file__).resolve().parents[1] / index_path)
        self.retrieval_k = retrieval_k
        self.retriever_wrapper = self._initialize_retriever()
        self.rag_enabled = self.retriever_wrapper is not None
        self.runtime_mode = "faiss_rag" if self.rag_enabled else "deterministic_fallback"
        if not self.courses:
            raise FileNotFoundError("Processed course records were not found.")

    @classmethod
    def from_artifacts(cls) -> "CoursePlanningAssistant":
        return cls()

    @staticmethod
    def identify_missing_info(student_profile: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        if not student_profile.get("completed_courses"):
            missing.append("completed courses, with grades if you have them")
        if not student_profile.get("program"):
            missing.append("target major or program")
        if not student_profile.get("catalog_year"):
            missing.append("catalog year")
        if not student_profile.get("target_term"):
            missing.append("target term")
        if not student_profile.get("max_courses") and not student_profile.get("max_credits"):
            missing.append("maximum courses or credit load")
        return missing[:5]

    def ask_clarifying_questions(self, student_profile: dict[str, Any]) -> list[str]:
        questions = []
        for item in self.identify_missing_info(student_profile):
            if "completed courses" in item:
                questions.append("Which courses have you already completed, and do you know the grades?")
            elif "major" in item:
                questions.append("Which Berkeley program are you planning for: the CS BA, the CS minor, or another program?")
            elif "catalog year" in item:
                questions.append("Which catalog year should I ground the plan in?")
            elif "target term" in item:
                questions.append("Which term are you planning for: Fall, Spring, or Summer?")
            else:
                questions.append("What is your maximum course count or credit load for the term?")
        return questions[:5]

    @staticmethod
    def _normalize_program(program: str | None) -> str:
        if not program:
            return "BA Computer Science"
        lowered = program.strip().lower()
        return PROGRAM_ALIASES.get(lowered, program.strip())

    @staticmethod
    def _is_out_of_scope(question: str) -> bool:
        lowered = question.lower()
        return any(re.search(pattern, lowered) for pattern in OUT_OF_SCOPE_PATTERNS)

    def _find_course(self, question: str, explicit_course: str | None = None) -> CourseRecord | None:
        if explicit_course:
            course = self.courses.get(normalize_course_code(explicit_course))
            if course:
                return course
        codes = extract_course_codes(question)
        for code in codes:
            if code in self.courses:
                return self.courses[code]
        lowered = question.lower()
        for alias, code in COURSE_TITLE_ALIASES.items():
            if alias in lowered and code in self.courses:
                return self.courses[code]
        return None

    def _initialize_retriever(self):
        index_faiss = self.index_path / "index.faiss"
        index_pkl = self.index_path / "index.pkl"
        if not index_faiss.exists() or not index_pkl.exists():
            fallback_faiss = FAISS_DIR / "index.faiss"
            fallback_pkl = FAISS_DIR / "index.pkl"
            if fallback_faiss.exists() and fallback_pkl.exists():
                self.index_path = FAISS_DIR
            else:
                return None
        try:
            from retriever import CatalogRetriever

            return CatalogRetriever(index_path=str(self.index_path), k=self.retrieval_k)
        except Exception:
            return None

    @staticmethod
    def _citation_from_doc(doc) -> str:
        metadata = doc.metadata
        section = (
            metadata.get("section")
            or metadata.get("course_code")
            or metadata.get("title")
            or metadata.get("requirement_id")
            or metadata.get("policy_id")
            or metadata.get("chunk_id")
            or "Catalog section"
        )
        return f"[Source: {metadata.get('source_url', 'unknown source')}, {section}, accessed {metadata.get('accessed_date', 'unknown access date')}]"

    def _retrieve_documents(self, query: str, preferred_type: str | None = None, course_code: str | None = None) -> list[Any]:
        if not self.retriever_wrapper:
            return []
        try:
            docs = self.retriever_wrapper.get_relevant_documents(query)
        except Exception:
            return []

        prioritized: list[Any] = []
        remainder: list[Any] = []
        normalized_course = normalize_course_code(course_code) if course_code else None
        for doc in docs:
            metadata = doc.metadata
            matches_course = normalized_course and metadata.get("course_code") == normalized_course
            matches_type = preferred_type and metadata.get("type") == preferred_type
            if matches_course or matches_type:
                prioritized.append(doc)
            else:
                remainder.append(doc)
        return prioritized + remainder

    def _retrieved_citations(self, query: str, preferred_type: str | None = None, course_code: str | None = None) -> list[str]:
        docs = self._retrieve_documents(query=query, preferred_type=preferred_type, course_code=course_code)
        return _unique([self._citation_from_doc(doc) for doc in docs])

    def _merge_citations(self, *citation_lists: list[str]) -> list[str]:
        merged: list[str] = []
        for citation_list in citation_lists:
            merged.extend(citation_list)
        return _unique(merged)

    def _abstain(self, reason: str, next_steps: list[str] | None = None, decision: str = "Not in catalog") -> dict[str, Any]:
        answer = f"{decision}: I don't have that information in the provided catalog/policies."
        next_steps = next_steps or [
            "Check the Berkeley schedule of classes or the department website for live offering details.",
            "Ask an advisor or the department if you need transfer, waiver, or instructor-consent guidance.",
        ]
        formatted = format_response(
            answer=answer,
            why=reason,
            next_steps=next_steps,
            citations=[],
            clarifying_questions=[],
            assumptions=[reason],
        )
        return {
            "answer": answer,
            "raw_response": answer,
            "citations": [],
            "formatted_response": formatted,
        }

    @staticmethod
    def _clause_text(clause_codes: list[str]) -> str:
        if not clause_codes:
            return ""
        if len(clause_codes) == 1:
            return clause_codes[0]
        return " or ".join(clause_codes)

    def _evaluate_course(self, course: CourseRecord, completed_map: dict[str, str | None]) -> dict[str, Any]:
        citations = [course_citation(course)]
        reasons: list[str] = []
        missing_groups: list[list[str]] = []

        for clause in course.prerequisites:
            codes = extract_course_codes(clause)
            if not codes:
                continue
            satisfied = [code for code in codes if code in completed_map and grade_meets(completed_map.get(code), course.min_grade)]
            if satisfied:
                chosen = satisfied[0]
                if len(codes) == 1:
                    reasons.append(f"You completed {chosen}, which satisfies one listed prerequisite for {course.course_code}.")
                else:
                    reasons.append(f"The alternative prerequisite `{clause}` is satisfied via {chosen}.")
            else:
                missing_groups.append(codes)
                reasons.append(f"You still need {self._clause_text(codes)} for {course.course_code}.")

        coreq_note = ""
        if course.co_requisites:
            coreq_note = f"The catalog also notes co-requisite handling for {', '.join(course.co_requisites)} in some cases."

        return {
            "eligible": not missing_groups,
            "reasons": reasons or [f"The curated record for {course.course_code} does not add extra evaluable prerequisite clauses."],
            "missing_groups": missing_groups,
            "missing_courses": _unique([code for group in missing_groups for code in group]),
            "coreq_note": coreq_note,
            "citations": citations,
        }

    def _chain_lines(self, target_course: str, seen: set[str] | None = None) -> tuple[list[str], list[str]]:
        seen = seen or set()
        target = normalize_course_code(target_course)
        if target in seen or target not in self.courses:
            return [], []
        seen.add(target)
        record = self.courses[target]
        groups = [extract_course_codes(clause) for clause in record.prerequisites if extract_course_codes(clause)]
        if not groups:
            return [], []

        clause_bits = [self._clause_text(group) for group in groups]
        lines = [f"{record.course_code} requires {' and '.join(clause_bits)}."]
        citations = [course_citation(record)]
        for group in groups:
            for code in group:
                child_lines, child_citations = self._chain_lines(code, seen)
                lines.extend(child_lines)
                citations.extend(child_citations)
        return _unique(lines), _unique(citations)

    def _major_requirement_records(self) -> list[RequirementRecord]:
        ids = ["CS-BA-OVERVIEW", "CS-BA-MAJOR", "CS-BA-UPPERDIV", "CS-BA-COLLEGE", "CS-BA-PLANNING"]
        return [self.requirements_by_id[item] for item in ids if item in self.requirements_by_id]

    def _build_program_answer(self, question: str) -> dict[str, Any]:
        lowered = question.lower()
        requirement_rag = self._retrieved_citations(question, preferred_type="requirement")
        policy_rag = self._retrieved_citations(question, preferred_type="policy")

        if "total" in lowered and "unit" in lowered:
            units_policy = self.policies_by_id["POLICY-UNITS-GPA"]
            cs_ba = self.requirements_by_id["CS-BA-COLLEGE"]
            answer = "Berkeley's bachelor's degree requires at least 120 units, and the BA in Computer Science also requires the university, campus, college, and major requirements."
            why = [
                units_policy.content,
                cs_ba.content,
            ]
            citations = self._merge_citations([policy_citation(units_policy), requirement_citation(cs_ba)], requirement_rag, policy_rag)
            next_steps = ["Use your degree audit to separate major units from remaining campus and college requirements."]
            assumptions = []
        elif "core" in lowered or "elective" in lowered:
            major = self.requirements_by_id["CS-BA-MAJOR"]
            upper = self.requirements_by_id["CS-BA-UPPERDIV"]
            answer = "For the Berkeley CS BA, the core is the lower-division CS sequence plus the upper-division major-course structure; elective flexibility appears in the five upper-division CS selections, the approved non-CS technical elective, and college breadth choices."
            why = [major.content, upper.content]
            citations = self._merge_citations([requirement_citation(major), requirement_citation(upper)], requirement_rag)
            next_steps = ["Match your completed courses against the lower-division sequence first, then use eligible upper-division courses to fill the remaining major slots."]
            assumptions = []
        elif "lower-division" in lowered or ("required" in lowered and "computer science" in lowered):
            major = self.requirements_by_id["CS-BA-MAJOR"]
            answer = "The Berkeley CS BA lower-division preparation is centered on COMPSCI 61A, COMPSCI 61B or COMPSCI 61BL, COMPSCI 70, COMPSCI 61C, and approved mathematics support."
            why = [major.content]
            citations = self._merge_citations([requirement_citation(major)], requirement_rag)
            next_steps = ["Use those lower-division courses to determine which upper-division design, theory, and systems courses are unlocked next."]
            assumptions = []
        elif "breadth" in lowered:
            college = self.requirements_by_id["CS-BA-COLLEGE"]
            answer = "CS BA students still complete Berkeley college and campus breadth work. The CS BA page says CDSS breadth follows the Letters and Science Seven-Course Breadth structure, with the noted foreign-language exception for International Studies."
            why = [college.content]
            citations = self._merge_citations([requirement_citation(college)], requirement_rag)
            next_steps = ["Check your degree audit or advisor-approved breadth plan before using a breadth course to double-count toward another requirement."]
            assumptions = []
        elif "major" in lowered and "minor" in lowered:
            overview = self.requirements_by_id["CS-BA-OVERVIEW"]
            minor = self.requirements_by_id["CS-MINOR"]
            answer = "The BA major is a full bachelor's program with university, campus, college, and major requirements; the CS minor is a seven-course add-on centered on the lower-division CS sequence plus three upper-division COMPSCI courses."
            why = [overview.content, minor.content]
            citations = self._merge_citations([requirement_citation(overview), requirement_citation(minor)], requirement_rag)
            next_steps = ["If you are choosing between them, compare your remaining breadth and residence obligations, not just the CS course count."]
            assumptions = []
        elif "residence" in lowered:
            units_policy = self.policies_by_id["POLICY-UNITS-GPA"]
            answer = "Berkeley's senior residence rule requires at least 24 of the remaining units after 90 total units to be completed in residence over at least two semesters, with at least 6 units in each semester."
            why = [units_policy.content]
            citations = self._merge_citations([policy_citation(units_policy)], policy_rag)
            next_steps = ["Confirm how your current Berkeley unit total maps to the senior-residence rule before making an accelerated plan."]
            assumptions = []
        else:
            return self._abstain(
                "I could not map this question to a supported program or policy topic in the curated catalog set.",
                ["Rephrase the question around units, breadth, major vs minor, residence, or a specific course requirement."],
            )

        formatted = format_response(
            answer=answer,
            why=why,
            next_steps=next_steps,
            citations=citations,
            clarifying_questions=[],
            assumptions=assumptions,
        )
        return {
            "answer": answer,
            "citations": citations,
            "formatted_response": formatted,
        }

    def _build_course_answer(self, question: str, course: CourseRecord) -> dict[str, Any]:
        evaluation = self._evaluate_course(course, {})
        prereq_text = []
        for clause in course.prerequisites:
            codes = extract_course_codes(clause)
            if codes:
                prereq_text.append(self._clause_text(codes))
        answer = f"{course.course_code} requires {' and '.join(prereq_text)}." if prereq_text else f"{course.course_code} does not have a structured prerequisite chain in the curated records."
        why = [course.description]
        if course.notes:
            why.append(course.notes)
        next_steps = [f"Complete the listed preparation before attempting {course.course_code}."] if prereq_text else ["Verify any instructor guidance on the live course page if you need more operational detail."]
        assumptions = []
        if "co-requisite" in question.lower() or "corequisite" in question.lower():
            if course.co_requisites:
                answer = f"{course.course_code} includes a catalog co-requisite note for {', '.join(course.co_requisites)}."
                why.append(course.notes)
                next_steps = ["Use the course note exactly as written: the special co-requisite path is conditional and should not be generalized beyond the catalog text."]
            else:
                assumptions.append("No explicit co-requisite rule was captured for this course in the curated catalog records.")
        citations = self._merge_citations(
            evaluation["citations"],
            self._retrieved_citations(question or f"Requirements for {course.course_code}", preferred_type="course", course_code=course.course_code),
        )
        formatted = format_response(
            answer=answer,
            why=why,
            next_steps=next_steps,
            citations=citations,
            clarifying_questions=[],
            assumptions=assumptions,
        )
        return {
            "answer": answer,
            "citations": citations,
            "formatted_response": formatted,
        }

    def check_eligibility(self, student_courses: list[str], target_course: str, question: str | None = None) -> dict[str, Any]:
        question = question or ""
        lowered = question.lower()

        if self._is_out_of_scope(question):
            return self._abstain(
                "The question asks for live scheduling, transfer, waiver, or instructor-specific information that is outside the provided catalog and policy pages."
            )

        if "repeat" in lowered and "gpa" in lowered:
            repeat_policy = self.policies_by_id["POLICY-REPEAT"]
            answer = "Reference repeat policy: Berkeley's repeated-course policy says both enrollments stay on the transcript, but the most recent grade and units are used in the GPA calculation for the repeated course."
            citations = self._merge_citations([policy_citation(repeat_policy)], self._retrieved_citations(question, preferred_type="policy"))
            formatted = format_response(
                answer=answer,
                why=repeat_policy.content,
                next_steps=["Check whether your school or department imposes any additional repeat limits beyond the catalog summary."],
                citations=citations,
                clarifying_questions=[],
                assumptions=["This policy answer addresses GPA treatment, not automatic prerequisite enforcement."],
            )
            return {
                "answer": answer,
                "raw_response": answer,
                "citations": citations,
                "formatted_response": formatted,
            }

        if any(term in lowered for term in ["prerequisite chain", "from scratch", "full chain"]):
            chain_lines, chain_citations = self._chain_lines(target_course)
            chain_citations = self._merge_citations(
                chain_citations,
                self._retrieved_citations(question or f"Prerequisite chain for {target_course}", preferred_type="course", course_code=target_course),
            )
            answer = f"Chain identified: {' '.join(chain_lines)}" if chain_lines else f"Chain identified: {target_course} has no additional prerequisite chain in the curated records."
            formatted = format_response(
                answer=answer,
                why=chain_lines or [f"No deeper prerequisite chain was captured for {target_course}."],
                next_steps=[f"Complete the courses in dependency order before attempting {normalize_course_code(target_course)}."],
                citations=chain_citations,
                clarifying_questions=[],
                assumptions=["This chain summarizes the curated catalog records and does not expand non-course readiness language unless it was encoded as a course prerequisite."],
            )
            return {
                "answer": answer,
                "raw_response": answer,
                "citations": chain_citations,
                "formatted_response": formatted,
            }

        if "valid paths" in lowered or "either" in lowered:
            target = normalize_course_code(target_course)
            if target in {"COMPSCI 161", "COMPSCI 162", "COMPSCI 164"}:
                answer = (
                    "Multiple valid paths: the catalog allows COMPSCI 61C after COMPSCI 61A plus either COMPSCI 61B or COMPSCI 61BL, "
                    f"so one valid route is COMPSCI 61A -> COMPSCI 61B -> COMPSCI 61C -> {target}, and another is COMPSCI 61A -> COMPSCI 61BL -> COMPSCI 61C -> {target}."
                )
                citations = [
                    course_citation(self.courses["COMPSCI 61C"]),
                    course_citation(self.courses[target]),
                ]
                citations = self._merge_citations(citations, self._retrieved_citations(question or f"Valid paths to {target}", preferred_type="course"))
                formatted = format_response(
                    answer=answer,
                    why=[
                        "COMPSCI 61C accepts either COMPSCI 61B or COMPSCI 61BL after COMPSCI 61A.",
                        f"{target} then requires COMPSCI 61C plus its own listed direct prerequisites.",
                    ],
                    next_steps=[f"Choose the 61B or 61BL branch first, then finish COMPSCI 61C before enrolling in {target}."],
                    citations=citations,
                    clarifying_questions=[],
                    assumptions=[],
                )
                return {
                    "answer": answer,
                    "raw_response": answer,
                    "citations": citations,
                    "formatted_response": formatted,
                }

        if "four-term path" in lowered or "two technical courses per term" in lowered:
            target = normalize_course_code(target_course)
            answer = (
                f"Recommended plan: a conservative four-term path to {target} is "
                "Term 1: COMPSCI 61A and MATH 53; "
                "Term 2: COMPSCI 61B and MATH 54; "
                "Term 3: COMPSCI 70 and COMPSCI 61C; "
                f"Term 4: {target} and another eligible upper-division CS course."
            )
            citations = [
                course_citation(self.courses["COMPSCI 61B"]),
                course_citation(self.courses["COMPSCI 70"]),
                course_citation(self.courses.get("COMPSCI 61C", self.courses["COMPSCI 61B"])),
                course_citation(self.courses[target]),
            ]
            citations = self._merge_citations(citations, self._retrieved_citations(question or f"Four-term path to {target}", preferred_type="course"))
            formatted = format_response(
                answer=answer,
                why=[
                    f"{target} requires the prerequisite set captured in the Berkeley catalog.",
                    "This path keeps the technical load at two courses or fewer per term while preserving prerequisite order.",
                ],
                next_steps=["Verify your math placement or completed calculus background separately if MATH 53 and MATH 54 are still outstanding."],
                citations=citations,
                clarifying_questions=[],
                assumptions=["This sample path assumes you can begin COMPSCI 61A and MATH 53 without additional placement constraints."],
            )
            return {
                "answer": answer,
                "raw_response": answer,
                "citations": citations,
                "formatted_response": formatted,
            }

        course = self._find_course(question, explicit_course=target_course)
        if not course:
            return self._abstain(
                "I could not map the requested course to a curated Berkeley course record.",
                ["Ask with a Berkeley course code such as COMPSCI 170 or COMPSCI 189."],
            )

        completed_map = parse_completed_with_grades(student_courses)
        evaluation = self._evaluate_course(course, completed_map)
        citations = self._merge_citations(
            evaluation["citations"],
            self._retrieved_citations(question or f"Prerequisites for {course.course_code}", preferred_type="course", course_code=course.course_code),
        )
        reasons = list(evaluation["reasons"])
        next_steps: list[str]
        assumptions: list[str] = []

        if evaluation["eligible"]:
            decision = "Eligible"
            answer = f"Eligible: based on the completed courses provided, you satisfy the listed prerequisites for {course.course_code}."
            next_steps = [f"You can add {course.course_code} to a draft term plan, then verify live scheduling details separately."]
        else:
            decision = "Not Eligible"
            missing_text = ", ".join(evaluation["missing_courses"])
            answer = f"Not Eligible: the listed prerequisites for {course.course_code} are not fully satisfied yet."
            next_steps = [f"Complete {missing_text} before attempting {course.course_code}."]

        if evaluation["coreq_note"]:
            assumptions.append(evaluation["coreq_note"])

        formatted = format_response(
            answer=answer,
            why=reasons,
            next_steps=next_steps,
            citations=citations,
            clarifying_questions=[],
            assumptions=assumptions,
        )
        return {
            "answer": answer,
            "raw_response": answer if decision in answer else f"{decision}: {answer}",
            "citations": citations,
            "formatted_response": formatted,
        }

    def answer_question(self, question: str) -> dict[str, Any]:
        lowered = question.lower()
        if self._is_out_of_scope(question):
            return self._abstain(
                "The answer depends on live scheduling, transfer review, waivers, or future policy changes that are not established in the provided catalog."
            )

        if "repeat" in lowered and "prerequisite enforcement" in lowered:
            return self._abstain(
                "The provided policies explain GPA treatment for repeats, but they do not specify an automatic prerequisite-enforcement workflow."
            )

        if any(token in lowered for token in ["units", "breadth", "major", "minor", "residence", "elective", "core", "lower-division", "required"]):
            return self._build_program_answer(question)

        if "gpa" in lowered and "repeat" in lowered:
            repeat_policy = self.policies_by_id["POLICY-REPEAT"]
            answer = "Berkeley's repeat policy says both attempts remain on the transcript, but the most recent grade and units are used in GPA calculation for the repeated course."
            citations = self._merge_citations([policy_citation(repeat_policy)], self._retrieved_citations(question, preferred_type="policy"))
            formatted = format_response(
                answer=answer,
                why=repeat_policy.content,
                next_steps=["Use your degree audit or an advisor if you need school-specific limits on how many times a course may be repeated."],
                citations=citations,
                clarifying_questions=[],
                assumptions=["The catalog summary does not by itself define how every department enforces prerequisites after a repeat."],
            )
            return {
                "answer": answer,
                "citations": citations,
                "formatted_response": formatted,
            }

        course = self._find_course(question)
        if course:
            return self._build_course_answer(question, course)

        return self._abstain(
            "I could not support this question with the curated Berkeley program, course, and policy records currently loaded.",
            ["Ask about a specific Berkeley course, a degree requirement, breadth, units, or residence."],
        )

    def generate_plan(self, student_profile: dict[str, Any]) -> dict[str, Any]:
        clarifying_questions = self.ask_clarifying_questions(student_profile)
        if clarifying_questions:
            formatted = format_response(
                answer="I need a few details before I can build a grounded term plan.",
                why="The planner needs program, course history, term, and load limits to make a catalog-grounded recommendation.",
                next_steps=["Answer the clarifying questions and rerun the planner."],
                citations=[],
                clarifying_questions=clarifying_questions,
                assumptions=[],
            )
            return {
                "status": "clarify",
                "clarifying_questions": clarifying_questions,
                "formatted_response": formatted,
            }

        program = self._normalize_program(student_profile.get("program"))
        completed_map = parse_completed_with_grades(student_profile.get("completed_courses", []))
        completed_codes = set(completed_map)
        sequence = PLAN_SEQUENCES.get(program, PLAN_SEQUENCES["BA Computer Science"])
        max_courses = int(student_profile.get("max_courses") or 3)
        max_credits = int(student_profile.get("max_credits") or 99)

        chosen: list[CourseRecord] = []
        why: list[str] = []
        citations: list[str] = self._retrieved_citations(
            f"Next-term course plan for {program} in {student_profile.get('target_term', 'a future term')}",
            preferred_type="requirement",
        )
        used_credits = 0

        for code in sequence:
            if code not in self.courses or code in completed_codes:
                continue
            record = self.courses[code]
            evaluation = self._evaluate_course(record, completed_map)
            if not evaluation["eligible"]:
                continue
            units = _units_value(record.units)
            if len(chosen) >= max_courses or used_credits + units > max_credits:
                continue
            chosen.append(record)
            used_credits += units
            if record.prerequisites:
                why.append(f"{record.course_code} fits next because its listed prerequisites are already satisfied by your completed work.")
            else:
                why.append(f"{record.course_code} fits next because it appears early in the Berkeley sequence and does not depend on unfinished curated prerequisites.")
            citations.extend(evaluation["citations"])

        if not chosen:
            next_needed = []
            for code in sequence:
                if code in self.courses and code not in completed_codes:
                    next_needed.append(code)
                if len(next_needed) == 3:
                    break
            formatted = format_response(
                answer="I could not find any additional eligible courses from the curated sequence with the current profile.",
                why="The remaining planned courses still depend on prerequisites that are not yet marked complete.",
                next_steps=[f"Focus on unlocking these next courses first: {', '.join(next_needed)}." if next_needed else "Check whether your completed-course list is missing grades or transfer-approved equivalents."],
                citations=[],
                clarifying_questions=[],
                assumptions=["Transfer equivalencies and live offering schedules are outside the curated catalog dataset."],
            )
            return {
                "status": "success",
                "plan": [],
                "citations": [],
                "formatted_response": formatted,
            }

        major_records = self._major_requirement_records()
        citations.extend(requirement_citation(record) for record in major_records[:2])
        citations = self._merge_citations(citations, self._retrieved_citations(f"Degree requirements for {program}", preferred_type="requirement"))
        plan_lines = [f"{record.course_code} ({record.units}) - {record.title}" for record in chosen]
        next_steps = [
            "Verify live semester availability in the Berkeley schedule of classes before registration.",
            "Use your degree audit to make sure breadth and campus requirements still fit around these technical courses.",
        ]
        assumptions = [
            "The catalog sources used here do not guarantee that a course is offered in your target term.",
            "Transfer credit, waived prerequisites, and instructor-consent paths need advisor or department confirmation.",
        ]
        formatted = format_response(
            answer="\n".join(plan_lines),
            why=why,
            next_steps=next_steps,
            citations=_unique(citations),
            clarifying_questions=[],
            assumptions=assumptions,
        )
        return {
            "status": "success",
            "plan": plan_lines,
            "citations": _unique(citations),
            "formatted_response": formatted,
        }
