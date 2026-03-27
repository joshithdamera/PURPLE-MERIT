from __future__ import annotations

from chunking import SmartChunker
from embeddings import EmbeddingManager
from ingestion import CatalogLoader


def main() -> None:
    print("=" * 60)
    print("CATALOG INDEXING PIPELINE")
    print("=" * 60)

    print("\n[1/4] Loading catalog documents...")
    loader = CatalogLoader()
    documents = loader.load_all()
    print(f"Loaded {len(documents)} documents")
    print(f"  - Courses: {len([d for d in documents if d.metadata['type'] == 'course'])}")
    print(f"  - Requirements: {len([d for d in documents if d.metadata['type'] == 'requirement'])}")
    print(f"  - Policies: {len([d for d in documents if d.metadata['type'] == 'policy'])}")

    print("\n[2/4] Chunking documents...")
    chunker = SmartChunker()
    chunks = chunker.chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")

    print("\n[3/4] Generating embeddings and saving FAISS index...")
    manager = EmbeddingManager()
    vector_store = manager.create_vector_store(chunks)
    print("Embeddings complete")

    print("\n[4/4] Testing retrieval...")
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    results = retriever.get_relevant_documents("What are the prerequisites for COMPSCI 161?")
    print(f"Test query returned {len(results)} results")
    for index, result in enumerate(results[:3], start=1):
        code = result.metadata.get("course_code", result.metadata.get("requirement_id", "Unknown"))
        preview = result.page_content[:120].replace("\n", " ")
        print(f"  Result {index}: {code}")
        print(f"  Preview: {preview}...")

    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

