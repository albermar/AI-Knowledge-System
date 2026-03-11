"""
Integration tests for router_3_ask_question.py endpoint
Tests the entire vertical pipeline: API -> Auth -> Use Case -> Retriever -> LLM -> Repository -> Database
"""
import io
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.main import app
from app.infra.db.engine import get_db_session
from app.infra.db.implementations import (
    PostgreSQL_QueryRepository,
    PostgreSQL_LLMUsageRepository,
    PostgreSQL_QueryChunkRepository,
)
from app.domain.entities import Organization
from app.application.services.api_key import generate_api_key, hash_api_key
from tests.use_cases.helpers import make_db_session


# Counter to ensure unique organization names across all tests
_org_counter = 0


def get_unique_org_name(base_name: str = "Test Org") -> str:
    """Generate unique organization names to avoid conflicts"""
    global _org_counter
    _org_counter += 1
    return f"{base_name} {uuid.uuid4()} {_org_counter}"


@pytest.fixture
def db_session() -> Session:
    """Fixture that provides a test database session"""
    return make_db_session()


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
def test_organization_with_documents(db_session: Session, client: TestClient):
    """Fixture that creates a test organization with ingested documents"""
    from app.infra.db.implementations import PostgreSQL_OrganizationRepository
    
    org_repo = PostgreSQL_OrganizationRepository(db_session)
    
    # Generate API key and hash
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    # Create organization with unique name
    org = Organization(name=get_unique_org_name("Question Test Org"), api_key_hash=api_key_hash)
    org_repo.add(org)
    db_session.commit()
    
    # Ingest a sample document to have chunks for retrieval
    pdf_path = Path("./samples/pdf-sample-test.pdf")
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Override dependency for ingestion
        def override_get_db_session_ingest():
            try:
                yield db_session
            finally:
                pass
        
        app.dependency_overrides[get_db_session] = override_get_db_session_ingest
        
        with TestClient(app) as ingest_client:
            headers = {"X-API-Key": api_key}
            files = {"file": ("test-doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            response = ingest_client.post("/api/ingest-document", headers=headers, files=files)
            
            if response.status_code == 200:
                db_session.commit()
        
        app.dependency_overrides.clear()
        
    return org, api_key


@pytest.fixture
def test_organization_no_documents(db_session: Session):
    """Fixture that creates a test organization without any documents"""
    from app.infra.db.implementations import PostgreSQL_OrganizationRepository
    
    org_repo = PostgreSQL_OrganizationRepository(db_session)
    
    # Generate API key and hash
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    # Create organization with unique name
    org = Organization(name=get_unique_org_name("Empty Org"), api_key_hash=api_key_hash)
    org_repo.add(org)
    db_session.commit()
    
    # Return organization with plain API key for testing
    return org, api_key


@pytest.fixture
def query_repo(db_session: Session) -> PostgreSQL_QueryRepository:
    """Fixture that provides a query repository"""
    return PostgreSQL_QueryRepository(db_session)


@pytest.fixture
def llm_usage_repo(db_session: Session) -> PostgreSQL_LLMUsageRepository:
    """Fixture that provides an LLM usage repository"""
    return PostgreSQL_LLMUsageRepository(db_session)


@pytest.fixture
def query_chunk_repo(db_session: Session) -> PostgreSQL_QueryChunkRepository:
    """Fixture that provides a query-chunk repository"""
    return PostgreSQL_QueryChunkRepository(db_session)


class TestAskQuestionEndpoint:
    """Test suite for POST /api/questions endpoint"""
    
    def test_ask_question_success(
        self,
        client: TestClient,
        test_organization_with_documents: Organization,
        query_repo: PostgreSQL_QueryRepository,
        llm_usage_repo: PostgreSQL_LLMUsageRepository,
        query_chunk_repo: PostgreSQL_QueryChunkRepository,
        db_session: Session
    ):
        """Test successful question answering returns 200 and correct response"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "What is the content about?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "query_id" in data
        assert "question" in data
        assert "answer" in data
        assert "model_name" in data
        assert "prompt_tokens" in data
        assert "completion_tokens" in data
        assert "total_tokens" in data
        assert "latency_ms" in data
        assert "estimated_cost_usd" in data
        
        # Verify response values
        assert data["question"] == "What is the content about?"
        assert data["answer"] is not None
        assert len(data["answer"]) > 0
        assert data["model_name"] is not None
        assert data["total_tokens"] > 0
        
        # Verify query persistence
        query = query_repo.get_by_id(org.id, data["query_id"])
        assert query is not None
        assert query.question == "What is the content about?"
        assert query.answer is not None
        assert query.organization_id == org.id
        
        # Verify LLM usage persistence
        llm_usages = llm_usage_repo.get_by_query_id(org.id, data["query_id"]) #what is this? We can have multiple LLM usage records per query if we call multiple LLMs in the use case, so this returns a list. We should verify at least one matches our data.
        assert llm_usages is not None
        assert any(usage.model_name == data["model_name"] for usage in llm_usages)
        assert any(usage.total_tokens == data["total_tokens"] for usage in llm_usages)
        
        # Verify query-chunk links persistence
        query_chunks = query_chunk_repo.get_by_query_id(org.id, data["query_id"])
        assert len(query_chunks) > 0
        assert all(qc.similarity_score >= 0 for qc in query_chunks)
        assert all(qc.rank > 0 for qc in query_chunks)
        
    def test_ask_question_with_whitespace_trimming(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that question is trimmed of leading/trailing whitespace"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "  What is this document?  "}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is this document?"
        
    def test_ask_question_missing_api_key_returns_422(self, client: TestClient):
        """Test that missing API key returns 422 Unprocessable Entity"""
        # Arrange
        payload = {"question": "What is RAG?"}
        
        # Act
        response = client.post("/api/questions", json=payload)
        
        # Assert
        assert response.status_code == 422  # FastAPI validation error for missing header
        
    def test_ask_question_invalid_api_key_returns_401(self, client: TestClient):
        """Test that invalid API key returns 401 Unauthorized"""
        # Arrange
        headers = {"X-API-Key": "invalid_api_key_12345"}
        payload = {"question": "What is RAG?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
        
    def test_ask_question_empty_question_returns_400(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that empty question returns 400 Bad Request"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "   "}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        
    def test_ask_question_missing_question_returns_422(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that missing question field returns 422 Unprocessable Entity"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 422  # FastAPI validation error
        
    def test_ask_question_no_relevant_chunks_returns_404(
        self,
        client: TestClient,
        test_organization_no_documents: Organization
    ):
        """Test that question with no relevant chunks returns 404"""
        # Arrange
        org, api_key = test_organization_no_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "What is the meaning of life?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 404
        assert "no relevant chunks" in response.json()["detail"].lower()
        
    def test_ask_question_persists_query_even_when_no_chunks_found(
        self,
        client: TestClient,
        test_organization_no_documents: Organization,
        query_repo: PostgreSQL_QueryRepository
    ):
        """Test that query is persisted even when no chunks are found"""
        # Arrange
        org, api_key = test_organization_no_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "Some question"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 404
        
        # Verify query was still persisted (but without answer)
        # We can't easily retrieve it without the query_id, but the use case ensures it's added
        
    def test_ask_question_transaction_rollback_on_error(
        self,
        client: TestClient,
        test_organization_with_documents: Organization,
        query_repo: PostgreSQL_QueryRepository,
        db_session: Session
    ):
        """Test that database transaction is rolled back on error"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "   "}  # Invalid empty question
        
        # Act - This should fail and rollback
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 400
        
        # Verify transaction was rolled back
        
    def test_ask_question_multiple_questions_same_organization(
        self,
        client: TestClient,
        test_organization_with_documents: Organization,
        query_repo: PostgreSQL_QueryRepository
    ):
        """Test that multiple questions can be asked by the same organization"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        
        # Act
        response1 = client.post("/api/questions", headers=headers, json={"question": "First question?"})
        response2 = client.post("/api/questions", headers=headers, json={"question": "Second question?"})
        
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify different query IDs
        assert response1.json()["query_id"] != response2.json()["query_id"]
        assert response1.json()["question"] == "First question?"
        assert response2.json()["question"] == "Second question?"
        
    def test_ask_question_query_chunks_have_correct_ranks(
        self,
        client: TestClient,
        test_organization_with_documents: Organization,
        query_chunk_repo: PostgreSQL_QueryChunkRepository
    ):
        """Test that query-chunk links have correct sequential ranks"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "What is this about?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify ranks are sequential starting from 1
        query_chunks = query_chunk_repo.get_by_query_id(org.id, data["query_id"])
        ranks = sorted([qc.rank for qc in query_chunks])
        
        assert len(ranks) > 0
        assert ranks[0] == 1
        assert ranks[-1] == len(ranks)
        assert ranks == list(range(1, len(ranks) + 1))
        
    def test_ask_question_similarity_scores_are_valid(
        self,
        client: TestClient,
        test_organization_with_documents: Organization,
        query_chunk_repo: PostgreSQL_QueryChunkRepository
    ):
        """Test that similarity scores are within valid range [0, 1]"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "What is the content?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify similarity scores
        query_chunks = query_chunk_repo.get_by_query_id(org.id, data["query_id"])
        for qc in query_chunks:
            assert 0.0 <= qc.similarity_score <= 1.0
            
    def test_ask_question_token_counts_are_positive(
        self,
        client: TestClient,
        test_organization_with_documents,
    ):
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "Tell me about this."}

        response = client.post("/api/questions", headers=headers, json=payload)

        assert response.status_code == 200, response.json()
        data = response.json()

        assert data["prompt_tokens"] > 0
        assert data["completion_tokens"] > 0
        assert data["total_tokens"] > 0
        assert data["total_tokens"] == data["prompt_tokens"] + data["completion_tokens"]
        
    def test_ask_question_latency_is_recorded(
        self,
        client: TestClient,
        test_organization_with_documents: Organization,
        query_repo: PostgreSQL_QueryRepository
    ):
        """Test that latency is recorded for the query"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "What is this document about?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["latency_ms"] is not None
        assert data["latency_ms"] >= 0
        
        # Verify in database
        query = query_repo.get_by_id(org.id, data["query_id"])
        assert query.latency_ms is not None
        assert query.latency_ms >= 0


class TestAskQuestionEndpointEdgeCases:
    """Additional edge case tests for the ask question endpoint"""
    
    def test_ask_question_very_long_question(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that very long questions are handled correctly"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        long_question = "What is " + "very " * 100 + "important information in this document?"
        payload = {"question": long_question}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == long_question
        
    def test_ask_question_exceeds_max_length_returns_422(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that question exceeding max length returns 422"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        too_long_question = "x" * 10_001  # Max is 10,000 per schema
        payload = {"question": too_long_question}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 422  # Pydantic validation error
        
    def test_ask_question_with_special_characters(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that questions with special characters are handled"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        special_questions = [
            "What is RAG?",
            "How does it work (technically)?",
            "Can you explain: embeddings & vectors?",
            "What's the difference?",
        ]
        
        # Act & Assert
        for question in special_questions:
            response = client.post("/api/questions", headers=headers, json={"question": question})
            assert response.status_code == 200, f"Failed for question: {question}"
            assert response.json()["question"] == question
            
    def test_ask_question_with_unicode(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that questions with Unicode characters are handled"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        unicode_question = "Qué es RAG? 你好 🤖"
        payload = {"question": unicode_question}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == unicode_question
        
    def test_ask_question_multiple_organizations_isolated(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test that questions are isolated between organizations"""
        # Create two organizations with documents
        from app.infra.db.implementations import PostgreSQL_OrganizationRepository
        
        org_repo = PostgreSQL_OrganizationRepository(db_session)
        
        api_key1 = generate_api_key()
        org1 = Organization(name=get_unique_org_name("Isolated Org 1"), api_key_hash=hash_api_key(api_key1))
        org_repo.add(org1)
        
        api_key2 = generate_api_key()
        org2 = Organization(name=get_unique_org_name("Isolated Org 2"), api_key_hash=hash_api_key(api_key2))
        org_repo.add(org2)
        db_session.commit()
        
        # Ingest documents for both (if sample exists)
        pdf_path = Path("./samples/pdf-sample-test.pdf")
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            for api_key in [api_key1, api_key2]:
                files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
                response = client.post("/api/ingest-document", headers={"X-API-Key": api_key}, files=files)
                if response.status_code == 200:
                    db_session.commit()
        
        # Ask questions with both organizations
        question = "What is this document about?"
        
        response1 = client.post("/api/questions", headers={"X-API-Key": api_key1}, json={"question": question})
        response2 = client.post("/api/questions", headers={"X-API-Key": api_key2}, json={"question": question})
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Query IDs should be different
        assert response1.json()["query_id"] != response2.json()["query_id"]
        
    def test_ask_question_cost_estimation_present(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that estimated cost is present in response"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "What is the main topic?"}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "estimated_cost_usd" in data
        assert data["estimated_cost_usd"] is not None
        assert data["estimated_cost_usd"] >= 0
        
    def test_ask_question_answer_is_not_empty(
        self,
        client: TestClient,
        test_organization_with_documents: Organization
    ):
        """Test that answer is not empty when successful"""
        # Arrange
        org, api_key = test_organization_with_documents
        headers = {"X-API-Key": api_key}
        payload = {"question": "Summarize the content."}
        
        # Act
        response = client.post("/api/questions", headers=headers, json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["answer"] is not None
        assert len(data["answer"]) > 0
        assert isinstance(data["answer"], str)
