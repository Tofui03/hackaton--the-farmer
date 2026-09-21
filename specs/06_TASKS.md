# 06_TASKS.md — Active Execution Plan & Task Queue

> **Status**: In Progress  
> **Governed by**: [`AGENTS.md`](file:///d:/ship/AGENTS.md)

---

## 1. Completed Tasks (DoD Satisfied)

- [x] **TASK-01: Document Ingestion & Pluggable Parsers**
  - Implemented `TextParser`, `DocxParser`, `ExcelParser`, `PdfParser`, and `DocumentAIAdapter`.
  - Added proactive corruption detection (`PdfStreamError` $\rightarrow$ `is_corrupted: true`).
  - *Verification*: `tests/test_parsers.py` (5/5 tests passing).

- [x] **TASK-02: High-Score Strategies Normalization Engine**
  - Implemented `FIELD_ALIASES` (POL, POD, Gross Weight, Container Count).
  - Implemented unit conversion (MT $\times 1000 \rightarrow$ kg, comma stripping).
  - Implemented spelled-out number extraction ("Three (3)" $\rightarrow$ 3).
  - Implemented corporate entity tolerance (SDN BHD, LTD, LLC $\rightarrow$ Match).
  - *Verification*: `tests/test_pipeline.py` (matching pair and discrepancy pair verified).

- [x] **TASK-03: Classification Veto & HITL Escalation**
  - Implemented Stage 1 categorization and non-comparison early veto (Secret 4).
  - Implemented Stage 2 missing attachment & corrupt file triage (Secret 3).
  - Generated structured HITL records with `evidence` snippets.
  - *Verification*: `tests/test_pipeline.py` (`email_507`, `email_511` verified).

- [x] **TASK-04: Dual Export & Schema Compliance**
  - Generates `submission.json` (100% compliant with `sample_submission.json`).
  - Generates `audit_report.json` (Strict Output Contract).
  - *Verification*: `tests/test_pipeline.py::test_validator` passed on 520 records.

- [x] **TASK-05: FastAPI Web Service & Render Configuration**
  - Created `app.py` and `main.py` entrypoint.
  - Implemented endpoints: `/health`, `/audit`, `/audit/{email_id}`, `/verify`, `/submission`.
  - Configured `render.yaml` (`env: python`, `plan: free`), `Procfile`, and `.python-version` (`3.12.8`).
  - *Verification*: `tests/test_api.py` (5/5 tests passing).

- [x] **TASK-06: GitHub Pages Dashboard & Automated CI/CD**
  - Built interactive single-page dashboard at `docs/index.html`.
  - Created `.github/workflows/pages.yml` for automated GitHub Pages deployment on push.

- [x] **TASK-07: Governance Framework Setup**
  - Established `AGENTS.md` and complete `specs/` hierarchy (`00_PRODUCT_SPEC.md` to `06_TASKS.md`).

---

## 2. Active / Next Tasks

- [ ] **TASK-08: Render Live Verification**
  - Verify live status on Render dashboard once latest commit deploys.
  - Test `/health` and `/audit/email_001` on public Render domain.

- [ ] **TASK-09: Production Gemini API Key Live Run**
  - When `GEMINI_API_KEY` is provided, execute full live multimodal LLM comparison run and benchmark against local heuristic baseline.
