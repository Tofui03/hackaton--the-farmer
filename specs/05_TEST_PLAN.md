# 05_TEST_PLAN.md — Verification, Testing & Quality Assurance Plan

> **Status**: APPROVED / BASELINED  
> **Revision**: 2.0-baselined (2026-09-22)  
> **Authority**: Original Use Case → [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) → [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) → [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) → [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) → [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md)  
> **Scope**: Comprehensive verification strategy, test taxonomy, test case catalogue, Master Verification Matrix, and gap analysis across all pipeline stages, AI adapters, data contracts, and UI workflows.  
> **Governance Constraint**: No production implementation code (`src/`), existing tests (`tests/`), or baselined specifications (`00`–`04`) are modified by this document.

---

## 1. Purpose

This document defines how every approved requirement, architectural decision, AI pipeline behavior, strict data contract, and frontend user workflow will be objectively and reproducibly verified.

It establishes the quality gates required before the Shipping Document Verification system can be deemed production-ready. Existing code and current test passes are **NOT** the source of truth; baselined specifications (`00` through `04`) are solely authoritative.

---

## 2. Scope

### 2.1 In Scope
- **Email Ingestion & Classification**: Verification of the 5 canonical email intent categories (`EC-001`), handling of ambiguous text, and decoupling of attachment count from classification intent (`EC-002`, `REG-001`).
- **Attachment Extraction & Role Resolution**: Verification of deterministic-first (`DEC-AI-P03`) and AI-on-demand identification of Shipping Instructions (SI) and draft Bills of Lading (BL).
- **Document Parsing & Text Usability**: Verification of TXT, DOCX, PDF, and XLSX parsers (`FR-005`, `FR-006A/B/C`, `DEC-P02`) against the qualitative Text Usability Validation model (no hardcoded character-count thresholds).
- **Field Extraction & Grounding**: Verification of all 7 mandatory comparison fields (`FR-010`), alternative field labels, multiline extractions, and strict `FieldEvidence` provenance citations (`DEC-AI-P05`, `DC-05`).
- **Deterministic Normalization & Comparison**: Verification of canonical normalizers (`DEC-P06A`, `DEC-P06B`), unit conversions, and exact match comparison logic (`DEC-01`), alongside negative regression checks preventing unapproved semantic equivalence (`DEC-P06C/D/E`).
- **Human-in-the-Loop (HITL) & Partial Preservation**: Verification of all 7 logical review reasons (`FR-013`, `FR-014`, `DEC-P02`), preservation of completed reliable work (`DEC-AI-P04`), and escalation payload integrity (`FR-015`).
- **Human Review & Optimistic Concurrency**: Verification of `ReviewUpdate` submission (`FR-016`), optimistic revision locking (`expected_revision`, `DC-07`), deterministic re-evaluation upon correction, and collision handling (HTTP 409).
- **REST API & Official Evaluation Adapter**: Verification of `/audit`, `/audit/{id}`, `/audit/{id}/review`, `/submission`, `/health` (`DEC-P03`, `NFR-005`), and safe `EXPORT_BLOCKED` behavior (`DC-08`).
- **Frontend Presentation & Accessibility**: Verification of the 4-column matrix, dedicated review workspace (`/cases/:email_id/review`), UI states, contract synchronization, and WCAG 2.1 AA accessibility targets.
- **Security, Data Integrity & Regression Suite**: Verification of read-only dataset isolation, credential protection, and explicit regression tests (REG-001 through REG-012).

### 2.2 Out of Scope
- Direct testing of proprietary external LLM weights or internal neural representations.
- Live external AI provider calls during routine deterministic CI runs (mocked deterministic adapters are authoritative for core verification).
- Automated resolution of business-governed domain equivalence rules (`DEC-P06C`, `DEC-P06D`, `DEC-P06E`), which remain open TBDs.
- Features formally classified as FUTURE in V1 (e.g. batch review confirmation, synchronized full-document split-screen PDF viewer).

---

## 3. Test Principles & Invariants

1. **Specifications Are Authoritative**: Existing test passes (e.g. 16/16 green) do not establish requirement compliance. When existing code or tests diverge from baselined specifications, the implementation is defective, not the specification.
2. **Deterministic Isolation**: Core business verification, unit tests, contract tests, and CI runs MUST execute 100% offline without live network dependencies on external LLM/OCR providers.
3. **Synthetic Fixtures Over Production Scraping**: Test fixtures must be synthetic, fully controlled, and isolated from evaluation dataset references. Tests must NEVER hardcode dataset-specific email IDs or embed private benchmark answers.
4. **No Semantic Leaks**: Tests must strictly enforce that the engine does not guess, hallucinate, or apply unauthorized fuzzy tolerances.
5. **Tri-State Integrity**: Tests must enforce that `mismatch_detected` is strictly tri-state (`true`, `false`, `null`). A case with unextracted or unresolved fields must NEVER emit `"No mismatch detected"`.
6. **Safety Invariance on Export**: Tests must verify that any case with unresolved intent, missing values, or unconfirmed review status triggers `EXPORT_BLOCKED` rather than fabricating default evaluation values.

---

## 4. Test Levels & Taxonomy

Verification is partitioned across 15 distinct test levels:

| Level | Code | Scope & Description | Execution Context |
|---|---|---|---|
| **A. Unit Tests** | `UT` | Isolated verification of pure functions (normalizers, math converters, diff checkers, validators). | Pytest (isolated, fast, in-memory) |
| **B. Contract Tests** | `CT` | Strict Pydantic v2 schema compliance for internal models, REST payloads, and evaluation formats. | Pytest (model instantiation & validation) |
| **C. Integration Tests** | `IT` | Multi-module interaction (e.g. parser output feeding extraction; review update triggering re-matching). | Pytest (synthetic filesystem fixtures) |
| **D. Pipeline Tests** | `PIPE` | End-to-end execution of Stages 1 through 4 using controlled synthetic email packages. | Pytest (pipeline orchestrator runner) |
| **E. AI Adapter Tests** | `AI` | Verification of schema enforcement, fallback chains, retry budgets, and error handling via mocked LLM responses. | Pytest (Mocked BaseAIAdapter fixtures) |
| **F. Parser / OCR Tests** | `PAR` | File format parsing (TXT, DOCX, PDF, XLSX) and Text Usability Validation rules. | Pytest (synthetic document files) |
| **G. HITL Workflow Tests** | `HITL` | Verification of review triggers, issue generation, partial work preservation, and escalation payloads. | Pytest (state machine & audit store) |
| **H. API Tests** | `API` | REST endpoint status codes, query filters, error structures (400, 404, 409, 422), and response models. | FastAPI TestClient |
| **I. Frontend Component** | `UI` | React component rendering, DOM semantics, badge styling, table structure, and drawer behaviors. | Vitest + React Testing Library |
| **J. Frontend Integration**| `UI-IT`| Multi-component frontend workflows (filter $\rightarrow$ select case $\rightarrow$ open drawer $\rightarrow$ review route). | Vitest + React Testing Library |
| **K. End-to-End Tests** | `E2E` | Full user journeys from email ingestion to queue inspection, human review correction, and export. | Pytest + Playwright (Headless browser) |
| **L. Evaluation Adapter** | `EVAL` | Lossless mapping from internal AuditRecord to official sample_submission.json schema and blocking rules. | Pytest (adapter transform assertions) |
| **M. Security & Integrity** | `SEC` | Dataset immutability, API credential masking, prompt encapsulation, and path traversal prevention. | Pytest + static code analysis |
| **N. Regression Tests** | `REG` | Explicit protection against recurring traps and previously rejected rules (REG-001 through REG-012). | Pytest (dedicated regression suite) |
| **O. Manual Acceptance** | `UAT` | Human operator inspection checklist validating operational usability and discrepancy clarity. | Manual execution by operations reviewer |

---

## 5. Test ID Convention

Test cases follow a strict, permanent identifier scheme:

$$\text{[SUITE]}-\text{[CATEGORY]}-\text{[NUMBER]}$$

- **`UT-xxx`**: Unit test (e.g. `UT-NORM-001`, `UT-EXT-001`)
- **`CT-xxx`**: Contract validation test (e.g. `CT-DATA-001`, `CT-REV-001`)
- **`AI-xxx`**: AI pipeline & adapter test (e.g. `AI-BUD-001`, `AI-ADP-001`)
- **`PAR-xxx`**: Parser & OCR text usability test (e.g. `PAR-PDF-001`, `PAR-USAB-001`)
- **`PIPE-xxx`**: Pipeline stage integration test (e.g. `PIPE-CLS-001`, `PIPE-CMP-001`)
- **`HITL-xxx`**: Human-in-the-loop escalation test (e.g. `HITL-RSN-001`, `HITL-PART-001`)
- **`API-xxx`**: REST API test (e.g. `API-AUD-001`, `API-REV-001`)
- **`UI-xxx`**: Frontend component & state test (e.g. `UI-DIFF-001`, `UI-REV-001`)
- **`EVAL-xxx`**: Evaluation adapter test (e.g. `EVAL-MAP-001`, `EVAL-BLOCK-001`)
- **`SEC-xxx`**: Security & data integrity test (e.g. `SEC-DATA-001`, `SEC-AUTH-001`)
- **`REG-xxx`**: Regression test (e.g. `REG-001` through `REG-012`)
- **`E2E-xxx`**: End-to-end system scenario (e.g. `E2E-001` through `E2E-016`)
- **`UAT-xxx`**: Operational acceptance scenario (e.g. `UAT-001` through `UAT-009`)

Every test specification defines: Test ID, Title, Requirement/Decision Reference, Level & Priority (`P0`–`P3`), Preconditions & Fixtures, Execution Steps, Expected Result, and Automation Status.

---

## 6. Test Data & Fixture Strategy

### 6.1 Synthetic Fixture Hierarchy
To prevent evaluation data leakage and guarantee test repeatability, tests rely on an isolated synthetic test directory (`tests/fixtures/`):

1. **`fixtures/emails/`**: Synthetic JSON emails covering all 5 categories, ambiguous texts, missing headers, and malformed structures.
2. **`fixtures/documents/txt/`**: Clean synthetic plain-text SI/BL pairs with known discrepancies and multi-line candidates.
3. **`fixtures/documents/docx/`**: Word documents featuring complex tables, nested cells, and header/footer metadata.
4. **`fixtures/documents/pdf/`**: 
   - Vector-text PDFs with exact layout structure.
   - Truncated/corrupted stream PDFs.
   - Image-only scanned PDFs (300 DPI synthetic scans).
   - Partially degraded PDFs (clear field tables, illegible footers).
5. **`fixtures/documents/xlsx/`**: Tabular Excel workbooks with multiple sheets and numeric formatting.
6. **`fixtures/ai_responses/`**: Recorded deterministic JSON payloads simulating LLM responses for classification, extraction, and schema violations.
7. **`fixtures/payloads/`**: Valid and invalid `ReviewUpdate` payloads for concurrency and correction testing.

