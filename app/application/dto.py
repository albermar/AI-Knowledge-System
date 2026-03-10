     
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
    
