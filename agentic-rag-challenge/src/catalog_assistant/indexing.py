from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from catalog_assistant.models import ChunkRecord
from catalog_assistant.utils import artifacts_dir


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_embedder() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def index_paths() -> tuple[Path, Path]:
    base = artifacts_dir()
    return base / "catalog.index", base / "catalog_chunks.jsonl"


def build_index(chunks: list[ChunkRecord]) -> tuple[Path, Path]:
    model = load_embedder()
    vectors = model.encode([chunk.text for chunk in chunks], normalize_embeddings=True)
    matrix = np.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    index_path, chunk_path = index_paths()
    faiss.write_index(index, str(index_path))
    with chunk_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.model_dump()))
            handle.write("\n")
    return index_path, chunk_path


def load_index() -> tuple[faiss.Index, list[ChunkRecord]]:
    index_path, chunk_path = index_paths()
    index = faiss.read_index(str(index_path))
    chunks = [
        ChunkRecord.model_validate(json.loads(line))
        for line in chunk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return index, chunks

