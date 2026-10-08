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


CARRIERS = [
    ("MAERSK LINE", "copenhagen-docs@maersk.com"),
    ("MEDITERRANEAN SHIPPING COMPANY (MSC)", "geneva-ops@msc.com"),
    ("CMA CGM S.A.", "marseille-export@cma-cgm.com"),
    ("COSCO SHIPPING LINES", "shanghai-docs@coscoshipping.com"),
    ("HAPAG-LLOYD AG", "hamburg-booking@hlag.com"),
    ("OCEAN NETWORK EXPRESS (ONE)", "singapore-ops@one-line.com"),
    ("EVERGREEN MARINE CORP", "taipei-export@evergreen-marine.com"),
    ("YANG MING MARINE TRANSPORT", "keelung-docs@yangming.com"),
    ("KUEHNE + NAGEL LOGISTICS", "seafreight@kuehne-nagel.com"),
    ("DB SCHENKER OCEAN", "ocean-docs@dbschenker.com"),
]

PORTS = [
    ("SINGAPORE (SGSIN)", "ROTTERDAM (NLRTM)"),
    ("SHANGHAI (CNSHA)", "LOS ANGELES (USLAX)"),
    ("NINGBO-ZHOUSHAN (CNNGB)", "HAMBURG (DEHAM)"),
    ("BUSAN (KRPUS)", "LONG BEACH (USLGB)"),
    ("SHENZHEN (CNSZX)", "ANTWERP (BEANR)"),
    ("TOKYO (JPTYO)", "SOUTHAMPTON (GBSOU)"),
    ("QINGDAO (CNTAO)", "FELIXSTOWE (GBFXT)"),
    ("PORT KLANG (MYPKG)", "LE HAVRE (FRLEH)"),
    ("KAOHSIUNG (TWKHH)", "NEW YORK (USNYC)"),
    ("TANJUNG PELEPAS (MYTPP)", "VALENCIA (ESVLC)"),
]

COMMODITIES = [
    "INDUSTRIAL MACHINERY COMPONENTS",
    "PHOTOVOLTAIC SOLAR MODULES & INVERTERS",
    "AUTOMOTIVE LITHIUM-ION BATTERY PACKS",
    "PRECISION MEDICAL DIAGNOSTIC WORKSTATIONS",
    "SPECIALTY GRADE ARABICA COFFEE BEANS",
    "SEMICONDUCTOR WAFER FABRICATION SPARES",
    "REFRIGERATED SEAFOOD COLD CHAIN CONTAINERS",
    "TELECOMMUNICATION OPTICAL SWITCHES",
    "AEROSPACE GRADE TITANIUM FASTENERS",
    "TECHNICAL TEXTILES AND POLYMER ROLLS",
]

CONSIGNEES = [
    "PACIFIC IMPORT DISTRIBUTORS B.V. WESTERDOKSDIJK 40 1013 AD AMSTERDAM",
    "ATLANTIC OCEAN IMPORTS GMBH SPEICHERSTRASSE 12 20457 HAMBURG",
    "WEST COAST FREIGHT RECEIVERS LLC 500 S GRAND AVE LOS ANGELES CA 90071",
    "EAST COAST CARGO LOGISTICS INC 111 8TH AVENUE NEW YORK NY 10011",
    "EUROPEAN SUPPLY CHAIN PARTNERS N.V. NOORDERLAAN 147 2030 ANTWERP",
]

ALT_CONSIGNEES = [
    "GLOBAL TRANSIT WAREHOUSING S.A. RUE DU RHONE 42 1204 GENEVA",
    "BENELUX LOGISTICS DISTRIBUTION B.V. MAASVLAKTE 2 3000 AA ROTTERDAM",
    "NORDIC MARITIME FREIGHT OY ETELARANTA 10 00130 HELSINKI",
    "MEDITERRANEAN CARGO TERMINALS S.L. MOLL DE BARCELONA 08039 BARCELONA",
]

ALT_PORTS = [
    "BREMERHAVEN (DEBRV)",
    "OAKLAND (USOAK)",
    "BARCELONA (ESBCN)",
    "GENOA (ITGOA)",
    "SAVANNAH (USSAV)",
]


