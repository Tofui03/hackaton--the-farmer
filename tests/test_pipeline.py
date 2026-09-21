import json
from pathlib import Path
import pytest
from src.pipeline.stage1_classify import rule_based_classify
from src.pipeline.stage2_extract import Stage2Extractor
from src.pipeline.stage3_compare import rule_based_compare
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
    assert early["status"] == "NEEDS_REVIEW"
    assert early["review_reason"] == "missing_attachment"


def test_stage2_corrupted_pdf():
    extractor = Stage2Extractor(BUNDLE_DIR)
    e511 = json.loads((BUNDLE_DIR / "inbox" / "email_511.json").read_text())
    ready, early = extractor.extract_comparison_pair(e511)
    assert ready is None
    assert early is not None
    assert early["status"] == "NEEDS_REVIEW"
    assert early["review_reason"] == "unreadable"


def test_stage3_matching_pair():
    si_text = (BUNDLE_DIR / "attachments" / "email_001_SI.txt").read_text()
    bl_text = (BUNDLE_DIR / "attachments" / "email_001_BL.txt").read_text()
    res = rule_based_compare(si_text, bl_text)
    assert res["status"] == "OK"
    assert res["has_defect"] is False
    assert res["defect_fields"] == []


def test_stage3_discrepancy_pair():
    si_text = (BUNDLE_DIR / "attachments" / "email_025_SI.txt").read_text()
    bl_text = (BUNDLE_DIR / "attachments" / "email_025_BL.txt").read_text()
    res = rule_based_compare(si_text, bl_text)
    assert res["status"] == "MISMATCH"
    assert res["has_defect"] is True
    assert "container_count" in res["defect_fields"]


def test_validator():
    sample_path = BUNDLE_DIR / "sample_submission.json"
    sample_data = json.loads(sample_path.read_text())
    valid, errors = validate_submission_dict(sample_data, sample_data)
    assert valid is True
    assert len(errors) == 0
