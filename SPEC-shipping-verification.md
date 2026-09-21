# Specification: Shipping Document Verification Pipeline

## 1. Overview & Objective

Build an automated, LLM-first document verification pipeline that processes an email inbox (`sdoc-hackathon-bundle/inbox`) containing 520 operational shipping emails and their associated attachments (`sdoc-hackathon-bundle/attachments`), producing a `submission.json` file adhering strictly to `sample_submission.json`.

### Evaluation & Success Metrics
$$\text{Final Score} = 0.50 \times \text{End-to-End Defect Accuracy} + 0.30 \times \text{Stage-1 Macro-F1} + 0.20 \times \text{Stage-3 Defect-F1}$$
- **Reliability Axis**: Correctly escalating edge cases to `NEEDS_REVIEW` with valid reasons (`wrong_doc_type`, `missing_attachment`, `unreadable`, `missing_value`) rather than hallucinating or failing silently.

---

## 2. Architecture & Design Decisions

- **Core Engine**: LLM-First using Google Gemini (`gemini-2.5-flash` or `gemini-1.5-flash`).
- **Pluggable Document Ingestion**: 
  - Standard text / `.docx` / `.xlsx` extracted via local parsers.
  - Native Gemini Multimodal for PDF/scanned document ingestion.
  - Pluggable Google Cloud Document AI provider when GCP credentials are provided.
- **API Optimization**:
  - Stage 1 Classification: Batched requests (25–50 emails per prompt) reducing 520 emails to ~15 API calls.
  - Stage 2 & 3 Comparison: Dedicated per-email prompts for the 124 emails with document pairs.
- **State Management & Caching**:
  - File-based checkpoint cache (`.cache_pipeline.json`) to allow safe interrupts and instant resumes without re-calling the API.
- **Strict Verification**:
  - Schema validator ensuring all 520 email IDs are present and all output types match `sample_submission.json`.

---

## 3. The 7 Compared Fields & Comparison Rules

| Field Name | Description | Normalization & Matching Rule |
|---|---|---|
| `shipper` | Exporter / Consignor entity name | Case-insensitive, strip corporate suffixes (SDN BHD, LTD, LLC, GMBH), whitespace normalize. LLM confirms semantic equality. |
| `consignee` | Receiving entity name | Same as shipper. Must represent the same business entity. |
| `notify_party` | Party to be notified on arrival | Same as shipper/consignee. |
| `port_of_loading` | Origin port (POL) | Extract UN/LOCODE if present (e.g. `MYPKG`), match port name and country. Ignore header variations (e.g. `Load Port` vs `POL`). |
| `port_of_discharge` | Destination port (POD) | Extract UN/LOCODE if present (e.g. `PECLL`), match port name and country. |
| `container_count` | Number of containers | Extract numeric quantity (e.g. `1 x 40'HC` $\rightarrow$ count = 1). Mismatch if numbers differ. |
| `gross_weight_kg` | Cargo weight in kilograms | Normalize units (convert MT/lbs to KG if required, strip `KG`, commas). Match numeric value within tolerance $\pm 1$ kg. |

---

## 4. Pipeline Modules & Project Structure

```
d:\ship\
├── src\
│   ├── __init__.py
│   ├── config.py              # Environment settings, API keys, model selections
│   ├── cache.py               # Checkpoint and persistence manager
│   ├── parsers\
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract document parser
│   │   ├── text_parser.py     # Plain text parser (.txt)
│   │   ├── docx_parser.py     # Word document parser (.docx)
│   │   ├── excel_parser.py    # Excel sheet parser (.xlsx)
│   │   ├── pdf_parser.py      # PDF text extractor & corruption detector
│   │   └── docai_adapter.py   # Optional Google Cloud Document AI pluggable client
│   ├── llm\
│   │   ├── __init__.py
│   │   ├── client.py          # Gemini API wrapper with retry & rate limiting
│   │   └── prompts.py         # Batch classification and document comparison prompts
│   ├── pipeline\
│   │   ├── __init__.py
│   │   ├── stage1_classify.py # Batch email classification engine
│   │   ├── stage2_extract.py  # Attachment loader, corruption check, text extraction
│   │   ├── stage3_compare.py  # Field comparison, defect detection, NEEDS_REVIEW assignment
│   │   └── validator.py       # Validates output schema against sample_submission.json
│   └── run_pipeline.py        # Main CLI runner with progress bar and resume
├── .env.example               # Template for GEMINI_API_KEY
├── requirements.txt           # Python dependencies
└── SPEC-shipping-verification.md
```

---

## 5. Escalation & Defect Matrix (`NEEDS_REVIEW`)

| Trigger Condition | `status` | `review_reason` | `has_defect` | `defect_fields` |
|---|---|---|---|---|
| Corrupt PDF stream (`EOF marker not found`) | `NEEDS_REVIEW` | `unreadable` | `false` | `[]` |
| Image-only PDF with illegible text & vision failure | `NEEDS_REVIEW` | `unreadable` | `false` | `[]` |
| Email with only 1 attachment (e.g. SI only, no BL) | `NEEDS_REVIEW` | `missing_attachment` | `false` | `[]` |
| Attachment is not an SI or BL (e.g., photo, invoice) | `NEEDS_REVIEW` | `wrong_doc_type` | `false` | `[]` |
| Mandatory field missing or unextractable in SI or BL | `NEEDS_REVIEW` | `missing_value` | `false` | `[]` |
| All 7 fields extractable & match | `OK` | `null` | `false` | `[]` |
| $\ge 1$ of the 7 fields differ | `MISMATCH` | `null` | `true` | `[list of differing fields]` |
| Non-`BL_COMPARISON` categories (`SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`) | `OK` | `null` | `false` | `[]` |

---

## 6. Execution Commands

```bash
# Setup environment
pip install -r requirements.txt

# Set Gemini API key
# Copy .env.example to .env and fill GEMINI_API_KEY, or:
$env:GEMINI_API_KEY="your-key-here"

# Run full pipeline with caching and resume
python -m src.run_pipeline --bundle sdoc-hackathon-bundle --output submission.json

# Optional: Validate generated submission against sample
python -m src.pipeline.validator submission.json sdoc-hackathon-bundle/sample_submission.json
```
