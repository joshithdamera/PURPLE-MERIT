from __future__ import annotations

import re

from catalog_assistant.models import QueryAnswer
from catalog_assistant.retrieval import Retriever
from catalog_assistant.utils import extract_course_codes


ABSTAIN_HINTS = ("semester", "fall", "spring", "summer", "professor", "instructor approval process", "seat availability")


def _extractive_summary(question: str, chunks: list[tuple[object, float]]) -> tuple[str, list[str]]:
    query_terms = {term for term in re.findall(r"[a-zA-Z]{4,}", question.lower())}
    selected_sentences: list[str] = []
    citations: list[str] = []
    for chunk, _score in chunks:
        sentences = re.split(r"(?<=[.!?])\s+", chunk.text)
        for sentence in sentences:
            words = set(re.findall(r"[a-zA-Z]{4,}", sentence.lower()))
            if query_terms & words or set(extract_course_codes(question)) & set(extract_course_codes(sentence)):
                cleaned = sentence.strip()
                if cleaned and cleaned not in selected_sentences:
                    selected_sentences.append(cleaned)
                    citations.append(f"{chunk.url} ({chunk.heading or chunk.chunk_id})")
            if len(selected_sentences) >= 3:
                break
        if len(selected_sentences) >= 3:
            break
    if not selected_sentences and chunks:
        chunk = chunks[0][0]
        selected_sentences.append(chunk.text[:280].strip())
        citations.append(f"{chunk.url} ({chunk.heading or chunk.chunk_id})")
    return " ".join(selected_sentences), citations


def answer_catalog_question(question: str, retriever: Retriever | None = None) -> QueryAnswer:
    retriever = retriever or Retriever()
    results = retriever.search(question, k=6)
    if not results:
        return QueryAnswer(
            answer="I don't have that information in the provided catalog/policies.",
            why="No relevant indexed catalog chunks were retrieved.",
            citations=[],
            clarifying_questions=[],
            assumptions=["Check the department page, schedule of classes, or an advisor for information outside the indexed catalog."],
        )

    top_score = results[0][1]
    lowered = question.lower()
    if top_score < 0.28 or any(hint in lowered for hint in ABSTAIN_HINTS):
        return QueryAnswer(
            answer="I don't have that information in the provided catalog/policies.",
            why="The indexed catalog supports requirements and policies, but not this operational detail.",
            citations=[],
            clarifying_questions=[],
            assumptions=["Next step: check the schedule of classes, department site, or contact an advisor."],
        )

    answer, citations = _extractive_summary(question, results)
    if not citations:
        return QueryAnswer(
            answer="I don't have that information in the provided catalog/policies.",
            why="Relevant evidence could not be cited from the indexed chunks.",
            citations=[],
            clarifying_questions=[],
            assumptions=["Check the official catalog page directly or verify with the program office."],
        )
    return QueryAnswer(
        answer=answer,
        why="This answer is limited to retrieved catalog text that overlaps with the question.",
        citations=sorted(set(citations)),
        clarifying_questions=[],
        assumptions=["If your catalog year differs, re-run with the correct year because requirements may change."],
    )

