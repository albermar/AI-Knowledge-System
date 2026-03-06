from dataclasses import dataclass
from pydoc import text
import uuid

from app.domain.interfaces import ChunkerInterface, PromptBuilderInterface
from app.domain.entities import Chunk
from typing import List

def approx_token_count(text: str) -> int:
    #we approximate 4 chars per token. Replace later with real tokenizer. 
    return max(1, (len(text) + 3) // 4)

@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    chunk_size: int = 1200
    overlap: int = 200
    strip: bool = True
    min_chunk_size: int = 100


class V1_Chunker(ChunkerInterface):
    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig() #use default config if none provided. This allows us to have a single source of truth for default values and validation in the ChunkingConfig dataclass. We can also create different configs for different use cases in the future if needed.
        
        if self.config.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")
        if self.config.overlap < 0:
            raise ValueError("overlap cannot be negative.")
        if self.config.overlap >= self.config.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")
        if self.config.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be greater than 0.")
        
    def chunk_text(self, organization_id: uuid.UUID, document_id: uuid.UUID, content: str) -> List[Chunk]:
        if content is None:
            raise ValueError("Content cannot be None.")
        
        clean_text = content.strip() if self.config.strip else content
        
        if not clean_text:
            return []
        
        #create a list of str (chunks). Later we will convert to Chunk entity
        chunks: list[str] = []
        start = 0
        n = len(clean_text)
        
        while start < n:        
            end = min(start + self.config.chunk_size, n)
            piece = clean_text[start:end]
            
            if self.config.strip:
                piece = piece.strip()
            
            if piece and len(piece) >= self.config.min_chunk_size:
                chunks.append(piece)
                            
            if end >= n:
                break
            
            start = max(0, end - self.config.overlap)
        #convert to list of Chunk entities with metadata
        chunk_entities: list[Chunk] = []
        for i, chunk_text in enumerate(chunks):
            chunk_entities.append(
                Chunk(
                    document_id=document_id,
                    organization_id=organization_id,
                    chunk_index=i,
                    content=chunk_text,
                    token_count=approx_token_count(chunk_text)
                )
            )
        return chunk_entities
