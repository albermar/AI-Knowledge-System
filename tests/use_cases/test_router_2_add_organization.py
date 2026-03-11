"""
Integration tests for router_2_add_organization.py endpoint
Tests the entire vertical pipeline: API -> Use Case -> Repository -> Database
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.main import app
from app.infra.db.engine import get_db_session
from app.infra.db.implementations import PostgreSQL_OrganizationRepository
from tests.use_cases.helpers import make_db_session


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
def org_repo(db_session: Session) -> PostgreSQL_OrganizationRepository:
    """Fixture that provides an organization repository for verification"""
    return PostgreSQL_OrganizationRepository(db_session)


class TestAddOrganizationEndpoint:
    """Test suite for POST /api/organizations endpoint"""
    
    def test_create_organization_success(self, client: TestClient, org_repo: PostgreSQL_OrganizationRepository, db_session: Session):
        """Test successful organization creation returns 201 and correct response"""
        # Arrange
        payload = {"name": "Acme Corporation"}
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "name" in data
        assert "api_key" in data
        assert "created_at" in data
        
        # Verify response values
        assert data["name"] == "Acme Corporation"
        assert len(data["api_key"]) > 0  # API key should be generated
        
        # Verify persistence in database
        org_id = data["id"]
        persisted_org = org_repo.get_by_id(org_id)
        assert persisted_org is not None
        assert persisted_org.name == "Acme Corporation"
        assert persisted_org.api_key_hash is not None
        assert len(persisted_org.api_key_hash) == 64  # SHA-256 hash length
        
    def test_create_organization_with_whitespace_trimming(self, client: TestClient, org_repo: PostgreSQL_OrganizationRepository):
        """Test that organization name is trimmed of leading/trailing whitespace"""
        # Arrange
        payload = {"name": "  Tech Startup  "}
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tech Startup"
        
        # Verify in database
        persisted_org = org_repo.get_by_name("Tech Startup")
        assert persisted_org is not None
        
    def test_create_organization_empty_name_returns_400(self, client: TestClient):
        """Test that empty organization name returns 400 Bad Request"""
        # Arrange
        payload = {"name": "   "}
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        
    def test_create_organization_missing_name_returns_422(self, client: TestClient):
        """Test that missing name field returns 422 Unprocessable Entity"""
        # Arrange
        payload = {}
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 422  # FastAPI validation error
        
    def test_create_organization_name_too_long_returns_400(self, client: TestClient):
        """Test that organization name exceeding 200 characters returns 400"""
        # Arrange
        payload = {"name": "X" * 201}        
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 422 #pydantic request schema raises validation error for max_length
        assert "200 characters" in response.json()["detail"][0]["msg"].lower()
        
    def test_create_organization_duplicate_name_returns_409(self, client: TestClient, db_session: Session):
        """Test that creating organization with duplicate name returns 409 Conflict"""
        # Arrange
        org_name = "Unique Company"
        payload = {"name": org_name}
        
        # Create first organization
        first_response = client.post("/api/organizations", json=payload)
        assert first_response.status_code == 201
        db_session.commit()
        
        # Act - Try to create duplicate
        second_response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert second_response.status_code == 409
        assert "already exists" in second_response.json()["detail"].lower()
        
    def test_create_organization_generates_unique_api_keys(self, client: TestClient):
        """Test that each organization gets a unique API key"""
        # Arrange & Act
        response1 = client.post("/api/organizations", json={"name": "Company One"})
        response2 = client.post("/api/organizations", json={"name": "Company Two"})
        
        # Assert
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        api_key1 = response1.json()["api_key"]
        api_key2 = response2.json()["api_key"]
        
        assert api_key1 != api_key2
        assert len(api_key1) > 0
        assert len(api_key2) > 0
        
    def test_create_organization_api_key_is_hashed_in_database(self, client: TestClient, org_repo: PostgreSQL_OrganizationRepository):
        """Test that API key is stored as hash in database, not plain text"""
        # Arrange
        payload = {"name": "Security Test Org"}
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        api_key = response.json()["api_key"]
        org_id = response.json()["id"]
        
        # Verify API key is not stored in plain text
        persisted_org = org_repo.get_by_id(org_id)
        assert persisted_org.api_key_hash != api_key
        assert len(persisted_org.api_key_hash) == 64  # SHA-256 hash
        
    def test_create_organization_transaction_rollback_on_error(self, client: TestClient, org_repo: PostgreSQL_OrganizationRepository, db_session: Session):
        """Test that database transaction is rolled back on duplicate name error"""
        # Arrange
        org_name = "Rollback Test Org"
        
        # Create first organization
        first_response = client.post("/api/organizations", json={"name": org_name})
        assert first_response.status_code == 201
        db_session.commit()
        
        # Act - Try to create duplicate (should rollback)
        second_response = client.post("/api/organizations", json={"name": org_name})
        
        # Assert
        assert second_response.status_code == 409
        
        # Verify the organization still exists with correct data
        orgs_with_name = org_repo.get_by_name(org_name)
        assert orgs_with_name is not None  # Still exists
        # There should only be one organization with this name
        
    def test_create_organization_min_length_name(self, client: TestClient):
        """Test creating organization with minimum valid name length"""
        # Arrange
        payload = {"name": "AB"}  # 2 characters is minimum per schema
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        assert response.json()["name"] == "AB"
        
    def test_create_organization_max_length_name(self, client: TestClient):
        """Test creating organization with maximum valid name length"""
        # Arrange
        payload = {"name": "X" * 200}  # 200 characters is maximum
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        assert len(response.json()["name"]) == 200
        
    def test_create_organization_special_characters_in_name(self, client: TestClient):
        """Test that organization names with special characters are accepted"""
        # Arrange
        special_names = [
            "Tech & Co.",
            "Smith-Jones LLC",
            "Café Résumé",
            "Company (2024)",
        ]
        
        # Act & Assert
        for name in special_names:
            response = client.post("/api/organizations", json={"name": name})
            assert response.status_code == 201, f"Failed for name: {name}"
            assert response.json()["name"] == name
            
    def test_create_organization_response_has_timestamp(self, client: TestClient):
        """Test that organization creation response includes created_at timestamp"""
        # Arrange
        payload = {"name": "Timestamp Test Org"}
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "created_at" in data
        assert data["created_at"] is not None
        # Verify timestamp format (ISO 8601)
        from datetime import datetime
        try:
            datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {data['created_at']}")


class TestAddOrganizationEndpointEdgeCases:
    """Additional edge case tests for the organization endpoint"""
    
    def test_create_organization_with_unicode_name(self, client: TestClient, org_repo: PostgreSQL_OrganizationRepository):
        """Test creating organization with Unicode characters"""
        # Arrange
        payload = {"name": "日本企業"}  # Japanese characters
        
        # Act
        response = client.post("/api/organizations", json=payload)
        
        # Assert
        assert response.status_code == 201
        assert response.json()["name"] == "日本企業"
        
        # Verify persistence
        org = org_repo.get_by_name("日本企業")
        assert org is not None
        
    def test_create_organization_case_sensitive_names(self, client: TestClient):
        """Test that organization names are case-sensitive"""
        # Arrange & Act
        response1 = client.post("/api/organizations", json={"name": "acme"})
        response2 = client.post("/api/organizations", json={"name": "ACME"})
        
        # Assert - Both should succeed as they are different names
        assert response1.status_code == 201
        assert response2.status_code == 201
        assert response1.json()["name"] == "acme"
        assert response2.json()["name"] == "ACME"
