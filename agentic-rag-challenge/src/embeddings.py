from __future__ import annotations

import os
from pathlib import Path

from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from utils import FAISS_DIR


class EmbeddingManager:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)

    def create_vector_store(self, documents: list[Document], index_path: str | Path = FAISS_DIR) -> FAISS:
        vector_store = FAISS.from_documents(documents, self.embeddings)
        vector_store.save_local(str(index_path))
        return vector_store

    def load_vector_store(self, index_path: str | Path = FAISS_DIR) -> FAISS:
        try:
            return FAISS.load_local(str(index_path), self.embeddings, allow_dangerous_deserialization=True)
        except TypeError:
            return FAISS.load_local(str(index_path), self.embeddings)
