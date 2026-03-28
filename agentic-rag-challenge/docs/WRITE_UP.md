# Short Write-Up

## Chosen catalog

This implementation is structured around UC Berkeley public catalog and policy sources, following the planning documents provided for the project.

## Architecture

The implemented assistant uses curated Berkeley JSONL records as the primary source of truth and a retrieval-augmented orchestration layer for prerequisite checks, chain tracing, planning, citation formatting, clarifying questions, and safe abstention. When the FAISS index is built, the runtime loads retrieved catalog chunks as evidence; if the index is absent, the same processed records are used directly as a development fallback.

## Retrieval and chunking

Course records are kept relatively self-contained, requirement blocks are grouped by program section, and policies are split into smaller atomic chunks. That supports the FAISS pipeline and keeps source metadata stable whether the assistant is citing retrieved chunks or the underlying processed records.

## Prompting / stages

The repo includes LangChain prompt templates for intake, retrieval QA, eligibility reasoning, plan generation, and verification in `src/chains.py`. The implemented runtime mirrors those stages in a lighter deterministic form: intake checks for missing student context, retrieval pulls supporting catalog chunks when the FAISS index is available, prerequisite / planning logic produces the decision, and the formatter attaches citation-linked output in the required response structure.

## Evaluation

The evaluation harness uses 25 Berkeley-grounded test queries across simple prerequisite checks, prerequisite chains, program requirements, and safe abstention. The current local run reports 96.0% citation coverage, 100% eligibility accuracy, 100% chain accuracy, 100% program accuracy, 100% abstention accuracy, 100% format compliance, and a 99.2 weighted score.

## Dataset

The curated dataset includes 35 source-backed documents: 22 course descriptions, 7 program-requirement records, and 6 academic policy records. The inventory with URL, access date, section, and coverage note is stored in `data/sources.json`.

## Failure modes

The main failure modes are incomplete catalog capture for edge-case exceptions, co-requisite rules that depend on student status or instructor approval, and the gap between response-level citation coverage and fully formal claim verification. Another practical limitation is that full FAISS-backed RAG behavior depends on local dependency installation and index construction before runtime.

## Next improvements

- add claim-level citation verification instead of response-level citation coverage
- expand the curated Berkeley dataset with more explicit grade-threshold and co-requisite variants
- add a verifier stage for contradictions between deterministic logic and optional retrieval outputs