### 6.2 Strict Data Integrity Rule
- **READ-ONLY EVALUATION BUNDLE**: Tests must never alter, overwrite, or delete files in `sdoc-hackathon-bundle/`.
- **NO HARDCODED EMAIL IDS**: Business logic and unit tests must not contain conditional branches keyed on specific email IDs (e.g. `if email_id == "email_025": ...`).

---

## 7. Unit Test Plan

Verifies pure functions in isolation: deterministic field extraction, grounding validation, canonical normalization, and unit conversion rules.

| Test ID | Title & Requirement | Tested Area | Input Variant | Expected Result & Invariant | Priority |
|---|---|---|---|---|---|
| `UT-EXT-001` | Standard Field Extraction (`FR-010`) | `shipper` | Standard label: `"Shipper: ACME EXPORTS LTD"` | Extracted raw: `"ACME EXPORTS LTD"`, `reliable = true`. | `P0` (Automated / Planned) |
| `UT-EXT-002` | Alternative Field Label (`FR-010`) | `shipper` | Alternative label: `"Consignor / Exporter: GLOBAL TRADE CORP"` | Extracted raw: `"GLOBAL TRADE CORP"`. Label equivalence accepted. | `P1` (Automated / Planned) |
| `UT-EXT-003` | Multiline Address Field (`FR-010`) | `consignee` | Consignee with 3-line corporate address block. | Preserves full text block without truncation; provenance spans lines 1–3. | `P1` (Automated / Planned) |
| `UT-EXT-004` | Notify Party "Same As" Reference (`FR-010`) | `notify_party` | Literal: `"SAME AS CONSIGNEE"` | Extracted raw: `"SAME AS CONSIGNEE"`. Normalizer resolves equivalence. | `P0` (Automated / Planned) |
| `UT-EXT-005` | Port of Loading with Code (`FR-010`) | `port_of_loading` | `"PORT OF LOADING: SHANGHAI (CNSHA)"` | Extracted raw text preserved; normalized value preserves port name and code. | `P0` (Automated / Planned) |
| `UT-EXT-006` | Port of Discharge Alternative (`FR-010`) | `port_of_discharge` | Label: `"Discharge Port: ROTTERDAM, NETHERLANDS"` | Alternative label matched; extracted raw preserved. | `P0` (Automated / Planned) |
| `UT-EXT-007` | Container Count in Words (`FR-010`) | `container_count` | `"Three (3) Containers"` | Extracted raw: `"Three (3) Containers"`. Normalizer converts to integer `3`. | `P0` (Automated / Existing) |
| `UT-EXT-008` | Container Count Multi-Size Format (`FR-010`) | `container_count` | `"2 X 40HC, 1 X 20GP"` | Extracted raw: `"2 X 40HC, 1 X 20GP"`. Normalizer sums total containers to `3`. | `P0` (Automated / Planned) |
| `UT-EXT-009` | Gross Weight with Metric Tons (`FR-010`) | `gross_weight_kg` | `"G.W.: 25 MT"` | Extracted raw: `"25 MT"`. Normalizer computes `Decimal("25000")`. | `P0` (Automated / Existing) |
| `UT-EXT-010` | Gross Weight with Comma Separators (`FR-010`) | `gross_weight_kg` | `"Gross Weight: 25,432.50 KGS"` | Extracted raw: `"25,432.50 KGS"`. Normalizer computes `Decimal("25432.50")`. | `P0` (Automated / Planned) |
| `UT-EXT-011` | Missing Mandatory Field (`FR-010`, `FR-014`) | Any of 7 fields | Field label and value completely absent from document. | Field marked `value = null`, `reliable = false`. Escalates to HITL: `missing_required_value`. | `P0` (Automated / Planned) |
| `UT-EXT-012` | Strict Evidence Grounding (`DEC-AI-P05`, `DC-05`) | All 7 fields | Valid document extraction. | Every extracted field contains non-empty `evidence_ids` linking to `FieldEvidence` with exact verbatim `quote`. | `P0` (Automated / Planned) |
| `UT-EXT-013` | Evidence Hallucination Rejection (`DEC-AI-P05`, `REG-011`) | All 7 fields | Mocked LLM extraction produces a quote string that does not exist in parsed text. | Evidence validator detects mismatch; rejects extraction as ungrounded; triggers retry or HITL. | `P0` (Automated / Planned) |
| `UT-NORM-001` | Unicode Normalization (`DEC-P06A`) | Normalization | `"ＳＨＡＮＧＨＡＩ"` (Fullwidth) | `"SHANGHAI"` (NFKC standard) | `P1` (Automated / Planned) |
| `UT-NORM-002` | Case-Folding & Spacing (`DEC-P06A`) | Normalization | `"  Acme   Industrial   Corp.  "` | `"ACME INDUSTRIAL CORP."` (Whitespace collapsed, upper case). | `P0` (Automated / Planned) |
| `UT-NORM-003` | Punctuation Cleanup (`DEC-P06A`) | Normalization | `"ROTTERDAM, NETHERLANDS."` | `"ROTTERDAM, NETHERLANDS"` (Trailing punctuation trimmed). | `P1` (Automated / Planned) |
| `UT-NORM-004` | Metric Ton Conversion (`DEC-P06B`) | Unit Conversion | `"22 MT"` | `Decimal("22000")` ($22 \times 1000 = 22000$). | `P0` (Automated / Planned) |
| `UT-NORM-005` | Decimal Gross Weight Representation (`DC-04`) | Data Type | `"22,500.50 KGS"` | `Decimal("22500.50")` (Exact decimal representation, no IEEE float drift). | `P0` (Automated / Planned) |
| `REG-NORM-001` | Negative Guard: No Undocumented Weight Tolerance (`DEC-P06E`, `REG-004`) | Domain Rule | SI: `22000 kg`, BL: `22001 kg` | `outcome == "MISMATCH"`. Enforces exact Decimal equality after approved unit normalization; no undocumented numeric tolerance. Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06E TBD. | `P0` (Automated / Planned) |
| `REG-NORM-002` | Negative Guard: No Port Equivalence (`DEC-P06C`, `REG-006`) | Domain Rule | SI: `"SHANGHAI"`, BL: `"PORT OF SHANGHAI"` | `outcome == "MISMATCH"`. Enforces exact equality after currently approved normalization; no automatic port alias, UN/LOCODE, city, or terminal equivalence. Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06C TBD. | `P0` (Automated / Planned) |
| `REG-NORM-003` | Negative Guard: No Organization Equivalence (`DEC-P06D`, `REG-005`) | Domain Rule | SI: `"ACME CORP"`, BL: `"ACME CORPORATION"` | `outcome == "MISMATCH"`. Enforces exact equality after currently approved normalization; no broad legal-suffix stripping; no token reordering or organization alias equivalence. Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06D TBD. | `P0` (Automated / Planned) |

---

## 8. Contract Test Plan

