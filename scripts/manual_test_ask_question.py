
print("[1] Starting manual test for ask question...\n")

from app.application.use_cases import AskQuestion


from app.application.services.prompt_builder import V1_PromptBuilder
from app.infra.retriever.implementations import V1_Retriever

from app.infra.db.engine import SessionLocal
from app.infra.db.implementations import (
    PostgreSQL_OrganizationRepository,
    PostgreSQL_QueryRepository,
    PostgreSQL_LLMUsageRepository,
    PostgreSQL_QueryChunkRepository,
    PostgreSQL_ChunkRepository,
)
from app.infra.embedder.implementations import SentenceTransformerEmbedder
from app.infra.llm.implementations import FakeLLMClient

print("[2] Imported necessary modules and classes.")


def main() -> None:
    print("Starting manual test for ask question...\n")
    db = SessionLocal()
    print("[OK] Database session created.")

    try:
        # 1. Build repositories
        org_repo = PostgreSQL_OrganizationRepository(db_session=db)
        query_repo = PostgreSQL_QueryRepository(db_session=db)
        llm_usage_repo = PostgreSQL_LLMUsageRepository(db_session=db)
        query_chunk_repo = PostgreSQL_QueryChunkRepository(db_session=db)
        chunk_repo = PostgreSQL_ChunkRepository(db_session=db)

        # 2. Build services
        embedder = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")
        retriever = V1_Retriever(chunk_repo=chunk_repo, embedder=embedder)
        prompt_builder = V1_PromptBuilder()
        llm_client = FakeLLMClient()

        # 3. Load organization
        org_name = "Test Organization"
        org = org_repo.get_by_name(org_name)

        if org is None:
            raise ValueError("Test organization not found. Run the ingest script first.")

        print(f"[OK] Using organization: {org.id}")

        # 4. Build use case
        use_case = AskQuestion(
            org_repo=org_repo,
            query_repo=query_repo,
            llm_usage_repo=llm_usage_repo,
            query_chunk_repo=query_chunk_repo,
            retriever=retriever,
            prompt_builder=prompt_builder,
            llm_client=llm_client,
        )

        # 5. Execute
        question = "What appears repeatedly in this document?"

        result = use_case.execute(
            organization_id=org.id,
            question=question,
        )

        # 6. Commit
        db.commit()

        print("\n[OK] ASK QUESTION COMPLETED")
        print(f"query_id:            {result.query_id}")
        print(f"question:            {result.question}")
        print(f"answer:              {result.answer}")
        print(f"model_name:          {result.model_name}")
        print(f"latency_ms:          {result.latency_ms}")
        print(f"prompt_tokens:       {result.prompt_tokens}")
        print(f"completion_tokens:   {result.completion_tokens}")
        print(f"total_tokens:        {result.total_tokens}")
        print(f"estimated_cost_usd:  {result.estimated_cost_usd}")

    except Exception:
        db.rollback()
        print("\n[ERROR] An error occurred during ask question. Rolled back the transaction.")
        raise
    finally:
        db.close()
        print("\n[OK] Database session closed.")


if __name__ == "__main__":
    main()