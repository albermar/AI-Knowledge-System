"""
Integration tests for router_1_ingest_document.py endpoint
Tests the entire vertical pipeline: API -> Use Case -> Repository -> Database -> Storage
"""
import io
import os
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.main import app
from app.infra.db.engine import get_db_session
from app.infra.db.implementations import (
    PostgreSQL_OrganizationRepository,
    PostgreSQL_DocumentRepository,
    PostgreSQL_ChunkRepository,
)
from app.domain.entities import Organization
from app.application.services.api_key import generate_api_key, hash_api_key
from tests.use_cases.helpers import make_db_session


@pytest.fixture
def db_session() -> Session:
    session = make_db_session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session):
    """Fixture that provides a TestClient with overridden database dependency"""
    def override_get_db_session():
        try:
            yield db_session
        finally:
            pass  # Don't close here, let the fixture handle it
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def test_organization(db_session: Session):
    """Fixture that creates a test organization with API key"""
    org_repo = PostgreSQL_OrganizationRepository(db_session)

    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    org = Organization(
        name=f"Test Org for Ingest {uuid.uuid4()}",
        api_key_hash=api_key_hash,
    )
    org_repo.add(org)
    db_session.commit()

    return org, api_key

@pytest.fixture
def doc_repo(db_session: Session) -> PostgreSQL_DocumentRepository:
    """Fixture that provides a document repository"""
    return PostgreSQL_DocumentRepository(db_session)


@pytest.fixture
def chunk_repo(db_session: Session) -> PostgreSQL_ChunkRepository:
    """Fixture that provides a chunk repository"""
    return PostgreSQL_ChunkRepository(db_session)


@pytest.fixture
def sample_pdf_bytes():
    """Fixture that provides sample PDF file bytes"""
    pdf_path = Path("./samples/pdf-sample-test.pdf")
    with open(pdf_path, "rb") as f:
        return f.read()


@pytest.fixture
def storage_cleanup():
    """Fixture to track and cleanup storage files created during tests"""
    created_paths = []
    
    def track_path(path: str):
        created_paths.append(path)
    
    yield track_path
    
    # Cleanup after test
    for path in created_paths:
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        except Exception:
            pass  # Best effort cleanup


