# Architecture

## Recommended stack

- Primary runtime: retrieval-augmented Python orchestration over curated Berkeley JSONL records
- Retrieval framework: LangChain-style document + retriever pipeline
- Vector store: FAISS
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Demo: Streamlit

## Pipeline

1. `src/ingestion.py`
   - loads curated JSONL files from `data/processed/`
   - turns courses, requirements, and policies into LangChain `Document` objects
2. `src/chunking.py`
   - applies type-aware chunking:
     - courses: `1000 / 150`
     - requirements: `1200 / 200`
     - policies: `500 / 50`
3. `src/embeddings.py`
   - creates and persists a local FAISS index under `faiss_catalog_index/`
4. `src/retriever.py`
   - exposes top-`k=5` retrieval over the FAISS index
5. `src/chains.py`
   - intake chain
   - retrieval QA chain
   - eligibility chain
   - plan generation chain
   - verifier chain
6. `src/orchestration.py`
   - loads Berkeley processed records
   - loads the FAISS retriever when index artifacts are present
   - performs retrieval-augmented prerequisite checks, chain tracing, planning, and abstention
   - asks clarifying questions when inputs are incomplete
   - formats all outputs into the required assessment sections
7. `evaluation/eval.py`
   - runs 25 queries
   - computes proxy metrics for citations, prerequisite accuracy, chain reasoning, abstention, and format compliance

## Retrieval and grounding rules

- Use only catalog-backed evidence from the processed Berkeley records and retrieved FAISS chunks when generating answers.
- Return source-backed citations for all factual claims.
- If the answer depends on availability, instructor assignment, transfer equivalency, or future policy changes, abstain and direct the student to the correct official source.

## Data model

### Course record

```json
{
  "course_code": "COMPSCI 161",
  "title": "Computer Security",
  "units": "3",
  "prerequisites": ["COMPSCI 61B or COMPSCI 61BL", "COMPSCI 70"],
  "co_requisites": [],
  "description": "...",
  "notes": "",
  "source_url": "...",
  "source_type": "course",
  "catalog_year": "2024-2025",
  "accessed_date": "2025-03-27"
}
```

### Requirement record

```json
{
  "requirement_id": "berkeley-ba-cs-core",
  "program": "BA Computer Science",
  "section": "Core Requirements",
  "content": "...",
  "source_url": "...",
  "source_type": "requirement",
  "catalog_year": "2024-2025",
  "accessed_date": "2025-03-27"
}
```

### Policy record

```json
{
  "policy_id": "berkeley-repeat-policy",
  "title": "Course Repeat Policy",
  "category": "repeat",
  "content": "...",
  "source_url": "...",
  "source_type": "policy",
  "catalog_year": "2024-2025",
  "accessed_date": "2025-03-27"
}
```
