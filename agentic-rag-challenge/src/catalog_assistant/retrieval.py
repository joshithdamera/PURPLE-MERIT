from __future__ import annotations

import numpy as np

from catalog_assistant.indexing import load_embedder, load_index
from catalog_assistant.models import ChunkRecord


class Retriever:
    def __init__(self) -> None:
        self.embedder = load_embedder()
        self.index, self.chunks = load_index()

    def search(self, query: str, k: int = 6) -> list[tuple[ChunkRecord, float]]:
        vector = self.embedder.encode([query], normalize_embeddings=True)
        scores, indices = self.index.search(np.asarray(vector, dtype="float32"), k)
        results: list[tuple[ChunkRecord, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:
                continue
            results.append((self.chunks[int(idx)], float(score)))
        return results

