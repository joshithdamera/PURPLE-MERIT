from __future__ import annotations

import json
from pathlib import Path

import typer

from catalog_assistant.assistant import CatalogAssistant
from catalog_assistant.chunking import chunk_documents
from catalog_assistant.evaluate import run_evaluation
from catalog_assistant.ingest import ingest_all
from catalog_assistant.indexing import build_index
from catalog_assistant.models import RawDocument, StudentCourse
from catalog_assistant.sources import load_sources
from catalog_assistant.utils import artifacts_dir, dump_json, load_json


app = typer.Typer(no_args_is_help=True)


def _docs_path() -> Path:
    return artifacts_dir() / "documents.json"


def _load_docs() -> list[RawDocument]:
    payload = load_json(_docs_path())
    return [RawDocument.model_validate(item) for item in payload]


def _parse_completed(entries: list[str]) -> list[StudentCourse]:
    completed: list[StudentCourse] = []
    for entry in entries:
        if ":" in entry:
            code, grade = entry.split(":", 1)
            completed.append(StudentCourse(course_code=code, grade=grade))
        else:
            completed.append(StudentCourse(course_code=entry))
    return completed


@app.command()
def build_catalog_index() -> None:
    """Fetch source pages, persist cleaned docs, and build a FAISS index."""
    sources = load_sources()
    docs = ingest_all(sources)
    dump_json(_docs_path(), [doc.model_dump() for doc in docs])
    chunks = chunk_documents(docs)
    index_path, chunk_path = build_index(chunks)
    typer.echo(f"Indexed {len(docs)} documents and {len(chunks)} chunks.")
    typer.echo(f"Index: {index_path}")
    typer.echo(f"Chunks: {chunk_path}")


@app.command()
def answer_prereq(
    target_course: str = typer.Option(..., "--target-course"),
    completed: list[str] = typer.Option(None, "--completed"),
) -> None:
    assistant = CatalogAssistant(_load_docs())
    result = assistant.answer_prereq(target_course, _parse_completed(completed or []))
    typer.echo("Answer / Plan:")
    typer.echo(f"{result.decision}: {result.reason}")
    typer.echo("Why (requirements/prereqs satisfied):")
    typer.echo(result.next_step)
    typer.echo("Citations:")
    for citation in result.citations:
        typer.echo(f"- {citation}")
    typer.echo("Clarifying questions (if needed):")
    typer.echo("- None" if result.decision != "Need more info" else "- Verify the course code and catalog year.")
    typer.echo("Assumptions / Not in catalog:")
    typer.echo("- Eligibility here is based only on indexed catalog prerequisite text.")


@app.command()
def plan_term(
    major: str = typer.Option(None, "--major"),
    catalog_year: str = typer.Option(None, "--catalog-year"),
    target_term: str = typer.Option("Fall", "--target-term"),
    max_credits: int = typer.Option(None, "--max-credits"),
    completed: list[str] = typer.Option(None, "--completed"),
) -> None:
    assistant = CatalogAssistant(_load_docs())
    result = assistant.plan_term(
        major=major,
        catalog_year=catalog_year,
        target_term=target_term,
        max_credits=max_credits,
        completed_courses=_parse_completed(completed or []),
    )
    typer.echo("Answer / Plan:")
    typer.echo(result.answer)
    typer.echo("Why (requirements/prereqs satisfied):")
    if result.courses:
        for course in result.courses:
            typer.echo(f"- {course.course_code}: {course.why}")
    else:
        typer.echo("- No courses proposed yet.")
    typer.echo("Citations:")
    for citation in result.citations:
        typer.echo(f"- {citation}")
    typer.echo("Clarifying questions (if needed):")
    for question in result.clarifying_questions or ["None"]:
        typer.echo(f"- {question}")
    typer.echo("Assumptions / Not in catalog:")
    for item in result.assumptions or ["None"]:
        typer.echo(f"- {item}")


@app.command()
def export_sources() -> None:
    payload = [item.model_dump() for item in load_sources()]
    typer.echo(json.dumps(payload, indent=2))


@app.command()
def answer_query(
    question: str = typer.Option(..., "--question"),
) -> None:
    assistant = CatalogAssistant(_load_docs())
    result = assistant.answer_question(question)
    typer.echo("Answer / Plan:")
    typer.echo(result.answer)
    typer.echo("Why (requirements/prereqs satisfied):")
    typer.echo(result.why)
    typer.echo("Citations:")
    for citation in result.citations or ["None"]:
        typer.echo(f"- {citation}")
    typer.echo("Clarifying questions (if needed):")
    for question_text in result.clarifying_questions or ["None"]:
        typer.echo(f"- {question_text}")
    typer.echo("Assumptions / Not in catalog:")
    for assumption in result.assumptions or ["None"]:
        typer.echo(f"- {assumption}")


@app.command()
def run_eval() -> None:
    report = run_evaluation()
    typer.echo(json.dumps(report["metrics"], indent=2))
