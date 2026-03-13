import uuid

from app.domain.interfaces import EmbedderInterface, LLMInterface
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_organization, get_embedder
from app.infra.db.engine import get_db_session
from app.api.schemas import AskQuestionRequest, AskQuestionResponse

from app.domain.entities import Organization
from app.application.use_cases import AskQuestion
from app.application.exceptions import (
    EmptyQuestionError,
    OrganizationNotFoundError,
    NoRelevantChunksFoundError,
    QueryPersistenceError,
    LLMUsagePersistenceError,
    QueryChunkPersistenceError,
    UseCaseError,
)

from app.infra.db.implementations import (
    PostgreSQL_OrganizationRepository,
    PostgreSQL_QueryRepository,
    PostgreSQL_LLMUsageRepository,
    PostgreSQL_QueryChunkRepository,
    PostgreSQL_ChunkRepository,
)

from app.infra.retriever.implementations import V1_Retriever
from app.application.services.prompt_builder import V1_PromptBuilder
#from app.infra.embedder.implementations import SentenceTransformerEmbedder

from app.api.dependencies import get_llm_client

router = APIRouter()

@router.post("/questions", response_model=AskQuestionResponse, status_code=200)
async def ask_question(
    payload: AskQuestionRequest,
    organization: Organization = Depends(get_current_organization),
    llm_client: LLMInterface = Depends(get_llm_client),
    db: Session = Depends(get_db_session),
    embedder: EmbedderInterface = Depends(get_embedder)
):
    # repositories
    org_repo = PostgreSQL_OrganizationRepository(db)
    query_repo = PostgreSQL_QueryRepository(db)
    llm_usage_repo = PostgreSQL_LLMUsageRepository(db)
    query_chunk_repo = PostgreSQL_QueryChunkRepository(db)
    chunk_repo = PostgreSQL_ChunkRepository(db)

    # services
    embedder = embedder

    retriever = V1_Retriever(
        chunk_repo=chunk_repo,
        embedder=embedder,
    )

    prompt_builder = V1_PromptBuilder()
    
    # use case
    use_case = AskQuestion(
        org_repo=org_repo,
        query_repo=query_repo,
        llm_usage_repo=llm_usage_repo,
        query_chunk_repo=query_chunk_repo,
        retriever=retriever,
        prompt_builder=prompt_builder,
        llm_client=llm_client,
    )

    try:
        result = use_case.execute(
            organization_id=organization.id, #here comes the org id from the auth context returned by the get_current_organization dependency. If the organization didn't exist or the API key was invalid, it would have already raised an HTTPException and we wouldn't reach this point.
            question=payload.question,
        )

        db.commit()

        return AskQuestionResponse.from_domain(result)

    except EmptyQuestionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except OrganizationNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    except NoRelevantChunksFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    except (QueryPersistenceError, LLMUsagePersistenceError, QueryChunkPersistenceError) as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    except UseCaseError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
        
