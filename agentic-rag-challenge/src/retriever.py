from __future__ import annotations

from langchain.schema import Document

from embeddings import EmbeddingManager


class CatalogRetriever:
    def __init__(self, index_path: str = "faiss_catalog_index", k: int = 5) -> None:
        manager = EmbeddingManager()
        self.vector_store = manager.load_vector_store(index_path)
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": k})

    def get_relevant_documents(self, query: str) -> list[Document]:
        return self.retriever.get_relevant_documents(query)

    def get_course_documents(self, course_code: str) -> list[Document]:
        return self.get_relevant_documents(f"Course prerequisites and description for {course_code}")

    def get_program_documents(self, program_name: str) -> list[Document]:
        return self.get_relevant_documents(f"Degree requirements and policies for {program_name}")

