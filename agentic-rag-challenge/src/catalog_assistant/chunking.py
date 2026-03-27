from __future__ import annotations

from catalog_assistant.models import ChunkRecord, RawDocument


def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def chunk_documents(docs: list[RawDocument], chunk_size: int = 900, overlap: int = 150) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for doc in docs:
        parts = split_text(doc.text, chunk_size=chunk_size, overlap=overlap)
        for index, text in enumerate(parts, start=1):
            heading = doc.headings[min(index - 1, len(doc.headings) - 1)] if doc.headings else doc.title
            chunks.append(
                ChunkRecord(
                    chunk_id=f"{doc.source_id}#chunk-{index}",
                    source_id=doc.source_id,
                    category=doc.category,
                    url=doc.url,
                    title=doc.title,
                    heading=heading,
                    text=text,
                )
            )
    return chunks

