#pydantic schemas
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from typing import Optional

from app.application.dto import (
    IngestDocumentResult,
    NewOrganizationResult,
    AskQuestionResult,
    DashboardResult,
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
    api_key: str
    created_at: datetime    
    
    @classmethod
    def from_domain(cls, result: NewOrganizationResult) -> "NewOrganizationResponse":
        return cls(
            id=result.id,
            name=result.name,
            api_key=result.api_key,
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
    


# -- Dashboard response schemas -- #

class DashboardDocumentResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    created_at: str
    chunks_created: int


class DashboardQueryResponse(BaseModel):
    query_id: uuid.UUID
    question: str
    created_at: str
    model_name: Optional[str] = None
    total_tokens: int
    estimated_cost_usd: float


class DashboardUsageSummaryResponse(BaseModel):
    request_count: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: float
    models_used: list[str]


class DashboardResponse(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_created_at: str

    documents: list[DashboardDocumentResponse]
    queries: list[DashboardQueryResponse]

    usage_summary: DashboardUsageSummaryResponse

    @classmethod
    def from_domain(cls, result: DashboardResult):

        return cls(
            organization_id=result.organization_id,
            organization_name=result.organization_name,
            organization_created_at=result.organization_created_at,

            documents=[
                DashboardDocumentResponse(
                    document_id=d.document_id,
                    filename=d.filename,
                    created_at=d.created_at,
                    chunks_created=d.chunks_created
                )
                for d in result.documents
            ],

            queries=[
                DashboardQueryResponse(
                    query_id=q.query_id,
                    question=q.question,
                    created_at=q.created_at,
                    model_name=q.model_name,
                    total_tokens=q.total_tokens,
                    estimated_cost_usd=q.estimated_cost_usd
                )
                for q in result.queries
            ],

            usage_summary=DashboardUsageSummaryResponse(
                request_count=result.usage_summary.request_count,
                total_prompt_tokens=result.usage_summary.total_prompt_tokens,
                total_completion_tokens=result.usage_summary.total_completion_tokens,
                total_tokens=result.usage_summary.total_tokens,
                total_estimated_cost_usd=result.usage_summary.total_estimated_cost_usd,
                models_used=result.usage_summary.models_used,
            ),
        )