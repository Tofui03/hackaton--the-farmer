"""Focused test suite for environment-gated UAT demo seed mechanism."""
from __future__ import annotations

import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app import app
from src.demo.uat_seed import (
    DEMO_EMAIL_IDS,
    DEMO_GENERAL_ID,
    DEMO_MATCH_ID,
    DEMO_MISMATCH_ID,
    DEMO_REVIEW_ID,
    is_uat_demo_seed_enabled,
    maybe_seed_uat_demo_records,
    seed_uat_demo_records,
)
from src.models.audit import AuditRecord
from src.store.audit_store import AuditStore


def test_seed_flag_parsing_cases():
    """Test SDOC_UAT_DEMO_SEED environment variable parsing."""
    # Absent
    with patch.dict(os.environ, {}, clear=True):
        assert is_uat_demo_seed_enabled() is False

    # False / 0 / empty
    for false_val in ["0", "false", "False", "no", "off", ""]:
        with patch.dict(os.environ, {"SDOC_UAT_DEMO_SEED": false_val}):
            assert is_uat_demo_seed_enabled() is False

    # True / 1 / yes / on
    for true_val in ["1", "true", "True", "TRUE", "yes", "on"]:
        with patch.dict(os.environ, {"SDOC_UAT_DEMO_SEED": true_val}):
            assert is_uat_demo_seed_enabled() is True


def test_flag_absent_does_not_seed():
    """When flag is absent, maybe_seed_uat_demo_records does not seed."""
    store = AuditStore()
    with patch.dict(os.environ, {}, clear=True):
        res = maybe_seed_uat_demo_records(store)
        assert res is None
        assert store.count() == 0


def test_flag_false_does_not_seed():
    """When flag is false, maybe_seed_uat_demo_records does not seed."""
    store = AuditStore()
    with patch.dict(os.environ, {"SDOC_UAT_DEMO_SEED": "0"}):
        res = maybe_seed_uat_demo_records(store)
        assert res is None
        assert store.count() == 0


def test_flag_true_seeds_expected_demo_records():
    """When flag is enabled, expected demo IDs exist and validate against AuditRecord."""
    store = AuditStore()
    with patch.dict(os.environ, {"SDOC_UAT_DEMO_SEED": "1"}):
        seeded = maybe_seed_uat_demo_records(store)
        assert seeded is not None
        assert len(seeded) == 4
        assert store.count() == 4

        for eid in DEMO_EMAIL_IDS:
            rec = store.get(eid)
            assert rec is not None
            # Validate against strict Pydantic AuditRecord model
            assert isinstance(rec, AuditRecord)
            AuditRecord.model_validate(rec.model_dump())


def test_seeded_match_record_properties():
    """Verify uat-demo-match has all 7 matching fields and correct status."""
    store = AuditStore()
    seed_uat_demo_records(store)

    rec = store.get(DEMO_MATCH_ID)
    assert rec is not None
    assert rec.classification.category == "document_comparison"
    assert rec.state == "COMPLETE"
    assert rec.outcome == "MATCH"
    assert rec.mismatch_detected is False
    assert rec.result_summary == "No mismatch detected"
    assert len(rec.discrepancies) == 0
    assert rec.review is None
    assert len(rec.documents) == 2
    assert len(rec.extractions) == 2


def test_seeded_mismatch_record_properties():
    """Verify uat-demo-mismatch has exactly container_count mismatch."""
    store = AuditStore()
    seed_uat_demo_records(store)

    rec = store.get(DEMO_MISMATCH_ID)
    assert rec is not None
    assert rec.classification.category == "document_comparison"
    assert rec.state == "COMPLETE"
    assert rec.outcome == "MISMATCH"
    assert rec.mismatch_detected is True
    assert len(rec.discrepancies) == 1
    assert rec.discrepancies[0].field == "container_count"
    assert rec.discrepancies[0].si_value == 3
    assert rec.discrepancies[0].bl_value == 4


def test_seeded_review_record_properties():
    """Verify uat-demo-review keeps mismatch_detected=None and preserves partial work."""
    store = AuditStore()
    seed_uat_demo_records(store)

    rec = store.get(DEMO_REVIEW_ID)
    assert rec is not None
    assert rec.classification.category == "document_comparison"
    assert rec.state == "NEEDS_REVIEW"
    assert rec.outcome is None
    assert rec.mismatch_detected is None
    assert rec.review is not None
    assert rec.review.state == "OPEN"
    assert any(
        issue.logical_reason == "missing_required_value"
        for issue in rec.review.issues
    )
    # 6 other fields match and are preserved in partial_result
    assert rec.partial_result is not None
    assert len(rec.partial_result.comparisons) == 6
    assert all(c.outcome == "MATCH" for c in rec.partial_result.comparisons)


def test_seeded_general_record_properties():
    """Verify uat-demo-general is a valid non-comparison record."""
    store = AuditStore()
    seed_uat_demo_records(store)

    rec = store.get(DEMO_GENERAL_ID)
    assert rec is not None
    assert rec.classification.category == "general"
    assert rec.state == "COMPLETE"
    assert rec.outcome == "NOT_APPLICABLE"
    assert rec.mismatch_detected is None


def test_seeding_is_idempotent():
    """Repeated calls to seed_uat_demo_records do not duplicate or corrupt records."""
    store = AuditStore()

    first_seed = seed_uat_demo_records(store)
    assert store.count() == 4

    second_seed = seed_uat_demo_records(store)
    assert store.count() == 4
    assert len(second_seed) == 4

    # Email IDs and state are unchanged
    for eid in DEMO_EMAIL_IDS:
        assert store.get(eid) is not None


def test_fastapi_startup_integration():
    """Test full FastAPI client startup with flag enabled."""
    with patch.dict(os.environ, {"SDOC_UAT_DEMO_SEED": "1"}):
        with TestClient(app) as client:
            resp = client.get("/audit")
            assert resp.status_code == 200
            records = resp.json()
            eids = {r["email_id"] for r in records}
            assert DEMO_MATCH_ID in eids
            assert DEMO_MISMATCH_ID in eids
            assert DEMO_REVIEW_ID in eids
            assert DEMO_GENERAL_ID in eids

            # Test detail fetch
            resp_detail = client.get(f"/audit/{DEMO_MATCH_ID}")
            assert resp_detail.status_code == 200
            assert resp_detail.json()["outcome"] == "MATCH"
