from decimal import ROUND_HALF_UP, Decimal
import time

from app.domain.interfaces import LLMInterface
from app.domain.types import LLMResponse

from openai import OpenAI
import os


# for testing purposes
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
        

class OpenAILLMClient(LLMInterface):
    """
    Production LLM client using OpenAI Responses API.

    Expected env vars:
    - OPENAI_API_KEY
    - OPENAI_MODEL (optional, default: gpt-4.1-mini)

    Notes:
    - Validates prompt is not empty
    - Measures latency in ms
    - Maps token usage into your LLMResponse
    - Estimates cost with configurable per-model pricing table
    """

    DEFAULT_MODEL = "gpt-4.1-mini"

    # Update these if you want exact pricing for your chosen model.
    # Prices are USD per 1M tokens.
    PRICING_PER_1M_TOKENS = {
        "gpt-4.1-mini": {
            "input": Decimal("0.40"),
            "output": Decimal("1.60"),
        },
        "gpt-4.1": {
            "input": Decimal("2.00"),
            "output": Decimal("8.00"),
        },
        "gpt-4o-mini": {
            "input": Decimal("0.15"),
            "output": Decimal("0.60"),
        },
        "gpt-4o": {
            "input": Decimal("2.50"),
            "output": Decimal("10.00"),
        },
    }

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        self.model = (model or os.getenv("OPENAI_MODEL") or self.DEFAULT_MODEL).strip()
        
        self.client = OpenAI(api_key=self.api_key)

    def call(self, prompt: str) -> LLMResponse:
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise ValueError("Prompt cannot be empty.")

        started_at = time.perf_counter()

        response = self.client.responses.create(
            model=self.model,
            input=clean_prompt,
        )

        latency_ms = int((time.perf_counter() - started_at) * 1000)

        generated_answer = self._extract_text(response)
        prompt_tokens = self._safe_int(getattr(response.usage, "input_tokens", 0))
        completion_tokens = self._safe_int(getattr(response.usage, "output_tokens", 0))
        total_tokens = self._safe_int(getattr(response.usage, "total_tokens", 0))

        estimated_cost_usd = self._estimate_cost_usd(
            model_name=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return LLMResponse(
            generated_answer=generated_answer,
            model_name=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=estimated_cost_usd,
        )

    def _extract_text(self, response) -> str:
        """
        Responses API commonly exposes text as `response.output_text`.
        Fallbacks included for robustness across SDK shapes.
        """
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        # Defensive fallback in case SDK shape changes or output_text is absent
        output = getattr(response, "output", None) or []
        collected_parts: list[str] = []

        for item in output:
            content = getattr(item, "content", None) or []
            for part in content:
                text_value = getattr(part, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    collected_parts.append(text_value.strip())

        final_text = "\n".join(collected_parts).strip()
        if not final_text:
            raise ValueError("OpenAI response did not contain generated text.")

        return final_text

    def _estimate_cost_usd(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        pricing = self.PRICING_PER_1M_TOKENS.get(model_name)
        if not pricing:
            return 0.0

        input_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * pricing["input"]
        output_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * pricing["output"]
        total_cost = input_cost + output_cost

        return float(total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0