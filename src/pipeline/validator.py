import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

VALID_CATEGORIES = {"BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"}
VALID_STATUSES = {"OK", "MISMATCH", "NEEDS_REVIEW"}
VALID_REVIEW_REASONS = {"wrong_doc_type", "missing_attachment", "unreadable", "missing_value"}
VALID_DEFECT_FIELDS = {
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
}


def validate_submission_dict(
    submission: Dict[str, Any],
    expected_sample: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Validate a submission dictionary against expectations and schema rules."""
    errors = []

    # 1. Check all expected email_ids are present
    missing_keys = set(expected_sample.keys()) - set(submission.keys())
    if missing_keys:
        errors.append(f"Missing {len(missing_keys)} email IDs (e.g. {sorted(list(missing_keys))[:3]})")

    extra_keys = set(submission.keys()) - set(expected_sample.keys())
    if extra_keys:
        errors.append(f"Extra {len(extra_keys)} email IDs (e.g. {sorted(list(extra_keys))[:3]})")

    # 2. Check each entry's schema
    for email_id, record in submission.items():
        if not isinstance(record, dict):
            errors.append(f"{email_id}: record is not a dictionary")
            continue

        required_fields = ["category", "status", "review_reason", "defect_fields", "has_defect"]
        for f in required_fields:
            if f not in record:
                errors.append(f"{email_id}: missing field '{f}'")

        cat = record.get("category")
        if cat not in VALID_CATEGORIES:
            errors.append(f"{email_id}: invalid category '{cat}'")

        stat = record.get("status")
        if stat not in VALID_STATUSES:
            errors.append(f"{email_id}: invalid status '{stat}'")

        has_defect = record.get("has_defect")
        if not isinstance(has_defect, bool):
            errors.append(f"{email_id}: 'has_defect' must be boolean, got {type(has_defect)}")

        defect_fields = record.get("defect_fields")
        if not isinstance(defect_fields, list):
            errors.append(f"{email_id}: 'defect_fields' must be a list")
        else:
            invalid_fields = set(defect_fields) - VALID_DEFECT_FIELDS
            if invalid_fields:
                errors.append(f"{email_id}: invalid defect fields {invalid_fields}")

        reason = record.get("review_reason")

        # Specific consistency constraints
        if stat == "MISMATCH":
            if not has_defect:
                errors.append(f"{email_id}: status is MISMATCH but has_defect is False")
            if not defect_fields:
                errors.append(f"{email_id}: status is MISMATCH but defect_fields is empty")
            if reason is not None:
                errors.append(f"{email_id}: status is MISMATCH but review_reason is not null")

        elif stat == "OK":
            if has_defect:
                errors.append(f"{email_id}: status is OK but has_defect is True")
            if defect_fields:
                errors.append(f"{email_id}: status is OK but defect_fields is non-empty")
            if reason is not None:
                errors.append(f"{email_id}: status is OK but review_reason is not null")

        elif stat == "NEEDS_REVIEW":
            if has_defect:
                errors.append(f"{email_id}: status is NEEDS_REVIEW but has_defect is True")
            if defect_fields:
                errors.append(f"{email_id}: status is NEEDS_REVIEW but defect_fields is non-empty")
            if reason not in VALID_REVIEW_REASONS:
                errors.append(f"{email_id}: invalid review_reason '{reason}' for NEEDS_REVIEW")

    return len(errors) == 0, errors


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m src.pipeline.validator <submission.json> <sample_submission.json>")
        sys.exit(1)

    sub_path = Path(sys.argv[1])
    sample_path = Path(sys.argv[2])

    if not sub_path.exists():
        print(f"Error: {sub_path} not found")
        sys.exit(1)

    sub_data = json.loads(sub_path.read_text(encoding="utf-8"))
    sample_data = json.loads(sample_path.read_text(encoding="utf-8"))

    valid, errs = validate_submission_dict(sub_data, sample_data)
    if valid:
        print(f"PASS: {sub_path.name} conforms perfectly to sample schema ({len(sub_data)} records).")
        sys.exit(0)
    else:
        print(f"FAIL: {len(errs)} validation issues found:")
        for err in errs[:20]:
            print(f"  - {err}")
        if len(errs) > 20:
            print(f"  ... and {len(errs) - 20} more errors.")
        sys.exit(1)
