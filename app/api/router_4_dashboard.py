from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization
from app.domain.entities import Organization
from app.infra.db.engine import get_db_session

from app.api.schemas import DashboardResponse

from app.application.use_cases import GetOrganizationDashboard
from app.application.exceptions import OrganizationNotFoundError, UseCaseError

from app.infra.db.implementations import (
    PostgreSQL_OrganizationRepository,
    PostgreSQL_DocumentRepository,
    PostgreSQL_ChunkRepository,
    PostgreSQL_QueryRepository,
    PostgreSQL_LLMUsageRepository,
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse, status_code=200)
async def get_dashboard(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db_session),
):
    # repositories
    org_repo = PostgreSQL_OrganizationRepository(db)
    doc_repo = PostgreSQL_DocumentRepository(db)
    chunk_repo = PostgreSQL_ChunkRepository(db)
    query_repo = PostgreSQL_QueryRepository(db)
    llm_usage_repo = PostgreSQL_LLMUsageRepository(db)

    # use case
    use_case = GetOrganizationDashboard(
        org_repo=org_repo,
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        query_repo=query_repo,
        llm_usage_repo=llm_usage_repo,
    )

    try:
        result = use_case.execute(
            organization_id=organization.id
        )

        return DashboardResponse.from_domain(result)

    except OrganizationNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    except UseCaseError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")