
print("[1] Starting manual test for document ingestion...\n")
from pathlib import Path
from app.application.services.chunker import V1_Chunker
from app.application.use_cases import IngestDocument
from app.domain.entities import Organization
from app.infra.db.engine import SessionLocal
from app.infra.db.implementations import PostgreSQL_ChunkRepository, PostgreSQL_DocumentRepository, PostgreSQL_OrganizationRepository
from app.infra.embedder.implementations import SentenceTransformerEmbedder
from app.infra.parser.implementations import V1_PDFParser
from app.infra.storage.implementations import Local_DocumentStorage

print("[2] Imported necessary modules and classes.")

def main() -> None:
    print("Starting manual test for document ingestion...\n")
    db = SessionLocal()
    print("[OK] Database session created.")
    
    try:
        # 1. build repos
        org_repo = PostgreSQL_OrganizationRepository(db_session=db)
        doc_repo = PostgreSQL_DocumentRepository(db_session=db)
        chunk_repo = PostgreSQL_ChunkRepository(db_session=db)
        
        # 2. Build infra services
        storage = Local_DocumentStorage(base_path="./data/storage")  
        parser = V1_PDFParser()
        chunker = V1_Chunker()
        embedder = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")
        
        # 3. Ensure test organization exists
        org_name = "Test Organization"
        org = org_repo.get_by_name(org_name)
        
        if org is None:
            org = Organization(name=org_name) 
            org_repo.add(org)
            print(f"Created test organization with id: {org.id}")
        else:
            print(f"Test organization already exists with id: {org.id}")
        
        # 4. Load PDF from disk:
        file_path = Path("./samples/pdf-sample-test.pdf")
        if not file_path.exists():
            raise FileNotFoundError(f"Test PDF not found at path: {file_path}")
        
        file_content = file_path.read_bytes()
        
        # 5. Build use case
        use_case = IngestDocument(
            org_repo=org_repo,
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            parser=parser,
            chunker=chunker,
            embedder=embedder
        )
        
        #6 . Exceute
        result = use_case.execute(
            organization_id=org.id,
            filename=file_path.name,
            file_content=file_content
        )
        
        # 7. Commit
        db.commit()
        
        print("\n[OK] INGEST COMPLETED")
        print(f"organization_id: {result.organization_id}")
        print(f"document_id:     {result.document_id}")
        print(f"chunks_created:  {result.chunks_created}")
        print(f"document_hash:   {result.document_hash}")
        
        # 8. Optional quick DB verification
        stored_chunks = chunk_repo.get_by_document(
            organization_id=org.id,
            document_id=result.document_id,
        )

        print(f"\n[OK] Chunks fetched back from DB: {len(stored_chunks)}")

        if stored_chunks:
            first_chunk = stored_chunks[0]
            print("\nFirst chunk preview:")
            print(f"chunk_index:   {first_chunk.chunk_index}")
            print(f"token_count:   {first_chunk.token_count}")
            print(f"content[:120]: {first_chunk.content[:120]!r}")
            print(f"embedding_len: {len(first_chunk.embedding)}")
            print(f"embedding[:5]: {first_chunk.embedding[:5]}")
        
    except Exception:
        db.rollback()
        print("\n[ERROR] An error occurred during the ingest process. Rolled back the transaction.")
        raise
    finally:
        db.close()
        print("\n[OK] Database session closed.")
    
if __name__ == "__main__":
    main()
        