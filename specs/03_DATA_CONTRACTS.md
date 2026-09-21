# 03_DATA_CONTRACTS.md — Data Contracts & Interface Schemas

> **Status**: Approved  
> **Implements**: [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md)

---

## 1. Schema A: Strict Output Contract (Per-Email Audit Record)

This is the primary deliverable contract requested by the operator and returned by the `/audit` endpoints:

```json
{
  "email_id": "email_025",
  "category": "document_comparison",
  "mismatch_detected": true,
  "result_summary": "Mismatches detected: container_count (SI: 6 / BL: 5)",
  "discrepancies": [
    {
      "field": "container_count",
      "si_value": 6,
      "bl_value": 5
    }
  ],
  "hitl_escalation": {
    "needed": false,
    "reason": null,
    "evidence": null
  }
}
```

### Allowed Values:
- **`category`**: `"document_comparison"` | `"new_si_request"` | `"invoice_query"` | `"general_message"` | `"spam"`
- **`mismatch_detected`**: `boolean` (`true` only when genuine defect is present)
- **`result_summary`**: Exactly `"No mismatch detected"` if all 7 fields agree; or `"Mismatches detected: ..."` with `SI: <val> / BL: <val>` side-by-side; or `"Human review required: <reason>"`.
- **`discrepancies`**: Array of objects with `field`, `si_value`, `bl_value`. Empty if match or non-comparison.
- **`hitl_escalation.reason`**: `null` | `"wrong_doc_type"` | `"missing_attachment"` | `"unreadable"` | `"missing_value"`

---

## 2. Schema B: Competition Submission Contract (`submission.json`)

Formatted exactly to match `sdoc-hackathon-bundle/sample_submission.json`:

```json
{
  "email_001": {
    "category": "BL_COMPARISON",
    "status": "OK",
    "review_reason": null,
    "defect_fields": [],
    "has_defect": false
  },
  "email_025": {
    "category": "BL_COMPARISON",
    "status": "MISMATCH",
    "review_reason": null,
    "defect_fields": ["container_count"],
    "has_defect": true
  },
  "email_507": {
    "category": "BL_COMPARISON",
    "status": "NEEDS_REVIEW",
    "review_reason": "missing_attachment",
    "defect_fields": [],
    "has_defect": false
  }
}
```

---

## 3. Schema C: REST API Contract

| Route | Method | Request Payload | Response | Description |
|---|---|---|---|---|
| `/health` | `GET` | None | `{"status": "healthy"}` | Health probe for Render |
| `/audit` | `GET` | Query: `category`, `mismatch_only`, `hitl_only` | `List[AuditOutputRecord]` | Full audit dataset |
| `/audit/{email_id}` | `GET` | Path: `email_id` | `AuditOutputRecord` | Single email audit record |
| `/verify` | `POST` | `{"email_id": str, "si_text": str, "bl_text": str}` | `AuditOutputRecord` | Real-time dynamic document audit |
| `/submission` | `GET` | None | `Dict[str, Any]` | Official `submission.json` |
| `/docs` | `GET` | None | HTML | Interactive OpenAPI / Swagger documentation |
