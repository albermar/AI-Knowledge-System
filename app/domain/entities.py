from app.infra.db.ormmodels import *
from dataclasses import dataclass, field
from datetime import datetime, timezone

#Now We are going to define the entities connected to ORM models

def new_uuid() -> uuid.UUID:
    return uuid.uuid4()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class Organization:
    id: uuid.UUID = field(default_factory=new_uuid)
    name: str #Mandatory field, no default value
    created_at: datetime = field(default_factory=utc_now)

@dataclass(frozen=True)
class Document:
    id: uuid.UUID = field(default_factory=new_uuid)
    organization_id: uuid.UUID 
    title: str #Mandatory field, no default value
    source_type: str #Mandatory field, no default value
    content: str #Mandatory field, no default value
    created_at: datetime = field(default_factory=utc_now)
    
@dataclass(frozen=True)
class Query:
    id: uuid.UUID = field(default_factory=new_uuid)
    organization_id: uuid.UUID
    question: str #Mandatory field, no default value
    answer: Optional[str] = None 
    latency_ms: Optional[int] = None
    created_at: datetime = field(default_factory=utc_now)
    
@dataclass(frozen=True)
class Chunk:
    id: uuid.UUID = field(default_factory=new_uuid)
    document_id: uuid.UUID
    organization_id: uuid.UUID    
    chunk_index: int #Mandatory field, no default value
    content: str #Mandatory field, no default value
    token_count: Optional[int] = None 
    created_at: datetime = field(default_factory=utc_now)
        
@dataclass(frozen=True)
class QueryChunk:
    query_id: uuid.UUID
    chunk_id: uuid.UUID
    similarity_score: Optional[float] = None
    rank: Optional[int] = None    

@dataclass(frozen=True)
class LLMUsage:
    id: uuid.UUID = field(default_factory=new_uuid)
    query_id: uuid.UUID    
    model_name: str #Mandatory field, no default value
    prompt_tokens: int = 0 #Mandatory field, default to 0
    completion_tokens: int = 0 #Mandatory field, default to 0
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    created_at: datetime = field(default_factory=utc_now)