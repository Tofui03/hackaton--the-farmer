# Synthetic AI Adapter Response & Fault Injection Fixtures (`tests/fixtures/ai/`)

This directory contains deterministic, provider-neutral synthetic AI responses, malformed JSON streams, schema violations, technical failure descriptors, retry sequence models, and fallback scenarios.

These fixtures support offline testing of `BaseAIAdapter`, structured-output schema validation, technical retries, semantic self-correction repairs, and reliability gatekeeping without reliance on live external APIs.

---

## 1. Directory Structure

```text
tests/fixtures/ai/
├── manifest.json                     # Complete metadata catalogue and mapping
├── README.md                         # Documentation & fixture governance
├── classification/
│   ├── valid/                        # 7 valid intent classification responses
│   └── invalid/                      # 4 schema violations & leaked evaluation enums
├── role_resolution/
│   ├── valid/                        # 3 clean role identification responses
│   └── ambiguous/                    # 4 ambiguous / conflicting / missing role cases
├── extraction/
│   ├── valid/                        # 4 full and partial 7-field extractions
│   ├── ungrounded/                   # 2 hallucinated / ungrounded evidence cases
│   ├── conflicting/                  # 1 conflicting candidate values case
│   └── invalid_schema/               # 4 type mismatches & structural contract violations
├── ocr/
│   ├── valid/                        # 2 raster scan field recoveries
│   └── failures/                     # 2 illegible stains & ambiguous readings
├── failures/
│   ├── technical/                    # 7 provider-neutral network & service faults
│   └── syntax/                       # 3 malformed & truncated raw JSON streams
├── retry_sequences/                  # 5 bounded retry sequence scenarios
├── fallbacks/                        # 3 stage-specific fallback scenarios
└── provider_specific/
    └── gemini/                       # Implementation-specific wire format reference
```

### Fixture Taxonomy & Counts Summary (Single Source of Truth: `manifest.json`)
- **Atomic Fixtures**: 43 (16 valid responses + 8 invalid schema + 9 semantic failures + 7 technical faults + 3 syntax faults)
- **Provider-Specific Wire Reference**: 2
- **Retry Sequences**: 5 (`TECH-SEQ-001/002`, `SEM-SEQ-001/002`, `NESTED-SEQ-001`)
- **Fallback Scenarios**: 3 (`fb_stage1_heuristic_success`, `fb_stage3_deterministic_success`, `fb_exhausted_hitl_escalation`)
- **Total Fixture Payloads**: 53 (50 valid JSON + 3 malformed raw text)
- **Metadata Files**: 3 (`ai/manifest.json`, `ai/README.md`, `gemini/README.md`)
- **Generator / Validator Scripts**: 2 (`generate_ai_fixtures.py`, `validate_ai_fixtures.py`)
- **Total Filesystem Files**: 58

---

## 2. Core Governance Principles

### 2.1 Perception vs. Deterministic Truth
- **AI Role**: Perception, unstructured text parsing, OCR interpretation, candidate proposal, and source evidence citation.
- **Software Role**: Schema validation, exact token/decimal comparison (`==`, `!=`), unit conversion (`MT` $\rightarrow$ `kg`), discrepancy detection, and final business truth.
- **Guardrail**: AI fixtures NEVER assert final discrepancy truth (`mismatch_detected`, `MATCH`, `MISMATCH`).

### 2.2 Canonical Internal Enums
All internal pipeline fixtures strictly use canonical snake_case categories:
- `document_comparison`
- `new_shipping_instruction`
- `invoice_query`
- `general`
- `spam`
*(or `null` when context is ambiguous).*

Evaluation uppercase enums (`BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`) are strictly isolated to evaluation-adapter translation and must trigger schema validation rejection if leaked into internal contracts.

### 2.3 Strict LogicalReason Guardrail
Downstream review escalations map strictly to one of the seven baselined `LogicalReason` values:
1. `missing_attachment`
2. `unreadable_document`
3. `wrong_or_uncertain_document_type`
4. `missing_required_value`
5. `uncertain_result`
6. `conflicting_candidate_values`
7. `processing_or_provider_failure`

Unapproved reasons (`low_confidence`, `parse_failed`, `ai_failed`, `unknown_error`) are strictly prohibited.

### 2.4 Diagnostic-Only Confidence
Model self-confidence (`HIGH`, `MEDIUM`, `LOW` or float scores) is purely diagnostic. High confidence NEVER bypasses schema validation, evidence grounding, or reliability gate checks.

