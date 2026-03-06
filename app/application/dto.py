     
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

from app.domain.entities import LLMUsage

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
    created_at: datetime
    
@dataclass(frozen=True)
class AskQuestionResult:
    query_id: uuid.UUID
    question: str
    answer: Optional[str]
    latency_ms: Optional[int]
    usage: Optional[LLMUsage]
