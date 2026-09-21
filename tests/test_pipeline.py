import json
from pathlib import Path
import pytest
from src.pipeline.stage1_classify import rule_based_classify
from src.pipeline.stage2_extract import Stage2Extractor
from src.pipeline.stage3_compare import rule_based_compare_audit
from src.pipeline.validator import validate_submission_dict

BUNDLE_DIR = Path(__file__).resolve().parent.parent / "sdoc-hackathon-bundle"


def test_classification_heuristics():
    e1 = json.loads((BUNDLE_DIR / "inbox" / "email_001.json").read_text())
    assert rule_based_classify(e1) == "BL_COMPARISON"

    e2 = json.loads((BUNDLE_DIR / "inbox" / "email_002.json").read_text())
    assert rule_based_classify(e2) == "INVOICE_QUERY"

    e7 = json.loads((BUNDLE_DIR / "inbox" / "email_007.json").read_text())
    assert rule_based_classify(e7) == "SI_REQUEST"

    e15 = json.loads((BUNDLE_DIR / "inbox" / "email_015.json").read_text())
    assert rule_based_classify(e15) == "SPAM"


def test_stage2_missing_attachment():
    extractor = Stage2Extractor(BUNDLE_DIR)
    e507 = json.loads((BUNDLE_DIR / "inbox" / "email_507.json").read_text())
    ready, early = extractor.extract_comparison_pair(e507)
    assert ready is None
    assert early is not None
    assert early.hitl_escalation.needed is True
    assert early.hitl_escalation.reason == "missing_attachment"
    assert "email_507" in early.hitl_escalation.evidence or "attachment" in early.hitl_escalation.evidence

    comp = early.to_competition_dict()
    assert comp["status"] == "NEEDS_REVIEW"
    assert comp["review_reason"] == "missing_attachment"


def test_stage2_corrupted_pdf():
    extractor = Stage2Extractor(BUNDLE_DIR)
    e511 = json.loads((BUNDLE_DIR / "inbox" / "email_511.json").read_text())
    ready, early = extractor.extract_comparison_pair(e511)
    assert ready is None
    assert early is not None
    assert early.hitl_escalation.needed is True
    assert early.hitl_escalation.reason == "unreadable"

    comp = early.to_competition_dict()
    assert comp["status"] == "NEEDS_REVIEW"
    assert comp["review_reason"] == "unreadable"


def test_stage3_matching_pair():
    si_text = (BUNDLE_DIR / "attachments" / "email_001_SI.txt").read_text()
    bl_text = (BUNDLE_DIR / "attachments" / "email_001_BL.txt").read_text()
    rec = rule_based_compare_audit("email_001", si_text, bl_text)
    assert rec.mismatch_detected is False
    assert rec.result_summary == "No mismatch detected"
    assert len(rec.discrepancies) == 0

    comp = rec.to_competition_dict()
    assert comp["status"] == "OK"
    assert comp["has_defect"] is False
    assert comp["defect_fields"] == []


def test_stage3_discrepancy_pair():
    si_text = (BUNDLE_DIR / "attachments" / "email_025_SI.txt").read_text()
    bl_text = (BUNDLE_DIR / "attachments" / "email_025_BL.txt").read_text()
    rec = rule_based_compare_audit("email_025", si_text, bl_text)
    assert rec.mismatch_detected is True
    assert any(d.field == "container_count" for d in rec.discrepancies)

    comp = rec.to_competition_dict()
    assert comp["status"] == "MISMATCH"
    assert comp["has_defect"] is True
    assert "container_count" in comp["defect_fields"]


def test_validator():
    sample_path = BUNDLE_DIR / "sample_submission.json"
    sample_data = json.loads(sample_path.read_text())
    valid, errors = validate_submission_dict(sample_data, sample_data)
    assert valid is True
    assert len(errors) == 0
