from __future__ import annotations

from typing import List

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


class SmartChunker:
    def __init__(self) -> None:
        self.course_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["PREREQUISITES:", "CO-REQUISITES:", "DESCRIPTION:", "\n\n", "\n"],
        )
        self.requirement_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["Required Core", "Electives", "Breadth", "\n\n", "\n"],
        )
        self.policy_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["Policy", "Rule", "\n\n", "\n"],
        )

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        chunked: list[Document] = []
        for doc in documents:
            doc_type = doc.metadata.get("type", "")
            if doc_type == "course":
                chunks = self.course_splitter.split_documents([doc])
            elif doc_type == "requirement":
                chunks = self.requirement_splitter.split_documents([doc])
            elif doc_type == "policy":
                chunks = self.policy_splitter.split_documents([doc])
            else:
                chunks = self.course_splitter.split_documents([doc])

            for index, chunk in enumerate(chunks):
                chunk.metadata.update(doc.metadata)
                base_id = doc.metadata.get("course_code") or doc.metadata.get("requirement_id") or doc.metadata.get("policy_id") or "doc"
                chunk.metadata["chunk_id"] = f"{base_id}_{index}"
            chunked.extend(chunks)
        return chunked

