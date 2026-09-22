# Shipping Document Verification System

An AI-assisted shipping document verification system that classifies incoming emails, processes Shipping Instructions (SI) and Draft Bills of Lading (BL), compares critical shipment information, and escalates uncertain cases for human review.

The system uses a **hybrid AI + deterministic architecture**:

- AI is used where semantic interpretation or document extraction is useful.
- Deterministic logic is used for normalization, validation, and the final field comparison.
- The language model does **not** decide whether two shipment values match.
- Uncertain, missing, conflicting, or unreadable information is escalated to a human reviewer instead of being guessed.

---

## Live Demo

**Frontend**

https://hackaton-the-farmer-1.onrender.com/

**Backend API**

https://hackaton-the-farmer.onrender.com

**Swagger API Documentation**

https://hackaton-the-farmer.onrender.com/docs

---

## Problem

Shipping operations teams frequently receive emails containing Shipping Instructions and Draft Bills of Lading that must be manually checked for inconsistencies.

Manual verification is repetitive and can become difficult when:

- emails contain different operational intents,
- document formats vary,
- values use different formatting,
- documents are incomplete or unclear,
- scanned documents require OCR,
- only one field is incorrect while the remaining information is valid.

This project automates the repetitive parts of the workflow while keeping uncertain decisions visible to a human reviewer.

---

## End-to-End Workflow

```text
Incoming Email
      |
      v
Email Classification
      |
      v
Document Comparison Request?
   /               \
 No                 Yes
 |                   |
 v                   v
Complete      Identify SI and Draft BL
                     |
                     v
              Parse Documents
                     |
                     v
               Extract 7 Fields
                     |
                     v
               Normalize Values
                     |
                     v
          Deterministic Comparison
                     |
          +----------+----------+
          |          |          |
        MATCH     MISMATCH   NEEDS_REVIEW
                                |
                                v
                          Human Correction
                                |
                                v
                       Automatic Recompute
```

---

## Email Categories

The system classifies incoming emails into five operational categories:

1. Document comparison
2. New shipping instruction
3. Invoice query
4. General operational update
5. Spam

Only **document comparison** requests continue into the SI / Draft BL verification pipeline.

This avoids unnecessary document processing for unrelated emails.

---

## Seven Compared Fields

For document comparison requests, the system verifies exactly seven shipment fields:

| Field             |
| ----------------- |
| Shipper           |
| Consignee         |
| Notify Party      |
| Port of Loading   |
| Port of Discharge |
| Container Count   |
| Gross Weight      |

The final comparison is performed using deterministic logic after normalization.

---

## Example

### Clean Match

```text
Shipping Instruction:
Container Count: 3

Draft Bill of Lading:
Container Count: 3

Result:
MATCH
```

### Detected Mismatch

```text
Shipping Instruction:
Container Count: 3

Draft Bill of Lading:
Container Count: 4

Result:
MISMATCH
```

Only the affected field is flagged. Other reliable matching fields remain preserved.

---

## Human-in-the-Loop Review

The system does not force a final answer when information is unreliable.

Examples that may trigger human review include:

* missing attachment,
* unreadable document,
* uncertain document type,
* missing required value,
* uncertain extraction result,
* conflicting candidate values,
* processing or provider failure.

A case then becomes:

```text
NEEDS_REVIEW
```

Reliable work already completed by the system is preserved.

The reviewer corrects the **source-level information**, not the final MATCH or MISMATCH result.

After the correction:

```text
Human Correction
      |
      v
Normalization
      |
      v
Deterministic Re-comparison
      |
      v
Updated Result
```

This prevents users from manually overriding the final verification result without going through the comparison logic.

---

## Why Hybrid AI + Deterministic Rules?

This system intentionally does not use AI for every decision.

### AI is useful for

* understanding ambiguous email intent,
* interpreting semi-structured documents,
* extracting information from complex input,
* assisting when deterministic extraction is insufficient.

### Deterministic logic is used for

* field normalization,
* numerical conversion,
* schema validation,
* final seven-field equality checks,
* MATCH / MISMATCH decisions.

This design reduces unnecessary AI usage and makes the final verification result more predictable and explainable.

---

## Source Evidence

Extracted information is linked to source evidence where available.

This allows the reviewer to inspect the original supporting text instead of relying only on the final result.

The review workflow therefore provides:

```text
Extracted Value
      +
Source Evidence
      +
Comparison Result
```

This improves traceability and makes discrepancies easier to verify.

---

## Supported Processing

The architecture supports:

* Plain text
* DOCX
* PDF
* Scanned / image-based documents
* OCR-assisted processing
* Structured extraction
* Human review fallback

The system follows a deterministic-first approach and only uses more advanced processing when required.

---

## Dataset

The supplied hackathon bundle contains:

```text
520 inbox records
250 attachment files
```

The original data bundle is preserved under:

```text
sdoc-hackathon-bundle/
```

The live presentation uses controlled representative cases so that each major workflow branch can be demonstrated clearly and reproducibly within the presentation time limit.

The same processing architecture supports batch execution across the supplied inbox dataset.

