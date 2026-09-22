from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
import pytest
from pydantic import ValidationError

from app import app
from src.comparator.field_comparator import (
    canonical_equal,
    compare_canonical_field,
    compare_seven_fields,
)
from src.llm.evidence_validator import validate_evidence_grounding
from src.models.audit import AuditRecord
from src.models.evidence import FieldEvidence
from src.models.extraction import ExtractedField
from src.models.ingestion import EmailRecord
from src.models.review import ReviewAction, ReviewUpdate
from src.normalization import normalize_gross_weight_kg, normalize_text
from src.parsers.usability_validator import assess_text_usability
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.stage1_classify import Stage1Classifier
from src.pipeline.stage2_role_binding import Stage2RoleBinder
from src.store.audit_store import AuditStore


DOC_SAMPLE_SI = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""

DOC_SAMPLE_BL = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
Description: ELECTRONIC GOODS
"""


def test_reg_001_zero_attachments_must_not_force_non_comparison():
    """REG-001 / EC-002: 0 attachments MUST NOT force non-comparison classification."""
    email = EmailRecord(
        email_id="reg_001_no_att",
        sender="shipper@example.com",
        subject="Draft BL check",
        body="Kindly compare attached SI and draft BL. Will send files shortly.",
        attachments=[],
    )
    store = AuditStore()
    orchestrator = PipelineOrchestrator(audit_store=store)

    audit_rec = orchestrator.process_email(email)

    assert audit_rec.classification.category == "document_comparison"
    assert audit_rec.classification.category != "general"
    assert audit_rec.state == "NEEDS_REVIEW"
    assert audit_rec.review is not None
    assert any(
        issue.logical_reason == "missing_attachment"
        for issue in audit_rec.review.issues
    )


def test_reg_002_zero_dataset_specific_shortcuts_in_src():
    """REG-002: AST scan verifying zero 'if email_id == \"email_xxx\":' branches in src/."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    violations: list[str] = []

    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check left vs comparators for email_id == 'email_xxx' pattern
                left_id = node.left.id if isinstance(node.left, ast.Name) else None
                for op, right in zip(node.ops, node.comparators):
                    if isinstance(op, ast.Eq):
                        right_val = (
                            right.value
                            if isinstance(right, ast.Constant)
                            and isinstance(right.value, str)
                            else None
                        )
                        right_id = (
                            right.id if isinstance(right, ast.Name) else None
                        )
                        left_val = (
                            node.left.value
                            if isinstance(node.left, ast.Constant)
                            and isinstance(node.left.value, str)
                            else None
                        )

                        if (
                            left_id == "email_id"
                            and right_val
                            and right_val.startswith("email_")
                        ):
                            violations.append(
                                f"{py_file.name}:{node.lineno} compares email_id == '{right_val}'"
                            )
                        if (
                            right_id == "email_id"
                            and left_val
                            and left_val.startswith("email_")
                        ):
                            violations.append(
                                f"{py_file.name}:{node.lineno} compares '{left_val}' == email_id"
                            )

    assert not violations, f"Detected dataset-specific conditional branches in src/: {violations}"


def test_reg_003_dynamic_metrics_check():
    """REG-003: Dynamic metrics check (zero hardcoded '520', '21', '63', '0.0%')."""
    from fastapi.testclient import TestClient

    store = AuditStore()
    client = TestClient(app)

    # Check root dynamic endpoint with 0 records
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_audited_emails"] == 0
    assert data["discrepancies_detected"] == 0

    # Ensure forbidden static mock literals are not in responses or API source
    routes_code = (
        Path(__file__).resolve().parents[1] / "src" / "api" / "routes.py"
    ).read_text(encoding="utf-8")
    for forbidden in ['"520"', '"21"', '"63"', '"0.0%"']:
        assert (
            forbidden not in routes_code
        ), f"Forbidden hardcoded metric {forbidden} found in src/api/routes.py"


def test_reg_004_no_undocumented_gross_weight_tolerance():
    """REG-004 / DEC-P06E: No undocumented +-1kg numeric tolerance."""
    si_val = Decimal("22000")
    bl_val = Decimal("22001")

    # Direct equality test
    assert not canonical_equal("gross_weight_kg", si_val, bl_val)

    # Comparator outcome test
    comparison = compare_canonical_field("gross_weight_kg", si_val, bl_val)
    assert comparison.outcome == "MISMATCH"


def test_reg_005_no_broad_company_suffix_stripping():
    """REG-005 / DEC-P06D: No broad company suffix stripping."""
    norm_corp = normalize_text("shipper", "ACME CORP")
    norm_corporation = normalize_text("shipper", "ACME CORPORATION")

    assert norm_corp.value == "ACME CORP"
    assert norm_corporation.value == "ACME CORPORATION"
    assert norm_corp.value != norm_corporation.value

    assert not canonical_equal(
        "shipper", norm_corp.value, norm_corporation.value
    )
    comparison = compare_canonical_field(
        "shipper", norm_corp.value, norm_corporation.value
    )
    assert comparison.outcome == "MISMATCH"


def test_reg_006_no_automatic_port_alias_equivalence():
    """REG-006 / DEC-P06C: No automatic port alias equivalence."""
    norm_shanghai = normalize_text("port_of_loading", "SHANGHAI")
    norm_port_shanghai = normalize_text("port_of_loading", "PORT OF SHANGHAI")

    assert norm_shanghai.value == "SHANGHAI"
    assert norm_port_shanghai.value == "PORT OF SHANGHAI"
    assert norm_shanghai.value != norm_port_shanghai.value

    assert not canonical_equal(
        "port_of_loading", norm_shanghai.value, norm_port_shanghai.value
    )
    comparison = compare_canonical_field(
        "port_of_loading", norm_shanghai.value, norm_port_shanghai.value
    )
    assert comparison.outcome == "MISMATCH"


