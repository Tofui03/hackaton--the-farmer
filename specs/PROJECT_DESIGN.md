# PROJECT_DESIGN.md — System Architecture & Technical Design Specification

> **Document Type**: Technical Architecture & System Design Document  
> **Implements**: [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md) / [`specs/PRODUCT_SPEC.md`](file:///d:/ship/specs/PRODUCT_SPEC.md)  
> **Source of Truth**: [`Shipping Document Verification Use Case.pdf`](file:///d:/ship/Shipping%20Document%20Verification%20Use%20Case.pdf)  
> **Methodology**: Spec-Driven Development (SDD) — Phase 2 Architecture & Design  
> **Status**: APPROVED / BASELINED  
> **Revision**: 3.0 (Baselined System Architecture; Unresolved Decisions Explicitly Preserved as TBD)

---

## 1. System Overview

The **Shipping Document Verification Engine** is an automated maritime documentation auditing and discrepancy detection platform. Its core objective is to ingest operational emails received by a shipping operations team, classify their intent, extract structured shipment entities from multi-format attachments (Shipping Instructions and draft Bills of Lading), and execute verification across seven mandatory fields.

### 1.1 Architectural Objectives
- **False-Positive Discrepancy Minimization** `[REQUIRED BY SOURCE - PDF Page 2]`:
  Minimize false-positive discrepancies through deterministic normalization and explicit uncertainty handling. The system **MUST NOT** claim zero false alarms unless demonstrated by empirical evaluation results.
- **SI is the Reference Document for Comparison** `[REQUIRED BY SOURCE - PDF Page 1]`:
  The Shipping Instruction (SI) contains intended shipment details and serves as the reference document for this check. If the SI itself is unavailable or unreadable, the case MUST escalate to human review (HITL) rather than proceeding with an unreliable reference.
- **Transparent Human-in-the-Loop (HITL)** `[REQUIRED BY SOURCE - PDF Page 1, 2]`:
  When the system cannot form a dependable decision due to corrupted, missing, ambiguous, or illegible documents, it MUST route the case to human operators with explicit reason codes and source evidence snippets rather than guessing or failing silently.
- **Provider-Agnostic Decoupled Architecture** `[APPROVED DESIGN DECISION WITH MODIFICATION - DEC-P01]`:
  Separate document parsing, semantic extraction, deterministic normalization, and business comparison into independent, testable stages via abstract adapter interfaces.
- **Standardized Evaluation Delivery** `[EVALUATION - PDF Page 3, 4]`:
  When self-evaluation is used, the submission artifact MUST conform to `sample_submission.json`. This format does not constrain the internal system data model.

---

## 2. High-Level Architecture

The system is organized into five decoupled layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          1. PRESENTATION LAYER                              │
│  - SPA + REST Decoupled Frontend [APPROVED DESIGN DECISION - DEC-P05]       │
│  - Concrete framework & hosting deferred to specs/04_UI_UX_SPEC.md          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         2. BACKEND SERVICE LAYER                            │
│  - REST API Web Application [APPROVED DESIGN DECISION - DEC-P03: FastAPI]   │
│  - Platform-Agnostic Hosting [DEFERRED - DEC-P04: Container/Proc Agnostic]  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Pipeline Controller
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                      3. PIPELINE & CORE LOGIC LAYER                         │
│  - Stage 1: Email Intent Classifier & Gatekeeper [CORE]                     │
│  - Stage 2: Attachment Ingestion & Triage [CORE / ADVANCED]                 │
│  - Stage 3A: Entity Extraction & Semantic Normalization [CORE / ADVANCED]   │
│  - Stage 3B: Deterministic SI vs BL Comparator [APPROVED DESIGN DECISION]   │
│  - Human Review Manager (HITL Escalations) [CORE / ADVANCED]                │
│  - Output Contract Serializer & Schema Validator [EVALUATION]               │
└──────────────────┬───────────────────────────────────┬──────────────────────┘
                   │                                   │
┌──────────────────▼──────────────────┐ ┌──────────────▼──────────────────────┐
│         4. AI / LLM LAYER           │ │   5. DOCUMENT PROCESSING LAYER     │
│ [APPROVED WITH MODIFICATION: DEC-P01│ │ [APPROVED: DEC-P02 / EXTENSION]    │
│ - Provider-Agnostic BaseAIAdapter   │ │ - Abstract Base Parser Interface   │
│ - Initial Provider: Gemini adapter  │ │ - Plain Text Parser (.txt) [CORE]  │
│ - Classification & Extraction prompt│ │ - Word Document Parser (.docx)[ADV]│
│ - Exponential Backoff & Retry Logic │ │ - PDF Parser (with stream check)[ADV│
│ - Deterministic Fallback Engine     │ │ - OCR / Vision Adapter [ADV - P02] │
│                                     │ │ - Excel Parser (.xlsx) [EXTENSION] │
└──────────────────┬──────────────────┘ └──────────────┬──────────────────────┘
                   │                                   │
┌──────────────────▼───────────────────────────────────▼──────────────────────┐
│                            DATA ACCESS LAYER                                │
│ - Inbox Dataset Loader (Static JSON or HTTP Server) [CORE]                  │
│ - Attachment Binary / Stream Loader [CORE / ADVANCED]                       │
│ - Execution Checkpoint Persistence Cache [APPROVED DESIGN DECISION]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. System Components

### 3.1 Inbox Manager
- **Requirement Level**: `CORE` `[REQUIRED BY SOURCE - PDF Page 3]`
- **Responsibility**: Ingests email records from the inbox dataset (via local directory or local server endpoint).
- **Behavior**: Provides an iterable stream of email records to downstream pipeline components without hardcoding dataset assumptions.

### 3.2 Email Classifier
- **Requirement Level**: `CORE` `[REQUIRED BY SOURCE - PDF Page 1]`
- **Responsibility**: Categorize each inbound email into exactly one of five operational classes:
  1. `document_comparison`
  2. `new_si_request`
  3. `invoice_query`
  4. `general_message`
  5. `spam`
- **Gating Mechanism (`First-Stage Veto`)**: Only `document_comparison` emails proceed to document processing. All other categories terminate immediately and emit non-comparison audit records.

### 3.3 Attachment Processor
- **Requirement Level**: `CORE` `[REQUIRED BY SOURCE - PDF Page 1, 2]`
- **Responsibility**: Detects and pairs corresponding SI and draft BL attachments referenced in the email record.
- **Triage**: Identifies missing attachments (e.g. fewer than 2 attachments or unpaired documents) and raises an escalation without invoking document extractors.

### 3.4 Document Extractor & OCR Adapter
- **Requirement Level**: `CORE` (txt) / `ADVANCED` (docx, pdf, scanned) / `DESIGN EXTENSION` (xlsx)
- **Status**: `[APPROVED DESIGN DECISION - DEC-P02]`
- **Responsibility**: Ingests raw attachments across supported formats (`.txt`, `.docx`, `.xlsx`, `.pdf`) and extracts text and table contents.
- **Scanned & Image-Only Strategy (`DEC-P02`)**: For image-only PDFs or scanned pages, the system **first attempts OCR / vision extraction**. It escalates to HITL (`unreadable`) only if extraction is missing, inconsistent, unreadable, or insufficiently reliable.
- **Defensive Parsing**: Detects corrupted file streams (`PdfStreamError`) and flags them for human escalation rather than throwing unhandled runtime crashes.

### 3.5 Field Normalizer
- **Status**: `[APPROVED DESIGN DECISIONS - DEC-P06A, DEC-P06B; TBD - DEC-P06C, DEC-P06D, DEC-P06E]`
- **Responsibility**: Performs controlled normalization across extracted fields:
  - **Formatting (`DEC-P06A - APPROVED`)**: Normalizes Unicode, capitalization, whitespace, punctuation, and numeric separators (commas).
  - **Unit Conversion (`DEC-P06B - APPROVED`)**: Mathematically exact conversion (e.g. $\text{MT} \times 1000 \rightarrow \text{kg}$).
  - **Port Equivalence (`DEC-P06C - TBD`)**: Port name, city, terminal, and UN/LOCODE equivalence requires explicit canonical mapping.
  - **Organization Names (`DEC-P06D - TBD`)**: Broad legal suffix removal is prohibited; only explicitly defined aliases (e.g. `LTD`/`LIMITED`) are normalized.
  - **Numeric Tolerance (`DEC-P06E - TBD`)**: Default to exact normalized comparison. No arbitrary $\pm 1\text{ kg}$ tolerance without validated business rules.

### 3.6 Deterministic SI/BL Comparator
- **Status**: `[APPROVED DESIGN DECISION - DEC-01]`
- **Architectural Rule**: The comparison engine **MUST NOT** delegate the final match/mismatch decision to an unconstrained LLM.
- **Responsibility**: Takes structured, normalized entity dictionaries from both documents and executes deterministic, testable comparison rules:
  - If all seven fields match: Emits `"No mismatch detected"`.
  - If discrepancies exist: Records each defect with side-by-side values (`SI: <val> / BL: <val>`).

### 3.7 Human Review Manager (HITL)
- **Requirement Level**: `CORE` (reasons & evidence) / `ADVANCED` (scanned/corrupt handling)
- **Responsibility**: Intercepts pipeline uncertainty, missing data, file corruption, or unreadable documents.
- **Output**: Produces structured escalation objects containing:
  - `needed: true`
  - `reason`: `"wrong_doc_type"` | `"missing_attachment"` | `"unreadable"` | `"missing_value"`
  - `evidence`: Extracted text snippet, missing filename, or exception context.

### 3.8 Report Generator
- **Requirement Level**: `EVALUATION` `[REQUIRED BY SOURCE - PDF Page 4]`
- **Responsibility**: Formats and serializes output conforming to the official evaluation contract (`sample_submission.json`) and exports extended audit records for operator inspection.

---

## 4. End-to-End Workflow

```
[Inbound Email]
       │
       ▼
[Stage 1: Intent Classifier] ──── Non-Comparison ───► [Emit Non-Comparison Record]
       │
       ▼ (document_comparison)
[Stage 2: Attachment Validation] ── Missing / Invalid ─► [HITL: missing_attachment / wrong_doc_type]
       │
       ▼ (Valid SI & BL Attachments)
[Stage 2B: Document Parser] ────── Corrupted Stream ───► [HITL: unreadable]
       │
       ▼ (Scanned Image?) ──── Yes ───► [Attempt OCR / Vision Extraction]
       │                                       │
       │                        Extraction Fails / Low Confidence
       │                                       │
       │                                       ▼
       │                               [HITL: unreadable]
       ▼ (Parsed Text / Extracted Content)
[Stage 3A: Entity Extraction & Normalization] ── Missing Field ─► [HITL: missing_value]
       │
       ▼ (Structured Normalized Dicts: SI_data & BL_data)
[Stage 3B: Deterministic Comparator]
       │
       ├─────────────────────────────────┐
       ▼ (All 7 Fields Match)            ▼ (Discrepancies Found)
["No mismatch detected"]          [Flag Discrepant Fields (SI: x / BL: y)]
       │                                 │
       └────────────────┬────────────────┘
                        │
                        ▼
       [Data Contract Validation (Pydantic)]
                        │
                        ├───────────────────────────────┐
                        ▼                               ▼
            [Official Submission JSON]        [Audit Report JSON]
```

---

## 5. AI Pipeline Design

### 5.1 Provider-Agnostic Adapter Pattern (`DEC-P01`)
The core system communicates with AI capabilities solely through an abstract adapter interface:

```python
class BaseAIAdapter(ABC):
    @abstractmethod
    def classify_email(self, email_data: dict) -> str:
        """Classifies email into one of five operational categories."""
        pass

    @abstractmethod
    def extract_entities(self, document_text: str) -> dict:
        """Extracts candidate shipment fields into structured key-value format."""
        pass

    @abstractmethod
    def extract_from_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """Extracts candidate shipment fields from image-only / scanned documents."""
        pass
```
- **Initial Implementation**: `GeminiAIAdapter` (using Google GenAI SDK).
- **Extensibility**: Alternative adapters (`OpenAIAdapter`, `LocalLLMAdapter`) can be plugged in without modifying core pipeline logic.

### 5.2 Responsibility Separation Principle
- **LLM / Vision Models are responsible for**:
  1. Semantic intent understanding (email classification).
  2. Entity extraction from unstructured text, tables, and vision/OCR documents into structured key-value objects.
  3. Header alias interpretation.
- **Deterministic Code is responsible for**:
  1. Unit conversion (MT $\rightarrow$ kg).
  2. Number parsing (container counts).
  3. Final comparison logic (`==`, `!=`, numeric tolerance checking).
  4. Decision reporting (`"No mismatch detected"` vs defect flagging).

---

## 6. Frontend Architecture

- **Status**: `[APPROVED DESIGN DECISION WITH MODIFICATION - DEC-P05]`
- **Architectural Boundary**: Frontend/backend separation and SPA + REST architecture are approved.
- **Deferred Decisions**: Concrete hosting platforms (e.g. GitHub Pages) and UI framework selections (e.g. Vanilla JS, Tailwind CSS, React) are deferred to [`specs/04_UI_UX_SPEC.md`](file:///d:/ship/specs/04_UI_UX_SPEC.md).
- **Core Principle**: **Dynamic Metric Calculation**. The frontend **MUST NOT** hardcode any counts or percentages.
- **Data Flow**:
  $$\text{Audit JSON / API Response} \longrightarrow \text{Dynamic Client-Side Aggregation} \longrightarrow \text{Rendered KPI Metrics}$$

---

## 7. Backend Architecture

- **Status**: `[APPROVED DESIGN DECISION - DEC-P03; DEFERRED - DEC-P04]`
- **Framework**: Python ASGI Application using **FastAPI + Uvicorn** (`DEC-P03`).
- **Platform Agnosticism (`DEC-P04`)**: The backend must remain container/deployment-platform agnostic. Render may serve as the initial deployment target, but the application must run identically in local Docker, Linux VMs, or other PaaS platforms via standard environment bindings (`$PORT`, `HOST`).
- **Operational Mode**: Stateless REST API serving precomputed audit runs or performing real-time verification of uploaded documents.

---

## 8. API Design

| Method | Route | Description | Status |
|---|---|---|---|
| `GET` | `/health` | Health check probe for container liveness | `[APPROVED - DEC-P03]` |
| `GET` | `/audit` | Query audit records with optional filters (`category`, `mismatch_only`, `hitl_only`) | `[APPROVED - DEC-P03]` |
| `GET` | `/audit/{email_id}` | Query single audit record by email ID | `[APPROVED - DEC-P03]` |
| `POST` | `/verify` | Dynamic verification endpoint for on-demand text/document checks | `[APPROVED - DEC-P03]` |
| `GET` | `/submission` | Retrieve official evaluation submission artifact | `[APPROVED - DEC-P03]` |
| `GET` | `/docs` | OpenAPI / Swagger interactive documentation | `[APPROVED - DEC-P03]` |

---

## 9. Data Models (Strict Contracts)

```python
class Discrepancy(BaseModel):
    field: str
    si_value: Any
    bl_value: Any

class HITLEscalation(BaseModel):
    needed: bool = False
    reason: Optional[str] = None  # wrong_doc_type | missing_attachment | unreadable | missing_value
    evidence: Optional[str] = None

class AuditOutputRecord(BaseModel):
    email_id: str
    category: str
    mismatch_detected: bool = False
    result_summary: str = "No mismatch detected"
    discrepancies: List[Discrepancy] = []
    hitl_escalation: HITLEscalation = HITLEscalation()
```

---

## 10. Error Handling Strategy

- **File Corruption & Format Errors** `[REQUIRED BY SOURCE - PDF Page 2]`:
  PDF stream truncation, corrupted archives, or invalid file encodings are caught at the parser level and routed to HITL with reason `unreadable`. The pipeline must never crash.
- **Missing Attachments** `[REQUIRED BY SOURCE - PDF Page 2]`:
  Missing files on disk or emails with insufficient attachments are caught at the triage stage and routed to HITL with reason `missing_attachment`.
- **API Transient Failures** `[PROPOSED]`:
  Network drops or HTTP 429/503 errors trigger exponential backoff retry. If retries are exhausted, the pipeline falls back to deterministic heuristics.

---

## 11. Human-in-the-Loop (HITL) Design

### 11.1 Standardized Escalation Triggers
The system MUST support four standardized escalation reasons derived from the use case:

| Trigger Code | Cause Description | Example Scenario |
|---|---|---|
| `missing_attachment` | Email does not contain the required pair of attachments | Email references draft BL check but has only 1 attachment |
| `unreadable` | Extraction fails after OCR/vision attempt, or file stream is corrupt | Truncated PDF stream, corrupt binary, or scanned image where OCR produces illegible/uncertain text |
| `wrong_doc_type` | Attachments do not represent an SI and draft BL | Attached files are invoices, packing lists, or unrelated images |
| `missing_value` | One of the 7 mandatory fields is absent from either document | SI does not list Gross Weight or Container Count |

### 11.2 Evidence Requirement `[REQUIRED BY SOURCE - PDF Page 2]`
Every escalation MUST include:
- `email_id`: The identifier of the affected email.
- `reason`: One of the four trigger codes.
- `evidence`: Specific contextual detail (e.g. filename, error description, or partial text snippet).

---

## 12. Logging & Observability

- **Structured Logging**: Standard logging format with timestamps, log levels, and component tags.
- **Execution Progress**: Dynamic progress indicators during batch operations without polluting stdout.
- **Dynamic Run Summaries**: Post-run statistics computed and reported dynamically upon completion.

---

## 13. Security Considerations

- **Secrets Management**: API credentials MUST be read strictly from environment variables.
- **Data Immutability** `[REQUIRED BY SOURCE]`: All operations on input datasets are strictly read-only.
- **Repository Hygiene**: Local environment configurations (`.env`), cache files, and private keys MUST be excluded via `.gitignore`.

---

## 14. Testing Strategy

The system enforces a multi-tier automated test suite:
1. **Parser Tests**: Validate extraction and corruption handling across `.txt`, `.docx`, `.xlsx`, and `.pdf` files.
2. **Classification Tests**: Validate intent categorization and non-comparison gating.
3. **Normalization & Comparator Tests**: Validate unit conversions (MT $\rightarrow$ kg), integer container counts, and deterministic discrepancy generation.
4. **HITL Tests**: Verify that corrupted files, missing attachments, and missing fields trigger explicit escalations with evidence.
5. **Contract Tests**: Validate output schema compliance against `sample_submission.json`.
6. **API Tests**: Verify endpoint status codes and response schemas.

---

## 15. Evaluation Strategy

- **Scoring Weights**:
  $$\text{Evaluation Metrics} = \text{TBD (Determined by the official evaluation endpoint / participant guide)}$$
  > [!IMPORTANT]
  > The system **MUST NOT** assume undocumented scoring weights or formulas. The evaluation endpoint (`POST /submit`) evaluates results against a private reference set without returning reference answers.
- **Self-Evaluation Integration (`OPEN QUESTION 2 DECISION - APPROVED`)`:
  - The official local `/submit` self-evaluation endpoint (via local server or `loader.py`) is approved for integration into the development validation loop once baseline pipeline operations are stable.
  - **Strict Anti-Leakage Guardrail**: Evaluation feedback must **never** result in email-ID-specific logic, hardcoded answers, or dataset-specific overrides.
- **Core Optimization Vectors** `[REQUIRED BY SOURCE - PDF Page 2, 4]`:
  1. Accuracy: Identifying the right requests and right discrepancies without creating false alarms.
  2. Reliability: Transparent and dependable human review escalation when inputs are unreadable, missing, or uncertain.
  3. Schema Compliance: 100% adherence to the required JSON structure in `sample_submission.json`.

---

## 16. Technology Stack Categorization

| Layer | Component / Technology | Status | Decision / Rationale |
|---|---|---|---|
| **Runtime** | Python 3.10+ | `[APPROVED DESIGN DECISION]` | Standard environment for data manipulation and LLM SDKs |
| **Data Validation** | Pydantic 2.0+ | `[APPROVED DESIGN DECISION]` | High-performance schema validation and serialization |
| **Web API** | FastAPI + Uvicorn | `[APPROVED DESIGN DECISION - DEC-P03]` | Standard ASGI framework for REST endpoints |
| **Local Parsers (Core/Adv)** | `pypdf`, `python-docx` | `[APPROVED DESIGN DECISION]` | Parsers for source-mandated text, docx, and pdf formats |
| **Local Parsers (Extension)**| `openpyxl` | `[DESIGN EXTENSION]` | Extends support to tabular Excel files |
| **AI Architecture** | `BaseAIAdapter` (Provider-Agnostic) | `[APPROVED WITH MODIFICATION - DEC-P01]` | Decoupled adapter interface; Gemini is initial adapter |
| **OCR / Vision** | Multimodal / Vision OCR Adapter | `[APPROVED DESIGN DECISION - DEC-P02]` | Attempted first on image-only/scanned documents before HITL |
| **Cloud Hosting** | Platform Agnostic (Render initial) | `[DEFERRED - DEC-P04]` | Deployment platform is not locked; runs anywhere |
| **Frontend** | Decoupled SPA + REST | `[APPROVED WITH MODIFICATION - DEC-P05]` | Specific framework and hosting deferred to UI_UX_SPEC |
| **Testing** | Pytest | `[APPROVED DESIGN DECISION]` | Standard automated test runner |

---

## 17. Project Folder Structure

```text
d:\ship\
├── AGENTS.md                      # AI Agent behavioral governance & constraints
├── requirements.txt               # Dependency specifications
├── render.yaml                    # Initial deployment target configuration [DEFERRED DEC-P04]
├── Procfile                       # Process entrypoint
├── main.py                        # Web application entrypoint
├── app.py                         # REST API application routes
│
├── specs/                         # Spec-Driven Development documentation
│   ├── PRODUCT_SPEC.md            # Product Requirements Specification
│   ├── PROJECT_DESIGN.md          # System Architecture Specification
│   ├── 00_PRODUCT_SPEC.md         # Synchronized Product Spec
│   ├── 01_PROJECT_DESIGN.md       # Synchronized Technical Design
│   ├── 02_AI_PIPELINE_SPEC.md     # AI Pipeline Specification
│   ├── 03_DATA_CONTRACTS.md       # Strict Data Contracts
│   ├── 04_UI_UX_SPEC.md           # UI/UX & Frontend Specification
│   ├── 05_TEST_PLAN.md            # Test Strategy & Test Matrix
│   └── 06_TASKS.md                # Task Execution Queue
│
├── src/                           # Implementation source code
│   ├── config.py                  # Settings & environment variables
│   ├── parsers/                   # Document parsing subsystem
│   ├── llm/                       # Provider-agnostic AI adapters & prompts
│   ├── pipeline/                  # Pipeline orchestration & deterministic comparator
│   └── run_pipeline.py            # CLI pipeline runner
│
├── docs/                          # Static dashboard assets [Deferred to UI_UX_SPEC]
└── tests/                         # Automated test suite
```

---

## 18. Requirements Traceability Matrix (RTM)

### 18.1 Requirement Level Legend
- `CORE`: Baseline common expectations derived from the source use case (PDF Page 1, 3, 4).
- `ADVANCED`: Advanced stage capabilities covering complex document formats, image OCR, and reliability/HITL flows (PDF Page 2).
- `DESIGN EXTENSION`: Architectural enhancements introduced to extend capability beyond original PDF requirements (e.g. `.xlsx`).
- `EVALUATION`: Evaluation interface format constraints applicable when using the self-evaluation endpoint (PDF Page 4).

### 18.2 Traceability Table

| Requirement ID | Requirement Level | Requirement Summary | Source | Design Component | Implementation | Automated Test |
|---|---|---|---|---|---|---|
| **FR-001** | `CORE` | Ingest JSON email records | PDF p. 1 | Inbox Manager | `src/run_pipeline.py` | `tests/test_pipeline.py` |
| **FR-002** | `CORE` | Categorize into 1 of 5 classes | PDF p. 1 | Email Classifier | `src/pipeline/stage1_classify.py` | `test_classification_heuristics` |
| **FR-003** | `CORE` | Only process `document_comparison` | PDF p. 1 | Pipeline Gatekeeper | `src/pipeline/stage1_classify.py` | `test_classification_heuristics` |
| **FR-004** | `CORE` | Terminate non-comparison emails | PDF p. 1 | Pipeline Gatekeeper | `src/pipeline/stage1_classify.py` | `test_classification_heuristics` |
| **FR-005** | `CORE` | Parse `.txt` attachments | PDF p. 1, 3 | Document Extractor | `src/parsers/text_parser.py` | `test_text_parser` |
| **FR-006A**| `ADVANCED` | Parse Word documents (`.docx`) | PDF p. 2 | Document Extractor | `src/parsers/docx_parser.py` | `test_docx_parser` |
| **FR-006B**| `ADVANCED` | Parse PDF documents (`.pdf`) | PDF p. 2 | Document Extractor | `src/parsers/pdf_parser.py` | `test_pdf_parser_valid` |
| **FR-006C**| `DESIGN EXTENSION` | Parse spreadsheets (`.xlsx`) | Extension | Document Extractor | `src/parsers/excel_parser.py` | `test_excel_parser` |
| **FR-007** | `ADVANCED` | Handle tables and page layouts in docx/pdf | PDF p. 2 | Document Extractor | `src/parsers/` | `test_docx_table_layout_extraction`<br>`test_pdf_layout_extraction [PLANNED]` |
| **FR-008** | `ADVANCED` | Support scanned / image-only documents | PDF p. 2 | Vision / OCR Adapter | `src/parsers/docai_adapter.py` | `test_scanned_ocr_extraction [PLANNED]` |
| **FR-009** | `CORE` | SI is the reference document for comparison | PDF p. 1 | Comparator | `src/pipeline/stage3_compare.py` | `test_stage3_matching_pair` |
| **FR-010** | `CORE` | Check 7 mandatory fields | PDF p. 2 | Field Normalizer & Comparator | `src/pipeline/stage3_compare.py` | `test_stage3_discrepancy_pair` |
| **FR-011** | `CORE` | Report "No mismatch detected" | PDF p. 2 | Comparator | `src/pipeline/stage3_compare.py` | `test_stage3_matching_pair` |
| **FR-012** | `CORE` | Flag defects side by side (`SI: x / BL: y`) | PDF p. 2 | Comparator | `src/pipeline/stage3_compare.py` | `test_stage3_discrepancy_pair` |
| **FR-013** | `CORE` | Escalate uncertainty to HITL | PDF p. 1, 2 | Human Review Manager | `src/pipeline/schema.py` | `test_stage2_missing_attachment` |
| **FR-014** | `ADVANCED` | Image-only documents attempt OCR/Vision first; escalate if unreliable | PDF p. 2 | Attachment Processor & Parsers | `src/pipeline/stage2_extract.py` | `test_stage2_corrupted_pdf` |
| **FR-015** | `CORE` | Provide `review_reason` and `evidence` | PDF p. 2 | Human Review Manager | `src/pipeline/schema.py` | `test_stage2_missing_attachment` |
| **FR-016** | `ADVANCED` | Operator review & report updates | PDF p. 2 | REST API & Dashboard | `app.py`, `docs/index.html` | `test_dynamic_verify_endpoint` |
| **FR-017** | `ADVANCED` | Handle failures visibly with retries | PDF p. 2 | AI Client & Error Handler | `src/llm/client.py` | `test_api.py` |
| **NFR-003**| `ADVANCED` | Corrupt streams do not crash | PDF p. 2 | PDF Parser | `src/parsers/pdf_parser.py` | `test_pdf_parser_corrupted` |
| **NFR-005**| `EVALUATION` | When self-evaluation is used, the submission artifact MUST conform to sample_submission.json. This format does not constrain the internal system data model. | PDF p. 4 | Report Validator | `src/pipeline/validator.py` | `test_validator` |

---

## 19. Design Decision Register

> [!NOTE]
> Baselining this specification does **NOT** imply that all design decisions are final. The unresolved items below (`DEC-P06C`, `DEC-P06D`, `DEC-P06E`) are explicitly preserved as **TBD**. These TBD items may **only** be resolved through an approved specification amendment.

| Decision ID | Area | Decision Summary | Status |
|---|---|---|---|
| **DEC-01** | Core Comparison | **Deterministic Comparison Engine**: Entity extraction uses LLM/parsers, but final comparison across normalized fields MUST be deterministic code. | `[APPROVED DESIGN DECISION]` |
| **DEC-P01** | AI Subsystem | **Provider-Agnostic AI Adapter**: Core pipeline communicates via `BaseAIAdapter`. Gemini is initial adapter implementation, but no hard dependency on Gemini. | `[APPROVED WITH MODIFICATION]` |
| **DEC-P02** | Scanned Docs | **OCR / Vision Before Escalation**: Scanned and image-only documents attempt OCR/Vision first; escalate to HITL (`unreadable`) only if extraction fails or is unreliable. | `[APPROVED DESIGN DECISION]` |
| **DEC-P03** | Web Framework | **FastAPI + Uvicorn**: Standard ASGI REST API with interactive Swagger documentation. | `[APPROVED DESIGN DECISION]` |
| **DEC-P04** | Cloud Hosting | **Platform-Agnostic Deployment**: Backend remains container/platform agnostic. Render is initial deployment target, not a hard requirement. | `[DEFERRED]` |
| **DEC-P05** | Frontend Architecture | **Frontend/Backend Decoupling (SPA + REST)**: Architecture approved. Specific framework (Vanilla JS/Tailwind) and static host (GitHub Pages) deferred to `04_UI_UX_SPEC.md`. | `[APPROVED WITH MODIFICATION]` |
| **DEC-P06A**| Normalization | **Formatting Normalization**: Unicode, capitalization, whitespace, punctuation, and comma separator stripping. | `[APPROVED DESIGN DECISION]` |
| **DEC-P06B**| Normalization | **Unit Normalization**: Mathematically exact conversion (MT $\times 1000 \rightarrow$ kg). | `[APPROVED DESIGN DECISION]` |
| **DEC-P06C**| Normalization | **Port Semantic Equivalence**: Do not automatically assume city, terminal, and UN/LOCODE are equivalent without explicit canonical mapping. | `[TBD - Awaiting Mapping Spec]` |
| **DEC-P06D**| Normalization | **Organization Name Equivalence**: Do not broadly strip legal suffixes; `LTD`/`LIMITED` normalized only where explicitly defined. | `[TBD - Awaiting Alias Rules]` |
| **DEC-P06E**| Comparison | **Numeric Tolerance**: Default to exact normalized comparison; no $\pm 1\text{ kg}$ tolerance without validated business rules. | `[TBD - Awaiting Validation]` |

---

## 20. Alternatives Considered

1. **Monolithic LLM Comparison (Single Prompt)**:
   - *Option*: Send raw emails and all attachments directly to an LLM to answer whether a mismatch exists.
   - *Rejection*: Inefficient token usage, non-deterministic outputs, hallucination risk, and inability to handle binary corruption gracefully.
2. **Pure Regular Expression Pipeline**:
   - *Option*: 100% regex-based parsing without any semantic model.
   - *Rejection*: Fragile against diverse layouts, synonyms, and multi-line entity blocks.
   - *Chosen*: Hybrid architecture — LLM/parsers for extraction, deterministic rules for normalization and comparison.
3. **Relational Database (SQL)**:
   - *Option*: Storing email states and audit results in an external SQL database.
   - *Rejection*: Over-engineering for a static evaluation dataset; JSON cache files and stateless REST endpoints provide zero-maintenance simplicity.

---

## 21. Future / Advanced Roadmap `[FUTURE]`

1. **Asynchronous Webhook / IMAP Streaming**: Continuous email ingestion from live mailboxes via Celery or Redis queues.
2. **Active Learning Feedback Loop**: Operator corrections in the web dashboard automatically update alias dictionaries and prompt exemplars.
3. **Carrier Amendment Reply Drafting**: Automatically compose professional amendment emails to carriers when draft BL errors are flagged.
