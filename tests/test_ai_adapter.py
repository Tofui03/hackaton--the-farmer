from __future__ import annotations

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.llm.base_adapter import BaseAIAdapter
from src.llm.evidence_validator import validate_evidence_grounding
from src.llm.gemini_adapter import GeminiAIAdapter
from src.llm.retry_handler import (
    AIBudgetExhaustedError,
    AIRetryCoordinator,
    AISemanticError,
    AITechnicalError,
)
from src.llm.schemas import (
    ClassificationResponse,
    DocumentFieldExtractionOutput,
    DocumentRoleResolutionOutput,
    EmailClassificationOutput,
)
from src.models.audit import AttemptTracker
from src.models.evidence import EvidenceKind, EvidenceLocation, FieldEvidence
from tests.mocks.mock_ai_adapter import MockAIAdapter

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ai"


def test_base_ai_adapter_abstract_contract():
    """Requirement 21A: BaseAIAdapter is an abstract contract that cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseAIAdapter()  # Abstract class cannot be instantiated directly


def test_ai_adp_001_valid_structured_classification():
    """AI-ADP-001: Valid structured classification parses against Pydantic schema (DEC-P01)."""
    raw_payload = {
        "category": "document_comparison",
        "confidence": 0.95,
        "evidence_quote": "compare draft BL",
        "evidence": ["compare draft BL"],
    }
    adapter = MockAIAdapter(default_response=raw_payload)
    res = adapter.invoke_structured(
        prompt="Classify this email",
        schema=ClassificationResponse,
    )
    assert isinstance(res, ClassificationResponse)
    assert res.category == "document_comparison"
    assert res.confidence == 0.95
    assert res.evidence_quote == "compare draft BL"


def test_ai_adp_002_invalid_classification_enum_triggers_semantic_retry():
    """AI-ADP-002: Invalid classification enum triggers ValidationError and semantic repair."""
    # Attempt 1: Invalid enum UNKNOWN_INTENT; Attempt 2: Repaired valid enum general
    responses = [
        {"category": "UNKNOWN_INTENT"},
        {"category": "general", "reason": "Operational update"},
    ]
    adapter = MockAIAdapter(responses=responses, semantic_attempt_limit=2)
    tracker = AttemptTracker()

    res = adapter.invoke_structured(
        prompt="Classify this email",
        schema=EmailClassificationOutput,
        tracker=tracker,
    )
    assert isinstance(res, EmailClassificationOutput)
    assert res.category == "general"
    assert len(tracker.attempts) == 2
    assert tracker.attempts[0].outcome == "INVALID"
    assert tracker.attempts[1].outcome == "SUCCEEDED"


def test_ai_adp_003_missing_mandatory_schema_key_triggers_retry():
    """AI-ADP-003: Missing mandatory schema key (category) triggers retry and repair."""
    # Attempt 1: Missing category; Attempt 2: Valid payload
    responses = [
        {"confidence": 0.9, "reason": "Missing category"},
        {"category": "invoice_query", "reason": "Billing dispute"},
    ]
    adapter = MockAIAdapter(responses=responses, semantic_attempt_limit=2)
    tracker = AttemptTracker()

    res = adapter.invoke_structured(
        prompt="Classify email",
        schema=EmailClassificationOutput,
        tracker=tracker,
    )
    assert res.category == "invoice_query"
    assert len(tracker.attempts) == 2


def test_ai_adp_004_unexpected_hallucinated_keys_rejected():
    """AI-ADP-004: Unexpected extra keys are strictly rejected per schema (extra = 'forbid')."""
    payload_with_extra = {
        "category": "spam",
        "hallucinated_bl": "BL-12345",  # Forbidden extra field
    }
    adapter = MockAIAdapter(default_response=payload_with_extra, semantic_attempt_limit=1)
    tracker = AttemptTracker()

    with pytest.raises(AIBudgetExhaustedError):
        adapter.invoke_structured(
            prompt="Classify email",
            schema=EmailClassificationOutput,
            tracker=tracker,
        )
    assert len(tracker.attempts) == 1
    assert tracker.attempts[0].outcome == "INVALID"


def test_ai_adp_005_confidence_diagnostic_decoupling_with_ungrounded_quote():
    """AI-ADP-005 & REG-011: Confidence indicator cannot bypass source evidence validation."""
    source_text = "SHIPPING INSTRUCTION: VESSEL MAERSK TAURUS PORT SINGAPORE TO ROTTERDAM"
    # Extracted quote is hallucinated/absent from source_text
    hallucinated_quote = "VESSEL EVER GIVEN"

    evidence = FieldEvidence(
        evidence_id="ev_001",
        source_type="document",
        source_id="si.pdf",
        kind=EvidenceKind.TEXT_SPAN,
        quote=hallucinated_quote,
    )

    # Even with high confidence (0.99), ungrounded quote MUST be rejected
    is_valid = validate_evidence_grounding(
        evidence=evidence,
        source_text=source_text,
        confidence=0.99,
    )
    assert is_valid is False

    # Verbatim quote present in source_text passes validation
    valid_evidence = FieldEvidence(
        evidence_id="ev_002",
        source_type="document",
        source_id="si.pdf",
        kind=EvidenceKind.TEXT_SPAN,
        quote="MAERSK TAURUS",
    )
    assert validate_evidence_grounding(evidence=valid_evidence, source_text=source_text) is True


def test_ai_adp_006_and_ai_bud_001_transient_failure_technical_retry():
    """AI-ADP-006 & AI-BUD-001: Transient HTTP 429/503 triggers technical retry and succeeds on attempt 2."""
    responses = [
        AITechnicalError("HTTP 429 Rate Limit"),
        {"category": "document_comparison", "reason": "Compare SI and BL"},
    ]
    adapter = MockAIAdapter(
        responses=responses,
        technical_attempt_limit=3,
        backoff_base_delay=0.0,
    )
    tracker = AttemptTracker()

    res = adapter.invoke_structured(
        prompt="Classify email",
        schema=EmailClassificationOutput,
        tracker=tracker,
    )
    assert res.category == "document_comparison"
    assert len(tracker.attempts) == 2
    assert tracker.attempts[0].outcome == "FAILED"
    assert tracker.attempts[1].outcome == "SUCCEEDED"


def test_ai_bud_002_technical_attempt_exhaustion():
    """AI-BUD-002: Provider technical failure on all attempts exhausts technical budget exactly at limit."""
    responses = [
        TimeoutError("Connection timed out"),
        TimeoutError("Connection timed out"),
        TimeoutError("Connection timed out"),
    ]
    adapter = MockAIAdapter(
        responses=responses,
        technical_attempt_limit=3,
        semantic_attempt_limit=1,
    )
    tracker = AttemptTracker()

    with pytest.raises(AIBudgetExhaustedError) as exc_info:
        adapter.invoke_structured(
            prompt="Classify email",
            schema=EmailClassificationOutput,
            tracker=tracker,
        )

    assert "Technical retry limit 3 exhausted" in str(exc_info.value)
    assert len(tracker.attempts) == 3
    assert tracker.total_provider_calls == 3


def test_ai_bud_003_semantic_retry_on_malformed_json():
    """AI-BUD-003: Model returns malformed JSON syntax on call 1; succeeds with valid JSON on call 2."""
    responses = [
        "{ malformed json syntax unquoted: yes }",
        {"category": "new_shipping_instruction", "reason": "New SI submission"},
    ]
    adapter = MockAIAdapter(
        responses=responses,
        semantic_attempt_limit=2,
    )
    tracker = AttemptTracker()

    res = adapter.invoke_structured(
        prompt="Classify email",
        schema=EmailClassificationOutput,
        tracker=tracker,
    )
    assert res.category == "new_shipping_instruction"
    assert len(tracker.attempts) == 2
    assert tracker.attempts[0].outcome == "INVALID"
    assert tracker.attempts[1].outcome == "SUCCEEDED"


def test_ai_bud_004_nested_provider_call_budget_cap_at_six():
    """AI-BUD-004 & DC-06: Total provider invocations capped strictly at 6 (technical=3 * semantic=2)."""
    # 6 consecutive failures: alternating technical and semantic errors
    responses = [
        AITechnicalError("503 Service Unavailable"),
        TimeoutError("Timeout"),
        "{ malformed json }",  # Semantic attempt 1 fails at call 3
        AITechnicalError("503 Service Unavailable"),
        TimeoutError("Timeout"),
        TimeoutError("Timeout"),  # Call 6: Budget exhausted
        {"category": "general"},  # 7th call: must NEVER be executed
    ]
    adapter = MockAIAdapter(
        responses=responses,
        technical_attempt_limit=3,
        semantic_attempt_limit=2,
    )
    tracker = AttemptTracker()

    with pytest.raises(AIBudgetExhaustedError):
        adapter.invoke_structured(
            prompt="Classify email",
            schema=EmailClassificationOutput,
            tracker=tracker,
        )

    # Invariant: Total calls cannot exceed 6
    assert len(tracker.attempts) == 6
    assert tracker.total_provider_calls == 6


def test_ut_ext_013_evidence_hallucination_rejection():
    """UT-EXT-013: Extracted quote string that does not exist in parsed text is rejected."""
    parsed_si_text = "CONSIGNEE: NORDIC GLOBAL TRADING BV ROTTERDAM"
    
    # Non-existent quote
    assert validate_evidence_grounding(
        evidence="CONSIGNEE: PACIFIC LOGISTICS",
        source_text=parsed_si_text,
    ) is False

    # Verbatim quote
    assert validate_evidence_grounding(
        evidence="NORDIC GLOBAL TRADING BV",
        source_text=parsed_si_text,
    ) is True


def test_spatial_evidence_bounding_box_validation():
    """Tests coordinate grounding validation for page_region and table_cell evidence."""
    # Valid page_region
    valid_region = FieldEvidence(
        evidence_id="ev_reg_1",
        source_type="document",
        source_id="doc1",
        kind=EvidenceKind.PAGE_REGION,
        location=EvidenceLocation(page=1, bbox=[0.1, 0.1, 0.5, 0.5]),
    )
    assert validate_evidence_grounding(valid_region, page_count=2) is True

    # Invalid page exceeding page_count
    assert validate_evidence_grounding(valid_region, page_count=0) is False


def test_gemini_adapter_interface_and_offline_safety():
    """T07-04: GeminiAIAdapter implements BaseAIAdapter and handles missing API key cleanly."""
    adapter = GeminiAIAdapter(api_key=None)
    assert isinstance(adapter, BaseAIAdapter)
    assert adapter.is_configured is False

    # Calling invoke_raw offline raises AITechnicalError without crashing unhandled
    with pytest.raises(AITechnicalError) as exc_info:
        adapter.invoke_raw("Test prompt")
    assert "GEMINI_API_KEY is missing" in str(exc_info.value)


def test_zero_tests_fixtures_path_dependencies_in_src():
    """Governance Requirement 21L: Proves src/ has zero references to tests/ or tests/fixtures."""
    src_dir = Path(__file__).resolve().parent.parent / "src"
    prohibited_tokens = ["tests/fixtures", "tests\\\\fixtures", "tests/"]
    matches = []

    for path in src_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in prohibited_tokens:
            if token in text:
                matches.append((str(path), token))

    assert len(matches) == 0, f"Found prohibited test path dependencies in src: {matches}"
