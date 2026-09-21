# 02_AI_PIPELINE_SPEC.md — AI Pipeline & Behavioral Specification

> **Document Type**: AI Pipeline Behavioral Contract & Component Specification  
> **Implements**: [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md), [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md)  
> **Source of Truth**: [`Shipping Document Verification Use Case.pdf`](file:///d:/ship/Shipping%20Document%20Verification%20Use%20Case.pdf)  
> **Governance**: [`AGENTS.md`](file:///d:/ship/AGENTS.md)  
> **Status**: APPROVED / BASELINED  
> **Revision**: 3.1 (Approved parsing-recovery clarification, 2026-09-22; see [amendment](AMENDMENT_2026-09-22.md))

---

## 1. Purpose

This specification defines the behavioral contract, input/output contracts, error boundaries, uncertainty taxonomy, and execution strategy for every AI-assisted and deterministic component in the Shipping Document Verification pipeline.

### Core Architectural Principles:
1. **AI-on-Demand Efficiency**: AI is utilized where perception, unstructured layout interpretation, and complex semantic disambiguation are required. When deterministic parsers, metadata, or pattern matchers reliably establish ground truth, unnecessary external AI invocations are avoided without sacrificing accuracy.
2. **Deterministic Governance**: AI models never act as final arbiters of equality comparison, numerical calculations, data contract validation, or business gatekeeping.
3. **Field-Level Source-Grounded Reliability**: Document usability is assessed at the level of the seven mandatory comparison fields. A case proceeds when all seven fields are established with source-grounded evidence, avoiding false failures caused by unreadable non-critical content.
4. **Resilient Fallback Hierarchy**: Technical and semantic failures transition through bounded retries and validated fallback paths; human escalation occurs only when reliable extraction cannot be achieved.
5. **Zero Requirement Drift**: Strictly preserves baselined specifications without inventing undocumented business rules or numerical ranges.

---

## 2. Required Pipeline & Execution Model

The system enforces a multi-stage execution model combining deterministic processing and on-demand AI assistance:

```
Inbound Email Record
        │
        ▼
Stage 1: Email Intent Classification (AI or Deterministic Rules)
        │
        ├── Non-Comparison Category ──► Emit Classification Record (Terminate Processing)
        │
        └── document_comparison
                │
                ▼
Stage 2: Attachment Identification & Validation
        │  • Primary: Deterministic metadata, filenames, MIME & header evidence
        │  • On-Demand AI: Semantic inspection if deterministic pairing is ambiguous
        │
        ├── Missing / Unresolvable Attachments ──► HITL Escalation
        │
        ▼
Stage 2B: Document Parsing (Format-Specific Parsers)
        │
        ├── Parser Failure / Unusable Text (including Scanned / Image-Only)
        │       │
        │       ▼
        │   Assess Applicable Recovery / OCR / Vision
        │       │
        │       ├── Unavailable / Exhausted / Unreliable ─► HITL (Preserve Partial Results)
        │       │
        │       └── Validated Usable Content
        │               │
        ▼               ▼
Stage 3A: Structured Field Extraction
        │  • Deterministic: Clear structured fields / plain-text patterns
        │  • On-Demand AI: Unstructured text, complex tables, ambiguous layouts
        │
        ▼
Deterministic Normalization (Formatting, Exact Units: MT -> kg)
        │
        ▼
Field-Level Reliability Gate (All 7 Mandatory Fields)
        │
        ├── One or More Fields Fail Gate ────────► HITL Escalation (Preserve Partial Results)
        │
        └── All 7 Fields Reliable
                │
                ▼
Stage 3B: Deterministic Comparison (SI vs draft BL Evaluation)
        │
        ├── 7 Fields Match ─────────────────────► "No mismatch detected"
        │
        └── Discrepancies Found ────────────────► Flagged Defects (SI: x / BL: y)
```

---

## 3. AI Responsibility Boundaries

Responsibilities are partitioned between AI capabilities and deterministic software authority:

```
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
│           AI PERMITTED ROLES                 │  │       DETERMINISTIC AUTHORITY ROLES          │
│   (Perception & Semantic Interpretation)     │  │       (Validation, Calculation & Logic)      │
├──────────────────────────────────────────────┤  ├──────────────────────────────────────────────┤
│ • Email intent classification                │  │ • Final equality comparison (== / !=)        │
│ • Semantic SI vs draft BL document pairing   │  │ • Container count integer matching          │
│   (when filenames/metadata are ambiguous)    │  │ • Gross weight exact equality checking       │
│ • Extraction from unstructured text & tables │  │ • Final mismatch boolean determination       │
│ • Complex layout and table cell correlation  │  │ • Structural and schema contract validation  │
│ • OCR / vision interpretation for scans      │  │ • Business-rule enforcement & gatekeeping    │
│ • Field label alias mapping (e.g. POL -> pol)│  │ • Exact unit conversion (MT * 1000 -> kg)    │
│ • Extracting source-grounded context evidence│  │ • Prevention of missing-value guessing       │
│ • Detecting unreadable / degraded text       │  │ • Primary attachment pairing via metadata    │
└──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘
```

> [!CAUTION]
> Under **NO** circumstances may an AI model be the final authority for deciding whether two normalized values match or whether an email contains a discrepancy. Comparison is strictly a deterministic software function.

---

## 4. Stage 1 — Email Classification Specification

### 4.1 Target Categories
Every incoming email MUST be categorized into exactly one of five operational classes:
1. `document_comparison`: Requests to check, review, or compare a draft Bill of Lading against a Shipping Instruction.
2. `new_shipping_instruction`: Submissions, requests, or operational reminders concerning new Shipping Instructions.
3. `invoice_query`: Inquiries regarding billing, freight charges, terminal handling charges (THC), or payment status.
4. `general`: Routine operational updates, vessel schedule notices, sailing schedules, or general chatter.
5. `spam`: Unsolicited commercial advertisements, sales solicitations, or irrelevant spam.

### 4.2 Available Inputs
- `email_id`: Unique identifier string.
- `sender`: Sender email address / header.
- `subject`: Email subject line.
- `body`: Email text body.
- `attachment_filenames`: List of attached filenames.

### 4.3 Logical Output Contract
```json
{
  "category": "document_comparison | new_shipping_instruction | invoice_query | general | spam",
  "reason": "Clear explanation citing operational indicators",
  "evidence": [
    "Source-grounded string snippet from subject, body, or relevant message context"
  ],
  "confidence_indicator": "HIGH | MEDIUM | LOW"
}
```

### 4.4 Execution & Validation Rules
1. **Decoupling Intent from Attachment Count**: Stage 1 evaluates semantic intent independently of attachment completeness. If an incoming email requests draft Bill of Lading verification but attaches zero files (or missing files), its intent is still `document_comparison`. It MUST proceed to Stage 2, where attachment validation will formally detect the missing file(s) and escalate to HITL with `missing_attachment`. Deterministic preprocessing may normalize or collect input evidence, but attachment count **MUST NOT** act as a negative intent-classification gate.
2. **Generalized Classification Evidence**: Classification evidence is NOT restricted to rigid keyword matches; any source-grounded text span, conversational context, or relevant message header constitutes valid evidence.
3. **Diagnostic-Only Confidence**: A model-reported `confidence_indicator` is strictly diagnostic metadata. It **MUST NOT** independently determine whether processing continues.
4. **Invalid Output Handling**: Malformed JSON or invalid category enums trigger bounded semantic retries.
5. **First-Stage Veto**: Non-comparison emails terminate processing immediately after classification, emitting an audit record without invoking document parsers.

---

## 5. Attachment Identification Specification

### 5.1 Deterministic-First Identification
The system identifies the pair of attachments required for comparison using a tiered strategy:
1. **Tier 1 (Deterministic Metadata & Filename Patterns)**:
   - Evaluates file extensions, MIME types, and filename conventions (e.g. `*_SI.*`, `*_BL.*`, `*Draft*`, `*Instruction*`).
   - If deterministic evidence uniquely and unambiguously identifies exactly one SI and one draft BL, **AI semantic document identification is bypassed**.
2. **Tier 2 (On-Demand AI Semantic Inspection)**:
   - Invoked ONLY when deterministic evidence is ambiguous, incomplete, or filenames are generic (e.g. `doc1.pdf`, `attachment.docx`).
   - The AI inspects document headers and opening text blocks (e.g. *"Shipping Instruction"*, *"Draft Bill of Lading"*) to classify document roles.

### 5.2 Failure & Escalation Conditions
- **Missing Attachments**: Email contains fewer than two attachments, or either SI or draft BL is absent.
- **Multiple Ambiguous Candidates**: Email attaches multiple candidate SIs or draft BLs and identity cannot be uniquely resolved.
- **Wrong / Unrelated Documents**: Attachments represent commercial invoices, packing lists, or certificates of origin.
- **Escalation**: Unresolved pairing triggers HITL review.

---

## 6. Document Parsing & Text Usability Specification

Document parsing (extracting raw text and table structures from binary container formats) is decoupled from semantic field extraction.

### 6.1 Supported Formats by Requirement Level
- `CORE`: Plain text documents (`.txt`).
- `ADVANCED`: Word documents (`.docx`), PDF documents (`.pdf`), and image-only / scanned documents.
- `DESIGN EXTENSION`: Excel spreadsheets (`.xlsx`).

### 6.2 Standardized Parser Result States
- `SUCCESS`: File parsed cleanly; text and table streams decoded with high integrity.
- `PARTIAL`: File parsed with minor warnings (e.g. unsupported font encodings, trailing junk bytes).
- `UNREADABLE`: Binary stream corrupted, truncated stream (missing EOF), password protected, or empty extraction.
- `UNSUPPORTED`: File format or MIME type not supported by registered parser suite.

> [!IMPORTANT]
> Parsers **MUST NOT** silently return an empty string (`""`) on extraction failures. An empty extraction must be explicitly recorded as `UNREADABLE`.

---

## 7. OCR & Multimodal Vision Specification

### 7.1 Text Usability Validation & Invocation Trigger
OCR / Vision capabilities are invoked on-demand when a deterministic **Text Usability Validation** step indicates that the digital text layer is insufficient:
1. Parser extraction is empty or returns `UNREADABLE`.
2. Extracted text stream is predominantly corrupted, garbled, or suffers font encoding failures.
3. Document structure cannot be recovered by text parsers.
4. Document is identified as a scanned or rasterized image document lacking an embedded digital font layer.
5. Mandatory shipment fields cannot be reliably located due to text layer degradation.

### 7.1.1 Parser Failure and Recovery Applicability
A parser exception is recorded visibly and assessed for applicable recovery; it is not an unconditional shortcut past the recovery policy. Where source bytes or pages remain usable, attempt the applicable approved fallback or OCR/Vision route under §§14–15. If the source cannot be opened or rendered and no applicable approved recovery exists, record that limitation and escalate without attempting an impossible OCR operation. If recovery is attempted, continue only with validated usable content; escalate when applicable bounded recovery is exhausted or required content remains unreliable. Preserve reliable fields, comparisons, and evidence under §12.2 on every escalation path.

### 7.2 Input & Processing Boundaries
- **Input**: Raw page image bytes rendered at readable resolution, or binary image streams.
- **Expected Output**: Structured candidate text blocks accompanied by source-grounded evidence.
- **Hallucination Prevention**: If a field is smudged, cut off, or illegible, the OCR adapter **MUST** mark the field as `MISSING` or `UNCERTAIN`. Synthesizing plausible shipment numbers or dates is **strictly forbidden**.

---

## 8. Structured Field Extraction Specification

Stage 3A extracts the seven mandatory fields mandated by the authoritative use case:
1. `shipper`: Shipper / Consignor legal name and address.
2. `consignee`: Consignee legal name and address (or "TO ORDER" phrasing).
3. `notify_party`: Notify Party legal name and address (or "SAME AS CONSIGNEE").
4. `port_of_loading`: Port where cargo is loaded onto the vessel.
5. `port_of_discharge`: Port where cargo is discharged from the vessel.
6. `container_count`: Total number of shipping containers.
7. `gross_weight_kg`: Total cargo gross weight normalized to kilograms.

### 8.1 Tiered Extraction (Deterministic-First + On-Demand AI)
1. **Deterministic Extraction**: High-confidence regular expressions, tabular column mappings, and structured key-value extractors MAY extract clearly formatted fields first.
2. **On-Demand AI Extraction**: Invoked when deterministic extraction is incomplete, ambiguous, encounters complex multi-line blocks, or cannot interpret table layouts.

### 8.2 Logical Extraction Entity Model
For each field, the extractor emits a structured entity object:
```json
{
  "field_name": "gross_weight_kg",
  "extracted_value": 22000.0,
  "raw_text": "22 MT",
  "source_document": "SI",
  "evidence": "Total Gross Weight: 22 MT (Twenty-Two Metric Tons)",
  "status": "FOUND | MISSING | UNCERTAIN"
}
```

---

## 9. Field Label Semantics

### 9.1 Field Label Equivalence (Permitted Mapping)
The extraction system maps typographical and domain label variations to canonical keys:
- `port_of_loading`: `Port of Loading`, `Load Port`, `Loading Port`, `POL`, `Port of Load`
- `port_of_discharge`: `Port of Discharge`, `Discharge Port`, `Discharging Port`, `POD`, `Port of Delivery`
- `gross_weight_kg`: `Gross Weight`, `Total Weight`, `G.W.`, `Cargo Weight`, `Gross Wt`, `Weight (KG)`
- `container_count`: `Container Count`, `Total Containers`, `Qty of Units`, `No. of Containers`, `Quantity`

### 9.2 Field Value Equivalence (Preserved TBD Boundary)
Label equivalence does **NOT** authorize value equivalence assumptions:
- **`DEC-P06C (Port Semantic Equivalence)`**: `[TBD]` — System must NOT assume UN/LOCODE, city names, and terminal names are equivalent without an approved canonical mapping specification.
- **`DEC-P06D (Organization Name Equivalence)`**: `[TBD]` — System must NOT broadly strip legal entity suffixes without an approved specification amendment.
- **`DEC-P06E (Numeric Tolerance)`**: `[TBD]` — System must perform exact normalized comparison without arbitrary $\pm 1\text{ kg}$ tolerances.

---

## 10. Normalization Boundary

Normalization occurs **after** extraction and **before** comparison using approved deterministic transformations:
1. **Formatting Normalization (`DEC-P06A`)**:
   - NFKC Unicode normalization.
   - Trimming leading/trailing whitespace and collapsing internal whitespace to single spaces.
   - Stripping thousand-separator commas (e.g. `"22,000"` $\rightarrow 22000$).
   - Standardizing case for non-entity codes (e.g. uppercase for port codes).
2. **Unit Normalization (`DEC-P06B`)**:
   - Mathematically exact conversion: $\text{MT} \times 1000 \rightarrow \text{kg}$.
   - Container count extracted as a discrete Arabic integer (e.g. `"3 x 40'HC"` $\rightarrow 3$).

---

## 11. Deterministic Comparison Boundary

### 11.1 SI is the Reference Document for Comparison
The Shipping Instruction (SI) contains the customer's intended shipment details and serves as the reference document for the check.
> [!IMPORTANT]
> The SI is **NOT** treated as an infallible absolute truth. If the SI itself is missing, unreadable, incomplete, conflicting, or uncertain, the system **MUST NOT** force a comparison; it MUST route the case to HITL.

### 11.2 Deterministic Comparison Rule
The AI subsystem **MUST NOT** execute or influence the comparison decision:

$$\text{SI Canonical Value} \quad \stackrel{\text{Deterministic Comparator}}{=\!=\;/\;\neq} \quad \text{BL Canonical Value}$$

- If all seven fields match: Returns `"No mismatch detected"`.
- If any field differs: Emits explicit defect record listing the mismatched field and side-by-side values (`SI: <val> / BL: <val>`).

---

## 12. Field-Level Reliability Gate

Reliability is evaluated **per required comparison field**, rather than requiring the entire document text to be 100% pristine. A document proceeds to comparison when there is **sufficient reliable content to establish all seven required fields**.

```
Required Comparison Field
           │
           ▼
     Value Extracted? ──────── No ────► MISSING ────────► HITL
           │ Yes
           ▼
    Source-Grounded? ──────── No ────► UNCERTAIN ──────► HITL
           │ Yes
           ▼
      Unambiguous? ────────── No ────► CONFLICTING ────► HITL
           │ Yes
           ▼
    Schema / Type Valid? ──── No ────► UNCERTAIN ──────► HITL
           │ Yes
           ▼
    Normalization Valid? ──── No ────► UNCERTAIN ──────► HITL
           │ Yes
           ▼
        RELIABLE ───────────► Ready for Deterministic Comparison
```

### 12.1 Gate Validation Criteria:
1. **Value Extracted**: Value is present and non-null.
2. **Source-Grounded**: Backed by verifiable context (text span, table cell, page/section location, OCR region, or document metadata).
3. **Unambiguous**: No conflicting or mutually exclusive candidate values within the document.
4. **Schema / Type Valid**: Conforms structurally to expected types (e.g. integer for container count, float for weight). **No arbitrary business range restrictions** (e.g. maximum weight) are invented.
5. **Normalization Valid**: Successfully passes approved exact unit conversion and formatting clean-up.

### 12.2 Partial Result Preservation During HITL
When one or more required fields are unresolved or fail the reliability gate:
1. **Preserve Reliable Fields**: Already extracted and validated fields **MUST NOT** be discarded simply because another field fails.
2. **Preserve Deterministic Comparisons**: Independent deterministic comparison results for fields that are reliable on both documents MUST be preserved.
3. **Preserve Source-Grounded Evidence**: Evidence associated with validated fields MUST be retained.
4. **Mark Case as Requiring Review**: The overall record status is flagged as requiring human review.
5. **No False Clean Passes**: The system **MUST NOT** emit a definitive `"No mismatch detected"` final status until all seven required fields are resolved.
6. **Dual Context Delivery**: The human operator receives both completed reliable work and the unresolved fields/reasons requiring attention.

> [!NOTE]
> The exact application-level schema for partial results belongs to [`specs/03_DATA_CONTRACTS.md`](file:///d:/ship/specs/03_DATA_CONTRACTS.md).

---

## 13. Logical Human-in-the-Loop (HITL) Trigger Model

### 13.1 Logical Behavioral Categories
1. **`missing_attachment`**: Fewer than two attachments, or missing required SI / draft BL.
2. **`unreadable_document`**: Parser failure, corrupt file stream, or illegible scan where text usability validation fails.
3. **`wrong_or_uncertain_document_type`**: Attachments do not represent an SI and draft BL pair, or multiple conflicting candidates exist.
4. **`missing_required_value`**: One or more of the 7 mandatory fields is absent or empty in either document.
5. **`uncertain_result`**: Extraction produces ambiguous interpretations that fail the reliability gate.
6. **`conflicting_candidate_values`**: Multiple distinct candidate values exist for a single field in the same document.
7. **`processing_or_provider_failure`**: External AI service timeouts, rate limits, or parse exceptions persist after retry exhaustion AND approved fallbacks cannot produce a validated result.

> [!IMPORTANT]
> **Provider Failure HITL Condition**: Provider failure alone does **NOT** automatically require HITL. `processing_or_provider_failure` triggers HITL only when:
> 1. Applicable retries are exhausted, AND
> 2. Approved fallback paths are unavailable or fail validation, AND
> 3. The required result cannot be produced reliably.
> If a validated deterministic fallback produces sufficient source-grounded results, processing continues!

### 13.2 Required Escalation Payload
Every escalation record must include:
- `email_id`: Impacted email identifier.
- `processing_stage`: Stage where failure occurred.
- `review_reason`: Applicable behavioral category.
- `affected_document`: Document filename or reference path.
- `affected_field`: Name of the specific field if applicable.
- `candidate_value`: Extracted candidate value if one existed prior to ambiguity.
- `source_evidence`: Source-grounded context (text span, table cell, page location, or exception context).
- `retry_info`: Number of retries attempted prior to escalation.

### 13.3 Operator Feedback Capability
Human review must be capable of confirming or correcting the findings and updating the final report, consistent with the source use case (PDF Page 2).

---

## 14. Retry Governance

Retries are strictly segregated into Technical and Semantic categories:

### 14.1 Bounded Technical Retries `[APPROVED CONFIGURABLE DEFAULT: DEC-AI-P01]`
- **Trigger**: HTTP 429 (Rate Limit), HTTP 503 (Unavailable), network timeout, temporary provider drop.
- **Strategy**: Exponential backoff with jitter (base delay 1.0s, multiplier 2.0).
- **Default Parameter Limit**: Up to 3 attempts `[CONFIGURABLE DEFAULT]`.
- **Governance**: Configurable operational parameter; may be adjusted via runtime configuration without an architecture specification amendment.
- **Exhaustion Behavior**: Transition to stage-specific fallback; if fallback fails $\rightarrow$ HITL (`processing_or_provider_failure`).

### 14.2 Bounded Semantic Retries `[APPROVED CONFIGURABLE DEFAULT: DEC-AI-P02]`
- **Trigger**: Malformed JSON syntax, missing required contract keys, invalid category enums.
- **Strategy**: Immediate re-prompt appending schema validation error message for self-correction.
- **Default Parameter Limit**: Up to 2 attempts `[CONFIGURABLE DEFAULT]`.
- **Governance**: Configurable operational parameter; may be adjusted via runtime configuration without an architecture specification amendment.
- **Exhaustion Behavior**: Transition to stage-specific fallback; if fallback fails $\rightarrow$ HITL (`uncertain_result`).

> [!IMPORTANT]
> Retries MUST be bounded and non-infinite. Endless loops and silent conversion of failures into fabricated results are strictly prohibited.

---

## 15. Stage-Specific Fallback Matrix

| Pipeline Stage | Primary Execution Path | Fallback Path | Validation & Guardrail Before Continuing | Escalation Trigger if Fallback Fails |
|---|---|---|---|---|
| **Stage 1 (Classification)** | AI intent classifier (or deterministic rule if clear) | Local deterministic keyword & header rule engine | Must match 1 of 5 categories with source-grounded message evidence; intent evaluated independently of attachment count. | Ambiguous or unsupported $\rightarrow$ HITL (`uncertain_result`). |
| **Stage 2 (Attachment Triage)**| Deterministic metadata, filenames & MIME evidence | On-demand AI semantic document inspection | Exactly one SI and one draft BL must be unambiguously identified and validated. | Ambiguous, missing, or multiple candidates $\rightarrow$ HITL (`missing_attachment` / `wrong_or_uncertain_document_type`). |
| **Stage 2B (Parsing & OCR)** | Format-specific parsers; OCR if usability validation fails | Local fallback text parser or alternative OCR engine | Must recover sufficient readable text to locate the seven comparison fields. | Content insufficient to establish fields $\rightarrow$ HITL (`unreadable_document` / `processing_or_provider_failure`). |
| **Stage 3A (Field Extraction)** | Deterministic extraction for clear patterns; AI for complex layouts | Local deterministic regex & key-value alias pattern matcher | Every extracted field must be source-grounded; all 7 mandatory fields must pass the Reliability Gate. | Any field missing or conflicting $\rightarrow$ HITL (`missing_required_value` / `conflicting_candidate_values`). |

> [!CAUTION]
> **Fallback Output Invariance**: Fallback success alone does NOT mean the result is reliable. Every fallback output MUST pass deterministic validation and have sufficient source-grounded evidence. If fallback output remains ambiguous, incomplete, unsupported, or fails validation $\rightarrow$ HITL.

---

## 16. Structured Output Validation

All data returned by AI models must pass strict programmatic validation before entering downstream stages:

```python
class EmailClassificationOutput(BaseModel):
    category: Literal[
        "document_comparison",
        "new_shipping_instruction",
        "invoice_query",
        "general",
        "spam"
    ]
    reason: str
    evidence: List[str]
    confidence_indicator: Literal["HIGH", "MEDIUM", "LOW"]

class ExtractedFieldEntity(BaseModel):
    field_name: Literal[
        "shipper", "consignee", "notify_party",
        "port_of_loading", "port_of_discharge",
        "container_count", "gross_weight_kg"
    ]
    extracted_value: Optional[Union[str, int, float]] = None
    raw_text: Optional[str] = None
    source_document: Literal["SI", "BL"]
    evidence: Optional[str] = None
    status: Literal["FOUND", "MISSING", "UNCERTAIN"]
```

- Extra / unexpected fields are discarded.
- Type mismatches or schema validation failures immediately trigger a bounded Semantic Retry.
- Invalid AI output must NEVER directly reach the comparison stage.

---

## 17. Prompt Governance

All prompts used across the pipeline are treated as controlled software artifacts:
1. **Semantic Versioning**: Every prompt template carries an explicit version ID (e.g. `PROMPT-CLS-V2.0`, `PROMPT-EXT-V2.0`).
2. **Explicit Uncertainty Instruction**: Every extraction prompt must include the directive:
   > *"If a field is not explicitly present in the document text, return null and set status to 'MISSING'. DO NOT extrapolate, infer, or fabricate shipment information."*
3. **Strict JSON Mode**: Prompts mandate JSON format with exact schema definitions.
4. **Zero Dataset Contamination**: Prompts **MUST NOT** include hardcoded email IDs, specific filenames, or answers derived from evaluation datasets.

---

## 18. Provider Abstraction (`DEC-P01`)

The pipeline interacts with AI providers strictly through the abstract `BaseAIAdapter` interface:

```python
class BaseAIAdapter(ABC):
    @abstractmethod
    def classify_email(self, email_input: dict) -> dict:
        """Classifies email into one of five operational categories."""
        pass

    @abstractmethod
    def extract_document_fields(self, doc_text: str, doc_type: str) -> dict:
        """Extracts seven mandatory shipment fields from document text."""
        pass

    @abstractmethod
    def extract_from_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """Extracts text and shipment fields from scanned/image-only documents."""
        pass
```

- **Initial Implementation**: `GeminiAIAdapter` (utilizing Google GenAI SDK).
- **Decoupling Guarantee**: No model-specific imports, headers, or parameters may leak into pipeline orchestration logic.

---

## 19. Security & Data Handling

1. **Data Transmission Disclosure**: Inbound email text, SI documents, draft BL documents, and rendered page images are transmitted to external AI APIs when cloud providers are active.
2. **Secrets Protection**: API credentials (`GEMINI_API_KEY`, etc.) MUST be injected exclusively via runtime environment variables. API keys must NEVER be logged, written to disk, or included in prompts.
3. **No Compliance Fabrication**: The system makes no unsupported claims regarding SOC2, ISO, or HIPAA compliance; data transmission is treated as an operational consideration.

---

## 20. Observability & Audit Trail

Every AI invocation produces an immutable audit record containing:
- `pipeline_stage`: Active execution stage.
- `provider_adapter`: Active adapter name (e.g. `GeminiAIAdapter`, `MockAdapter`).
- `model_identifier`: Exact model version reported by the provider.
- `prompt_version`: Version identifier of the prompt template used.
- `token_usage`: Prompt and completion token counts (if reported by provider).
- `latency_ms`: Round-trip execution latency in milliseconds.
- `retry_count`: Number of retries required.
- `fallback_applied`: Boolean indicating whether heuristic fallback was invoked.

---

## 21. Testability Specification

To guarantee reliable CI/CD and offline verification, every AI-assisted component must be fully testable without external network access:

1. **Mock AI Adapters (`MockAIAdapter`)**: Simulates provider responses for classification, extraction, and image handling.
2. **Deterministic Fixtures**: Predefined email and document fixtures testing:
   - Clean 7-field match.
   - Clean 7-field mismatch (container count and weight defects).
   - Malformed / corrupted JSON outputs from model.
   - Missing mandatory fields.
   - Ambiguous classification inputs.
   - Technical timeout and 429 rate limit triggers.
3. **Offline Test Gate**: `pytest tests/` must execute 100% offline with zero live API dependencies.

---

## 22. AI Pipeline Traceability Matrix (RTM)

| Requirement ID | Requirement Level | AI Pipeline Stage | AI Responsibility | Deterministic Responsibility | Failure Path | Automated Test Target |
|---|---|---|---|---|---|---|
| **FR-001** | `CORE` | Ingestion | None | JSON file parsing & record loading | File error $\rightarrow$ Halt | `test_pipeline.py` |
| **FR-002** | `CORE` | Stage 1 (Classify) | Semantic intent categorization (or deterministic rules) | Input sanitization & enum validation | Invalid JSON $\rightarrow$ Semantic retry $\rightarrow$ Stage-1 fallback | `test_classification_heuristics` |
| **FR-003** | `CORE` | Stage 1 (Gatekeeper)| None | Gating: only `document_comparison` proceeds | Non-comparison $\rightarrow$ Early exit | `test_classification_heuristics` |
| **FR-004** | `CORE` | Stage 1 (Gatekeeper)| None | Terminate non-comparison processing | Non-comparison $\rightarrow$ Output record | `test_classification_heuristics` |
| **FR-005** | `CORE` | Stage 2B (Parsing) | None | Extract plain text from `.txt` files | Unreadable file -> applicable recovery assessment (§7.1.1) -> HITL if unresolved | `test_text_parser` |
| **FR-006A**| `ADVANCED` | Stage 2B (Parsing) | None | Decode Word `.docx` structures | Corrupt archive -> applicable recovery assessment (§7.1.1) -> HITL if unresolved | `test_docx_parser` |
| **FR-006B**| `ADVANCED` | Stage 2B (Parsing) | None | Extract text stream from `.pdf` files | Stream error -> applicable recovery/OCR assessment (§7.1.1) -> HITL if unresolved | `test_pdf_parser_valid`, `test_pdf_parser_corrupted` |
| **FR-006C**| `DESIGN EXTENSION` | Stage 2B (Parsing) | None | Extract sheet cells from `.xlsx` files | Format error -> applicable recovery assessment (§7.1.1) -> HITL if unresolved | `test_excel_parser` |
| **FR-007** | `ADVANCED` | Stage 2B (Parsing) | Table layout semantic extraction (on-demand) | Tabular data structure preservation | Layout failure -> applicable recovery/OCR assessment (§7.1.1) -> HITL if unresolved | `test_docx_table_layout_extraction` |
| **FR-008** | `ADVANCED` | Stage 2B (OCR/Vision)| OCR / Vision text decoding from images | Usability validation & pre-check | Content insufficient $\rightarrow$ HITL | `test_scanned_ocr_extraction [PLANNED]` |
| **FR-009** | `CORE` | Stage 3A (Extraction)| Extract reference fields from SI (on-demand) | Anchor SI as reference document | Field missing / unreadable SI $\rightarrow$ HITL | `test_stage3_matching_pair` |
| **FR-010** | `CORE` | Stage 3A (Extraction)| Extract candidate fields from BL (on-demand) | Validate 7-field completeness via Gate | Field missing $\rightarrow$ HITL | `test_stage3_discrepancy_pair` |
| **FR-011** | `CORE` | Stage 3B (Comparison)| None | Compare 7 normalized fields (==) | Inequality $\rightarrow$ Flag defect | `test_stage3_matching_pair` |
| **FR-012** | `CORE` | Stage 3B (Comparison)| None | Format side-by-side mismatch (`SI: x / BL: y`)| Discrepancy $\rightarrow$ Report | `test_stage3_discrepancy_pair` |
| **FR-013** | `CORE` | HITL Manager | Generate context evidence snippet | Package structured escalation record | Uncertainty $\rightarrow$ HITL | `test_stage2_missing_attachment` |
| **FR-014** | `ADVANCED` | Attachment Triage | OCR attempt on image-only documents | Usability validation & stream triage | Scan unusable $\rightarrow$ HITL | `test_stage2_corrupted_pdf` |
| **FR-015** | `CORE` | HITL Manager | Extract source-grounded snippet | Validate review reason and evidence payload | Missing evidence $\rightarrow$ Error | `test_stage2_missing_attachment` |
| **FR-016** | `ADVANCED` | HITL Manager | None | Operator review ingestion & update | Ingestion error $\rightarrow$ Error | `test_dynamic_verify_endpoint` |
| **FR-017** | `ADVANCED` | Error Handler | None | Exponential backoff & retry coordination | Max retries $\rightarrow$ Stage fallback | `test_api.py` |
| **NFR-003**| `ADVANCED` | Parser Subsystem | None | Intercept `PdfStreamError` gracefully | Corrupt stream -> applicable recovery assessment (§7.1.1) -> HITL if unresolved | `test_pdf_parser_corrupted` |
| **NFR-005**| `EVALUATION` | Validator | None | Validate against `sample_submission.json` | Schema mismatch $\rightarrow$ Error | `test_validator` |

---

## 23. Design Parameters Register & Preserved TBDs

### 23.1 Design Parameters by Status
- **`APPROVED DESIGN DECISION`**:
  - `DEC-01`: Deterministic Comparison Engine.
  - `DEC-P01`: Provider-Agnostic AI Adapter architecture (`BaseAIAdapter`).
  - `DEC-P02`: OCR / Vision attempted on unusable/scanned documents before HITL.
  - `DEC-P03`: FastAPI + Uvicorn web framework.
  - `DEC-P06A`: Formatting Normalization (Unicode, punctuation, whitespace, commas).
  - `DEC-P06B`: Unit Normalization (Exact mathematical MT $\rightarrow$ kg).
  - `DEC-AI-P03`: AI-on-Demand Execution Policy (deterministic metadata & parsing first; AI invoked for ambiguity and complex layouts).
  - `DEC-AI-P04`: Field-Level Reliability Gate (sufficient reliable content to establish the seven required comparison fields; partial reliable work preserved during HITL).
  - `DEC-AI-P05`: Generalized Source-Grounded Evidence (text span, table cell, page location, OCR region, metadata).
- **`APPROVED CONFIGURABLE DEFAULT`**:
  - `DEC-AI-P01`: Technical retry limit (default: 3 attempts, exponential backoff with base 1.0s; configurable via runtime settings without architecture amendment).
  - `DEC-AI-P02`: Semantic retry limit (default: 2 attempts, prompt feedback with validation error; configurable via runtime settings without architecture amendment).
- **`TBD (Preserved Prescriptions)`**:
  - `DEC-P06C (Port Semantic Equivalence)`: Port code, city, and terminal equivalence requires approved canonical mapping.
  - `DEC-P06D (Organization Name Equivalence)`: Legal suffixes not stripped without approved alias rules.
  - `DEC-P06E (Numeric Tolerance)`: Mathematical exact equality enforced without $\pm 1\text{ kg}$ tolerance.

---

## 24. Non-Goals

This specification explicitly does NOT define:
- Final frontend visual design, styling, or component layout (belongs to `04_UI_UX_SPEC.md`).
- Selection of specific frontend libraries (e.g. React, Tailwind, Vanilla JS).
- Specific cloud hosting providers (e.g. Render, AWS, GCP).
- Implementation execution order or task scheduling (reserved for `06_TASKS.md`).
- Specific data payload schemas for REST endpoints (reserved for `03_DATA_CONTRACTS.md`).
- Email-specific shortcuts or dataset-specific answers.

---

## 25. Document Governance

- **Status**: `APPROVED / BASELINED`
- **Revision**: `3.1 (Approved parsing-recovery clarification)`
- **Change Record**: [AMENDMENT_2026-09-22.md](AMENDMENT_2026-09-22.md). The Stage-1 intent and partial-result corrections from revision 3.0 remain intact.
- **Integrity Guarantee**: This document does NOT modify, weaken, or supersede [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md), [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md), or [`AGENTS.md`](file:///d:/ship/AGENTS.md).
- **Amendment Rule**: Any modifications to AI responsibility boundaries or baselined architecture require explicit human approval.
