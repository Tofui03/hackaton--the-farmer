from __future__ import annotations

from pathlib import Path
import pytest

from src.models.audit import AttemptTracker
from src.models.document import DocumentRole
from src.models.ingestion import AttachmentReference, EmailRecord
from src.models.review import LogicalReason
from src.pipeline.stage2_role_binding import (
    RoleBindingResult,
    Stage2RoleBinder,
    bind_attachment_roles,
)
from tests.mocks.mock_ai_adapter import MockAIAdapter


def test_par_role_001_deterministic_filename_role_binding():
    """PAR-ROLE-001 / DEC-AI-P03: Deterministic role binding for filenames shipment_SI.pdf, shipment_BL.pdf.
    Binds SI and BL without invoking AI adapter.
    """
    mock_adapter = MockAIAdapter()
    binder = Stage2RoleBinder(ai_adapter=mock_adapter)

    attachments = ["shipment_SI.pdf", "shipment_BL.pdf"]
    res = binder.bind_roles(attachments)

    assert isinstance(res, RoleBindingResult)
    assert res.state == "RESOLVED"
    assert res.si_doc is not None
    assert res.bl_doc is not None
    assert res.si_doc.document_id == "shipment_SI.pdf"
    assert res.si_doc.role == DocumentRole.SI
    assert res.bl_doc.document_id == "shipment_BL.pdf"
    assert res.bl_doc.role == DocumentRole.BL
    assert len(res.documents) == 2
    assert len(res.evidence) == 2

    # Invariant: AI adapter must NOT be called when deterministic evidence is conclusive (DEC-AI-P03)
    assert mock_adapter.total_calls == 0


def test_par_role_002_generic_filenames_header_or_ai_resolution():
    """PAR-ROLE-002: Generic filenames (doc1.pdf, doc2.pdf) resolved via AI semantic role analysis."""
    mock_adapter = MockAIAdapter(
        default_response={
            "document_roles": {
                "doc1.pdf": "SI",
                "doc2.pdf": "BL",
            },
            "rationale": "Header inspection indicates doc1 is Shipping Instruction and doc2 is Draft Bill of Lading",
            "confidence_indicator": "HIGH",
        }
    )
    binder = Stage2RoleBinder(ai_adapter=mock_adapter)

    attachments = ["doc1.pdf", "doc2.pdf"]
    tracker = AttemptTracker()
    res = binder.bind_roles(attachments, tracker=tracker)

    assert res.state == "RESOLVED"
    assert res.si_doc is not None
    assert res.bl_doc is not None
    assert res.si_doc.document_id == "doc1.pdf"
    assert res.si_doc.role == DocumentRole.SI
    assert res.bl_doc.document_id == "doc2.pdf"
    assert res.bl_doc.role == DocumentRole.BL

    # AI adapter was invoked because filenames were generic
    assert mock_adapter.total_calls == 1
    assert tracker.total_provider_calls == 1


def test_par_role_003_missing_si_escalates_missing_attachment():
    """PAR-ROLE-003 / FR-014: Draft BL attached, SI missing.
    Flags missing SI -> HITL: logical_reason = 'missing_attachment', expected_role = 'SI'.
    """
    binder = Stage2RoleBinder()
    attachments = ["shipment_BL.pdf"]
    res = binder.bind_roles(attachments)

    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.MISSING_ATTACHMENT
    assert res.review_issue is not None
    assert res.review_issue.logical_reason == LogicalReason.MISSING_ATTACHMENT
    assert res.review_issue.expected_role == DocumentRole.SI
    assert "shipment_BL.pdf" in res.review_issue.document_ids
    assert len(res.evidence) >= 1


def test_par_role_004_missing_bl_escalates_missing_attachment():
    """PAR-ROLE-004 / FR-014: SI attached, Draft BL missing.
    Flags missing BL -> HITL: logical_reason = 'missing_attachment', expected_role = 'BL'.
    """
    binder = Stage2RoleBinder()
    attachments = ["shipment_SI.pdf"]
    res = binder.bind_roles(attachments)

    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.MISSING_ATTACHMENT
    assert res.review_issue is not None
    assert res.review_issue.logical_reason == LogicalReason.MISSING_ATTACHMENT
    assert res.review_issue.expected_role == DocumentRole.BL
    assert "shipment_SI.pdf" in res.review_issue.document_ids
    assert len(res.evidence) >= 1


