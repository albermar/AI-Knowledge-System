"""
Integration tests for router_4_dashboard.py endpoint
Tests the vertical pipeline: API -> Auth -> Use Case -> Repository -> Database
"""

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
    PostgreSQL_QueryRepository,
    PostgreSQL_LLMUsageRepository,
)
from app.domain.entities import Organization, Document, Chunk, Query, LLMUsage
from app.application.services.api_key import generate_api_key, hash_api_key
from tests.use_cases.helpers import make_db_session


_org_counter = 0


def get_unique_org_name(base_name: str = "Dashboard Test Org") -> str:
    global _org_counter
    _org_counter += 1
    return f"{base_name} {uuid.uuid4()} {_org_counter}"


def make_fake_embedding(value: float = 0.1, dim: int = 384) -> list[float]:
    return [value] * dim


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
            pass

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_organization_empty(db_session: Session):
    """Organization with no docs and no queries"""
    org_repo = PostgreSQL_OrganizationRepository(db_session)

    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    org = Organization(
        name=get_unique_org_name("Empty Dashboard Org"),
        api_key_hash=api_key_hash,
    )

    org_repo.add(org)
    db_session.commit()

    return org, api_key


@pytest.fixture
def test_organization_with_dashboard_data(db_session: Session):
    """Organization populated with documents, chunks, queries, and llm usage"""
    org_repo = PostgreSQL_OrganizationRepository(db_session)
    doc_repo = PostgreSQL_DocumentRepository(db_session)
    chunk_repo = PostgreSQL_ChunkRepository(db_session)
    query_repo = PostgreSQL_QueryRepository(db_session)
    llm_usage_repo = PostgreSQL_LLMUsageRepository(db_session)

    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    org = Organization(
        name=get_unique_org_name("Populated Dashboard Org"),
        api_key_hash=api_key_hash,
    )
    org_repo.add(org)
    db_session.flush()

    # -------------------------
    # Documents + chunks
    # -------------------------
    doc1 = Document(
        organization_id=org.id,
        title="doc-1.pdf",
        source_type="pdf",
        content="This is the content of document one.",
        document_hash=f"hash-doc-1-{uuid.uuid4().hex}",
    )
    doc2 = Document(
        organization_id=org.id,
        title="doc-2.pdf",
        source_type="pdf",
        content="This is the content of document two.",
        document_hash=f"hash-doc-2-{uuid.uuid4().hex}",
    )
    doc_repo.add(doc1)
    doc_repo.add(doc2)
    db_session.flush()

    chunk_repo.add_many(
        [
            Chunk(
                document_id=doc1.id,
                organization_id=org.id,
                chunk_index=0,
                content="Chunk 1 of document 1",
                embedding=make_fake_embedding(0.1),
                token_count=10,
            ),
            Chunk(
                document_id=doc1.id,
                organization_id=org.id,
                chunk_index=1,
                content="Chunk 2 of document 1",
                embedding=make_fake_embedding(0.2),
                token_count=12,
            ),
            Chunk(
                document_id=doc2.id,
                organization_id=org.id,
                chunk_index=0,
                content="Chunk 1 of document 2",
                embedding=make_fake_embedding(0.3),
                token_count=8,
            ),
        ]
    )
    db_session.flush()

    # -------------------------
    # Queries + usage
    # -------------------------
    query1 = Query(
        organization_id=org.id,
        question="What is document 1 about?",
        answer="It is about document one.",
        latency_ms=120,
    )
    query2 = Query(
        organization_id=org.id,
        question="Summarize document 2",
        answer="It is about document two.",
        latency_ms=140,
    )
    query_repo.add(query1)
    query_repo.add(query2)
    db_session.flush()

    llm_usage_repo.add(
        LLMUsage(
            query_id=query1.id,
            model_name="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=25,
            total_tokens=125,
            estimated_cost_usd=0.0012,
        )
    )
    llm_usage_repo.add(
        LLMUsage(
            query_id=query2.id,
            model_name="gpt-4.1-mini",
            prompt_tokens=150,
            completion_tokens=50,
            total_tokens=200,
            estimated_cost_usd=0.0023,
        )
    )

    db_session.commit()

    return org, api_key