def is_uat_demo_seed_enabled() -> bool:
    """Check if SDOC_UAT_DEMO_SEED is enabled in environment or running on Render."""
    val = os.environ.get("SDOC_UAT_DEMO_SEED", "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return bool(os.environ.get("RENDER"))


def seed_uat_demo_records(
    store: AuditStore, count: Optional[int] = None
) -> List[AuditRecord]:
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

    # Additional bulk cases to populate realistic high-density verification queues (up to count)
    if count is not None:
        target_count = count
    else:
        env_count = os.environ.get("SDOC_UAT_SEED_COUNT", "").strip()
        if env_count:
            target_count = int(env_count)
        elif os.environ.get("RENDER"):
            target_count = 250
        else:
            target_count = 4

    if target_count > 4:
        for i in range(4, target_count):
            c_name, c_email = CARRIERS[i % len(CARRIERS)]
            pol, pod = PORTS[i % len(PORTS)]
            cargo = COMMODITIES[i % len(COMMODITIES)]
            consignee = CONSIGNEES[i % len(CONSIGNEES)]
            cnt = 2 + (i % 12)
            wt = 14500.0 + (i * 275.5) % 32000.0

            bucket = i % 10
            if bucket in (0, 1, 2, 3, 4):  # Clean Match
                eid = f"uat-case-{i+1:03d}-match"
                if store.get(eid) is None:
                    si = f"""[SHIPPING INSTRUCTION]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Container Count: {cnt}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""
                    bl = si
                    email = EmailRecord(
                        email_id=eid,
                        sender=c_email,
                        subject=f"[UAT] Verification Request - Booking #UAT-{1000+i} (Clean Match)",
                        body="Please verify attached Draft BL against our SI.",
                        attachments=[
                            AttachmentReference(document_id=f"{eid}_SI.txt", path=f"{eid}_SI.txt"),
                            AttachmentReference(document_id=f"{eid}_BL.txt", path=f"{eid}_BL.txt"),
                        ],
                    )
                    rec = orchestrator.process_email(
                        email,
                        document_texts={f"{eid}_SI.txt": si, f"{eid}_BL.txt": bl},
                    )
                    seeded.append(rec)
                else:
                    existing = store.get(eid)
                    if existing:
                        seeded.append(existing)

            elif bucket in (5, 6):  # Mismatch across diverse fields
                eid = f"uat-case-{i+1:03d}-mismatch"
                if store.get(eid) is None:
                    sub_type = i % 4
                    if sub_type == 0:
                        diff_label = "Container Count Mismatch"
                        bl_cnt = cnt + 1
                        bl_wt = wt
                        bl_pod = pod
                        bl_consignee = consignee
                    elif sub_type == 1:
                        diff_label = "Gross Weight Discrepancy"
                        bl_cnt = cnt
                        bl_wt = wt + 850.0
                        bl_pod = pod
                        bl_consignee = consignee
                    elif sub_type == 2:
                        diff_label = "Discharge Port Mismatch"
                        bl_cnt = cnt
                        bl_wt = wt
                        bl_pod = ALT_PORTS[i % len(ALT_PORTS)]
                        bl_consignee = consignee
                    else:
                        diff_label = "Consignee Entity Mismatch"
                        bl_cnt = cnt
                        bl_wt = wt
                        bl_pod = pod
                        bl_consignee = ALT_CONSIGNEES[i % len(ALT_CONSIGNEES)]

                    si = f"""[SHIPPING INSTRUCTION]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Container Count: {cnt}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""
                    bl = f"""[BILL OF LADING]
Shipper: {c_name}
Consignee: {bl_consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {bl_pod}
Container Count: {bl_cnt}
Gross Weight: {bl_wt:,.2f} KGS
Description: {cargo}
"""
                    email = EmailRecord(
                        email_id=eid,
                        sender=c_email,
                        subject=f"[UAT] Discrepancy Alert - Booking #UAT-{1000+i} ({diff_label})",
                        body="Please verify attached Draft BL against our SI.",
                        attachments=[
                            AttachmentReference(document_id=f"{eid}_SI.txt", path=f"{eid}_SI.txt"),
                            AttachmentReference(document_id=f"{eid}_BL.txt", path=f"{eid}_BL.txt"),
                        ],
                    )
                    rec = orchestrator.process_email(
                        email,
                        document_texts={f"{eid}_SI.txt": si, f"{eid}_BL.txt": bl},
                    )
                    seeded.append(rec)
                else:
                    existing = store.get(eid)
                    if existing:
                        seeded.append(existing)

            elif bucket in (7, 8):  # Review Required
                eid = f"uat-case-{i+1:03d}-review"
                if store.get(eid) is None:
                    sub_type = i % 3
                    if sub_type == 0:
                        issue_label = "Missing Weight in SI"
                        si = f"""[SHIPPING INSTRUCTION]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Container Count: {cnt}
Description: {cargo}
"""
                        bl = f"""[BILL OF LADING]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Container Count: {cnt}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""
                    elif sub_type == 1:
                        issue_label = "Missing Container Count in BL"
                        si = f"""[SHIPPING INSTRUCTION]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Container Count: {cnt}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""
                        bl = f"""[BILL OF LADING]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""
                    else:
                        issue_label = "Missing Port of Loading in SI"
                        si = f"""[SHIPPING INSTRUCTION]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Discharge: {pod}
Container Count: {cnt}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""
                        bl = f"""[BILL OF LADING]
Shipper: {c_name}
Consignee: {consignee}
Notify Party: SAME AS CONSIGNEE
Port of Loading: {pol}
Port of Discharge: {pod}
Container Count: {cnt}
Gross Weight: {wt:,.2f} KGS
Description: {cargo}
"""

                    email = EmailRecord(
                        email_id=eid,
                        sender=c_email,
                        subject=f"[UAT] Review Required - Booking #UAT-{1000+i} ({issue_label})",
                        body="Please review documentation. Required shipping data must be audited by reviewer.",
                        attachments=[
                            AttachmentReference(document_id=f"{eid}_SI.txt", path=f"{eid}_SI.txt"),
                            AttachmentReference(document_id=f"{eid}_BL.txt", path=f"{eid}_BL.txt"),
                        ],
                    )
                    rec = orchestrator.process_email(
                        email,
                        document_texts={f"{eid}_SI.txt": si, f"{eid}_BL.txt": bl},
                    )
                    seeded.append(rec)
                else:
                    existing = store.get(eid)
                    if existing:
                        seeded.append(existing)

            else:  # Multi-category auxiliary distribution (new_si, invoice, spam, general, unresolved)
                sub = (i // 10) % 5
                if sub == 0:
                    eid = f"uat-case-{i+1:03d}-si"
                    if store.get(eid) is None:
                        email = EmailRecord(
                            email_id=eid,
                            sender=c_email,
                            subject=f"[UAT] Request SI Submission _ Booking #UAT-{1000+i}",
                            body=f"Please find attached new shipping instruction for booking UAT-{1000+i}.",
                            attachments=[],
                        )
                        rec = orchestrator.process_email(email)
                        seeded.append(rec)
                    else:
                        existing = store.get(eid)
                        if existing:
                            seeded.append(existing)
                elif sub == 1:
                    eid = f"uat-case-{i+1:03d}-invoice"
                    if store.get(eid) is None:
                        email = EmailRecord(
                            email_id=eid,
                            sender=c_email,
                            subject=f"[UAT] Query on Invoice #INV-{1000+i} - Demurrage Charges",
                            body=f"Good day, please clarify telex release charges and local charges for booking UAT-{1000+i}.",
                            attachments=[],
                        )
                        rec = orchestrator.process_email(email)
                        seeded.append(rec)
                    else:
                        existing = store.get(eid)
                        if existing:
                            seeded.append(existing)
                elif sub == 2:
                    eid = f"uat-case-{i+1:03d}-spam"
                    if store.get(eid) is None:
                        email = EmailRecord(
                            email_id=eid,
                            sender="promo@freight-specials.com",
                            subject=f"[UAT] Exclusive Offer: Increase your shipping revenue by 50%",
                            body="Click here for promotional offer and casino prizes. Marketing solicitation.",
                            attachments=[],
                        )
                        rec = orchestrator.process_email(email)
                        seeded.append(rec)
                    else:
                        existing = store.get(eid)
                        if existing:
                            seeded.append(existing)
                elif sub == 3:
                    eid = f"uat-case-{i+1:03d}-general"
                    if store.get(eid) is None:
                        email = EmailRecord(
                            email_id=eid,
                            sender=c_email,
                            subject=f"[UAT] Sailing Schedule Update - Asia to Europe #UAT-{1000+i}",
                            body=f"Good day, please find latest vessel sailing schedule update for {pol} to {pod}.",
                            attachments=[],
                        )
                        rec = orchestrator.process_email(email)
                        seeded.append(rec)
                    else:
                        existing = store.get(eid)
                        if existing:
                            seeded.append(existing)
                else:
                    eid = f"uat-case-{i+1:03d}-unresolved"
                    if store.get(eid) is None:
                        email = EmailRecord(
                            email_id=eid,
                            sender=c_email,
                            subject=f"[UAT] Inbound inquiry regarding shipment reference #{1000+i}",
                            body=f"Hello operational team, following up on our previous correspondence. Best regards, {c_name}.",
                            attachments=[],
                        )
                        rec = orchestrator.process_email(email)
                        seeded.append(rec)
                    else:
                        existing = store.get(eid)
                        if existing:
                            seeded.append(existing)

    logger.info("Seeded %d synthetic UAT demo records into AuditStore.", len(seeded))
    return seeded


def maybe_seed_uat_demo_records(store: AuditStore) -> Optional[List[AuditRecord]]:
    """Seed UAT demo records if and only if SDOC_UAT_DEMO_SEED is set."""
    if is_uat_demo_seed_enabled():
        return seed_uat_demo_records(store)
    return None
