from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import ValidationError

from src.llm.retry_handler import AIRetryCoordinator, AISemanticError
from src.llm.schemas import (
    DocumentFieldExtractionOutput,
    DocumentRoleResolutionOutput,
    EmailClassificationOutput,
)
from src.models.audit import AttemptTracker

logger = logging.getLogger(__name__)

T = TypeVar("T")


def clean_and_parse_json(raw_text: str) -> Any:
    """Extract and parse JSON object/array from model output, handling markdown code fences."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)


class BaseAIAdapter(ABC):
    """Abstract, provider-agnostic interface for structured AI operations (DEC-P01)."""

    def __init__(
        self,
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
        backoff_base_delay: float = 0.0,
    ):
        self.retry_coordinator = AIRetryCoordinator(
            technical_attempt_limit=technical_attempt_limit,
            semantic_attempt_limit=semantic_attempt_limit,
            backoff_base_delay=backoff_base_delay,
        )

    @abstractmethod
    def invoke_raw(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Call underlying AI provider returning raw text response."""
        pass

    def invoke_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
        tracker: Optional[AttemptTracker] = None,
        stage: str = "general",
        operation_id: str = "ai_structured_op",
        **kwargs: Any,
    ) -> T:
        """Invoke provider with bounded retry coordinator, strictly validating schema (DEC-P01)."""

        def _provider_fn(current_prompt: str) -> str:
            return self.invoke_raw(
                prompt=current_prompt,
                system_instruction=system_instruction,
                **kwargs,
            )

        def _parser_fn(raw_response: str) -> T:
            try:
                data = clean_and_parse_json(raw_response)
            except Exception as e:
                raise AISemanticError(f"Malformed JSON syntax: {e}") from e

            try:
                if isinstance(data, dict) and hasattr(schema, "model_validate"):
                    return schema.model_validate(data)
                elif isinstance(data, list) and hasattr(schema, "model_validate"):
                    return schema.model_validate(data)
                else:
                    return schema(**data) if isinstance(data, dict) else schema(data)
            except ValidationError as ve:
                raise AISemanticError(f"Schema validation error: {ve}") from ve
            except Exception as e:
                raise AISemanticError(f"Schema parsing error: {e}") from e

        return self.retry_coordinator.execute(
            provider_fn=_provider_fn,
            parser_fn=_parser_fn,
            initial_prompt=prompt,
            tracker=tracker,
            stage=stage,
            operation_id=operation_id,
            provider_adapter_name=self.__class__.__name__,
        )

    def classify_email(
        self,
        email_record: Any,
        tracker: Optional[AttemptTracker] = None,
        **kwargs: Any,
    ) -> EmailClassificationOutput:
        """Structured email intent classification (Stage 1 contract)."""
        prompt = (
            f"Classify the following email:\n"
            f"Subject: {getattr(email_record, 'subject', str(email_record))}\n"
            f"Body: {getattr(email_record, 'body', '')}\n"
        )
        return self.invoke_structured(
            prompt=prompt,
            schema=EmailClassificationOutput,
            tracker=tracker,
            stage="classify",
            operation_id=getattr(email_record, "email_id", "email_classify"),
            **kwargs,
        )

    def resolve_document_roles(
        self,
        attachments: Any,
        tracker: Optional[AttemptTracker] = None,
        **kwargs: Any,
    ) -> DocumentRoleResolutionOutput:
        """Structured document role resolution (Stage 2 contract)."""
        prompt = f"Resolve roles for attachments: {attachments}"
        return self.invoke_structured(
            prompt=prompt,
            schema=DocumentRoleResolutionOutput,
            tracker=tracker,
            stage="triage",
            operation_id="role_resolution",
            **kwargs,
        )

    def extract_fields(
        self,
        document_text: str,
        role: str,
        tracker: Optional[AttemptTracker] = None,
        **kwargs: Any,
    ) -> DocumentFieldExtractionOutput:
        """Structured 7-field extraction (Stage 3A contract)."""
        prompt = f"Extract shipping fields from {role} document:\n{document_text[:4000]}"
        return self.invoke_structured(
            prompt=prompt,
            schema=DocumentFieldExtractionOutput,
            tracker=tracker,
            stage="extract",
            operation_id=f"extract_{role}",
            **kwargs,
        )


__all__ = [
    "BaseAIAdapter",
    "clean_and_parse_json",
]
