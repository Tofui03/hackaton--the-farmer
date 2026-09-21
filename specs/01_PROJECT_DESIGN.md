# 01_PROJECT_DESIGN.md — System Architecture & Technical Design

> **Status**: Approved & Protected  
> **Implements**: [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md)

---

## 1. High-Level Architecture & Dataflow

```
                     ┌──────────────────────────────┐
                     │   Inbox Directory (520 JSON) │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │  Stage 1: Email Classifier   │
                     │  (Batched LLM + Heuristics)  │
                     └──────────────┬───────────────┘
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼                                     ▼
      [Non-Comparison Email]                 [document_comparison]
     (SI_REQUEST, INVOICE, SPAM, ...)                  │
                 │                                     ▼
                 │                       ┌───────────────────────────┐
                 │                       │  Stage 2: Doc Extractor   │
                 │                       │  (Pluggable File Parsers) │
                 │                       └─────────────┬─────────────┘
                 │                                     │
                 │                   ┌─────────────────┴─────────────────┐
                 │                   ▼                                   ▼
                 │           [Corrupt / Missing]                [Valid Document Pair]
                 │        (missing_attachment, unreadable)               │
                 │                   │                                   ▼
                 │                   │                     ┌───────────────────────────┐
                 │                   │                     │  Stage 3: Comparator      │
                 │                   │                     │  (Semantic Normalization) │
                 │                   │                     └─────────────┬─────────────┘
                 │                   │                                   │
                 ▼                   ▼                                   ▼
     ┌─────────────────────────────────────────────────────────────────────────┐
     │                      Output Serializer & Dual Exporter                  │
     │   - submission.json (Official Competition Schema)                       │
     │   - audit_report.json (Strict Output Contract Schema)                   │
     └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Directory Layout

```text
d:\ship\
├── AGENTS.md                 # Agent behavioral boundaries & governance
├── specs/                    # Specification suite
│   ├── 00_PRODUCT_SPEC.md    # Business context & capabilities
│   ├── 01_PROJECT_DESIGN.md  # System architecture & design
│   ├── 02_AI_PIPELINE_SPEC.md# AI model & prompt specs
│   ├── 03_DATA_CONTRACTS.md  # JSON contracts & API schemas
│   ├── 04_UI_UX_SPEC.md      # Dashboard & Swagger UX
│   ├── 05_TEST_PLAN.md       # Test matrix & verification
│   └── 06_TASKS.md           # Execution queue & DoD
├── src/
│   ├── config.py             # Environment & credentials manager
│   ├── cache.py              # Checkpoint persistence manager
│   ├── parsers/              # Multi-format document parsers
│   │   ├── base.py           # Abstract BaseParser & DocumentParseResult
│   │   ├── text_parser.py    # .txt parser with multi-encoding fallback
│   │   ├── docx_parser.py    # .docx table & paragraph extractor
│   │   ├── excel_parser.py   # .xlsx sheet extractor
│   │   ├── pdf_parser.py     # .pdf stream corruption & scanned detector
│   │   └── docai_adapter.py  # Pluggable Google Cloud Document AI adapter
│   ├── llm/
│   │   ├── client.py         # Gemini API client with exponential backoff
│   │   └── prompts.py        # Batched classification & comparison prompts
│   └── pipeline/
│       ├── schema.py         # Pydantic schemas & format converters
│       ├── stage1_classify.py# Email intent classifier (Secret 4)
│       ├── stage2_extract.py # Attachment pairing & HITL triage (Secret 3)
│       ├── stage3_compare.py # 7-field semantic comparator (Secrets 1 & 2)
│       └── validator.py      # Output schema compliance validator
├── docs/                     # GitHub Pages static dashboard
│   ├── index.html            # Single-page interactive audit dashboard
│   ├── audit_report.json     # Strict contract data source
│   └── submission.json       # Competition submission data source
├── tests/                    # Pytest test suite (16 automated tests)
├── main.py                   # ASGI application entrypoint (Render default)
├── app.py                    # FastAPI server definition & routes
├── Procfile                  # Render process runner
└── render.yaml               # Render Infrastructure-as-Code Blueprint
```

---

## 3. Pluggable Document Parsing Strategy

The document parser subsystem routes attachments based on file extension:
- `.txt`: Decodes via UTF-8, Latin-1, or CP1252.
- `.docx`: Parses structured tables and body paragraphs into formatted key-value blocks.
- `.xlsx`: Extracts tabular rows across all workbook sheets.
- `.pdf`: Detects stream truncation (`PdfStreamError` $\rightarrow$ `is_corrupted: true`). Detects image-only scans ($\text{char count} < 20 \rightarrow \text{is\_scanned: true}$).
- `DocAI Adapter`: Activated if `DOCAI_PROCESSOR_ID` and GCP credentials are configured.

---

## 4. Deployment Topology

1. **Render Web Service (Dynamic API)**:
   - Framework: FastAPI + Uvicorn
   - Entrypoint: `main:app`
   - Port: `$PORT` (bound to `0.0.0.0`)
   - Endpoints: `GET /`, `GET /health`, `GET /audit`, `GET /audit/{email_id}`, `POST /verify`, `GET /submission`, `GET /docs`.
2. **GitHub Pages (Static Dashboard)**:
   - Automated deployment via GitHub Actions ([`.github/workflows/pages.yml`](file:///d:/ship/.github/workflows/pages.yml)).
   - Static single-page dashboard ([`docs/index.html`](file:///d:/ship/docs/index.html)).
