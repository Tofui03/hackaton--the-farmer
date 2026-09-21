# 06_TASKS.md — Implementation Execution Plan

> **Status**: APPROVED / BASELINED  
> **Revision**: 1.0 (2026-09-22)  
> **Authority**: Original Use Case → [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) → [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) → [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) → [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) → [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) → [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md)  
> **Scope**: Ordered, dependency-aware engineering work breakdown covering data models, normalizers, parsers, AI adapters, pipeline stages, HITL engine, REST endpoints, Evaluation Adapter, React frontend, and regression/E2E test suites.  
> **Governance Constraint**: Strictly follow [`AGENTS.md`](../AGENTS.md). The AI acts strictly as an **Implementation Agent**. No production code (`src/`), existing tests (`tests/`), or baselined specifications (`00`–`05`) are modified during the creation of this plan.

---

## 1. Execution Principles & Task Governance

1. **Strict Traceability**: Every task links directly:
   $$\text{Baseline Requirement/Decision} \longrightarrow \text{Test Plan Test ID(s)} \longrightarrow \text{Current Code Gap} \longrightarrow \text{Implementation Task} \longrightarrow \text{Acceptance Evidence}$$
2. **Vertical, Testable Increments**: Monolithic rewrites are forbidden. Each task introduces an isolated schema, function, boundary, or endpoint with immediate test assertions, leaving the repository in a verified, passing state.
3. **Test-First / Test-Alongside**: For every implementation task, write or activate the corresponding synthetic test fixture and assertion, observe failure on unmigrated code, implement the change, verify pass, and confirm zero regression.
4. **Data Integrity & Immutability**: No task may alter or overwrite evaluation data in `sdoc-hackathon-bundle/`. All test suites must execute against isolated synthetic fixtures in `tests/fixtures/`.
5. **Business TBD Guardrail**: Domain business rules `DEC-P06C` (port alias equivalence), `DEC-P06D` (legal entity suffix stripping), and `DEC-P06E` (numeric weight tolerance) remain open TBDs under human governance. Tasks must enforce strict baseline behavior (exact match after approved normalization) and **MUST NOT** resolve these TBDs autonomously. If a task requires resolving an open TBD, it must be set to `BLOCKED`. Planned regression/CI guards will block unapproved relaxation once the corresponding implementation tasks are completed.
6. **Task Status Lifecycle**: Tasks transition through `NOT_STARTED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `DONE` (or `BLOCKED` / `DEFERRED`). A task is marked `DONE` **ONLY** when implementation meets specification 100%, referenced tests pass, regression suite passes, and documentation is updated.

---

## 2. Legacy Migration Strategy

Existing implementation code in `src/` and `app.py` is evidence of current operational state, **NOT** the source of truth. Components are classified into four migration categories:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   LEGACY CODE MIGRATION MATRIX                                   │
├──────────────────────────┬──────────────┬────────────────────────────────────────────────────────┤
│ Component / File         │ Disposition  │ Migration Rationale & Safety Boundary                  │
├──────────────────────────┼──────────────┼────────────────────────────────────────────────────────┤
│ src/parsers/text_parser  │ ADAPT        │ Retain regex/UTF-8 reader; adapt to BaseParser/Model. │
│ src/parsers/docx_parser  │ ADAPT        │ Retain python-docx reader; upgrade table/cell coord.   │
│ src/parsers/pdf_parser   │ ADAPT        │ Retain pypdf stream check; adapt to Usability Engine.  │
│ src/parsers/excel_parser │ ADAPT        │ Retain openpyxl reader; adapt to cell metadata models. │
│ src/parsers/docai_adapter│ ADAPT        │ Decouple cloud calls; wrap under OCR fallback adapter. │
│ src/parsers/base.py      │ ADAPT        │ Retain/refine BaseParser interface; require ParserResult Pydantic model return; separate behavior from data. │
│ src/parsers/__init__.py  │ ADAPT        │ Remove 'len > 20' fixed rule; bind Usability Engine.   │
│ src/llm/client.py        │ ADAPT        │ Wrap inside GeminiAdapter implementing BaseAIAdapter.  │
│ src/llm/prompts.py       │ ADAPT        │ Align prompts to strict Pydantic JSON schema outputs.  │
│ src/pipeline/schema.py   │ REPLACE      │ Replace legacy schema with baselined Data Contracts.   │
│ src/pipeline/stage1      │ ADAPT        │ Remove competition strings & 0-att filter; use models. │
│ src/pipeline/stage2      │ ADAPT        │ Add deterministic role binding; 7 HITL reasons.        │
│ src/pipeline/stage3      │ REPLACE      │ Replace heuristic compare with pure deterministic diff.│
│ src/pipeline/validator   │ ADAPT        │ Move and adapt into dedicated Evaluation Adapter.      │
│ src/run_pipeline.py      │ ADAPT        │ Adapt orchestrator to AuditRecord store & contracts.   │
│ app.py                   │ ADAPT        │ Retain routes; migrate response models to AuditRecord. │
│ POST /verify (in app.py) │ REMOVE LATER │ Retain temporarily for legacy tests; deprecate in T12. │
│ docs/index.html          │ ADAPT/PRESERVE | Preserve as visual reference (docs/reference/ui_prototype.html); build React SPA as production serving route. │
└──────────────────────────┴──────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. High-Level Task Dependency Graph

```mermaid
flowchart TD
    subgraph Wave 0: Safety & Fixtures
        T00[T00: Baseline Capture & Repo Safety] --> T01[T01: Synthetic Test Fixtures]
    end

    subgraph Wave 1: Contracts & Deterministic Core
        T01 --> T02[T02: Pydantic Data Contract Foundation]
        T02 --> T03[T03: Deterministic Normalization Foundation]
        T03 --> T04[T04: Deterministic 7-Field Comparator]
    end

    subgraph Wave 2: Parsers, AI & Pipeline Stages
        T02 --> T07[T07: Provider-Agnostic AI Adapter]
        T07 --> T08[T08: Stage 1 Email Intent Classifier]
        T08 --> T09[T09: Stage 2 Document Role Binding]
        T02 --> T05[T05: Pluggable Parsers & Usability Engine]
        T05 --> T06[T06: OCR / Vision Recovery Adapter]
        T05 & T06 & T07 & T09 --> T10[T10: Stage 3 Seven-Field Extraction & Reliability Gate]
    end

    subgraph Wave 3: HITL & Review Backend
        T10 & T03 & T04 --> T11[T11: Stage 4 HITL Engine & Pipeline Orchestrator]
        T11 --> T12[T12: REST API & Human Review Workspace]
    end

    subgraph Wave 4: Evaluation Adapter & Export
        T12 --> T13[T13: Evaluation Adapter & Safe Export]
    end

    subgraph Wave 5: Frontend Application
        T12 --> T14[T14: Frontend Foundation & Contract Sync]
        T14 --> T15[T15: Frontend Core Views & Review UX]
    end

    subgraph Wave 6: Verification, E2E & Readiness
        T13 & T15 --> T16[T16: Regression Suite, E2E & Final UAT]
    end
