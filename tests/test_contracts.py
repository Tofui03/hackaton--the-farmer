from __future__ import annotations

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.models import (
    AttachmentReference,
    ClassificationResult,
    DocumentReference,
    DocumentRole,
    EmailCategory,
    EmailRecord,
    EvidenceKind,
    EvidenceLocation,
    FieldEvidence,
    ParserResult,
    ParserStatus,
)


# =============================================================================
# T02-01: Ingestion & Classification Contracts (CT-DATA-001)
# =============================================================================


def test_ct_data_001_valid_email_record():
    """Verify clean instantiation of EmailRecord and AttachmentReference."""
    att = AttachmentReference(
        document_id="doc_001",
        path="attachments/si.pdf",
        mime_type="application/pdf",
    )
    email = EmailRecord(
        email_id="em_001",
        sender="shipper@acme.com",
        subject="Shipping Documents",
        body="Please find SI and draft BL attached.",
        attachments=[att],
    )
    assert email.email_id == "em_001"
    assert len(email.attachments) == 1
    assert email.attachments[0].document_id == "doc_001"


def test_ct_data_001_email_record_extra_forbidden():
    """Verify strict extra-field rejection on EmailRecord."""
    with pytest.raises(ValidationError):
        EmailRecord(
            email_id="em_001",
            sender="a@b.com",
            subject="Subj",
            body="Body",
            attachments=[],
            unapproved_extra_field="rejected",
        )


def test_ct_data_001_attachment_reference_validation():
    """Verify AttachmentReference rejects empty ID or path."""
    with pytest.raises(ValidationError):
        AttachmentReference(document_id="", path="attachments/si.pdf")
    with pytest.raises(ValidationError):
        AttachmentReference(document_id="doc_001", path="")


def test_ct_data_001_canonical_categories():
    """Verify all 5 canonical categories are accepted and evaluation enums rejected."""
    valid_categories = [
        "document_comparison",
        "new_shipping_instruction",
        "invoice_query",
        "general",
        "spam",
    ]
    for cat in valid_categories:
        res = ClassificationResult(
            state="RESOLVED",
            category=cat,
            reason="Intent matched",
            evidence_ids=["ev_001"],
        )
        assert res.category == cat

    # Also test via Enum members
    for enum_val in EmailCategory:
        res = ClassificationResult(
            state="RESOLVED",
            category=enum_val,
            reason="Intent matched",
            evidence_ids=["ev_001"],
        )
        assert res.category == enum_val.value

    # Leaked evaluation enums must be rejected
    for eval_cat in ["BL_COMPARISON", "SI_REQUEST", "GENERAL", "SPAM"]:
        with pytest.raises(ValidationError):
            ClassificationResult(
                state="RESOLVED",
                category=eval_cat,
                reason="Intent matched",
                evidence_ids=["ev_001"],
            )


def test_ct_data_001_classification_nullability_and_resolution():
    """Verify category=None is allowed ONLY when state='NEEDS_REVIEW'."""
    # Valid unresolved review state
    unres = ClassificationResult(
        state="NEEDS_REVIEW",
        category=None,
        reason="Ambiguous email body",
        evidence_ids=[],
    )
    assert unres.category is None
    assert unres.state == "NEEDS_REVIEW"

    # Invalid: state='NEEDS_REVIEW' with category populated
    with pytest.raises(ValidationError, match="category exists only when resolved"):
        ClassificationResult(
            state="NEEDS_REVIEW",
            category="document_comparison",
            reason="Contradiction",
            evidence_ids=[],
        )

    # Invalid: state='RESOLVED' with category None
    with pytest.raises(ValidationError, match="category exists only when resolved"):
        ClassificationResult(
            state="RESOLVED",
            category=None,
            reason="Missing category",
            evidence_ids=["ev_001"],
        )

    # Invalid: state='RESOLVED' with empty evidence_ids
    with pytest.raises(ValidationError, match="resolved intent requires evidence"):
        ClassificationResult(
            state="RESOLVED",
            category="document_comparison",
            reason="No evidence",
            evidence_ids=[],
        )


# =============================================================================
# T02-02: Document Reference & Parser Result Models (DEC-P02, CT-DATA-009)
# =============================================================================


def test_parser_models_document_reference():
    """Verify DocumentReference validates roles and identification evidence."""
    ref_si = DocumentReference(
        document_id="doc_si_001",
        role="SI",
        identification_evidence_ids=["ev_id_001"],
    )
    assert ref_si.role == "SI"

    ref_bl = DocumentReference(
        document_id="doc_bl_001",
        role=DocumentRole.BL,
        identification_evidence_ids=["ev_id_002"],
    )
    assert ref_bl.role == "BL"

    ref_unk = DocumentReference(
        document_id="doc_unk_001",
        role="UNKNOWN",
        identification_evidence_ids=[],
    )
    assert ref_unk.role == "UNKNOWN"

    with pytest.raises(ValidationError):
        DocumentReference(
            document_id="doc_001",
            role="INVALID_ROLE",
            identification_evidence_ids=[],
        )


