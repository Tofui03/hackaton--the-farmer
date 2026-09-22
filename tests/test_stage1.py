from __future__ import annotations

import pytest
from src.models.audit import AttemptTracker
from src.models.ingestion import (
    AttachmentReference,
    ClassificationResult,
    EmailCategory,
    EmailRecord,
)
from src.pipeline.stage1_classify import (
    Stage1Classifier,
    deterministic_classify_email,
    rule_based_classify,
)
from tests.mocks.mock_ai_adapter import MockAIAdapter


def test_pipe_cls_001_five_canonical_categories():
    """PIPE-CLS-001 / EC-001: 5 synthetic emails covering all 5 canonical categories."""
    classifier = Stage1Classifier()

    emails = [
        # 1. document_comparison
        {
            "email_id": "email_test_001",
            "from": "agent@shipline.com",
            "subject": "TO CONFIRM DOCS _ 5RSG-00133",
            "body": "Hi team, please find attached SI and draft BL for confirmation.",
            "attachments": ["doc1_SI.pdf", "doc1_BL.pdf"],
        },
        # 2. new_shipping_instruction
        {
            "email_id": "email_test_002",
            "from": "ops@freight.com",
            "subject": "REQUEST SI _ Booking 992834",
            "body": "Please assist to send SI for booking 992834 before vessel cutoff.",
            "attachments": [],
        },
        # 3. invoice_query
        {
            "email_id": "email_test_003",
            "from": "finance@client.com",
            "subject": "INVOICE QUERY - Local Charges and THC",
            "body": "Could you provide breakdown of telex release charges on invoice 44321?",
            "attachments": ["inv_44321.pdf"],
        },
        # 4. general
        {
            "email_id": "email_test_004",
            "from": "updates@carrier.com",
            "subject": "Vessel Schedule Update - Week 42",
            "body": "Notice of arrival and revised ETA update for vessel Ocean Star.",
            "attachments": [],
        },
        # 5. spam
        {
            "email_id": "email_test_005",
            "from": "promo@marketing.biz",
            "subject": "Increase your shipping revenue with this ONE weird trick",
            "body": "Exclusive offer: click here for free trial at our online casino.",
            "attachments": [],
        },
    ]

    expected_categories = [
        EmailCategory.DOCUMENT_COMPARISON,
        EmailCategory.NEW_SHIPPING_INSTRUCTION,
        EmailCategory.INVOICE_QUERY,
        EmailCategory.GENERAL,
        EmailCategory.SPAM,
    ]

    for email, expected_cat in zip(emails, expected_categories):
        res, evidence = classifier.classify(email)
        assert isinstance(res, ClassificationResult)
        assert res.state == "RESOLVED"
        assert res.category == expected_cat.value
        assert len(evidence) >= 1
        assert res.evidence_ids[0] == evidence[0].evidence_id
        assert evidence[0].source_id == email["email_id"]
        assert evidence[0].kind == "text_span"
        assert evidence[0].quote is not None


def test_pipe_cls_002_body_intent_prevails_over_subject():
    """PIPE-CLS-002: Subject is 'Invoice Query', but body says 'Compare attached SI and draft BL'.
    Body comparison intent prevails -> document_comparison.
    """
    classifier = Stage1Classifier()
    email = {
        "email_id": "email_pipe_002",
        "from": "shipper@co.com",
        "subject": "Invoice Query",
        "body": "Please ignore previous note. Compare attached SI and draft BL for any discrepancies.",
        "attachments": ["email_002_SI.txt", "email_002_BL.txt"],
    }

    res, evidence = classifier.classify(email)
    assert res.state == "RESOLVED"
    assert res.category == "document_comparison"
    assert res.category == EmailCategory.DOCUMENT_COMPARISON.value
    assert len(evidence) >= 1
    assert "Compare attached SI and draft BL" in evidence[0].quote


def test_pipe_cls_003_vague_subject_body_resolves():
    """PIPE-CLS-003: Subject is 'Update', body is 'Please see attached draft BL and SI'.
    Body intent resolves -> document_comparison.
    """
    classifier = Stage1Classifier()
    email = {
        "email_id": "email_pipe_003",
        "from": "shipper@co.com",
        "subject": "Update",
        "body": "Good morning. Please see attached draft BL and SI for verification.",
        "attachments": ["doc_si.pdf", "doc_bl.pdf"],
    }

    res, evidence = classifier.classify(email)
    assert res.state == "RESOLVED"
    assert res.category == "document_comparison"
    assert len(evidence) >= 1


