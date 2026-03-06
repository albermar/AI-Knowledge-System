# -- Intermediate data structures used inside use cases -- #

from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    content: str
    similarity_score: Optional[float]
    
@dataclass(frozen=True)
class LLMResponse:
    generated_answer: str
    model_name: str    
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost_usd: float | None
    total_tokens: int | None
    
    