def test_parser_models_parser_result_success():
    """Verify ParserResult in SUCCESS status requires non-empty text."""
    pr = ParserResult(
        document_id="doc_001",
        status="SUCCESS",
        text="SHIPPING INSTRUCTION...",
        usable_for_extraction=True,
        diagnostic_evidence_ids=["ev_diag_001"],
        attempt_ids=["att_001"],
        page_count=2,
        is_scanned=False,
    )
    assert pr.status == "SUCCESS"
    assert pr.usable_for_extraction is True

    # Empty text under SUCCESS must fail
    with pytest.raises(ValidationError, match="empty extraction is not success/partial"):
        ParserResult(
            document_id="doc_001",
            status="SUCCESS",
            text="   ",
            usable_for_extraction=True,
            diagnostic_evidence_ids=[],
            attempt_ids=[],
        )


def test_parser_models_parser_result_unreadable():
    """Verify ParserResult in UNREADABLE status requires diagnostic evidence and unusable flag."""
    pr = ParserResult(
        document_id="doc_002",
        status=ParserStatus.UNREADABLE,
        text=None,
        usable_for_extraction=False,
        diagnostic_evidence_ids=["ev_err_corrupt"],
        attempt_ids=["att_002"],
        error_message="Stream truncated at EOF",
    )
    assert pr.status == "UNREADABLE"
    assert pr.usable_for_extraction is False

    # UNREADABLE with usable_for_extraction=True must fail
    with pytest.raises(ValidationError, match="failed parsing needs diagnostic context"):
        ParserResult(
            document_id="doc_002",
            status="UNREADABLE",
            text=None,
            usable_for_extraction=True,
            diagnostic_evidence_ids=["ev_001"],
            attempt_ids=[],
        )

    # UNREADABLE with empty diagnostic_evidence_ids must fail
    with pytest.raises(ValidationError, match="failed parsing needs diagnostic context"):
        ParserResult(
            document_id="doc_002",
            status="UNREADABLE",
            text=None,
            usable_for_extraction=False,
            diagnostic_evidence_ids=[],
            attempt_ids=[],
        )


# =============================================================================
# T02-03: FieldEvidence & EvidenceLocation Models (DC-05, CT-DATA-005)
# =============================================================================


def test_ct_data_005_text_span_evidence():
    """Verify text_span evidence requires quote."""
    ev = FieldEvidence(
        evidence_id="ev_text_001",
        source_type="document",
        source_id="doc_001",
        kind="text_span",
        quote="SHIPPER: ACME CORP",
        location=EvidenceLocation(page=1, section="Header"),
    )
    assert ev.kind == "text_span"
    assert ev.quote == "SHIPPER: ACME CORP"

    # text_span without quote must fail
    with pytest.raises(ValidationError, match="text/cell evidence requires source text"):
        FieldEvidence(
            evidence_id="ev_text_bad",
            source_type="document",
            source_id="doc_001",
            kind="text_span",
            quote=None,
        )


def test_ct_data_005_table_cell_evidence():
    """Verify table_cell evidence requires quote and table/row/column coordinates."""
    ev = FieldEvidence(
        evidence_id="ev_cell_001",
        source_type="document",
        source_id="doc_001",
        kind="table_cell",
        quote="22,000 KGS",
        location=EvidenceLocation(table="ManifestTable", row=2, column=3),
    )
    assert ev.kind == "table_cell"

    # Missing row/column must fail
    with pytest.raises(ValidationError, match="cell requires table and coordinates"):
        FieldEvidence(
            evidence_id="ev_cell_bad",
            source_type="document",
            source_id="doc_001",
            kind="table_cell",
            quote="22,000 KGS",
            location=EvidenceLocation(table="ManifestTable"),
        )


def test_ct_data_005_page_region_evidence():
    """Verify page_region requires page and ordered bounding box [x0, y0, x1, y1]."""
    ev = FieldEvidence(
        evidence_id="ev_reg_001",
        source_type="document",
        source_id="doc_001",
        kind=EvidenceKind.PAGE_REGION,
        location=EvidenceLocation(page=1, bbox=[0.1, 0.2, 0.5, 0.6]),
    )
    assert ev.location.bbox == [0.1, 0.2, 0.5, 0.6]

    # Inverted bbox (x0 >= x1) must fail
    with pytest.raises(ValidationError, match="bbox must be an ordered non-empty region"):
        EvidenceLocation(page=1, bbox=[0.8, 0.2, 0.3, 0.6])

    # Bbox without page must fail
    with pytest.raises(ValidationError, match="region requires page"):
        EvidenceLocation(bbox=[0.1, 0.2, 0.5, 0.6])


