import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infra.db.engine import get_db_session
from app.api.schemas import AskQuestionRequest, AskQuestionResponse

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
from app.infra.llm.implementations import FakeLLMClient
from app.infra.embedder.implementations import SentenceTransformerEmbedder

router = APIRouter()

# TEMPORARY — until API key auth is implemented
DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


@router.post("/questions", response_model=AskQuestionResponse, status_code=200)
async def ask_question(
    payload: AskQuestionRequest,
    db: Session = Depends(get_db_session),
):
    organization_id = DEFAULT_ORGANIZATION_ID
    organization_id = uuid.UUID("08e7b03b-3301-4c0f-8ea4-f4753b6510b8") #QUITAR


    # repositories
    org_repo = PostgreSQL_OrganizationRepository(db)
    query_repo = PostgreSQL_QueryRepository(db)
    llm_usage_repo = PostgreSQL_LLMUsageRepository(db)
    query_chunk_repo = PostgreSQL_QueryChunkRepository(db)
    chunk_repo = PostgreSQL_ChunkRepository(db)

    # services
    embedder = SentenceTransformerEmbedder()

    retriever = V1_Retriever(
        chunk_repo=chunk_repo,
        embedder=embedder,
    )

    prompt_builder = V1_PromptBuilder()
    llm_client = FakeLLMClient()

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
            organization_id=organization_id,
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