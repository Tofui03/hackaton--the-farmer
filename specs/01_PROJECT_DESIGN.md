# 01_PROJECT_DESIGN.md — System Architecture & Technical Design Specification

> **Document Type**: Technical Architecture & System Design Document  
> **Implements**: [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md) / [`specs/PRODUCT_SPEC.md`](file:///d:/ship/specs/PRODUCT_SPEC.md)  
> **Methodology**: Spec-Driven Development (SDD) — Phase 2 System Design  
> **Status**: Awaiting User Review & Approval  

---

## 1. Architectural Principles & Patterns

The system is architected as a **Gated Multi-Stage Verification Pipeline with Pluggable Document Adapters and Dual Output Serializers**:

1. **Strict Separation of Concerns (SoC)**:
   - File format parsing is decoupled from document verification.
   - Email intent classification (Stage 1) is decoupled from document extraction (Stage 2) and comparison (Stage 3).
2. **First-Stage Veto Principle**:
   - Only `document_comparison` emails trigger document extraction and comparison.
   - Non-comparison emails (`new_si_request`, `invoice_query`, `general_message`, `spam`) terminate processing immediately after Stage 1, preventing unauthorized document evaluation.
3. **Golden Baseline Anchoring**:
   - The Shipping Instruction (SI) is treated as the immutable golden truth; differences in the draft Bill of Lading (BL) are flagged as defects.
4. **Resilient Offline Degradation**:
   - The system is fully operational offline via deterministic heuristics, regular expression parsers, and fuzzy semantic normalizers, while supporting seamless LLM augmentation when credentials (`GEMINI_API_KEY`) are present.
5. **Human-in-the-Loop (HITL) Transparency**:
   - When confidence cannot be achieved, the pipeline emits audit-ready structured escalations with extracted evidence rather than guessing.

---

## 2. End-to-End System Architecture

```
                                  INBOX SOURCE
                     (520 Email JSON records in inbox/)
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: EMAIL INTENT CLASSIFIER (src/pipeline/stage1_classify.py)          │
│ - Batched Gemini Prompt (25-50 emails/chunk)                                │
│ - Deterministic Keyword & Header Fallback                                   │
│ - Categorizes into: document_comparison, new_si_request, invoice_query,     │
│                     general_message, spam                                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
         [Non-Comparison Emails]               [document_comparison]
         (Terminates Immediately)                         │
                    │                                     ▼
                    │    ┌────────────────────────────────────────────────────┐
                    │    │ STAGE 2: ATTACHMENT INGESTION & TRIAGE             │
                    │    │ (src/pipeline/stage2_extract.py)                   │
                    │    │ - Validates >= 2 attachments                       │
                    │    │ - Dispatches to Pluggable Parsers:                 │
                    │    │     • TextParser (.txt)                            │
                    │    │     • DocxParser (.docx)                           │
                    │    │     • ExcelParser (.xlsx)                          │
                    │    │     • PdfParser (.pdf)                             │
                    │    │     • DocumentAIAdapter (GCP DocAI)                │
                    │    │ - Evaluates stream corruption & scanned images     │
                    │    └─────────────────────┬──────────────────────────────┘
                    │                          │
                    │        ┌─────────────────┴─────────────────┐
                    │        ▼                                   ▼
                    │  [Triage Issue]                    [Clean Doc Pair]
                    │  (missing_attachment,                      │
                    │   unreadable, etc.)                        ▼
                    │        │         ┌──────────────────────────────────────┐
                    │        │         │ STAGE 3: SEMANTIC COMPARATOR         │
                    │        │         │ (src/pipeline/stage3_compare.py)     │
                    │        │         │ - Field alias normalization          │
                    │        │         │ - Metric weight conversion (MT->kg)  │
                    │        │         │ - Container count digit parsing      │
                    │        │         │ - Corporate entity suffix tolerance  │
                    │        │         │ - Gemini LLM Verification Prompt     │
                    │        │         └──────────────────┬───────────────────┘
                    │        │                            │
                    ▼        ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ DUAL OUTPUT SERIALIZER & CHECKPOINT CACHE (src/pipeline/schema.py)          │
│ - audit_report.json (Strict Output Contract Schema)                         │
│ - submission.json (Official Competition Schema)                             │
│ - .cache_pipeline.json (Interrupt & Resume Checkpoint Manager)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        RENDER WEB SERVICE (API)               GITHUB PAGES (DASHBOARD)
      - Framework: FastAPI (app.py)          - Path: docs/index.html
      - Entry: main:app                      - Automated GitHub Actions
      - Ports: $PORT / 0.0.0.0               - Zero-server client inspector
```

---

## 3. Subsystem Detailed Designs

### 3.1 Document Parsing Subsystem (`src/parsers/`)
- **`BaseParser`**: Abstract interface enforcing `parse(file_path: Path) -> DocumentParseResult`.
- **`DocumentParseResult`**: Unified container holding `text`, `success`, `is_corrupted`, `is_scanned`, `error_message`, and `metadata`.
- **`PdfParser`**:
  - Catches `PdfStreamError` and `PdfReadError` (e.g. truncated streams without EOF marker like `email_511_BL.pdf` and `email_515_BL.pdf`) and flags `is_corrupted: true`.
  - Measures extracted text density; if $\text{length} < 20\text{ chars}$, flags `is_scanned: true`.
- **`TextParser`**: Automatically detects encoding through UTF-8, Latin-1, and CP1252 fallbacks.
- **`DocxParser`**: Extracts text from both paragraph runs and multi-column document tables using `python-docx`.
- **`ExcelParser`**: Reads cell values across all sheets in `.xlsx` workbooks using `openpyxl`.
- **`DocumentAIAdapter`**: Pluggable cloud adapter that activates if `GOOGLE_APPLICATION_CREDENTIALS` and `DOCAI_PROCESSOR_ID` are present.

### 3.2 Email Classification Subsystem (`src/pipeline/stage1_classify.py`)
- **Batching Engine**: Assembles email headers, sender, attachment counts, and body previews into batches of 25–50 items.
- **Gemini System Prompt**: Constrains categorization strictly to the 5 valid target strings.
- **Deterministic Heuristic Engine**:
  - Checks for spam marketing signatures.
  - Checks for attachment presence and draft BL checking keywords (`BL_COMPARISON`).
  - Checks subject priority keywords for SI requests vs Invoice queries.
  - Defaults unassigned messages to `GENERAL`.

### 3.3 Semantic Normalization & Comparison Subsystem (`src/pipeline/stage3_compare.py`)
- **Field Alias Dictionary (`FIELD_ALIASES`)**:
  - POL: `Port of Loading`, `Load Port`, `POL`, `Loading Port`, `Port of Load`
  - POD: `Port of Discharge`, `Discharge Port`, `POD`, `Discharging Port`, `Destination Port`
  - Weight: `Gross Weight`, `Total Weight`, `G.W.`, `Cargo Weight`, `Gross Wt`, `Weight (KG)`
  - Containers: `Container Count`, `Total Containers`, `Qty of Units`, `No. of Containers`, `Number of Containers`
- **Unit Normalization (`normalize_gross_weight_kg`)**:
  - Regex detects Metric Tons (`MT`, `METRIC TONS`) and multiplies numerical value by 1000.
  - Strips commas, trailing whitespace, and units (`KG`).
  - Enforces numeric tolerance $\le 1.0\text{ kg}$.
- **Container Extraction (`normalize_container_count`)**:
  - Extracts parenthetical digits (`"Three (3) Containers"` $\rightarrow 3$).
  - Maps spelled-out numeric words (`"Three Containers"` $\rightarrow 3$).
  - Extracts unit multipliers (`"6 x 20'GP"` $\rightarrow 6$).
- **Entity Matching (`normalize_text_entity`)**:
  - Strips legal entity suffixes (`SDN BHD`, `LTD`, `LIMITED`, `LLC`, `INC`, `CORP`, `GMBH`, `PTE LTD`).
  - Normalizes whitespace and removes punctuation.

### 3.4 Delivery & Web Service Subsystem (`app.py`, `main.py`)
- **ASGI Entrypoint (`main.py`)**: Exports `app` to satisfy standard ASGI loaders (`uvicorn main:app`).
- **Dynamic Port Binding**: Detects `PORT` environment variable (Render standard: 10000) and binds to `0.0.0.0`.
- **CORS Middleware**: Allows cross-origin requests (`*`) to permit the GitHub Pages frontend to query the Render API.
- **REST Endpoints**:
  - `GET /health`: Health probe.
  - `GET /audit`: Returns all 520 records in Strict Output Contract JSON.
  - `GET /audit/{email_id}`: Returns a single audit record.
  - `POST /verify`: Real-time audit endpoint accepting custom SI and draft BL text.
  - `GET /submission`: Returns official competition `submission.json`.
  - `GET /docs`: Interactive OpenAPI / Swagger UI.

---

## 4. Requirements Traceability Matrix

| Requirement ID | Requirement Summary | Architectural Component | Implementation File |
|---|---|---|---|
| **FR-001** | Ingest inbox JSON records | Email Loader | [`src/run_pipeline.py`](file:///d:/ship/src/run_pipeline.py) |
| **FR-002** | Categorize every email | Stage 1 Classifier | [`src/pipeline/stage1_classify.py`](file:///d:/ship/src/pipeline/stage1_classify.py) |
| **FR-003** | Compare only document-comparison | Pipeline Controller | [`src/run_pipeline.py`](file:///d:/ship/src/run_pipeline.py) |
| **FR-004** | Early termination for non-comparison | Pipeline Controller | [`src/run_pipeline.py`](file:///d:/ship/src/run_pipeline.py) |
| **FR-005** | Plain text parsing (`.txt`) | TextParser | [`src/parsers/text_parser.py`](file:///d:/ship/src/parsers/text_parser.py) |
| **FR-006** | Advanced formats (`.docx`, `.xlsx`, `.pdf`) | Multi-format Parsers | [`src/parsers/`](file:///d:/ship/src/parsers/) |
| **FR-007** | Table and paragraph extraction | Docx & Excel Parsers | [`src/parsers/docx_parser.py`](file:///d:/ship/src/parsers/docx_parser.py), [`excel_parser.py`](file:///d:/ship/src/parsers/excel_parser.py) |
| **FR-008** | Scanned document OCR support | PdfParser & DocAI Adapter | [`src/parsers/pdf_parser.py`](file:///d:/ship/src/parsers/pdf_parser.py), [`docai_adapter.py`](file:///d:/ship/src/parsers/docai_adapter.py) |
| **FR-009** | SI as golden reference | Stage 3 Comparator | [`src/pipeline/stage3_compare.py`](file:///d:/ship/src/pipeline/stage3_compare.py) |
| **FR-010** | 7 mandatory comparison fields | Stage 3 Comparator | [`src/pipeline/stage3_compare.py`](file:///d:/ship/src/pipeline/stage3_compare.py) |
| **FR-011** | Output "No mismatch detected" | Stage 3 Comparator | [`src/pipeline/stage3_compare.py`](file:///d:/ship/src/pipeline/stage3_compare.py) |
| **FR-012** | Side-by-side discrepancy output | Stage 3 Comparator | [`src/pipeline/stage3_compare.py`](file:///d:/ship/src/pipeline/stage3_compare.py) |
| **FR-013** | HITL escalation for uncertainty | Stage 2 & 3 Triage | [`src/pipeline/stage2_extract.py`](file:///d:/ship/src/pipeline/stage2_extract.py), [`stage3_compare.py`](file:///d:/ship/src/pipeline/stage3_compare.py) |
| **FR-014** | Missing / corrupt / scan triage | Stage 2 Extractor | [`src/pipeline/stage2_extract.py`](file:///d:/ship/src/pipeline/stage2_extract.py) |
| **FR-015** | Escalation reason & source evidence | Stage 2 & 3 Triage | [`src/pipeline/schema.py`](file:///d:/ship/src/pipeline/schema.py) |
| **NFR-001** | Deterministic repeatability | Pipeline Runner & Cache | [`src/cache.py`](file:///d:/ship/src/cache.py), [`run_pipeline.py`](file:///d:/ship/src/run_pipeline.py) |
| **NFR-003** | Corrupt stream fault tolerance | PdfParser | [`src/parsers/pdf_parser.py`](file:///d:/ship/src/parsers/pdf_parser.py) |
| **NFR-005** | Schema compliance | Submission Validator | [`src/pipeline/validator.py`](file:///d:/ship/src/pipeline/validator.py) |
