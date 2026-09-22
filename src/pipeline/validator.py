import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.adapters.evaluation_adapter import EvaluationAdapter

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
    """Legacy compatibility wrapper around the authoritative T13 validator.

    ``expected_sample`` contributes coverage keys only.  Its values are never
    treated as answer keys.
    """
    return EvaluationAdapter.validate_submission_dict(
        submission,
        expected_email_ids=expected_sample.keys(),
    )


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