def test_pipe_cls_004_and_reg_001_zero_attachments_preserves_comparison_intent():
    """PIPE-CLS-004 / EC-002 / REG-001: Zero attachments but body asks for SI/BL verification.
    Intent MUST remain document_comparison. Attachment count MUST NOT force email into general.
    """
    classifier = Stage1Classifier()

    # Case A: Explicit body verification request with empty attachments list
    email_zero_att = {
        "email_id": "email_zero_att",
        "from": "willy@company.com",
        "subject": "Draft BL check",
        "body": "Kindly compare attached SI and draft BL. Oops, will send files shortly.",
        "attachments": [],  # 0 attachments!
    }

    res, evidence = classifier.classify(email_zero_att)
    assert res.state == "RESOLVED"
    assert res.category == "document_comparison"
    assert res.category != "general"

    # Case B: 'TO CONFIRM DOCS' subject with 0 attachments (REG-001 specific trigger)
    email_to_confirm_zero_att = {
        "email_id": "email_to_confirm_zero",
        "from": "willy@company.com",
        "subject": "TO CONFIRM DOCS _ 5RSG-00133 _ CALLAO_PERU",
        "body": "Please find documents for review.",
        "attachments": [],  # 0 attachments!
    }

    res_confirm, _ = classifier.classify(email_to_confirm_zero_att)
    assert res_confirm.state == "RESOLVED"
    assert res_confirm.category == "document_comparison"
    assert res_confirm.category != "general"


def test_pipe_cls_005_invoice_query_with_attachments_bypasses_comparison():
    """PIPE-CLS-005 / FR-004: Attachments present, but email is an invoice inquiry.
    Classified as invoice_query. SI/BL verification is bypassed.
    """
    classifier = Stage1Classifier()
    email = {
        "email_id": "email_pipe_005",
        "from": "accounts@shipline.com",
        "subject": "RE: LOCAL CHARGES FOB - TELEX RELEASE CHARGES",
        "body": "Query on invoice 5250075931: is the THC / local charge included or billed separately?",
        "attachments": ["invoice_5250075931.pdf", "receipt.pdf"],
    }

    res, evidence = classifier.classify(email)
    assert res.state == "RESOLVED"
    assert res.category == "invoice_query"
    assert res.category != "document_comparison"


def test_pipe_cls_006_and_dc_001_ambiguous_intent_null_category():
    """PIPE-CLS-006 / DC-01 / HITL-RSN-005: Vague email with ambiguous text and generic attachments.
    Intent confidence low; category is None; state is NEEDS_REVIEW.
    """
    # 1. No AI adapter configured, ambiguous email
    vague_email = {
        "email_id": "email_vague_001",
        "from": "someone@somewhere.com",
        "subject": "Important message",
        "body": "Hello, please see this and advise on next steps.",
        "attachments": ["doc1.pdf"],
    }

    classifier = Stage1Classifier()
    res, evidence = classifier.classify(vague_email)
    assert res.state == "NEEDS_REVIEW"
    assert res.category is None
    assert res.confidence_indicator == "LOW"
    assert "Ambiguous" in res.reason

    # 2. Mock AI adapter explicitly returning null/ambiguous category (DC-01)
    mock_adapter = MockAIAdapter(
        default_response={
            "category": None,
            "reason": "Unable to determine clear business intent from context",
            "evidence": ["Important message"],
            "confidence_indicator": "LOW",
        }
    )
    classifier_with_ai = Stage1Classifier(ai_adapter=mock_adapter)
    res_ai, evidence_ai = classifier_with_ai.classify(vague_email)
    assert res_ai.state == "NEEDS_REVIEW"
    assert res_ai.category is None
    assert res_ai.confidence_indicator == "LOW"


def test_pipe_cls_007_and_dec_ai_p03_deterministic_fast_path_bypasses_ai():
    """PIPE-CLS-007 / DEC-AI-P03: Clean standard verification email with explicit keywords.
    Deterministic heuristics classify intent without invoking AI adapter.
    """
    mock_adapter = MockAIAdapter()
    classifier = Stage1Classifier(ai_adapter=mock_adapter)

    standard_email = {
        "email_id": "email_clean_standard",
        "from": "ops@shipping.com",
        "subject": "TO CONFIRM DOCS _ 5RSG-00133 _ CALLAO_PERU",
        "body": "Hi Najiha, attached are the SI and draft BL. Please check the details and confirm.",
        "attachments": ["email_001_SI.txt", "email_001_BL.txt"],
    }

    res, evidence = classifier.classify(standard_email)
    assert res.state == "RESOLVED"
    assert res.category == "document_comparison"

    # Strict invariant: AI adapter must NOT be called when deterministic path succeeds (DEC-AI-P03)
    assert mock_adapter.total_calls == 0


def test_ai_on_demand_classification_fallback():
    """Verify on-demand AI fallback for ambiguous email when AI returns HIGH/MEDIUM confidence."""
    mock_adapter = MockAIAdapter(
        default_response={
            "category": "new_shipping_instruction",
            "reason": "Customer is requesting shipping booking paperwork submission",
            "evidence": ["Please process this booking paperwork"],
            "confidence_indicator": "HIGH",
        }
    )
    classifier = Stage1Classifier(ai_adapter=mock_adapter)

    ambiguous_email = {
        "email_id": "email_ambig_002",
        "from": "forwarder@logistics.com",
        "subject": "Booking paperwork 88921",
        "body": "Please process this booking paperwork promptly.",
        "attachments": ["paperwork.pdf"],
    }

    tracker = AttemptTracker()
    res, evidence = classifier.classify(ambiguous_email, tracker=tracker)

    # Deterministic heuristics were inconclusive, so AI was called
    assert mock_adapter.total_calls == 1
    assert res.state == "RESOLVED"
    assert res.category == "new_shipping_instruction"
    assert res.confidence_indicator == "HIGH"
    assert len(evidence) >= 1
    assert tracker.total_provider_calls == 1


