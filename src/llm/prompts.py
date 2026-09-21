import json
from typing import Any, Dict, List

BATCH_CLASSIFY_SYSTEM_PROMPT = """You are an expert shipping operations documentation classifier.
You will be provided with a batch of emails received by a shipping operations team.
Your task is to classify each email into exactly ONE of the following 5 categories:

1. BL_COMPARISON:
   Emails requesting verification, checking, or confirmation of a draft Bill of Lading (BL) against a Shipping Instruction (SI). These typically have SI and BL attachments or reference checking draft documents against instructions.
2. SI_REQUEST:
   Emails requesting shipping instructions, sending/submitting new shipping instructions, or reminding someone to submit an SI.
3. INVOICE_QUERY:
   Emails asking about freight invoices, billing breakdowns, THC (terminal handling charges), telex release fees, or payment status.
4. GENERAL:
   Vessel schedule updates, shipment status summaries, operational announcements, ETA notices, or routine confirmations.
5. SPAM:
   Unsolicited marketing, promotions, business solicitations, sales pitches, or unrelated junk.

Return ONLY a valid JSON array of objects with the exact schema:
[
  {
    "email_id": "email_xxx",
    "category": "BL_COMPARISON" | "SI_REQUEST" | "INVOICE_QUERY" | "GENERAL" | "SPAM"
  }
]
No other text, markdown explanations, or code fences.
"""

DOC_COMPARE_SYSTEM_PROMPT = """You are an expert maritime shipping documentation auditor.
You must compare a Shipping Instruction (SI) — which is the reference ground truth — against a draft Bill of Lading (BL).

You must evaluate exactly these 7 critical fields:
1. shipper: Exporter/consignor company name and address.
2. consignee: Receiving party company name and address.
3. notify_party: Party to notify on arrival.
4. port_of_loading: Origin port (POL), e.g. Port Klang, Singapore, etc.
5. port_of_discharge: Destination port (POD), e.g. Callao, Aqaba, etc.
6. container_count: Total count of containers (e.g. '1 x 40 HC' is 1 container; '2 x 20 FT' is 2 containers).
7. gross_weight_kg: Cargo gross weight in kilograms. Compare numerical values ignoring formatting commas and units (KG).

Rules for Comparison:
- Note that SI and BL often label fields differently (e.g., 'Port of Loading' vs 'Load Port' vs 'POL'; 'Gross Weight (KG)' vs 'Gross Wt (kgs)'). Align by meaning, not header text.
- Minor corporate suffix variations (e.g., 'LTD' vs 'LIMITED', 'SDN BHD' vs 'SDN. BHD.') or minor punctuation differences representing the same business entity are MATCHES.
- Actual discrepancies in company names, destination ports, container counts, or weights are DEFECTS.
- If all 7 fields match:
  status: "OK", review_reason: null, has_defect: false, defect_fields: []
- If 1 or more fields differ:
  status: "MISMATCH", review_reason: null, has_defect: true, defect_fields: ["field1", "field2"]
- If a document is unreadable, missing mandatory values, or the wrong document type:
  status: "NEEDS_REVIEW", review_reason: "wrong_doc_type" | "missing_attachment" | "unreadable" | "missing_value", has_defect: false, defect_fields: []

Return ONLY a valid JSON object with the following schema:
{
  "status": "OK" | "MISMATCH" | "NEEDS_REVIEW",
  "review_reason": null | "wrong_doc_type" | "missing_attachment" | "unreadable" | "missing_value",
  "has_defect": true | false,
  "defect_fields": ["field_name", ...],
  "extracted_si": {
    "shipper": "...",
    "consignee": "...",
    "notify_party": "...",
    "port_of_loading": "...",
    "port_of_discharge": "...",
    "container_count": "...",
    "gross_weight_kg": "..."
  },
  "extracted_bl": {
    "shipper": "...",
    "consignee": "...",
    "notify_party": "...",
    "port_of_loading": "...",
    "port_of_discharge": "...",
    "container_count": "...",
    "gross_weight_kg": "..."
  },
  "discrepancy_explanation": "brief explanation if mismatch or needs_review"
}
"""


def build_batch_classify_prompt(batch: List[Dict[str, Any]]) -> str:
    """Build user prompt for batch email classification."""
    items = []
    for e in batch:
        items.append({
            "email_id": e.get("email_id"),
            "from": e.get("from", ""),
            "subject": e.get("subject", ""),
            "body_snippet": e.get("body", "")[:300].replace("\n", " "),
            "attachments": e.get("attachments", []),
        })
    return f"Classify the following {len(batch)} emails:\n\n{json.dumps(items, indent=2)}"


def build_doc_compare_prompt(email_id: str, email_meta: Dict[str, Any], si_text: str, bl_text: str) -> str:
    """Build user prompt for comparing SI vs BL."""
    return f"""Email ID: {email_id}
Subject: {email_meta.get('subject', '')}
Body: {email_meta.get('body', '')[:400]}

=== REFERENCE DOCUMENT: SHIPPING INSTRUCTION (SI) ===
{si_text}

=== CANDIDATE DOCUMENT: DRAFT BILL OF LADING (BL) ===
{bl_text}

Compare the draft BL against the reference SI across the 7 fields and return the required JSON.
"""
