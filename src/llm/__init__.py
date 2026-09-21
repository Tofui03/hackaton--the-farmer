from __future__ import annotations

from src.llm.base_adapter import BaseAIAdapter, clean_and_parse_json
from src.llm.client import GeminiClient, clean_json_response
from src.llm.evidence_validator import validate_evidence_grounding
from src.llm.gemini_adapter import GeminiAIAdapter
from src.llm.prompts import (
    BATCH_CLASSIFY_SYSTEM_PROMPT,
    DOC_COMPARE_SYSTEM_PROMPT,
    build_batch_classify_prompt,
    build_doc_compare_prompt,
)
from src.llm.retry_handler import (
    AIBudgetExhaustedError,
    AIError,
    AIRetryCoordinator,
    AISemanticError,
    AITechnicalError,
)
from src.llm.schemas import (
    ClassificationResponse,
    DocumentFieldExtractionOutput,
    DocumentRoleResolutionOutput,
    EmailClassificationOutput,
    ExtractedFieldRaw,
)

__all__ = [
    "BaseAIAdapter",
    "GeminiAIAdapter",
    "GeminiClient",
    "clean_json_response",
    "clean_and_parse_json",
    "AIRetryCoordinator",
    "AIError",
    "AITechnicalError",
    "AISemanticError",
    "AIBudgetExhaustedError",
    "validate_evidence_grounding",
    "EmailClassificationOutput",
    "ClassificationResponse",
    "DocumentRoleResolutionOutput",
    "DocumentFieldExtractionOutput",
    "ExtractedFieldRaw",
    "BATCH_CLASSIFY_SYSTEM_PROMPT",
    "DOC_COMPARE_SYSTEM_PROMPT",
    "build_batch_classify_prompt",
    "build_doc_compare_prompt",
]