class TestGetDashboardEndpoint:
    """Core integration tests for GET /api/dashboard"""

    def test_get_dashboard_success_returns_200_and_expected_shape(
        self,
        client: TestClient,
        test_organization_with_dashboard_data,
    ):
        org, api_key = test_organization_with_dashboard_data
        headers = {"X-API-Key": api_key}

        response = client.get("/api/dashboard", headers=headers)

        assert response.status_code == 200, response.json()
        data = response.json()

        assert data["organization_id"] == str(org.id)
        assert data["organization_name"] == org.name
        assert "organization_created_at" in data

        assert "documents" in data
        assert "queries" in data
        assert "usage_summary" in data

        assert isinstance(data["documents"], list)
        assert isinstance(data["queries"], list)
        assert isinstance(data["usage_summary"], dict)

    def test_get_dashboard_returns_documents_with_chunk_counts(
        self,
        client: TestClient,
        test_organization_with_dashboard_data,
    ):
        org, api_key = test_organization_with_dashboard_data
        headers = {"X-API-Key": api_key}

        response = client.get("/api/dashboard", headers=headers)

        assert response.status_code == 200, response.json()
        data = response.json()

        assert len(data["documents"]) == 2

        docs_by_filename = {doc["filename"]: doc for doc in data["documents"]}

        assert "doc-1.pdf" in docs_by_filename
        assert "doc-2.pdf" in docs_by_filename

        assert docs_by_filename["doc-1.pdf"]["chunks_created"] == 2
        assert docs_by_filename["doc-2.pdf"]["chunks_created"] == 1

        for doc in data["documents"]:
            assert doc["document_id"] is not None
            assert doc["created_at"] is not None

    def test_get_dashboard_returns_queries_with_usage_data(
        self,
        client: TestClient,
        test_organization_with_dashboard_data,
    ):
        org, api_key = test_organization_with_dashboard_data
        headers = {"X-API-Key": api_key}

        response = client.get("/api/dashboard", headers=headers)

        assert response.status_code == 200, response.json()
        data = response.json()

        assert len(data["queries"]) == 2

        questions = {q["question"]: q for q in data["queries"]}

        assert "What is document 1 about?" in questions
        assert "Summarize document 2" in questions

        q1 = questions["What is document 1 about?"]
        q2 = questions["Summarize document 2"]

        assert q1["model_name"] == "gpt-4.1-mini"
        assert q1["total_tokens"] == 125
        assert q1["estimated_cost_usd"] == 0.0012

        assert q2["model_name"] == "gpt-4.1-mini"
        assert q2["total_tokens"] == 200
        assert q2["estimated_cost_usd"] == 0.0023

        for q in data["queries"]:
            assert q["query_id"] is not None
            assert q["created_at"] is not None

    def test_get_dashboard_returns_aggregated_usage_summary(
        self,
        client: TestClient,
        test_organization_with_dashboard_data,
    ):
        org, api_key = test_organization_with_dashboard_data
        headers = {"X-API-Key": api_key}

        response = client.get("/api/dashboard", headers=headers)

        assert response.status_code == 200, response.json()
        data = response.json()
        usage = data["usage_summary"]

        assert usage["request_count"] == 2
        assert usage["total_prompt_tokens"] == 250
        assert usage["total_completion_tokens"] == 75
        assert usage["total_tokens"] == 325
        assert usage["total_estimated_cost_usd"] == pytest.approx(0.0035)
        assert usage["models_used"] == ["gpt-4.1-mini"]

    def test_get_dashboard_empty_organization_returns_empty_lists_and_zero_summary(
        self,
        client: TestClient,
        test_organization_empty,
    ):
        org, api_key = test_organization_empty
        headers = {"X-API-Key": api_key}

        response = client.get("/api/dashboard", headers=headers)

        assert response.status_code == 200, response.json()
        data = response.json()

        assert data["organization_id"] == str(org.id)
        assert data["organization_name"] == org.name

        assert data["documents"] == []
        assert data["queries"] == []

        usage = data["usage_summary"]
        assert usage["request_count"] == 0
        assert usage["total_prompt_tokens"] == 0
        assert usage["total_completion_tokens"] == 0
        assert usage["total_tokens"] == 0
        assert usage["total_estimated_cost_usd"] == 0.0
        assert usage["models_used"] == []

    def test_get_dashboard_without_api_key_returns_422(
        self,
        client: TestClient,
    ):
        response = client.get("/api/dashboard")

        # Header is required by FastAPI dependency
        assert response.status_code == 422

    def test_get_dashboard_with_invalid_api_key_returns_401(
        self,
        client: TestClient,
    ):
        headers = {"X-API-Key": "invalid-api-key"}

        response = client.get("/api/dashboard", headers=headers)

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_get_dashboard_multiple_organizations_are_isolated(
        self,
        client: TestClient,
        db_session: Session,
    ):
        org_repo = PostgreSQL_OrganizationRepository(db_session)
        doc_repo = PostgreSQL_DocumentRepository(db_session)
        chunk_repo = PostgreSQL_ChunkRepository(db_session)
        query_repo = PostgreSQL_QueryRepository(db_session)
        llm_usage_repo = PostgreSQL_LLMUsageRepository(db_session)

        # Org 1
        api_key_1 = generate_api_key()
        org1 = Organization(
            name=get_unique_org_name("Dashboard Org 1"),
            api_key_hash=hash_api_key(api_key_1),
        )
        org_repo.add(org1)
        db_session.flush()

        doc1 = Document(
            organization_id=org1.id,
            title="org1-doc.pdf",
            source_type="pdf",
            content="Org 1 document content",
            document_hash=f"org1-{uuid.uuid4().hex}",
        )
        doc_repo.add(doc1)
        db_session.flush()

        chunk_repo.add_many(
            [
                Chunk(
                    document_id=doc1.id,
                    organization_id=org1.id,
                    chunk_index=0,
                    content="Org 1 chunk",
                    embedding=make_fake_embedding(0.1),
                    token_count=7,
                )
            ]
        )

        query1 = Query(
            organization_id=org1.id,
            question="Question for org1",
            answer="Answer for org1",
            latency_ms=50,
        )
        query_repo.add(query1)
        db_session.flush()

        llm_usage_repo.add(
            LLMUsage(
                query_id=query1.id,
                model_name="gpt-4.1-mini",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                estimated_cost_usd=0.0001,
            )
        )

        # Org 2
        api_key_2 = generate_api_key()
        org2 = Organization(
            name=get_unique_org_name("Dashboard Org 2"),
            api_key_hash=hash_api_key(api_key_2),
        )
        org_repo.add(org2)
        db_session.flush()

        doc2 = Document(
            organization_id=org2.id,
            title="org2-doc.pdf",
            source_type="pdf",
            content="Org 2 document content",
            document_hash=f"org2-{uuid.uuid4().hex}",
        )
        doc_repo.add(doc2)
        db_session.flush()

        chunk_repo.add_many(
            [
                Chunk(
                    document_id=doc2.id,
                    organization_id=org2.id,
                    chunk_index=0,
                    content="Org 2 chunk A",
                    embedding=make_fake_embedding(0.3),
                    token_count=6,
                ),
                Chunk(
                    document_id=doc2.id,
                    organization_id=org2.id,
                    chunk_index=1,
                    content="Org 2 chunk B",
                    embedding=make_fake_embedding(0.5),
                    token_count=9,
                ),
            ]
        )

        query2 = Query(
            organization_id=org2.id,
            question="Question for org2",
            answer="Answer for org2",
            latency_ms=70,
        )
        query_repo.add(query2)
        db_session.flush()

        llm_usage_repo.add(
            LLMUsage(
                query_id=query2.id,
                model_name="gpt-4.1",
                prompt_tokens=20,
                completion_tokens=10,
                total_tokens=30,
                estimated_cost_usd=0.0007,
            )
        )

        db_session.commit()

        # Call dashboard for org1 only
        response = client.get("/api/dashboard", headers={"X-API-Key": api_key_1})

        assert response.status_code == 200, response.json()
        data = response.json()

        assert data["organization_id"] == str(org1.id)
        assert data["organization_name"] == org1.name

        assert len(data["documents"]) == 1
        assert data["documents"][0]["filename"] == "org1-doc.pdf"
        assert data["documents"][0]["chunks_created"] == 1

        assert len(data["queries"]) == 1
        assert data["queries"][0]["question"] == "Question for org1"
        assert data["queries"][0]["model_name"] == "gpt-4.1-mini"
        assert data["queries"][0]["total_tokens"] == 15

        usage = data["usage_summary"]
        assert usage["request_count"] == 1
        assert usage["total_prompt_tokens"] == 10
        assert usage["total_completion_tokens"] == 5
        assert usage["total_tokens"] == 15
        assert usage["total_estimated_cost_usd"] == pytest.approx(0.0001)
        assert usage["models_used"] == ["gpt-4.1-mini"]


