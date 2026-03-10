# -- Intermediate data structures used inside use cases -- #

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    content: str
    chunk_index: int
    similarity_score: float
    
@dataclass(frozen=True)
class LLMResponse:
    generated_answer: str
    model_name: str    
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int | None
    estimated_cost_usd: float | None
    
    