```

---

## 4. Execution Waves Summary

| Wave | Primary Objective | Key Task Range | Entry Criteria | Exit Criteria / Verification Gate |
|---|---|---|---|---|
| **Wave 0** | Baseline Safety & Fixtures | `T00-01` to `T01-04` | Approved `05_TEST_PLAN.md`. | Git commit clean; 16 legacy tests green; synthetic fixtures loaded. |
| **Wave 1** | Contracts & Deterministic Core | `T02-01` to `T04-02` | Wave 0 exit passed. | `CT-DATA-*` & `UT-NORM-*` pass 100%; 7-field pure comparator passing. |
| **Wave 2** | Parsers, AI & Pipeline Stages | `T05-01` to `T10-03` | Wave 1 exit passed. | `PAR-*`, `AI-*`, `PIPE-CLS-*`, `UT-EXT-*` pass without live bundle dependency. |
| **Wave 3** | HITL & Review Backend | `T11-01` to `T12-04` | Wave 2 exit passed. | `HITL-RSN-*`, `HITL-REV-*`, `API-AUD-*`, `API-REV-*` passing with 409 concurrency. |
| **Wave 4** | Evaluation Adapter & Export | `T13-01` to `T13-02` | Wave 3 exit passed. | `EVAL-MAP-*`, `API-EXP-001/002` passing; `EXPORT_BLOCKED` enforced. |
| **Wave 5** | Frontend Application | `T14-01` to `T15-06` | Wave 4 exit passed. | React SPA operational; TypeScript types verified; review route functional. |
| **Wave 6** | Verification, E2E & Readiness | `T16-01` to `T16-05` | Wave 5 exit passed. | `REG-001`–`012` green; `E2E-001`–`016` green; UAT checklist qualified. |

---

## 5. Detailed Task Catalogue

---

### Wave 0: Safety, Pre-Change Capture & Synthetic Fixtures

#### `T00-01`: Pre-Change Baseline Checkpoint & Repository Status Capture
- **Priority**: `P0`
- **Dependencies**: None
- **Specification References**: [`AGENTS.md`](../AGENTS.md) §1, §9
- **Test References**: Current 16 pytest tests
- **Current Gap**: Uncommitted modifications exist across specs in git working tree. Need explicit baseline record before implementation.
- **Scope**: Document current test execution logs, package versions, entry points, and establish clean pre-implementation Git checkpoint.
- **Files Likely Affected**: `docs/BASELINE_STATUS_2026-09-22.md`
- **Implementation Requirements**:
  1. Record exact Python environment (`python -V`, `pip list`).
  2. Record 16/16 test run output and SHA256 hashes of test files.
  3. Ensure working tree status is committed or clean before code migration starts.
- **Explicit Non-Goals**: Modifying any production or test code.
- **Acceptance Criteria**: Baseline status document authored and committed; all 16 legacy tests pass cleanly.
- **Verification Commands**: `python -m pytest tests -v`
- **Expected Evidence**: Clean pytest log showing 16 passes; documentation artifact in `docs/`.
- **Status**: `DONE`

---

#### `T00-02`: Dependency Audit & Environment Isolation
- **Priority**: `P0`
- **Dependencies**: `T00-01`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §11, [`AGENTS.md`](../AGENTS.md) §8
- **Test References**: N/A
- **Current Gap**: Verify if existing packages (`fastapi`, `pydantic>=2.0.0`, `pypdf`, `python-docx`, `openpyxl`, `google-genai`, `pytest`) are sufficient; lock dependencies cleanly.
- **Scope**: Inspect `requirements.txt`; ensure `pydantic>=2.0.0` features (e.g. `model_validator`, `field_validator`) execute without deprecation warnings.
- **Files Likely Affected**: `requirements.txt`
- **Implementation Requirements**: Verify no unapproved external heavy dependencies are introduced.
- **Explicit Non-Goals**: Adding unnecessary web frameworks or databases.
- **Acceptance Criteria**: `pip check` reports zero broken requirements; environment ready for Pydantic v2 schemas.
- **Verification Commands**: `pip check`
- **Expected Evidence**: Exit code 0 from dependency check.
- **Status**: `DONE`

---

#### `T01-01`: Synthetic Email JSON Fixture Suite
- **Priority**: `P0`
- **Dependencies**: `T00-01`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §6.1, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.1
- **Test References**: `PIPE-CLS-001` through `PIPE-CLS-007`, `REG-001`
- **Current Gap**: Tests currently load live evaluation files from `sdoc-hackathon-bundle/inbox/`.
- **Scope**: Create isolated synthetic email fixtures in `tests/fixtures/emails/`.
- **Files Likely Affected**: `tests/fixtures/emails/*.json`
- **Implementation Requirements**:
  1. Synthetic email JSON files covering all 5 categories (`document_comparison`, `new_shipping_instruction`, `invoice_query`, `general`, `spam`).
  2. Edge case fixture: 0-attachment email requesting SI/BL comparison (`EC-002`, `REG-001`).
  3. Edge case fixture: non-comparison email containing SI/BL attachment names (`FR-004`).
  4. Ambiguous intent fixture with low classification confidence.
- **Explicit Non-Goals**: Scraping or copying private evaluation answers.
- **Acceptance Criteria**: All synthetic email fixtures validate against `EmailRecord` schema; zero reliance on `sdoc-hackathon-bundle/inbox/`.
- **Verification Commands**: `python -c "import json, glob; [json.load(open(f)) for f in glob.glob('tests/fixtures/emails/*.json')]"`
- **Expected Evidence**: Valid JSON loading across all synthetic fixtures.
- **Status**: `DONE`

---

#### `T01-02`: Synthetic Multi-Format Document Fixture Suite
- **Priority**: `P0`
- **Dependencies**: `T00-01`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §6.1, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §3
- **Test References**: `PAR-TXT-001`, `PAR-DOCX-001`, `PAR-PDF-001/002`, `PAR-XLSX-001`, `PAR-USAB-001`–`004`
- **Current Gap**: Parser tests currently read from `sdoc-hackathon-bundle/attachments/`.
- **Scope**: Generate controlled synthetic documents in `tests/fixtures/documents/`.
- **Files Likely Affected**: `tests/fixtures/documents/{txt, docx, pdf, xlsx}/*`
- **Implementation Requirements**:
  1. Plain-text SI and BL pairs with standard and alternative labels.
  2. Word document (`.docx`) containing multi-column tables and cell metadata.
  3. Vector PDF with cleanly extractable text layer.
  4. Truncated/corrupted stream PDF (`is_corrupted = True`).
  5. Synthetic scanned image PDF (300 DPI image rendered without text layer).
  6. Multi-sheet Excel workbook (`.xlsx`) containing container and cargo weight tables.
  7. Partial usability document (valid comparison fields, garbled footer disclaimer).
- **Explicit Non-Goals**: Touching `sdoc-hackathon-bundle/attachments/`.
- **Acceptance Criteria**: Synthetic document files generated and verified readable by standard parsers.
- **Verification Commands**: `pytest tests/test_parsers.py` (updated to support fixtures).
- **Expected Evidence**: Synthetic fixtures present in repository under `tests/fixtures/documents/`.
- **Status**: `DONE`

---

#### `T01-03`: Synthetic AI Adapter Response & Fault Injection Fixtures
- **Priority**: `P0`
- **Dependencies**: `T00-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2, §6, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §6
- **Test References**: `AI-ADP-001` through `AI-ADP-006`, `AI-BUD-001` through `AI-BUD-005`
- **Scope**: Create mock JSON responses, technical fault injection payloads, and retry sequences in `tests/fixtures/ai/`.
- **Files Likely Affected**: `tests/fixtures/ai/**`
- **Implementation Requirements**:
  1. Valid structured JSON responses for classification, role resolution, and extraction.
  2. Malformed JSON syntax (missing quotes, unclosed brackets) to verify semantic retry repair.
  3. Schema violation responses (invalid enum values, missing mandatory keys, extra hallucinated keys).
  4. Simulated HTTP 429 Rate Limit and HTTP 503 Provider Error injection payloads.
- **Explicit Non-Goals**: Calling live external APIs in deterministic test runs.
- **Acceptance Criteria**: Mock adapter can load and replay all scenarios without live network access.
- **Verification Commands**: `python tests/fixtures/validate_ai_fixtures.py`
- **Expected Evidence**: 100% offline synthetic AI response fixtures available in `tests/fixtures/ai/`.
- **Status**: `DONE`

---

#### `T01-04`: Synthetic Human Review & Concurrency Payloads
- **Priority**: `P0`
- **Dependencies**: `T00-01`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7, §8
- **Test References**: `CT-DATA-007`, `HITL-REV-001` through `HITL-REV-006`, `API-REV-001` through `API-REV-003`
- **Current Gap**: Zero fixtures for `ReviewUpdate`, optimistic locking revision collisions, or field corrections.
- **Scope**: Create valid and invalid review payloads in `tests/fixtures/payloads/`.
- **Files Likely Affected**: `tests/fixtures/payloads/*.json`
- **Implementation Requirements**:
  1. Valid `ReviewUpdate` for field correction (e.g. correcting `gross_weight_kg`).
  2. Valid `ReviewUpdate` for role assignment (binding SI and BL paths).
  3. Valid `ReviewUpdate` for category resolution (`category = null` $\rightarrow$ `document_comparison`).
  4. Stale `expected_revision` payload simulating HTTP 409 revision collision.
  5. Invalid payload attempting direct modification of `mismatch_detected` boolean (`REG-012`).
- **Explicit Non-Goals**: Bypassing Pydantic payload validation.
- **Acceptance Criteria**: Fixtures validate against `ReviewUpdate` schema or trigger expected validation errors.
- **Verification Commands**: `python tests/fixtures/validate_review_fixtures.py`
- **Expected Evidence**: Complete suite of human review mutation fixtures available in `tests/fixtures/review/`.
- **Status**: `DONE`

---

### Wave 1: Data Contracts & Deterministic Core

#### `T02-01`: Core Ingestion & Classification Pydantic Models (`DC-01`)
- **Priority**: `P0`
- **Dependencies**: `T01-01`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §2, §3
- **Test References**: `CT-DATA-001`, `CT-DATA-009`, `EC-001`, `DC-01`
- **Current Gap**: `src/pipeline/schema.py` uses legacy string category types and competition strings.
- **Scope**: Implement `EmailRecord`, `AttachmentReference`, `EmailCategory` enum, and `ClassificationResult` in `src/models/ingestion.py`.
- **Files Likely Affected**: `src/models/ingestion.py`, `src/models/__init__.py`
- **Implementation Requirements**:
  1. `EmailCategory` enum: `document_comparison`, `new_shipping_instruction`, `invoice_query`, `general`, `spam`.
  2. `ClassificationResult.category: Optional[EmailCategory] = None` allowing `None` strictly for internal unresolved state (`DC-01`).
  3. `ClassificationResult.evidence: FieldEvidence` required for grounded intent tracking.
  4. Strict validation (`extra = "forbid"`).
- **Explicit Non-Goals**: Exposing competition categories (`BL_COMPARISON`) inside domain models.
- **Acceptance Criteria**: `CT-DATA-001` passes; model rejects invalid string categories and validates nullability properly.
- **Verification Commands**: `pytest tests/test_contracts.py -k CT-DATA-001 -v`
- **Expected Evidence**: Passing unit contract test.
- **Status**: `DONE`

---

#### `T02-02`: Document Reference & Parser Result Models (`DEC-P02`)
- **Priority**: `P0`
- **Dependencies**: `T02-01`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §4
- **Test References**: `CT-DATA-009`, `PAR-USAB-001`–`004`
- **Current Gap**: `src/parsers/base.py` uses an untyped Python class `DocumentParseResult`.
- **Scope**: Implement `DocumentRole` enum (`SI`, `BL`, `SUPPORTING`, `UNKNOWN`), `ParserStatus` enum (`SUCCESS`, `PARTIAL`, `UNREADABLE`), `DocumentReference`, and `ParserResult`.
- **Files Likely Affected**: `src/models/document.py`, `src/parsers/base.py`
- **Implementation Requirements**:
  1. `ParserResult` model with fields: `raw_text`, `clean_text`, `status`, `usable_for_extraction`, `page_count`, `table_count`, `is_scanned`, `error_message`, `metadata`.
  2. Enforce Pydantic v2 model validation and immutable serialization.
- **Explicit Non-Goals**: Modifying parser implementations in this task.
- **Acceptance Criteria**: `ParserResult` instantiates and validates cleanly across all parser output states.
- **Verification Commands**: `pytest tests/test_contracts.py -k test_parser_models -v`
- **Expected Evidence**: Passing model validation tests.
- **Status**: `DONE`

---

#### `T02-03`: Structured FieldEvidence & Provenance Models (`DC-05`)
- **Priority**: `P0`
- **Dependencies**: `T02-02`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §5
- **Test References**: `CT-DATA-005`, `UT-EXT-012`, `UT-EXT-013`, `REG-011`
- **Current Gap**: Existing schema only provides a flat `evidence: Optional[str]`.
- **Scope**: Implement `EvidenceKind` enum, `EvidenceLocation`, and `FieldEvidence` models in `src/models/evidence.py`.
- **Files Likely Affected**: `src/models/evidence.py`
- **Implementation Requirements**:
  1. `EvidenceKind` enum supporting generalized evidence forms: `text_span`, `table_cell`, `page_region`, `visual_ocr_box`, `document_metadata`, `synthetic_test`, `error_context`.
  2. `FieldEvidence` fields: `evidence_id`, `kind`, `source_document_id`, `source_document_path`, `quote: Optional[str]`, `location: Optional[EvidenceLocation]`.
  3. Source-grounded FieldEvidence validation and unsupported-evidence rejection: only `text_span` evidence requires a verbatim `quote`; non-text-span evidence references table cell, page/section, or OCR bounding region.
- **Explicit Non-Goals**: Allowing ungrounded or unsupported evidence.
- **Acceptance Criteria**: `CT-DATA-005` passes; models enforce source grounding and provenance across all evidence kinds.
- **Verification Commands**: `pytest tests/test_contracts.py -k CT-DATA-005 -v`
- **Expected Evidence**: Passing contract test.
- **Status**: `DONE`

---

#### `T02-04`: Field Extraction & Normalization Models (`DC-04`)
- **Priority**: `P0`
- **Dependencies**: `T02-03`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §4, §5
- **Test References**: `CT-DATA-004`, `UT-NORM-005`, `DC-04`
- **Current Gap**: Gross weight is stored as IEEE binary `float` in `stage3_compare.py`.
- **Scope**: Implement `NormalizedGrossWeight` with `Decimal` representation, `ExtractedField`, and `NormalizedField`.
- **Files Likely Affected**: `src/models/extraction.py`
- **Implementation Requirements**:
  1. `NormalizedGrossWeight.canonical_kg: Decimal` using Python standard library `decimal.Decimal`.
  2. Custom serializer/validator preserving exact decimal string without floating-point drift.
  3. `FieldStatus` enum: `MISSING`, `RELIABLE`, `UNCERTAIN`, `CONFLICTING`, `UNREADABLE`.
- **Explicit Non-Goals**: Allowing float conversions for canonical weight storage.
- **Acceptance Criteria**: `CT-DATA-004` passes; `Decimal("22500.50")` validates without IEEE precision loss.
- **Verification Commands**: `pytest tests/test_contracts.py -k CT-DATA-004 -v`
- **Expected Evidence**: Passing Decimal contract test.
- **Status**: `DONE`

---

#### `T02-05`: Comparison, Discrepancy & Tri-State Mismatch Models (`DC-03`)
- **Priority**: `P0`
- **Dependencies**: `T02-04`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.3
- **Test References**: `CT-DATA-003`, `PIPE-CMP-004`, `REG-010`, `DC-03`
- **Current Gap**: `mismatch_detected` in `AuditOutputRecord` defaults to `bool = False`.
- **Scope**: Implement `ComparisonOutcome` enum (`MATCH`, `MISMATCH`, `NOT_APPLICABLE`), `FieldComparison`, `Discrepancy`, and `PartialResult` in `src/models/comparison.py`.
- **Files Likely Affected**: `src/models/comparison.py`
- **Implementation Requirements**:
  1. `FieldComparison` with fields: `field_name`, `si_raw`, `si_normalized`, `bl_raw`, `bl_normalized`, `outcome`, `evidence_ids`.
  2. `PartialResult` storing reliable matching fields and pending field issues.
  3. Strict tri-state model where `mismatch_detected` is `Optional[bool] = None` when unresolved.
- **Explicit Non-Goals**: Forcing boolean `false` when fields are unextracted or uncompared.
- **Acceptance Criteria**: `CT-DATA-003` passes; tri-state boolean verified.
- **Verification Commands**: `pytest tests/test_contracts.py -k CT-DATA-003 -v`
- **Expected Evidence**: Passing contract test.
- **Status**: `DONE`

---

#### `T02-06`: HITL Reason Taxonomy & ReviewUpdate Models (`DC-02`, `DC-07`)
- **Priority**: `P0`
- **Dependencies**: `T02-05`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §4
- **Test References**: `CT-DATA-002`, `CT-DATA-007`, `CT-DATA-010`, `HITL-REV-001`, `REG-012`
- **Current Gap**: `HITLEscalation` only has 4 unstructured string reasons; no `ReviewUpdate` schema.
- **Scope**: Implement `LogicalReason` enum (7 values), `ReviewIssue`, `ReviewCase`, `RoleCorrection`, `FieldCorrection`, and `ReviewUpdate` in `src/models/review.py`.
- **Files Likely Affected**: `src/models/review.py`
- **Implementation Requirements**:
  1. `LogicalReason` enum: `missing_attachment`, `unreadable_document`, `wrong_or_uncertain_document_type`, `missing_required_value`, `uncertain_result`, `conflicting_candidate_values`, `processing_or_provider_failure`.
  2. `ReviewUpdate` fields: `action: Literal['CONFIRM', 'CORRECT']`, `expected_revision: int`, `corrections: list[FieldCorrection]`, `role_corrections`, `category_correction`, `notes`.
  3. `ReviewUpdate` configured with `extra = "forbid"`; no `mismatch_detected` field permitted (`REG-012`).
- **Explicit Non-Goals**: Allowing reviewer to manually set derived `mismatch_detected` boolean.
- **Acceptance Criteria**: `CT-DATA-002`, `CT-DATA-007`, `CT-DATA-010` pass cleanly.
- **Verification Commands**: `pytest tests/test_contracts.py -k "CT-DATA-002 or CT-DATA-007 or CT-DATA-010" -v`
- **Expected Evidence**: Passing contract tests.
- **Status**: `DONE`

---

#### `T02-07`: Full AuditRecord & AttemptTracker Models (`DC-06`, `DC-08`)
- **Priority**: `P0`
- **Dependencies**: `T02-06`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5, §6, §8
- **Test References**: `CT-DATA-006`, `CT-DATA-008`, `CT-DATA-009`, `AI-BUD-004`
- **Current Gap**: Legacy `AuditOutputRecord` lacks `revision`, `state`, `evidence`, `documents`, and retry tracking.
- **Scope**: Implement `WorkflowState` enum (`PENDING`, `PROCESSING`, `COMPLETE`, `NEEDS_REVIEW`, `FAILED`), `AttemptTracker`, `AuditRecord`, and `ErrorResponse` in `src/models/audit.py`.
- **Files Likely Affected**: `src/models/audit.py`, `src/models/__init__.py`
- **Implementation Requirements**:
  1. `AttemptTracker` with `technical_attempt_limit: int = 3`, `semantic_attempt_limit: int = 2`, `total_provider_calls: int`.
  2. `AuditRecord` exposing complete state, revision counter (`revision: int = 1`), `mismatch_detected: Optional[bool]`, `outcome: Optional[ComparisonOutcome]`, `documents: dict`, `comparisons: list`, `evidence: dict`, `partial_result`, and `review: Optional[ReviewCase]`.
  3. `ErrorResponse` with `code: str`, `message: str`, `blocking_emails: list[str]`.
- **Explicit Non-Goals**: Omitting required lineage or concurrency revision counters.
- **Acceptance Criteria**: All 15 contract examples from `specs/03_DATA_CONTRACTS_EXAMPLES.json` instantiate without validation error.
- **Verification Commands**: `pytest tests/test_contracts.py -k CT-DATA-009 -v`
- **Expected Evidence**: Full contract validation pass.
- **Status**: `DONE`

---

#### `T02-08`: Contract Test Suite Automation
- **Priority**: `P0`
- **Dependencies**: `T02-01` through `T02-07`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §8
- **Test References**: `CT-DATA-001` through `CT-DATA-010`
- **Current Gap**: `tests/` currently contains zero schema contract tests.
- **Scope**: Implement `tests/test_contracts.py` verifying all 10 contract test specifications.
- **Files Likely Affected**: `tests/test_contracts.py`
- **Implementation Requirements**:
  1. Test instantiation against `specs/03_DATA_CONTRACTS_EXAMPLES.json`.
  2. Verify rejection of extra fields (`extra = "forbid"`).
  3. Verify nullability of `category` strictly for internal unresolved state.
  4. Verify tri-state `mismatch_detected` invariance.
- **Explicit Non-Goals**: Testing business pipeline logic in this unit contract suite.
- **Acceptance Criteria**: All 10 contract tests (`CT-DATA-001` through `CT-DATA-010`) execute and pass cleanly.
- **Verification Commands**: `pytest tests/test_contracts.py -v`
- **Expected Evidence**: 10 passed tests in `tests/test_contracts.py`.
- **Status**: `DONE`

---

#### `T03-01`: Deterministic Text & Spacing Canonical Normalizers (`DEC-P06A`)
- **Priority**: `P0`
- **Dependencies**: `T02-08`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §10, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §5.3
- **Test References**: `UT-NORM-001`, `UT-NORM-002`, `UT-NORM-003`
- **Current Gap**: Existing normalizer strips legal suffixes (`LTD`, `INC`), violating `DEC-P06D`.
- **Scope**: Implement pure text normalizers in `src/normalization/text_normalizer.py`.
- **Files Likely Affected**: `src/normalization/text_normalizer.py`, `src/normalization/__init__.py`
- **Implementation Requirements**:
  1. Unicode NFKC normalization (converting full-width characters to standard ASCII/Unicode).
  2. Whitespace collapsing and case-folding to uppercase.
  3. Punctuation cleanup (stripping trailing dots, extraneous commas, standardizing quotes).
  4. **Strict Guard**: Do **NOT** strip corporate entity suffixes (`LTD`, `CORP`, `INC`).
- **Explicit Non-Goals**: Semantic alias mapping or dictionary translations.
- **Acceptance Criteria**: `UT-NORM-001`, `UT-NORM-002`, `UT-NORM-003` pass cleanly.
- **Verification Commands**: `pytest tests/test_normalization.py -k "UT-NORM-001 or UT-NORM-002 or UT-NORM-003" -v`
- **Expected Evidence**: Passing unit normalization tests.
- **Status**: `NOT_STARTED`

---

#### `T03-02`: Unit Normalizer & Decimal Weight Conversion (`DEC-P06B`, `DC-04`)
- **Priority**: `P0`
- **Dependencies**: `T03-01`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §10, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §4
- **Test References**: `UT-NORM-004`, `UT-NORM-005`, `UT-EXT-007`, `UT-EXT-009`
- **Current Gap**: `normalize_gross_weight_kg` uses floating-point arithmetic.
- **Scope**: Implement `src/normalization/unit_normalizer.py` for numeric container counts and gross weights.
- **Files Likely Affected**: `src/normalization/unit_normalizer.py`
- **Implementation Requirements**:
  1. Container count: extract spelled numbers (`"Three (3)"` $\rightarrow$ `3`), sum multi-container formats (`"2 X 40HC, 1 X 20GP"` $\rightarrow$ `3`).
  2. Gross weight: exact mathematical MT conversion ($MT \times 1000 = kg$) using `Decimal`.
  3. Strip thousand-separator commas (`"25,432.50 KGS"` $\rightarrow$ `Decimal("25432.50")`).
- **Explicit Non-Goals**: Introducing floating-point approximations.
- **Acceptance Criteria**: `UT-NORM-004`, `UT-NORM-005` pass cleanly.
- **Verification Commands**: `pytest tests/test_normalization.py -k "UT-NORM-004 or UT-NORM-005" -v`
- **Expected Evidence**: Passing unit test assertions for exact Decimal conversions.
- **Status**: `NOT_STARTED`

---

#### `T03-03`: Negative Normalization Regression Guards (`DEC-P06C/D/E`)
- **Priority**: `P0`
- **Dependencies**: `T03-02`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §10, [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §7, §21, §26
- **Test References**: `REG-NORM-001`, `REG-NORM-002`, `REG-NORM-003`, `REG-004`, `REG-005`, `REG-006`
- **Current Gap**: Legacy code allowed $\pm 1\text{ kg}$ tolerance, port stripping, and company suffix stripping.
- **Scope**: Implement negative regression unit tests in `tests/test_normalization_guards.py`.
- **Files Likely Affected**: `tests/test_normalization_guards.py`
- **Implementation Requirements**:
  1. `REG-NORM-001`: Assert `22000 kg` vs `22001 kg` evaluates to `MISMATCH` (no $\pm 1\text{ kg}$ tolerance, `DEC-P06E`).
  2. `REG-NORM-002`: Assert `"SHANGHAI"` vs `"PORT OF SHANGHAI"` evaluates to `MISMATCH` (no port aliasing, `DEC-P06C`).
  3. `REG-NORM-003`: Assert `"ACME CORP"` vs `"ACME CORPORATION"` evaluates to `MISMATCH` (no legal suffix stripping, `DEC-P06D`).
  4. Explicitly document that these tests protect CURRENT baseline behavior and remain amendment-sensitive.
- **Explicit Non-Goals**: Silently resolving any of the three TBDs.
- **Acceptance Criteria**: All 3 negative guard tests pass cleanly.
- **Verification Commands**: `pytest tests/test_normalization_guards.py -v`
- **Expected Evidence**: Regression guard tests passing 100%.
- **Status**: `NOT_STARTED`

---

#### `T04-01`: Pure Deterministic 7-Field Comparator Engine (`DEC-01`)
- **Priority**: `P0`
- **Dependencies**: `T03-03`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §7, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.3
- **Test References**: `PIPE-CMP-001`, `PIPE-CMP-002`, `PIPE-CMP-003`, `DEC-01`, `FR-011`, `FR-012`
- **Current Gap**: Legacy `stage3_compare.py` has substring matching, fuzzy tolerances, and monolithic text comparison.
- **Scope**: Implement `src/comparator/field_comparator.py`.
- **Files Likely Affected**: `src/comparator/field_comparator.py`, `src/comparator/__init__.py`
- **Implementation Requirements**:
  1. Compares exactly and only the 7 mandatory fields: `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, `gross_weight_kg`.
  2. Pure deterministic software execution: **zero LLM calls**.
  3. Emits `"No mismatch detected"` ONLY when all 7 fields are present, reliable, and match 1:1 (`FR-011`).
  4. Generates structured `Discrepancy` array with field, `si_value`, `bl_value` for any difference (`FR-012`).
- **Explicit Non-Goals**: Tolerating fuzzy string matches or unresolved fields.
- **Acceptance Criteria**: `PIPE-CMP-001` (match), `PIPE-CMP-002` (single mismatch), and `PIPE-CMP-003` (multiple mismatches) pass cleanly.
- **Verification Commands**: `pytest tests/test_comparator.py -v`
- **Expected Evidence**: Passing comparator test suite.
- **Status**: `NOT_STARTED`

---

#### `T04-02`: Tri-State Mismatch Evaluation & Partial Result Accumulator
- **Priority**: `P0`
- **Dependencies**: `T04-01`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §4.3
- **Test References**: `PIPE-CMP-004`, `PIPE-CMP-005`, `REG-009`, `REG-010`, `HITL-PART-001`
- **Current Gap**: When any field was unextracted, legacy engine defaulted `mismatch_detected` to `False`.
- **Scope**: Implement accumulator logic inside `src/comparator/field_comparator.py`.
- **Files Likely Affected**: `src/comparator/field_comparator.py`
- **Implementation Requirements**:
  1. If any of the 7 mandatory fields is missing, uncertain, unreadable, or conflicting, `mismatch_detected` is strictly set to `None` (`DC-03`).
  2. Preserve all reliable matching fields in `partial_result.comparisons` (`DEC-AI-P04`, `REG-009`).
  3. Ensure `"No mismatch detected"` is **NEVER** emitted when a case requires review (`REG-010`).
- **Explicit Non-Goals**: Converting unresolved status into `false` or clean match.
- **Acceptance Criteria**: `PIPE-CMP-004`, `PIPE-CMP-005`, `REG-009`, `REG-010` pass cleanly.
- **Verification Commands**: `pytest tests/test_comparator.py -k "PIPE-CMP-004 or REG-009 or REG-010" -v`
- **Expected Evidence**: Passing tri-state invariant tests.
- **Status**: `NOT_STARTED`

---

### Wave 2: Parsers, AI Adapter & Pipeline Stages

#### `T05-01`: Pluggable BaseParser Interface & ParserResult Model Alignment
- **Priority**: `P0`
- **Dependencies**: `T02-08`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §4, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §4
- **Test References**: `PAR-TXT-001`, `NFR-004`
- **Current Gap**: `src/parsers/base.py` currently returns a legacy untyped `DocumentParseResult` class.
- **Scope**: Adapt `src/parsers/base.py` and `src/parsers/text_parser.py` to refine the `BaseParser` abstraction and return Pydantic `ParserResult`.
- **Files Likely Affected**: `src/parsers/base.py`, `src/parsers/text_parser.py`
- **Implementation Requirements**:
  1. Retain and refine the `BaseParser` interface/abstraction: abstract method `parse(file_path: Path) -> ParserResult`.
  2. Require concrete parser implementations to return the baselined `ParserResult` Pydantic model.
  3. Keep parsing behavior separate from parser result data.
  4. `TextParser` reads UTF-8 and returns `ParserResult(status=ParserStatus.SUCCESS, usable_for_extraction=True, clean_text=...)`.
  5. Retain backwards compatibility wrapper for legacy callers during migration.
- **Explicit Non-Goals**: Replacing `BaseParser` abstraction with a data model or breaking existing `tests/test_parsers.py`.
- **Acceptance Criteria**: `PAR-TXT-001` passes using synthetic text fixture; existing 16 tests remain green.
- **Verification Commands**: `pytest tests/test_parsers.py -v`
- **Expected Evidence**: Clean passing parser test run.
- **Status**: `NOT_STARTED`

---

#### `T05-02`: Qualitative Text Usability Validation Engine (`DEC-P02`)
- **Priority**: `P0`
- **Dependencies**: `T05-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §3.2
- **Test References**: `PAR-USAB-001`, `PAR-USAB-002`, `PAR-USAB-003`, `PAR-USAB-004`, `REG-007`
- **Current Gap**: `src/parsers/__init__.py` used `len(text) > 20` to trigger OCR/DocAI.
- **Scope**: Implement `src/parsers/usability_validator.py`.
- **Files Likely Affected**: `src/parsers/usability_validator.py`, `src/parsers/__init__.py`
- **Implementation Requirements**:
  1. Inspect parsed text for empty content, high proportion of replacement/garbage characters (`\ufffd`), or missing text streams.
  2. Valid short documents (e.g. 18 chars) must be accepted without OCR (`PAR-USAB-001`, `REG-007`).
  3. Image-only empty PDFs trigger `is_scanned = True` and OCR fallback routing (`PAR-USAB-003`).
  4. Partial usability allows extraction to proceed if essential fields are readable (`PAR-USAB-004`).
- **Explicit Non-Goals**: Enforcing arbitrary minimum character counts.
- **Acceptance Criteria**: `PAR-USAB-001` through `PAR-USAB-004` and `REG-007` pass cleanly.
- **Verification Commands**: `pytest tests/test_usability.py -v`
- **Expected Evidence**: Passing usability test suite.
- **Status**: `NOT_STARTED`

---

#### `T05-03`: DOCX, PDF, and XLSX Pluggable Parsers Upgrade
- **Priority**: `P1`
- **Dependencies**: `T05-02`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §4, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.2
- **Test References**: `PAR-DOCX-001`, `PAR-PDF-001`, `PAR-PDF-002`, `PAR-XLSX-001`, `NFR-003`, `FR-006A/B/C`, `FR-007`
- **Current Gap**: Existing parsers do not preserve table coordinates, cell locations, or page metadata.
- **Scope**: Upgrade `src/parsers/docx_parser.py`, `src/parsers/pdf_parser.py`, and `src/parsers/excel_parser.py`.
- **Files Likely Affected**: `src/parsers/docx_parser.py`, `src/parsers/pdf_parser.py`, `src/parsers/excel_parser.py`
- **Implementation Requirements**:
  1. `DocxParser`: Extract table structures with row/col metadata (`FR-007`).
  2. `PdfParser`: Intercept corrupt streams cleanly (`is_corrupted = True`, `status = UNREADABLE`, `NFR-003`); record page numbers.
  3. `ExcelParser`: Extract sheet names and cell coordinates (`FR-006C`).
  4. Return standardized `ParserResult`.
- **Explicit Non-Goals**: Rewriting PDF rendering engines.
- **Acceptance Criteria**: `PAR-DOCX-001`, `PAR-PDF-001/002`, `PAR-XLSX-001` pass on synthetic fixtures.
- **Verification Commands**: `pytest tests/test_parsers.py -v`
- **Expected Evidence**: 100% pass on synthetic documents.
- **Status**: `NOT_STARTED`

---

#### `T06-01`: OCR / Vision Fallback Interface & Mock Adapter (`FR-008`, `DEC-P02`)
- **Priority**: `P1`
- **Dependencies**: `T05-02`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §5, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §3.3
- **Test References**: `AI-OCR-001`, `AI-OCR-005`, `AI-OCR-006`
- **Current Gap**: `docai_adapter.py` is an unmocked stub without fallback cascade or retry budgets.
- **Scope**: Implement `BaseVisionAdapter` and `MockVisionAdapter` in `src/parsers/vision_adapter.py`.
- **Files Likely Affected**: `src/parsers/vision_adapter.py`
- **Implementation Requirements**:
  1. Triggered only when deterministic parse yields `is_scanned = True` or `usable_for_extraction = False`.
  2. Mocked implementation for deterministic CI runs returning structured OCR bounding boxes and text.
  3. Intercept provider errors; escalate to `processing_or_provider_failure` upon exhaustion (`AI-OCR-006`).
- **Explicit Non-Goals**: Calling live external OCR services during routine CI.
- **Acceptance Criteria**: `AI-OCR-001`, `AI-OCR-005`, `AI-OCR-006` pass under simulated adapter conditions.
- **Verification Commands**: `pytest tests/test_vision_adapter.py -v`
- **Expected Evidence**: Passing OCR fallback tests.
- **Status**: `NOT_STARTED`

---

#### `T06-02`: Essential Field Legibility Gate & Partial Degradation Handler
- **Priority**: `P1`
- **Dependencies**: `T06-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §3.3, §4.3
- **Test References**: `AI-OCR-002`, `AI-OCR-003`, `AI-OCR-004`, `DEC-AI-P04`
- **Current Gap**: Unreadable footers in previous drafts caused full document rejection.
- **Scope**: Implement partial legibility filter in `src/parsers/vision_adapter.py`.
- **Files Likely Affected**: `src/parsers/vision_adapter.py`
- **Implementation Requirements**:
  1. If terms/conditions or footer disclaimers are blurry, but all 7 comparison fields are sharp, accept document (`AI-OCR-002`).
  2. If a mandatory field is blurred/unreadable, flag only that field as `missing_required_value` (`AI-OCR-003`).
  3. If ambiguous OCR produces multiple candidates, escalate to `conflicting_candidate_values` (`AI-OCR-004`).
- **Explicit Non-Goals**: Discarding legible fields when an irrelevant section is smudged.
- **Acceptance Criteria**: `AI-OCR-002`, `AI-OCR-003`, `AI-OCR-004` pass cleanly.
- **Verification Commands**: `pytest tests/test_vision_adapter.py -k "AI-OCR-002 or AI-OCR-003 or AI-OCR-004" -v`
- **Expected Evidence**: Passing partial legibility tests.
- **Status**: `NOT_STARTED`

---

#### `T07-01`: Provider-Agnostic `BaseAIAdapter` Interface & Schema Validator (`DEC-P01`)
- **Priority**: `P0`
- **Dependencies**: `T02-08`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §5, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2.1
- **Test References**: `AI-ADP-001`, `AI-ADP-002`, `AI-ADP-003`, `AI-ADP-004`
- **Current Gap**: Direct dependency on `google.genai` in `src/llm/client.py`; no abstract adapter interface.
- **Scope**: Implement `BaseAIAdapter` in `src/llm/base_adapter.py` and `MockAIAdapter` in `tests/mocks/mock_ai_adapter.py`.
- **Files Likely Affected**: `src/llm/base_adapter.py`, `tests/mocks/mock_ai_adapter.py`
- **Implementation Requirements**:
  1. Methods: `classify_email()`, `resolve_document_roles()`, `extract_fields()`.
  2. Automatic response parsing and Pydantic v2 model validation.
  3. Extra keys rejected per schema configuration (`AI-ADP-004`).
  4. Invalid JSON or invalid enums trigger semantic retry repair prompt (`AI-ADP-002/003`).
- **Explicit Non-Goals**: Allowing AI to make final comparison decisions.
- **Acceptance Criteria**: `AI-ADP-001` through `AI-ADP-004` pass cleanly in mocked offline mode.
- **Verification Commands**: `pytest tests/test_ai_adapter.py -k "AI-ADP-001 or AI-ADP-002 or AI-ADP-003 or AI-ADP-004" -v`
- **Expected Evidence**: Passing offline adapter contract tests.
- **Status**: `NOT_STARTED`

---

#### `T07-02`: Bounded Retry Tracker & Nested Provider Budget Cap (`DEC-AI-P01/02`)
- **Priority**: `P0`
- **Dependencies**: `T07-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2.3, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §6
- **Test References**: `AI-BUD-001`, `AI-BUD-002`, `AI-BUD-003`, `AI-BUD-004`, `AI-BUD-005`, `AI-ADP-006`, `DC-06`
- **Current Gap**: Unbounded `max_retries = 4` with linear delays in `GeminiClient`; no nested call budget tracking.
- **Scope**: Implement `AttemptTracker` and retry budget coordinator in `src/llm/retry_handler.py`.
- **Files Likely Affected**: `src/llm/retry_handler.py`, `src/llm/base_adapter.py`
- **Implementation Requirements**:
  1. Default attempt limits: `technical_attempt_limit = 3` (includes initial call), `semantic_attempt_limit = 2` (includes initial call).
  2. Exponential backoff with jitter on transient network/HTTP 429 errors (`AI-ADP-006`).
  3. **Strict Invariant**: Total provider invocations across retries and fallbacks within any single request are capped at **6** (`AI-BUD-004`).
  4. Mandatory validation of fallback outputs before ingestion (`AI-BUD-005`, `REG-008`).
- **Explicit Non-Goals**: Permitting infinite retry loops or unbudgeted cascade calls.
- **Acceptance Criteria**: `AI-BUD-001` through `AI-BUD-005` pass cleanly.
- **Verification Commands**: `pytest tests/test_ai_adapter.py -k "AI-BUD" -v`
- **Expected Evidence**: Passing retry budget test suite.
- **Status**: `NOT_STARTED`

---

#### `T07-03`: Diagnostic Confidence Decoupling & Source-Grounded Evidence Validator
- **Priority**: `P0`
- **Dependencies**: `T07-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2.2, §5.2
- **Test References**: `AI-ADP-005`, `REG-011`, `UT-EXT-013`
- **Current Gap**: Confidence was used as a bypass gate for verification in early prototypes.
- **Scope**: Implement `validate_evidence_grounding()` in `src/llm/evidence_validator.py`.
- **Files Likely Affected**: `src/llm/evidence_validator.py`
- **Implementation Requirements**:
  1. Diagnostic-only treatment of confidence: confidence $\ge 0.99$ **CANNOT** bypass evidence validation (`AI-ADP-005`, `REG-011`).
  2. Source-grounded FieldEvidence validation and unsupported-evidence rejection: verify that extracted evidence is grounded in source content. Only `text_span` evidence requires a verbatim `quote` matching the parsed document text layer (`UT-EXT-013`); non-text-span evidence validates against coordinate, table cell, or OCR bounding regions.
  3. Fabricated or ungrounded evidence is rejected. The affected field fails the reliability gate and is routed to the appropriate existing ReviewIssue / LogicalReason according to the actual failure condition (e.g. `uncertain_result`, `missing_required_value`, `conflicting_candidate_values`, or `processing_or_provider_failure`). Do not introduce an eighth LogicalReason.
- **Explicit Non-Goals**: Accepting unsupported citations or allowing confidence to bypass evidence checks.
- **Acceptance Criteria**: `AI-ADP-005`, `REG-011`, `UT-EXT-013` pass cleanly.
- **Verification Commands**: `pytest tests/test_ai_adapter.py -k "AI-ADP-005 or REG-011 or UT-EXT-013" -v`
- **Expected Evidence**: Passing evidence validation tests.
- **Status**: `NOT_STARTED`

---

#### `T07-04`: Google Gemini Adapter Implementation
- **Priority**: `P1`
- **Dependencies**: `T07-01`, `T07-02`, `T07-03`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §5, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2
- **Test References**: Integration tests
- **Current Gap**: `GeminiClient` in `src/llm/client.py` does not adhere to `BaseAIAdapter` interface.
- **Scope**: Implement `GeminiAIAdapter` in `src/llm/gemini_adapter.py` wrapping `genai.Client`.
- **Files Likely Affected**: `src/llm/gemini_adapter.py`, `src/llm/client.py`
- **Implementation Requirements**:
  1. Implements `BaseAIAdapter` methods using `google-genai` SDK.
  2. Integrates `AttemptTracker` and `validate_evidence_grounding`.
  3. Gracefully handles missing `GEMINI_API_KEY` by falling back to deterministic-first or mock adapter.
- **Explicit Non-Goals**: Breaking offline deterministic execution.
- **Acceptance Criteria**: Adapter instantiates, passes interface assertions, and passes mock integration tests.
- **Verification Commands**: `pytest tests/test_gemini_adapter.py -v`
- **Expected Evidence**: Passing adapter implementation tests.
- **Status**: `NOT_STARTED`

---

#### `T08-01`: Deterministic-First / AI-on-Demand Email Intent Classifier (`EC-001`, `DEC-AI-P03`)
- **Priority**: `P0`
- **Dependencies**: `T07-01`, `T01-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §1, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.1
- **Test References**: `PIPE-CLS-001`, `PIPE-CLS-002`, `PIPE-CLS-003`, `PIPE-CLS-005`, `PIPE-CLS-007`, `EC-001`, `DEC-AI-P03`
- **Current Gap**: Legacy classifier outputs competition strings (`BL_COMPARISON`) and skips canonical internal enums.
- **Scope**: Refactor `src/pipeline/stage1_classify.py`.
- **Files Likely Affected**: `src/pipeline/stage1_classify.py`
- **Implementation Requirements**:
  1. Outputs canonical internal `EmailCategory`: `document_comparison`, `new_shipping_instruction`, `invoice_query`, `general`, `spam` (`EC-001`).
  2. Email intent classification operates on available email-level context such as subject, sender, body, and attachment metadata where useful. It does not depend on document parsing or OCR.
  3. Deterministic fast-path: unambiguous keywords and headers resolve without calling AI adapter (`DEC-AI-P03`, `PIPE-CLS-007`).
  4. AI-on-demand fallback for ambiguous text.
  5. Non-comparison emails (`invoice_query`, `general`, `spam`) terminate checking immediately without attachment parsing (`FR-004`).
- **Explicit Non-Goals**: Emitting competition format strings inside Stage 1.
- **Acceptance Criteria**: `PIPE-CLS-001`, `002`, `003`, `005`, `007` pass cleanly.
- **Verification Commands**: `pytest tests/test_stage1.py -k "PIPE-CLS" -v`
- **Expected Evidence**: Passing Stage 1 classification suite.
- **Status**: `NOT_STARTED`

---

#### `T08-02`: Attachment Count Intent Decoupling (`EC-002`, `REG-001`)
- **Priority**: `P0`
- **Dependencies**: `T08-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §1.2, [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §21
- **Test References**: `PIPE-CLS-004`, `REG-001`, `EC-002`
- **Current Gap**: Line 35 of `stage1_classify.py` gated `BL_COMPARISON` on `len(attachments) >= 1`.
- **Scope**: Remove attachment count gate from intent classification in `src/pipeline/stage1_classify.py`.
- **Files Likely Affected**: `src/pipeline/stage1_classify.py`
- **Implementation Requirements**:
  1. If email text expresses intent to compare draft BL and SI, classify as `document_comparison` even if attachments list is empty (`PIPE-CLS-004`, `REG-001`).
  2. Attachment count MUST NOT force an email out of `document_comparison`.
  3. Stage 2 subsequently catches the missing attachment and escalates to `missing_attachment`.
  4. Never force an email into `general` merely because attachments are absent.
- **Explicit Non-Goals**: Allowing attachment count to act as a negative intent gate.
- **Acceptance Criteria**: `PIPE-CLS-004` and `REG-001` pass cleanly.
- **Verification Commands**: `pytest tests/test_stage1.py -k "REG-001 or PIPE-CLS-004" -v`
- **Expected Evidence**: Passing regression test.
- **Status**: `NOT_STARTED`

---

#### `T08-03`: Ambiguous Intent & Null Category Handling (`DC-01`)
- **Priority**: `P0`
- **Dependencies**: `T08-01`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §2, §7, [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §1.3
- **Test References**: `PIPE-CLS-006`, `DC-01`, `HITL-RSN-005`
- **Current Gap**: Classifier forced fallback to `"GENERAL"` when intent was uncertain.
- **Scope**: Update `stage1_classify.py` to support `category = null`.
- **Files Likely Affected**: `src/pipeline/stage1_classify.py`
- **Implementation Requirements**:
  1. When classification confidence is low and heuristics are inconclusive, set `category = None`.
  2. Escalate case to HITL with `logical_reason = "uncertain_result"`.
  3. Case state becomes `NEEDS_REVIEW` until human operator selects category.
- **Explicit Non-Goals**: Inventing a 6th category enum.
- **Acceptance Criteria**: `PIPE-CLS-006` passes cleanly.
- **Verification Commands**: `pytest tests/test_stage1.py -k "PIPE-CLS-006" -v`
- **Expected Evidence**: Passing null category test.
- **Status**: `NOT_STARTED`

---

#### `T09-01`: Deterministic-First Attachment Role Binding (`DEC-AI-P03`)
- **Priority**: `P0`
- **Dependencies**: `T08-01`, `T05-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2, [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §4
- **Test References**: `PAR-ROLE-001`, `DEC-AI-P03`
- **Current Gap**: Role binding was coupled with extraction in legacy `stage2_extract.py`.
- **Scope**: Implement `src/pipeline/stage2_role_binding.py`.
- **Files Likely Affected**: `src/pipeline/stage2_role_binding.py`
- **Implementation Requirements**:
  1. Tier 1 deterministic identification: file naming patterns (`_SI`, `_BL`, `SHIPPING INSTRUCTION`, `BILL OF LADING`), MIME types, and unambiguous headers.
  2. Successfully binds `SI` and `BL` without invoking AI adapter when deterministic evidence is conclusive (`PAR-ROLE-001`).
- **Explicit Non-Goals**: Invoking LLM when deterministic evidence is 100% clear.
- **Acceptance Criteria**: `PAR-ROLE-001` passes without calling AI adapter.
- **Verification Commands**: `pytest tests/test_stage2.py -k "PAR-ROLE-001" -v`
- **Expected Evidence**: Passing deterministic role binding test.
- **Status**: `NOT_STARTED`

---

#### `T09-02`: AI-on-Demand Role Resolution & Ambiguity Escalation
- **Priority**: `P0`
- **Dependencies**: `T09-01`, `T07-01`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §2.2, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.2
- **Test References**: `PAR-ROLE-002` through `PAR-ROLE-008`, `HITL-RSN-001`, `HITL-RSN-002`, `HITL-RSN-003`
- **Current Gap**: Ambiguous documents defaulted to generic strings or crashed.
- **Scope**: Extend `src/pipeline/stage2_role_binding.py` with AI-on-demand and HITL escalation.
- **Files Likely Affected**: `src/pipeline/stage2_role_binding.py`
- **Implementation Requirements**:
  1. Generic filenames (`doc1.pdf`, `doc2.pdf`) route to AI semantic role analysis (`PAR-ROLE-002`).
  2. Missing SI or BL attachments trigger HITL: `logical_reason = "missing_attachment"` (`PAR-ROLE-003/004`, `HITL-RSN-001`).
  3. Duplicate candidate files trigger HITL: `wrong_or_uncertain_document_type` (`PAR-ROLE-005`).
  4. Same file assigned to both roles rejected $\rightarrow$ `wrong_or_uncertain_document_type` (`PAR-ROLE-006`).
  5. Irrelevant document types (e.g. packing list) $\rightarrow$ `wrong_or_uncertain_document_type` (`PAR-ROLE-007`).
  6. Corrupt stream $\rightarrow$ `unreadable_document` (`PAR-ROLE-008`, `HITL-RSN-002`).
- **Explicit Non-Goals**: Silently guessing attachment roles when ambiguous.
- **Acceptance Criteria**: `PAR-ROLE-002` through `PAR-ROLE-008` pass cleanly.
- **Verification Commands**: `pytest tests/test_stage2.py -k "PAR-ROLE" -v`
- **Expected Evidence**: Passing role escalation tests.
- **Status**: `NOT_STARTED`

---

#### `T10-01`: Deterministic Field Extraction & Alias Mapping (`FR-010`)
- **Priority**: `P0`
- **Dependencies**: `T09-01`, `T05-01`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §4, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.3
- **Test References**: `UT-EXT-001` through `UT-EXT-010`, `FR-010`
- **Current Gap**: Regex alias matching in legacy `stage3_compare.py` lacked provenance tracking and multiline address preservation.
- **Scope**: Implement `src/pipeline/stage3_extract.py`.
- **Files Likely Affected**: `src/pipeline/stage3_extract.py`
- **Implementation Requirements**:
  1. Extracts exactly the 7 mandatory fields using comprehensive alias tables.
  2. Preserves full multi-line address blocks for `consignee` and `shipper` without truncation (`UT-EXT-003`).
  3. Resolves `"SAME AS CONSIGNEE"` for `notify_party` (`UT-EXT-004`).
  4. Preserves port name and code (`UT-EXT-005/006`).
  5. Attaches source-grounded `FieldEvidence` citations to every extracted field.
- **Explicit Non-Goals**: Extracting unapproved non-mandatory fields.
- **Acceptance Criteria**: `UT-EXT-001` through `UT-EXT-010` pass cleanly.
- **Verification Commands**: `pytest tests/test_extraction.py -k "UT-EXT" -v`
- **Expected Evidence**: Passing deterministic extraction tests.
- **Status**: `NOT_STARTED`

---

#### `T10-02`: AI Semantic Extraction & Source-Grounded Evidence Validation (`DEC-AI-P05`)
- **Priority**: `P0`
- **Dependencies**: `T10-01`, `T07-01`, `T07-03`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §4, §5, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5
- **Test References**: `UT-EXT-012`, `UT-EXT-013`, `DEC-AI-P05`, `DC-05`
- **Current Gap**: No AI extraction fallback path existed; text extraction was purely regex-based.
- **Scope**: Implement AI semantic extraction fallback in `src/pipeline/stage3_extract.py`.
- **Files Likely Affected**: `src/pipeline/stage3_extract.py`
- **Implementation Requirements**:
  1. Invoked only when deterministic extraction fails to identify a mandatory field.
  2. Prompts LLM for structured field extraction with source evidence reference.
  3. Validates evidence against parsed text/locations using `validate_evidence_grounding` (`UT-EXT-013`). For text spans, validates verbatim quote; for layout/tables, validates cell or coordinate presence.
  4. Stores `FieldEvidence` with document path and line/cell coordinates when available.
  5. Fabricated or ungrounded evidence is rejected. The affected field fails the reliability gate and is routed to the appropriate existing ReviewIssue / LogicalReason according to the actual failure condition (e.g. `uncertain_result`, `missing_required_value`, `conflicting_candidate_values`, or `processing_or_provider_failure`).
- **Explicit Non-Goals**: Allowing unsupported values into comparison.
- **Acceptance Criteria**: `UT-EXT-012` and `UT-EXT-013` pass cleanly.
- **Verification Commands**: `pytest tests/test_extraction.py -k "UT-EXT-012 or UT-EXT-013" -v`
- **Expected Evidence**: Passing grounded AI extraction tests.
- **Status**: `NOT_STARTED`

---

#### `T10-03`: Field-Level Reliability Gate & Partial Work Preservation (`DEC-AI-P04`)
- **Priority**: `P0`
- **Dependencies**: `T10-02`, `T02-04`, `T02-05`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §4.3, [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §21
- **Test References**: `UT-EXT-011`, `HITL-PART-001`, `REG-009`, `DEC-AI-P04`
- **Current Gap**: One failing field caused the entire comparison to abort without recording valid matches.
- **Scope**: Implement field reliability evaluation in `src/pipeline/stage3_extract.py`.
- **Files Likely Affected**: `src/pipeline/stage3_extract.py`
- **Implementation Requirements**:
  1. Assess each of the 7 fields: value extracted $\rightarrow$ grounded $\rightarrow$ unambiguous $\rightarrow$ valid schema $\rightarrow$ `RELIABLE`.
  2. If missing or ungrounded, mark `status = MISSING`, `reliable = False`. Fabricated or ungrounded evidence is rejected; the affected field fails the reliability gate and is routed to the appropriate existing ReviewIssue / LogicalReason according to the actual failure condition (e.g. `missing_required_value`, `uncertain_result`, `conflicting_candidate_values`, or `processing_or_provider_failure`) (`UT-EXT-011`).
  3. Reliable fields proceed to comparison and are preserved in `partial_result.comparisons` (`HITL-PART-001`, `REG-009`).
  4. Case transitions to `NEEDS_REVIEW` while retaining the 6 passing field comparisons.
  5. The extraction task does **NOT** logically depend on the comparator.
- **Explicit Non-Goals**: Discarding passing field results when another field is incomplete.
- **Acceptance Criteria**: `UT-EXT-011`, `HITL-PART-001`, `REG-009` pass cleanly.
- **Verification Commands**: `pytest tests/test_extraction.py -k "HITL-PART-001 or REG-009" -v`
- **Expected Evidence**: Passing partial work preservation tests.
- **Status**: `NOT_STARTED`

---

### Wave 3: HITL Engine, Audit Store & Review Backend

#### `T11-01`: 7 Internal Logical Review Reasons Dispatcher (`DC-02`)
- **Priority**: `P0`
- **Dependencies**: `T09-02`, `T10-03`, `T02-06`
- **Specification References**: [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md) §4.1, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7
- **Test References**: `HITL-RSN-001` through `HITL-RSN-007`, `FR-013`, `FR-014`, `FR-015`, `DC-02`
- **Current Gap**: Legacy code used arbitrary string reasons (`"missing_attachment"`, `"unreadable"`).
- **Scope**: Implement `src/hitl/escalation_engine.py`.
- **Files Likely Affected**: `src/hitl/escalation_engine.py`, `src/hitl/__init__.py`
- **Implementation Requirements**:
  1. Construct `ReviewCase` and `ReviewIssue` models across all 7 baselined reasons:
     - `missing_attachment` (`HITL-RSN-001`)
     - `unreadable_document` (`HITL-RSN-002`)
     - `wrong_or_uncertain_document_type` (`HITL-RSN-003`)
     - `missing_required_value` (`HITL-RSN-004`)
     - `uncertain_result` (`HITL-RSN-005`)
     - `conflicting_candidate_values` (`HITL-RSN-006`)
     - `processing_or_provider_failure` (`HITL-RSN-007`)
  2. Embed affected document, field name, candidate values, and source evidence in issue payload.
- **Explicit Non-Goals**: Silently dropping unhandled error states.
- **Acceptance Criteria**: `HITL-RSN-001` through `HITL-RSN-007` pass cleanly.
- **Verification Commands**: `pytest tests/test_hitl.py -k "HITL-RSN" -v`
- **Expected Evidence**: Passing HITL escalation test suite.
- **Status**: `NOT_STARTED`

---

#### `T11-02`: Pipeline Orchestrator & Audit Record Store
- **Priority**: `P0`
- **Dependencies**: `T11-01`, `T10-03`, `T03-02`, `T04-02`, `T02-07`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §3, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3
- **Test References**: `PIPE-CMP-001` through `PIPE-CMP-006`, `FR-001`, `FR-002`, `FR-003`, `FR-004`
- **Current Gap**: `run_pipeline.py` emitted legacy `AuditOutputRecord` dicts.
- **Scope**: Implement `PipelineOrchestrator` in `src/pipeline/orchestrator.py` and `AuditStore` in `src/store/audit_store.py`.
- **Files Likely Affected**: `src/pipeline/orchestrator.py`, `src/store/audit_store.py`, `src/run_pipeline.py`
- **Implementation Requirements**:
  1. Integrate: Stage 1 (classify) $\rightarrow$ Stage 2 (roles) $\rightarrow$ Stage 3 (extract / reliability gate) $+$ Normalization $+$ Comparator $\rightarrow$ Stage 4 (escalate / review store).
  2. Non-comparison emails stop checking immediately; store `AuditRecord(state=COMPLETE, outcome=NOT_APPLICABLE)` (`FR-004`).
  3. Persist and index full `AuditRecord` objects with revision tracking (`revision = 1`).
  4. Update `src/run_pipeline.py` CLI to invoke new orchestrator.
- **Explicit Non-Goals**: Bypassing pipeline stage boundaries.
- **Acceptance Criteria**: Pipeline runs end-to-end on synthetic fixtures; emits fully compliant `AuditRecord` models.
- **Verification Commands**: `pytest tests/test_pipeline_orchestrator.py -v`
- **Expected Evidence**: Passing pipeline integration tests.
- **Status**: `NOT_STARTED`

---

#### `T12-01`: FastAPI Router Modernization & Schema Migration
- **Priority**: `P0`
- **Dependencies**: `T11-02`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §9, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §8
- **Test References**: `API-AUD-001`, `API-AUD-002`, `API-AUD-003`, `API-HLT-001`, `DEC-P03`
- **Current Gap**: `app.py` returned legacy schemas and had hardcoded scorecard stats.
- **Scope**: Refactor `app.py` and implement routers in `src/api/routes.py`.
- **Files Likely Affected**: `app.py`, `src/api/routes.py`, `src/api/__init__.py`
- **Implementation Requirements**:
  1. `GET /`: Return dynamic summary metrics matching `AuditStore` (zero hardcoded strings, `REG-003`).
  2. `GET /health`: Fast liveness probe returning HTTP 200 (`API-HLT-001`).
  3. `GET /audit`: Query filters by `state`, `category`, `outcome`, `has_discrepancy` (`API-AUD-001`).
  4. `GET /audit/{email_id}`: Full `AuditRecord` detail or HTTP 404 `ErrorResponse` (`API-AUD-002/003`).
- **Explicit Non-Goals**: Changing REST status codes or schema keys arbitrarily.
- **Acceptance Criteria**: `API-AUD-001`, `002`, `003`, `API-HLT-001` pass cleanly.
- **Verification Commands**: `pytest tests/test_api_endpoints.py -k "API-AUD or API-HLT" -v`
- **Expected Evidence**: Passing API endpoint tests.
- **Status**: `NOT_STARTED`

---

#### `T12-02`: Human Review Endpoint (`POST /audit/{email_id}/review`, `FR-016`)
- **Priority**: `P0`
- **Dependencies**: `T12-01`, `T04-01`, `T02-06`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §9.2, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7
- **Test References**: `API-REV-001`, `API-REV-003`, `HITL-REV-001`, `HITL-REV-002`, `HITL-REV-003`, `HITL-REV-004`, `HITL-REV-005`, `FR-016`
- **Current Gap**: `POST /audit/{id}/review` endpoint did not exist; review workflow was completely unbuilt.
- **Scope**: Implement review submission handler in `src/api/routes.py`.
- **Files Likely Affected**: `src/api/routes.py`, `src/hitl/review_service.py`
- **Implementation Requirements**:
  1. Ingest `ReviewUpdate` payload; reject malformed JSON or unknown fields with HTTP 422 (`API-REV-003`).
  2. Support category correction, role correction, and field correction (`HITL-REV-002/003/004`).
  3. Recompute comparisons deterministically upon correction; increment to `revision = N + 1` (`HITL-REV-002`).
  4. Reject direct modification of derived comparison booleans (`HITL-REV-001`, `REG-012`).
  5. `CONFIRM` action on unextracted field rejected or maintains `NEEDS_REVIEW` (`HITL-REV-005`).
- **Explicit Non-Goals**: Allowing reviewers to bypass deterministic comparator rules.
- **Acceptance Criteria**: `API-REV-001`, `API-REV-003`, `HITL-REV-001`–`005` pass cleanly.
- **Verification Commands**: `pytest tests/test_api_endpoints.py -k "API-REV or HITL-REV" -v`
- **Expected Evidence**: Passing review API tests.
- **Status**: `NOT_STARTED`

---

#### `T12-03`: Optimistic Revision Concurrency & HTTP 409 Collision Handler (`DC-07`)
- **Priority**: `P0`
- **Dependencies**: `T12-02`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §9.3, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7
- **Test References**: `API-REV-002`, `HITL-REV-006`, `DC-07`
- **Current Gap**: No concurrency locking or revision check existed.
- **Scope**: Implement optimistic concurrency verification in `src/store/audit_store.py` and API route.
- **Files Likely Affected**: `src/store/audit_store.py`, `src/api/routes.py`
- **Implementation Requirements**:
  1. Check `ReviewUpdate.expected_revision == current_record.revision`.
  2. If revision has advanced (e.g. expected 1, current is 2), abort transaction immediately.
  3. Return **HTTP 409 Conflict** with structured error: `{"code": "REVISION_CONFLICT", "current_revision": 2, "expected_revision": 1}` (`API-REV-002`, `HITL-REV-006`).
- **Explicit Non-Goals**: Allowing stale updates to overwrite newer revisions.
- **Acceptance Criteria**: `API-REV-002` and `HITL-REV-006` pass cleanly.
- **Verification Commands**: `pytest tests/test_api_endpoints.py -k "API-REV-002 or HITL-REV-006" -v`
- **Expected Evidence**: Passing concurrency conflict tests.
- **Status**: `NOT_STARTED`

---

#### `T12-04`: Legacy `POST /verify` Deprecation Adapter
- **Priority**: `P2`
- **Dependencies**: `T12-02`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §9
- **Test References**: Existing `test_dynamic_verify_endpoint` in `tests/test_api.py`
- **Current Gap**: `POST /verify` is not part of baselined REST API, but existing `test_api.py` tests it.
- **Scope**: Wrap `POST /verify` in `app.py` as a deprecated compatibility shim delegating to field comparator.
- **Files Likely Affected**: `app.py`
- **Implementation Requirements**:
  1. Route `POST /verify` calls through the new deterministic normalizer and comparator.
  2. Add `Deprecated` warning header in HTTP response.
  3. Preserve legacy tests passing without breaking CI.
- **Explicit Non-Goals**: Adding new features to `POST /verify`.
- **Acceptance Criteria**: Legacy `test_dynamic_verify_endpoint` passes; endpoint marked deprecated in OpenAPI spec.
- **Verification Commands**: `pytest tests/test_api.py -k test_dynamic_verify_endpoint -v`
- **Expected Evidence**: Legacy test green.
- **Status**: `NOT_STARTED`

---

### Wave 4: Evaluation Adapter & Safe Export

#### `T13-01`: Lossless Evaluation Adapter Schema Mapping (`DC-02`, `NFR-005`)
- **Priority**: `P0`
- **Dependencies**: `T11-02`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §5, [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §6
- **Test References**: `EVAL-MAP-001`, `EVAL-MAP-003`, `EVAL-MAP-004`, `EVAL-MAP-005`, `EVAL-MAP-006`, `NFR-005`
- **Current Gap**: `AuditOutputRecord.to_competition_dict()` had hardcoded defective mappings in `src/pipeline/schema.py`.
- **Scope**: Implement `src/adapters/evaluation_adapter.py`.
- **Files Likely Affected**: `src/adapters/evaluation_adapter.py`, `src/adapters/__init__.py`
- **Implementation Requirements**:
  1. Lossless mapping from internal categories to official strings:
     - `document_comparison` $\rightarrow$ `BL_COMPARISON`
     - `new_shipping_instruction` $\rightarrow$ `SI_REQUEST`
     - `invoice_query` $\rightarrow$ `INVOICE_QUERY`
     - `general` $\rightarrow$ `GENERAL`
     - `spam` $\rightarrow$ `SPAM`
  2. Verified 7-field defect names: `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, `gross_weight_kg` (`EVAL-MAP-005`).
  3. Clean match mapped to `status = "OK"`, `has_defect = false`, `defect_fields = []` (`EVAL-MAP-003`).
  4. Discrepancy mapped to `status = "MISMATCH"`, `has_defect = true`, sorted defect fields (`EVAL-MAP-004/006`).
- **Explicit Non-Goals**: Leaking official evaluation enums back into internal domain models.
- **Acceptance Criteria**: `EVAL-MAP-001`, `003`, `004`, `005`, `006` pass cleanly.
- **Verification Commands**: `pytest tests/test_evaluation_adapter.py -k "EVAL-MAP" -v`
- **Expected Evidence**: Passing evaluation adapter tests.
- **Status**: `NOT_STARTED`

---

#### `T13-02`: Safe Submission Export (`GET /submission`) with `EXPORT_BLOCKED` Enforcement (`DC-08`)
- **Priority**: `P0`
- **Dependencies**: `T13-01`, `T12-01`
- **Specification References**: [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §8, [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §9.4
- **Test References**: `API-EXP-001`, `API-EXP-002`, `EVAL-MAP-002`, `EVAL-MAP-007`, `DC-08`
- **Current Gap**: `GET /submission` served raw file without verifying if cases remained in `NEEDS_REVIEW`.
- **Scope**: Update `GET /submission` in `src/api/routes.py` and evaluation adapter.
- **Files Likely Affected**: `src/api/routes.py`, `src/adapters/evaluation_adapter.py`
- **Implementation Requirements**:
  1. Inspect batch: if 100% of cases are in `COMPLETE` state, return HTTP 200 with submission JSON matching official schema (`API-EXP-001`).
  2. **Safety Invariant (DC-08)**: If any case has `category = null` or state `NEEDS_REVIEW`, raise `ExportBlockedException`.
  3. Return **HTTP 409 Conflict** with payload:
     `{"code": "EXPORT_BLOCKED", "message": "Cannot export submission while cases remain in NEEDS_REVIEW", "blocking_emails": [...]}` (`API-EXP-002`, `EVAL-MAP-002/007`).
  4. Never invent fallback values (`has_defect = false`) to force export.
- **Explicit Non-Goals**: Fabricating default answers for unconfirmed records.
- **Acceptance Criteria**: `API-EXP-001` and `API-EXP-002` pass cleanly.
- **Verification Commands**: `pytest tests/test_evaluation_adapter.py -k "API-EXP" -v`
- **Expected Evidence**: Passing safe export tests.
- **Status**: `NOT_STARTED`

---

### Wave 5: Frontend Application & Review UX

#### `T14-01`: React + Vite + TypeScript + Tailwind Setup & Prototype Preservation
- **Priority**: `P1`
- **Dependencies**: `T12-01`
- **Specification References**: [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md) §8, [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §1, §9
- **Test References**: Build smoke tests
- **Current Gap**: No React application exists; only static prototype `docs/index.html`.
- **Scope**: Preserve the approved HTML visual prototype and initialize the frontend project in `frontend/` using approved stack: React + Vite + TypeScript + Tailwind CSS.
- **Files Likely Affected**: `docs/reference/ui_prototype.html`, `frontend/*`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`
- **Implementation Requirements**:
  1. **Preserve Approved Visual Prototype**: Copy `docs/index.html` to `docs/reference/ui_prototype.html` before any frontend changes. The approved HTML prototype is preserved as a permanent visual and interaction reference (`04_UI_UX_SPEC.md` = behavioral authority; `03_DATA_CONTRACTS.md` = data/API authority; HTML prototype = visual/interaction reference). The React production UI replaces the serving entry point, but does not overwrite or destroy the reference artifact.
  2. Scaffold React + Vite + TypeScript application in `frontend/`.
  3. Port visual theme from approved prototype: enterprise dark console (`bg-slate-900`, `bg-slate-950`), Inter + JetBrains Mono typography, status badge color schemes.
  4. Configure API client with environment-based proxy to FastAPI backend (`/api` $\rightarrow$ `http://localhost:10000`).
- **Explicit Non-Goals**: Overwriting the reference prototype or carrying over prototype-only hardcoded values (520, 21, 63, 0.0%).
- **Acceptance Criteria**: `docs/reference/ui_prototype.html` preserved; `npm run build` generates clean production bundle; static assets mountable by FastAPI.
- **Verification Commands**: `cd frontend && npm run build`
- **Expected Evidence**: Successful frontend build; preserved prototype file in `docs/reference/`.
- **Status**: `NOT_STARTED`

---

#### `T14-02`: OpenAPI-Generated TypeScript Contracts & Sync Validator (`UI-CT-001`)
- **Priority**: `P0`
- **Dependencies**: `T14-01`, `T12-01`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §8.2
- **Test References**: `UI-CT-001`
- **Current Gap**: High risk of contract drift between backend Pydantic models and frontend TypeScript interfaces.
- **Scope**: Implement OpenAPI-generated TypeScript API contracts and contract verification script.
- **Files Likely Affected**: `scripts/verify_contracts.py`, `frontend/src/types/api.ts`
- **Implementation Requirements**:
  1. **Implementation Decision**: Adopt OpenAPI-generated TypeScript API contracts as an implementation-level contract synchronization mechanism (not a source business requirement).
  2. Acknowledge that TypeScript types alone do not guarantee runtime contract synchronization; automated validation must verify the interface boundary against the live FastAPI OpenAPI schema.
  3. Export OpenAPI JSON from FastAPI application; generate and assert 1:1 synchronization with TypeScript interfaces (`AuditRecord`, `ReviewUpdate`, `FieldCorrection`, `FieldEvidence`, `ErrorResponse`). Do not lock a specific codegen library unless separately necessary.
  4. CI fails if frontend types drift from backend models.
- **Explicit Non-Goals**: Hand-crafting diverging frontend data models or claiming TypeScript alone guarantees runtime safety.
- **Acceptance Criteria**: `UI-CT-001` passes; automated contract validator exits code 0.
- **Verification Commands**: `python scripts/verify_contracts.py`
- **Expected Evidence**: Contract sync confirmed with 0 drift.
- **Status**: `NOT_STARTED`

---

#### `T15-01`: Case Queue Grid View (`/cases`, Dynamic KPIs, Filters, States)
- **Priority**: `P1`
- **Dependencies**: `T14-02`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §2
- **Test References**: `UI-GRID-001`, `UI-BADGE-001`
- **Current Gap**: Prototype used static in-memory array and hardcoded KPI counts.
- **Scope**: Implement `<CaseQueueGrid />`, `<OutcomeBadge />`, and `<KPICard />` in `frontend/src/views/CaseQueueView.tsx`.
- **Files Likely Affected**: `frontend/src/views/CaseQueueView.tsx`, `frontend/src/components/*`
- **Implementation Requirements**:
  1. Dynamic KPI strip calculating live counts from `/audit` records (total, mismatches, needs review, complete).
  2. Filter tabs: All, Needs Review, Mismatches, Match OK, Non-Comparison.
  3. Search input filtering email ID, category, or notes.
  4. Non-color cues on badges: icons (checkmark, alert triangle, clock) alongside text labels (`UI-BADGE-001`).
  5. Loading skeleton, empty state, and API error banners (`UI-GRID-001`).
- **Explicit Non-Goals**: Hardcoding KPI counts.
- **Acceptance Criteria**: `UI-GRID-001` and `UI-BADGE-001` pass component tests.
- **Verification Commands**: `cd frontend && npm run test`
- **Expected Evidence**: Passing Vitest component tests.
- **Status**: `NOT_STARTED`

---

#### `T15-02`: Four-Column Comparison Matrix Component (`<ComparisonMatrix />`)
- **Priority**: `P0`
- **Dependencies**: `T15-01`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §3
- **Test References**: `UI-DIFF-001`, `UI-DIFF-002`
- **Current Gap**: Prototype showed raw JSON inside a modal instead of a 4-column diff matrix.
- **Scope**: Implement `<ComparisonMatrix />` in `frontend/src/components/ComparisonMatrix.tsx`.
- **Files Likely Affected**: `frontend/src/components/ComparisonMatrix.tsx`
- **Implementation Requirements**:
  1. Render 4 explicit columns: `Field`, `Shipping Instruction (SI)`, `Draft Bill of Lading (BL)`, `Outcome / Result`.
  2. Always display all 7 mandatory fields; never hide rows (`UI-DIFF-001`).
  3. Render raw value beneath normalized value in muted font.
  4. Missing field rendered as `[Not Found in Document]` with amber `UNRESOLVED` badge (`UI-DIFF-002`).
  5. "View Evidence" button linking to drawer for each field.
- **Explicit Non-Goals**: Full split-screen document rendering (future scope).
- **Acceptance Criteria**: `UI-DIFF-001` and `UI-DIFF-002` pass component tests.
- **Verification Commands**: `cd frontend && npm run test -- ComparisonMatrix`
- **Expected Evidence**: Passing diff matrix component tests.
- **Status**: `NOT_STARTED`

---

#### `T15-03`: Source Evidence Side Drawer (`<EvidenceDrawer />`)
- **Priority**: `P1`
- **Dependencies**: `T15-02`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §5
- **Test References**: `UI-DRW-001`
- **Current Gap**: Prototype had no evidence viewing mechanism.
- **Scope**: Implement `<EvidenceDrawer />` in `frontend/src/components/EvidenceDrawer.tsx`.
- **Files Likely Affected**: `frontend/src/components/EvidenceDrawer.tsx`
- **Implementation Requirements**:
  1. Slides out over right viewport when triggered from a matrix row or issue card.
  2. Renders verbatim quote snippet, source document filename, and location metadata (page/cell/line).
  3. Close via Escape key, overlay click, or close button.
  4. Strictly prohibits rendering hidden prompts, internal chain-of-thought, or secrets (`SEC-LEAK-001`).
- **Explicit Non-Goals**: Displaying raw LLM completion tokens or system instructions.
- **Acceptance Criteria**: `UI-DRW-001` passes component tests.
- **Verification Commands**: `cd frontend && npm run test -- EvidenceDrawer`
- **Expected Evidence**: Passing evidence drawer tests.
- **Status**: `NOT_STARTED`

---

#### `T15-04`: Dedicated Review Workspace Route (`/cases/:email_id/review`)
- **Priority**: `P0`
- **Dependencies**: `T15-02`, `T15-03`, `T12-02`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §4
- **Test References**: `UI-REV-001`, `UI-REV-002`, `E2E-009`
- **Current Gap**: Review route did not exist; review workflow was completely unbuilt.
- **Scope**: Implement `ReviewWorkspaceView` in `frontend/src/views/ReviewWorkspaceView.tsx`.
- **Files Likely Affected**: `frontend/src/views/ReviewWorkspaceView.tsx`, `frontend/src/components/ReviewControls.tsx`
- **Implementation Requirements**:
  1. Dedicated route mounted at `/cases/:email_id/review` (`UI-REV-001`).
  2. Two-panel operational layout: left panel preserves the 4-column matrix showing reliable fields; right panel renders active review issues and targeted correction tabs.
  3. Humanized review reason copy (e.g. `"Conflicting values found"` instead of `conflicting_candidate_values`, `UI-REV-002`).
  4. Targeted correction forms: Category, Attachment Roles, Field Values.
  5. Submission sends `ReviewUpdate` to backend; disables manual boolean overrides.
- **Explicit Non-Goals**: Single modal or drawer as the primary container for the complete review workflow.
- **Acceptance Criteria**: `UI-REV-001` and `UI-REV-002` pass integration tests.
- **Verification Commands**: `cd frontend && npm run test -- ReviewWorkspace`
- **Expected Evidence**: Passing review workspace tests.
- **Status**: `NOT_STARTED`

---

#### `T15-05`: Revision Collision Conflict Modal (`UI-REV-003`)
- **Priority**: `P0`
- **Dependencies**: `T15-04`, `T12-03`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §6, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7
- **Test References**: `UI-REV-003`, `E2E-012`
- **Current Gap**: Zero conflict handling on frontend; potential data loss on concurrent edits.
- **Scope**: Implement `<ConflictModal />` in `frontend/src/components/ConflictModal.tsx`.
- **Files Likely Affected**: `frontend/src/components/ConflictModal.tsx`, `frontend/src/views/ReviewWorkspaceView.tsx`
- **Implementation Requirements**:
  1. Intercept HTTP 409 Conflict responses from `POST /audit/{email_id}/review`.
  2. Open in-place conflict alert modal explaining another user saved changes.
  3. Preserves operator's unsubmitted form values in component state.
  4. Actions: "Reload Latest Server Version" and "Review Differences".
  5. Never silently overwrite newer revisions or automatically resubmit stale data.
- **Explicit Non-Goals**: Silent auto-merging without operator awareness.
- **Acceptance Criteria**: `UI-REV-003` passes frontend test simulating HTTP 409.
- **Verification Commands**: `cd frontend && npm run test -- ConflictModal`
- **Expected Evidence**: Passing conflict modal tests.
- **Status**: `NOT_STARTED`

---

#### `T15-06`: Safe Export Blocked Modal & Download Flow (`UI-EXP-001`)
- **Priority**: `P0`
- **Dependencies**: `T15-01`, `T13-02`
- **Specification References**: [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §8, [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §8
- **Test References**: `UI-EXP-001`, `E2E-016`
- **Current Gap**: Prototype provided direct links to static submission file without checking review status.
- **Scope**: Implement `<ExportModal />` in `frontend/src/components/ExportModal.tsx`.
- **Files Likely Affected**: `frontend/src/components/ExportModal.tsx`, `frontend/src/views/CaseQueueView.tsx`
- **Implementation Requirements**:
  1. "Export Submission" button calls `GET /submission`.
  2. If HTTP 200, triggers file download of `submission.json`.
  3. If HTTP 409 `EXPORT_BLOCKED`, renders diagnostic modal displaying the safety invariant (DC-08) and listing blocking email IDs with click-to-resolve links (`UI-EXP-001`).
- **Explicit Non-Goals**: Allowing download of fabricated default values.
- **Acceptance Criteria**: `UI-EXP-001` passes test asserting blocked modal rendering.
- **Verification Commands**: `cd frontend && npm run test -- ExportModal`
- **Expected Evidence**: Passing export modal tests.
- **Status**: `NOT_STARTED`

---

### Wave 6: Verification, Regression, Security, Observability & UAT

#### `T16-01`: Complete Regression Test Suite Automation (`REG-001`–`REG-012`)
- **Priority**: `P0`
- **Dependencies**: `T13-02`, `T12-03`, `T10-03`, `T04-02`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §21
- **Test References**: `REG-001` through `REG-012`
- **Current Gap**: Zero automated regression suite protecting against historical traps.
- **Scope**: Implement `tests/test_regression_suite.py`.
- **Files Likely Affected**: `tests/test_regression_suite.py`
- **Implementation Requirements**:
  1. Implement automated test for all 12 regression specifications:
     - `REG-001`: 0 attachments MUST NOT force non-comparison.
     - `REG-002`: AST scan verifying zero `if email_id == "email_xxx":` branches in `src/`.
     - `REG-003`: Dynamic metrics check (zero hardcoded `520`, `21`, `63`, `0.0%`).
     - `REG-004`: No undocumented $\pm 1\text{ kg}$ tolerance.
     - `REG-005`: No broad company suffix stripping.
     - `REG-006`: No automatic port alias equivalence.
     - `REG-007`: No fixed character count OCR trigger.
     - `REG-008`: Validated fallback output prevents unnecessary HITL.
     - `REG-009`: Reliable partial work preserved during escalation.
     - `REG-010`: Unresolved comparison never emits `"No mismatch detected"`.
     - `REG-011`: Confidence score does not bypass evidence verification.
     - `REG-012`: Direct boolean edit on `mismatch_detected` rejected.
- **Explicit Non-Goals**: Skipping any of the 12 regression checks.
- **Acceptance Criteria**: All 12 regression tests pass 100%.
- **Verification Commands**: `pytest tests/test_regression_suite.py -v`
- **Expected Evidence**: 12 passed regression tests.
- **Status**: `NOT_STARTED`

---

#### `T16-02A`: E2E Classification & Non-Comparison Lifecycle (`E2E-001`)
- **Priority**: `P0`
- **Dependencies**: `T16-01`, `T15-01`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §19 (`E2E-001`), [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §3.1
- **Test References**: `E2E-001`
- **Current Gap**: No automated end-to-end journey tests for non-comparison emails.
- **Scope**: Implement E2E test for non-comparison email ingestion, classification, bypass, and UI queue visibility in `tests/e2e/test_e2e_classification.py`.
- **Files Likely Affected**: `tests/e2e/test_e2e_classification.py`
- **Implementation Requirements**:
  1. Ingest email $\rightarrow$ classify as `invoice_query` $\rightarrow$ halt verification $\rightarrow$ mark `COMPLETE`/`NOT_APPLICABLE` $\rightarrow$ verify display in queue $\rightarrow$ export maps to `INVOICE_QUERY`.
  2. Independently executable and diagnosable scenario.
- **Explicit Non-Goals**: Coupling with multi-field document comparison logic.
- **Acceptance Criteria**: `E2E-001` passes independently.
- **Verification Commands**: `pytest tests/e2e/test_e2e_classification.py -k E2E-001 -v`
- **Expected Evidence**: Passing E2E test log.
- **Status**: `NOT_STARTED`

---

#### `T16-02B`: E2E Deterministic SI/BL Comparison Lifecycle (`E2E-002`, `E2E-003`, `E2E-004`)
- **Priority**: `P0`
- **Dependencies**: `T16-02A`, `T15-02`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §19 (`E2E-002`, `E2E-003`, `E2E-004`)
- **Test References**: `E2E-002`, `E2E-003`, `E2E-004`
- **Current Gap**: No automated E2E tests for clean match, single mismatch, or multiple field mismatches.
- **Scope**: Implement E2E tests in `tests/e2e/test_e2e_comparison.py`.
- **Files Likely Affected**: `tests/e2e/test_e2e_comparison.py`
- **Implementation Requirements**:
  1. `E2E-002`: Clean SI/BL match across all 7 fields $\rightarrow$ `COMPLETE`/`MATCH` $\rightarrow$ clean UI scorecard.
  2. `E2E-003`: Single mismatch (`container_count`) $\rightarrow$ `COMPLETE`/`MISMATCH` $\rightarrow$ rose diff row $\rightarrow$ export `defect_fields = ["container_count"]`.
  3. `E2E-004`: Multiple mismatches (`shipper` & `gross_weight_kg`) $\rightarrow$ side-by-side diff rows $\rightarrow$ evidence links intact.
- **Explicit Non-Goals**: Combining with human review workflows.
- **Acceptance Criteria**: `E2E-002`, `E2E-003`, `E2E-004` pass independently.
- **Verification Commands**: `pytest tests/e2e/test_e2e_comparison.py -v`
- **Expected Evidence**: Passing E2E comparison suite.
- **Status**: `NOT_STARTED`

---

#### `T16-02C`: E2E OCR Recovery & HITL Escalation Lifecycle (`E2E-005`–`008`, `E2E-013`, `E2E-014`)
- **Priority**: `P0`
- **Dependencies**: `T16-02A`, `T06-01`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §19 (`E2E-005` through `E2E-008`, `E2E-013`, `E2E-014`)
- **Test References**: `E2E-005`, `E2E-006`, `E2E-007`, `E2E-008`, `E2E-013`, `E2E-014`
- **Current Gap**: No automated E2E tests for missing attachments, scan OCR recovery, or conflicting values.
- **Scope**: Implement E2E tests in `tests/e2e/test_e2e_hitl_escalation.py`.
- **Files Likely Affected**: `tests/e2e/test_e2e_hitl_escalation.py`
- **Implementation Requirements**:
  1. `E2E-005`: Comparison missing BL $\rightarrow$ Stage 1: `document_comparison` $\rightarrow$ Stage 2 flags missing attachment $\rightarrow$ HITL: `missing_attachment`.
  2. `E2E-006`: Image-only PDF BL $\rightarrow$ OCR recovery $\rightarrow$ all 7 fields resolved $\rightarrow$ compared successfully.
  3. `E2E-007`: Degraded scan OCR failure $\rightarrow$ HITL: `unreadable_document` $\rightarrow$ partial results preserved.
  4. `E2E-008`: Conflicting gross weights $\rightarrow$ HITL: `conflicting_candidate_values`.
  5. `E2E-013`: Provider outage with validated fallback $\rightarrow$ pipeline continues without human escalation.
  6. `E2E-014`: Provider outage and fallback exhaustion $\rightarrow$ HITL: `processing_or_provider_failure`.
- **Explicit Non-Goals**: Conflating OCR escalation with manual review submission.
- **Acceptance Criteria**: `E2E-005`, `006`, `007`, `008`, `013`, `014` pass independently.
- **Verification Commands**: `pytest tests/e2e/test_e2e_hitl_escalation.py -v`
- **Expected Evidence**: Passing HITL escalation E2E tests.
- **Status**: `NOT_STARTED`

---

#### `T16-02D`: E2E Human Review Correction & Concurrency Lifecycle (`E2E-009`–`E2E-012`)
- **Priority**: `P0`
- **Dependencies**: `T16-02C`, `T15-04`, `T15-05`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §19 (`E2E-009` through `E2E-012`), [`specs/04_UI_UX_SPEC.md`](04_UI_UX_SPEC.md) §4, §6
- **Test References**: `E2E-009`, `E2E-010`, `E2E-011`, `E2E-012`
- **Current Gap**: No automated E2E tests verifying the full operator correction cycle or HTTP 409 conflict handling.
- **Scope**: Implement E2E review tests in `tests/e2e/test_e2e_review.py`.
- **Files Likely Affected**: `tests/e2e/test_e2e_review.py`
- **Implementation Requirements**:
  1. `E2E-009`: Operator opens review route $\rightarrow$ corrects conflicting gross weight $\rightarrow$ submits `ReviewUpdate` $\rightarrow$ re-normalizes $\rightarrow$ re-matches $\rightarrow$ `revision = 2` $\rightarrow$ `COMPLETE`.
  2. `E2E-010`: Case in HITL with `category = null` $\rightarrow$ operator selects `document_comparison` $\rightarrow$ pipeline completes Stages 2–4.
  3. `E2E-011`: Operator resolves ambiguous document roles $\rightarrow$ pipeline extracts from assigned roles.
  4. `E2E-012`: Concurrency collision $\rightarrow$ Operator A submits with stale revision $\rightarrow$ HTTP 409 $\rightarrow$ conflict modal preserves inputs.
- **Explicit Non-Goals**: Allowing direct boolean editing without comparator recomputation.
- **Acceptance Criteria**: `E2E-009`, `010`, `011`, `012` pass independently.
- **Verification Commands**: `pytest tests/e2e/test_e2e_review.py -v`
- **Expected Evidence**: Passing review lifecycle E2E tests.
- **Status**: `NOT_STARTED`

---

#### `T16-02E`: E2E Evaluation Adapter & Safe Export Lifecycle (`E2E-015`, `E2E-016`)
- **Priority**: `P0`
- **Dependencies**: `T16-02D`, `T15-06`, `T13-02`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §19 (`E2E-015`, `E2E-016`), [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §8
- **Test References**: `E2E-015`, `E2E-016`
- **Current Gap**: No automated E2E tests for submission export readiness or `EXPORT_BLOCKED` modal flow.
- **Scope**: Implement E2E export tests in `tests/e2e/test_e2e_export.py`.
- **Files Likely Affected**: `tests/e2e/test_e2e_export.py`
- **Implementation Requirements**:
  1. `E2E-015`: All batch cases `COMPLETE` $\rightarrow$ `GET /submission` $\rightarrow$ generates valid `submission.json` matching official schema.
  2. `E2E-016`: 1 case in `NEEDS_REVIEW` $\rightarrow$ `GET /submission` blocked with HTTP 409 `EXPORT_BLOCKED` $\rightarrow$ UI modal displays blocking case IDs.
- **Explicit Non-Goals**: Fabricating default answers to force export.
- **Acceptance Criteria**: `E2E-015` and `E2E-016` pass independently.
- **Verification Commands**: `pytest tests/e2e/test_e2e_export.py -v`
- **Expected Evidence**: Passing export lifecycle E2E tests.
- **Status**: `NOT_STARTED`

---

#### `T16-03`: Security & Data Integrity Audit Automation
- **Priority**: `P0`
- **Dependencies**: `T16-02A`, `T16-02B`, `T16-02C`, `T16-02D`, `T16-02E`
- **Specification References**: [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §7, [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §17
- **Test References**: `SEC-DATA-001`, `SEC-AUTH-001`, `SEC-LEAK-001`, `SEC-PATH-001`, `SEC-INTEG-001`
- **Current Gap**: No automated verification of bundle immutability, path traversal defense, or credential protection.
- **Scope**: Implement `tests/test_security_integrity.py`.
- **Files Likely Affected**: `tests/test_security_integrity.py`
- **Implementation Requirements**:
  1. `SEC-DATA-001`: Compute SHA256 hashes of `sdoc-hackathon-bundle/` files before and after tests; assert 100% immutability.
  2. `SEC-AUTH-001`: Assert API keys are absent from all API responses and logs.
  3. `SEC-LEAK-001`: Assert chain-of-thought and system prompts are excluded from API payloads.
  4. `SEC-PATH-001`: Assert directory traversal attempts (`../../etc/passwd`) are rejected with HTTP 400.
  5. `SEC-INTEG-001`: AST scan asserting no benchmark lookup tables exist in codebase.
- **Explicit Non-Goals**: Modifying files in `sdoc-hackathon-bundle/`.
- **Acceptance Criteria**: All security audit tests pass cleanly.
- **Verification Commands**: `pytest tests/test_security_integrity.py -v`
- **Expected Evidence**: Passing security audit logs.
- **Status**: `NOT_STARTED`

---

#### `T16-04`: Performance Observability Instrumentation (`PERF-001`–`PERF-007`)
- **Priority**: `P2`
- **Dependencies**: `T16-02A`, `T16-02B`, `T16-02C`, `T16-02D`, `T16-02E`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §18, [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) §4
- **Test References**: `PERF-001` through `PERF-007`
- **Current Gap**: Zero latency or throughput metrics collected.
- **Scope**: Instrument timing middleware in `src/api/middleware.py` and benchmark runner in `scripts/measure_benchmarks.py`.
- **Files Likely Affected**: `src/api/middleware.py`, `scripts/measure_benchmarks.py`
- **Implementation Requirements**:
  1. Record latencies for `GET /audit`, `GET /audit/{id}`, `POST /audit/{id}/review`, and parser throughput.
  2. Measure AI call avoidance rate (% of clean cases resolved deterministically).
  3. **Strict Invariant**: Report all metrics as `TBD / OBSERVATIONAL BASELINE`. Do **NOT** fail CI on numeric thresholds.
- **Explicit Non-Goals**: Inventing SLA targets or failing builds on latency.
- **Acceptance Criteria**: Benchmark script runs and emits formatted performance summary report.
- **Verification Commands**: `python scripts/measure_benchmarks.py`
- **Expected Evidence**: Observational latency report artifact.
- **Status**: `NOT_STARTED`

---

#### `T16-05`: Manual User Acceptance Testing (UAT) Qualification Checklist
- **Priority**: `P1`
- **Dependencies**: `T15-06`, `T16-02A`, `T16-02B`, `T16-02C`, `T16-02D`, `T16-02E`
- **Specification References**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md) §20
- **Test References**: `UAT-001` through `UAT-009`
- **Current Gap**: No operational qualification protocol for deployment readiness.
- **Scope**: Execute manual inspection checklist covering operational usability and discrepancy clarity.
- **Files Likely Affected**: `docs/UAT_REPORT_FINAL.md`
- **Implementation Requirements**:
  1. Verify `UAT-001`: Mismatched fields identified quickly via rose diff rows in 4-column matrix.
  2. Verify `UAT-002`: Verbatim quote evidence directly accessible via side drawer.
  3. Verify `UAT-003`: Non-color discrimination verified across badges.
  4. Verify `UAT-004`: Humanized review explanation copy verified.
  5. Verify `UAT-005`: Targeted correction tabs verify partial work preservation.
  6. Verify `UAT-006`: Continuous context preserved in left review panel.
  7. Verify `UAT-007`: Correction recomputation updates case cleanly.
  8. Verify `UAT-008`: In-place revision collision modal verified.
  9. Verify `UAT-009`: Actionable export blocked dialog verified.
- **Explicit Non-Goals**: Measuring subjective timing or mouse-click quotas.
- **Acceptance Criteria**: All 9 UAT operational criteria signed off as Pass in `docs/UAT_REPORT_FINAL.md`.
- **Verification Commands**: Manual review walkthrough per protocol.
- **Expected Evidence**: Signed-off UAT documentation artifact.
- **Status**: `NOT_STARTED`

---

## 6. Implementation Sequences

### 6.1 Backend Implementation Sequence
$$\text{T00-01/02} \longrightarrow \text{T01-01} \dots \text{04} \longrightarrow \text{T02-01} \dots \text{08} \longrightarrow \text{T03-01} \dots \text{03} \longrightarrow \text{T04-01/02} \longrightarrow \text{T11-01/02} \longrightarrow \text{T12-01} \dots \text{04}$$

### 6.2 AI & Parser Implementation Sequence
$$\text{T05-01} \longrightarrow \text{T05-02} \longrightarrow \text{T05-03} \longrightarrow \text{T06-01/02} \longrightarrow \text{T07-01} \dots \text{04} \longrightarrow \text{T08-01} \dots \text{03} \longrightarrow \text{T09-01/02} \longrightarrow \text{T10-01} \dots \text{03}$$

### 6.3 HITL & Review Implementation Sequence
$$\text{T02-06} \longrightarrow \text{T10-03} \longrightarrow \text{T11-01} \longrightarrow \text{T11-02} \longrightarrow \text{T12-02} \longrightarrow \text{T12-03}$$

### 6.4 Evaluation Adapter Sequence
$$\text{T02-07} \longrightarrow \text{T11-02} \longrightarrow \text{T13-01} \longrightarrow \text{T13-02}$$

### 6.5 Frontend Implementation Sequence
$$\text{T12-01/02} \longrightarrow \text{T14-01} \longrightarrow \text{T14-02} \longrightarrow \text{T15-01} \longrightarrow \text{T15-02} \longrightarrow \text{T15-03} \longrightarrow \text{T15-04} \longrightarrow \text{T15-05} \longrightarrow \text{T15-06}$$

### 6.6 Test, Regression & E2E Sequence
$$\text{T01 Fixtures} \longrightarrow \text{T02-08 Contract Tests} \longrightarrow \text{Unit/Module Tests} \longrightarrow \text{T16-01 Regression} \longrightarrow \text{T16-02A}\dots\text{E (E2E)} \longrightarrow \text{T16-03 Security} \longrightarrow \text{T16-04 Perf} \longrightarrow \text{T16-05 UAT}$$

---

## 7. Known Blockers, High-Impact Risks & Safeguards

### 7.1 Tasks Sensitive to Business TBDs
- **`T03-03`**, **`T04-01`**, **`T16-01`**:
  - `DEC-P06C` (Port Semantic Equivalence): Current baseline requires exact match after approved normalization.
  - `DEC-P06D` (Organization Name Equivalence): Current baseline requires exact equality after currently approved normalization without broad suffix stripping.
  - `DEC-P06E` (Gross Weight Tolerance): Current baseline requires exact Decimal equality without numeric tolerance.
  - *Governance Guardrail*: If testing or domain inspection suggests relaxing any of these three rules, tasks **MUST NOT** resolve them autonomously. They remain strict baseline rules until the human engineer formally approves a specification amendment. Planned regression/CI guards will block unapproved relaxation once the corresponding implementation tasks are completed.

### 7.2 High-Impact Migration Risks & Safeguards
1. **Contract Drift between Backend and Frontend**:
   - *Risk*: Frontend TypeScript types diverge from FastAPI Pydantic v2 models, causing runtime rendering failures.
   - *Safeguard*: `T14-02` introduces OpenAPI-generated TypeScript contracts and automated CI verification (`scripts/verify_contracts.py`).
2. **Premature Evaluation Export (`EXPORT_BLOCKED`)**:
   - *Risk*: System emits default `has_defect = false` when cases require human review, incurring competition scoring penalties.
   - *Safeguard*: `T13-02` enforces HTTP 409 `EXPORT_BLOCKED` at the API level (Safety Invariant DC-08).
3. **Optimistic Revision Collisions**:
   - *Risk*: Reviewer A overwrites Reviewer B's simultaneous corrections.
   - *Safeguard*: `T12-03` and `T15-05` implement `expected_revision` locking with in-place conflict preservation.
4. **Evaluation Dataset Mutation**:
   - *Risk*: Test scripts inadvertently alter files in `sdoc-hackathon-bundle/`.
   - *Safeguard*: `T16-03` audits bundle hashes; all automated tests execute strictly against `tests/fixtures/`.

---

## 8. Definition of Project Completion (Done Gate)

Implementation is complete **ONLY** when:
1. All 51 P0 tasks and all 8 P1 tasks are marked `DONE`.
2. 100% pass across all required deterministic suites and required manual/UAT exit criteria. (Optional live-provider tests are not authoritative completion gates).
3. Strict Pydantic v2 data contracts are enforced across all internal stages and public APIs.
4. Human review recomputation and optimistic concurrency locking are operational.
5. Safe `EXPORT_BLOCKED` behavior is verified.
6. All 12 regression tests (`REG-001` through `REG-012`) pass without failure.
7. React frontend provides dedicated review route (`/cases/:id/review`), 4-column matrix, and evidence drawer.
8. Zero files in `sdoc-hackathon-bundle/` were modified or deleted.
9. All 9 operational UAT criteria are verified and signed off.
