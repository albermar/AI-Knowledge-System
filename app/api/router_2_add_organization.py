
from app.application.exceptions import InvalidOrganizationNameError, PersistenceError,  OrganizationAlreadyExistsError
from fastapi import Depends, HTTPException
from fastapi import APIRouter
from sqlalchemy.orm import Session 
from app.infra.db.engine import get_db_session

from app.api.schemas import NewOrganizationResponse, NewOrganizationRequest
from app.infra.db.implementations import PostgreSQL_OrganizationRepository
from app.application.use_cases import NewOrganization

router = APIRouter()

@router.post("/organizations", response_model = NewOrganizationResponse, status_code=201)
async def add_organization(payload: NewOrganizationRequest, db: Session = Depends(get_db_session)):
    #create orgnization repository
    org_repo = PostgreSQL_OrganizationRepository(db)
    use_case = NewOrganization(org_repo=org_repo)
    result = None
    try:
        result = use_case.execute(name=payload.name)
        db.commit()
        return NewOrganizationResponse.from_domain(result)
    except InvalidOrganizationNameError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except OrganizationAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except PersistenceError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to persist organization: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