def test_ct_data_005_context_evidence_requires_detail():
    """Verify document_metadata, processing_error, human_review require detail text."""
    for kind in ["document_metadata", "processing_error", "human_review"]:
        ev = FieldEvidence(
            evidence_id=f"ev_{kind}",
            source_type="processing",
            source_id="doc_001",
            kind=kind,
            detail="Contextual error or review rationale",
        )
        assert ev.detail is not None

        # Missing detail must fail
        with pytest.raises(ValidationError, match="context evidence requires detail"):
            FieldEvidence(
                evidence_id=f"ev_{kind}_bad",
                source_type="processing",
                source_id="doc_001",
                kind=kind,
                detail=None,
            )


# =============================================================================
# Wave 0 Fixture Cross-Validation Against Real Models
# =============================================================================


def test_cross_validate_synthetic_email_fixtures():
    """Verify Wave 0 synthetic email fixtures parse cleanly into EmailRecord."""
    email_files = list(Path("tests/fixtures/emails").glob("syn_email_*.json"))
    assert len(email_files) >= 18

    for fpath in email_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        email_record = EmailRecord(**data)
        assert email_record.email_id == data["email_id"]
        assert len(email_record.attachments) == len(data.get("attachments", []))


def test_cross_validate_review_case_evidence_models():
    """Verify all FieldEvidence structures in Wave 0 review cases validate against FieldEvidence."""
    case_files = list(Path("tests/fixtures/review/cases").glob("case_*.json"))
    assert len(case_files) == 10

    total_evidence_validated = 0
    for fpath in case_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        for ev_raw in data.get("evidence", []):
            loc = None
            if ev_raw.get("location"):
                loc = EvidenceLocation(**ev_raw["location"])
            ev = FieldEvidence(
                evidence_id=ev_raw["evidence_id"],
                source_type=ev_raw["source_type"],
                source_id=ev_raw["source_id"],
                kind=ev_raw["kind"],
                quote=ev_raw.get("quote"),
                location=loc,
                detail=ev_raw.get("detail"),
            )
            assert ev.evidence_id == ev_raw["evidence_id"]
            total_evidence_validated += 1

    assert total_evidence_validated > 20


def test_cross_validate_ai_classification_fixtures():
    """Verify Wave 0 AI classification valid fixtures validate and invalid fixtures fail."""
    valid_cls_files = list(Path("tests/fixtures/ai/classification/valid").glob("*.json"))
    assert len(valid_cls_files) >= 7

    for fpath in valid_cls_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        cat = data.get("category")
        state = "RESOLVED" if cat is not None else "NEEDS_REVIEW"
        ev_ids = [f"ev_intent_{i}" for i in range(len(data.get("evidence", [])))]
        if state == "NEEDS_REVIEW" and not ev_ids:
            ev_ids = []
        elif state == "RESOLVED" and not ev_ids:
            ev_ids = ["ev_default"]

        cr = ClassificationResult(
            state=state,
            category=cat,
            reason=data.get("reason", "Parsed"),
            evidence_ids=ev_ids,
            confidence_indicator=data.get("confidence_indicator"),
        )
        assert cr.category == cat

    invalid_cls_files = list(Path("tests/fixtures/ai/classification/invalid").glob("*.json"))
    assert len(invalid_cls_files) >= 4

    for fpath in invalid_cls_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        ev_ids = [f"ev_{i}" for i in range(len(data.pop("evidence", [])))] or ["ev_default"]
        with pytest.raises(ValidationError):
            ClassificationResult(
                state="RESOLVED",
                evidence_ids=ev_ids,
                **data,
            )


def test_cross_validate_ai_role_resolution_fixtures():
    """Verify Wave 0 AI role resolution valid fixtures construct DocumentReference cleanly."""
    valid_role_files = list(Path("tests/fixtures/ai/role_resolution/valid").glob("*.json"))
    assert len(valid_role_files) >= 3

    for fpath in valid_role_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        docs = data.get("documents", {})
        for doc_id, doc_info in docs.items():
            role = doc_info.get("identified_role")
            if role in ("SI", "BL", "UNKNOWN"):
                doc_ref = DocumentReference(
                    document_id=doc_id,
                    role=role,
                    identification_evidence_ids=["ev_role_ident"],
                )
                assert doc_ref.role == role


def test_cross_validate_review_updates_added_evidence():
    """Verify all added_evidence entries in review updates validate against FieldEvidence."""
    update_files = list(Path("tests/fixtures/review/updates").glob("*.json"))
    assert len(update_files) >= 18

    total_added_evidence = 0
    for fpath in update_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        for ev_raw in data.get("added_evidence", []):
            loc = None
            if ev_raw.get("location"):
                loc = EvidenceLocation(**ev_raw["location"])
            ev = FieldEvidence(
                evidence_id=ev_raw["evidence_id"],
                source_type=ev_raw["source_type"],
                source_id=ev_raw["source_id"],
                kind=ev_raw["kind"],
                quote=ev_raw.get("quote"),
                location=loc,
                detail=ev_raw.get("detail"),
            )
            assert ev.evidence_id == ev_raw["evidence_id"]
            total_added_evidence += 1

    assert total_added_evidence >= 10

