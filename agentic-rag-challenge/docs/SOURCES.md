# Sources

## Institution

- University of California, Berkeley
- Catalog years represented: `2024-2025` and `2025-2026`
- Curation strategy: manually curated public catalog pages plus official Berkeley program and policy pages

## Source types

- 20 curated course descriptions
- 7 program / requirement records
- 6 academic policy records
- 33 total curated source-backed documents in the processed dataset

## Machine-readable inventory

The structured inventory is stored in `data/sources.json`. Each entry includes:

- source URL
- access date
- covered course or section
- short note on what the source record covers

## Included source families

- Berkeley course catalog pages for COMPSCI and MATH
- Berkeley Academic Guide program pages for the CS BA and EECS BS
- Berkeley undergraduate catalog policy pages for units, grades, repetition, and campus requirements

## Curation notes

- Every processed record stores its source URL and access date.
- Citations are emitted as `URL + section/course identifier + access date`.
- Degree requirements and academic policies are stored separately from course descriptions so planning logic can cite them independently.
- The inventory counts processed course descriptions and curated requirement/policy records as the dataset documents used by the assistant and evaluator.
