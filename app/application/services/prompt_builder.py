    

from app.domain.interfaces import PromptBuilderInterface
from app.domain.types import RetrievedChunk


class V1_PromptBuilder(PromptBuilderInterface):
    def build_prompt(self, question: str, retrieved_chunks: list[RetrievedChunk]) -> str:
        clean_question = (question or "").strip()
        if not clean_question:
            raise ValueError("Question cannot be empty.")

        if not retrieved_chunks:
            raise ValueError("Retrieved chunks cannot be empty.")

        context_parts: list[str] = []

        for i, chunk in enumerate(retrieved_chunks, start=1):
            context_parts.append(
                f"[Chunk {i} | chunk_index={chunk.chunk_index} | score={chunk.similarity_score:.4f}]\n"
                f"{chunk.content}"
            )

        context = "\n\n".join(context_parts)

        return (
            "You are a helpful assistant.\n"
            "Answer the user's question using only the provided context.\n"
            "If the answer cannot be found in the context, say that the context does not contain enough information.\n\n"
            f"Question:\n{clean_question}\n\n"
            f"Context:\n{context}\n\n"
            "Answer:"
        )