### 2.5 Bounded Retry Budgets
- `technical_attempt_limit = 3` (HTTP 429, 503, timeouts; exponential backoff).
- `semantic_attempt_limit = 2` (Malformed JSON, schema error; re-prompting).
- `nested_total_invocation_cap = 6` (Strict upper bound across sequential retries).

---

## 3. Fixture Inventory

### 3.1 Classification Fixtures
| Fixture ID | Category | Valid Schema | Expected Downstream Escalation | Test Focus |
|---|---|:---:|:---:|---|
| `cls_valid_doc_comparison` | `document_comparison` | YES | None | Standard clean comparison intent |
| `cls_valid_doc_comparison_zero_attachments` | `document_comparison` | YES | `missing_attachment` | 0-attachment email; intent preserved independently |
| `cls_valid_new_si` | `new_shipping_instruction` | YES | None | Inbound new SI submission |
| `cls_valid_invoice_query` | `invoice_query` | YES | None | Freight invoice dispute inquiry |
| `cls_valid_general` | `general` | YES | None | General terminal hours question |
| `cls_valid_spam` | `spam` | YES | None | Unsolicited promotional marketing |
| `cls_valid_unresolved_null` | `null` | YES | `uncertain_result` | Vague body; unresolved intent routes to HITL |
| `cls_invalid_eval_enum_leaked` | `BL_COMPARISON` | NO | `processing_or_provider_failure` | Leaked evaluation enum rejected |
| `cls_invalid_unknown_enum` | `OTHER` | NO | `processing_or_provider_failure` | Unapproved category enum rejected |
| `cls_invalid_missing_category` | Missing key | NO | `processing_or_provider_failure` | Missing mandatory schema key |
| `cls_invalid_extra_field` | `document_comparison` | NO | `processing_or_provider_failure` | Unexpected extra property rejected (`extra="forbid"`) |

### 3.2 Role Resolution Fixtures
| Fixture ID | Roles Identified | Valid Schema | Expected Downstream Escalation | Test Focus |
|---|---|:---:|:---:|---|
| `role_valid_pair` | `SI`, `BL` | YES | None | Unambiguous 1:1 role identification |
| `role_valid_si_only` | `SI` | YES | `missing_attachment` | Missing Draft BL routes to missing_attachment |
| `role_valid_bl_only` | `BL` | YES | `missing_attachment` | Missing SI routes to missing_attachment |
| `role_ambig_duplicate_si` | `SI`, `SI` | YES | `wrong_or_uncertain_document_type` | Multiple SI candidates without resolution |
| `role_ambig_duplicate_bl` | `BL`, `BL` | YES | `wrong_or_uncertain_document_type` | Multiple Draft BL candidates without resolution |
| `role_ambig_same_file_both_roles` | `SI` & `BL` on 1 file | NO | `wrong_or_uncertain_document_type` | Single file claimed as both roles rejected |
| `role_ambig_missing_both` | `UNKNOWN`, `UNKNOWN` | YES | `wrong_or_uncertain_document_type` | Unrelated documents (packing list / invoice) |

### 3.3 Extraction Fixtures (7 Mandatory Fields)
| Fixture ID | Status / Focus | Valid Schema | Expected Downstream Escalation | Test Focus |
|---|---|:---:|:---:|---|
| `ext_valid_full_seven_fields` | All 7 fields FOUND | YES | None | Clean text extraction with verified evidence quotes |
| `ext_valid_partial_missing_field` | 6 FOUND, 1 MISSING | YES | `missing_required_value` | Missing notify party routes to missing_required_value |
| `ext_valid_with_evidence` | All 7 fields FOUND | YES | None | Grounded table cell coordinates evidence |
| `ext_valid_multiline_address` | All 7 fields FOUND | YES | None | Preserves multiline postal blocks without reordering |
| `ext_ungrounded_hallucinated_shipper` | Hallucinated quote | YES (Schema) | `uncertain_result` | High confidence fails evidence grounding check |
| `ext_ungrounded_missing_evidence` | Null evidence | YES (Schema) | `uncertain_result` | Extracted value missing evidence fails Reliability Gate |
| `ext_conflict_split_candidates` | Conflicting weights | YES | `conflicting_candidate_values` | Multiple distinct candidates without guessing |
| `ext_invalid_wrong_type_count` | String count ("four") | NO | `processing_or_provider_failure` | Integer field type validation |
| `ext_invalid_wrong_type_weight` | Prose weight ("~20t") | NO | `uncertain_result` | Vague prose normalization failure |
| `ext_invalid_null_field_name` | Null dictionary key | NO | `processing_or_provider_failure` | Field key cannot be null |
| `ext_invalid_array_not_object` | Top-level array | NO | `processing_or_provider_failure` | Schema requires mapping object |

