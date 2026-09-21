import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
from tqdm import tqdm

from src.cache import PipelineCache
from src.config import is_gemini_available
from src.llm.client import GeminiClient
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
    output_file: str = "submission.json",
    cache_file: str = ".cache_pipeline.json",
    use_cache: bool = True,
    limit: int = 0,
    batch_size: int = 30,
) -> Dict[str, Any]:
    """Execute end-to-end verification pipeline."""
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

    if limit > 0:
        logger.info("Limiting run to first %d emails", limit)
        emails = all_emails[:limit]
    else:
        emails = all_emails

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
    logger.info("=== Starting Stage 2 & 3: Document Extraction & Verification ===")
    extractor = Stage2Extractor(base_dir=bundle_path, cache=cache)
    comparator = Stage3Comparator(gemini_client=gemini_client, cache=cache)

    submission: Dict[str, Any] = {}

    for email in tqdm(emails, desc="Processing emails"):
        eid = email["email_id"]
        category = classifications.get(eid, "GENERAL")

        if category == "BL_COMPARISON":
            ready_payload, early_decision = extractor.extract_comparison_pair(email)

            if early_decision:
                submission[eid] = early_decision
            else:
                comp_result = comparator.compare(ready_payload)
                submission[eid] = comp_result
        else:
            # Non-comparison emails default to standard non-defect record
            submission[eid] = {
                "category": category,
                "status": "OK",
                "review_reason": None,
                "defect_fields": [],
                "has_defect": False,
            }

    # If limited run, populate remainder with sample submission keys so schema validation succeeds
    sample_sub_path = bundle_path / "sample_submission.json"
    if sample_sub_path.exists():
        sample_data = json.loads(sample_sub_path.read_text(encoding="utf-8"))
        if len(submission) < len(sample_data):
            logger.info("Filling missing entries with baseline defaults for full schema test...")
            for eid, default_rec in sample_data.items():
                if eid not in submission:
                    submission[eid] = default_rec

        # Validate against sample_submission.json
        valid, errors = validate_submission_dict(submission, sample_data)
        if valid:
            logger.info("PASSED: Output submission adheres perfectly to sample schema!")
        else:
            logger.warning("FAILED validation with %d issues: %s", len(errors), errors[:5])

    # Write output submission
    out_path = Path(output_file)
    out_path.write_text(json.dumps(submission, indent=2), encoding="utf-8")
    logger.info("Wrote %d records to %s", len(submission), out_path.resolve())

    # Summary report
    status_counts = Counter(rec["status"] for rec in submission.values())
    reasons = Counter(rec["review_reason"] for rec in submission.values() if rec["review_reason"])
    defect_fields_counter = Counter(
        f for rec in submission.values() for f in rec.get("defect_fields", [])
    )

    print("\n" + "=" * 60)
    print("           VERIFICATION PIPELINE RUN SUMMARY")
    print("=" * 60)
    print(f"Total Emails Processed : {len(emails)} (of {total_inbox_count})")
    print(f"Categories Breakdown   : {dict(category_counts)}")
    print(f"Verification Statuses  : {dict(status_counts)}")
    if reasons:
        print(f"Review Reasons         : {dict(reasons)}")
    if defect_fields_counter:
        print(f"Defects Identified     : {dict(defect_fields_counter)}")
    print(f"Output File Saved      : {out_path.name}")
    print("=" * 60 + "\n")

    return submission


def main():
    parser = argparse.ArgumentParser(description="Run Shipping Document Verification Pipeline")
    parser.add_argument(
        "--bundle",
        default="sdoc-hackathon-bundle",
        help="Path to dataset bundle directory",
    )
    parser.add_argument(
        "--output",
        default="submission.json",
        help="Path to output submission JSON",
    )
    parser.add_argument(
        "--cache",
        default=".cache_pipeline.json",
        help="Path to pipeline cache file",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not use cached checkpoint data",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit execution to first N emails (0 for all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="Batch size for Stage 1 classification",
    )

    args = parser.parse_args()
    try:
        run_pipeline(
            bundle_dir=args.bundle,
            output_file=args.output,
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
