# Pre-Change Baseline Status Checkpoint (2026-09-22)

> **Task ID**: `T00-01` — Pre-Change Baseline Checkpoint & Repository Status Capture  
> **Status**: COMPLETED  
> **Authority**: [`AGENTS.md`](../AGENTS.md), [`specs/06_TASKS.md`](../specs/06_TASKS.md) §5  
> **Execution Date**: 2026-09-22  
> **Governance Invariant**: Zero production code modified; zero existing tests modified; zero evaluation data modified.

---

## 1. Git Repository State

- **Active Branch**: `main`
- **Pre-Change HEAD Commit**: `6e75222fe7815e833fce9bf6bba704847519fbbd` (`Approve and synchronize PRODUCT_SPEC.md and 01_PROJECT_DESIGN.md architecture`)
- **Parent Commit**: `2d9b3a9` (`Establish Spec-Driven Governance Framework: AGENTS.md and specs suite (00 to 06)`)
- **Working Tree State**:
  - The working tree contains approved, baselined specifications (00 through 06) and supporting specification schemas/amendments.
  - Zero modifications exist in `src/` (production code) or `tests/` (test suite).
  - Modified files in working tree:
    - `specs/00_PRODUCT_SPEC.md`
    - `specs/01_PROJECT_DESIGN.md`
    - `specs/02_AI_PIPELINE_SPEC.md`
    - `specs/03_DATA_CONTRACTS.md`
    - `specs/04_UI_UX_SPEC.md`
    - `specs/05_TEST_PLAN.md`
    - `specs/06_TASKS.md`
    - `specs/PRODUCT_SPEC.md`
  - Untracked files in working tree:
    - `specs/03_DATA_CONTRACTS_EXAMPLES.json`
    - `specs/03_DATA_CONTRACTS_GENERATION_PROMPT.md`
    - `specs/AMENDMENT_2026-09-22.md`
    - `specs/PROJECT_DESIGN.md`

---

## 2. Approved Specification Baseline Revisions

All project specifications are verified as `APPROVED / BASELINED` prior to commencing implementation:

| Specification Document | Approved Status | Baselined Revision |
|---|---|---|
| [`specs/00_PRODUCT_SPEC.md`](../specs/00_PRODUCT_SPEC.md) | `APPROVED / BASELINED` | Rev 3.1 (2026-09-22) |
| [`specs/01_PROJECT_DESIGN.md`](../specs/01_PROJECT_DESIGN.md) | `APPROVED / BASELINED` | Rev 3.0 (2026-09-22) |
| [`specs/02_AI_PIPELINE_SPEC.md`](../specs/02_AI_PIPELINE_SPEC.md) | `APPROVED / BASELINED` | Rev 3.1 (2026-09-22) |
| [`specs/03_DATA_CONTRACTS.md`](../specs/03_DATA_CONTRACTS.md) | `APPROVED / BASELINED` | Rev 2.0-baselined (2026-09-22) |
| [`specs/04_UI_UX_SPEC.md`](../specs/04_UI_UX_SPEC.md) | `APPROVED / BASELINED` | Rev 2.0-baselined (2026-09-22) |
| [`specs/05_TEST_PLAN.md`](../specs/05_TEST_PLAN.md) | `APPROVED / BASELINED` | Rev 2.0-baselined (2026-09-22) |
| [`specs/06_TASKS.md`](../specs/06_TASKS.md) | `APPROVED / BASELINED` | Rev 1.0 (2026-09-22) |

---

## 3. Runtime & Dependency Baseline

- **Python Runtime**: `Python 3.12.10` (`win32`)
- **Key Project Dependencies**:
  - `fastapi`: `0.141.1`
  - `pydantic`: `2.13.5` (Core `2.46.5`)
  - `starlette`: `1.6.0`
  - `uvicorn`: `0.53.0`
  - `httpx`: `0.28.1`
  - `pypdf`: `6.16.1`
  - `python-docx`: `1.2.0`
  - `openpyxl`: `3.1.5`
  - `google-genai`: `2.24.0`
  - `google-auth`: `2.58.0`
  - `pytest`: `9.1.1` (Pluggy `1.6.0`)
  - `anyio`: `4.15.1`

---

## 4. Legacy Test Suite Verification

- **Command**: `python -m pytest tests -v`
- **Collected**: 16 test items
- **Passed**: 16 / 16 (100% Pass)
- **Failed**: 0
- **Execution Time**: ~0.77s – 0.89s

### Detailed Test Execution Log:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\ship
plugins: anyio-4.15.1
collected 16 items

tests/test_api.py::test_root_endpoint PASSED                             [  6%]
tests/test_api.py::test_health_endpoint PASSED                           [ 12%]
tests/test_api.py::test_get_single_audit_ok PASSED                       [ 18%]
tests/test_api.py::test_get_single_audit_mismatch PASSED                 [ 25%]
tests/test_api.py::test_dynamic_verify_endpoint PASSED                   [ 31%]
tests/test_parsers.py::test_text_parser PASSED                           [ 37%]
tests/test_parsers.py::test_excel_parser PASSED                          [ 43%]
tests/test_parsers.py::test_docx_parser PASSED                           [ 50%]
tests/test_parsers.py::test_pdf_parser_valid PASSED                      [ 56%]
tests/test_parsers.py::test_pdf_parser_corrupted PASSED                  [ 62%]
tests/test_pipeline.py::test_classification_heuristics PASSED            [ 68%]
tests/test_pipeline.py::test_stage2_missing_attachment PASSED            [ 75%]
tests/test_pipeline.py::test_stage2_corrupted_pdf PASSED                 [ 81%]
tests/test_pipeline.py::test_stage3_matching_pair PASSED                 [ 87%]
tests/test_pipeline.py::test_stage3_discrepancy_pair PASSED              [ 93%]
tests/test_pipeline.py::test_validator PASSED                            [100%]

