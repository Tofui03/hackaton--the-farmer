"""Deterministic Generator for Synthetic AI Adapter Response & Fault Injection Fixtures (Task T01-03).

This generator relies strictly on:
- Python standard library (json, os, pathlib)

Zero undeclared or external libraries are used.
No network calls or live AI provider APIs are invoked.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "ai"

# Directory structure
DIRS = {
    "cls_valid": BASE_DIR / "classification" / "valid",
    "cls_invalid": BASE_DIR / "classification" / "invalid",
    "role_valid": BASE_DIR / "role_resolution" / "valid",
    "role_ambig": BASE_DIR / "role_resolution" / "ambiguous",
    "ext_valid": BASE_DIR / "extraction" / "valid",
    "ext_ungrounded": BASE_DIR / "extraction" / "ungrounded",
    "ext_conflict": BASE_DIR / "extraction" / "conflicting",
    "ext_invalid": BASE_DIR / "extraction" / "invalid_schema",
    "ocr_valid": BASE_DIR / "ocr" / "valid",
    "ocr_failures": BASE_DIR / "ocr" / "failures",
    "fail_tech": BASE_DIR / "failures" / "technical",
    "fail_syntax": BASE_DIR / "failures" / "syntax",
    "retry_seq": BASE_DIR / "retry_sequences",
    "fallbacks": BASE_DIR / "fallbacks",
    "gemini": BASE_DIR / "provider_specific" / "gemini",
}

for d in DIRS.values():
    d.mkdir(parents=True, exist_ok=True)


def main():
    fixtures_meta = {}
    retry_sequences_meta = {}
    fallback_scenarios_meta = {}

    # ==========================================================================
    # 1. CLASSIFICATION: VALID
    # ==========================================================================
    # 1.1 document_comparison (clean 2 attachments)
    f_id = "cls_valid_doc_comparison"
    f_data = {
        "category": "document_comparison",
        "reason": "Explicit user request to verify shipping instruction against attached draft bill of lading.",
        "evidence": [
            "Please compare the attached Shipping Instruction with the draft B/L",
            "verify container count and weight match before filing"
        ],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "standard_comparison_request",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": None,
        "tags": ["PIPE-CLS-001", "AI-ADP-001", "document_comparison"],
        "rationale": "Canonical document_comparison intent with grounded email body evidence."
    }

    # 1.2 document_comparison with zero attachments (EC-002, REG-001)
    f_id = "cls_valid_doc_comparison_zero_attachments"
    f_data = {
        "category": "document_comparison",
        "reason": "Inbound email explicitly requests verification of draft BL against SI, but no files are attached.",
        "evidence": [
            "Can you check if our SI matches the draft bill of lading?"
        ],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "zero_attachment_comparison_intent",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": "missing_attachment",
        "tags": ["PIPE-CLS-004", "EC-002", "REG-001", "attachment_invariant"],
        "rationale": "Attachment count does not veto email intent. Category resolves to document_comparison; downstream Stage 2 triggers missing_attachment."
    }

    # 1.3 new_shipping_instruction
    f_id = "cls_valid_new_si"
    f_data = {
        "category": "new_shipping_instruction",
        "reason": "Inbound email submits new shipping instructions for booking BK-9901.",
        "evidence": [
            "Please find attached new shipping instruction for booking BK-9901",
            "Kindly issue draft bill of lading at your earliest convenience"
        ],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "new_si_submission",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": None,
        "tags": ["PIPE-CLS-001", "new_shipping_instruction"],
        "rationale": "Canonical new_shipping_instruction intent."
    }

    # 1.4 invoice_query
    f_id = "cls_valid_invoice_query"
    f_data = {
        "category": "invoice_query",
        "reason": "Customer inquiring about demurrage and detention charges on freight invoice.",
        "evidence": [
            "Please clarify demurrage charges on invoice INV-77210"
        ],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "invoice_query",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": None,
        "tags": ["PIPE-CLS-001", "invoice_query"],
        "rationale": "Canonical invoice_query intent; bypasses document comparison."
    }

    # 1.5 general
    f_id = "cls_valid_general"
    f_data = {
        "category": "general",
        "reason": "General operational inquiry regarding terminal holiday hours.",
        "evidence": [
            "What are your holiday receiving hours for Singapore port terminal?"
        ],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "general_inquiry",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": None,
        "tags": ["PIPE-CLS-001", "general"],
        "rationale": "Canonical general inquiry intent."
    }

    # 1.6 spam
    f_id = "cls_valid_spam"
    f_data = {
        "category": "spam",
        "reason": "Unsolicited promotional marketing message.",
        "evidence": [
            "Claim your free enterprise software demo now"
        ],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "spam_marketing",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": None,
        "tags": ["PIPE-CLS-001", "spam"],
        "rationale": "Canonical spam intent."
    }

    # 1.7 unresolved null category (vague context)
    f_id = "cls_valid_unresolved_null"
    f_data = {
        "category": None,
        "reason": "Vague email body with zero operational context; intent cannot be reliably determined.",
        "evidence": [
            "FYI please see attached."
        ],
        "confidence_indicator": "LOW"
    }
    (DIRS["cls_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/valid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "unresolved_ambiguous_intent",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID_NULL_CATEGORY",
        "expected_downstream_review_reason": "uncertain_result",
        "tags": ["PIPE-CLS-006", "unresolved_intent", "uncertain_result"],
        "rationale": "Valid contract representation of unresolved classification; category is null and routes to HITL."
    }

    # ==========================================================================
    # 2. CLASSIFICATION: INVALID
    # ==========================================================================
    # 2.1 Leaked Evaluation Enum (BL_COMPARISON)
    f_id = "cls_invalid_eval_enum_leaked"
    f_data = {
        "category": "BL_COMPARISON",
        "reason": "Leaked evaluation uppercase enum instead of internal canonical enum.",
        "evidence": ["compare SI and BL"],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/invalid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "invalid_evaluation_enum_leaked",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-ADP-002", "schema_violation", "enum_guardrail"],
        "rationale": "Rejects evaluation bundle enum BL_COMPARISON. Internal canonical enum must be document_comparison."
    }

    # 2.2 Unknown Enum Value (OTHER)
    f_id = "cls_invalid_unknown_enum"
    f_data = {
        "category": "OTHER",
        "reason": "Model invented unapproved category enum.",
        "evidence": ["hello world"],
        "confidence_indicator": "LOW"
    }
    (DIRS["cls_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/invalid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "unapproved_enum_value",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-ADP-002", "unapproved_enum"],
        "rationale": "Model returns unapproved category 'OTHER'. Schema validation must reject."
    }

    # 2.3 Missing Category Key
    f_id = "cls_invalid_missing_category"
    f_data = {
        "reason": "Model returned explanation without category key.",
        "evidence": ["compare attached documents"],
        "confidence_indicator": "HIGH"
    }
    (DIRS["cls_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/invalid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "missing_mandatory_key",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-ADP-003", "missing_key"],
        "rationale": "Missing mandatory 'category' field. Schema validation fails."
    }

    # 2.4 Extra Forbidden Property
    f_id = "cls_invalid_extra_field"
    f_data = {
        "category": "document_comparison",
        "reason": "Valid reason.",
        "evidence": ["compare attached SI and BL"],
        "confidence_indicator": "HIGH",
        "hallucinated_extra_key": "injected_field_value_123"
    }
    (DIRS["cls_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"classification/invalid/{f_id}.json",
        "stage": "Stage 1: Classification",
        "scenario": "extra_forbidden_property",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-ADP-004", "extra_forbidden_key"],
        "rationale": "Schema validation configured with extra='forbid' must reject unexpected properties."
    }

    # ==========================================================================
    # 3. ROLE RESOLUTION: VALID
    # ==========================================================================
    # 3.1 Clean Pair
    f_id = "role_valid_pair"
    f_data = {
        "document_roles": {
            "attachment_01_si.pdf": "SI",
            "attachment_02_draft_bl.pdf": "BL"
        },
        "rationale": "attachment_01 contains Shipping Instruction header and booking number; attachment_02 contains Draft Bill of Lading header and B/L number.",
        "confidence_indicator": "HIGH"
    }
    (DIRS["role_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/valid/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "clean_si_bl_pair",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID",
        "expected_downstream_review_reason": None,
        "tags": ["PAR-ROLE-002", "clean_role_pair"],
        "rationale": "Exactly one SI and one BL identified unambiguously."
    }

    # 3.2 Valid SI only
    f_id = "role_valid_si_only"
    f_data = {
        "document_roles": {
            "attachment_01_si.pdf": "SI"
        },
        "rationale": "attachment_01 is definitively a Shipping Instruction; no BL candidate attached.",
        "confidence_indicator": "HIGH"
    }
    (DIRS["role_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/valid/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "si_only_attached",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID_PARTIAL_ROLE",
        "expected_downstream_review_reason": "missing_attachment",
        "tags": ["PAR-ROLE-004", "missing_attachment"],
        "rationale": "AI identifies SI accurately, but missing draft BL routes case to missing_attachment."
    }

    # 3.3 Valid BL only
    f_id = "role_valid_bl_only"
    f_data = {
        "document_roles": {
            "attachment_02_draft_bl.pdf": "BL"
        },
        "rationale": "attachment_02 is definitively a Draft Bill of Lading; no SI candidate attached.",
        "confidence_indicator": "HIGH"
    }
    (DIRS["role_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/valid/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "bl_only_attached",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "VALID_PARTIAL_ROLE",
        "expected_downstream_review_reason": "missing_attachment",
        "tags": ["PAR-ROLE-003", "missing_attachment"],
        "rationale": "AI identifies BL accurately, but missing SI routes case to missing_attachment."
    }

    # ==========================================================================
    # 4. ROLE RESOLUTION: AMBIGUOUS
    # ==========================================================================
    # 4.1 Duplicate SI candidates
    f_id = "role_ambig_duplicate_si"
    f_data = {
        "document_roles": {
            "candidate_doc_a.pdf": "SI",
            "candidate_doc_b.pdf": "SI"
        },
        "rationale": "Both attachments contain Shipping Instruction headers; cannot determine which is authoritative.",
        "confidence_indicator": "LOW"
    }
    (DIRS["role_ambig"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/ambiguous/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "duplicate_si_candidates",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "ROLE_AMBIGUITY_DETECTED",
        "expected_downstream_review_reason": "wrong_or_uncertain_document_type",
        "tags": ["PAR-ROLE-005", "duplicate_roles", "wrong_or_uncertain_document_type"],
        "rationale": "Multiple SI candidates without resolution must route to wrong_or_uncertain_document_type."
    }

    # 4.2 Duplicate BL candidates
    f_id = "role_ambig_duplicate_bl"
    f_data = {
        "document_roles": {
            "draft_v1.pdf": "BL",
            "draft_v2.pdf": "BL"
        },
        "rationale": "Two versions of draft BL attached without clear superseding indication.",
        "confidence_indicator": "LOW"
    }
    (DIRS["role_ambig"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/ambiguous/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "duplicate_bl_candidates",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "ROLE_AMBIGUITY_DETECTED",
        "expected_downstream_review_reason": "wrong_or_uncertain_document_type",
        "tags": ["PAR-ROLE-005", "duplicate_bl", "wrong_or_uncertain_document_type"],
        "rationale": "Multiple BL candidates without resolution must route to wrong_or_uncertain_document_type."
    }

    # 4.3 Same file proposed for both roles
    f_id = "role_ambig_same_file_both_roles"
    f_data = {
        "document_roles": {
            "single_file.pdf": ["SI", "BL"]
        },
        "rationale": "Model proposed that single file serves as both SI and BL simultaneously.",
        "confidence_indicator": "LOW"
    }
    (DIRS["role_ambig"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/ambiguous/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "same_attachment_both_roles",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "ROLE_MUTUAL_EXCLUSION_ERROR",
        "expected_downstream_review_reason": "wrong_or_uncertain_document_type",
        "tags": ["PAR-ROLE-006", "wrong_or_uncertain_document_type"],
        "rationale": "Single file cannot fulfill both SI and BL roles simultaneously; routes to wrong_or_uncertain_document_type."
    }

    # 4.4 Missing both roles (unrelated attachments)
    f_id = "role_ambig_missing_both"
    f_data = {
        "document_roles": {
            "packing_list.pdf": "UNKNOWN",
            "commercial_invoice.pdf": "UNKNOWN"
        },
        "rationale": "Attachments are packing list and commercial invoice, neither is an SI or draft BL.",
        "confidence_indicator": "LOW"
    }
    (DIRS["role_ambig"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"role_resolution/ambiguous/{f_id}.json",
        "stage": "Stage 2: Role Resolution",
        "scenario": "unrelated_document_types",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "UNSUPPORTED_ROLES",
        "expected_downstream_review_reason": "wrong_or_uncertain_document_type",
        "tags": ["PAR-ROLE-007", "wrong_or_uncertain_document_type"],
        "rationale": "Neither document fulfills required shipping roles; routes to wrong_or_uncertain_document_type."
    }

    # ==========================================================================
    # 5. EXTRACTION: VALID
    # ==========================================================================
    # 5.1 Full seven fields extraction
    f_id = "ext_valid_full_seven_fields"
    f_data = {
        "document_id": "txt_si_001_clean.txt",
        "role": "SI",
        "fields": {
            "shipper": {
                "raw_value": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
                "status": "FOUND",
                "evidence": "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD"
            },
            "consignee": {
                "raw_value": "ATLANTIC IMPORTS & TRADING GMBH",
                "status": "FOUND",
                "evidence": "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH"
            },
            "notify_party": {
                "raw_value": "MARITIME CUSTOMS BROKERS INC",
                "status": "FOUND",
                "evidence": "NOTIFY PARTY: MARITIME CUSTOMS BROKERS INC"
            },
            "port_of_loading": {
                "raw_value": "SINGAPORE",
                "status": "FOUND",
                "evidence": "PORT OF LOADING: SINGAPORE"
            },
            "port_of_discharge": {
                "raw_value": "ROTTERDAM",
                "status": "FOUND",
                "evidence": "PORT OF DISCHARGE: ROTTERDAM"
            },
            "container_count": {
                "raw_value": 4,
                "status": "FOUND",
                "evidence": "CONTAINER COUNT: 4"
            },
            "gross_weight_kg": {
                "raw_value": "22000 KG",
                "status": "FOUND",
                "evidence": "GROSS WEIGHT: 22000 KG"
            }
        },
        "confidence_indicator": "HIGH"
    }
    (DIRS["ext_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/valid/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "full_successful_extraction",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "ALL_SEVEN_RELIABLE",
        "expected_downstream_review_reason": None,
        "tags": ["AI-ADP-001", "PIPE-CMP-001", "seven_fields_clean"],
        "rationale": "All seven mandatory fields extracted with exact textual evidence snippets."
    }

    # 5.2 Partial extraction with missing field
    f_id = "ext_valid_partial_missing_field"
    f_data = {
        "document_id": "txt_si_007_missing_field.txt",
        "role": "SI",
        "fields": {
            "shipper": {
                "raw_value": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
                "status": "FOUND",
                "evidence": "SHIPPER: PACIFIC SYNTHETIC LOGISTICS PTE LTD"
            },
            "consignee": {
                "raw_value": "ATLANTIC IMPORTS & TRADING GMBH",
                "status": "FOUND",
                "evidence": "CONSIGNEE: ATLANTIC IMPORTS & TRADING GMBH"
            },
            "notify_party": {
                "raw_value": None,
                "status": "MISSING",
                "evidence": None
            },
            "port_of_loading": {
                "raw_value": "SINGAPORE",
                "status": "FOUND",
                "evidence": "PORT OF LOADING: SINGAPORE"
            },
            "port_of_discharge": {
                "raw_value": "ROTTERDAM",
                "status": "FOUND",
                "evidence": "PORT OF DISCHARGE: ROTTERDAM"
            },
            "container_count": {
                "raw_value": 4,
                "status": "FOUND",
                "evidence": "CONTAINER COUNT: 4"
            },
            "gross_weight_kg": {
                "raw_value": "22000 KG",
                "status": "FOUND",
                "evidence": "GROSS WEIGHT: 22000 KG"
            }
        },
        "confidence_indicator": "HIGH"
    }
    (DIRS["ext_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/valid/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "partial_missing_field",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "MISSING_FIELD_FLAGGED",
        "expected_downstream_review_reason": "missing_required_value",
        "tags": ["HITL-RSN-004", "missing_required_value"],
        "rationale": "AI correctly identifies notify_party as MISSING; routes to missing_required_value without hallucinating."
    }

    # 5.3 Extraction with table coordinates evidence
    f_id = "ext_valid_with_evidence"
    f_data = {
        "document_id": "docx_bl_001_table.docx",
        "role": "BL",
        "fields": {
            "shipper": {
                "raw_value": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
                "status": "FOUND",
                "evidence": "Table 0, Row 0, Col 1: 'PACIFIC SYNTHETIC LOGISTICS PTE LTD'"
            },
            "consignee": {
                "raw_value": "ATLANTIC IMPORTS & TRADING GMBH",
                "status": "FOUND",
                "evidence": "Table 0, Row 1, Col 1: 'ATLANTIC IMPORTS & TRADING GMBH'"
            },
            "notify_party": {
                "raw_value": "MARITIME CUSTOMS BROKERS INC",
                "status": "FOUND",
                "evidence": "Table 0, Row 2, Col 1: 'MARITIME CUSTOMS BROKERS INC'"
            },
            "port_of_loading": {
                "raw_value": "SINGAPORE",
                "status": "FOUND",
                "evidence": "Table 1, Row 0, Col 1: 'SINGAPORE'"
            },
            "port_of_discharge": {
                "raw_value": "ROTTERDAM",
                "status": "FOUND",
                "evidence": "Table 1, Row 1, Col 1: 'ROTTERDAM'"
            },
            "container_count": {
                "raw_value": 4,
                "status": "FOUND",
                "evidence": "Table 2, Row 0, Col 1: '4'"
            },
            "gross_weight_kg": {
                "raw_value": "22000 KG",
                "status": "FOUND",
                "evidence": "Table 2, Row 1, Col 1: '22000 KG'"
            }
        },
        "confidence_indicator": "HIGH"
    }
    (DIRS["ext_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/valid/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "table_cell_grounded_evidence",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "ALL_SEVEN_RELIABLE",
        "expected_downstream_review_reason": None,
        "tags": ["PAR-DOCX-001", "grounded_table_evidence"],
        "rationale": "Valid structured extraction backed by table cell coordinate evidence."
    }

    # 5.4 Multiline postal address
    f_id = "ext_valid_multiline_address"
    f_data = {
        "document_id": "txt_si_006_multiline_orgs.txt",
        "role": "SI",
        "fields": {
            "shipper": {
                "raw_value": "PACIFIC SYNTHETIC LOGISTICS PTE LTD\nSUITE 400, 128 HARBOR WAY\nSINGAPORE 049318",
                "status": "FOUND",
                "evidence": "Lines 3-5: multiline postal block"
            },
            "consignee": {
                "raw_value": "ATLANTIC IMPORTS & TRADING GMBH\nINDUSTRIESTRASSE 12\n20457 HAMBURG, GERMANY",
                "status": "FOUND",
                "evidence": "Lines 8-10: multiline postal block"
            },
            "notify_party": {
                "raw_value": "MARITIME NOTIFY SERVICES LTD\n100 SHIPPING PLAZA, SINGAPORE 049319",
                "status": "FOUND",
                "evidence": "Lines 13-14: multiline postal block"
            },
            "port_of_loading": {
                "raw_value": "SINGAPORE",
                "status": "FOUND",
                "evidence": "PORT OF LOADING: SINGAPORE"
            },
            "port_of_discharge": {
                "raw_value": "ROTTERDAM",
                "status": "FOUND",
                "evidence": "PORT OF DISCHARGE: ROTTERDAM"
            },
            "container_count": {
                "raw_value": 4,
                "status": "FOUND",
                "evidence": "CONTAINER COUNT: 4"
            },
            "gross_weight_kg": {
                "raw_value": "22000 KG",
                "status": "FOUND",
                "evidence": "GROSS WEIGHT: 22000 KG"
            }
        },
        "confidence_indicator": "HIGH"
    }
    (DIRS["ext_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/valid/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "multiline_organization_addresses",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "ALL_SEVEN_RELIABLE",
        "expected_downstream_review_reason": None,
        "tags": ["multiline_address", "preservation"],
        "rationale": "Preserves newline formatting in organization addresses without token reordering."
    }

    # ==========================================================================
    # 6. EXTRACTION: UNGROUNDED / HALLUCINATED
    # ==========================================================================
    # 6.1 Hallucinated shipper entity
    f_id = "ext_ungrounded_hallucinated_shipper"
    f_data = {
        "document_id": "txt_si_001_clean.txt",
        "role": "SI",
        "fields": {
            "shipper": {
                "raw_value": "ACME GLOBAL FABRICATED SHIPPERS INC",
                "status": "FOUND",
                "evidence": "SHIPPER: ACME GLOBAL FABRICATED SHIPPERS INC"  # Fabricated quote!
            }
        },
        "confidence_indicator": "HIGH"  # Model claims high confidence despite fabrication!
    }
    (DIRS["ext_ungrounded"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/ungrounded/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "hallucinated_entity_high_confidence",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "EVIDENCE_GROUNDING_FAILED",
        "expected_downstream_review_reason": "uncertain_result",
        "tags": ["AI-ADP-005", "hallucination", "REG-011", "uncertain_result"],
        "rationale": "High confidence does not bypass evidence verification. Fabricated quote fails grounding check and routes to uncertain_result."
    }

    # 6.2 Missing evidence field
    f_id = "ext_ungrounded_missing_evidence"
    f_data = {
        "document_id": "txt_si_001_clean.txt",
        "role": "SI",
        "fields": {
            "container_count": {
                "raw_value": 4,
                "status": "FOUND",
                "evidence": None  # Missing evidence quote
            }
        },
        "confidence_indicator": "MEDIUM"
    }
    (DIRS["ext_ungrounded"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/ungrounded/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "unsupported_value_missing_evidence",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "RELIABILITY_GATE_FAILED",
        "expected_downstream_review_reason": "uncertain_result",
        "tags": ["DC-02", "evidence_required", "uncertain_result"],
        "rationale": "Field value provided without source evidence fails Reliability Gate."
    }

    # ==========================================================================
    # 7. EXTRACTION: CONFLICTING
    # ==========================================================================
    # 7.1 Conflicting candidate values
    f_id = "ext_conflict_split_candidates"
    f_data = {
        "document_id": "txt_si_008_conflicting_candidates.txt",
        "role": "SI",
        "fields": {
            "gross_weight_kg": {
                "raw_value": None,
                "status": "CONFLICTING",
                "candidates": [
                    {"raw_value": "24500 KG", "evidence": "ESTIMATED GROSS WEIGHT: 24500 KG"},
                    {"raw_value": "28000 KG", "evidence": "FINAL CERTIFIED GROSS WEIGHT: 28000 KG"}
                ]
            }
        },
        "confidence_indicator": "LOW"
    }
    (DIRS["ext_conflict"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/conflicting/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "conflicting_candidate_values",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "CONFLICT_FLAGGED",
        "expected_downstream_review_reason": "conflicting_candidate_values",
        "tags": ["HITL-RSN-006", "conflicting_candidate_values"],
        "rationale": "Multiple candidates detected; AI does not guess. Routes to conflicting_candidate_values."
    }

    # ==========================================================================
    # 8. EXTRACTION: INVALID SCHEMA
    # ==========================================================================
    # 8.1 Wrong primitive type: container_count string
    f_id = "ext_invalid_wrong_type_count"
    f_data = {
        "document_id": "txt_si_001_clean.txt",
        "role": "SI",
        "fields": {
            "container_count": {
                "raw_value": "four containers",  # Must be integer!
                "status": "FOUND",
                "evidence": "four containers"
            }
        }
    }
    (DIRS["ext_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/invalid_schema/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "wrong_primitive_type_container_count",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-ADP-003", "type_mismatch"],
        "rationale": "container_count must be integer; string rejected by schema."
    }

    # 8.2 Wrong primitive type: gross_weight_kg prose
    f_id = "ext_invalid_wrong_type_weight"
    f_data = {
        "document_id": "txt_si_001_clean.txt",
        "role": "SI",
        "fields": {
            "gross_weight_kg": {
                "raw_value": "approximately twenty tons",  # Unparseable prose
                "status": "FOUND",
                "evidence": "approximately twenty tons"
            }
        }
    }
    (DIRS["ext_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/invalid_schema/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "unparseable_weight_prose",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "NORMALIZATION_FAILURE",
        "expected_downstream_review_reason": "uncertain_result",
        "tags": ["normalization_error", "uncertain_result"],
        "rationale": "Vague prose cannot be normalized deterministically."
    }

    # 8.3 Null field name
    f_id = "ext_invalid_null_field_name"
    f_data = {
        "document_id": "txt_si_001_clean.txt",
        "role": "SI",
        "fields": {
            "null": {
                "raw_value": "22000 KG",
                "status": "FOUND"
            }
        }
    }
    (DIRS["ext_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/invalid_schema/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "null_field_name_key",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["schema_error"],
        "rationale": "Field dictionary key cannot be null."
    }

    # 8.4 Array where object expected
    f_id = "ext_invalid_array_not_object"
    f_data = [
        {"field": "shipper", "value": "PACIFIC SYNTHETIC LOGISTICS PTE LTD"},
        {"field": "consignee", "value": "ATLANTIC IMPORTS & TRADING GMBH"}
    ]
    (DIRS["ext_invalid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"extraction/invalid_schema/{f_id}.json",
        "stage": "Stage 3A: Extraction",
        "scenario": "array_instead_of_object",
        "response_kind": "structured_json",
        "valid_schema": False,
        "expected_validation_result": "SCHEMA_VALIDATION_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["schema_structural_error"],
        "rationale": "Document extraction contract requires JSON object mapping, not top-level array."
    }

    # ==========================================================================
    # 9. OCR / VISION ADAPTER FIXTURES
    # ==========================================================================
    # 9.1 Full OCR recovery (Grounded in scan_si_001_readable.pdf, canvas 600x800)
    f_id = "ocr_valid_full_recovery"
    f_data = {
        "document_id": "scan_si_001_readable.pdf",
        "raster_dimensions": {"width": 600, "height": 800},
        "role": "SI",
        "fields": {
            "shipper": {
                "raw_value": "MARITIME EXPORT CARGO CORP",
                "status": "FOUND",
                "ocr_box": {"xmin": 220, "ymin": 116, "xmax": 532, "ymax": 130}
            },
            "consignee": {
                "raw_value": "NORDIC GLOBAL TRADING BV",
                "status": "FOUND",
                "ocr_box": {"xmin": 220, "ymin": 138, "xmax": 508, "ymax": 152}
            },
            "notify_party": {
                "raw_value": "NORDIC GLOBAL TRADING BV",
                "status": "FOUND",
                "ocr_box": {"xmin": 220, "ymin": 160, "xmax": 508, "ymax": 174}
            },
            "port_of_loading": {
                "raw_value": "SINGAPORE",
                "status": "FOUND",
                "ocr_box": {"xmin": 268, "ymin": 182, "xmax": 376, "ymax": 196}
            },
            "port_of_discharge": {
                "raw_value": "ROTTERDAM",
                "status": "FOUND",
                "ocr_box": {"xmin": 268, "ymin": 204, "xmax": 376, "ymax": 218}
            },
            "container_count": {
                "raw_value": 2,
                "status": "FOUND",
                "ocr_box": {"xmin": 268, "ymin": 226, "xmax": 280, "ymax": 240}
            },
            "gross_weight_kg": {
                "raw_value": "16500 KG",
                "status": "FOUND",
                "ocr_box": {"xmin": 268, "ymin": 248, "xmax": 364, "ymax": 262}
            }
        },
        "confidence_indicator": "HIGH"
    }
    (DIRS["ocr_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"ocr/valid/{f_id}.json",
        "stage": "Stage 2B: OCR / Vision",
        "scenario": "full_raster_field_recovery",
        "response_kind": "structured_json",
        "valid_schema": True,
        "is_ocr_grounded": True,
        "source_fixture": "scanned/scan_si_001_readable.pdf",
        "expected_validation_result": "ALL_SEVEN_RELIABLE",
        "expected_downstream_review_reason": None,
        "tags": ["AI-OCR-001", "raster_recovery", "grounded_box"],
        "rationale": "All 7 fields extracted from raster scan_si_001_readable.pdf with exact, grounded bounding box coordinates matching rendered text pixels on the 600x800 canvas."
    }

    # 9.2 Partial clean fields (terms blurry)
    f_id = "ocr_valid_partial_clean_fields"
    f_data = {
        "document_id": "scan_si_002_degraded.pdf",
        "raster_dimensions": {"width": 600, "height": 800},
        "role": "SI",
        "fields": {
            "shipper": {"raw_value": "MARITIME EXPORT CARGO CORP", "status": "FOUND"},
            "consignee": {"raw_value": "NORDIC GLOBAL TRADING BV", "status": "FOUND"},
            "notify_party": {"raw_value": "NORDIC GLOBAL TRADING BV", "status": "FOUND"},
            "port_of_loading": {"raw_value": "SINGAPORE", "status": "FOUND"},
            "port_of_discharge": {"raw_value": "ROTTERDAM", "status": "FOUND"},
            "container_count": {"raw_value": 2, "status": "FOUND"},
            "gross_weight_kg": {"raw_value": "16500 KG", "status": "FOUND"}
        },
        "footer_terms_legible": False,
        "confidence_indicator": "MEDIUM"
    }
    (DIRS["ocr_valid"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"ocr/valid/{f_id}.json",
        "stage": "Stage 2B: OCR / Vision",
        "scenario": "essential_fields_readable_footer_corrupted",
        "response_kind": "structured_json",
        "valid_schema": True,
        "source_fixture": "scanned/scan_si_002_degraded.pdf",
        "expected_validation_result": "ALL_SEVEN_RELIABLE",
        "expected_downstream_review_reason": None,
        "tags": ["AI-OCR-002", "DEC-AI-P04", "partial_clean"],
        "rationale": "Terms blurry, but all 7 comparison fields are sharp and reliable; document accepted."
    }

    # 9.3 Unreadable mandatory field
    f_id = "ocr_unreadable_mandatory_field"
    f_data = {
        "document_id": "scan_si_stained.pdf",
        "role": "SI",
        "fields": {
            "container_count": {
                "raw_value": None,
                "status": "UNREADABLE",
                "evidence": "Stained / illegible area at Row 5"
            }
        },
        "confidence_indicator": "LOW"
    }
    (DIRS["ocr_failures"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"ocr/failures/{f_id}.json",
        "stage": "Stage 2B: OCR / Vision",
        "scenario": "unreadable_mandatory_field_smudge",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "UNREADABLE_FIELD_FLAGGED",
        "expected_downstream_review_reason": "missing_required_value",
        "tags": ["AI-OCR-003", "missing_required_value", "illegible_scan"],
        "rationale": "Illegible mandatory field routes to missing_required_value HITL."
    }

    # 9.4 Conflicting OCR interpretations
    f_id = "ocr_conflicting_readings"
    f_data = {
        "document_id": "scan_si_lowres.pdf",
        "role": "SI",
        "fields": {
            "gross_weight_kg": {
                "raw_value": None,
                "status": "CONFLICTING",
                "candidates": [
                    {"raw_value": "22500 KG", "confidence": 0.50},
                    {"raw_value": "28500 KG", "confidence": 0.50}
                ]
            }
        }
    }
    (DIRS["ocr_failures"] / f"{f_id}.json").write_text(json.dumps(f_data, indent=2), encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"ocr/failures/{f_id}.json",
        "stage": "Stage 2B: OCR / Vision",
        "scenario": "ambiguous_ocr_candidate_split",
        "response_kind": "structured_json",
        "valid_schema": True,
        "expected_validation_result": "CONFLICT_FLAGGED",
        "expected_downstream_review_reason": "conflicting_candidate_values",
        "tags": ["AI-OCR-004", "conflicting_candidate_values"],
        "rationale": "Ambiguous glyphs produce multiple candidates without consensus; routes to conflicting_candidate_values."
    }

    # ==========================================================================
    # 10. TECHNICAL FAILURES (Provider-Neutral Fault Descriptors)
    # ==========================================================================
    tech_cases = [
        ("tech_timeout", "timeout", None, "Provider request timed out (connection deadline exceeded)", "ARBITRARY SYNTHETIC EXAMPLE — NOT A BASELINE TIMEOUT POLICY"),
        ("tech_connection_error", "connection_error", None, "Failed to establish TLS connection to AI provider", None),
        ("tech_rate_limit_429", "rate_limit", 429, "Resource has been exhausted (rate limit quota exceeded)", None),
        ("tech_provider_unavailable_503", "provider_unavailable", 503, "Service temporarily unavailable due to high server load", None),
        ("tech_empty_response", "empty_response", 200, "Provider returned HTTP 200 with empty body/candidates", None),
        ("tech_interrupted_stream", "interrupted_stream", 200, "Stream terminated prematurely before finish_reason marker", None),
        ("tech_decode_error", "decode_error", 200, "Response bytes cannot be decoded as UTF-8", None),
    ]

    for fid, ftype, code, msg, note in tech_cases:
        fdata = {
            "fault_type": ftype,
            "http_status": code,
            "message": msg,
        }
        if note:
            fdata["note"] = note
        (DIRS["fail_tech"] / f"{fid}.json").write_text(json.dumps(fdata, indent=2), encoding="utf-8")
        fixtures_meta[fid] = {
            "file": f"failures/technical/{fid}.json",
            "stage": "Technical Provider Layer",
            "scenario": f"provider_fault_{ftype}",
            "response_kind": "technical_failure_descriptor",
            "valid_schema": True,
            "scenario_metadata": {
                "simulated_fault": ftype,
                "note": note or "Provider-neutral fault descriptor. Retry behavior asserted via retry_sequences."
            },
            "expected_validation_result": "TECHNICAL_FAULT_DETECTED",
            "expected_downstream_review_reason": "processing_or_provider_failure" if ftype == "decode_error" else None,
            "tags": ["AI-ADP-006", "fault_injection", ftype],
            "rationale": f"Simulates technical provider exception: {ftype}."
        }

    # ==========================================================================
    # 11. SYNTAX / MALFORMED FAILURES (Text Files)
    # ==========================================================================
    # 11.1 Unclosed brace
    f_id = "malformed_unclosed_brace"
    content = '{\n  "category": "document_comparison",\n  "reason": "unclosed string and brace'
    (DIRS["fail_syntax"] / f"{f_id}.json.txt").write_text(content, encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"failures/syntax/{f_id}.json.txt",
        "stage": "Wire Format / JSON Decoder",
        "scenario": "unclosed_json_brace",
        "response_kind": "malformed_text_stream",
        "valid_schema": False,
        "is_malformed_syntax": True,
        "retry_class": "semantic",
        "expected_validation_result": "JSON_DECODE_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-BUD-003", "malformed_json", "semantic_retry"],
        "rationale": "Malformed JSON triggers semantic repair retry."
    }

    # 11.2 Unquoted key
    f_id = "malformed_unquoted_key"
    content = '{\n  category: "document_comparison",\n  reason: "unquoted key"\n}'
    (DIRS["fail_syntax"] / f"{f_id}.json.txt").write_text(content, encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"failures/syntax/{f_id}.json.txt",
        "stage": "Wire Format / JSON Decoder",
        "scenario": "unquoted_json_key",
        "response_kind": "malformed_text_stream",
        "valid_schema": False,
        "is_malformed_syntax": True,
        "retry_class": "semantic",
        "expected_validation_result": "JSON_DECODE_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-BUD-003", "malformed_json"],
        "rationale": "JavaScript-style unquoted key triggers JSON decode error and semantic repair."
    }

    # 11.3 Truncated stream
    f_id = "malformed_truncated_stream"
    content = '{"category": "document_com'
    (DIRS["fail_syntax"] / f"{f_id}.json.txt").write_text(content, encoding="utf-8")
    fixtures_meta[f_id] = {
        "file": f"failures/syntax/{f_id}.json.txt",
        "stage": "Wire Format / JSON Decoder",
        "scenario": "truncated_stream_cut_off",
        "response_kind": "malformed_text_stream",
        "valid_schema": False,
        "is_malformed_syntax": True,
        "retry_class": "semantic",
        "expected_validation_result": "JSON_DECODE_ERROR",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "tags": ["AI-BUD-003", "truncated_json"],
        "rationale": "Abrupt stream cut-off triggers semantic repair."
    }

    # ==========================================================================
    # 12. RETRY SEQUENCES
    # ==========================================================================
    # 12.1 TECH-SEQ-001: Transient Recover on Attempt 3
    s_id = "seq_tech_001_transient_recover"
    s_data = {
        "sequence_id": "TECH-SEQ-001",
        "scenario": "transient_failures_recover_attempt_3",
        "max_technical_attempts": 3,
        "attempts": [
            {"attempt": 1, "type": "technical", "error": "timeout", "action": "backoff_and_retry"},
            {"attempt": 2, "type": "technical", "error": "timeout", "action": "backoff_and_retry"},
            {"attempt": 3, "type": "technical", "result": "cls_valid_doc_comparison.json", "action": "succeed"}
        ],
        "final_status": "SUCCESS",
        "total_calls": 3,
        "exceeded_budget": False,
        "rationale": "Succeeds on attempt 3 within technical_attempt_limit = 3."
    }
    (DIRS["retry_seq"] / f"{s_id}.json").write_text(json.dumps(s_data, indent=2), encoding="utf-8")
    retry_sequences_meta[s_id] = s_data

    # 12.2 TECH-SEQ-002: Technical Exhaustion to Fallback
    s_id = "seq_tech_002_exhaust_to_fallback"
    s_data = {
        "sequence_id": "TECH-SEQ-002",
        "scenario": "technical_retries_exhausted_fallback_invoked",
        "max_technical_attempts": 3,
        "attempts": [
            {"attempt": 1, "type": "technical", "error": "rate_limit_429", "action": "backoff_and_retry"},
            {"attempt": 2, "type": "technical", "error": "provider_unavailable_503", "action": "backoff_and_retry"},
            {"attempt": 3, "type": "technical", "error": "provider_unavailable_503", "action": "exhaust_and_fallback"}
        ],
        "final_status": "TECHNICAL_EXHAUSTED",
        "total_calls": 3,
        "exceeded_budget": False,
        "fallback_invoked": True,
        "rationale": "Exhausts 3 technical attempts; transitions cleanly to stage-specific fallback."
    }
    (DIRS["retry_seq"] / f"{s_id}.json").write_text(json.dumps(s_data, indent=2), encoding="utf-8")
    retry_sequences_meta[s_id] = s_data

    # 12.3 SEM-SEQ-001: Semantic Repair on Attempt 2
    s_id = "seq_sem_001_evidence_repair"
    s_data = {
        "sequence_id": "SEM-SEQ-001",
        "scenario": "semantic_repair_grounding_fix",
        "max_semantic_attempts": 2,
        "attempts": [
            {"attempt": 1, "type": "semantic", "result": "ext_ungrounded_hallucinated_shipper.json", "validation": "EVIDENCE_MISSING", "action": "re_prompt_with_schema_error"},
            {"attempt": 2, "type": "semantic", "result": "ext_valid_full_seven_fields.json", "validation": "VALID", "action": "succeed"}
        ],
        "final_status": "SUCCESS",
        "total_calls": 2,
        "exceeded_budget": False,
        "rationale": "Corrects ungrounded evidence on semantic repair attempt 2 within limit = 2."
    }
    (DIRS["retry_seq"] / f"{s_id}.json").write_text(json.dumps(s_data, indent=2), encoding="utf-8")
    retry_sequences_meta[s_id] = s_data

    # 12.4 SEM-SEQ-002: Semantic Exhaustion to Reliability Gate
    s_id = "seq_sem_002_conflict_exhaust"
    s_data = {
        "sequence_id": "SEM-SEQ-002",
        "scenario": "semantic_repair_conflict_exhaustion",
        "max_semantic_attempts": 2,
        "attempts": [
            {"attempt": 1, "type": "semantic", "result": "ext_conflict_split_candidates.json", "validation": "CONFLICTING_CANDIDATES", "action": "re_prompt_for_disambiguation"},
            {"attempt": 2, "type": "semantic", "result": "ext_conflict_split_candidates.json", "validation": "STILL_CONFLICTING", "action": "exhaust_to_gate"}
        ],
        "final_status": "SEMANTIC_EXHAUSTED",
        "total_calls": 2,
        "exceeded_budget": False,
        "expected_downstream_review_reason": "conflicting_candidate_values",
        "rationale": "Conflict persists across 2 semantic attempts; routes safely to conflicting_candidate_values HITL."
    }
    (DIRS["retry_seq"] / f"{s_id}.json").write_text(json.dumps(s_data, indent=2), encoding="utf-8")
    retry_sequences_meta[s_id] = s_data

    # 12.5 NESTED-SEQ-001: Budget Cap at 6 Invocations
    s_id = "seq_nested_001_budget_cap_six"
    s_data = {
        "sequence_id": "NESTED-SEQ-001",
        "scenario": "nested_technical_and_semantic_budget_cap",
        "maximum_total_call_budget": 6,
        "attempts": [
            {"call": 1, "semantic_attempt": 1, "type": "technical", "error": "provider_unavailable_503"},
            {"call": 2, "semantic_attempt": 1, "type": "technical", "error": "timeout"},
            {"call": 3, "semantic_attempt": 1, "type": "semantic", "result": "malformed_unclosed_brace"},
            {"call": 4, "semantic_attempt": 2, "type": "technical", "error": "provider_unavailable_503"},
            {"call": 5, "semantic_attempt": 2, "type": "technical", "error": "timeout"},
            {"call": 6, "semantic_attempt": 2, "type": "technical", "error": "timeout"}
        ],
        "budget_cap_enforced": True,
        "seventh_call_permitted": False,
        "final_status": "TOTAL_BUDGET_EXHAUSTED",
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "rationale": "Total provider invocations capped strictly at 6. No infinite loop; terminates with processing_or_provider_failure."
    }
    (DIRS["retry_seq"] / f"{s_id}.json").write_text(json.dumps(s_data, indent=2), encoding="utf-8")
    retry_sequences_meta[s_id] = s_data

    # ==========================================================================
    # 13. STAGE-SPECIFIC FALLBACK SCENARIOS
    # ==========================================================================
    # 13.1 Stage 1 Fallback Success
    fb_id = "fb_stage1_heuristic_success"
    fb_data = {
        "stage": "Stage 1: Classification",
        "primary_status": "AI_PROVIDER_UNAVAILABLE",
        "fallback_mechanism": "deterministic_keyword_and_header_rules",
        "fallback_input": {
            "subject": "Verification Request: SI vs Draft BL",
            "body": "Please compare attached SI and draft B/L for discrepancy."
        },
        "fallback_output": {
            "category": "document_comparison",
            "matched_rules": ["KEYWORD_COMPARE_SI_BL", "HEADER_VERIFICATION"],
            "is_reliable": True
        },
        "pipeline_action": "CONTINUE_PROCESSING",
        "hitl_escalated": False,
        "rationale": "AI provider unavailable, but deterministic rule engine cleanly classifies intent; processing continues."
    }
    (DIRS["fallbacks"] / f"{fb_id}.json").write_text(json.dumps(fb_data, indent=2), encoding="utf-8")
    fallback_scenarios_meta[fb_id] = fb_data

    # 13.2 Stage 3 Fallback Success
    fb_id = "fb_stage3_deterministic_success"
    fb_data = {
        "stage": "Stage 3A: Field Extraction",
        "primary_status": "AI_EXTRACTION_UNAVAILABLE",
        "fallback_mechanism": "deterministic_plain_text_regex_and_cell_parser",
        "fallback_output": {
            "all_seven_fields_extracted": True,
            "reliability_gate_passed": True,
            "fields": {
                "shipper": "PACIFIC SYNTHETIC LOGISTICS PTE LTD",
                "consignee": "ATLANTIC IMPORTS & TRADING GMBH",
                "notify_party": "MARITIME CUSTOMS BROKERS INC",
                "port_of_loading": "SINGAPORE",
                "port_of_discharge": "ROTTERDAM",
                "container_count": 4,
                "gross_weight_kg": "22000"
            }
        },
        "pipeline_action": "CONTINUE_TO_COMPARISON",
        "hitl_escalated": False,
        "rationale": "Deterministic parser has already reliably extracted all 7 fields; AI timeout does not block pipeline."
    }
    (DIRS["fallbacks"] / f"{fb_id}.json").write_text(json.dumps(fb_data, indent=2), encoding="utf-8")
    fallback_scenarios_meta[fb_id] = fb_data

    # 13.3 Fallback Exhausted / Insufficient
    fb_id = "fb_exhausted_hitl_escalation"
    fb_data = {
        "stage": "Stage 3A: Field Extraction",
        "primary_status": "AI_PROVIDER_UNAVAILABLE",
        "fallback_mechanism": "deterministic_regex_parser",
        "fallback_output": {
            "all_seven_fields_extracted": False,
            "missing_fields": ["gross_weight_kg", "container_count"],
            "is_reliable": False
        },
        "pipeline_action": "ESCALATE_TO_HITL",
        "hitl_escalated": True,
        "expected_downstream_review_reason": "processing_or_provider_failure",
        "rationale": "AI provider unavailable AND deterministic fallback cannot extract required fields; escalates to processing_or_provider_failure."
    }
    (DIRS["fallbacks"] / f"{fb_id}.json").write_text(json.dumps(fb_data, indent=2), encoding="utf-8")
    fallback_scenarios_meta[fb_id] = fb_data

    # ==========================================================================
    # 14. PROVIDER-SPECIFIC (GEMINI SAMPLES)
    # ==========================================================================
    # 14.1 README
    gemini_readme = (
        "# Provider-Specific Wire Format: Google Gemini\n\n"
        "> [!IMPORTANT]\n"
        "> **IMPLEMENTATION-SPECIFIC FIXTURE — NOT CORE CONTRACT AUTHORITY**\n"
        "> This directory contains samples of the raw Google GenAI API response structure.\n"
        "> The internal `BaseAIAdapter` abstraction MUST remain provider-neutral.\n"
    )
    (DIRS["gemini"] / "README.md").write_text(gemini_readme, encoding="utf-8")

    # 14.2 Raw response
    gemini_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "{\n  \"category\": \"document_comparison\",\n  \"reason\": \"Request to compare SI and Draft BL\",\n  \"evidence\": [\"compare attached SI and draft BL\"],\n  \"confidence_indicator\": \"HIGH\"\n}"
                        }
                    ],
                    "role": "model"
                },
                "finish_reason": "STOP"
            }
        ],
        "usage_metadata": {
            "prompt_token_count": 142,
            "candidates_token_count": 48,
            "total_token_count": 190
        }
    }
    (DIRS["gemini"] / "gemini_raw_classification_response.json").write_text(json.dumps(gemini_resp, indent=2), encoding="utf-8")

    # 14.3 Raw error
    gemini_err = {
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (e.g. check quota).",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [
                        {"subject": "project:shipping-demo", "description": "Rate limit exceeded"}
                    ]
                }
            ]
        }
    }
    (DIRS["gemini"] / "gemini_raw_error_payload.json").write_text(json.dumps(gemini_err, indent=2), encoding="utf-8")

    # Provider-specific wire format reference files
    fixtures_meta["gemini_raw_classification_response"] = {
        "file": "provider_specific/gemini/gemini_raw_classification_response.json",
        "stage": "Provider Wire Format Reference",
        "scenario": "gemini_raw_response_shape",
        "response_kind": "provider_wire_payload",
        "valid_schema": True,
        "is_provider_specific": True,
        "provider": "gemini",
        "expected_validation_result": "VALID_WIRE_PAYLOAD",
        "expected_downstream_review_reason": None,
        "tags": ["gemini", "wire_format", "implementation_specific"],
        "rationale": "IMPLEMENTATION-SPECIFIC FIXTURE — NOT CORE CONTRACT AUTHORITY."
    }

    fixtures_meta["gemini_raw_error_payload"] = {
        "file": "provider_specific/gemini/gemini_raw_error_payload.json",
        "stage": "Provider Wire Format Reference",
        "scenario": "gemini_raw_error_shape",
        "response_kind": "provider_wire_payload",
        "valid_schema": True,
        "is_provider_specific": True,
        "provider": "gemini",
        "expected_validation_result": "VALID_WIRE_PAYLOAD",
        "expected_downstream_review_reason": None,
        "tags": ["gemini", "error_format", "implementation_specific"],
        "rationale": "IMPLEMENTATION-SPECIFIC FIXTURE — NOT CORE CONTRACT AUTHORITY."
    }

    # ==========================================================================
    # 15. MANIFEST COMPILATION & PROGRAMMATIC COUNT MODEL
    # ==========================================================================
    core_atomic_fixtures = {k: v for k, v in fixtures_meta.items() if not v.get("is_provider_specific")}
    provider_fixtures = {k: v for k, v in fixtures_meta.items() if v.get("is_provider_specific")}

    count_model = {
        "total_atomic_fixtures": len(core_atomic_fixtures),
        "valid_atomic_responses": (
            sum(1 for f in core_atomic_fixtures.values() if "classification/valid" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "role_resolution/valid" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "extraction/valid" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "ocr/valid" in f["file"])
        ),
        "invalid_schema_fixtures": (
            sum(1 for f in core_atomic_fixtures.values() if "classification/invalid" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "extraction/invalid_schema" in f["file"])
        ),
        "semantic_failure_fixtures": (
            sum(1 for f in core_atomic_fixtures.values() if "role_resolution/ambiguous" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "extraction/ungrounded" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "extraction/conflicting" in f["file"])
            + sum(1 for f in core_atomic_fixtures.values() if "ocr/failures" in f["file"])
        ),
        "technical_failure_fixtures": sum(1 for f in core_atomic_fixtures.values() if "failures/technical" in f["file"]),
        "syntax_failure_fixtures": sum(1 for f in core_atomic_fixtures.values() if "failures/syntax" in f["file"]),
        "retry_sequences_count": len(retry_sequences_meta),
        "fallback_scenarios_count": len(fallback_scenarios_meta),
        "provider_specific_count": len(provider_fixtures),
        "total_fixture_payloads": len(core_atomic_fixtures) + len(provider_fixtures) + len(retry_sequences_meta) + len(fallback_scenarios_meta),
        "valid_json_payloads": len(core_atomic_fixtures) + len(provider_fixtures) + len(retry_sequences_meta) + len(fallback_scenarios_meta) - sum(1 for f in core_atomic_fixtures.values() if "failures/syntax" in f["file"]),
        "malformed_text_payloads": sum(1 for f in core_atomic_fixtures.values() if "failures/syntax" in f["file"]),
        "metadata_files_count": 3,
        "generator_validator_files_count": 2,
    }

    # Verify count consistency
    assert count_model["total_atomic_fixtures"] == (
        count_model["valid_atomic_responses"]
        + count_model["invalid_schema_fixtures"]
        + count_model["semantic_failure_fixtures"]
        + count_model["technical_failure_fixtures"]
        + count_model["syntax_failure_fixtures"]
    ), "Atomic fixture breakdown must exactly sum to total atomic fixtures!"

    assert count_model["total_fixture_payloads"] == (
        count_model["valid_json_payloads"] + count_model["malformed_text_payloads"]
    ), "Valid JSON + malformed text must exactly sum to total fixture payloads!"

    manifest = {
        "manifest_version": "1.1",
        "counts": count_model,
        "approved_internal_categories": [
            "document_comparison",
            "new_shipping_instruction",
            "invoice_query",
            "general",
            "spam"
        ],
        "approved_logical_reasons": [
            "missing_attachment",
            "unreadable_document",
            "wrong_or_uncertain_document_type",
            "missing_required_value",
            "uncertain_result",
            "conflicting_candidate_values",
            "processing_or_provider_failure"
        ],
        "retry_governance_limits": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "nested_total_invocation_cap": 6
        },
        "breakdown_by_category": {
            "classification": sum(1 for f in core_atomic_fixtures.values() if "classification/" in f["file"]),
            "role_resolution": sum(1 for f in core_atomic_fixtures.values() if "role_resolution/" in f["file"]),
            "extraction": sum(1 for f in core_atomic_fixtures.values() if "extraction/" in f["file"]),
            "ocr": sum(1 for f in core_atomic_fixtures.values() if "ocr/" in f["file"]),
            "technical_failures": sum(1 for f in core_atomic_fixtures.values() if "failures/technical" in f["file"]),
            "syntax_failures": sum(1 for f in core_atomic_fixtures.values() if "failures/syntax" in f["file"]),
            "retry_sequences": len(retry_sequences_meta),
            "fallback_scenarios": len(fallback_scenarios_meta),
            "provider_specific": len(provider_fixtures),
        },
        "fixtures": fixtures_meta,
        "retry_sequences": retry_sequences_meta,
        "fallback_scenarios": fallback_scenarios_meta,
    }

    manifest_path = BASE_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2)

    print(f"Generated {count_model['total_fixture_payloads']} synthetic AI fixture payloads.")
    print("Programmatic Counts:", count_model)
    print("Breakdown by Category:", manifest["breakdown_by_category"])


if __name__ == "__main__":
    main()
