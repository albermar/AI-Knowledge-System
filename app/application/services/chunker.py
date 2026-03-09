from dataclasses import dataclass
from pydoc import text
import uuid

from app.domain.interfaces import ChunkerInterface, PromptBuilderInterface
from app.domain.entities import Chunk
from typing import List

@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    chunk_size: int = 1200
    overlap: int = 200
    strip: bool = True
    min_chunk_size: int = 100


class V1_Chunker(ChunkerInterface):
    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

        if self.config.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")
        if self.config.overlap < 0:
            raise ValueError("overlap cannot be negative.")
        if self.config.overlap >= self.config.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")
        if self.config.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be greater than 0.")

    def chunk_text(self, content: str) -> list[str]:
        if content is None:
            raise ValueError("Content cannot be None.")

        clean_text = content.strip() if self.config.strip else content

        if not clean_text:
            return []

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

        return chunks
