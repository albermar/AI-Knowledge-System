from app.infra.db.engine import SessionLocal
from app.infra.db.implementations import PostgreSQL_OrganizationRepository, PostgreSQL_ChunkRepository
from app.infra.embedder.implementations import SentenceTransformerEmbedder
def main() -> None:
    db = SessionLocal()

    try:
        org_repo = PostgreSQL_OrganizationRepository(db_session=db)
        chunk_repo = PostgreSQL_ChunkRepository(db_session=db)
        embedder = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")

        org_name = "Test Organization"
        org = org_repo.get_by_name(org_name)
        if org is None:
            raise ValueError("Test organization not found.")

        question = "What does the document say about Lorem ipsum?"
        embedded_question = embedder.embed_text(question)

        results = chunk_repo.vector_search(
            organization_id=org.id,
            embedded_question=embedded_question,
            top_k=5,
        )

        print("\n[OK] VECTOR SEARCH COMPLETED")
        print(f"question: {question}")
        print(f"results: {len(results)}")

        for i, chunk in enumerate(results, start=1):
            print(f"\n--- Result {i} ---")
            print(f"chunk_id: {chunk.chunk_id}")
            print(f"chunk_index: {chunk.chunk_index}")
            print(f"similarity_score: {chunk.similarity_score}")
            print(f"content[:300]: {chunk.content[:300]!r}")

    finally:
        db.close()


if __name__ == "__main__":
    main()