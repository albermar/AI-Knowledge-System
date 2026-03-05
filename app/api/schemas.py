#pydantic schemas
from dataclasses import Field
import datetime
import uuid

from pydantic import BaseModel
from typing import List, Optional

from app.domain.entities import IngestDocumentResult, NewOrganizationResult

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

'''
@dataclass(frozen=True)
class IngestDocumentResult:
    organization_id: uuid.UUID
    document_id: uuid.UUID
    chunks_created: int
    document_hash: str | None
'''

class NewOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)

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
