# 05_TEST_PLAN.md — Verification & Testing Plan

> **Status**: Approved  
> **Implements**: [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md), [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md)

---

## 1. Test Suite Architecture

All automated tests are executed via `pytest` under `tests/`:

```bash
python -m pytest tests -v
```

---

## 2. Test Matrix & Coverage

### Suite 1: Document Parsers (`tests/test_parsers.py`)
- `test_text_parser`: Verifies plain text extraction from `email_001_SI.txt`.
- `test_excel_parser`: Verifies tabular extraction from `email_005_SI.xlsx`.
- `test_docx_parser`: Verifies table & paragraph extraction from `.docx` files.
- `test_pdf_parser_valid`: Verifies text extraction on valid PDF (`email_059_SI.pdf`).
- `test_pdf_parser_corrupted`: Verifies detection of stream truncation on `email_511_BL.pdf` (`is_corrupted: true`).

### Suite 2: Pipeline Stages & Governance (`tests/test_pipeline.py`)
- `test_classification_heuristics`: Validates Stage 1 categorization for `BL_COMPARISON`, `INVOICE_QUERY`, `SI_REQUEST`, `SPAM`.
- `test_stage2_missing_attachment`: Verifies HITL escalation on single-attachment email (`email_507` $\rightarrow$ `missing_attachment`).
- `test_stage2_corrupted_pdf`: Verifies HITL escalation on corrupt PDF (`email_511` $\rightarrow$ `unreadable`).
- `test_stage3_matching_pair`: Verifies zero false alarm on matching pair (`email_001` $\rightarrow$ `"No mismatch detected"`).
- `test_stage3_discrepancy_pair`: Verifies discrepancy capture on `email_025` (`container_count` SI: 6 / BL: 5).
- `test_validator`: Verifies schema compliance against `sample_submission.json`.

### Suite 3: REST API & Render Deployment (`tests/test_api.py`)
- `test_root_endpoint`: Tests `GET /` service metadata.
- `test_health_endpoint`: Tests `GET /health` probe (200 OK).
- `test_get_single_audit_ok`: Tests `GET /audit/email_001`.
- `test_get_single_audit_mismatch`: Tests `GET /audit/email_025`.
- `test_dynamic_verify_endpoint`: Tests `POST /verify` dynamic audit across all 7 fields with unit normalization (MT to KG, "Three (3)" to 3).

---

## 3. Regression & Continuous Verification

1. **Schema Validation Assertion**:
   Every pipeline execution automatically validates output against `sample_submission.json` (asserts 520 keys, exact field types, valid status strings).
2. **Deterministic Fallback**:
   Tests must pass 100% offline with zero external API dependencies.