def test_email_record_contract_input():
    """Verify Stage1Classifier accepts formal EmailRecord Pydantic models."""
    email_record = EmailRecord(
        email_id="email_record_001",
        sender="billing@ports.com",
        subject="Demurrage & Detention Invoice",
        body="Attached please find the D & D charges invoice for container MSKU991823.",
        attachments=[
            AttachmentReference(
                document_id="doc_inv_1",
                path="attachments/doc_inv_1.pdf",
                mime_type="application/pdf",
            )
        ],
    )

    classifier = Stage1Classifier()
    res, evidence = classifier.classify(email_record)
    assert res.state == "RESOLVED"
    assert res.category == "invoice_query"
    assert len(evidence) >= 1
    assert evidence[0].source_id == "email_record_001"


def test_legacy_rule_based_classify_preserves_compatibility():
    """Verify rule_based_classify maintains backward compatibility while honoring REG-001."""
    # 0-attachment comparison email MUST NOT be rejected to GENERAL (REG-001)
    e_zero = {
        "subject": "TO CONFIRM DOCS _ REF123",
        "body": "Please check docs",
        "attachments": [],
    }
    assert rule_based_classify(e_zero) == "BL_COMPARISON"

    # Other legacy mappings
    e_inv = {"subject": "LOCAL CHARGES FOB", "body": "", "attachments": []}
    assert rule_based_classify(e_inv) == "INVOICE_QUERY"

    e_si = {"subject": "REQUEST SI FOR ORDER", "body": "", "attachments": []}
    assert rule_based_classify(e_si) == "SI_REQUEST"

    e_spam = {"subject": "CASINO FREE TRIAL", "body": "", "attachments": []}
    assert rule_based_classify(e_spam) == "SPAM"


def test_confidence_decoupling_high_confidence_ungrounded_rejects():
    """A. HIGH confidence + ungrounded result -> does NOT resolve merely because confidence is HIGH (REG-011)."""
    mock_adapter = MockAIAdapter(
        default_response={
            "category": "document_comparison",
            "reason": "AI confidently believes this is a comparison request",
            "evidence": ["Hallucinated quote that does not appear anywhere in this email"],
            "confidence_indicator": "HIGH",
        }
    )
    classifier = Stage1Classifier(ai_adapter=mock_adapter)
    ambiguous_email = {
        "email_id": "email_hallucinated_01",
        "from": "user@domain.com",
        "subject": "Inquiry regarding order",
        "body": "Could you please check our order status and advise.",
        "attachments": ["order.pdf"],
    }
    res, evidence = classifier.classify(ambiguous_email)
    assert res.state == "NEEDS_REVIEW"
    assert res.category is None
    assert "ungrounded evidence" in res.reason


def test_confidence_decoupling_low_confidence_grounded_resolves():
    """B. LOW confidence + valid canonical grounded output -> confidence alone does NOT force NEEDS_REVIEW."""
    mock_adapter = MockAIAdapter(
        default_response={
            "category": "invoice_query",
            "reason": "AI resolved statement inquiry to invoice_query",
            "evidence": ["verify settlement detail 4491"],
            "confidence_indicator": "LOW",
        }
    )
    classifier = Stage1Classifier(ai_adapter=mock_adapter)
    email = {
        "email_id": "email_low_conf_01",
        "from": "accounting@vendor.com",
        "subject": "Question about statement 4491",
        "body": "Hello, please verify settlement detail 4491 when possible.",
        "attachments": ["statement4491.pdf"],
    }
    res, evidence = classifier.classify(email)
    assert res.state == "RESOLVED"
    assert res.category == "invoice_query"
    assert res.confidence_indicator == "LOW"
    assert len(evidence) >= 1
    assert evidence[0].quote == "verify settlement detail 4491"


def test_confidence_decoupling_ambiguous_null_category_escalates():
    """C. Actual unresolved/ambiguous AI result -> category=None / NEEDS_REVIEW according to DC-01."""
    mock_adapter = MockAIAdapter(
        default_response={
            "category": None,
            "reason": "Intent is completely ambiguous between SI submission and general question",
            "evidence": ["status update request"],
            "confidence_indicator": "MEDIUM",
        }
    )
    classifier = Stage1Classifier(ai_adapter=mock_adapter)
    email = {
        "email_id": "email_ambig_cat_01",
        "from": "client@partner.com",
        "subject": "Status update",
        "body": "Please provide a status update request for our files.",
        "attachments": ["status.pdf"],
    }
    res, evidence = classifier.classify(email)
    assert res.state == "NEEDS_REVIEW"
    assert res.category is None
    assert res.confidence_indicator == "MEDIUM"
    assert "Ambiguous" in res.reason