### 3.4 OCR / Vision Semantic Fixtures
*Note: All bounding boxes in `ocr_valid_full_recovery.json` are empirically grounded in the exact text pixel locations rendered on the 600x800 grayscale canvas of `tests/fixtures/documents/scanned/scan_si_001_readable.pdf`.*

| Fixture ID | Scenario | Valid Schema | Expected Downstream Escalation | Test Focus |
|---|---|:---:|:---:|---|
| `ocr_valid_full_recovery` | Clean scan recovery | YES | None | 7 fields recovered with grounded pixel bounding boxes |
| `ocr_valid_partial_clean_fields` | Blurry disclaimer | YES | None | Essential 7 fields sharp; document accepted |
| `ocr_unreadable_mandatory_field` | Coffee stain smudge | YES | `missing_required_value` | Illegible container count routes to HITL |
| `ocr_conflicting_readings` | Ambiguous low-res | YES | `conflicting_candidate_values` | Split OCR readings route to conflicting candidates |

### 3.5 Technical & Syntax Failure Fixtures
*Note: Atomic failure descriptors capture observed fault conditions neutrally without asserting global retryability policy. Retry behaviors and bounds are validated via Section 4 Retry Sequences.*

| Fixture ID | Fault Type | Observed Fault Details | Test Focus / Expected Handling |
|---|---|---|---|
| `tech_timeout` | `timeout` | Upstream socket timeout / read timeout | Network timeout simulation |
| `tech_connection_error` | `connection_error` | Transport connection reset / TLS failure | Connection fault handling |
| `tech_rate_limit_429` | `rate_limit_429` | HTTP 429 Too Many Requests | Rate-limit throttling simulation |
| `tech_provider_unavailable_503` | `provider_unavailable_503` | HTTP 503 Service Unavailable | Transient service outage simulation |
| `tech_empty_response` | `empty_response` | HTTP 200 with zero-length payload | Empty response stream handling |
| `tech_interrupted_stream` | `interrupted_stream` | Premature EOF during chunked transfer | Stream termination handling |
| `tech_decode_error` | `decode_error` | Non-UTF8 byte sequence in body | Encoding decode failure handling |
| `malformed_unclosed_brace` | `malformed_json` | Unclosed JSON curly brace | Syntax repair prompting test |
| `malformed_unquoted_key` | `malformed_json` | Unquoted JSON dictionary key | Syntax repair prompting test |
| `malformed_truncated_stream` | `malformed_json` | Incomplete truncated JSON stream | Syntax repair prompting test |

---

## 4. Retry Sequences Catalogue

1. **`TECH-SEQ-001`**: Timeout $\rightarrow$ Timeout $\rightarrow$ Valid Response. Succeeds on Attempt 3 within `technical_attempt_limit = 3`.
2. **`TECH-SEQ-002`**: Rate Limit (429) $\rightarrow$ Unavailable (503) $\rightarrow$ Unavailable (503). Exhausts 3 attempts; invokes stage-specific fallback.
3. **`SEM-SEQ-001`**: Ungrounded Evidence $\rightarrow$ Corrected Grounded Response. Succeeds on Semantic Attempt 2 within `semantic_attempt_limit = 2`.
4. **`SEM-SEQ-002`**: Conflicting Candidates $\rightarrow$ Still Conflicting Candidates. Exhausts 2 semantic attempts; routes to `conflicting_candidate_values` HITL.
5. **`NESTED-SEQ-001`**: 3 Technical Retries on Semantic Attempt 1 + 3 Technical Retries on Semantic Attempt 2. Total calls = 6. Strictly caps nested invocations at 6 without executing a 7th call; escalates to `processing_or_provider_failure`.

---

## 5. Fallback Scenarios Catalogue

1. **`fb_stage1_heuristic_success`**: AI classifier unavailable (503) $\rightarrow$ local deterministic keyword rule engine classifies email intent with grounded evidence $\rightarrow$ pipeline continues without HITL.
2. **`fb_stage3_deterministic_success`**: AI extractor unavailable (timeout) $\rightarrow$ deterministic plain-text regex / table cell parser has already reliably extracted all 7 fields $\rightarrow$ pipeline continues to comparison without HITL.
3. **`fb_exhausted_hitl_escalation`**: AI provider unavailable $\rightarrow$ deterministic fallback unable to extract required fields (scan / corrupted) $\rightarrow$ escalates gracefully to HITL: `processing_or_provider_failure`.
