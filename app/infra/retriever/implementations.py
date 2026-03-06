from app.domain.interfaces import ChunkRepositoryInterface, RetrieverInterface, EmbedderInterface
from app.domain.entities import Chunk
from app.domain.types import RetrievedChunk
import uuid

class V1_Retriever(RetrieverInterface):
    chunk_repo: ChunkRepositoryInterface
    embedder: EmbedderInterface 
    
    def __init__(self, chunk_repo: ChunkRepositoryInterface, embedder: EmbedderInterface):
        self.chunk_repo = chunk_repo
        self.embedder = embedder
        
    def retrieve_best_chunks(self, organization_id: uuid.UUID, question: str) -> list[RetrievedChunk]:
        # 1. Embed the question using the embedder. 
        embedded_question = self.embedder.embed_question(question)
        chunks_ann : list[Chunk] = self.chunk_repo.vector_search(organization_id, embedded_question)
        return chunks_ann