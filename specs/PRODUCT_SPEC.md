# 00_PRODUCT_SPEC.md — Shipping Document Verification Product Specification

> **Document Type**: Authoritative Product Requirements Specification  
> **Source of Truth**: [`Shipping Document Verification Use Case.pdf`](file:///d:/ship/Shipping%20Document%20Verification%20Use%20Case.pdf)  
> **Methodology**: Spec-Driven Development (SDD) — Phase 1 Requirements Engineering  
> **Status**: APPROVED / BASELINED  
> **Revision**: 3.1 (Approved handoff synchronization, 2026-09-22)  
> **Change Record**: [AMENDMENT_2026-09-22.md](AMENDMENT_2026-09-22.md)  

Requirement levels are `CORE`, `ADVANCED`, `DESIGN EXTENSION`, and `EVALUATION`. A source citation identifies the capability in the original use case; concrete implementation policies are identified separately as design decisions. Proposed operational targets are not approved acceptance criteria.

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
2. **Accurate Verification**: Extract and compare the seven mandatory shipment fields, distinguishing approved formatting variations from real discrepancies. Do not claim zero false alarms without empirical evaluation evidence.
3. **Audit-Ready Discrepancy Reporting**: Produce structured reports displaying exact mismatched fields with side-by-side values (`SI: <val> / BL: <val>`), or confirm `"No mismatch detected"`.
4. **Dependable Human-in-the-Loop (HITL)**: Proactively detect corrupted, missing, ambiguous, or illegible documents and escalate them to human operators with explicit reason codes and source evidence snippets.
5. **Evaluation Delivery**: When self-evaluation is used, provide the agreed submission format. The approved REST application architecture is defined in `01_PROJECT_DESIGN.md`; public hosting is not a source requirement.

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
- **FR-005** `[CORE; SOURCE: PDF Page 1, 3]`: The system MUST parse plain-text (`.txt`) attachments referenced in email records.
- **FR-006**: Format support beyond TXT is separated by requirement level:
  - **FR-006A** `[ADVANCED; SOURCE: PDF Page 2]`: Word (`.docx`).
  - **FR-006B** `[ADVANCED; SOURCE: PDF Page 2]`: PDF (`.pdf`).
  - **FR-006C** `[DESIGN EXTENSION; APPROVED DESIGN]`: Excel (`.xlsx`), not an explicit original-use-case requirement.
- **FR-007** `[SOURCE: PDF Page 2]`: The system MUST handle table layouts, key-value listings, and free-form paragraph structures within attachments.
- **FR-008** `[SOURCE: PDF Page 2]`: The system MUST support scanned or image-only PDF documents via OCR or vision-capable models.

### 4.3 Comparison Engine
- **FR-009** `[CORE; SOURCE: PDF Page 1; APPROVED RELIABILITY POLICY]`: The SI is the reference document for comparison, not infallible truth. Missing, unreadable, conflicting, or uncertain SI information requires HITL when it cannot be reliably resolved.
- **FR-010** `[SOURCE: PDF Page 2]`: The system MUST verify exactly and only seven mandatory fields:
  1. `shipper`
  2. `consignee`
  3. `notify party` (or `notify_party`)
  4. `port of loading` (or `port_of_loading`)
  5. `port of discharge` (or `port_of_discharge`)
  6. `container count` (or `container_count`)
  7. `gross weight` (or `gross_weight_kg`)
- **FR-011** `[SOURCE: PDF Page 2; APPROVED FIELD-LEVEL GATE]`: Only after all seven fields are reliably established in both documents and match under approved deterministic normalization may the system return the final phrase `"No mismatch detected"`.
- **FR-012** `[SOURCE: PDF Page 2]`: If one or more fields differ, the system MUST flag the specific mismatched fields and present the values side by side in the format: `SI: <value> / BL: <value>`.

### 4.4 Human-in-the-Loop (HITL) Escalation
- **FR-013** `[SOURCE: PDF Page 1, 2]`: When the system cannot form a dependable decision, it MUST escalate the case for human review rather than guessing or failing silently.
- **FR-014** `[SOURCE: PDF Page 2; APPROVED RECOVERY POLICY: DEC-P02]`: The system MUST trigger human review when the required result cannot be reliably established. For unusable/scanned content, attempt applicable OCR/Vision and approved recovery before escalation; record why recovery is unavailable or fails. Cases include:
  - An attachment is missing or cannot be opened/read.
  - A mandatory comparison field is missing from either document.
  - A document is a scanned image whose required fields remain illegible or uncertain after applicable recovery; model-reported confidence alone is not a reliability gate.
  - An attachment represents the wrong document type.
- **FR-015** `[SOURCE: PDF Page 2; APPROVED DESIGN: DEC-AI-P05]`: Every escalation MUST provide the reason and source-grounded evidence, which may include text spans, table cells, page locations, OCR regions, metadata, or processing-error context. Exact evidence contracts belong to `03_DATA_CONTRACTS.md`.
- **FR-016** `[SOURCE: PDF Page 2]`: The system SHOULD allow human operators to review, confirm, or correct findings and subsequently update the report.
- **FR-017** `[SOURCE: PDF Page 2]`: The system MUST handle processing failures visibly and allow retries.

---

## 5. Non-Functional Requirements

- **NFR-001 (Deterministic Repeatability)** `[APPROVED DESIGN: DEC-01]`: Identical validated canonical inputs and approved rule versions MUST produce identical deterministic comparison results. This does not assert that independent AI calls always return identical extractions or classifications.
- **NFR-002 (Performance & Throughput)** `[PROPOSED; NOT AN ACCEPTANCE GATE]`: Measure throughput and latency during evaluation. Numeric performance targets require a separately approved benchmark; no fixed dataset size or unapproved time threshold is normative.
- **NFR-003 (Robustness against Corrupted Files)** `[SOURCE: PDF Page 2]`: Truncated, malformed, or unreadable attachments (e.g. EOF stream errors) MUST NOT crash the process; they must be gracefully captured and recorded as unreadable.
- **NFR-004 (Extensibility & Pluggability)** `[APPROVED DESIGN: DEC-P01, DEC-P02]`: Decouple parsers and provider-agnostic AI/OCR adapters as defined in `01_PROJECT_DESIGN.md`. A new provider still requires the applicable approval; extensibility is not blanket provider authorization.
- **NFR-005 (Schema Integrity)** `[EVALUATION; SOURCE: PDF Page 4]`: When self-evaluation is used, the submission MUST follow `sample_submission.json` and include every input email ID. This evaluation format does not constrain internal models, which require their own validated contracts.

---

## 6. Email Classification Requirements

- **EC-001 (Target Categories)** `[SOURCE: PDF Page 1; APPROVED NAMING: HANDOFF / 02 §4.1]`: Every email MUST receive exactly one operational category. Evaluation aliases below are adapter mappings, not additional categories:
  1. `document_comparison` (or `BL_COMPARISON`): Emails requesting draft BL confirmation or cross-check against SI.
  2. `new_shipping_instruction` (evaluation: `SI_REQUEST`): Emails requesting, submitting, or reminding about Shipping Instructions.
  3. `invoice_query` (or `INVOICE_QUERY`): Questions regarding billing, THC, telex release fees, or freight payment.
  4. `general` (evaluation: `GENERAL`): Routine vessel schedules, shipment status summaries, or operational announcements.
  5. `spam` (or `SPAM`): Unsolicited marketing, sales pitches, or promotional noise.
- **EC-002 (Single-Label Exclusivity)** `[SOURCE: PDF Page 1]`: Each email MUST belong to exactly one category.
- **EC-003 (Intent Independent of Attachment Completeness)** `[APPROVED DESIGN: 02 §4.4]`: Attachment count MUST NOT act as a negative email-intent gate. A comparison request with missing attachments remains `document_comparison` and proceeds to attachment validation, then HITL for the missing document. Evidence is not limited to explicit keywords.

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

- **CR-001 (Reference Document)** `[SOURCE: PDF Page 1; APPROVED DESIGN: DEC-01]`: Compare reliable SI and draft BL values after approved normalization. AI may extract candidate values but MUST NOT make the final equality or mismatch decision. Unresolved SI values require review.
- **CR-002 (Numeric Container Verification)** `[SOURCE: PDF Page 2]`: Container counts MUST be compared as pure numeric quantities. Variations such as `"3 containers"` vs `"3 x 40'HC"` MUST match if the count is 3.
- **CR-003 (Gross Weight Unit Normalization)** `[SOURCE: PDF Page 2: kilograms; APPROVED DESIGN: DEC-P06A/B; TOLERANCE: DEC-P06E TBD]`: Gross weight MUST be normalized to kilograms before deterministic comparison:
  - Metric Tons (MT) MUST be multiplied by 1000.
  - Apply approved formatting and numeric-separator normalization.
  - Compare mathematically normalized values exactly. Numeric tolerance remains TBD; no implicit ±1 kg or other tolerance is authorized.
- **CR-004 (Port Value Equivalence)** `[TBD: DEC-P06C]`: Do not assume UN/LOCODE, city, port, and terminal names are equivalent without an approved canonical mapping amendment. Field-label aliases do not authorize field-value equivalence.
- **CR-005 (Organization Value Equivalence)** `[TBD: DEC-P06D]`: Do not broadly remove legal suffixes or infer company identity. Semantic aliases require explicit approved rules. Approved formatting normalization remains permitted.
- **CR-006 (Formatting Differences)** `[SOURCE: PDF Page 2; APPROVED DESIGN: DEC-P06A]`: Approved formatting and capitalization normalization must prevent spurious mismatches. Accuracy claims require evaluation evidence.

---

## 9. Human-in-the-Loop (HITL) Requirements

- **HL-001 (Escalation Triggering)** `[SOURCE: PDF Page 2]`: When automated comparison cannot proceed with high confidence, the system MUST generate an escalation record.
- **HL-002 (Evaluation Escalation Reasons)** `[EVALUATION; BUNDLE CONTRACT]`: The evaluation adapter uses four standardized reason codes:
  1. `wrong_doc_type`: Attachment is not a valid SI or draft BL.
  2. `missing_attachment`: Missing either the SI or draft BL file.
  3. `unreadable`: Corrupt stream, unparseable binary, or illegible image scan.
  4. `missing_value`: One of the 7 mandatory fields is absent or empty in the document.
  Internal logical causes also include uncertainty, conflicting candidates, and unresolved processing/provider failure as defined in `02` §13. Exact internal enums and any lossy evaluation mapping belong to `03`; do not silently invent mappings.
- **HL-003 (Audit Evidence Preservation)** `[SOURCE: PDF Page 2]`: Escalation records MUST preserve the specific source evidence (e.g. error message, file name, or surrounding text snippet).
- **HL-004 (No Silent Guessing)** `[SOURCE: PDF Page 1, 2]`: The system is strictly forbidden from hallucinating or guessing values for unreadable or missing fields.
- **HL-005 (Partial Reliable Work)** `[APPROVED DESIGN: DEC-AI-P04]`: HITL MUST retain reliable extractions, deterministic comparisons for fields reliable on both sides, and their evidence. Preserve unresolved fields and reasons separately; do not publish a definitive clean result before all seven fields are resolved.

---

## 10. Error Handling Requirements

- **EH-001 (File System Fault Tolerance)** `[PROPOSED DESIGN DECISION]`: If an attachment referenced by an email does not exist on disk, the system MUST catch the error and escalate with `missing_attachment`.
- **EH-002 (Parser Exceptions)** `[APPROVED RECOVERY POLICY]`: Intercept and record parser failures visibly. Assess usable content and applicable recovery/OCR paths; escalate when the required result cannot be reliably recovered. No empty-string success or fixed character-count OCR gate is permitted.
- **EH-003 (LLM API Failure Fallback)** `[APPROVED DESIGN: 02 §§14–15]`: Apply bounded, stage-specific retries and validated fallbacks. Provider failure alone does not require HITL if an approved fallback reliably produces the required result. Technical and semantic attempt defaults remain configurable as specified in `02`.

---

## 11. Input Data Contract

### 11.1 Email Record JSON Schema (`inbox/email_*.json`)
This illustrates the input bundle shape; canonical models and validation belong to `03_DATA_CONTRACTS.md`. IDs below are synthetic placeholders, not evaluation records.
```json
{
  "email_id": "string (e.g. 'example-message')",
  "from": "string (email address)",
  "subject": "string",
  "body": "string",
  "attachments": [
    "string (relative path, e.g. 'attachments/example-si.txt')"
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

The examples below illustrate reporting and evaluation shapes, not complete internal contracts. `03_DATA_CONTRACTS.md` must define evidence, partial results, review updates, and serialization consistently with `01` and `02`. Existing lower-level drafts require review where they differ from this amendment.

### 12.1 Contract A: Strict Operator Audit Schema (`audit_report.json` / REST `/audit`)
```json
{
  "email_id": "example-mismatch",
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
  "example-general": {
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

- **AC-001** `[EVALUATION]`: Every input email ID MUST be present in the output submission when self-evaluation is used; no fixed dataset size is assumed.
- **AC-002**: For matching document pairs, `mismatch_detected` MUST be `false` and `result_summary` MUST equal `"No mismatch detected"`.
- **AC-003**: For defective document pairs, `mismatch_detected` MUST be `true`, `has_defect` MUST be `true`, and all differing fields MUST be listed.
- **AC-004**: A document-comparison request missing the required SI or draft BL MUST require review with `missing_attachment`, including when there are no attachments. Non-comparison emails still terminate after classification.
- **AC-005**: Parser failures MUST be visible; where applicable, attempt approved recovery/OCR. If required content remains unreadable or no applicable recovery exists, escalate to review with the failure evidence. Preserve already reliable work.
- **AC-006**: Non-comparison emails (`SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`) MUST NOT trigger document comparison and MUST have `mismatch_detected: false` and `has_defect: false`.
- **AC-007** `[EVALUATION]`: When self-evaluation is used, its output MUST comply with `sample_submission.json`; this does not prescribe the internal schema.

---

## 15. General Reliability Scenarios

1. **Missing Attachment**: A comparison request lacks the SI or draft BL, regardless of filename or email ID.
2. **Truncated / Corrupt Streams**: Capture parser errors and recovery outcomes; escalate if required information cannot be recovered reliably.
3. **Scanned Documents**: Assess text usability, attempt applicable OCR/Vision, and escalate unresolved required fields.
4. **Header and Label Variations**: Headers such as `No. of Containers or Packages:`, `Total Containers:`, `Port of Loading (POL):`, and `POD:`.
5. **Metric Ton vs Kilogram Units**: Invoices and SIs using `MT` (Metric Tons) which require multiplication by 1000 to compare against BL values in `KG`.

---

## 16. Assumptions

1. Input records and source documents are read-only; the supplied dataset is not a source of hardcoded business rules or expected answers.
2. Filenames and metadata may help identify document roles, but do not independently determine email intent.
3. The SI is the comparison reference; uncertain SI content requires review. The application reports differences without modifying original documents.
4. Company and port semantic equivalence and numeric tolerances remain governed by DEC-P06C/D/E; current implementation behavior does not approve these rules.

---

## 17. Out-of-Scope Items

1. Direct integration with live SMTP / IMAP mail servers (the system reads static JSON inbox records or HTTP evaluation endpoints).
2. Automatic modification or writing back to original customer SI or carrier BL binary files.
3. Financial ledger accounting or automated bank payment processing for invoice query emails.
4. Modifying the 7 mandatory comparison fields or adding speculative extra comparison fields (such as HS codes, vessel names, or voyage numbers) to the official evaluation score.

---

## 18. Open Questions & Architectural Decisions for User Review

- **OQ-001 (OCR Architecture)** `[APPROVED: DEC-P01/P02]`: Use provider-agnostic adapters and attempt applicable OCR/Vision before escalating unusable/scanned content. This does not approve an additional cloud provider.
- **OQ-002 (Weight Tolerance)** `[TBD: DEC-P06E]`: Exact mathematically normalized comparison remains the default. A business tolerance requires an approved amendment.
- **OQ-003 (Port Equivalence)** `[TBD: DEC-P06C]`: An explicit canonical mapping requires an approved amendment; code/city/terminal equivalence is not presumed.
- **OQ-004 (Organization Equivalence)** `[TBD: DEC-P06D]`: Legal-suffix and company-name aliases require explicit approved rules; broad suffix stripping is not authorized.

## 19. Change Control

This synchronized product baseline implements the user's approved handoff decisions under the 2026-09-22 amendment. It does not authorize implementation changes, resolve DEC-P06C/D/E, or certify existing tests or runtime behavior. The numbered file is authoritative under `AGENTS.md`; `PRODUCT_SPEC.md` is maintained as an identical compatibility copy.
