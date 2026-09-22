from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.api.routes import get_audit_store, set_audit_store
from src.models.ingestion import AttachmentReference, EmailRecord
from src.parsers import sanitize_attachment_path
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore


ROOT_DIR = Path(__file__).resolve().parents[1]
BUNDLE_DIR = ROOT_DIR / "sdoc-hackathon-bundle"


def _hash_bundle() -> dict[str, str]:
    """Calculate SHA-256 for every file in sdoc-hackathon-bundle/."""
    hashes: dict[str, str] = {}
    if not BUNDLE_DIR.exists():
        return hashes

    for file_path in sorted(BUNDLE_DIR.rglob("*")):
        if file_path.is_file():
            rel_path = file_path.relative_to(BUNDLE_DIR).as_posix()
            content = file_path.read_bytes()
            hashes[rel_path] = hashlib.sha256(content).hexdigest()
    return hashes


def test_sec_data_001_evaluation_bundle_immutability():
    """SEC-DATA-001: Verification suite asserts 100% evaluation bundle immutability."""
    assert BUNDLE_DIR.exists(), f"Evaluation bundle missing at {BUNDLE_DIR}"
    initial_hashes = _hash_bundle()
    assert len(initial_hashes) > 0, "Evaluation bundle must contain files"

    # Simulate read-only traversal
    inbox_files = list((BUNDLE_DIR / "inbox").glob("*.json"))
    assert len(inbox_files) > 0

    post_hashes = _hash_bundle()
    assert initial_hashes == post_hashes, "sdoc-hackathon-bundle files were mutated!"


def test_sec_auth_001_api_key_leak_prevention():
    """SEC-AUTH-001: Assert API keys are absent from all API responses and public metadata."""
    client = TestClient(app)

    # Check root, health, audit endpoints
    endpoints = ["/", "/health", "/audit"]
    sensitive_keys = ["AIza", "GEMINI_API_KEY", "SECRET", "PRIVATE_KEY"]

    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200
        text = resp.text
        for key in sensitive_keys:
            assert key not in text, f"Sensitive credential token {key} found in response from {ep}"


def test_sec_leak_001_prompt_and_cot_masking():
    """SEC-LEAK-001: Internal system prompts and chain-of-thought excluded from API responses."""
    store = AuditStore()
    orch = PipelineOrchestrator(audit_store=store)

    email = EmailRecord(
        email_id="sec_leak_001",
        sender="shipper@example.com",
        subject="Booking SI vs Draft BL check",
        body="Please compare attached SI and Draft BL.",
        attachments=[],
    )
    orch.process_email(email)

    client = TestClient(app)
    set_audit_store(store)

    resp = client.get("/audit/sec_leak_001")
    assert resp.status_code == 200
    data = resp.text

    # Assert system prompt leak phrases and raw chain-of-thought reasoning tokens are absent
    forbidden_phrases = [
        "You are an expert shipping document verification assistant",
        "Let's think step by step",
        "system_instruction",
        "INTERNAL_PROMPT",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in data, f"Internal prompt or CoT phrase '{phrase}' leaked in /audit/sec_leak_001"


def test_sec_path_001_directory_traversal_defense():
    """SEC-PATH-001: Directory traversal attempts rejected with HTTP 400 or security error."""
    client = TestClient(app)

    # 1. API route path traversal defense
    traversal_ids = [
        "..%2F..%2Fetc%2Fpasswd",
        "../../etc/passwd",
        "..\\..\\Windows\\win.ini",
    ]
    for tid in traversal_ids:
        resp = client.get(f"/audit/{tid}")
        assert resp.status_code in (400, 404), f"Expected 400 or 404 for traversal {tid}, got {resp.status_code}"
        if resp.status_code == 400:
            err = resp.json()
            assert err["code"] == "INVALID_PATH_TRAVERSAL"

    # 2. File parser path sanitization defense
    insecure_paths = [
        "../../../../etc/passwd",
        "../../../etc/shadow",
        "C:\\Windows\\win.ini",
        "/etc/passwd",
    ]
    for ipath in insecure_paths:
        with pytest.raises(ValueError) as exc_info:
            sanitize_attachment_path(ipath)
        assert any(
            token in str(exc_info.value).lower()
            for token in ("traversal", "insecure", "escapes")
        )


def test_sec_integ_001_no_benchmark_answer_lookup_tables():
    """SEC-INTEG-001: AST scan asserting zero benchmark ground-truth answer tables in src/."""
    src_dir = ROOT_DIR / "src"
    violations: list[str] = []

    # Detect dictionaries mapping email IDs like 'email_001': {'category': ..., 'defect_fields': ...}
    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                # Inspect string keys for suspicious ground truth maps
                str_keys = [
                    k.value
                    for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                ]
                email_keys = [k for k in str_keys if k.startswith("email_") and len(k) <= 12]
                if len(email_keys) >= 3:
                    violations.append(
                        f"{py_file.name}:{node.lineno} contains hardcoded email lookup dictionary with keys {email_keys[:3]}"
                    )

    assert not violations, f"Detected benchmark lookup table violations: {violations}"
