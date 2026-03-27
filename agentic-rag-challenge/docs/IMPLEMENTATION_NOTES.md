# Implementation Notes

## Chunking strategy

- Courses: 1000 tokens, 150 overlap
- Requirements: 1200 tokens, 200 overlap
- Policies: 500 tokens, 50 overlap

## Retrieval configuration

- Vector store: FAISS
- Retriever top-k: 5
- Embeddings: `all-MiniLM-L6-v2`

## Citation format

```text
[C1] [Source: URL, Section, accessed YYYY-MM-DD]
```

## Safe abstention cases

- future semester availability
- instructor assignments
- waitlist / seat counts
- specific transfer equivalencies
- future catalog changes

## Known limitations

- Automated evaluation is a proxy and should be supplemented with manual review.
- Course planning quality depends on the completeness of curated JSONL data.
- Real prerequisite nuance may still require advisor review.