def test_reg_007_no_fixed_char_count_ocr_trigger():
    """REG-007 / DEC-P02: No '<20 characters -> OCR' fixed rule (qualitative usability check)."""
    from src.models.document import ParserStatus

    short_valid_text = "SI: 22000kg 2x40HC"
    assert len(short_valid_text) == 18

    assessment = assess_text_usability(short_valid_text)
    assert assessment.is_usable is True
    assert assessment.is_scanned is False
    assert assessment.status == ParserStatus.SUCCESS


def test_reg_008_validated_fallback_prevents_unnecessary_hitl():
    """REG-008: Validated fallback output prevents unnecessary HITL."""
    from src.models.document import ParserResult, ParserStatus
    from src.parsers.vision_adapter import MockVisionAdapter, recover_document_if_needed

    # 1. Simulate initial unreadable / scanned document
    initial_unreadable = ParserResult(
        document_id="scan_doc.pdf",
        status=ParserStatus.UNREADABLE,
        text="",
        usable_for_extraction=False,
        is_scanned=True,
        diagnostic_evidence_ids=["diag_1"],
        attempt_ids=["att_1"],
    )

    # 2. Injected validated fallback adapter produces high-quality text layer
    mock_payload = {
        "text": DOC_SAMPLE_BL,
        "blocks": [
            {
                "text": DOC_SAMPLE_BL,
                "bbox": [10, 10, 500, 700],
                "confidence": 0.98,
            }
        ],
    }
    fallback_adapter = MockVisionAdapter(payload=mock_payload)

    # 3. Fallback recovery succeeds with validated output
    dummy_file = Path("scan_doc.pdf")
    recovered = recover_document_if_needed(
        initial_unreadable, dummy_file, adapter=fallback_adapter
    )

    assert recovered.status == ParserStatus.SUCCESS
    assert recovered.usable_for_extraction is True
    assert recovered.text is not None
    assert "ACME EXPORTS LTD" in recovered.text


def test_reg_009_reliable_partial_work_preserved_during_escalation():
    """REG-009 / DEC-AI-P04: Reliable partial work preserved during escalation."""
    si_fields = {
        "shipper": "ACME CORP",
        "consignee": "GLOBAL LLC",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SHANGHAI",
        "port_of_discharge": "ROTTERDAM",
        "container_count": 2,
        "gross_weight_kg": Decimal("22000"),
    }
    # BL matches 6 fields, but container_count is unresolved (None)
    bl_fields = {
        "shipper": "ACME CORP",
        "consignee": "GLOBAL LLC",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SHANGHAI",
        "port_of_discharge": "ROTTERDAM",
        "container_count": None,
        "gross_weight_kg": Decimal("22000"),
    }

    result = compare_seven_fields(si_fields, bl_fields)
    assert result.mismatch_detected is None
    assert result.outcome is None
    assert len(result.comparisons) == 6
    assert result.unresolved_fields == ["container_count"]
    assert all(c.outcome == "MATCH" for c in result.comparisons)


def test_reg_010_unresolved_comparison_never_emits_no_mismatch():
    """REG-010 / FR-011 / DC-03: Unresolved comparison never emits 'No mismatch detected'."""
    si_fields = {
        "shipper": "ACME CORP",
        "consignee": "GLOBAL LLC",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SHANGHAI",
        "port_of_discharge": "ROTTERDAM",
        "container_count": 2,
        "gross_weight_kg": Decimal("22000"),
    }
    bl_fields = {
        "shipper": "ACME CORP",
        "consignee": "GLOBAL LLC",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SHANGHAI",
        "port_of_discharge": "ROTTERDAM",
        "container_count": None,
        "gross_weight_kg": Decimal("22000"),
    }

    result = compare_seven_fields(si_fields, bl_fields)
    assert result.mismatch_detected is None
    assert "No mismatch detected" not in result.result_summary


def test_reg_011_confidence_score_does_not_bypass_evidence_verification():
    """REG-011: Confidence score does not bypass evidence verification."""
    source_text = "Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE"
    # Hallucinated quote with confidence 1.0
    ev = FieldEvidence(
        evidence_id="ev_hallucinated",
        source_type="document",
        source_id="doc_si",
        kind="text_span",
        quote="PACIFIC TRANS GLOBAL CORPORATION",
    )

    # Confidence is 1.0 (or HIGH), but quote is not in source_text
    is_valid = validate_evidence_grounding(
        ev, source_text=source_text, confidence=1.0
    )
    assert is_valid is False


def test_reg_012_direct_boolean_edit_on_mismatch_detected_rejected():
    """REG-012: Direct boolean edit on mismatch_detected rejected."""
    # ReviewUpdate schema strictly forbids extra fields including mismatch_detected
    with pytest.raises(ValidationError) as exc_info:
        ReviewUpdate(
            review_id="rev_1",
            expected_revision=1,
            actor_id="operator_1",
            action=ReviewAction.CONFIRM,
            rationale="Attempting manual override",
            mismatch_detected=False,  # type: ignore
        )
    assert "extra_forbidden" in str(exc_info.value)
