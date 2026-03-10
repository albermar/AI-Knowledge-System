import uuid
from app.infra.db.implementations import PostgreSQL_OrganizationRepository
import pytest

from app.application.use_cases import NewOrganization
from app.application.exceptions import (
    InvalidOrganizationNameError,
    OrganizationAlreadyExistsError,
    PersistenceError,
)
from app.domain.entities import Organization

from tests.use_cases.helpers import make_db_session


FAKE_HASH = "a" * 64


def test_new_organization_rejects_empty_name():
    class OrgRepoFake:
        def get_by_name(self, name): return None
        def add(self, org): raise AssertionError("should not be called")

    uc = NewOrganization(org_repo=OrgRepoFake())

    with pytest.raises(InvalidOrganizationNameError):
        uc.execute("   ")


def test_new_organization_rejects_too_long_name():
    class OrgRepoFake:
        def get_by_name(self, name): return None
        def add(self, org): raise AssertionError("should not be called")

    uc = NewOrganization(org_repo=OrgRepoFake())

    with pytest.raises(InvalidOrganizationNameError):
        uc.execute("a" * 201)


def test_new_organization_rejects_duplicate_name():
    class OrgRepoFake:
        def get_by_name(self, name):
            return Organization(name=name, api_key_hash=FAKE_HASH)  # any non-None means exists 
        def add(self, org): raise AssertionError("should not be called")

    uc = NewOrganization(org_repo=OrgRepoFake())

    with pytest.raises(OrganizationAlreadyExistsError):
        uc.execute("Acme")


def test_new_organization_wraps_persistence_error():
    class OrgRepoFake:
        def get_by_name(self, name): return None
        def add(self, org): raise Exception("db down")

    uc = NewOrganization(org_repo=OrgRepoFake())

    with pytest.raises(PersistenceError):
        uc.execute("Acme")


def test_new_organization_happy_path_returns_result():
    seen = {"added": None}

    class OrgRepoFake:
        def get_by_name(self, name): return None
        def add(self, org):
            seen["added"] = org

    uc = NewOrganization(org_repo=OrgRepoFake())

    result = uc.execute("  Acme  ")

    assert result.name == "Acme"
    assert isinstance(result.id, uuid.UUID)
    assert result.created_at is not None
    assert seen["added"] is not None
    assert seen["added"].name == "Acme"
    assert seen["added"].api_key_hash is not None
    
    
# Integration test with real db session (requires test db configured in env vars)

def test_new_organization_persists_and_can_read_back():
    db = make_db_session()
    try:
        repo = PostgreSQL_OrganizationRepository(db)
        uc = NewOrganization(org_repo=repo)

        result = uc.execute("Acme")

        # read using repo
        org_by_id = repo.get_by_id(result.id)
        assert org_by_id is not None
        assert org_by_id.id == result.id
        assert org_by_id.name == "Acme"
        assert org_by_id.api_key_hash is not None
        assert len(org_by_id.api_key_hash) == 64
        
        org_by_name = repo.get_by_name("Acme")
        assert org_by_name is not None
        assert org_by_name.id == result.id
        assert org_by_name.api_key_hash is not None
        assert len(org_by_name.api_key_hash) == 64
        
        

    finally:
        db.rollback()
        db.close()


def test_new_organization_duplicate_name_raises():
    db = make_db_session()
    try:
        repo = PostgreSQL_OrganizationRepository(db)
        uc = NewOrganization(org_repo=repo)

        uc.execute("Acme")

        with pytest.raises(OrganizationAlreadyExistsError):
            uc.execute("Acme")

    finally:
        db.rollback()
        db.close()