class TestGetDashboardEndpointEdgeCases:
    """Additional edge case tests for GET /api/dashboard"""

    def test_get_dashboard_query_without_llm_usage_returns_zeroed_query_usage(
        self,
        client: TestClient,
        db_session: Session,
    ):
        org_repo = PostgreSQL_OrganizationRepository(db_session)
        query_repo = PostgreSQL_QueryRepository(db_session)

        api_key = generate_api_key()
        org = Organization(
            name=get_unique_org_name("No Usage Org"),
            api_key_hash=hash_api_key(api_key),
        )
        org_repo.add(org)
        db_session.flush()

        query = Query(
            organization_id=org.id,
            question="Question without usage",
            answer="Answer without usage",
            latency_ms=33,
        )
        query_repo.add(query)
        db_session.commit()

        response = client.get("/api/dashboard", headers={"X-API-Key": api_key})

        assert response.status_code == 200, response.json()
        data = response.json()

        assert len(data["queries"]) == 1
        q = data["queries"][0]

        assert q["question"] == "Question without usage"
        assert q["model_name"] is None
        assert q["total_tokens"] == 0
        assert q["estimated_cost_usd"] == 0.0

        usage = data["usage_summary"]
        assert usage["request_count"] == 1
        assert usage["total_prompt_tokens"] == 0
        assert usage["total_completion_tokens"] == 0
        assert usage["total_tokens"] == 0
        assert usage["total_estimated_cost_usd"] == 0.0
        assert usage["models_used"] == []