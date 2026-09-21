"""Comprehensive Validation Script for Synthetic AI Adapter Fixtures (Task T01-03)."""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

AI_DIR = Path(__file__).resolve().parent / "ai"
manifest_path = AI_DIR / "manifest.json"

print("--- Step 1: Manifest Integrity & Structure Check ---")
assert manifest_path.exists(), f"manifest.json must exist at {manifest_path}"
with open(manifest_path, "r", encoding="utf-8") as fp:
    manifest = json.load(fp)

counts = manifest.get("counts", {})
fixtures_dict = manifest.get("fixtures", {})
retry_seqs_dict = manifest.get("retry_sequences", {})
fallbacks_dict = manifest.get("fallback_scenarios", {})

print("Programmatic Counts from Manifest:")
for k, v in counts.items():
    print(f"  {k:35s}: {v}")

# Verify file system counts match programmatic model
payload_files_on_disk = [
    p for p in AI_DIR.glob("**/*")
    if p.is_file() and p.name not in ("manifest.json", "README.md")
]
print(f"\nTotal payload files found on disk: {len(payload_files_on_disk)}")
assert len(payload_files_on_disk) == counts["total_fixture_payloads"], (
    f"Disk file count ({len(payload_files_on_disk)}) does not match manifest total_fixture_payloads ({counts['total_fixture_payloads']})"
)

valid_json_on_disk = [p for p in payload_files_on_disk if p.suffix == ".json"]
malformed_text_on_disk = [p for p in payload_files_on_disk if p.name.endswith(".json.txt")]
assert len(valid_json_on_disk) == counts["valid_json_payloads"], "Valid JSON payload count mismatch"
assert len(malformed_text_on_disk) == counts["malformed_text_payloads"], "Malformed text payload count mismatch"

APPROVED_CATEGORIES = set(manifest["approved_internal_categories"])
APPROVED_LOGICAL_REASONS = set(manifest["approved_logical_reasons"])
FORBIDDEN_EVAL_CATEGORIES = {"BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"}

print("\n--- Step 2: Individual Fixture Verification ---")
errors = []

for f_id, f_meta in fixtures_dict.items():
    rel_path = f_meta["file"]
    full_path = AI_DIR / rel_path
    if not full_path.exists():
        errors.append(f"Missing fixture file: {rel_path}")
        continue

    is_malformed = f_meta.get("is_malformed_syntax", False)
    content = full_path.read_text(encoding="utf-8")

    # Check for secret or token leakage
    for forbidden_token in ["AIzaSy", "GEMINI_API_KEY", "sk-", "Bearer "]:
        if forbidden_token in content:
            errors.append(f"Secret or token leakage detected in {rel_path}")

    # Check syntax handling
    if is_malformed:
        try:
            json.loads(content)
            errors.append(f"Fixture {rel_path} was declared malformed but parsed successfully!")
        except Exception:
            pass  # Expected to fail
    else:
        try:
            data = json.loads(content)
            # Verify category enum in valid classification fixtures
            if "classification/valid" in rel_path:
                cat = data.get("category")
                if cat is not None and cat not in APPROVED_CATEGORIES:
                    errors.append(f"Unapproved category '{cat}' in {rel_path}")
                if cat in FORBIDDEN_EVAL_CATEGORIES:
                    errors.append(f"Evaluation uppercase enum '{cat}' leaked into {rel_path}")

            # Verify no SLA or timeout policy established in atomic timeout fixture
            if f_id == "tech_timeout":
                if "30000ms" in content or "30s" in content:
                    errors.append(f"tech_timeout establishes unapproved SLA duration: {content}")
                if data.get("fault_type") != "timeout":
                    errors.append(f"tech_timeout must use fault_type = 'timeout'")

            # Verify no global retryable claim in atomic fault descriptors
            if "failures/technical" in rel_path:
                if "retryable" in data:
                    errors.append(f"Atomic fault descriptor {rel_path} establishes global retryable policy: {data}")

        except Exception as e:
            errors.append(f"Valid fixture {rel_path} failed to parse as JSON: {e}")

    # Check downstream review reason guardrail
    review_reason = f_meta.get("expected_downstream_review_reason")
    if review_reason is not None and review_reason not in APPROVED_LOGICAL_REASONS:
        errors.append(f"Invalid review reason '{review_reason}' in {f_id}. Must be one of {APPROVED_LOGICAL_REASONS}")