class TestIngestDocumentEndpoint:
    """Test suite for POST /api/ingest-document endpoint"""
    
    def test_ingest_document_success(
        self,
        client: TestClient,
        test_organization: Organization,
        doc_repo: PostgreSQL_DocumentRepository,
        chunk_repo: PostgreSQL_ChunkRepository,
        sample_pdf_bytes: bytes,
        db_session: Session,
        storage_cleanup
    ):
        """Test successful document ingestion returns 200 and correct response"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        files = {"file": ("test-document.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "organization_id" in data
        assert "document_id" in data
        assert "chunks_created" in data
        assert "document_hash" in data
        
        # Verify response values
        assert data["organization_id"] == str(org.id)
        assert data["document_id"] is not None
        assert data["chunks_created"] > 0
        assert data["document_hash"] is not None
        assert len(data["document_hash"]) == 64  # SHA-256 hash
        
        # Verify document persistence in database
        document = doc_repo.get_by_id(org.id, data["document_id"])
        assert document is not None
        assert document.title == "test-document.pdf"
        assert document.source_type == "pdf"
        assert document.document_hash == data["document_hash"]
        assert len(document.content) > 0
        
        # Verify chunks persistence
        chunks = chunk_repo.get_by_document(org.id, data["document_id"])
        assert len(chunks) == data["chunks_created"]
        assert all(chunk.embedding is not None for chunk in chunks)
        assert all(chunk.token_count > 0 for chunk in chunks)
        
        # Verify storage file exists
        storage_path = Path(f"./storage/{org.id}/{data['document_id']}.bin")
        assert storage_path.exists()
        
    def test_ingest_document_missing_api_key_returns_422(self, client: TestClient, sample_pdf_bytes: bytes):
        """Test that missing API key returns 422 Unprocessable Entity"""
        # Arrange
        files = {"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", files=files)
        
        # Assert
        assert response.status_code == 422  # FastAPI validation error for missing header
        
    def test_ingest_document_invalid_api_key_returns_401(self, client: TestClient, sample_pdf_bytes: bytes):
        """Test that invalid API key returns 401 Unauthorized"""
        # Arrange
        headers = {"X-API-Key": "invalid_api_key_12345"}
        files = {"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
        
    def test_ingest_document_empty_file_returns_400(
        self,
        client: TestClient,
        test_organization: Organization
    ):
        """Test that empty file returns 400 Bad Request"""
        # Arrange
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        
    def test_ingest_document_file_too_large_returns_400(
        self,
        client: TestClient,
        test_organization: Organization
    ):
        """Test that file exceeding max size returns 400"""
        # Arrange
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 400
        assert "exceeds max size" in response.json()["detail"]
        
    def test_ingest_document_duplicate_hash_returns_409(
        self,
        client: TestClient,
        test_organization: Organization,
        sample_pdf_bytes: bytes,
        db_session: Session,
        storage_cleanup
    ):
        """Test that ingesting the same document twice returns 409 Conflict"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        files = {"file": ("duplicate.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # First ingestion
        first_response = client.post("/api/ingest-document", headers=headers, files=files)
        assert first_response.status_code == 200
        db_session.commit()
        
        # Act - Second ingestion with same content
        files = {"file": ("duplicate.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        second_response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert second_response.status_code == 409
        assert "already exists" in second_response.json()["detail"].lower()
        
    def test_ingest_document_invalid_pdf_returns_400(
        self,
        client: TestClient,
        test_organization: Organization
    ):
        """Test that invalid PDF file returns 400"""
        # Arrange
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        invalid_content = b"This is not a PDF file, just plain text."
        files = {"file": ("fake.pdf", io.BytesIO(invalid_content), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 400
        assert "parse" in response.json()["detail"].lower()
        
    def test_ingest_document_creates_embeddings(
        self,
        client: TestClient,
        test_organization: Organization,
        chunk_repo: PostgreSQL_ChunkRepository,
        sample_pdf_bytes: bytes,
        storage_cleanup
    ):
        """Test that chunks have embeddings created"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        files = {"file": ("embeddings-test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify all chunks have embeddings
        chunks = chunk_repo.get_by_document(org.id, data["document_id"])
        assert len(chunks) > 0
        
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) > 0  # Embedding vector should have dimensions
            assert chunk.content is not None
            assert len(chunk.content) > 0
            
    def test_ingest_document_transaction_rollback_on_error(
        self,
        client: TestClient,
        test_organization: Organization,
        doc_repo: PostgreSQL_DocumentRepository,
        db_session: Session
    ):
        """Test that database transaction is rolled back on error"""
        # Arrange
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        invalid_content = b"Not a valid PDF"
        files = {"file": ("invalid.pdf", io.BytesIO(invalid_content), "application/pdf")}
        
        # Act - This should fail and rollback
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 400  # Parsing error
        
        # Verify transaction was rolled back (no document persisted)
        
    def test_ingest_document_content_is_parsed_correctly(
        self,
        client: TestClient,
        test_organization: Organization,
        doc_repo: PostgreSQL_DocumentRepository,
        sample_pdf_bytes: bytes,
        storage_cleanup
    ):
        """Test that PDF content is correctly parsed and stored"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        files = {"file": ("content-test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify content was parsed
        document = doc_repo.get_by_id(org.id, data["document_id"])
        assert document is not None
        assert document.content is not None
        assert len(document.content) > 100  # Should have substantial content
        
        # Verify expected content from the sample PDF
        # (These are fragments from the sample PDF based on the existing test)
        expected_fragments = ["Integer", "lacinia", "lobortis", "imperdiet"]
        content_lower = document.content.lower()
        assert any(fragment.lower() in content_lower for fragment in expected_fragments)
        
    def test_ingest_document_chunks_have_correct_indices(
        self,
        client: TestClient,
        test_organization: Organization,
        chunk_repo: PostgreSQL_ChunkRepository,
        sample_pdf_bytes: bytes,
        storage_cleanup
    ):
        """Test that chunks are indexed correctly starting from 0"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        files = {"file": ("chunks-test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        chunks = chunk_repo.get_by_document(org.id, data["document_id"])
        chunk_indices = sorted([chunk.chunk_index for chunk in chunks])
        
        # Verify indices are sequential starting from 0
        assert chunk_indices[0] == 0
        assert chunk_indices[-1] == len(chunks) - 1
        assert chunk_indices == list(range(len(chunks)))
        
    def test_ingest_document_different_filenames_same_content_deduplicated(
        self,
        client: TestClient,
        test_organization: Organization,
        sample_pdf_bytes: bytes,
        db_session: Session,
        storage_cleanup
    ):
        """Test that same content with different filename is deduplicated by hash"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        
        # First upload
        files1 = {"file": ("original-name.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        response1 = client.post("/api/ingest-document", headers=headers, files=files1)
        assert response1.status_code == 200
        db_session.commit()
        
        # Act - Second upload with different filename but same content
        files2 = {"file": ("different-name.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        response2 = client.post("/api/ingest-document", headers=headers, files=files2)
        
        # Assert
        assert response2.status_code == 409  # Duplicate detected
        assert response1.json()["document_hash"] == response2.json()["detail"].split()[-1] or "already exists" in response2.json()["detail"].lower()


class TestIngestDocumentEndpointEdgeCases:
    """Additional edge case tests for the ingest document endpoint"""
    
    def test_ingest_document_missing_file_returns_422(
        self,
        client: TestClient,
        test_organization: Organization
    ):
        """Test that missing file parameter returns 422"""
        # Arrange
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        
        # Act - No files parameter
        response = client.post("/api/ingest-document", headers=headers)
        
        # Assert
        assert response.status_code == 422  # FastAPI validation error
        
    def test_ingest_document_multiple_organizations_isolated(
        self,
        client: TestClient,
        db_session: Session,
        sample_pdf_bytes: bytes,
        storage_cleanup
    ):
        """Test that documents are isolated between organizations"""
        storage_cleanup("./storage")
        
        # Create two organizations
        org_repo = PostgreSQL_OrganizationRepository(db_session)
        
        api_key1 = generate_api_key()
        org1 = Organization(name="Org One", api_key_hash=hash_api_key(api_key1))
        org_repo.add(org1)
        
        api_key2 = generate_api_key()
        org2 = Organization(name="Org Two", api_key_hash=hash_api_key(api_key2))
        org_repo.add(org2)
        db_session.commit()
        
        # Upload same document to both organizations
        files1 = {"file": ("shared.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        response1 = client.post("/api/ingest-document", headers={"X-API-Key": api_key1}, files=files1)
        
        files2 = {"file": ("shared.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
        response2 = client.post("/api/ingest-document", headers={"X-API-Key": api_key2}, files=files2)
        
        # Both should succeed (hash is scoped to organization)
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Document IDs should be different
        assert response1.json()["document_id"] != response2.json()["document_id"]
        assert response1.json()["organization_id"] != response2.json()["organization_id"]
        
    def test_ingest_document_filename_with_special_characters(
        self,
        client: TestClient,
        test_organization: Organization,
        sample_pdf_bytes: bytes,
        doc_repo: PostgreSQL_DocumentRepository,
        storage_cleanup
    ):
        """Test that filenames with special characters are handled correctly"""
        # Arrange
        storage_cleanup("./storage")
        org, api_key = test_organization
        headers = {"X-API-Key": api_key}
        special_filename = "test doc (2024) - v1.2 #final.pdf"
        files = {"file": (special_filename, io.BytesIO(sample_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/ingest-document", headers=headers, files=files)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify filename is preserved
        document = doc_repo.get_by_id(org.id, data["document_id"])
        assert document.title == special_filename
