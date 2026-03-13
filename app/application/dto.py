     
from dataclasses import dataclass
from datetime import datetime
import uuid

# -- Use case results -- #

@dataclass(frozen=True)
class IngestDocumentResult:
    organization_id: uuid.UUID
    document_id: uuid.UUID
    chunks_created: int
    document_hash: str | None
    
@dataclass(frozen=True)
class NewOrganizationResult:
    id: uuid.UUID
    name: str
    api_key: str
    created_at: datetime
    
@dataclass(frozen=True)
class AskQuestionResult:
    query_id: uuid.UUID
    question: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    answer: str | None
    latency_ms: int | None
    estimated_cost_usd: float | None
    


# -- DTOs for Dashboard -- #


@dataclass
class DashboardDocument:
    document_id: uuid.UUID
    filename: str
    created_at: str
    chunks_created: int


@dataclass
class DashboardQuery:
    query_id: uuid.UUID
    question: str
    created_at: str
    model_name: str | None
    total_tokens: int
    estimated_cost_usd: float


@dataclass
class DashboardUsageSummary:
    request_count: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: float
    models_used: list[str]


@dataclass
class DashboardResult:
    organization_id: uuid.UUID
    organization_name: str
    organization_created_at: str

    documents: list[DashboardDocument]
    queries: list[DashboardQuery]

    usage_summary: DashboardUsageSummary