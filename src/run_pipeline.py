import argparse
import json
import logging
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple
from tqdm import tqdm

from src.cache import PipelineCache
from src.config import is_gemini_available
from src.llm.client import GeminiClient
from src.pipeline.schema import COMPETITION_TO_STRICT_CAT, AuditOutputRecord, HITLEscalation
from src.pipeline.stage1_classify import Stage1Classifier
from src.pipeline.stage2_extract import Stage2Extractor
from src.pipeline.stage3_compare import Stage3Comparator
from src.pipeline.validator import validate_submission_dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


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
    cache_file: str = ".cache_pipeline.json",
    use_cache: bool = True,
    limit: int = 0,
    batch_size: int = 30,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Execute end-to-end verification pipeline adhering to High-Score Strategies.
    Generates both official hackathon submission.json and strict audit_report.json.
    """
    bundle_path = Path(bundle_dir)
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle directory '{bundle_dir}' does not exist.")

    logger.info("Initializing Shipping Document Verification Pipeline...")
    logger.info("Gemini API configured: %s", is_gemini_available())

    cache = PipelineCache(cache_file) if use_cache else None
    gemini_client = GeminiClient() if is_gemini_available() else None

    # Load emails
    all_emails = load_inbox_emails(bundle_path)
    total_inbox_count = len(all_emails)
    logger.info("Loaded %d emails from %s", total_inbox_count, bundle_dir)

    emails = all_emails[:limit] if limit > 0 else all_emails

    # Stage 1: Classification
    logger.info("=== Starting Stage 1: Email Classification ===")
    classifier = Stage1Classifier(
        gemini_client=gemini_client,
        cache=cache,
        batch_size=batch_size,
    )
    classifications = classifier.classify_all(emails)

    category_counts = Counter(classifications.values())
    logger.info("Classification Breakdown: %s", dict(category_counts))

    # Stage 2 & 3: Extraction & Comparison
    logger.info("=== Starting Stage 2 & 3: Document Verification (Strict Veto Logic) ===")
    extractor = Stage2Extractor(base_dir=bundle_path, cache=cache)
    comparator = Stage3Comparator(gemini_client=gemini_client, cache=cache)

    competition_submission: Dict[str, Any] = {}
    audit_records: List[AuditOutputRecord] = []

    for email in tqdm(emails, desc="Auditing emails"):
        eid = email["email_id"]
        comp_category = classifications.get(eid, "GENERAL")
        strict_category = COMPETITION_TO_STRICT_CAT.get(comp_category, "general_message")

        # Secret 4: Classification Veto Rule — Only document_comparison proceeds
        if comp_category == "BL_COMPARISON":
            ready_payload, early_audit_record = extractor.extract_comparison_pair(email)

            if early_audit_record:
                audit_rec = early_audit_record
            else:
                audit_rec = comparator.compare(ready_payload)
        else:
            # Terminate immediately for non-comparison emails
            audit_rec = AuditOutputRecord(
                email_id=eid,
                category=strict_category,
                mismatch_detected=False,
                result_summary="No mismatch detected",
                discrepancies=[],
                hitl_escalation=HITLEscalation(needed=False),
            )

        audit_records.append(audit_rec)
        competition_submission[eid] = audit_rec.to_competition_dict()

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
    audit_dict_list = [r.model_dump() for r in audit_records]
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
    print(f"Categories Breakdown    : {dict(category_counts)}")
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
    parser.add_argument("--cache", default=".cache_pipeline.json", help="Cache file path")
    parser.add_argument("--no-cache", action="store_true", help="Do not use cache")
    parser.add_argument("--limit", type=int, default=0, help="Limit to first N emails")
    parser.add_argument("--batch-size", type=int, default=30, help="Stage 1 batch size")

    args = parser.parse_args()
    try:
        run_pipeline(
            bundle_dir=args.bundle,
            submission_output=args.output,
            audit_output=args.audit,
            cache_file=args.cache,
            use_cache=not args.no_cache,
            limit=args.limit,
            batch_size=args.batch_size,
        )
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
