# Short Write-Up

## Chosen catalog

This implementation is structured around UC Berkeley public catalog and policy sources, following the planning documents provided for the project.

## Architecture

The implemented assistant uses curated Berkeley JSONL records as the primary source of truth and a retrieval-augmented orchestration layer for prerequisite checks, chain tracing, planning, citation formatting, clarifying questions, and safe abstention. When the FAISS index is built, the runtime loads retrieved catalog chunks as evidence; if the index is absent, the same processed records are used directly as a development fallback.

## Retrieval and chunking

Course records are kept relatively self-contained, requirement blocks are grouped by program section, and policies are split into smaller atomic chunks. That supports the FAISS pipeline and keeps source metadata stable whether the assistant is citing retrieved chunks or the underlying processed records.

## Evaluation

The evaluation harness uses 25 Berkeley-grounded test queries across simple prerequisite checks, prerequisite chains, program requirements, and safe abstention. The current local run reports 96.0% citation coverage, 100% eligibility accuracy, 100% chain accuracy, 100% program accuracy, 100% abstention accuracy, 100% format compliance, and a 99.2 weighted score.

## Dataset

The curated dataset includes 33 source-backed documents: 20 course descriptions, 7 program-requirement records, and 6 academic policy records. The inventory with URL, access date, section, and coverage note is stored in `data/sources.json`.

## Next improvements

- add claim-level citation verification instead of response-level citation coverage
- expand the curated Berkeley dataset with more explicit grade-threshold and co-requisite variants
- add a verifier stage for contradictions between deterministic logic and optional retrieval outputs
