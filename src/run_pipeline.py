import argparse
from collections import Counter
import json
import logging
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm

from src.models.audit import AuditRecord
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.validator import validate_submission_dict
from src.store.audit_store import AuditStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")

STRICT_TO_COMPETITION_CAT = {
    "document_comparison": "BL_COMPARISON",
    "new_shipping_instruction": "SI_REQUEST",
    "invoice_query": "INVOICE_QUERY",
    "general": "GENERAL",
    "general_message": "GENERAL",
    "spam": "SPAM",
}


def audit_record_to_competition_dict(rec: AuditRecord) -> Dict[str, Any]:
    """Map canonical AuditRecord to evaluation submission schema format."""
    cat = rec.classification.category or "general"
    comp_category = STRICT_TO_COMPETITION_CAT.get(cat, "GENERAL")

    if rec.state == "NEEDS_REVIEW":
        reason = "unreadable"
        if rec.review and rec.review.issues:
            iss = rec.review.issues[0]
            lr = iss.logical_reason
            val = lr.value if hasattr(lr, "value") else str(lr)
            if val in ("missing_attachment", "wrong_or_uncertain_document_type"):
                reason = "wrong_doc_type" if val == "wrong_or_uncertain_document_type" else "missing_attachment"
            elif val == "missing_required_value":
                reason = "missing_value"
            else:
                reason = "unreadable"
        return {
            "category": comp_category,
            "status": "NEEDS_REVIEW",
            "review_reason": reason,
            "defect_fields": [],
            "has_defect": False,
        }
    elif rec.mismatch_detected:
        return {
            "category": comp_category,
            "status": "MISMATCH",
            "review_reason": None,
            "defect_fields": [d.field for d in rec.discrepancies],
            "has_defect": True,
        }
    else:
        return {
            "category": comp_category,
            "status": "OK",
            "review_reason": None,
            "defect_fields": [],
            "has_defect": False,
        }


def load_inbox_emails(bundle_path: Path) -> List[Dict[str, Any]]:
    """Load and sort all email_*.json records from bundle inbox/ directory."""
    inbox_dir = bundle_path / "inbox"
    if not inbox_dir.exists():
        raise FileNotFoundError(f"Inbox directory not found: {inbox_dir}")

    email_files = sorted(inbox_dir.glob("email_*.json"))
    emails = []
    for p in email_files:
        try:
            emails.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            logger.error("Failed to read email %s: %s", p.name, e)

    return emails


def run_pipeline(
    bundle_dir: str = "sdoc-hackathon-bundle",
    submission_output: str = "submission.json",
    audit_output: str = "audit_report.json",
    limit: int = 0,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Execute end-to-end verification pipeline synthesizing strict AuditRecord models (T11-02)."""
    bundle_path = Path(bundle_dir)
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle directory '{bundle_dir}' does not exist.")

    logger.info("Initializing Shipping Document Verification Pipeline...")

    store = AuditStore()
    orchestrator = PipelineOrchestrator(
        base_dir=bundle_path,
        audit_store=store,
    )

    all_emails = load_inbox_emails(bundle_path)
    total_inbox_count = len(all_emails)
    logger.info("Loaded %d emails from %s", total_inbox_count, bundle_dir)

    emails = all_emails[:limit] if limit > 0 else all_emails

    competition_submission: Dict[str, Any] = {}
    audit_records: List[AuditRecord] = []

    logger.info("=== Executing Pipeline Across Ingested Emails ===")
    for email in tqdm(emails, desc="Auditing emails"):
        eid = email["email_id"]
        audit_rec = orchestrator.process_email(email)
        audit_records.append(audit_rec)
        competition_submission[eid] = audit_record_to_competition_dict(audit_rec)

    # Fill remainder if limited run for schema validation
    sample_sub_path = bundle_path / "sample_submission.json"
    if sample_sub_path.exists():
        sample_data = json.loads(sample_sub_path.read_text(encoding="utf-8"))
        if len(competition_submission) < len(sample_data):
            for eid, default_rec in sample_data.items():
                if eid not in competition_submission:
                    competition_submission[eid] = default_rec

        # Validate against sample_submission.json
        valid, errors = validate_submission_dict(competition_submission, sample_data)
        if valid:
            logger.info("PASSED: Competition submission conforms 100%% to sample schema!")
        else:
            logger.warning("FAILED validation with %d issues: %s", len(errors), errors[:5])

    # 1. Write official competition submission.json
    sub_path = Path(submission_output)
    sub_path.write_text(json.dumps(competition_submission, indent=2), encoding="utf-8")
    logger.info("Wrote %d records to %s", len(competition_submission), sub_path.resolve())

    # 2. Write strict contract audit_report.json
    audit_dict_list = [json.loads(r.model_dump_json()) for r in audit_records]
    audit_path = Path(audit_output)
    audit_path.write_text(json.dumps(audit_dict_list, indent=2), encoding="utf-8")
    logger.info("Wrote %d strict audit records to %s", len(audit_dict_list), audit_path.resolve())

    # 3. Synchronize to docs/ for GitHub Pages
    docs_dir = Path("docs")
    if docs_dir.exists():
        shutil.copy(audit_path, docs_dir / "audit_report.json")
        shutil.copy(sub_path, docs_dir / "submission.json")
        logger.info("Synchronized reports to docs/ for GitHub Pages.")

    # Summary metrics
    status_counts = Counter(rec["status"] for rec in competition_submission.values())
    reasons = Counter(rec["review_reason"] for rec in competition_submission.values() if rec["review_reason"])
    defect_fields_counter = Counter(
        f for rec in competition_submission.values() for f in rec.get("defect_fields", [])
    )

    print("\n" + "=" * 65)
    print("      SDOC AUDIT ENGINE - RUN SUMMARY (ZERO FALSE ALARMS)")
    print("=" * 65)
    print(f"Total Emails Processed  : {len(emails)} (of {total_inbox_count})")
    print(f"Verification Statuses   : {dict(status_counts)}")
    if reasons:
        print(f"HITL Review Reasons     : {dict(reasons)}")
    if defect_fields_counter:
        print(f"Discrepancies Caught    : {dict(defect_fields_counter)}")
    print(f"Output Submission File  : {sub_path.name}")
    print(f"Output Audit File       : {audit_path.name}")
    print("=" * 65 + "\n")

    return competition_submission, audit_dict_list


def main():
    parser = argparse.ArgumentParser(description="Run Shipping Document Verification Pipeline")
    parser.add_argument("--bundle", default="sdoc-hackathon-bundle", help="Path to bundle folder")
    parser.add_argument("--output", default="submission.json", help="Path to submission.json")
    parser.add_argument("--audit", default="audit_report.json", help="Path to audit_report.json")
    parser.add_argument("--limit", type=int, default=0, help="Limit to first N emails")

    args = parser.parse_args()
    try:
        run_pipeline(
            bundle_dir=args.bundle,
            submission_output=args.output,
            audit_output=args.audit,
            limit=args.limit,
        )
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
