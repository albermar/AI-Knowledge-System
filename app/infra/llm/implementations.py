from app.domain.interfaces import LLMInterface
from app.domain.types import LLMResponse


class FakeLLMClient(LLMInterface):
    def call(self, prompt: str) -> LLMResponse:
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise ValueError("Prompt cannot be empty.")

        return LLMResponse(
            generated_answer=f"This is a fake answer generated for manual testing with a {len(clean_prompt.split())} words prompt \n Prompt was: {clean_prompt}",
            model_name="fake-llm",
            prompt_tokens=120,
            completion_tokens=10,
            total_tokens=130,
            latency_ms=25,
            estimated_cost_usd=0.0,
        )
        