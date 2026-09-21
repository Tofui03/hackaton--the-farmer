from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.models.document import ParserResult, ParserStatus
from src.parsers.pdf_parser import PdfParser
from src.parsers.vision_adapter import (
    BaseVisionAdapter,
    MockVisionAdapter,
    normalize_pixel_box,
    recover_document_if_needed,
    validate_bounding_box,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "documents"
AI_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ai" / "ocr"


def test_ai_ocr_001_scanned_clean_document_recovery():
    """AI-OCR-001: Scanned clean document recovery via mocked adapter (FR-008, DEC-P02).
    
    1. PdfParser parses scanned PDF -> produces is_scanned=True, usable_for_extraction=False
    2. recover_document_if_needed invokes OCR recovery
    3. Produces ParserResult with status SUCCESS, usable_for_extraction=True, is_scanned=True
    4. Text and normalized bounding boxes are recovered and validated
    """
    scanned_path = FIXTURES_DIR / "scanned" / "scan_si_001_readable.pdf"
    assert scanned_path.exists(), f"Fixture missing: {scanned_path}"

    # Step 1: Ordinary parse produces unreadable scanned document
    pdf_parser = PdfParser()
    initial_res = pdf_parser.parse(scanned_path)
    assert isinstance(initial_res, ParserResult)
    assert initial_res.is_scanned is True
    assert initial_res.usable_for_extraction is False
    assert initial_res.status == ParserStatus.UNREADABLE

    # Step 2: Targeted OCR recovery invocation
    adapter = MockVisionAdapter()
    recovered_res = recover_document_if_needed(initial_res, scanned_path, adapter=adapter)

    # Step 3: Verified recovered state
    assert isinstance(recovered_res, ParserResult)
    assert recovered_res.status == ParserStatus.SUCCESS
    assert recovered_res.usable_for_extraction is True
    assert recovered_res.is_scanned is True
    assert recovered_res.text is not None
    assert "MARITIME EXPORT CARGO CORP" in recovered_res.text
    assert "ROTTERDAM" in recovered_res.text
    assert "16500 KG" in recovered_res.text

    # Step 4: Metadata provenance and bounding box verification
    assert recovered_res.metadata["recovery_method"] == "ocr_vision"
    assert recovered_res.metadata["adapter"] == "MockVisionAdapter"
    assert "ocr_boxes" in recovered_res.metadata

    boxes = json.loads(recovered_res.metadata["ocr_boxes"])
    assert "shipper" in boxes
    assert "gross_weight_kg" in boxes
    for field_name, bbox in boxes.items():
        assert len(bbox) == 4
        assert validate_bounding_box(bbox) is True, f"Invalid box for {field_name}: {bbox}"


def test_ai_ocr_002_essential_fields_readable_footer_corrupted():
    """AI-OCR-002: Essential fields readable, footer corrupted (DEC-AI-P04).
    
    When terms & conditions or footer disclaimers are blurry/illegible (footer_terms_legible=false),
    but all 7 comparison fields are sharp, document is accepted with status PARTIAL
    and usable_for_extraction=True without escalating to HITL.
    """
    degraded_path = FIXTURES_DIR / "scanned" / "scan_si_002_degraded.pdf"
    assert degraded_path.exists(), f"Fixture missing: {degraded_path}"

    initial_res = PdfParser().parse(degraded_path)
    assert initial_res.is_scanned is True

    adapter = MockVisionAdapter()
    recovered_res = recover_document_if_needed(initial_res, degraded_path, adapter=adapter)

    assert isinstance(recovered_res, ParserResult)
    assert recovered_res.status == ParserStatus.PARTIAL
    assert recovered_res.usable_for_extraction is True
    assert recovered_res.is_scanned is True
    assert recovered_res.metadata.get("footer_terms_legible") == "false"
    assert recovered_res.metadata.get("partial_degradation") == "footer_terms_illegible"
    assert "MARITIME EXPORT CARGO CORP" in recovered_res.text
    assert "16500 KG" in recovered_res.text


def test_ai_ocr_003_unreadable_mandatory_field():
    """AI-OCR-003: Unreadable mandatory field flagged without guessing (FR-014).
    
    When an essential mandatory field (e.g. container_count) is stained or illegible,
    OCR recovery records diagnostic evidence and unreadable field metadata without
    fabricating or synthesizing a value.
    """
    fixture_path = AI_FIXTURES_DIR / "failures" / "ocr_unreadable_mandatory_field.json"
    assert fixture_path.exists()

    dummy_path = Path("scan_si_stained.pdf")
    adapter = MockVisionAdapter(fixture_path=fixture_path)
    res = adapter.recover_document(dummy_path, document_id="scan_si_stained.pdf")

    assert isinstance(res, ParserResult)
    assert "unreadable_fields" in res.metadata
    unreadable = json.loads(res.metadata["unreadable_fields"])
    assert "container_count" in unreadable
    assert any("unreadable_container_count" in diag for diag in res.diagnostic_evidence_ids)


def test_ai_ocr_004_conflicting_ocr_interpretations():
    """AI-OCR-004: Conflicting candidate readings preserved without guessing (FR-014, DC-02).
    
    When ambiguous scan yields conflicting candidate readings (e.g. 22500 vs 28500),
    OCR recovery records candidate values in diagnostic metadata without silently picking one.
    """
    fixture_path = AI_FIXTURES_DIR / "failures" / "ocr_conflicting_readings.json"
    assert fixture_path.exists()

    dummy_path = Path("scan_si_lowres.pdf")
    adapter = MockVisionAdapter(fixture_path=fixture_path)
    res = adapter.recover_document(dummy_path, document_id="scan_si_lowres.pdf")

    assert isinstance(res, ParserResult)
    assert "conflicting_fields" in res.metadata
    conflicts = json.loads(res.metadata["conflicting_fields"])
    assert "gross_weight_kg" in conflicts
    assert conflicts["gross_weight_kg"] == ["22500 KG", "28500 KG"]
    assert any("conflict_gross_weight_kg" in diag for diag in res.diagnostic_evidence_ids)


def test_ai_ocr_005_vision_provider_unavailable_with_bounded_retry_recovery():
    """AI-OCR-005: Transient provider error with bounded retry recovery (DEC-AI-P01, REG-008).
    
    Simulates transient errors (429 Rate Limit, 503 Unavailable) on attempts 1 and 2,
    succeeding on attempt 3 within technical_attempt_limit = 3.
    """
    dummy_path = Path("scan_si_001_readable.pdf")
    adapter = MockVisionAdapter(
        simulated_faults=["rate_limit_429", "provider_unavailable_503"],
        technical_attempt_limit=3,
    )
    res = adapter.recover_document(dummy_path, document_id="scan_si_001_readable.pdf")

    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    # Exactly 3 attempts recorded
    assert len(res.attempt_ids) == 3
    assert res.attempt_ids == [
        "att_ocr_scan_si_001_readable.pdf_1",
        "att_ocr_scan_si_001_readable.pdf_2",
        "att_ocr_scan_si_001_readable.pdf_3",
    ]


def test_ai_ocr_006_total_provider_failure_and_exhaustion():
    """AI-OCR-006: Total provider failure and fallback exhaustion (FR-014, DEC-AI-P01).
    
    When retries are exhausted across all technical attempts, gracefully catches exhaustion,
    returns status=UNREADABLE, usable_for_extraction=False, error_message='processing_or_provider_failure',
    without crashing.
    """
    dummy_path = Path("scan_si_001_readable.pdf")
    adapter = MockVisionAdapter(
        simulated_faults=[
            "provider_unavailable_503",
            "provider_unavailable_503",
            "provider_unavailable_503",
        ],
        technical_attempt_limit=3,
    )
    res = adapter.recover_document(dummy_path, document_id="scan_si_001_readable.pdf")

    assert isinstance(res, ParserResult)
    assert res.status == ParserStatus.UNREADABLE
    assert res.usable_for_extraction is False
    assert res.text is None
    assert res.error_message == "processing_or_provider_failure"
    assert len(res.attempt_ids) == 3
    assert any("provider_failure_exhausted" in diag for diag in res.diagnostic_evidence_ids)


def test_vector_pdf_bypasses_ocr_recovery():
    """Routing Invariant: Usable vector PDF completely bypasses OCR recovery.
    
    Verifies that when ordinary parse succeeds with usable_for_extraction=True and
    is_scanned=False, OCR adapter is never called (call_count remains 0).
    """
    clean_pdf_path = FIXTURES_DIR / "pdf" / "pdf_si_001_clean.pdf"
    assert clean_pdf_path.exists()

    initial_res = PdfParser().parse(clean_pdf_path)
    assert initial_res.status == ParserStatus.SUCCESS
    assert initial_res.usable_for_extraction is True
    assert initial_res.is_scanned is False

    adapter = MockVisionAdapter()
    dispatched_res = recover_document_if_needed(initial_res, clean_pdf_path, adapter=adapter)

    # Invariant: Dispatched result is identical to initial parse, adapter was never called
    assert dispatched_res is initial_res
    assert adapter.call_count == 0


def test_geometric_coordinate_validation():
    """Validates bounding box geometry invariants (T02-02, FieldEvidence).
    
    Tests normalized coordinate constraints and pixel normalization.
    """
    # Valid normalized bbox: 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
    assert validate_bounding_box([0.1, 0.2, 0.8, 0.9]) is True
    assert validate_bounding_box([0.0, 0.0, 1.0, 1.0]) is True

    # Inverted geometry
    assert validate_bounding_box([0.8, 0.2, 0.1, 0.9]) is False  # x0 > x1
    assert validate_bounding_box([0.1, 0.9, 0.8, 0.2]) is False  # y0 > y1

    # Out of range coordinates
    assert validate_bounding_box([-0.1, 0.2, 0.8, 0.9]) is False  # negative
    assert validate_bounding_box([0.1, 0.2, 1.1, 0.9]) is False   # > 1.0

    # Wrong length
    assert validate_bounding_box([0.1, 0.2, 0.8]) is False

    # Pixel normalization
    pixel_box = {"xmin": 220, "ymin": 116, "xmax": 532, "ymax": 130}
    norm = normalize_pixel_box(pixel_box, width=600, height=800)
    assert norm is not None
    assert norm == [round(220/600, 4), round(116/800, 4), round(532/600, 4), round(130/800, 4)]
    assert validate_bounding_box(norm) is True

    # Invalid raster dimensions
    assert normalize_pixel_box(pixel_box, width=0, height=800) is None
    assert normalize_pixel_box(pixel_box, width=600, height=-100) is None


def test_provider_confidence_is_diagnostic_only():
    """Confidence indicator is retained as diagnostic metadata only and does not bypass validation."""
    fixture_data = {
        "document_id": "scan_test_low_conf.pdf",
        "fields": {
            "shipper": {
                "raw_value": "GLOBAL TRADERS LTD",
                "status": "FOUND",
            }
        },
        "confidence_indicator": "LOW",
    }
    adapter = MockVisionAdapter(fixture_data=fixture_data)
    res = adapter.recover_document(Path("scan_test_low_conf.pdf"))

    assert res.status == ParserStatus.SUCCESS
    assert res.usable_for_extraction is True
    # Confidence is recorded in metadata
    assert res.metadata["confidence"] == "LOW"