Verifies strict Pydantic v2 schema compliance for internal models, REST payloads, and evaluation formats ([`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md)).

| Test ID | Decision | Invariant Verified | Validation Step / Assert | Priority |
|---|---|---|---|---|
| `CT-DATA-001` | `DC-01` | Internal Category Nullability | `ClassificationResult.category` accepts `None` as internal unresolved state; rejects arbitrary non-enum strings. | `P0` (Automated / Planned) |
| `CT-DATA-002` | `DC-02` | Internal vs Official HITL Separation | `ReviewIssue.logical_reason` accepts all 7 internal enum values. Official adapter rejects unmapped reasons. | `P0` (Automated / Planned) |
| `CT-DATA-003` | `DC-03` | Tri-State Mismatch Model | `AuditRecord.mismatch_detected` accepts `True`, `False`, `None`. When `state == "NEEDS_REVIEW"`, asserts `outcome is None` and `mismatch_detected is None`. | `P0` (Automated / Planned) |
| `CT-DATA-004` | `DC-04` | Decimal Weight Representation | `NormalizedGrossWeight.canonical_kg` is type `Decimal`. `12.345` is not stored as binary float. | `P0` (Automated / Planned) |
| `CT-DATA-005` | `DC-05` | Structured FieldEvidence | `FieldEvidence` requires `kind`, `source_id`, `quote`. Coordinates optional when not provided by parser. | `P0` (Automated / Planned) |
| `CT-DATA-006` | `DC-06` | Attempt Limit Semantics | `AttemptTracker` asserts `technical_attempt_limit >= 1`, `semantic_attempt_limit >= 1`. Initial attempt counted as 1. | `P1` (Automated / Planned) |
| `CT-DATA-007` | `DC-07` | ReviewUpdate Payload Schema | Validates `action: Literal['CONFIRM', 'CORRECT']`, `expected_revision: int`, `corrections: list[FieldCorrection]`. | `P0` (Automated / Planned) |
| `CT-DATA-008` | `DC-08` | Export Blocked Safety Schema | `ErrorResponse` returns `code = "EXPORT_BLOCKED"`, `message`, and list of blocking `email_ids`. | `P0` (Automated / Planned) |
| `CT-DATA-009` | Model Instantiation | Valid Synthetic Model Fixtures | All 15 synthetic models in `specs/03_DATA_CONTRACTS_EXAMPLES.json` pass Pydantic v2 validation cleanly. | `P0` (Automated / Planned) |
| `CT-DATA-010` | Extra Fields Rejection | Strict Payload Security | Passing unexpected fields to `ReviewUpdate` raises `ValidationError` (`extra = "forbid"`). | `P1` (Automated / Planned) |

---

## 9. AI Test Plan

Verifies `BaseAIAdapter` abstraction (`DEC-P01`), structured schema enforcement, retry budgets (`DEC-AI-P01`, `DEC-AI-P02`), fallback cascades, and confidence decoupling. Core tests run 100% offline using deterministic mocks.

| Test ID | Title & Requirement | Input / Scenario | Steps | Expected Result | Priority |
|---|---|---|---|---|---|
| `AI-ADP-001` | Valid Structured Classification (`DEC-P01`) | Mocked JSON: `{"category": "document_comparison", "confidence": 0.95, "evidence_quote": "compare draft BL"}` | Execute adapter parse. | Validates against `ClassificationResponse` Pydantic model without error. | `P0` (Automated / Planned) |
| `AI-ADP-002` | Invalid Classification Enum (`DEC-P01`) | Mocked JSON: `{"category": "UNKNOWN_INTENT"}` | Execute adapter parse. | Pydantic validation raises `ValidationError`; triggers semantic repair retry. | `P1` (Automated / Planned) |
| `AI-ADP-003` | Missing Mandatory Schema Key (`DEC-P01`) | Mocked JSON: `{"confidence": 0.9}` (missing `category`). | Execute adapter parse. | Schema validation fails; error logged; triggers retry. | `P1` (Automated / Planned) |
| `AI-ADP-004` | Unexpected Hallucinated Keys (`DEC-P01`) | Mocked JSON contains extra keys: `{"category": "spam", "hallucinated_bl": "123"}` | Execute adapter parse. | Extra keys stripped or rejected per schema configuration (`extra = "forbid"`). | `P2` (Automated / Planned) |
| `AI-ADP-005` | Confidence Diagnostic Decoupling (`REG-011`) | Model returns `confidence = 0.99`, but extracted quote is absent from document. | Run evidence verification. | High confidence does **NOT** bypass evidence validation. Extraction rejected. | `P0` (Automated / Planned) |
| `AI-ADP-006` | Rate Limit (HTTP 429) Handling (`DEC-AI-P01`) | Mocked adapter simulates HTTP 429 Rate Limit. | Call adapter. | Adapter captures rate limit, applies exponential backoff, retries up to technical limit. | `P1` (Automated / Planned) |
| `AI-BUD-001` | Technical Retry on Transient Failure (`DEC-AI-P01`, `DC-06`) | Provider returns HTTP 503 on call 1; returns valid JSON on call 2. | Run adapter call with transient failure. | Retries automatically after backoff; succeeds on attempt 2. `attempt = 2`, `stage_status = "SUCCESS"`. | `P1` (Automated / Planned) |
| `AI-BUD-002` | Technical Attempt Exhaustion (`DEC-AI-P01`, `DC-06`) | Provider returns timeout on 3 consecutive calls. | Run adapter call with 3 failures. | Exhausts `technical_attempt_limit = 3`. Transitions to approved fallback path. | `P0` (Automated / Planned) |
| `AI-BUD-003` | Semantic Retry on Malformed JSON (`DEC-AI-P02`, `DC-06`) | Model returns invalid JSON syntax on call 1; returns valid JSON matching schema on call 2. | Feed malformed response; invoke repair prompt. | Successfully parses repaired JSON on attempt 2. `semantic_attempts = 2`. | `P1` (Automated / Planned) |
| `AI-BUD-004` | Bounded Provider Invocation Budget Cap at 6 (`DEC-AI-P01`, `DEC-AI-P02`, `DC-06`) | Provider transient and semantic retries triggered across sequential stages. | Trigger cascading retries up to budget limit. | Total provider invocations across retries and fallbacks within any single processing request are capped strictly at 6 to prevent infinite execution loops. Once exhausted, processing terminates and escalates to HITL. | `P0` (Automated / Planned) |
| `AI-BUD-005` | Fallback Output Validation Required (`REG-008`) | Fallback produces output, but output violates Pydantic schema or lacks evidence. | Ingest fallback output. | Fallback output rejected by validator. Does **NOT** continue pipeline; escalates to HITL. | `P0` (Automated / Planned) |

---

## 10. Parser & OCR Test Plan

Verifies pluggable parsers (TXT, DOCX, PDF, XLSX) and Text Usability Validation rules ([`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §3).

| Test ID | Title & Requirement | Input / Fixture | Steps | Expected Result | Priority |
|---|---|---|---|---|---|
| `PAR-TXT-001` | Plain Text Parsing (`FR-005`, `DEC-P02`) | Synthetic UTF-8 TXT file containing multi-line SI fields. | Execute `TextParser.parse()`. | `status == "SUCCESS"`, `usable_for_extraction == true`, text preserved exactly. | `P0` (Automated / Existing) |
| `PAR-DOCX-001` | Word Document Table Parsing (`FR-006A`, `FR-007`) | Synthetic DOCX file with fields laid out in multi-column tables and free paragraphs. | Execute `DocxParser.parse()`. | `status == "SUCCESS"`, table cells extracted with row/column coordinate metadata, text intact. | `P1` (Automated / Existing) |
| `PAR-PDF-001` | Standard Vector PDF Parsing (`FR-006B`, `FR-007`) | Synthetic multi-page vector PDF containing form layout and text blocks. | Execute `PdfParser.parse()`. | `status == "SUCCESS"`, page numbers recorded, character count reflects text layer. | `P0` (Automated / Existing) |
| `PAR-PDF-002` | Corrupted PDF Detection (`FR-006B`, `NFR-003`) | Synthetically truncated PDF file (EOF marker missing, header corrupted). | Execute `PdfParser.parse()`. | `status == "UNREADABLE"`, `is_corrupted == true`, gracefully handles exception without crashing. | `P0` (Automated / Existing) |
| `PAR-XLSX-001` | Excel Sheet Parsing (`FR-006C`, Design Extension) | Synthetic XLSX workbook with container manifest and cargo weight rows. | Execute `ExcelParser.parse()`. | `status == "SUCCESS"`, cell coordinates preserved, tabular structure flattened to structured text. | `P2` (Automated / Existing) |
| `PAR-USAB-001` | Valid Short Document (`REG-007`) | Synthetic plain-text SI with concise format: `"SI: ACME / 2 CTR / 22MT"` (approx. 25 chars). | Run Text Usability Validation. | `usable_for_extraction == true`. Must **NOT** trigger OCR or fail merely because length is short. | `P0` (Automated / Planned) |
| `PAR-USAB-002` | Long Garbage / Binary Extraction (`DEC-P02`) | Corrupted text extraction containing 500+ characters of non-printable or replacement characters (`\ufffd`). | Run Text Usability Validation. | `usable_for_extraction == false`, `status == "UNREADABLE"`. Escalates to OCR or HITL. | `P0` (Automated / Planned) |
| `PAR-USAB-003` | Image-Only Scanned PDF (`FR-008`, `DEC-P02`) | Scanned 300 DPI PDF without embedded text layer (extracted text = `""`). | Run `PdfParser` and Usability Validation. | Detects empty text layer; routes document to Vision/OCR fallback stage. | `P0` (Automated / Planned) |
| `PAR-USAB-004` | Partial Usability with Essential Fields (`DEC-AI-P04`) | PDF where header and 7 comparison fields are legible, but footer disclaimer is garbled. | Run Usability Validation. | `status == "PARTIAL"`, `usable_for_extraction == true`. Extraction proceeds; document is **NOT** rejected. | `P1` (Automated / Planned) |
| `AI-OCR-001` | Scanned Clean Document (`FR-008`, `DEC-P02`) | High-resolution scanned draft BL (image-only PDF). | Invoke Vision/OCR extraction via mocked adapter. | Extracts structured text layer and bounding box metadata. `usable_for_extraction == true`. | `P1` (Automated / Planned) |
| `AI-OCR-002` | Essential Fields Readable, Footer Corrupted (`DEC-AI-P04`) | Scanned document where terms & conditions are blurry/illegible, but all 7 fields are sharp. | Run OCR extraction and field extraction. | All 7 fields successfully extracted. Document accepted. System does **NOT** escalate to HITL. | `P0` (Automated / Planned) |
| `AI-OCR-003` | Unreadable Mandatory Field (`FR-014`) | Scanned document with severe coffee stain/smudge over `container_count` field. | Run OCR extraction. | Field extraction flags `container_count` as unreadable. Escalates to HITL: `logical_reason = "missing_required_value"`. | `P0` (Automated / Planned) |
| `AI-OCR-004` | Conflicting OCR Interpretations (`FR-014`, `DC-02`) | Ambiguous low-resolution scan where gross weight could be read as `22,500` or `28,500`. | Run OCR extraction returning multiple candidates with split confidence. | Escalates to HITL: `logical_reason = "conflicting_candidate_values"`, listing both candidates. | `P0` (Automated / Planned) |
| `AI-OCR-005` | Vision Provider Unavailable with Fallback (`DEC-AI-P01`, `REG-008`) | AI/OCR provider encounters transient error $\rightarrow$ bounded retries $\rightarrow$ approved stage-specific fallback. | Execute OCR extraction under provider error. | Bounded retries executed; approved stage-specific fallback invoked; produces validated result $\rightarrow$ pipeline continues without HITL. | `P1` (Automated / Planned) |
| `AI-OCR-006` | Total Provider Failure and Fallback Exhaustion (`FR-014`, `DEC-AI-P01`) | AI/OCR provider unavailable $\rightarrow$ retries exhausted $\rightarrow$ stage-specific fallback unavailable or insufficient. | Execute OCR extraction. | Gracefully catches exhaustion. Escalates to HITL: `logical_reason = "processing_or_provider_failure"`. No crash. | `P0` (Automated / Planned) |

---

## 11. Pipeline Test Plan

Verifies end-to-end stage orchestration across Stages 1, 2, 3, and 4, deterministic comparisons, and partial work preservation.

| Test ID | Stage / Focus | Scenario & Input | Verification Criteria | Priority |
|---|---|---|---|---|
| `PIPE-CLS-001` | Stage 1: Classify | 5 synthetic emails covering all 5 categories (`EC-001`). | Categories match 1:1 (`document_comparison`, `new_shipping_instruction`, `invoice_query`, `general`, `spam`). | `P0` (Automated / Planned) |
| `PIPE-CLS-002` | Stage 1: Classify | Subject: `"Invoice Query"`; Body: `"Compare attached SI and draft BL"`. | Body intent prevails $\rightarrow$ `document_comparison`. | `P1` (Automated / Planned) |
| `PIPE-CLS-003` | Stage 1: Classify | Subject: `"Update"`; Body: `"Please see attached draft BL and SI"`. | Body intent resolves $\rightarrow$ `document_comparison`. | `P1` (Automated / Planned) |
| `PIPE-CLS-004` | Stage 1: Classify | Zero attachments but body asks for SI/BL verification (`EC-002`, `REG-001`). | `category == "document_comparison"`. Stage 2 then escalates to `missing_attachment`. Category is **NOT** forced to `general`. | `P0` (Automated / Planned) |
| `PIPE-CLS-005` | Stage 1: Classify | Attachments present, but email is an invoice payment inquiry (`FR-004`). | `category == "invoice_query"`. Pipeline bypasses SI/BL verification. | `P1` (Automated / Planned) |
| `PIPE-CLS-006` | Stage 1: Classify | Vague email with ambiguous text and generic attachments. | Intent confidence low; `category = null`; escalates to HITL: `uncertain_result`. | `P0` (Automated / Planned) |
| `PIPE-CLS-007` | Stage 1: Classify | Clean standard verification email with explicit keywords (`DEC-AI-P03`). | Deterministic heuristics classify intent without invoking LLM API adapter. | `P1` (Automated / Planned) |
| `PAR-ROLE-001` | Stage 2: Role Binding | Filenames: `shipment_SI.pdf`, `shipment_BL.pdf` (`DEC-AI-P03`). | Deterministic pattern binding binds SI and BL without invoking AI adapter. | `P0` (Automated / Planned) |
| `PAR-ROLE-002` | Stage 2: Role Binding | Generic filenames (`doc1.pdf`, `doc2.pdf`) with distinct headers. | Content header analysis binds `SI` and `BL`. | `P1` (Automated / Planned) |
| `PAR-ROLE-003` | Stage 2: Role Binding | Draft BL attached, SI missing (`FR-014`). | Flags missing SI $\rightarrow$ HITL: `logical_reason = "missing_attachment"`. | `P0` (Automated / Planned) |
| `PAR-ROLE-004` | Stage 2: Role Binding | SI attached, Draft BL missing (`FR-014`). | Flags missing BL $\rightarrow$ HITL: `logical_reason = "missing_attachment"`. | `P0` (Automated / Planned) |
| `PAR-ROLE-005` | Stage 2: Role Binding | Two distinct SI candidate files attached (`FR-014`). | Detects duplicate role candidates $\rightarrow$ HITL: `wrong_or_uncertain_document_type`. | `P1` (Automated / Planned) |
| `PAR-ROLE-006` | Stage 2: Role Binding | Single file attempted for both SI and BL roles. | Validation fails; assigns neither $\rightarrow$ HITL: `wrong_or_uncertain_document_type`. | `P1` (Automated / Planned) |
| `PAR-ROLE-007` | Stage 2: Role Binding | Attachment is packing list / customs invoice instead of BL (`FR-014`). | Role analysis rejects attachment $\rightarrow$ HITL: `wrong_or_uncertain_document_type`. | `P0` (Automated / Planned) |
| `PAR-ROLE-008` | Stage 2: Role Binding | Valid SI + Corrupted PDF BL (`FR-014`, `NFR-003`). | Detects corrupt stream $\rightarrow$ HITL: `logical_reason = "unreadable_document"`. | `P0` (Automated / Planned) |
| `PIPE-CMP-001` | Stage 4: Compare | All 7 fields identical between SI and BL (`FR-011`, `DEC-01`). | `state = "COMPLETE"`, `outcome = "MATCH"`, `mismatch_detected = false`, `result_summary = "No mismatch detected"`. | `P0` (Automated / Existing) |
| `PIPE-CMP-002` | Stage 4: Compare | Only `container_count` differs (2 vs 3) (`FR-012`, `DEC-01`). | `state = "COMPLETE"`, `outcome = "MISMATCH"`, `mismatch_detected = true`, `discrepancies` has 1 item. | `P0` (Automated / Existing) |
| `PIPE-CMP-003` | Stage 4: Compare | `shipper` and `gross_weight_kg` differ (`FR-012`). | `state = "COMPLETE"`, `outcome = "MISMATCH"`, `mismatch_detected = true`, `discrepancies` lists both fields. | `P0` (Automated / Planned) |
| `PIPE-CMP-004` | Stage 4: Compare | 6 fields match, 1 field unextracted in BL (`FR-011`, `DC-03`, `REG-010`). | `state = "NEEDS_REVIEW"`, `outcome = null`, `mismatch_detected = null`. NEVER emit `"No mismatch detected"`. | `P0` (Automated / Planned) |
| `PIPE-CMP-005` | Stage 4: Compare | `container_count` differs, but `gross_weight_kg` unreadable (`DC-03`). | `state = "NEEDS_REVIEW"`, `outcome = null`, `mismatch_detected = null`. Known mismatch stored in partial results. | `P0` (Automated / Planned) |
| `PIPE-CMP-006` | Stage 4: Compare | 2 conflicting gross weight values in SI (`FR-014`). | Field marked unresolved $\rightarrow$ `state = "NEEDS_REVIEW"`, `mismatch_detected = null`. | `P0` (Automated / Planned) |
| `HITL-PART-001` | Partial Preservation | 6 reliable matching fields + 1 conflicting field (`DEC-AI-P04`, `REG-009`). | `partial_result.comparisons` preserves 6 `MATCH` results; 1 unresolved; case `NEEDS_REVIEW`. | `P0` (Automated / Planned) |
| `HITL-PART-002` | Partial Preservation | SI parsed cleanly, but 2 BL candidates exist (`DEC-AI-P04`). | Preserves parsed SI text and classification; marks BL role pending. | `P1` (Automated / Planned) |
| `HITL-PART-003` | Partial Preservation | Reviewer corrects only the 7th field via API (`FR-016`, `DC-07`). | Normalizes and compares only 7th field; other 6 fields preserved untouched. Generates revision 2. | `P0` (Automated / Planned) |

---

## 12. HITL Workflow Test Plan

Verifies all 7 logical review reasons, escalation payloads, operator actions, and optimistic revision locking ([`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §4 and [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7).

| Test ID | Test Focus | Scenario | Expected Invariant & System Response | Priority |
|---|---|---|---|---|
| `HITL-RSN-001` | Reason Code | Email comparison request missing draft BL (`FR-014`). | Escalates with `logical_reason = "missing_attachment"`, records missing role `BL`. | `P0` (Automated / Existing) |
| `HITL-RSN-002` | Reason Code | Corrupted PDF attachment (`FR-014`, `NFR-003`). | Escalates with `logical_reason = "unreadable_document"`, records parser diagnostic. | `P0` (Automated / Existing) |
| `HITL-RSN-003` | Reason Code | Attachment roles ambiguous or unverified (`FR-014`). | Escalates with `logical_reason = "wrong_or_uncertain_document_type"`. | `P0` (Automated / Planned) |
| `HITL-RSN-004` | Reason Code | Mandatory `port_of_discharge` missing from SI (`FR-014`). | Escalates with `logical_reason = "missing_required_value"`, records field name. | `P0` (Automated / Planned) |
| `HITL-RSN-005` | Reason Code | Classification or comparison confidence ambiguous (`FR-014`). | Escalates with `logical_reason = "uncertain_result"`. | `P0` (Automated / Planned) |
| `HITL-RSN-006` | Reason Code | Multiple conflicting candidate weights in document (`FR-014`). | Escalates with `logical_reason = "conflicting_candidate_values"`, stores candidates. | `P0` (Automated / Planned) |
| `HITL-RSN-007` | Reason Code | OCR/AI provider timeout after retries exhausted (`FR-017`). | Escalates with `logical_reason = "processing_or_provider_failure"`, records stage. | `P0` (Automated / Planned) |
| `HITL-REV-001` | Review Safety | Reviewer attempts to submit `mismatch_detected = false` (`FR-016`, `REG-012`). | HTTP 422 Unprocessable Entity. Reviewer cannot override derived boolean directly. | `P0` (Automated / Planned) |
| `HITL-REV-002` | Review Correction | Operator supplies correct gross weight (`"22,500 KG"`) (`FR-016`, `DC-07`). | Normalizes to `22500`, re-runs comparison, creates `revision = 2`, state becomes `COMPLETE`. | `P0` (Automated / Planned) |
| `HITL-REV-003` | Review Correction | Operator resolves `category = null` to `document_comparison` (`DC-07`). | Sets category; triggers Stage 2 document identification; creates revision 2. | `P0` (Automated / Planned) |
| `HITL-REV-004` | Review Correction | Operator assigns `file_a.pdf` $\rightarrow$ `SI` and `file_b.pdf` $\rightarrow$ `BL` (`DC-07`). | Binds roles; validates files are distinct; triggers Stage 3 extraction. | `P0` (Automated / Planned) |
| `HITL-REV-005` | Confirm Guardrail | Reviewer submits `action = "CONFIRM"` on unextracted field (`DC-07`). | Backend rejects premature resolution or maintains `NEEDS_REVIEW`. `CONFIRM` cannot force unextracted fields to reliable. | `P0` (Automated / Planned) |
| `HITL-REV-006` | Concurrency Lock | Reviewer A and B load revision 1; B submits $\rightarrow$ rev 2; A submits with `expected_revision = 1` (`DC-07`). | Server responds with **HTTP 409 Conflict**. Revision 2 intact. Reviewer A's edits held in memory; reload required. | `P0` (Automated / Planned) |

---

## 13. API Test Plan

Verifies FastAPI REST endpoints ([`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §9 and [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §8).

| Test ID | Endpoint & Method | Test Scenario | Expected Status & Response | Priority |
|---|---|---|---|---|
| `API-AUD-001` | `GET /audit` | List all cases with filter: `?state=NEEDS_REVIEW` (`DEC-P03`). | HTTP 200. Returns list of `AuditRecordSummary`, filtered accurately. | `P0` (Automated / Planned) |
| `API-AUD-002` | `GET /audit/{email_id}` | Retrieve existing audited case detail (`DEC-P03`). | HTTP 200. Returns full `AuditRecord` including email context, documents, comparisons, evidence, and revision lineage. | `P0` (Automated / Existing) |
| `API-AUD-003` | `GET /audit/{email_id}` | Retrieve non-existent email ID (`email_9999`) (`DEC-P03`). | HTTP 404 Not Found with structured `ErrorResponse`. | `P1` (Automated / Planned) |
| `API-REV-001` | `POST /audit/{email_id}/review` | Submit valid review correction (`DEC-P03`, `DC-07`). | HTTP 200. Returns updated `AuditRecord` with incremented `revision`. | `P0` (Automated / Planned) |
| `API-REV-002` | `POST /audit/{email_id}/review` | Submit with stale `expected_revision` (concurrency collision) (`DC-07`). | HTTP 409 Conflict with detail indicating current revision. | `P0` (Automated / Planned) |
| `API-REV-003` | `POST /audit/{email_id}/review` | Submit malformed JSON or invalid field name (`DEC-P03`). | HTTP 422 Unprocessable Entity with validation errors. | `P1` (Automated / Planned) |
| `API-EXP-001` | `GET /submission` | Export when 100% of cases are in `COMPLETE` state (`NFR-005`). | HTTP 200. Returns JSON dictionary matching `sample_submission.json`. | `P0` (Automated / Planned) |
| `API-EXP-002` | `GET /submission` | Export when one or more cases are in `NEEDS_REVIEW` state (`DC-08`). | HTTP 409 Conflict with `code = "EXPORT_BLOCKED"` (Safety Invariant DC-08). | `P0` (Automated / Planned) |
| `API-HLT-001` | `GET /health` | Basic application health and readiness check (`DEC-P03`). | HTTP 200. `{"status": "healthy"}`. *(Note: Provider connectivity diagnostics are OPTIONAL / OBSERVABILITY EXTENSIONS, not a core requirement of this endpoint)*. | `P1` (Automated / Existing) |

---

## 14. Evaluation Adapter Test Plan

Verifies translation to official hackathon evaluation schemas and safety blocking rules ([`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5).

| Test ID | Title & Requirement | Input Scenario | Expected Output / Behavior | Priority |
|---|---|---|---|---|
| `EVAL-MAP-001` | 5-Category Mapping (`NFR-005`, `DC-02`) | Internal categories: `document_comparison`, `new_shipping_instruction`, `invoice_query`, `general`, `spam`. | Maps exactly to: `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`. | `P0` (Automated / Planned) |
| `EVAL-MAP-002` | Null Category Rejection (`DC-01`, `DC-08`) | Internal case with `category = null`. | Adapter raises `ExportBlockedException`. Must **NOT** fabricate a category. | `P0` (Automated / Planned) |
| `EVAL-MAP-003` | Clean Match Mapping (`NFR-005`) | Internal case with `outcome = "MATCH"`. | `status = "OK"`, `has_defect = false`, `defect_fields = []`. | `P0` (Automated / Existing) |
| `EVAL-MAP-004` | Discrepancy Field Mapping (`NFR-005`) | Internal case with `container_count` mismatch. | `status = "MISMATCH"`, `has_defect = true`, `defect_fields = ["container_count"]`. | `P0` (Automated / Existing) |
| `EVAL-MAP-005` | Canonical Defect Field Identifiers (`NFR-005`) | Internal discrepancies across all 7 fields. | Mapped field names match exact official strings: `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, `gross_weight_kg`. | `P0` (Automated / Planned) |
| `EVAL-MAP-006` | Multiple Defect Fields Sorting (`NFR-005`) | Mismatches on `gross_weight_kg` and `shipper`. | `defect_fields` contains both strings, sorted deterministically. | `P1` (Automated / Planned) |
| `EVAL-MAP-007` | Contract-Dependent: NEEDS_REVIEW Export (`DC-08`) | Audit record with `state = "NEEDS_REVIEW"`. | Current baseline: Adapter refuses export and triggers `EXPORT_BLOCKED`. *(Marked CONTRACT-DEPENDENT: subject to future evaluation amendments)*. | `P0` (Automated / Planned) |

---

## 15. Frontend Test Plan

Verifies React components, dedicated review routes, and frontend/backend contract drift prevention ([`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md)).

| Test ID | Component / Area | Scenario | Expected Visual / Semantic Behavior | Priority |
|---|---|---|---|---|
| `UI-GRID-001` | `<CaseQueueGrid />` | Loading, Ready, Empty states. | Skeleton rows during loading; populated data grid when ready; clean empty message on no match. | `P1` (Automated / Planned) |
| `UI-BADGE-001` | `<OutcomeBadge />` | `MATCH`, `MISMATCH`, `NOT_APPLICABLE`, `UNRESOLVED`. | Color + icon + text label. Does not rely on color alone. `UNRESOLVED` renders amber warning stripes. | `P0` (Automated / Planned) |
| `UI-DIFF-001` | `<ComparisonMatrix />` | 4-column diff matrix (`Field`, `SI`, `Draft BL`, `Outcome/Result`). | Renders all 7 mandatory rows. Column 1: field; Column 2: SI value + raw; Column 3: BL value + raw; Column 4: outcome + view evidence button. | `P0` (Automated / Planned) |
| `UI-DIFF-002` | `<ComparisonMatrix />` | Missing field row. | Shows `[Not Found in Document]` and amber `UNRESOLVED` badge. Zero hidden rows. | `P0` (Automated / Planned) |
| `UI-DRW-001` | `<EvidenceDrawer />` | User triggers evidence view. | Drawer slides out over right side. Renders exact quote snippet, location metadata, and source document tag. | `P1` (Automated / Planned) |
| `UI-REV-001` | `<ReviewWorkspace />` | Dedicated route `/cases/:email_id/review`. | Renders two panels: preserved 4-column matrix on left; review issues banner and multi-scope correction tabs on right. | `P0` (Automated / Planned) |
| `UI-REV-002` | `<ReviewWorkspace />` | Humanized review reason labels. | Displays operational labels (e.g. `"Conflicting values found"`) instead of raw enums (`conflicting_candidate_values`). | `P1` (Automated / Planned) |
| `UI-REV-003` | `<ReviewWorkspace />` | HTTP 409 Conflict handling. | In-place collision modal: preserves unsubmitted edits; provides reload and view diff actions. | `P0` (Automated / Planned) |
| `UI-EXP-001` | `<ExportBlockedModal />` | User attempts export while cases require review. | Displays modal with `EXPORT_BLOCKED` warning, listing blocking email IDs with click-to-resolve links. | `P0` (Automated / Planned) |
| `UI-CT-001` | TypeScript Contract Sync | API schema vs frontend types. | Automated contract verification script asserts TypeScript types match FastAPI OpenAPI schema 1:1. | `P0` (Automated / Planned) |

---

## 16. Accessibility & Responsive Test Plan

Verifies WCAG 2.1 AA targets and responsive transformations ([`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §7).

| Test ID | Focus Area | Verification Method | Acceptance Condition | Priority |
|---|---|---|---|---|
| `ACC-001` | Keyboard Navigation | Manual Tab/Shift-Tab walk | Full keyboard access across queues, matrix rows, evidence drawers, and modal focus traps. | `P1` (Manual / Planned) |
| `ACC-002` | Visible Focus Rings | CSS inspection & manual check | All interactive elements display high-contrast `:focus-visible` outlines. | `P1` (Manual / Planned) |
| `ACC-003` | Non-Color Cues | Visual review | Badges combine text, icons (checkmark, triangle alert, clock), and colors. No color-only meaning. | `P1` (Manual / Planned) |
| `ACC-004` | Contrast Ratios | Automated axe-core scan | Minimum 4.5:1 text-to-background contrast ratio across all diff panels and badges. | `P2` (Automated / Planned) |
| `RESP-001` | Desktop Primary Layout | Desktop viewport review | Case detail renders 3-column / 2-panel operational view without horizontal clipping. | `P1` (Manual / Planned) |
| `RESP-002` | Narrow Screen Adaptation | Narrow viewport review | 4-column table transforms into stacked field cards. Values, badges, and evidence buttons remain operationally usable. *(Breakpoint thresholds remain TBD unless explicitly approved)*. | `P2` (Manual / Planned) |

---

## 17. Security & Data Integrity Plan

Verifies non-destructive data isolation, credential protection, and defense against prompt injection ([`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §7 and [`AGENTS.md`](file:///d:/ship/AGENTS.md)).

| Test ID | Focus Area | Attack Vector / Check | Expected Defense | Priority |
|---|---|---|---|---|
| `SEC-DATA-001` | Evaluation Bundle Immutability | Test harness monitors file hashes in `sdoc-hackathon-bundle/`. | File hashes in bundle directory remain identical before and after test runs. No files modified. | `P0` (Automated / Planned) |
| `SEC-AUTH-001` | API Key Leak Prevention | Inspect all HTTP responses, client logs, and error traces. | LLM provider API keys are never exposed in `/health`, `/audit`, or client bundles. | `P0` (Automated / Planned) |
| `SEC-LEAK-001` | Prompt & CoT Masking | API response inspection on `/audit/{id}`. | Internal system prompts and chain-of-thought reasoning are excluded from public API responses. | `P1` (Automated / Planned) |
| `SEC-PATH-001` | Directory Traversal Defense | Requesting attachment path: `../../../../etc/passwd` or `C:\Windows\win.ini`. | Path sanitization rejects directory traversal; returns HTTP 400 or raises security error. | `P0` (Automated / Planned) |
| `SEC-INTEG-001` | No Benchmark Answer Leaks | Grep codebase for private evaluation ground-truth tables. | Business logic contains zero hardcoded mapping tables matching email IDs to answers. | `P0` (Automated / Planned) |

---

## 18. Performance & Observability Plan

Defines measurable performance metrics. In accordance with AGENTS.md, all numeric acceptance thresholds are explicitly set to **`TBD / OBSERVATIONAL BASELINE`** until separately approved. The test plan does not convert benchmark suggestions into baseline requirements.

| Metric ID | Performance Metric Description | Measurement Method | Baseline Status |
|---|---|---|---|
| `PERF-001` | Queue Summary API Latency | `GET /audit` response time with 500 records | TBD / OBSERVATIONAL BASELINE |
| `PERF-002` | Single Case Detail API Latency | `GET /audit/{email_id}` response time | TBD / OBSERVATIONAL BASELINE |
| `PERF-003` | Review Correction Recomputation Latency | `POST /audit/{id}/review` (normalization + comparison) | TBD / OBSERVATIONAL BASELINE |
| `PERF-004` | Deterministic Parser Throughput | Parse time per TXT / DOCX / Vector PDF | TBD / OBSERVATIONAL BASELINE |
| `PERF-005` | External AI Call Latency | Mocked adapter overhead vs provider timeout limit | TBD / OBSERVATIONAL BASELINE |
| `PERF-006` | AI Call Avoidance Rate | % of clean cases resolved deterministically without external AI | TBD / OBSERVATIONAL BASELINE |
| `PERF-007` | Batch Pipeline Throughput | End-to-end processing time for 100 mixed cases | TBD / OBSERVATIONAL BASELINE |

---

## 19. End-to-End (E2E) Scenario Catalogue

Defines 16 comprehensive end-to-end lifecycle scenarios:

1. **`E2E-001` (Non-Comparison Email)**: Email ingested $\rightarrow$ Stage 1 classifies as `invoice_query` $\rightarrow$ Pipeline halts verification $\rightarrow$ Case marked `COMPLETE` / `NOT_APPLICABLE` $\rightarrow$ Viewable in queue $\rightarrow$ Export maps to `INVOICE_QUERY`.
2. **`E2E-002` (Clean SI/BL Match)**: Email with TXT SI and TXT BL $\rightarrow$ Classified as `document_comparison` $\rightarrow$ Roles bound $\rightarrow$ All 7 fields extracted $\rightarrow$ Normalized $\rightarrow$ Compared $\rightarrow$ 100% Match $\rightarrow$ `COMPLETE` / `MATCH` $\rightarrow$ Clean scorecard.
3. **`E2E-003` (Single Deterministic Mismatch)**: Matching shipment except `container_count` (SI: 2 vs BL: 3) $\rightarrow$ Compared $\rightarrow$ `COMPLETE` / `MISMATCH` $\rightarrow$ Discrepancy highlighted in rose diff row $\rightarrow$ Export maps `defect_fields = ["container_count"]`.
4. **`E2E-004` (Multiple Field Mismatches)**: Differences in `shipper` and `gross_weight_kg` $\rightarrow$ Compared $\rightarrow$ `COMPLETE` / `MISMATCH` $\rightarrow$ Discrepancies listed side-by-side $\rightarrow$ Evidence drawer links intact for both.
5. **`E2E-005` (Comparison Missing Attachment)**: Email requests verification but omits draft BL $\rightarrow$ Stage 1: `document_comparison` $\rightarrow$ Stage 2 flags missing attachment $\rightarrow$ Escalates to HITL (`missing_attachment`) $\rightarrow$ Queue displays amber badge $\rightarrow$ Review workspace explains missing file.
6. **`E2E-006` (Scanned Document OCR Recovery)**: Image-only PDF BL $\rightarrow$ Usability check fails deterministic parse $\rightarrow$ Triggers Vision/OCR fallback $\rightarrow$ OCR extracts usable text $\rightarrow$ All 7 fields resolved $\rightarrow$ Compared successfully.
7. **`E2E-007` (Scanned Document OCR Insufficient)**: Heavily degraded scan $\rightarrow$ OCR fails to recover required fields $\rightarrow$ Escalates to HITL (`unreadable_document`) $\rightarrow$ Partial results preserved $\rightarrow$ Operator flagged.
8. **`E2E-008` (Conflicting Gross Weight Candidates)**: SI contains 2 conflicting weights in table vs footer $\rightarrow$ Extraction flags ambiguity $\rightarrow$ Escalates to HITL (`conflicting_candidate_values`) $\rightarrow$ Review workspace presents both candidates.
9. **`E2E-009` (Human Corrects Field Candidate)**: Operator opens `E2E-008` in `/cases/:id/review` $\rightarrow$ Selects correct weight $\rightarrow$ Submits `ReviewUpdate` $\rightarrow$ Backend re-normalizes $\rightarrow$ Re-matches $\rightarrow$ Updates to `revision = 2` $\rightarrow$ Status becomes `COMPLETE`.
10. **`E2E-010` (Human Resolves Ambiguous Classification)**: Case in HITL with `category = null` $\rightarrow$ Operator selects `document_comparison` $\rightarrow$ Submits $\rightarrow$ Pipeline runs Stages 2–4 $\rightarrow$ Comparison succeeds.
11. **`E2E-011` (Human Resolves Document Roles)**: Case with 2 ambiguous PDF attachments $\rightarrow$ Operator assigns roles $\rightarrow$ Submits $\rightarrow$ Backend executes extraction on assigned roles.
12. **`E2E-012` (Revision Collision Scenario)**: Operator A and B open Case detail $\rightarrow$ B updates gross weight $\rightarrow$ Server advances to `revision = 2` $\rightarrow$ A attempts to submit on `revision = 1` $\rightarrow$ HTTP 409 Conflict $\rightarrow$ A's UI displays conflict modal, preserving inputs.
13. **`E2E-013` (Provider Outage with Validated Fallback)**: AI provider unavailable $\rightarrow$ bounded retries $\rightarrow$ approved stage-specific fallback $\rightarrow$ source-grounded validated result $\rightarrow$ pipeline continues without human escalation.
14. **`E2E-014` (Provider Outage and Fallback Insufficient)**: AI provider unavailable $\rightarrow$ retries exhausted $\rightarrow$ applicable stage-specific fallback unavailable or insufficient $\rightarrow$ HITL escalation with `logical_reason = "processing_or_provider_failure"`.
15. **`E2E-015` (Valid Official Evaluation Export)**: All cases in batch processed to `COMPLETE` state $\rightarrow$ User requests `GET /submission` $\rightarrow$ Generates valid `submission.json` matching official schema $\rightarrow$ Download triggers.
16. **`E2E-016` (Evaluation Export Blocked by Unresolved Case)**: Batch has 1 case in `NEEDS_REVIEW` $\rightarrow$ User requests `GET /submission` $\rightarrow$ Blocked with HTTP 409 `EXPORT_BLOCKED` $\rightarrow$ UI modal displays blocking case IDs.

---

## 20. User Acceptance Testing (UAT) Plan

Provides a manual operational verification checklist for deployment qualification based strictly on behavioral criteria:

| UAT ID | Operational Reviewer Checklist Item | Acceptance Verification Standard | Result |
|---|---|---|---|
| `UAT-001` | Identify Mismatched Fields Quickly | Reviewer can identify mismatched fields without raw JSON inspection; prominent rose diff rows in 4-column matrix clearly isolate mismatched fields and side-by-side values. | Pass / Fail |
| `UAT-002` | Direct Evidence Accessibility | Source evidence is directly accessible from the comparison workflow; direct pathway to inspect verbatim quote snippet, page/cell location, and source document. | Pass / Fail |
| `UAT-003` | Non-Color Status Discrimination | Reviewer can distinguish MATCH, MISMATCH, and UNRESOLVED without relying solely on color; distinct icons (checkmark, alert triangle, clock) and clear text badges are present. | Pass / Fail |
| `UAT-004` | Transparent Escalation Rationale | Reviewer clearly understands why HITL triggered; review banner displays humanized operational copy with suggested action. | Pass / Fail |
| `UAT-005` | Targeted Correction Scope | Reviewer can correct only the problematic item without re-verifying or touching already reliable fields; multi-tab form allows targeted field, role, or category correction. | Pass / Fail |
| `UAT-006` | Continuous Work Context | Prior reliable work remains visible during review; the left panel of `/cases/:email_id/review` preserves the 4-column matrix showing reliable fields with green badges. | Pass / Fail |
| `UAT-007` | Automatic Recomputation | Corrected result recomputes automatically; submitting correction triggers immediate deterministic re-normalization and comparison, updating the case. | Pass / Fail |
| `UAT-008` | Clear Collision Resolution | Revision conflict is understandable to the reviewer; in-place collision modal clearly states another user saved changes, displays current server revision, and preserves unsubmitted inputs. | Pass / Fail |
| `UAT-009` | Actionable Export Blocking | Blocked export is understandable and actionable; export blocked dialog explains safety invariant DC-08 and lists direct links to resolve remaining cases. | Pass / Fail |

---

## 21. Regression Suite (REG-001 to REG-012)

Dedicated suite protecting against historical misconceptions, anti-patterns, and rejected rules identified during specification baselining.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               REGRESSION SUITE CATALOGUE                               │
├─────────┬─────────────────────────────────────────────────────────────┬────────────────┤
│ ID      │ Trap / Anti-Pattern Avoided                                 │ Priority       │
├─────────┼─────────────────────────────────────────────────────────────┼────────────────┤
│ REG-001 │ 0 attachments MUST NOT force non-comparison classification. │ P0 (Critical)  │
│ REG-002 │ No dataset-specific email-ID conditional branches in code.  │ P0 (Critical)  │
│ REG-003 │ No hardcoded dashboard KPIs or 0.0% false alarm claims.     │ P0 (Critical)  │
│ REG-004 │ No undocumented ±1kg gross weight tolerance (DEC-P06E TBD). │ P0 (Critical)  │
│ REG-005 │ No broad company suffix stripping (DEC-P06D TBD).           │ P0 (Critical)  │
│ REG-006 │ No automatic port/city/terminal equivalence (DEC-P06C TBD). │ P0 (Critical)  │
│ REG-007 │ No "<20 characters → OCR" fixed rule (Use Usability check). │ P0 (Critical)  │
│ REG-008 │ Provider failure alone != HITL if validated fallback works. │ P1 (Core)      │
│ REG-009 │ Partial reliable work MUST be preserved during HITL.        │ P0 (Critical)  │
│ REG-010 │ Unresolved result NEVER becomes false/no-mismatch.          │ P0 (Critical)  │
│ REG-011 │ Self-reported LLM confidence does NOT bypass validation.    │ P0 (Critical)  │
│ REG-012 │ UI/Reviewer CANNOT directly edit mismatch_detected boolean. │ P0 (Critical)  │
└─────────┴─────────────────────────────────────────────────────────────┴────────────────┘
```

Detailed regression test specifications:

- **`REG-001` (Zero Attachment Intent)**: Feed email requesting SI/BL check with zero attachments. Assert `category == "document_comparison"`. Stage 2 then escalates to `missing_attachment`. Assert category never changes to `general`.
- **`REG-002` (Zero Dataset Shortcuts)**: Scan codebase with AST parser to assert no `if email_id == "email_xxx":` constructs exist in `src/`.
- **`REG-003` (No Hardcoded Metrics)**: Verify `/audit` scorecard counts dynamically match `len(records)` and contains zero hardcoded strings (`520`, `21`, `63`, `0.0%`).
- **`REG-004` (No Undocumented Numeric Tolerance)**: Compare `22000 kg` vs `22001 kg`. Enforces exact Decimal equality after approved unit normalization; no undocumented numeric tolerance. Assert `outcome == "MISMATCH"`. Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06E TBD.
- **`REG-005` (No Organization Name Equivalence)**: Compare `"ACME CORP"` vs `"ACME CORPORATION"`. Enforces exact equality after currently approved normalization; no broad legal-suffix stripping; no token reordering or organization alias equivalence. Assert `outcome == "MISMATCH"`. Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06D TBD.
- **`REG-006` (No Port Semantic Equivalence)**: Compare `"SHANGHAI"` vs `"PORT OF SHANGHAI"`. Enforces exact equality after currently approved normalization; no automatic port alias, UN/LOCODE, city, or terminal equivalence. Assert `outcome == "MISMATCH"`. Protects CURRENT baseline behavior only; amendment-sensitive; does NOT resolve DEC-P06C TBD.
- **`REG-007` (No Fixed Char-Count OCR Trigger)**: Feed valid 18-character SI text. Assert text usability is valid; OCR is not triggered.
- **`REG-008` (Validated Fallback Prevents HITL)**: Simulate primary failure + successful validated fallback. Assert case completes without HITL.
- **`REG-009` (Preserve Partial Work)**: Inject error into 1 field while 6 match. Assert partial results store 6 matches; case is `NEEDS_REVIEW`.
- **`REG-010` (Unresolved Never Emits Clean Match)**: 6 match + 1 unextracted. Assert `mismatch_detected is None`, summary does not say `"No mismatch detected"`.
- **`REG-011` (Confidence Decoupling)**: Inject `confidence = 1.0` with ungrounded quote. Assert validator rejects extraction.
- **`REG-012` (No Direct Boolean Override)**: Send `ReviewUpdate(mismatch_detected=False)` to API. Assert HTTP 422 rejection.

---

## 22. Master Verification Matrix

Maps every authoritative requirement, architecture decision, AI policy, and data contract to planned/formal verification mechanisms using exact baselined identifiers:

| Authoritative Reference ID | Specification Description | Test Level | Primary Test IDs | Expected Evidence Produced | Coverage Status |
|---|---|---|---|---|---|
| **PRODUCT SPEC: FUNCTIONAL** | | | | | |
| `FR-001` | Ingest email records from inbox dataset in JSON format | Pipeline / Integration | `PIPE-CLS-001` | Ingested `EmailRecord` with parsed fields | `PLANNED` |
| `FR-002` | Categorize every email into exactly 1 designated category | Pipeline / Unit | `PIPE-CLS-001`–`003` | Validated `ClassificationResult` with 1 of 5 categories | `PLANNED` |
| `FR-003` | Execute SI/BL extraction/comparison ONLY for document_comparison | Pipeline / Integration | `PIPE-CLS-001`, `PIPE-CLS-005` | Gatekeeper execution log verifying document processing boundary | `PLANNED` |
| `FR-004` | Non-comparison emails terminate checking immediately | Pipeline / Integration | `PIPE-CLS-005` | Non-comparison `AuditRecord` emitted without attachment parsing | `PLANNED` |
| `FR-005` | Parse plain-text (`.txt`) attachments referenced in email | Parser / Unit | `PAR-TXT-001` | `ParserResult(status="SUCCESS", text=...)` | `COVERED` |
| `FR-006A` | Parse Word (`.docx`) attachments | Parser / Integration | `PAR-DOCX-001` | `ParserResult` containing paragraph and table structures | `PARTIALLY COVERED` |
| `FR-006B` | Parse PDF (`.pdf`) attachments | Parser / Integration | `PAR-PDF-001`, `PAR-PDF-002` | `ParserResult` with page references and stream error detection | `PARTIALLY COVERED` |
| `FR-006C` | Parse Excel (`.xlsx`) attachments (Design Extension) | Parser / Unit | `PAR-XLSX-001` | `ParserResult` containing sheet and cell coordinate data | `PARTIALLY COVERED` |
| `FR-007` | Handle table layouts, key-value listings, and free paragraphs | Parser / Vision | `PAR-DOCX-001`, `PAR-PDF-001` | Extracted cell coordinates and preserved table alignments | `PARTIALLY COVERED` |
| `FR-008` | Support scanned or image-only PDF documents via OCR/Vision | Parser / Vision | `PAR-USAB-003`, `AI-OCR-001` | Decoded text layer and bounding box metadata from image bytes | `PLANNED` |
| `FR-009` | SI is reference document; missing/unreadable SI routes to HITL | Pipeline / HITL | `PAR-ROLE-003`, `HITL-RSN-001` | Escalation payload citing SI absence or unreadable state | `PLANNED` |
| `FR-010` | Verify exactly and only 7 mandatory fields | Unit / Integration | `UT-EXT-001`–`013` | Structured entity dictionary containing all 7 comparison fields | `PLANNED` |
| `FR-011` | Return "No mismatch detected" ONLY when all 7 fields reliable and match | Pipeline / Unit | `PIPE-CMP-001`, `PIPE-CMP-004` | Exact string `"No mismatch detected"` emitted only on 7/7 match | `PARTIALLY COVERED` |
| `FR-012` | Flag specific mismatched fields side-by-side (`SI: x / BL: y`) | Pipeline / Unit | `PIPE-CMP-002`, `PIPE-CMP-003` | Structured `Discrepancy` array with field, `si_value`, `bl_value` | `PARTIALLY COVERED` |
| `FR-013` | Escalate for human review rather than guessing or failing silently | Pipeline / HITL | `HITL-RSN-001`–`007` | Structured `ReviewCase` containing non-null reason and evidence | `PLANNED` |
| `FR-014` | Trigger HITL when required result cannot be reliably established | Pipeline / HITL | `HITL-RSN-001`–`007` | Verified triggers for missing, unreadable, or conflicting items | `PLANNED` |
| `FR-015` | Escalation MUST provide reason and source-grounded evidence | HITL / Contract | `UT-EXT-012`, `HITL-RSN-001` | `ReviewIssue` containing `logical_reason` and `FieldEvidence` | `PLANNED` |
| `FR-016` | Allow human operators to review, confirm, or correct findings | API / HITL | `HITL-REV-001`–`006` | Updated `AuditRecord` revision reflecting operator corrections | `PLANNED` |
| `FR-017` | Handle processing failures visibly and allow retries | AI Adapter / API | `AI-BUD-001`, `AI-BUD-004` | Logged retry attempts and visible error states in audit record | `PLANNED` |
| **PRODUCT SPEC: NON-FUNCTIONAL** | | | | | |
| `NFR-001` | Deterministic Repeatability across canonical inputs | Unit / Pipeline | `PIPE-CMP-001`, `UT-NORM-004` | Identical hash/equality across repeated deterministic runs | `PLANNED` |
| `NFR-002` | Performance & Throughput (Proposed benchmark) | Performance | `PERF-001`–`007` | Latency and throughput execution metrics recorded | `PLANNED` |
| `NFR-003` | Robustness against Corrupted Files | Parser / Pipeline | `PAR-PDF-002`, `PAR-ROLE-008` | `PdfStreamError` intercepted; status `UNREADABLE`; no crash | `COVERED` |
| `NFR-004` | Extensible Pluggable Parsers | Parser Architecture | `PAR-TXT-001`–`XLSX-001` | `BaseParser` subclass polymorphism verified across formats | `COVERED` |
| `NFR-005` | Evaluation Submission Conformance (`sample_submission.json`) | Eval Adapter | `EVAL-MAP-001`–`007` | JSON artifact validating against official evaluation schema | `PARTIALLY COVERED` |
| **PRODUCT SPEC: CLASSIFICATION** | | | | | |
| `EC-001` | Exactly 5 canonical operational categories | Pipeline / Contract | `PIPE-CLS-001`, `CT-DATA-001` | Enum validation enforcing the 5 specified category strings | `PLANNED` |
| `EC-002` | Decouple Attachment Count from Intent | Pipeline / Regression | `PIPE-CLS-004`, `REG-001` | 0-attachment comparison request maintains comparison category | `PLANNED` |
| **PROJECT DESIGN DECISIONS** | | | | | |
| `DEC-01` | Deterministic SI/BL Comparator (No LLM comparison) | Pipeline / Unit | `PIPE-CMP-001`–`006` | Pure deterministic software comparison execution | `PARTIALLY COVERED` |
| `DEC-P01` | Provider-Agnostic Decoupled Architecture (`BaseAIAdapter`) | AI Adapter | `AI-ADP-001`–`006` | Mocked adapter executing without cloud SDK coupling | `PLANNED` |
| `DEC-P02` | Document Processing Layer & OCR/Vision Adapter | Parser / Vision | `PAR-USAB-001`–`004` | Tiered parser execution with OCR fallback on unusable text | `PLANNED` |
| `DEC-P03` | FastAPI REST API Web Application | API | `API-AUD-001`, `API-REV-001` | Validated REST routes returning OpenAPI compliant responses | `PARTIALLY COVERED` |
| `DEC-P04` | Platform-Agnostic Hosting (Container/Proc Agnostic) | Integration / Env | Docker CI execution | Headless container build running cleanly | `PLANNED` |
| `DEC-P05` | SPA + REST Decoupled Frontend | Frontend Contract | `UI-CT-001` | Static build mounting cleanly under FastAPI | `PLANNED` |
| `DEC-P06A` | Formatting Normalization (Unicode, punctuation, spacing, commas) | Unit | `UT-NORM-001`–`003` | Canonical normalized text output matching normalization spec | `PLANNED` |
| `DEC-P06B` | Unit Normalization (Exact mathematical MT $\rightarrow$ kg) | Unit | `UT-NORM-004`, `UT-NORM-006` | Exact mathematical transformation ($22 \times 1000 = 22000$) | `PLANNED` |
| `DEC-P06C` | Port Semantic Equivalence (Preserved TBD) | Regression / Unit | `REG-NORM-002` | Exact equality after currently approved normalization; no automatic port alias, UN/LOCODE, city, or terminal equivalence | `PLANNED` |
| `DEC-P06D` | Organization Name Equivalence (Preserved TBD) | Regression / Unit | `REG-NORM-003` | Exact equality after currently approved normalization; no broad legal-suffix stripping; no token reordering or organization alias equivalence | `PLANNED` |
| `DEC-P06E` | Numeric Tolerance (Preserved TBD) | Regression / Unit | `REG-NORM-001` | Exact Decimal equality after approved unit normalization; no undocumented numeric tolerance | `PLANNED` |
| **AI PIPELINE DECISIONS** | | | | | |
| `DEC-AI-P01` | Bounded Technical Retries (Configurable default: 3) | AI Adapter | `AI-BUD-001`, `AI-BUD-002` | Retry count logged; exponential backoff verified; cap enforced | `PLANNED` |
| `DEC-AI-P02` | Bounded Semantic Retries (Configurable default: 2) | AI Adapter | `AI-BUD-003` | Re-prompting with schema validation error executed | `PLANNED` |
| `DEC-AI-P03` | AI-on-Demand Execution Policy | Pipeline / Integration | `PIPE-CLS-007`, `PAR-ROLE-001` | Deterministic path resolves without calling AI adapter | `PLANNED` |
| `DEC-AI-P04` | Field-Level Reliability Gate & Partial Preservation | HITL / Pipeline | `HITL-PART-001`, `REG-009` | Reliable fields preserved in partial results during escalation | `PLANNED` |
| `DEC-AI-P05` | Generalized Source-Grounded Evidence | Unit / Contract | `UT-EXT-012`, `CT-DATA-005` | Validated `FieldEvidence` linking quote to source context | `PLANNED` |
| **DATA CONTRACTS DECISIONS** | | | | | |
| `DC-01` | Nullable Internal Category | Contract | `CT-DATA-001` | Category accepts `None` as internal unresolved state | `PLANNED` |
| `DC-02` | Rich Internal HITL Reason Taxonomy (Separated from Export)| Contract / Eval | `CT-DATA-002`, `EVAL-MAP-001` | Internal model accepts 7 reasons; export maps or blocks | `PLANNED` |
| `DC-03` | Tri-State Mismatch Model + Explicit Workflow State | Contract / Pipeline | `CT-DATA-003`, `PIPE-CMP-004` | Tri-state boolean (`True`, `False`, `None`) strictly enforced | `PLANNED` |
| `DC-04` | Decimal Gross Weight Representation | Contract / Unit | `CT-DATA-004`, `UT-NORM-005` | `Decimal` type validated without floating-point drift | `PLANNED` |
| `DC-05` | Source-Grounded FieldEvidence Model | Contract / Unit | `CT-DATA-005`, `UT-EXT-012` | Structured provenance model validated across extractions | `PLANNED` |
| `DC-06` | Normalized Attempt Limit Semantics | Contract / AI | `CT-DATA-006`, `AI-BUD-004` | Total attempts bounded and tracked per stage | `PLANNED` |
| `DC-07` | ReviewUpdate & Optimistic Revision Locking | Contract / API | `CT-DATA-007`, `HITL-REV-006` | `expected_revision` verified; HTTP 409 raised on collision | `PLANNED` |
| `DC-08` | Safe EXPORT_BLOCKED Behavior | Contract / Eval | `CT-DATA-008`, `API-EXP-002` | HTTP 409 `EXPORT_BLOCKED` returned on unconfirmed records | `PLANNED` |
| **UI/UX SPEC DECISIONS** | | | | | |
| Dedicated Review Route| `/cases/:email_id/review` Primary V1 Container | Frontend / E2E | `UI-REV-001`, `E2E-009` | Two-panel review workspace rendered on dedicated route | `PLANNED` |
| Four-Column Matrix | Field + SI + Draft BL + Outcome/Result | Frontend | `UI-DIFF-001`, `UI-DIFF-002` | 4-column diff matrix rendered across all 7 fields | `PLANNED` |
| Humanized Reason Labels| Primary operational copy for 7 logical reasons | Frontend | `UI-REV-002` | Operational text rendered instead of raw system enums | `PLANNED` |
| Concurrency Conflict | In-place HTTP 409 collision alert modal | Frontend | `UI-REV-003`, `E2E-012` | Conflict modal preserves edits and offers reload action | `PLANNED` |
| Export Blocked Dialog | Diagnostic modal explaining EXPORT_BLOCKED | Frontend | `UI-EXP-001`, `E2E-016` | Modal lists blocking email IDs with click-to-resolve links | `PLANNED` |
| Approved Stack | React + Vite + TypeScript + Tailwind CSS | Frontend Contract| `UI-CT-001` | TypeScript types verified against backend OpenAPI schema | `PLANNED` |

---

## 23. Existing Test Gap Analysis

An exhaustive audit of the 16 tests currently passing in `tests/`:

| Test Name | File | What It Actually Tests | Quality / Limitations | Baseline Spec Gaps Exposed |
|---|---|---|---|---|
| `test_root_endpoint` | `test_api.py` | `GET /` metadata | Passable smoke test. | Uses legacy `total_audited_emails` metric. Missing baselined scorecard fields. |
| `test_health_endpoint` | `test_api.py` | `GET /health` | Clean pass for process liveness. | Tests basic health. *(Note: Provider connectivity diagnostics are an OPTIONAL / OBSERVABILITY EXTENSION, not an implementation defect of this endpoint)*. |
| `test_get_single_audit_ok` | `test_api.py` | `GET /audit/email_001` | Tests legacy audit response. | Missing `revision`, `state`, `evidence`, and `documents` structure from `03_DATA_CONTRACTS.md`. |
| `test_get_single_audit_mismatch` | `test_api.py` | `GET /audit/email_025` | Checks mismatch on `container_count`. | Asserts legacy boolean format; lacks `revision` and full contract validation. |
| `test_dynamic_verify_endpoint` | `test_api.py` | `POST /verify` | Custom verify endpoint test. | `POST /verify` is not a baselined REST route; `POST /audit/{id}/review` is completely untested! |
| `test_text_parser` | `test_parsers.py` | `TextParser` on `email_001_SI.txt` | Reads live bundle file. | Flaky if bundle missing; does not test synthetic edge cases or usability check. |
| `test_excel_parser` | `test_parsers.py` | `ExcelParser` on `email_005_SI.xlsx` | Basic length check (>50 chars). | Does not verify row/col cell coordinate extraction or sheet handling. |
| `test_docx_parser` | `test_parsers.py` | `DocxParser` on first found docx | Skips if no docx found. | Weak assertion (`len > 50`); does not test table layout extraction (`FR-007`). |
| `test_pdf_parser_valid` | `test_parsers.py` | `PdfParser` on `email_059_SI.pdf` | Weak assertion (`len > 100`). | Reads live bundle file; does not verify page numbers or layout preservation. |
| `test_pdf_parser_corrupted` | `test_parsers.py` | `PdfParser` on `email_511_BL.pdf` | Checks `is_corrupted == True`. | Reads live bundle file; lacks synthetic corruption unit tests. |
| `test_classification_heuristics`| `test_pipeline.py`| Stage 1 on 4 bundle emails | **Major Flaw**: Asserts official competition strings (`BL_COMPARISON`), not canonical internal categories! | Does not test `general` category; does not test 0-attachment rule (`EC-002`, `REG-001`); no synthetic edge cases. |
| `test_stage2_missing_attachment`| `test_pipeline.py`| Stage 2 on `email_507` | Checks legacy `hitl_escalation`. | Uses legacy 4-reason taxonomy; missing `ReviewCase` / `ReviewIssue` models from `DC-02`. |
| `test_stage2_corrupted_pdf` | `test_pipeline.py`| Stage 2 on `email_511` | Checks legacy `hitl_escalation`. | Uses legacy reason `"unreadable"` instead of `unreadable_document`. |
| `test_stage3_matching_pair` | `test_pipeline.py`| Stage 3 on `email_001` | Monolithic text compare. | Does not test individual field extractions or evidence provenance. |
| `test_stage3_discrepancy_pair` | `test_pipeline.py`| Stage 3 on `email_025` | Monolithic text compare. | Does not verify Decimal gross weight or tri-state mismatch model. |
| `test_validator` | `test_pipeline.py`| Validates `sample_submission.json` | Trivial self-validation. | Validates sample file against itself; does not test adapter transformation or `EXPORT_BLOCKED`. |

### Critical Gap Summary
The existing 16 tests provide limited partial coverage of the baselined specification. Requirement coverage is determined by the Master Verification Matrix rather than raw pytest test count. The existing tests completely omit:
1. `ReviewUpdate` workflow, `action = "CONFIRM"`, and optimistic concurrency locking (`expected_revision`, HTTP 409).
2. The 7 approved `LogicalReason` types and partial reliable work preservation.
3. Tri-state `mismatch_detected` (`null` when incomplete).
4. `Decimal` gross weight representation and strict unit conversion.
5. `FieldEvidence` source grounding and anti-hallucination validation.
6. `EXPORT_BLOCKED` behavior on unconfirmed cases (DC-08).
7. Negative regression tests against unauthorized semantic equivalence (DEC-P06C/D/E).
8. Pluggable AI adapter schema enforcement and retry budget caps.
9. All frontend components, routes, and UI state matrices.

---

## 24. Automation Priority

To guide execution in `specs/06_TASKS.md`, test cases are prioritized across operational tiers. The baseline establishes the P0 critical test set across 10 functional categories:

- **Priority 0 (P0 — Critical Safety & Core Correctness)**:
  - Tri-state `mismatch_detected` (`PIPE-CMP-004`, `CT-DATA-003`).
  - 5-category classification and zero-attachment regression (`PIPE-CLS-004`, `REG-001`).
  - Strict Pydantic v2 data contract validation for DC-01 through DC-08.
  - All 7 mandatory field extractions and `FieldEvidence` grounding (`UT-EXT-001`–`013`).
  - HITL escalation and 7 logical reasons (`HITL-RSN-001`–`007`).
  - Human review correction, optimistic locking (409), and recomputation (`HITL-REV-001`–`006`).
  - Safe `EXPORT_BLOCKED` behavior on unconfirmed records (`EVAL-MAP-002`, `API-EXP-002`).
  - Negative regression guards against unauthorized equivalence (`REG-NORM-001`–`003`).
  - Read-only dataset protection (`SEC-DATA-001`).

- **Priority 1 (P1 — Core Workflows & Robustness)**:
  - Alternative field labels and multiline extraction (`UT-EXT-002`, `UT-EXT-003`).
  - Deterministic-first bypass tests (`PIPE-CLS-007`, `PAR-ROLE-001`).
  - Text Usability Validation rules (`PAR-USAB-001`–`004`).
  - AI retry budgets and repair prompts (`AI-BUD-001`, `AI-BUD-003`).
  - Frontend 4-column matrix, evidence drawer, and dedicated review workspace (`UI-DIFF-001`, `UI-REV-001`).
  - API listing filters and pagination (`API-AUD-001`).
  - E2E primary scenarios (`E2E-001`–`009`).

- **Priority 2 (P2 — Secondary Extensions & Deep Validation)**:
  - Excel parser edge cases (`PAR-XLSX-001`).
  - Provider budget limit verification (`AI-BUD-004`).
  - WCAG 2.1 AA automated contrast and accessibility scans (`ACC-004`).
  - Narrow-screen stacked card transformation (`RESP-002`).
  - Provider fallback execution tests (`AI-OCR-005`).

- **Priority 3 (P3 — Observability & Polish)**:
  - Performance latency benchmarks (`PERF-001`–`007`).
  - Deterministic avoidance rate observability (`PERF-006`).
  - Advanced layout visual regression testing.

---

## 25. Entry & Exit Criteria

### 25.1 Phase Entry Criteria
- Baselined specifications `00_PRODUCT_SPEC.md`, `01_PROJECT_DESIGN.md`, `02_AI_PIPELINE_SPEC.md`, `03_DATA_CONTRACTS.md`, and `04_UI_UX_SPEC.md` approved.
- `05_TEST_PLAN.md` drafted and under human review.

### 25.2 Implementation Task Exit Criteria (Definition of Done)
An implementation task in `specs/06_TASKS.md` is complete **ONLY** when:
1. All P0 automated test cases associated with the requirement pass cleanly.
2. New code adheres strictly to baselined Pydantic schemas.
3. Relevant regression tests (REG-001 through REG-012) pass without failure.
4. Zero files in `sdoc-hackathon-bundle/` are modified or deleted.
5. No unresolved hardcoded shortcuts or dataset-specific rules are introduced.
6. Documentation and test traceability matrices are updated.

---

## 26. Known Business TBDs

The following domain business rules remain open TBDs per [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) and [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md):

1. **`DEC-P06C` (Port Semantic Equivalence)**:
   - Current Baseline Behavior: Exact equality after currently approved normalization; no automatic port alias, UN/LOCODE, city, or terminal equivalence.
   - Verification: Tests `REG-NORM-002`, `REG-006`, and `PIPE-CMP-001` verify this invariant.
2. **`DEC-P06D` (Organization Name Equivalence)**:
   - Current Baseline Behavior: Exact equality after currently approved normalization; no broad legal-suffix stripping; no token reordering or organization alias equivalence.
   - Verification: Tests `REG-NORM-003` and `REG-005` verify this invariant.
3. **`DEC-P06E` (Numeric Tolerance)**:
   - Current Baseline Behavior: Exact Decimal equality after approved unit normalization; no undocumented numeric tolerance.
   - Verification: Tests `REG-NORM-001` and `REG-004` verify this invariant (e.g. $\pm 1\text{ kg}$ is flagged as a mismatch).

> [!IMPORTANT]
> **Governance Invariant**: These tests protect CURRENT baseline behavior only. They remain amendment-sensitive and MUST NOT resolve the TBD business decisions. The test plan does not resolve these TBDs autonomously; tests assert current strict baseline behavior until a formal requirement amendment is approved.

---

## 27. Open Governance Questions

The following operational questions are submitted for user review:

1. **Synthetic vs Live Bundle in Regression CI**:
   - *Recommendation*: Migrate all automated pytest runs to 100% synthetic fixtures under `tests/fixtures/`, reserving `sdoc-hackathon-bundle/` solely for optional large-scale batch evaluation runs.
2. **Frontend Test Framework Approval**:
   - *Recommendation*: Approve **Vitest + React Testing Library** for frontend component unit tests, and **Playwright** for headless E2E verification.
3. **Contract Drift Automation**:
   - *Recommendation*: Approve an automated script (`scripts/verify_contracts.py`) that exports FastAPI OpenAPI schemas and verifies that TypeScript types in `frontend/src/types/` are strictly synchronized.

---

## 28. Document Governance & Status Gate

- **Current Status**: `APPROVED / BASELINED`
- **Revision**: `2.0-baselined (2026-09-22)`
- **Authority Chain**: `Original Use Case PDF → 00_PRODUCT_SPEC.md (v3.1) → 01_PROJECT_DESIGN.md (v3.0) → 02_AI_PIPELINE_SPEC.md (v3.1) → 03_DATA_CONTRACTS.md (v2.0) → 04_UI_UX_SPEC.md (v2.0) → 05_TEST_PLAN.md (v2.0)`
- **Subsequent Stage**: Drafting [`specs/06_TASKS.md`](06_TASKS.md) (Work breakdown, execution queue, and implementation gates).
