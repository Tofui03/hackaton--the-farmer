import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, GEMINI_MODEL, is_gemini_available

logger = logging.getLogger(__name__)


def clean_json_response(raw_text: str) -> Any:
    """Strip markdown formatting or extraneous text and parse JSON."""
    text = raw_text.strip()
    # Match markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting innermost or outermost JSON brackets
        array_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)
        if array_match:
            return json.loads(array_match.group(0))
        obj_match = re.search(r"\{[\s\S]*\}", text)
        if obj_match:
            return json.loads(obj_match.group(0))
        raise


class GeminiClient:
    """Robust client for Google Gemini API with retries and structured output handling."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Gemini Client: %s", e)

    def is_ready(self) -> bool:
        return self.client is not None

    def generate_json(
        self,
        system_instruction: str,
        user_prompt: str,
        parts: Optional[List[Any]] = None,
        max_retries: int = 4,
        backoff_factor: float = 2.0,
    ) -> Any:
        """Call Gemini model with system instruction and prompt, returning parsed JSON."""
        if not self.is_ready():
            raise RuntimeError(
                "GeminiClient is not ready: GEMINI_API_KEY is not set. "
                "Please configure GEMINI_API_KEY in your .env file."
            )

        contents = []
        if parts:
            contents.extend(parts)
        contents.append(user_prompt)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json",
        )

        last_error = None
        delay = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                raw_text = response.text or ""
                return clean_json_response(raw_text)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Gemini API attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    e,
                    delay,
                )
                time.sleep(delay)
                delay *= backoff_factor

        raise RuntimeError(f"Gemini API call failed after {max_retries} attempts: {last_error}")
