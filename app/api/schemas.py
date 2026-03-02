#pydantic schemas
import uuid

from pydantic import BaseModel
from typing import List, Optional

from app.domain.entities import IngestDocumentResult

class IngestDocumentResponse(BaseModel):
    status: bool
    number_of_chunks: Optional[int] = None
    document_id: Optional[uuid.UUID] = None
    
    @classmethod
    def from_domain(cls, result: IngestDocumentResult) -> "IngestDocumentResponse":
        return cls(
            status=result.status,
            number_of_chunks=result.number_of_chunks,
            document_id=result.document_id
        )
