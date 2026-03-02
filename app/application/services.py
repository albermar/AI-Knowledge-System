from app.domain.interfaces import ChunkerInterface

class V1_Chunker(ChunkerInterface):
    def chunk_text(self, text: str) -> list[str]:
        pass