from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

import uuid
from typing import Optional


#Now We are going to define the entities connected to ORM models

def new_uuid() -> uuid.UUID:
    return uuid.uuid4()

# -- Knowledge related entities -- #
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True, slots=True)
class Organization:
    name: str #Mandatory field, no default value
    api_key_hash: str #mandatory field, no default value
    
    id: uuid.UUID = field(default_factory=new_uuid)
    created_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self) -> None:
        name = (self.name or "").strip()  # Remove leading/trailing whitespace
        if not name:
            raise ValueError("Organization name cannot be empty")
        if len(name) > 255:
            raise ValueError("Organization name cannot exceed 255 characters")
        
        #chech if the api key hash is valid (len > 0 and less than 64 chars)
        api_key_hash = (self.api_key_hash or "").strip()
        if not api_key_hash:
            raise ValueError("API key hash cannot be empty")
        if len(api_key_hash) != 64:
            raise ValueError("API key hash must be exactly 64 characters")
                
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "api_key_hash", api_key_hash)

@dataclass(frozen=True, slots=True)
class Document:
    # Non-default fields first
    organization_id: uuid.UUID
    title: str  # mandatory
    source_type: str  # mandatory
    content: str  # mandatory
    document_hash: str | None = None  # For future deduplication
    
    id: uuid.UUID = field(default_factory=new_uuid) #build automatically when creating the object.
    created_at: datetime = field(default_factory=utc_now) #build automatically when creating the object.

    def __post_init__(self) -> None:
        # ---- Title validation ----
        title = (self.title or "").strip()
        if not title:
            raise ValueError("Document title cannot be empty")
        if len(title) > 255:
            raise ValueError("Document title cannot exceed 255 characters")

        # ---- Source type validation ----
        source_type = (self.source_type or "").strip()
        if not source_type:
            raise ValueError("Document source_type cannot be empty")
        if len(source_type) > 32:
            raise ValueError("Document source_type cannot exceed 32 characters")

        # ---- Content validation (preserve original text) ----
        raw_content = self.content or ""
        if not raw_content.strip():
            raise ValueError("Document content cannot be empty")

        # ---- Frozen-safe assignments ----
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "content", raw_content)
 
@dataclass(frozen=True, slots=True)
class Chunk:
    # non-default fields first
    document_id: uuid.UUID
    organization_id: uuid.UUID
    chunk_index: int
    content: str
    embedding: list[float]
    
    token_count: int | None
    
    
    id: uuid.UUID = field(default_factory=new_uuid)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.chunk_index < 0:
            raise ValueError("Chunk.chunk_index cannot be negative.")

        content = (self.content or "").strip()
        if not content:
            raise ValueError("Chunk.content cannot be empty.")

        if self.token_count is not None and self.token_count < 0:
            raise ValueError("Chunk.token_count cannot be negative.")

        if self.embedding is None or len(self.embedding) == 0:
            raise ValueError("Chunk.embedding cannot be empty.")

        object.__setattr__(self, "content", content)


# -- Question answering related entities -- #
@dataclass(frozen=True, slots=True)
class Query:
    # non-default fields first
    organization_id: uuid.UUID
    question: str  # mandatory
    
    answer: str | None
    latency_ms: int | None
    
    id: uuid.UUID = field(default_factory=new_uuid)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        question = (self.question or "").strip()
        if not question:
            raise ValueError("Query.question cannot be empty.")

        answer = self.answer
        if answer is not None:
            answer = answer.strip()
            if answer == "":
                answer = None

        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("Query.latency_ms cannot be negative.")

        object.__setattr__(self, "question", question)
        object.__setattr__(self, "answer", answer)

    # immutable update: return a NEW instance
    def mark_answered(self, answer: str, latency_ms: Optional[int] = None) -> "Query":
        answer2 = (answer or "").strip()
        if not answer2:
            raise ValueError("Answer cannot be empty.")

        if latency_ms is not None and latency_ms < 0:
            raise ValueError("Latency_ms cannot be negative.")

        return replace(self, answer=answer2, latency_ms=latency_ms)

@dataclass(frozen=True, slots=True)
class QueryChunk:
    query_id: uuid.UUID
    chunk_id: uuid.UUID
    similarity_score: float | None = None
    rank: int | None = None #what is rank? 

    def __post_init__(self) -> None:
        if self.similarity_score is not None and self.similarity_score < 0:
            raise ValueError("QueryChunk.similarity_score cannot be negative.")
        if self.rank is not None and self.rank < 1:
            raise ValueError("QueryChunk.rank must be >= 1.")

@dataclass(frozen=True, slots=True)
class LLMUsage:
    # non-default fields first
    query_id: uuid.UUID
    model_name: str
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    estimated_cost_usd: float | None = None
    
    id: uuid.UUID = field(default_factory=new_uuid)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        model_name = (self.model_name or "").strip()
        if not model_name:
            raise ValueError("LLMUsage.model_name cannot be empty.")
        if len(model_name) > 128:
            raise ValueError("LLMUsage.model_name too long (max 128).")

        if self.prompt_tokens < 0:
            raise ValueError("prompt_tokens cannot be negative.")
        if self.completion_tokens < 0:
            raise ValueError("completion_tokens cannot be negative.")
        if self.total_tokens < 0:
            raise ValueError("total_tokens cannot be negative.")

        derived_total = self.prompt_tokens + self.completion_tokens
        final_total = self.total_tokens if self.total_tokens != 0 else derived_total

        if self.estimated_cost_usd is not None and self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd cannot be negative.")

        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "total_tokens", final_total)
        
   