def test_par_role_005_duplicate_si_candidates_escalates():
    """PAR-ROLE-005 / FR-014: Two distinct SI candidate files attached.
    Detects duplicate role candidates -> HITL: wrong_or_uncertain_document_type.
    """
    binder = Stage2RoleBinder()
    attachments = ["booking_SI.pdf", "revised_SI.pdf", "shipment_BL.pdf"]
    res = binder.bind_roles(attachments)

    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE
    assert res.review_issue is not None
    assert res.review_issue.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE
    assert "booking_SI.pdf" in res.review_issue.document_ids
    assert "revised_SI.pdf" in res.review_issue.document_ids


def test_par_role_006_same_file_for_both_roles_rejected():
    """PAR-ROLE-006: Single file attempted for both SI and BL roles.
    Validation fails; assigns neither -> HITL: wrong_or_uncertain_document_type.
    """
    binder = Stage2RoleBinder()
    attachments = ["same_doc.pdf", "same_doc.pdf"]
    res = binder.bind_roles(attachments)

    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE
    assert res.review_issue is not None
    assert res.review_issue.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE


def test_par_role_007_irrelevant_document_rejected():
    """PAR-ROLE-007 / FR-014: Attachment is packing list / customs invoice instead of BL.
    Rejects attachment -> HITL: wrong_or_uncertain_document_type.
    """
    binder = Stage2RoleBinder()
    attachments = ["shipment_SI.pdf", "packing_list.pdf"]
    res = binder.bind_roles(attachments)

    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE
    assert res.review_issue is not None
    assert res.review_issue.logical_reason == LogicalReason.WRONG_OR_UNCERTAIN_DOCUMENT_TYPE
    assert "packing_list.pdf" in res.review_issue.document_ids


def test_par_role_008_corrupted_pdf_stream_escalates_unreadable(tmp_path):
    """PAR-ROLE-008 / FR-014 / NFR-003: Valid SI + Corrupted PDF BL.
    Detects corrupt stream -> HITL: logical_reason = 'unreadable_document'.
    """
    # Create valid text SI
    si_file = tmp_path / "test_SI.txt"
    si_file.write_text("Shipper: Vital Solutions\nConsignee: Al Gurg Stationery\n", encoding="utf-8")

    # Create corrupted PDF BL
    corrupt_bl = tmp_path / "corrupt_BL.pdf"
    corrupt_bl.write_bytes(b"%PDF-1.4\nJUNK NOT A REAL PDF STREAM\n%%EOF_CORRUPTED")

    binder = Stage2RoleBinder(base_dir=tmp_path)
    attachments = ["test_SI.txt", "corrupt_BL.pdf"]
    res = binder.bind_roles(attachments)

    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.UNREADABLE_DOCUMENT
    assert res.review_issue is not None
    assert res.review_issue.logical_reason == LogicalReason.UNREADABLE_DOCUMENT
    assert "corrupt_BL.pdf" in res.review_issue.document_ids


def test_stage2_role_binding_with_email_record():
    """Verify Stage2RoleBinder accepts formal EmailRecord contracts."""
    email = EmailRecord(
        email_id="email_binding_001",
        sender="willy@april.com",
        subject="TO CONFIRM DOCS",
        body="Please confirm SI and draft BL",
        attachments=[
            AttachmentReference(
                document_id="att_si_01",
                path="order_SI.pdf",
                mime_type="application/pdf",
            ),
            AttachmentReference(
                document_id="att_bl_01",
                path="order_BL.pdf",
                mime_type="application/pdf",
            ),
        ],
    )

    res = bind_attachment_roles(email)
    assert res.state == "RESOLVED"
    assert res.si_doc is not None
    assert res.bl_doc is not None
    assert res.si_doc.document_id == "att_si_01"
    assert res.bl_doc.document_id == "att_bl_01"


def test_zero_attachments_escalates_missing_attachment():
    """Verify empty attachments list escalates to missing_attachment."""
    res = bind_attachment_roles([])
    assert res.state == "NEEDS_REVIEW"
    assert res.logical_reason == LogicalReason.MISSING_ATTACHMENT
    assert res.review_issue is not None
    assert res.review_issue.expected_role is None
