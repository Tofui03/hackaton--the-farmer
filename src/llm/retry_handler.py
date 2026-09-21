from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional, Type, TypeVar
from pydantic import ValidationError

from src.models.audit import AttemptRecord, AttemptTracker
from src.models.review import StageType

logger = logging.getLogger(__name__)

STAGE_MAPPING: dict[str, StageType] = {
    "ingestion": "ingestion",
    "classification": "classification",
    "classify": "classification",
    "identification": "identification",
    "triage": "identification",
    "parsing": "parsing",
    "parse": "parsing",
    "ocr": "ocr",
    "extraction": "extraction",
    "extract": "extraction",
    "normalization": "normalization",
    "normalize": "normalization",
    "reliability": "reliability",
    "comparison": "comparison",
    "compare": "comparison",
    "review": "review",
    "audit": "review",
    "serialization": "serialization",
}

T = TypeVar("T")


class AIError(Exception):
    """Base exception for AI adapter errors."""
    pass


class AITechnicalError(AIError):
    """Transient technical or transport provider failure (HTTP 429, 503, timeout)."""
    pass


class AISemanticError(AIError):
    """Semantic or syntax output error (malformed JSON, invalid schema, bad enum)."""
    pass


class AIBudgetExhaustedError(AIError):
    """Exhaustion of technical, semantic, or nested provider call budget (capped at 6)."""
    pass


class AIRetryCoordinator:
    """Orchestrates bounded technical backoff and semantic re-prompting (DEC-AI-P01/P02, DC-06).
    
    Invariants:
    - technical_attempt_limit default: 3 (includes initial attempt)
    - semantic_attempt_limit default: 2 (includes initial attempt)
    - maximum nested provider calls cap: 6 (strictly <= 6)
    """

    def __init__(
        self,
        technical_attempt_limit: int = 3,
        semantic_attempt_limit: int = 2,
        backoff_base_delay: float = 0.0,
        backoff_multiplier: float = 2.0,
    ):
        if technical_attempt_limit * semantic_attempt_limit > 6:
            raise ValueError(
                f"Nested budget cap exceeded: {technical_attempt_limit} * {semantic_attempt_limit} > 6"
            )
        self.technical_attempt_limit = technical_attempt_limit
        self.semantic_attempt_limit = semantic_attempt_limit
        self.backoff_base_delay = backoff_base_delay
        self.backoff_multiplier = backoff_multiplier

    def execute(
        self,
        provider_fn: Callable[[str], str],
        parser_fn: Callable[[str], T],
        initial_prompt: str,
        tracker: Optional[AttemptTracker] = None,
        stage: str = "general",
        operation_id: str = "ai_op",
        provider_adapter_name: str = "BaseAIAdapter",
        model_name: str = "gemini",
    ) -> T:
        """Execute request under bounded technical and semantic retry loops with audit tracking."""
        current_prompt = initial_prompt
        semantic_attempt = 1
        call_count = 0
        max_total_calls = min(6, self.technical_attempt_limit * self.semantic_attempt_limit)
        canonical_stage = STAGE_MAPPING.get(stage.lower(), "classification")

        while semantic_attempt <= self.semantic_attempt_limit:
            technical_attempt = 1
            delay = self.backoff_base_delay

            while technical_attempt <= self.technical_attempt_limit:
                # Enforce strict invariant: total provider calls capped at 6 (AI-BUD-004)
                if call_count >= max_total_calls:
                    raise AIBudgetExhaustedError(
                        f"Total provider invocation budget cap of {max_total_calls} exhausted."
                    )

                call_count += 1
                att_num = call_count
                att_id = f"att_{operation_id}_{att_num}"
                kind = "primary" if call_count == 1 else (
                    "semantic_repair" if technical_attempt == 1 else "technical_retry"
                )

                try:
                    # 1. Invoke Provider
                    raw_response = provider_fn(current_prompt)

                    # 2. Parse and validate output
                    parsed_result = parser_fn(raw_response)

                    # Record successful attempt in tracker if provided
                    if tracker is not None:
                        record = AttemptRecord(
                            attempt_id=att_id,
                            operation_id=operation_id,
                            stage=canonical_stage,
                            kind=kind,
                            attempt_number=att_num,
                            outcome="SUCCEEDED",
                            provider_adapter=provider_adapter_name,
                            model_identifier=model_name,
                        )
                        tracker.attempts.append(record)
                        tracker.total_provider_calls = len(tracker.attempts)

                    return parsed_result

                except (AITechnicalError, TimeoutError, ConnectionError) as tech_err:
                    # Technical failure: backoff and retry within technical budget
                    if tracker is not None:
                        record = AttemptRecord(
                            attempt_id=att_id,
                            operation_id=operation_id,
                            stage=canonical_stage,
                            kind=kind,
                            attempt_number=att_num,
                            outcome="FAILED",
                            error_code=str(tech_err) or "technical_failure",
                            provider_adapter=provider_adapter_name,
                            model_identifier=model_name,
                        )
                        tracker.attempts.append(record)
                        tracker.total_provider_calls = len(tracker.attempts)

                    if technical_attempt == self.technical_attempt_limit:
                        # Technical retries exhausted for this semantic cycle
                        if semantic_attempt == self.semantic_attempt_limit or call_count >= max_total_calls:
                            raise AIBudgetExhaustedError(
                                f"Technical retry limit {self.technical_attempt_limit} exhausted: {tech_err}"
                            )
                        # Break to next semantic attempt
                        break

                    if delay > 0:
                        time.sleep(delay)
                        delay *= self.backoff_multiplier

                    technical_attempt += 1

                except (AISemanticError, ValidationError, json.JSONDecodeError, ValueError) as sem_err:
                    # Semantic failure: record and trigger re-prompt with error message
                    if tracker is not None:
                        record = AttemptRecord(
                            attempt_id=att_id,
                            operation_id=operation_id,
                            stage=canonical_stage,
                            kind=kind,
                            attempt_number=att_num,
                            outcome="INVALID",
                            error_code=str(sem_err) or "validation_error",
                            provider_adapter=provider_adapter_name,
                            model_identifier=model_name,
                        )
                        tracker.attempts.append(record)
                        tracker.total_provider_calls = len(tracker.attempts)

                    if semantic_attempt >= self.semantic_attempt_limit or call_count >= max_total_calls:
                        raise AIBudgetExhaustedError(
                            f"Semantic retry limit {self.semantic_attempt_limit} exhausted: {sem_err}"
                        )

                    # Update prompt with error message for semantic repair self-correction
                    current_prompt = (
                        f"{initial_prompt}\n\n"
                        f"[VALIDATION_ERROR]: Your previous response was rejected due to: {sem_err}. "
                        "Please correct the JSON output strictly adhering to the schema."
                    )
                    break

            semantic_attempt += 1

        raise AIBudgetExhaustedError("All technical and semantic retry budgets exhausted.")


__all__ = [
    "AIError",
    "AITechnicalError",
    "AISemanticError",
    "AIBudgetExhaustedError",
    "AIRetryCoordinator",
]
