# Shipping Document Verification System

An AI-assisted shipping document verification and discrepancy audit engine that classifies incoming operational emails, extracts and normalizes Shipping Instructions (SI) and Draft Bills of Lading (BL), performs deterministic 7-field cross-comparisons, and escalates ambiguous cases for Human-in-the-Loop (HITL) review.

The system uses a **hybrid AI + deterministic architecture**:

- **AI on Demand**: Used exclusively for semantic interpretation (unstructured email intent classification, complex table extraction, and image-only scanned document OCR).
- **Deterministic Comparator**: Normalization, mathematical unit conversion, and field-by-field comparisons execute strictly through deterministic code. The language model **never** decides whether two shipment values match.
- **Human-in-the-Loop (HITL)**: Missing, unreadable, conflicting, or uncertain values trigger actionable review cases with verbatim source provenance instead of fabricating guesses.
- **Partial Work Preservation**: Reliable fields are permanently preserved during escalations so operators only verify the specific problematic items.

---

## Live Demo

- **Frontend Web Console**: [https://hackaton-the-farmer-1.onrender.com/](https://hackaton-the-farmer-1.onrender.com/)
- **Backend REST API**: [https://hackaton-the-farmer.onrender.com](https://hackaton-the-farmer.onrender.com)
- **Interactive Swagger Documentation**: [https://hackaton-the-farmer.onrender.com/docs](https://hackaton-the-farmer.onrender.com/docs)

---

## Problem & Solution

Shipping operations teams handle hundreds of inbound booking emails daily containing Shipping Instructions and draft Bills of Lading that require meticulous cross-checking. Manual verification is error-prone and time-consuming because:

1. Emails span multiple operational intents (booking checks, invoice queries, new SI submissions, general updates, spam).
2. Documents arrive in disparate formats (`.txt`, `.docx`, `.pdf`, `.xlsx`, scanned images).
3. Field formatting differs widely (e.g., metric tons vs. kilograms, multiline address blocks, alternative labels).
4. Subtle discrepancies (e.g., container count mismatch: 3 vs. 4) lead to costly customs penalties or cargo re-routing if overlooked.
5. Traditional automated systems either hallucinate matches using generative AI or fail entirely on minor OCR noise.

This platform automates repetitive ingestion, role binding, and deterministic validation while providing operations reviewers with a transparent, evidence-grounded review console.

---

## End-to-End Workflow

```text
                     Incoming Inbound Email
                               |
                               v
               [Stage 1: Intent Classification]
                               |
            +------------------+------------------+
            |                                     |
   (Non-Comparison Category)             (document_comparison)
            |                                     |
            v                                     v
  [Complete: NOT_APPLICABLE]           [Stage 2: Role Binding]
  (INVOICE_QUERY / SPAM / etc.)         (Identify SI vs. Draft BL)
                                                  |
                                                  v
                                       [Document Parsing & OCR]
                                       (TXT / DOCX / PDF / XLSX)
                                                  |
                                                  v
                                       [Stage 3: Field Extraction]
                                       (Extract 7 Mandatory Fields)
                                                  |
                                                  v
                                       [Canonical Normalization]
                                       (NFKC, Spacing, MT -> kg)
                                                  |
                                                  v
                                       [Stage 4: Deterministic Comparator]
                                                  |
                      +---------------------------+---------------------------+
                      |                                                       |
              (All 7 Fields Match)                                   (Discrepancies Detected)
                      |                                                       |
                      v                                                       v
               COMPLETE: MATCH                                       COMPLETE: MISMATCH
          ("No mismatch detected")                               (Rose diff row in UI matrix)
                      |                                                       |
                      +---------------------------+---------------------------+
                                                  |
                                       (Uncertain / Unreadable)
                                                  |
                                                  v
                                             NEEDS_REVIEW
                                      [Human Review Workspace]
                                                  |
                                                  v
                                         Operator Correction
                                      (Targeted Field / Role)
                                                  |
                                                  v
                                       Deterministic Recomputation
                                        (Revision N -> Rev N+1)
```

---

## The 7 Mandatory Comparison Fields

The core comparison engine verifies exactly and only the 7 mandatory shipment attributes:

| Field Name | Type | Normalization & Validation Standard |
| :--- | :--- | :--- |
| `shipper` | String | Unicode NFKC, uppercase, whitespace collapsed, trailing punctuation trimmed. |
| `consignee` | String | Multiline corporate address blocks preserved with full line-span evidence. |
| `notify_party` | String | Resolved against consignee references (`"SAME AS CONSIGNEE"`). |
| `port_of_loading` | String | Normalized port name with UN/LOCODE identifier preserved. |
| `port_of_discharge` | String | Normalized destination port name with UN/LOCODE identifier preserved. |
| `container_count` | Integer | Word conversion (`"Three (3)"` $\rightarrow$ `3`), multi-size manifest summation. |
| `gross_weight_kg` | Decimal | Exact mathematical conversion (`22 MT` $\rightarrow$ `Decimal("22000")`), no binary float drift. |

---

## Key Architectural Highlights

### 1. Tri-State Safety Model
Comparisons evaluate strictly to:
- `MATCH`: All 7 mandatory fields extracted reliably and match 100%.
- `MISMATCH`: All 7 fields extracted reliably, with 1 or more deterministic discrepancies isolated.
- `UNRESOLVED` (`null`): If any mandatory field is missing, unreadable, or conflicting, `mismatch_detected` remains `null`. The system **never** emits a false clean match on incomplete data.

### 2. Evidence Grounding & Provenance
Every extracted entity maintains a strict `FieldEvidence` reference containing:
- Exact verbatim text quote.
- Page number / table coordinate metadata.
- Parent source document ID.
Self-reported AI confidence scores are treated as diagnostic only and can **never** bypass evidence validation.

### 3. Concurrency-Safe Human Review
Reviewers submit corrections via `POST /audit/{id}/review` protected by optimistic revision locking (`expected_revision`). If a concurrent operator modifies the record first, the server returns HTTP 409 Conflict, preserving the local reviewer's unsubmitted inputs.

### 4. Safe Export Gate (`EXPORT_BLOCKED`)
Evaluation submission generation (`GET /submission`) enforces Safety Invariant DC-08. If any batch record remains in `NEEDS_REVIEW`, export is blocked with HTTP 409, detailing the blocking email IDs and direct resolution links.

---

## Technology Stack

- **Backend Framework**: Python 3.12, [FastAPI](https://fastapi.tiangolo.com/), [Pydantic v2](https://docs.pydantic.dev/) (strict contract schemas)
- **Document Parsers**: `pypdf` (Vector PDF), `python-docx` (Word tables), `openpyxl` (Excel), standard UTF-8 text parser
- **AI & Vision Adapter**: Google GenAI / Gemini API adapter with bounded exponential backoff retries and structured output schemas
- **Frontend Console**: React 18, TypeScript 5.7, Vite, Tailwind CSS, Lucide / Heroicons
- **Testing & Verification**: Pytest (246 test suite), Vitest, React Testing Library

---

## API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service status and dynamic audit store summary metrics. |
| `GET` | `/health` | Application health and readiness check. |
| `GET` | `/audit` | Query audit queue summaries with filtering (`state`, `outcome`, `category`). |
| `GET` | `/audit/{email_id}` | Retrieve full audit report including documents, comparisons, evidence, and review lineage. |
| `POST` | `/audit/{email_id}/review` | Submit targeted human review correction with optimistic concurrency locking. |
| `GET` | `/submission` | Export official evaluation submission JSON (blocks with HTTP 409 if cases remain unresolved). |
| `POST` | `/verify` | On-demand SI and Draft BL verification payload. |

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ & npm

### 2. Backend Setup
```bash
# Clone repository
git clone https://github.com/tofui03/ship.git
cd ship

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Enable demo seed records for live local UI walkthrough
# export SDOC_UAT_DEMO_SEED=1  # On Windows: $env:SDOC_UAT_DEMO_SEED="1"

# Run FastAPI backend
uvicorn app:app --reload --port 10000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run Vite development server (proxies API calls to localhost:10000)
npm run dev
```

The frontend console will be live at `http://localhost:5173`.

---

## Verification & Quality Assurance

The codebase is governed by a comprehensive verification test suite enforcing contract integrity, negative regression guards, and end-to-end lifecycle flows.

```bash
# 1. Run complete Pytest suite (246 tests)
python -m pytest tests -v

# 2. Run AI and Review fixture governance validators
python tests/fixtures/validate_ai_fixtures.py
python tests/fixtures/validate_review_fixtures.py

# 3. Run Frontend unit and component tests
npm --prefix frontend run test

# 4. Compile Frontend production build
npm --prefix frontend run build

# 5. Verify OpenAPI and TypeScript contract synchronization
python scripts/verify_contracts.py

# 6. Run single-command deadline verification harness
powershell -ExecutionPolicy Bypass -File .\scripts\verify_deadline.ps1
```

---

## Project Structure

```text
├── app.py                     # FastAPI application entrypoint & SPA static mount
├── src/
│   ├── adapters/              # Evaluation submission schema adapter
│   ├── api/                   # REST routes, dependencies & timing middleware
│   ├── comparator/            # Deterministic 7-field comparison engine
│   ├── demo/                  # Environment-gated synthetic UAT demo seed
│   ├── hitl/                  # Escalation engine & human review mutation service
│   ├── llm/                   # Provider-agnostic AI adapters, retries & schemas
│   ├── models/                # Strict Pydantic v2 data contracts
│   ├── normalization/         # Unicode, text, and gross weight unit normalizers
│   ├── parsers/               # TXT, DOCX, PDF, XLSX parsers & usability validator
│   ├── pipeline/              # Ingestion, Stage 1-4 orchestration
│   └── store/                 # Thread-safe in-memory AuditStore
├── frontend/                  # React + TypeScript single-page application
│   ├── src/components/        # 4-Column Matrix, OutcomeBadge, EvidenceDrawer, Modals
│   └── src/views/             # CaseQueueView, ReviewWorkspaceView
├── specs/                     # Baselined product, architecture & test specifications
├── docs/                      # Compiled frontend assets & UAT reports
└── tests/                     # 246 unit, contract, regression, security & E2E tests
```

---

## License

This project was built for the SDOC Hackathon.