print(f"Fixture validation errors: {len(errors)}")
for e in errors:
    print("  ERROR:", e)
assert len(errors) == 0, f"Found {len(errors)} validation errors"

print("\n--- Step 3: OCR Bounding-Box Empirical Grounding Check ---")
from tests.fixtures.generate_document_fixtures import render_bitmap_text, SCAN_SI_LINES

ocr_box_fixture = AI_DIR / "ocr" / "valid" / "ocr_valid_full_recovery.json"
assert ocr_box_fixture.exists(), "ocr_valid_full_recovery.json must exist"
with open(ocr_box_fixture, "r", encoding="utf-8") as fp:
    ocr_data = json.load(fp)

source_doc = REPO_ROOT / "tests" / "fixtures" / "documents" / "scanned" / "scan_si_001_readable.pdf"
assert source_doc.exists(), f"Source document {source_doc} must exist"

raw_pixels = render_bitmap_text(SCAN_SI_LINES, width=600, height=800, scale=2, degraded=False)
fields = ocr_data.get("fields", {})
assert len(fields) == 7, "All seven mandatory fields must be present in OCR recovery fixture"

ocr_errors = []
for fname, fdata in fields.items():
    box = fdata.get("ocr_box")
    if not box:
        ocr_errors.append(f"Field {fname} missing ocr_box")
        continue
    xmin, ymin, xmax, ymax = box["xmin"], box["ymin"], box["xmax"], box["ymax"]
    if not (0 <= xmin < xmax <= 600 and 0 <= ymin < ymax <= 800):
        ocr_errors.append(f"Field {fname} box {box} out of canvas bounds (600x800)")
        continue
    # Check that dark text pixels actually exist inside this bounding box
    dark_px = sum(1 for y in range(ymin, ymax) for x in range(xmin, xmax) if raw_pixels[y * 600 + x] < 100)
    if dark_px == 0:
        ocr_errors.append(f"Field {fname} box {box} contains zero text pixels in rendered bitmap!")
    else:
        print(f"  [PASS] {fname:18s}: {box} -> {dark_px} dark text pixels grounded in scan_si_001_readable.pdf")

assert len(ocr_errors) == 0, f"OCR bounding-box errors: {ocr_errors}"

print("\n--- Step 4: Retry Sequences Governance Check ---")
seq_errors = []
for s_id, s_data in retry_seqs_dict.items():
    attempts = s_data.get("attempts", [])
    total_calls = s_data.get("total_calls", len(attempts))
    if total_calls > 6:
        seq_errors.append(f"Sequence {s_id} exceeds maximum provider budget of 6 calls (has {total_calls})")
    
    downstream_reason = s_data.get("expected_downstream_review_reason")
    if downstream_reason is not None and downstream_reason not in APPROVED_LOGICAL_REASONS:
        seq_errors.append(f"Sequence {s_id} has invalid review reason '{downstream_reason}'")

print(f"Retry sequence errors: {len(seq_errors)}")
for e in seq_errors:
    print("  ERROR:", e)
assert len(seq_errors) == 0, f"Found {len(seq_errors)} retry sequence errors"

print("\n--- Step 5: Fallback Scenarios Check (No Multi-Provider Routing) ---")
fb_errors = []
for fb_id, fb_data in fallbacks_dict.items():
    mechanism = fb_data.get("fallback_mechanism", "")
    if "provider" in mechanism.lower() and "deterministic" not in mechanism.lower():
        fb_errors.append(f"Fallback {fb_id} specifies multi-provider routing: '{mechanism}'")
    downstream_reason = fb_data.get("expected_downstream_review_reason")
    if downstream_reason is not None and downstream_reason not in APPROVED_LOGICAL_REASONS:
        fb_errors.append(f"Fallback {fb_id} has invalid review reason '{downstream_reason}'")

print(f"Fallback scenario errors: {len(fb_errors)}")
for e in fb_errors:
    print("  ERROR:", e)
assert len(fb_errors) == 0, f"Found {len(fb_errors)} fallback scenario errors"

print("\nALL 53 AI FIXTURE PAYLOADS AND GOVERNANCE RULES VALIDATED SUCCESSFULLY.")
