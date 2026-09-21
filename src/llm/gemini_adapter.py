from __future__ import annotations

import logging
from typing import Any, Optional
from src.config import GEMINI_API_KEY, GEMINI_MODEL, is_gemini_available
from src.llm.base_adapter import BaseAIAdapter
from src.llm.retry_handler import AITechnicalError

logger = logging.getLogger(__name__)


class GeminiAIAdapter(BaseAIAdapter):
    """Google Gemini provider adapter implementing BaseAIAdapter (T07-04)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
        backoff_base_delay: float = 1.0,
    ):
        super().__init__(
            technical_attempt_limit=technical_attempt_limit,
            semantic_attempt_limit=semantic_attempt_limit,
            backoff_base_delay=backoff_base_delay,
        )
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.client = None
        self.is_configured = False

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.is_configured = True
            except Exception as e:
                logger.warning("Could not initialize Gemini Client: %s", e)
                self.is_configured = False

    def invoke_raw(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Call Gemini model, translating transient transport/API errors to AITechnicalError."""
        if not self.is_configured or self.client is None:
            raise AITechnicalError(
                "GeminiAIAdapter is not configured: GEMINI_API_KEY is missing or client failed to initialize."
            )

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                response_mime_type="application/json",
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=config,
            )
            return response.text or ""
        except Exception as e:
            err_str = str(e).lower()
            if any(code in err_str for code in ("429", "resource_exhausted", "503", "unavailable", "timeout")):
                raise AITechnicalError(f"Transient Gemini API error: {e}") from e
            raise AITechnicalError(f"Gemini API invocation error: {e}") from e


__all__ = [
    "GeminiAIAdapter",
]
