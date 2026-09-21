# PRODUCT_SPEC.md — Shipping Document Verification Product Specification

> **Document Type**: Authoritative Product Requirements Specification  
> **Source of Truth**: [`Shipping Document Verification Use Case.pdf`](file:///d:/ship/Shipping%20Document%20Verification%20Use%20Case.pdf)  
> **Methodology**: Spec-Driven Development (SDD) — Phase 1 Requirements Engineering  
> **Status**: Awaiting User Review & Approval  

---

## 1. Problem Statement

A maritime shipping operations team manages a high-volume shared email inbox containing heterogeneous operational communications:
1. **Inbox Triage Bottleneck**: Operations staff must manually read through every inbound message to identify actionable document-checking requests amidst general operational chatter, invoice inquiries, new shipping instruction submissions, and promotional spam. Overlooked emails delay downstream logistics.
2. **High-Risk Manual Comparison**: For document-checking requests, operators must compare a Shipping Instruction (SI) against a carrier draft Bill of Lading (BL) across multiple dense fields. Manual cross-referencing is repetitive, prone to fatigue, and slow. Overlooked discrepancies lead to customs detention, carrier amendment fees, delayed cargo releases, and commercial disputes.
3. **Semantic and Layout Heterogeneity**: Information across documents does not follow uniform formatting or naming conventions. One document may label a field "Port of Loading" while another uses "Load Port" or "POL". Different file formats (plain text, Word documents, Excel spreadsheets, scanned or digital PDFs) further complicate extraction.
4. **Lack of Transparent Escalation**: Existing ad-hoc automated tools often fail silently or hallucinate guesses on ambiguous or illegible inputs, creating false confidence rather than routing uncertainty to human operators with audit-ready evidence.

---

## 2. Project Goals

1. **Automated Triage**: Automatically classify 100% of inbound emails into verified operational categories.
2. **Zero False Alarms in Verification**: Accurately extract and compare the 7 mandatory shipment fields between the reference SI and candidate draft BL, distinguishing benign formatting variations from real commercial discrepancies.
3. **Audit-Ready Discrepancy Reporting**: Produce structured reports displaying exact mismatched fields with side-by-side values (`SI: <val> / BL: <val>`), or confirm `"No mismatch detected"`.
4. **Dependable Human-in-the-Loop (HITL)**: Proactively detect corrupted, missing, ambiguous, or illegible documents and escalate them to human operators with explicit reason codes and source evidence snippets.
5. **Standardized Evaluation Delivery**: Comply with automated evaluation contracts and expose a public HTTP interface for automated scoring and examiner inspection.

---

## 3. Actors

1. **Shipping Operations Specialist (Primary User)**: Reviews triage results, inspects flagged discrepancies, reviews HITL escalations, and confirms whether to release the draft BL to the carrier.
2. **Carrier / Freight Forwarder (External Sender)**: Issues draft Bills of Lading and operational email updates.
3. **Shipper / Customer (External Sender)**: Issues Shipping Instructions and invoice inquiries.
4. **Evaluation Engine / Examiner (Auditor)**: Ingests automated submission artifacts (`submission.json` / REST endpoints) to compute accuracy, F1 scores, and reliability metrics.
5. **System / AI Verification Engine**: Ingests inbox records, executes document parsers, runs semantic normalization, and generates audit contracts.

---

## 4. Functional Requirements

### 4.1 General Pipeline & Control
- **FR-001** `[SOURCE: PDF Page 1]`: The system MUST ingest email records from the inbox dataset in JSON format.
- **FR-002** `[SOURCE: PDF Page 1]`: The system MUST categorize every email record into exactly one designated category before any document checking occurs.
- **FR-003** `[SOURCE: PDF Page 1]`: The system MUST execute SI/BL document extraction and comparison ONLY for emails classified as document-comparison requests.
- **FR-004** `[SOURCE: PDF Page 1]`: For all non-document-comparison emails, the system MUST terminate document checking immediately after classification.

### 4.2 Document Extraction & Ingestion
- **FR-005** `[SOURCE: PDF Page 1, 3]`: The system MUST parse plain-text (`.txt`) attachments referenced in email records.
- **FR-006** `[SOURCE: PDF Page 2]`: The system MUST support advanced attachment formats, specifically Microsoft Word (`.docx`), Excel spreadsheets (`.xlsx`), and Adobe PDF (`.pdf`).
- **FR-007** `[SOURCE: PDF Page 2]`: The system MUST handle table layouts, key-value listings, and free-form paragraph structures within attachments.
- **FR-008** `[SOURCE: PDF Page 2]`: The system MUST support scanned or image-only PDF documents via OCR or vision-capable models.

### 4.3 Comparison Engine
- **FR-009** `[SOURCE: PDF Page 1]`: The system MUST treat the Shipping Instruction (SI) as the sole reference ground truth for comparison.
- **FR-010** `[SOURCE: PDF Page 2]`: The system MUST verify exactly and only seven mandatory fields:
  1. `shipper`
  2. `consignee`
  3. `notify party` (or `notify_party`)
  4. `port of loading` (or `port_of_loading`)
  5. `port of discharge` (or `port_of_discharge`)
  6. `container count` (or `container_count`)
  7. `gross weight` (or `gross_weight_kg`)
- **FR-011** `[SOURCE: PDF Page 2]`: If all seven fields agree between the SI and BL, the system MUST return the exact phrase `"No mismatch detected"`.
- **FR-012** `[SOURCE: PDF Page 2]`: If one or more fields differ, the system MUST flag the specific mismatched fields and present the values side by side in the format: `SI: <value> / BL: <value>`.

### 4.4 Human-in-the-Loop (HITL) Escalation
- **FR-013** `[SOURCE: PDF Page 1, 2]`: When the system cannot form a dependable decision, it MUST escalate the case for human review rather than guessing or failing silently.
- **FR-014** `[SOURCE: PDF Page 2]`: The system MUST trigger human review when:
  - An attachment is missing or cannot be opened/read.
  - A mandatory comparison field is missing from either document.
  - A document is a scanned image with illegible or low-confidence text.
  - An attachment represents the wrong document type.
- **FR-015** `[SOURCE: PDF Page 2]`: Every escalation MUST provide the human reviewer with the specific `review_reason` and an extracted `source_evidence` text snippet.
- **FR-016** `[SOURCE: PDF Page 2]`: The system SHOULD allow human operators to review, confirm, or correct findings and subsequently update the report.
- **FR-017** `[SOURCE: PDF Page 2]`: The system MUST handle processing failures visibly and allow retries.

---

## 5. Non-Functional Requirements

- **NFR-001 (Deterministic Repeatability)** `[PROPOSED DESIGN DECISION]`: Running the pipeline against the static dataset MUST produce identical classifications and comparison results across multiple executions.
- **NFR-002 (Performance & Throughput)** `[PROPOSED DESIGN DECISION]`: The pipeline SHOULD process the entire 520-email inbox bundle in under 60 seconds when utilizing local heuristic/parser engines, or under 5 minutes when utilizing batched LLM APIs.
- **NFR-003 (Robustness against Corrupted Files)** `[SOURCE: PDF Page 2]`: Truncated, malformed, or unreadable attachments (e.g. EOF stream errors) MUST NOT crash the process; they must be gracefully captured and recorded as unreadable.
- **NFR-004 (Extensibility & Pluggability)** `[PROPOSED DESIGN DECISION]`: Document parsers and OCR modules MUST be decoupled via abstract interfaces (`BaseParser`) to enable plug-and-play addition of cloud OCR engines (e.g. Google Cloud Document AI).
- **NFR-005 (Schema Integrity)** `[SOURCE: PDF Page 4]`: All output files MUST strictly adhere to the expected JSON schemas without missing email IDs or invalid field types.

---

## 6. Email Classification Requirements

- **EC-001 (Target Categories)** `[SOURCE: PDF Page 1, Bundle README]`: Every email MUST be categorized into one of the following five classes:
  1. `document_comparison` (or `BL_COMPARISON`): Emails requesting draft BL confirmation or cross-check against SI.
  2. `new_si_request` (or `SI_REQUEST`): Emails requesting, submitting, or reminding about Shipping Instructions.
  3. `invoice_query` (or `INVOICE_QUERY`): Questions regarding billing, THC, telex release fees, or freight payment.
  4. `general_message` (or `GENERAL`): Routine vessel schedules, shipment status summaries, or operational announcements.
  5. `spam` (or `SPAM`): Unsolicited marketing, sales pitches, or promotional noise.
- **EC-002 (Single-Label Exclusivity)** `[SOURCE: PDF Page 1]`: Each email MUST belong to exactly one category.
- **EC-003 (Attachment Pre-Filter Heuristic)** `[PROPOSED DESIGN DECISION]`: Emails with zero attachments that do not mention draft BL checking MUST NOT be classified as `document_comparison`.

---

## 7. Document Extraction Requirements

- **DE-001 (Header Invariance)** `[SOURCE: PDF Page 1, 2]`: The system MUST align fields by semantic meaning rather than literal header strings.
- **DE-002 (Port of Loading Aliases)** `[SOURCE: PDF Page 1, 2]`: The system MUST recognize aliases for Port of Loading: `Port of Loading`, `Load Port`, `POL`, `Loading Port`, `Port of Load`.
- **DE-003 (Port of Discharge Aliases)** `[SOURCE: PDF Page 1, 2]`: The system MUST recognize aliases for Port of Discharge: `Port of Discharge`, `Discharge Port`, `POD`, `Discharging Port`, `Destination Port`.
- **DE-004 (Gross Weight Aliases)** `[SOURCE: PDF Page 1, 2]`: The system MUST recognize aliases for Gross Weight: `Gross Weight`, `Total Weight`, `G.W.`, `Cargo Weight`, `Gross Wt`, `Weight (KG)`.
- **DE-005 (Container Count Aliases)** `[SOURCE: PDF Page 1, 2]`: The system MUST recognize aliases for Container Count: `Container Count`, `Total Containers`, `Qty of Units`, `No. of Containers`, `Number of Containers`, `Containers or Packages`.
- **DE-006 (Entity Identification)** `[SOURCE: PDF Page 2]`: The system MUST extract company names and addresses for `shipper`, `consignee`, and `notify party`.
- **DE-007 (Table & Column Extraction)** `[SOURCE: PDF Page 2]`: For `.docx` and `.xlsx` files, the system MUST extract cell contents across tabular rows and sheets.

---

## 8. SI vs BL Comparison Requirements

- **CR-001 (Golden Reference)** `[SOURCE: PDF Page 1]`: The Shipping Instruction (SI) is the benchmark. Any difference in the draft Bill of Lading (BL) relative to the SI constitutes a defect.
- **CR-002 (Numeric Container Verification)** `[SOURCE: PDF Page 2]`: Container counts MUST be compared as pure numeric quantities. Variations such as `"3 containers"` vs `"3 x 40'HC"` MUST match if the count is 3.
- **CR-003 (Gross Weight Unit Normalization)** `[SOURCE: PDF Page 2]`: Gross weight MUST be normalized to kilograms (kg) before comparison:
  - Metric Tons (MT) MUST be multiplied by 1000.
  - Commas and formatting characters MUST be removed.
  - Numeric values MUST match within a tolerance of $\pm 1.0\text{ kg}$.
- **CR-004 (Port Matching & Code Resolution)** `[SOURCE: PDF Page 2]`: Ports MUST be evaluated by matching either the UN/LOCODE (e.g. `MYPKG`) or the normalized port city and country name.
- **CR-005 (Corporate Suffix Tolerance)** `[PROPOSED DESIGN DECISION]`: Variations in legal entity punctuation or standard abbreviations (`LTD` vs `LTD.` vs `LIMITED`; `SDN BHD` vs `SDN. BHD.`) representing the same legal entity MUST NOT be flagged as defects.
- **CR-006 (Zero False Alarms)** `[SOURCE: PDF Page 2]`: The comparison engine MUST NOT trigger false alarms on benign formatting or capitalization differences.

---

## 9. Human-in-the-Loop (HITL) Requirements

- **HL-001 (Escalation Triggering)** `[SOURCE: PDF Page 2]`: When automated comparison cannot proceed with high confidence, the system MUST generate an escalation record.
- **HL-002 (Structured Escalation Reasons)** `[SOURCE: PDF Bundle README]`: The system MUST assign one of four standardized reason codes:
  1. `wrong_doc_type`: Attachment is not a valid SI or draft BL.
  2. `missing_attachment`: Missing either the SI or draft BL file.
  3. `unreadable`: Corrupt stream, unparseable binary, or illegible image scan.
  4. `missing_value`: One of the 7 mandatory fields is absent or empty in the document.
- **HL-003 (Audit Evidence Preservation)** `[SOURCE: PDF Page 2]`: Escalation records MUST preserve the specific source evidence (e.g. error message, file name, or surrounding text snippet).
- **HL-004 (No Silent Guessing)** `[SOURCE: PDF Page 1, 2]`: The system is strictly forbidden from hallucinating or guessing values for unreadable or missing fields.

---

## 10. Error Handling Requirements

- **EH-001 (File System Fault Tolerance)** `[PROPOSED DESIGN DECISION]`: If an attachment referenced by an email does not exist on disk, the system MUST catch the error and escalate with `missing_attachment`.
- **EH-002 (Parser Exceptions)** `[PROPOSED DESIGN DECISION]`: Corrupt PDF streams (`PdfStreamError`), malformed Word archives, or unreadable Excel workbooks MUST be intercepted and recorded as `unreadable`.
- **EH-003 (LLM API Failure Fallback)** `[PROPOSED DESIGN DECISION]`: If an external LLM call encounters rate limits (HTTP 429) or network outages, the system MUST retry with exponential backoff, and fall back to local deterministic rule engines if retries expire.

---

## 11. Input Data Contract

### 11.1 Email Record JSON Schema (`inbox/email_*.json`)
```json
{
  "email_id": "string (e.g. 'email_001')",
  "from": "string (email address)",
  "subject": "string",
  "body": "string",
  "attachments": [
    "string (relative path, e.g. 'attachments/email_001_SI.txt')"
  ]
}
```

### 11.2 Attachment Types
- Plain text: `.txt` (UTF-8, Latin-1, CP1252)
- Word documents: `.docx`
- Excel workbooks: `.xlsx`
- Portable Document Format: `.pdf` (text-based and scanned images)

---

## 12. Output Data Contract

### 12.1 Contract A: Strict Operator Audit Schema (`audit_report.json` / REST `/audit`)
```json
{
  "email_id": "email_025",
  "category": "document_comparison",
  "mismatch_detected": true,
  "result_summary": "Mismatches detected: container_count (SI: 6 / BL: 5)",
  "discrepancies": [
    {
      "field": "container_count",
      "si_value": 6,
      "bl_value": 5
    }
  ],
  "hitl_escalation": {
    "needed": false,
    "reason": null,
    "evidence": null
  }
}
```

### 12.2 Contract B: Official Competition Schema (`submission.json` / REST `/submission`)
```json
{
  "email_001": {
    "category": "GENERAL",
    "status": "OK",
    "review_reason": null,
    "defect_fields": [],
    "has_defect": false
  }
}
```
*Where `status` $\in \{\text{"OK"}, \text{"MISMATCH"}, \text{"NEEDS_REVIEW"}\}$, and `defect_fields` $\subseteq \{\text{"shipper"}, \text{"consignee"}, \text{"notify_party"}, \text{"port_of_loading"}, \text{"port_of_discharge"}, \text{"container_count"}, \text{"gross_weight_kg"}\}$.*

---

## 13. User Stories

- **US-001**: As a shipping operations specialist, I want the system to filter out spam, general announcements, and invoice questions so that I can focus only on urgent draft BL reviews.
- **US-002**: As an operator, I want all matching documents to clearly state `"No mismatch detected"` so that I can immediately release the draft BL with confidence.
- **US-003**: As an operator, when a discrepancy exists (e.g. container count 3 vs 4), I want to see `SI: 3 / BL: 4` side by side so that I can instruct the carrier to correct the draft without re-reading the entire file.
- **US-004**: As an operator, when an attachment is corrupted or missing, I want the system to alert me with the specific reason and snippet so that I can request a replacement file from the customer immediately.
- **US-005**: As a competition examiner, I want to submit `submission.json` or query the public HTTP API to verify macro-F1 classification and defect detection accuracy.

---

## 14. Acceptance Criteria

- **AC-001**: 100% of the 520 emails in the inbox dataset MUST be present in the output submission.
- **AC-002**: For matching document pairs, `mismatch_detected` MUST be `false` and `result_summary` MUST equal `"No mismatch detected"`.
- **AC-003**: For defective document pairs, `mismatch_detected` MUST be `true`, `has_defect` MUST be `true`, and all differing fields MUST be listed.
- **AC-004**: Single-attachment emails (e.g. `email_507`, `email_509`) MUST be escalated to `NEEDS_REVIEW` with reason `missing_attachment`.
- **AC-005**: Corrupted PDFs with EOF errors (e.g. `email_511`, `email_515`) MUST be escalated to `NEEDS_REVIEW` with reason `unreadable`.
- **AC-006**: Non-comparison emails (`SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`) MUST NOT trigger document comparison and MUST have `mismatch_detected: false` and `has_defect: false`.
- **AC-007**: The output schema MUST pass 100% compliance against `sample_submission.json`.

---

## 15. Edge Cases Discovered in Dataset

1. **Missing Attachment**: `email_507` and `email_509` contain only 1 attachment (`_SI.txt` only, no BL).
2. **Truncated / Corrupt PDF Streams**: `email_511_BL.pdf` and `email_515_BL.pdf` trigger `EOF marker not found` / `PdfStreamError`.
3. **Scanned Image PDFs with Zero Text**: `email_512`, `email_513`, and `email_514` contain no machine-readable font text layer (require OCR or escalation to `unreadable`).
4. **Header and Label Variations**: Headers such as `No. of Containers or Packages:`, `Total Containers:`, `Port of Loading (POL):`, and `POD:`.
5. **Metric Ton vs Kilogram Units**: Invoices and SIs using `MT` (Metric Tons) which require multiplication by 1000 to compare against BL values in `KG`.

---

## 16. Assumptions

1. The provided static dataset (`sdoc-hackathon-bundle`) represents the benchmark ground truth distribution for testing and evaluation.
2. An email with 2 attachments named `*_SI.*` and `*_BL.*` is intended for document comparison.
3. The Shipping Instruction (SI) is always the authoritative reference; discrepancies in the BL must be changed to match the SI, not vice versa.
4. Corporate legal suffix differences (such as `Ltd` vs `Limited`) do not constitute commercial defects in shipping operations unless the company name itself differs.

---

## 17. Out-of-Scope Items

1. Direct integration with live SMTP / IMAP mail servers (the system reads static JSON inbox records or HTTP evaluation endpoints).
2. Automatic modification or writing back to original customer SI or carrier BL binary files.
3. Financial ledger accounting or automated bank payment processing for invoice query emails.
4. Modifying the 7 mandatory comparison fields or adding speculative extra comparison fields (such as HS codes, vessel names, or voyage numbers) to the official evaluation score.

---

## 18. Open Questions & Architectural Decisions for User Review

- **OQ-001 (OCR Engine Choice for Scanned Documents)**: For image-only PDFs (`email_512` to `email_514`), should the production deployment enforce Gemini Multimodal vision, local Tesseract OCR, or escalate directly to human review (`NEEDS_REVIEW` / `unreadable`)?  
  *(Currently implemented: Defaults to Gemini Multimodal with pluggable Google Cloud Document AI; escalates to `NEEDS_REVIEW` if OCR text is unavailable).*
- **OQ-002 (Weight Tolerance Window)**: What is the maximum acceptable rounding variance between SI and BL weights?  
  *(Currently implemented: $\pm 1.0\text{ kg}$).*
- **OQ-003 (Port UN/LOCODE vs Full Name)**: If an SI specifies `PORT KLANG (MYPKG)` and the draft BL specifies only `PORT KLANG`, is this considered a match or a defect?  
  *(Currently implemented: Match, because both resolve to the same underlying port facility).*
