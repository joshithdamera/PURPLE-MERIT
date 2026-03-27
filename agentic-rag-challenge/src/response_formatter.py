from __future__ import annotations


def _unique(items: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in items:
        if item and item not in ordered:
            ordered.append(item)
    return ordered


def _label_map(citations: list[str]) -> tuple[dict[str, str], list[str]]:
    ordered = _unique(citations)
    citation_to_label = {citation: f"C{index}" for index, citation in enumerate(ordered, start=1)}
    rendered = [f"[{citation_to_label[citation]}] {citation}" for citation in ordered]
    return citation_to_label, rendered


def _apply_labels(text: str, citation_refs: list[str], citation_to_label: dict[str, str]) -> str:
    labels = [citation_to_label[citation] for citation in citation_refs if citation in citation_to_label]
    labels = _unique(labels)
    if not labels:
        return text
    return f"{text} [{', '.join(labels)}]"


def format_response(
    answer: str,
    why: list[str] | str,
    next_steps: list[str] | str | None = None,
    citations: list[str] | None = None,
    clarifying_questions: list[str] | None = None,
    assumptions: list[str] | None = None,
    answer_citations: list[str] | None = None,
    why_citations: list[list[str]] | None = None,
    next_step_citations: list[list[str]] | None = None,
    assumption_citations: list[list[str]] | None = None,
) -> str:
    why_items = why if isinstance(why, list) else [why]
    next_step_items = [] if next_steps is None else (next_steps if isinstance(next_steps, list) else [next_steps])
    citations = citations or []
    clarifying_questions = clarifying_questions or []
    assumptions = assumptions or []
    answer_citations = answer_citations or citations
    why_citations = why_citations or [citations for _ in why_items]
    next_step_citations = next_step_citations or [citations for _ in next_step_items]
    assumption_citations = assumption_citations or [citations for _ in assumptions]
    citation_to_label, rendered_citations = _label_map(citations)

    lines = ["Answer / Plan:", _apply_labels(answer, answer_citations, citation_to_label)]
    for item, item_citations in zip(next_step_items, next_step_citations):
        if item:
            lines.append(_apply_labels(f"Next step: {item}", item_citations, citation_to_label))

    lines.append("Why (requirements/prereqs satisfied):")
    why_count = 0
    for item, item_citations in zip(why_items, why_citations):
        if item:
            why_count += 1
            lines.append(f"- {_apply_labels(item, item_citations, citation_to_label)}")
    if why_count == 0:
        lines.append("- None")

    lines.append("Citations:")
    lines.extend(f"- {item}" for item in rendered_citations)
    if not rendered_citations:
        lines.append("- None")

    lines.append("Clarifying questions (if needed):")
    lines.extend(f"- {item}" for item in clarifying_questions)
    if not clarifying_questions:
        lines.append("- None")

    lines.append("Assumptions / Not in catalog:")
    assumption_count = 0
    for item, item_citations in zip(assumptions, assumption_citations):
        if item:
            assumption_count += 1
            lines.append(f"- {_apply_labels(item, item_citations, citation_to_label)}")
    if assumption_count == 0:
        lines.append("- None")

    return "\n".join(lines)
