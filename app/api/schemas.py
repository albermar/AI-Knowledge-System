#pydantic schemas
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from typing import List, Optional

from app.application.dto import (
    IngestDocumentResult,
    NewOrganizationResult,
    AskQuestionResult,
)


# -- Response schemas -- #

class IngestDocumentResponse(BaseModel):
    organization_id: Optional[uuid.UUID] = None
    document_hash: Optional[str] = None
    chunks_created: Optional[int] = None
    document_id: Optional[uuid.UUID] = None
    
    @classmethod
    def from_domain(cls, result: IngestDocumentResult) -> "IngestDocumentResponse":
        return cls(
            organization_id=result.organization_id,
            document_hash=result.document_hash,
            chunks_created=result.chunks_created,
            document_id=result.document_id
        )

class NewOrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime    
    
    @classmethod
    def from_domain(cls, result: NewOrganizationResult) -> "NewOrganizationResponse":
        return cls(
            id=result.id,
            name=result.name,
            created_at=result.created_at
        )

class AskQuestionResponse(BaseModel):
    query_id: uuid.UUID
    question: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    answer: Optional[str] = None
    latency_ms: Optional[int] = None
    estimated_cost_usd: Optional[float] = None

    @classmethod
    def from_domain(cls, result: AskQuestionResult) -> "AskQuestionResponse":
        return cls(
            query_id=result.query_id,
            question=result.question,
            model_name=result.model_name,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            answer=result.answer,
            latency_ms=result.latency_ms,
            estimated_cost_usd=result.estimated_cost_usd,
        )



# --- Request schemas -- #

class NewOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)

class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10_000)