"""Environment-gated UAT / Demo Audit Store Seeding Mechanism.

Strict Governance:
1. Enabled ONLY when SDOC_UAT_DEMO_SEED=1 (or 'true', 'yes', 'on').
2. Default production behavior is UNCHANGED (zero records seeded).
3. Synthetic records built via canonical Pydantic models (no validator bypass).
4. No dependencies on test fixtures or evaluation dataset.
5. Idempotent: repeated calls do not duplicate records.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from src.models.audit import AuditRecord
from src.models.ingestion import AttachmentReference, EmailRecord
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore

logger = logging.getLogger(__name__)

DEMO_MATCH_ID = "uat-demo-match"
DEMO_MISMATCH_ID = "uat-demo-mismatch"
DEMO_REVIEW_ID = "uat-demo-review"
DEMO_GENERAL_ID = "uat-demo-general"

DEMO_EMAIL_IDS = [
    DEMO_MATCH_ID,
    DEMO_MISMATCH_ID,
    DEMO_REVIEW_ID,
    DEMO_GENERAL_ID,
]

# Synthetic clean documents for UAT Match
SYNTHETIC_SI_MATCH = """[SYNTHETIC UAT DEMO DATA - SHIPPING INSTRUCTION]
Shipper: ACME GLOBAL LOGISTICS PTE LTD 10 MARINA BOULEVARD SINGAPORE 018983
Consignee: PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM
Notify Party: SAME AS CONSIGNEE
Port of Loading: SINGAPORE (SGSIN)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 3
Gross Weight: 24,500.00 KGS
Description: INDUSTRIAL MACHINERY COMPONENTS
"""

SYNTHETIC_BL_MATCH = """[SYNTHETIC UAT DEMO DATA - BILL OF LADING]
Shipper: ACME GLOBAL LOGISTICS PTE LTD 10 MARINA BOULEVARD SINGAPORE 018983
Consignee: PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM
Notify Party: SAME AS CONSIGNEE
Port of Loading: SINGAPORE (SGSIN)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 3
Gross Weight: 24,500.00 KGS
Description: INDUSTRIAL MACHINERY COMPONENTS
"""

# Synthetic documents with single deterministic container count mismatch (SI=3, BL=4)
SYNTHETIC_SI_MISMATCH = """[SYNTHETIC UAT DEMO DATA - SHIPPING INSTRUCTION]
Shipper: ACME GLOBAL LOGISTICS PTE LTD 10 MARINA BOULEVARD SINGAPORE 018983
Consignee: PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM
Notify Party: SAME AS CONSIGNEE
Port of Loading: SINGAPORE (SGSIN)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 3
Gross Weight: 24,500.00 KGS
Description: INDUSTRIAL MACHINERY COMPONENTS
"""

SYNTHETIC_BL_MISMATCH = """[SYNTHETIC UAT DEMO DATA - BILL OF LADING]
Shipper: ACME GLOBAL LOGISTICS PTE LTD 10 MARINA BOULEVARD SINGAPORE 018983
Consignee: PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM
Notify Party: SAME AS CONSIGNEE
Port of Loading: SINGAPORE (SGSIN)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 4
Gross Weight: 24,500.00 KGS
Description: INDUSTRIAL MACHINERY COMPONENTS
"""

# Synthetic documents where SI is missing gross weight, triggering HITL missing_required_value
SYNTHETIC_SI_REVIEW = """[SYNTHETIC UAT DEMO DATA - SHIPPING INSTRUCTION]
Shipper: ACME GLOBAL LOGISTICS PTE LTD 10 MARINA BOULEVARD SINGAPORE 018983
Consignee: PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM
Notify Party: SAME AS CONSIGNEE
Port of Loading: SINGAPORE (SGSIN)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 3
Description: INDUSTRIAL MACHINERY COMPONENTS
"""

SYNTHETIC_BL_REVIEW = """[SYNTHETIC UAT DEMO DATA - BILL OF LADING]
Shipper: ACME GLOBAL LOGISTICS PTE LTD 10 MARINA BOULEVARD SINGAPORE 018983
Consignee: PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM
Notify Party: SAME AS CONSIGNEE
Port of Loading: SINGAPORE (SGSIN)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 3
Gross Weight: 24,500.00 KGS
Description: INDUSTRIAL MACHINERY COMPONENTS
"""


def is_uat_demo_seed_enabled() -> bool:
    """Check if SDOC_UAT_DEMO_SEED is enabled in environment."""
    val = os.environ.get("SDOC_UAT_DEMO_SEED", "").strip().lower()
    return val in ("1", "true", "yes", "on")


def seed_uat_demo_records(store: AuditStore) -> List[AuditRecord]:
    """Seed synthetic UAT demo records into the target AuditStore idempotently."""
    seeded: List[AuditRecord] = []
    orchestrator = PipelineOrchestrator(audit_store=store)

    # 1. uat-demo-match: Complete Clean Match across 7 fields
    if store.get(DEMO_MATCH_ID) is None:
        email_match = EmailRecord(
            email_id=DEMO_MATCH_ID,
            sender="operations@acmeglobal.com",
            subject="[UAT DEMO] Verification Request - Booking #UAT-M01",
            body="Kindly compare the attached Shipping Instruction and Draft Bill of Lading.",
            attachments=[
                AttachmentReference(
                    document_id=f"{DEMO_MATCH_ID}_SI.txt",
                    path=f"{DEMO_MATCH_ID}_SI.txt",
                ),
                AttachmentReference(
                    document_id=f"{DEMO_MATCH_ID}_BL.txt",
                    path=f"{DEMO_MATCH_ID}_BL.txt",
                ),
            ],
        )
        rec_match = orchestrator.process_email(
            email_match,
            document_texts={
                f"{DEMO_MATCH_ID}_SI.txt": SYNTHETIC_SI_MATCH,
                f"{DEMO_MATCH_ID}_BL.txt": SYNTHETIC_BL_MATCH,
            },
        )
        seeded.append(rec_match)
    else:
        existing_match = store.get(DEMO_MATCH_ID)
        if existing_match:
            seeded.append(existing_match)

    # 2. uat-demo-mismatch: Complete Mismatch on container_count (3 vs 4)
    if store.get(DEMO_MISMATCH_ID) is None:
        email_mismatch = EmailRecord(
            email_id=DEMO_MISMATCH_ID,
            sender="operations@acmeglobal.com",
            subject="[UAT DEMO] Verification Request - Booking #UAT-MM02 (Container Discrepancy)",
            body="Please verify the attached Draft BL against our SI.",
            attachments=[
                AttachmentReference(
                    document_id=f"{DEMO_MISMATCH_ID}_SI.txt",
                    path=f"{DEMO_MISMATCH_ID}_SI.txt",
                ),
                AttachmentReference(
                    document_id=f"{DEMO_MISMATCH_ID}_BL.txt",
                    path=f"{DEMO_MISMATCH_ID}_BL.txt",
                ),
            ],
        )
        rec_mismatch = orchestrator.process_email(
            email_mismatch,
            document_texts={
                f"{DEMO_MISMATCH_ID}_SI.txt": SYNTHETIC_SI_MISMATCH,
                f"{DEMO_MISMATCH_ID}_BL.txt": SYNTHETIC_BL_MISMATCH,
            },
        )
        seeded.append(rec_mismatch)
    else:
        existing_mismatch = store.get(DEMO_MISMATCH_ID)
        if existing_mismatch:
            seeded.append(existing_mismatch)

    # 3. uat-demo-review: Needs Review on missing_required_value (gross_weight_kg missing from SI)
    if store.get(DEMO_REVIEW_ID) is None:
        email_review = EmailRecord(
            email_id=DEMO_REVIEW_ID,
            sender="operations@acmeglobal.com",
            subject="[UAT DEMO] Review Required - Booking #UAT-REV03 (Missing Weight Value)",
            body="Please review attached documentation. Gross weight must be verified by reviewer.",
            attachments=[
                AttachmentReference(
                    document_id=f"{DEMO_REVIEW_ID}_SI.txt",
                    path=f"{DEMO_REVIEW_ID}_SI.txt",
                ),
                AttachmentReference(
                    document_id=f"{DEMO_REVIEW_ID}_BL.txt",
                    path=f"{DEMO_REVIEW_ID}_BL.txt",
                ),
            ],
        )
        rec_review = orchestrator.process_email(
            email_review,
            document_texts={
                f"{DEMO_REVIEW_ID}_SI.txt": SYNTHETIC_SI_REVIEW,
                f"{DEMO_REVIEW_ID}_BL.txt": SYNTHETIC_BL_REVIEW,
            },
        )
        seeded.append(rec_review)
    else:
        existing_review = store.get(DEMO_REVIEW_ID)
        if existing_review:
            seeded.append(existing_review)

    # 4. uat-demo-general: Non-comparison inquiry (Vessel Schedule / General Operational Update)
    if store.get(DEMO_GENERAL_ID) is None:
        email_general = EmailRecord(
            email_id=DEMO_GENERAL_ID,
            sender="inquiries@shipper-support.com",
            subject="[UAT DEMO] Sailing Schedule Update - Asia to Europe #UAT-GEN04",
            body="Good day, please find the latest vessel sailing schedule update for Singapore to Rotterdam.",
            attachments=[],
        )
        rec_general = orchestrator.process_email(email_general)
        seeded.append(rec_general)
    else:
        existing_general = store.get(DEMO_GENERAL_ID)
        if existing_general:
            seeded.append(existing_general)

    logger.info("Seeded %d synthetic UAT demo records into AuditStore.", len(seeded))
    return seeded


def maybe_seed_uat_demo_records(store: AuditStore) -> Optional[List[AuditRecord]]:
    """Seed UAT demo records if and only if SDOC_UAT_DEMO_SEED is set."""
    if is_uat_demo_seed_enabled():
        return seed_uat_demo_records(store)
    return None
