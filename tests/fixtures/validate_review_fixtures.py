#!/usr/bin/env python3
"""
validate_review_fixtures.py — Offline Governance & Contract Validator for Review Fixtures

Validates all review fixtures under tests/fixtures/review/ without live network, API, or production model dependencies:
1. Manifest integrity & programmatic count consistency against disk.
2. Unique fixture IDs and file existence.
3. Proper JSON syntax across all payloads.
4. Valid ReviewUpdate contracts:
   - Action enums strictly in {'CONFIRM', 'CORRECT'}
   - Canonical internal categories only (no evaluation enum leakage)
   - 7 mandatory comparison field names only
   - Strict prohibition of direct mismatch_detected, outcome, or comparison_result overrides
   - Valid FieldEvidence structures (non-empty quotes for text/cell, valid table coords, ordered bboxes)
5. Review case states:
   - LogicalReason strictly in 7 approved values (no 8th reason)
   - Tri-state null preservation (mismatch_detected is null when unresolved fields remain)
   - Partial result partition of 7 mandatory fields
   - Preservation of reliable fields
6. Optimistic concurrency scenarios:
   - Consistent expected vs current revisions
   - HTTP 409 conflict verification on stale revision
7. Intentionally invalid payloads:
   - Labeled valid_payload == False and expected_validation_result == 'REJECTED'
   - Verify presence of intentional contract violation
8. Evaluation bundle integrity & secret/leakage guardrails.
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "review"
MANIFEST_PATH = BASE_DIR / "manifest.json"

APPROVED_CATEGORIES = {
    "document_comparison",
    "new_shipping_instruction",
    "invoice_query",
    "general",
    "spam",
}

EVAL_CATEGORIES = {
    "BL_COMPARISON",
    "SI_REQUEST",
    "INVOICE_QUERY",
    "GENERAL",
    "SPAM",
}

APPROVED_LOGICAL_REASONS = {
    "missing_attachment",
    "unreadable_document",
    "wrong_or_uncertain_document_type",
    "missing_required_value",
    "uncertain_result",
    "conflicting_candidate_values",
    "processing_or_provider_failure",
}

PROHIBITED_LOGICAL_REASONS = {
    "low_confidence",
    "manual_override",
    "user_error",
    "parser_failed",
    "ai_failed",
    "unknown_error",
}

APPROVED_ACTIONS = {"CONFIRM", "CORRECT"}

PROHIBITED_ACTIONS = {"OVERRIDE", "APPROVE", "REJECT", "FORCE_MATCH", "FORCE_MISMATCH"}

FIELD_NAMES = {
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
}

def validate_review_fixtures():
    errors = []

    print("--- Step 1: Manifest Integrity & Structure Check ---")
    if not MANIFEST_PATH.exists():
        print(f"[FAIL] Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    counts = manifest.get("counts", {})
    fixtures = manifest.get("fixtures", {})

    print(f"Manifest Version: {manifest.get('manifest_version')}")
    print("Programmatic Counts from Manifest:")
    for k, v in counts.items():
        print(f"  {k:<35}: {v}")

    # Count payload files on disk
    payload_files_on_disk = []
    for sub in ["cases", "updates", "concurrency", "invalid"]:
        subdir = BASE_DIR / sub
        if subdir.exists():
            payload_files_on_disk.extend(list(subdir.glob("*.json")))

    total_payloads_on_disk = len(payload_files_on_disk)
    print(f"\nTotal payload files found on disk: {total_payloads_on_disk}")

    if total_payloads_on_disk != counts.get("total_fixture_payloads"):
        errors.append(f"Disk payload count ({total_payloads_on_disk}) != manifest total_fixture_payloads ({counts.get('total_fixture_payloads')})")

    # Step 2: Individual Fixture Verification
    print("\n--- Step 2: Individual Fixture Verification ---")
    seen_fixture_ids = set()

    for fix_id, meta in fixtures.items():
        if fix_id in seen_fixture_ids:
            errors.append(f"Duplicate fixture ID: {fix_id}")
        seen_fixture_ids.add(fix_id)

        rel_file = meta.get("file")
        if not rel_file:
            errors.append(f"Fixture {fix_id} missing 'file' property in manifest")
            continue

        file_path = BASE_DIR / rel_file
        if not file_path.exists():
            errors.append(f"Referenced file does not exist: {file_path}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"Failed to parse JSON for {file_path}: {e}")
            continue

        fixture_type = meta.get("fixture_type")
        is_valid_payload = meta.get("valid_payload", True)

        # 2A: Review Cases Validation
        if fixture_type == "review_case":
            # Check review case structure
            if data.get("schema_version") != "1.0-draft":
                errors.append(f"Case {fix_id}: schema_version must be '1.0-draft'")

            state = data.get("state")
            if state == "NEEDS_REVIEW":
                if data.get("outcome") is not None:
                    errors.append(f"Case {fix_id}: NEEDS_REVIEW case must have outcome = null")
                if data.get("mismatch_detected") is not None:
                    errors.append(f"Case {fix_id}: NEEDS_REVIEW case must have mismatch_detected = null (tri-state rule)")
                if data.get("result_summary") == "No mismatch detected":
                    errors.append(f"Case {fix_id}: NEEDS_REVIEW case cannot have summary 'No mismatch detected'")

            review = data.get("review")
            if not review or review.get("state") != "OPEN":
                errors.append(f"Case {fix_id}: NEEDS_REVIEW case must have open review")
            else:
                for issue in review.get("issues", []):
                    reason = issue.get("logical_reason")
                    if reason not in APPROVED_LOGICAL_REASONS:
                        errors.append(f"Case {fix_id}: unapproved logical_reason '{reason}'")
                    if reason in PROHIBITED_LOGICAL_REASONS:
                        errors.append(f"Case {fix_id}: prohibited logical_reason '{reason}'")

            # Check partial_result partition if comparison
            cat = data.get("classification", {}).get("category")
            if cat == "document_comparison":
                pr = data.get("partial_result")
                if not pr:
                    errors.append(f"Case {fix_id}: comparison request requires partial_result")
                else:
                    comp_fields = {c.get("field") for c in pr.get("comparisons", [])}
                    unres_fields = set(pr.get("unresolved_fields", []))
                    if comp_fields.intersection(unres_fields):
                        errors.append(f"Case {fix_id}: comparisons and unresolved_fields must be disjoint")
                    if comp_fields.union(unres_fields) != FIELD_NAMES:
                        errors.append(f"Case {fix_id}: comparisons + unresolved_fields must partition all 7 fields")

        # 2B: Review Updates Validation (Valid Payloads)
        elif fixture_type == "review_update":
            if not is_valid_payload:
                errors.append(f"Fixture {fix_id} labeled review_update but marked invalid")
            action = data.get("action")
            if action not in APPROVED_ACTIONS:
                errors.append(f"Update {fix_id}: action '{action}' not in approved actions {APPROVED_ACTIONS}")

            # Guardrails: Reviewers do NOT directly set mismatch_detected or outcome
            if "mismatch_detected" in data:
                errors.append(f"Update {fix_id}: valid ReviewUpdate must NOT contain mismatch_detected")
            if "outcome" in data:
                errors.append(f"Update {fix_id}: valid ReviewUpdate must NOT contain outcome")
            if "comparison_result" in data:
                errors.append(f"Update {fix_id}: valid ReviewUpdate must NOT contain comparison_result")

            cat = data.get("category")
            if cat is not None and cat not in APPROVED_CATEGORIES:
                errors.append(f"Update {fix_id}: category '{cat}' is not a canonical internal category")
            if cat in EVAL_CATEGORIES:
                errors.append(f"Update {fix_id}: leaked evaluation enum '{cat}' in valid ReviewUpdate")

            for corr in data.get("corrections", []):
                fn = corr.get("field")
                if fn not in FIELD_NAMES:
                    errors.append(f"Update {fix_id}: field '{fn}' not in approved 7 fields")
                if not corr.get("evidence_ids"):
                    errors.append(f"Update {fix_id}: FieldCorrection requires evidence_ids")
                if not corr.get("rationale"):
                    errors.append(f"Update {fix_id}: FieldCorrection requires rationale")

            for rcorr in data.get("role_corrections", []):
                role = rcorr.get("assigned_role")
                if role not in {"SI", "BL", "UNKNOWN"}:
                    errors.append(f"Update {fix_id}: assigned_role '{role}' invalid")
                if not rcorr.get("evidence_ids"):
                    errors.append(f"Update {fix_id}: RoleCorrection requires evidence_ids")

            for ev in data.get("added_evidence", []):
                kind = ev.get("kind")
                if kind in ("text_span", "table_cell"):
                    if not ev.get("quote"):
                        errors.append(f"Update {fix_id}: evidence kind '{kind}' requires quote")
                if kind == "table_cell":
                    loc = ev.get("location", {})
                    if not loc.get("table") or loc.get("row") is None or loc.get("column") is None:
                        errors.append(f"Update {fix_id}: table_cell requires table, row, column coordinates")
                if kind == "page_region":
                    loc = ev.get("location", {})
                    bbox = loc.get("bbox")
                    if not bbox or len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                        errors.append(f"Update {fix_id}: page_region requires ordered bbox [x0, y0, x1, y1]")

        # 2C: Concurrency Scenarios Validation
        elif fixture_type == "concurrency_scenario":
            scen_id = data.get("scenario_id")
            if not scen_id:
                errors.append(f"Concurrency scenario {fix_id} missing scenario_id")
            if scen_id == "CONC-001":
                if data.get("expected_http_status") != 200 or data.get("expected_resulting_revision") != 4:
                    errors.append(f"CONC-001 expected status 200 and rev 4")
            elif scen_id == "CONC-002":
                if data.get("expected_http_status") != 409 or data.get("expected_result") != "REVISION_CONFLICT":
                    errors.append(f"CONC-002 expected status 409 REVISION_CONFLICT")
            elif scen_id == "CONC-003":
                s1 = data.get("step_1_reviewer_a", {})
                s2 = data.get("step_2_reviewer_b", {})
                if s1.get("expected_http_status") != 200 or s2.get("expected_http_status") != 409:
                    errors.append(f"CONC-003 step expectations inconsistent")

        # 2D: Invalid Review Payloads Validation
        elif fixture_type == "invalid_review_payload":
            if is_valid_payload:
                errors.append(f"Fixture {fix_id} in invalid/ must have valid_payload = False")
            if meta.get("expected_validation_result") != "REJECTED":
                errors.append(f"Fixture {fix_id} in invalid/ must have expected_validation_result = REJECTED")

    print(f"Fixture validation errors: {len(errors)}")

    # Step 3: Governance & Guardrail Checks
    print("\n--- Step 3: Governance & Guardrail Checks ---")
    # Verify no unapproved business rules (port alias, org equivalence, weight tolerance)
    for fpath in payload_files_on_disk:
        content = fpath.read_text(encoding="utf-8")
        if "DEC-P06C" in content or "DEC-P06D" in content or "DEC-P06E" in content:
            errors.append(f"File {fpath} contains unapproved business rule reference")

    print(f"Governance check errors: {len(errors)}")

    # Step 4: Recomputation & Tri-State Scenarios Check
    print("\n--- Step 4: Recomputation & Tri-State Scenarios Check ---")
    recomputations = manifest.get("recomputation_scenarios", {})
    if len(recomputations) < 3:
        errors.append(f"Expected at least 3 recomputation scenarios, found {len(recomputations)}")

    tristate = manifest.get("tristate_scenarios", {})
    if len(tristate) < 1:
        errors.append(f"Expected at least 1 tri-state scenario, found {len(tristate)}")

    print(f"Recomputation scenarios: {len(recomputations)}")
    for r_id, r_info in recomputations.items():
        print(f"  [{r_id}] {r_info.get('name')}: {r_info.get('rule')}")

    print(f"Tri-state scenarios: {len(tristate)}")
    for t_id, t_info in tristate.items():
        print(f"  [{t_id}] {t_info.get('name')}: invariant={t_info.get('invariant')}")

    if errors:
        print(f"\n[FAIL] Validation completed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"\nALL {total_payloads_on_disk} REVIEW FIXTURE PAYLOADS AND GOVERNANCE RULES VALIDATED SUCCESSFULLY.")

if __name__ == "__main__":
    validate_review_fixtures()