======================= 16 passed, 2 warnings in 0.77s ========================
```

### SHA256 Hashes of Test Suite Files:
```text
tests/test_api.py:      e5517dca3979c981ca611daed26a7db50b9eed2792856ffd48a1236c1ffd0478 (2,098 bytes)
tests/test_parsers.py:  9b934301c063dc8521088c90afb9541d1117f5c7be4c791df05a5e58eccd5699 (1,609 bytes)
tests/test_pipeline.py: 7781c9e80907ec508d4013dbe97de9b645a5a4a6b2b77ada4ef093cad0f422c1 (3,398 bytes)
```

---

## 5. Evaluation Dataset Inventory & Immutability Baseline

- **Directory**: `sdoc-hackathon-bundle/`
- **Inbox Email Count**: 520 JSON files (`sdoc-hackathon-bundle/inbox/**/*.json`)
- **Attachment Count**: 250 document files (`sdoc-hackathon-bundle/attachments/**/*`)
- **Immutability Invariant**: Per [`AGENTS.md`](../AGENTS.md) §5 and §9, zero files within `sdoc-hackathon-bundle/` may be altered, moved, or deleted.

---

## 6. Component Inventory & Existing Entry Points

| Component Layer | File Path | Existing Disposition | Description |
|---|---|---|---|
| **ASGI Web Server** | `main.py` | ADAPT | Uvicorn launch script (`uvicorn.run(app)`) supporting `PORT` env var. |
| **FastAPI App** | `app.py` | ADAPT | FastAPI instance defining `/`, `/health`, `/audit`, `/audit/{id}`, `/submission`, `/verify`. |
| **Pipeline Runner** | `src/run_pipeline.py` | ADAPT | CLI script running legacy pipeline on `sdoc-hackathon-bundle/inbox/`. |
| **Data Schema** | `src/pipeline/schema.py` | REPLACE | Legacy Pydantic schema using competition category strings and unvalidated structures. |
| **Intent Classifier** | `src/pipeline/stage1_classify.py` | ADAPT | Stage 1 classification heuristics. Contains `len(attachments) >= 1` filter to be removed. |
| **Extractor / Roles** | `src/pipeline/stage2_extract.py` | ADAPT | Attachment parsing & role detection. Lacks deterministic 2-document binding & 7 HITL reasons. |
| **Comparator** | `src/pipeline/stage3_compare.py` | REPLACE | Heuristic field comparison. To be replaced with pure deterministic 7-field comparator. |
| **Submission Validator** | `src/pipeline/validator.py` | ADAPT | Validation logic for competition export. To be adapted into Evaluation Adapter. |
| **Base Parser** | `src/parsers/base.py` | ADAPT | Abstract class defining `BaseParser.parse()`. To return `ParserResult` model. |
| **Text Parser** | `src/parsers/text_parser.py` | ADAPT | Plain text regex parser. |
| **DOCX Parser** | `src/parsers/docx_parser.py` | ADAPT | `python-docx` parser. Table cell coordinates to be upgraded. |
| **PDF Parser** | `src/parsers/pdf_parser.py` | ADAPT | `pypdf` stream parser. To bind to Usability Engine. |
| **Excel Parser** | `src/parsers/excel_parser.py` | ADAPT | `openpyxl` spreadsheet parser. |
| **OCR / DocAI** | `src/parsers/docai_adapter.py` | ADAPT | Cloud OCR stub. To be wrapped under provider-agnostic OCR fallback. |
| **LLM Client** | `src/llm/client.py` | ADAPT | `genai.Client` wrapper. To implement `BaseAIAdapter`. |
| **LLM Prompts** | `src/llm/prompts.py` | ADAPT | Prompt templates. To be aligned to strict Pydantic JSON schemas. |
| **Visual Prototype** | `docs/index.html` | PRESERVE | Single-page UI prototype (14,579 bytes). Preserved as visual reference artifact. |

---

## 7. Open Domain TBD Safeguard Baseline

Three domain comparison rules remain explicit human-governed TBDs:
1. `DEC-P06C` (Port Semantic Equivalence): Current baseline requires exact string equality after approved normalization (trim and uppercase).
2. `DEC-P06D` (Organization Name Equivalence): Current baseline requires exact equality after currently approved normalization without broad suffix stripping.
3. `DEC-P06E` (Gross Weight Tolerance): Current baseline requires exact Decimal equality without numeric tolerance.

*Governance Invariant*: Implementation tasks enforce strict baseline behavior and **MUST NOT** resolve these TBDs autonomously. Planned regression/CI guards will block unapproved relaxation once the corresponding implementation tasks are completed.