---

## Live Demo Cases

The deployed demo includes representative scenarios:

### `uat-demo-general`

Shows:

```text
Email classification
→ General operational message
→ No document comparison required
```

### `uat-demo-match`

Shows:

```text
SI + Draft BL
→ 7 fields extracted
→ All fields match
→ COMPLETE / MATCH
```

### `uat-demo-mismatch`

Shows:

```text
Container Count
SI = 3
BL = 4

→ COMPLETE / MISMATCH
```

### `uat-demo-review`

Shows:

```text
Missing Gross Weight
→ NEEDS_REVIEW
→ Human correction
→ Automatic deterministic recomputation
```

The UAT demo records are synthetic and are clearly separated from the official evaluation dataset.

---

## Validation

The project is validated at multiple levels.

| Validation                      |         Result |
| ------------------------------- | -------------: |
| Backend automated tests         |     246 passed |
| AI fixture validation           | 53 / 53 passed |
| Human-review fixture validation | 48 / 48 passed |
| Frontend tests                  |   9 / 9 passed |
| Frontend production build       |           PASS |
| API contract synchronization    |           PASS |
| Evaluation bundle immutability  |           PASS |

Automated testing validates system behavior and regression safety.

It does not replace human usability testing.

---

## API

Main API endpoints:

```text
GET  /
GET  /health
GET  /audit
GET  /audit/{email_id}
POST /audit/{email_id}/review
GET  /submission
POST /verify
```

### Audit Queue

```http
GET /audit
```

Returns the current verification cases.

### Single Case

```http
GET /audit/{email_id}
```

Returns the complete audit record for one email.

### Human Review

```http
POST /audit/{email_id}/review
```

Submits reviewer corrections and triggers deterministic recomputation.

### Submission Export

```http
GET /submission
```

Produces structured output when all required cases are exportable.

---

## Frontend

The frontend is built using:

* React
* TypeScript
* Vite
* Tailwind CSS

Main views include:

```text
Case Queue
Case Detail
Comparison Matrix
Evidence Viewer
Human Review
Export
```

The comparison interface presents:

```text
Field | Shipping Instruction | Draft BL | Result
```

so reviewers can identify mismatches without reading raw JSON.

---

## Backend

The backend uses:

* Python
* FastAPI
* Pydantic
* Uvicorn
* Pluggable parsing components
* Deterministic comparison engine
* Human-in-the-loop review service

---

## Project Structure

```text
.
├── app.py
├── main.py
├── requirements.txt
├── render.yaml
│
├── frontend/
│   └── React / TypeScript user interface
│
├── src/
│   ├── adapters/
│   ├── api/
│   ├── demo/
│   ├── hitl/
│   ├── models/
│   ├── parsers/
│   ├── pipeline/
│   └── store/
│
├── tests/
│   └── automated and regression tests
│
├── scripts/
│   └── verification and benchmark scripts
│
├── specs/
│   └── product, architecture, contracts,
│       UI and testing specifications
│
└── sdoc-hackathon-bundle/
    ├── inbox/
    ├── attachments/
    ├── sample_submission.json
    └── loader.py
```

---

## Running the Backend Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app:app --reload
```

Then open:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

For production build:

```bash
npm run build
```

---

## Running Tests

Backend:

```bash
python -m pytest tests -q
```

AI fixture validation:

```bash
python tests/fixtures/validate_ai_fixtures.py
```

Review fixture validation:

```bash
python tests/fixtures/validate_review_fixtures.py
```

Frontend:

```bash
npm --prefix frontend run test
```

Production build:

```bash
npm --prefix frontend run build
```

Full deadline verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify_deadline.ps1
```

---

## Design Principles

The implementation follows several core principles:

### 1. Do not guess uncertain results

If a reliable decision cannot be made:

```text
mismatch_detected = unresolved
```

rather than silently returning no mismatch.

### 2. Preserve reliable work

If one field requires review, already verified fields are not discarded.

### 3. AI does not decide equality

AI may assist with understanding and extraction, but final equality checks are deterministic.

### 4. Evidence remains accessible

Reviewers should be able to understand why a field was extracted or flagged.

### 5. Human corrections trigger recomputation

Users correct the source information rather than directly editing the final mismatch decision.

---

## Current Limitations

Some semantic equivalence rules are intentionally conservative.

Examples include:

* organization-name equivalence,
* semantic port aliases,
* numerical tolerances.

The system avoids silently introducing assumptions such as:

```text
±1 kg tolerance
```

unless such behavior is explicitly defined.

External AI providers may also introduce latency or availability limitations, which are handled through bounded retries and human-review fallback where appropriate.

---

## Presentation Summary

The system demonstrates the complete operational workflow:

```text
Inbox
→ Classification
→ Document Identification
→ Parsing
→ Extraction
→ Deterministic Comparison
→ Evidence
→ Human Review
→ Automatic Re-comparison
→ Structured Output
```

The objective is not simply to add AI to document processing.

The objective is to use AI where interpretation is valuable while keeping final verification deterministic, traceable, and reviewable.
