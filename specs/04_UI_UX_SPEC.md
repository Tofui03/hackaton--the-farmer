# 04_UI_UX_SPEC.md — UI/UX Specification for Operational Verification & Human Review

> **Status**: APPROVED / BASELINED
> **Revision**: 2.0-baselined (2026-09-22)
> **Authority**: Original use case → [00_PRODUCT_SPEC.md](00_PRODUCT_SPEC.md) → [01_PROJECT_DESIGN.md](01_PROJECT_DESIGN.md) → [02_AI_PIPELINE_SPEC.md](02_AI_PIPELINE_SPEC.md) → [03_DATA_CONTRACTS.md](03_DATA_CONTRACTS.md)
> **Scope**: User interfaces, interaction models, screen states, human review workspace, and data contract traceability.
> **Implementation Constraint**: No production implementation code or baselined specification is modified by this document.

---

## 1. Document Purpose & Design Principles

### 1.1 Purpose
This specification defines the frontend presentation layer, user workflows, interface states, evidence inspection, and Human-in-the-Loop (HITL) review workspace for the Shipping Document Verification system.

It translates the baselined data contracts ([`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md)) into an operational tool designed for examiners and document verification operators.

### 1.2 Non-Goals
This specification explicitly does **NOT** define:
- Backend business rules or extraction algorithms (governed by `01` and `02`).
- Pydantic models or wire schemas (governed by `03`).
- Evaluation scoring formulas or test plans (governed by `05`).
- Implementation task breakdown (governed by `06`).

### 1.3 Core Design Principles
The interface must prioritize operational efficiency and risk visibility over decorative vanity metrics:

1. **Operational Clarity**: An operator must immediately identify which cases require attention, what documents are involved, and what action is required.
2. **Discrepancy Visibility**: Discrepancies between Shipping Instructions (SI) and draft Bills of Lading (BL) must be unmistakably highlighted with side-by-side diffing.
3. **Review Efficiency**: When a case requires human review, already reliable comparisons must be preserved. Reviewers must not be forced to re-examine resolved fields.
4. **Source Evidence Traceability**: Every extracted value must provide a direct, one-click pathway to inspect its supporting source document evidence (text span, table cell, page region, or metadata).
5. **Uncertainty Transparency**: Incomplete, unreadable, or conflicting information must be displayed with explicit status badges. The UI must **NEVER** present an unresolved case as a clean pass (`"No mismatch detected"`).
6. **No Hardcoded Metrics**: The UI must dynamically derive all queue counts and summaries from loaded API data. Hardcoded dataset statistics (e.g. `520`, `21`, `63`, `0.0% false alarms`) are strictly prohibited.

---

## 2. User Roles & Access Boundaries

| Role | Core Responsibilities | UI Permissions & Boundaries |
|---|---|---|
| **Document Verification Operator** | Queue triage, discrepancy inspection, human review resolution, source candidate correction. | Can view all queues, inspect case details, submit `ReviewUpdate` payloads (category, role assignment, raw field correction, evidence citation). **Cannot** directly override match booleans. |
| **Compliance / Audit Examiner** | Independent verification, evidence lineage inspection, evaluation export generation. | Read-only access to audit logs, revision histories, attempt metadata, and `/submission` export validation. |

*Note: The system does not authorize direct manipulation of database tables or manual toggling of comparison results.*

---

## 3. Primary User Journey

```
┌───────────────────────────────────────────────────────────────┐
│                    Inbox / Case Queue                         │
│   (Filter by Category, State: Needs Review / Mismatch / OK)   │
└──────────────────────────────┬────────────────────────────────┘
                               │ Click Case
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Case Detail View                         │
│  ├─ Header: Email ID, State Badge, Outcome Badge, Revision    │
│  ├─ Section 1: Email Context (Sender, Subject, Body, Files)   │
│  ├─ Section 2: Document Role Resolution (SI vs BL Status)     │
│  └─ Section 3: 4-Column Comparison Matrix & Evidence Tracing  │
└──────────────────────────────┬────────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │ Case State                          │ Case State
            ▼ [COMPLETE]                          ▼ [NEEDS_REVIEW]
┌──────────────────────────────┐        ┌──────────────────────────────┐
│       Final Outcome          │        │    Human Review Workspace    │
│  • MATCH: Clean audit pass   │        │     (/cases/:email_id/review)│
│  • MISMATCH: Prominent diff  │        │  • View review issues & why  │
│  • N/A: Non-comparison info  │        │  • Inspect partial results   │
└──────────────────────────────┘        │  • Input source corrections  │
                                        └──────────────┬───────────────┘
                                                       │ Submit ReviewUpdate
                                                       │ (with expected_revision)
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │ Backend Deterministic Re-run │
                                        │  • Normalization & Recheck   │
                                        │  • Generates new revision    │
                                        └──────────────┬───────────────┘
                                                       │ Redirect
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │ Updated Audit Case Detail    │
                                        └──────────────────────────────┘
```

---

## 4. Information Architecture & Navigation

The frontend application provides 3 primary operational views and 1 utility dialog:

```
[SDOC Verification Console]
├── 1. Cases Queue View (/cases)
│    ├── Dynamic Metric Summary (Total, Complete, Mismatches, Needs Review)
│    ├── Search & Filter Toolbar
│    └── Case Data Grid (Paginated / Virtualized)
├── 2. Case Detail View (/cases/:email_id)
│    ├── Email & Document Context Bar
│    ├── Four-Column Comparison Matrix
│    ├── Source Evidence Inspector (Slide-out Drawer)
│    └── Audit Lineage & Processing Metadata (Accordion)
├── 3. Human Review Workspace (/cases/:email_id/review)  <-- Dedicated Route (V1)
│    ├── Review Trigger Summary (Issues list & suggested action)
│    ├── Preserved Partial Comparisons Panel
│    ├── Multi-Scope Correction Form (Category, Document Roles, Field Values, Evidence)
│    └── Concurrency Conflict Handler (Revision collision modal)
└── 4. Evaluation Export Dialog
     ├── Export Readiness Checker
     └── Blocked Export Diagnostic Viewer (when EXPORT_BLOCKED)
```

---

## 5. View Specifications

### 5.1 Cases Queue View (`/cases`)

The default landing view for operational triage.

#### 5.1.1 Header & Operational Scorecard
KPI values are dynamically derived from the latest loaded case data and refresh when the underlying data is refreshed. The system does not use polling, WebSockets, or Server-Sent Events:
- **Total Cases**: Total ingested emails in dataset.
- **Needs Review**: Count of cases where `state == "NEEDS_REVIEW"`.
- **Mismatches**: Count of completed cases where `outcome == "MISMATCH"`.
- **Clean Matches**: Count of completed cases where `outcome == "MATCH"`.
- **Non-Comparison**: Count of completed cases where `outcome == "NOT_APPLICABLE"`.

*(No static numbers; zero claims of 0% false alarms).*

#### 5.1.2 Filter & Search Toolbar
- **Text Search**: Client-side filtering across `email_id`, `sender`, and `subject`.
- **Category Filter**: Dropdown with canonical categories: `All`, `document_comparison`, `new_shipping_instruction`, `invoice_query`, `general`, `spam`, `Unresolved Intent`.
- **Processing State Filter**: `All`, `NEEDS_REVIEW`, `COMPLETE`.
- **Outcome Filter**: `All`, `MISMATCH`, `MATCH`, `NOT_APPLICABLE`.
- **Action Button**: `[Export Official Submission]` (triggers evaluation export flow).

#### 5.1.3 Data Grid Columns

| Column | Data Source | Visual Representation |
|---|---|---|
| **Email ID** | `email_id` | Monospace link to Case Detail (`/cases/{email_id}`). |
| **Subject / Sender** | `email.subject`, `email.sender` | Primary line: Subject; Secondary line: Sender address. |
| **Category** | `classification.category` | Tag badge. If `null`, display amber badge: `Unresolved Classification`. |
| **Processing State** | `state` | `COMPLETE` (neutral/slate), `NEEDS_REVIEW` (amber alert badge). |
| **Outcome** | `outcome`, `mismatch_detected` | `MATCH` (emerald badge), `MISMATCH` (rose/red badge), `NOT_APPLICABLE` (slate badge), `REVIEW PENDING` (amber badge). |
| **Discrepancy / Review Summary** | `result_summary`, `discrepancies` | Text snippet summarizing mismatches (e.g. `container_count (SI: 2 / BL: 3)`) or review reason. |
| **Revision** | `revision` | Monospace revision badge (e.g. `r1`, `r2`). |
| **Action** | — | Button: `[Inspect]` or `[Review Case]` (highlighted if `NEEDS_REVIEW`). |

---

### 5.2 Case Detail View (`/cases/:email_id`)

The primary inspection screen for an individual shipment comparison.

#### 5.2.1 Case Header Bar
- Breadcrumb: `Cases / email_004`
- Left: Email ID, Subject, Category badge, Revision lineage (`r1` or `r2 (from r1)`).
- Right Status Badges:
  - **State Badge**: `COMPLETE` or `NEEDS_REVIEW`.
  - **Outcome Badge**: `MATCH`, `MISMATCH`, `NOT_APPLICABLE`, or `REVIEW REQUIRED`.
- Action: If state is `NEEDS_REVIEW`, a prominent button: `[Open Review Workspace]`.

#### 5.2.2 Section 1: Email & Attachment Context
Collapsible panel displaying preserved source context:
- Sender, Subject, Date/Lineage.
- Email Body excerpt.
- Attachments list: filename, relative path, MIME type, parsed character count, and parser usability status badge (`SUCCESS`, `PARTIAL`, `UNREADABLE`).

#### 5.2.3 Section 2: Document Role Resolution
Summary card displaying identified document roles:
- **Shipping Instruction (SI)**: Filename link + identification evidence snippet.
- **Draft Bill of Lading (BL)**: Filename link + identification evidence snippet.
- *Ambiguity Alert*: If roles are undetermined or conflicting, display warning banner with link to role reassignment.

#### 5.2.4 Section 3: Four-Column Comparison Matrix
The centerpiece of document verification in V1 is an operational diff structured strictly as a **four-column comparison matrix**: `Field Name` + `Shipping Instruction (SI)` + `Draft Bill of Lading (BL)` + `Outcome / Result`.

*(Note: A synchronized full-document split viewer is **FUTURE / ADVANCED UX**, not part of V1).*

```
┌──────────────────┬──────────────────────────┬──────────────────────────┬──────────────────────────┐
│ Field Name       │ Shipping Instruction (SI)│ Draft Bill of Lading (BL)│ Outcome / Result         │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ shipper          │ ACME INDUSTRIAL CORP     │ ACME INDUSTRIAL CORP     │ [MATCH]                  │
│                  │ raw: "ACME INDUSTRIAL"   │ raw: "ACME INDUSTRIAL"   │ [View Evidence (2)]      │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ consignee        │ GLOBAL FREIGHT GMBH      │ GLOBAL FREIGHT GMBH      │ [MATCH]                  │
│                  │ raw: "GLOBAL FREIGHT"    │ raw: "GLOBAL FREIGHT"    │ [View Evidence (2)]      │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ notify_party     │ SAME AS CONSIGNEE        │ SAME AS CONSIGNEE        │ [MATCH]                  │
│                  │ raw: "SAME AS CONSIGNEE" │ raw: "SAME AS CONSIGNEE" │ [View Evidence (2)]      │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ port_of_loading  │ SHANGHAI, CHINA          │ SHANGHAI, CHINA          │ [MATCH]                  │
│                  │ raw: "PORT OF SHANGHAI"  │ raw: "SHANGHAI PORT"     │ [View Evidence (2)]      │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ port_of_discharge│ ROTTERDAM, NETHERLANDS   │ ROTTERDAM, NETHERLANDS   │ [MATCH]                  │
│                  │ raw: "ROTTERDAM"         │ raw: "PORT ROTTERDAM"    │ [View Evidence (2)]      │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ container_count  │ 2                        │ 3                        │ [MISMATCH: 2 vs 3]       │
│                  │ raw: "2 X 40HC"          │ raw: "3 CONTAINERS"      │ [View Evidence (2)]      │
├──────────────────┼──────────────────────────┼──────────────────────────┼──────────────────────────┤
│ gross_weight_kg  │ 22500                    │ 22500                    │ [MATCH]                  │
│                  │ raw: "22,500.00 KGS"     │ raw: "22500 KG"          │ [View Evidence (2)]      │
└──────────────────┴──────────────────────────┴──────────────────────────┴──────────────────────────┘
```

##### Field Row Rules:
1. **Four-Column Structure**:
   - Column 1 (`Field Name`): Displays the mandatory field key (`shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, `gross_weight_kg`).
   - Column 2 (`Shipping Instruction (SI)`): Canonical normalized value as primary text; source raw candidate text beneath in subtle styling.
   - Column 3 (`Draft Bill of Lading (BL)`): Canonical normalized value as primary text; source raw candidate text beneath in subtle styling.
   - Column 4 (`Outcome / Result`): Comparison outcome badge (`MATCH`, `MISMATCH`, or `UNRESOLVED`), discrepancy detail snippet, and direct `[View Evidence]` trigger button.
2. **Outcome Badge Styling**:
   - `MATCH`: Soft green background, dark green text, checkmark icon.
   - `MISMATCH`: Soft red/rose background, bold red text, alert triangle icon. Side-by-side values visually highlighted.
   - `UNRESOLVED`: Striped amber background, amber text, clock icon. Shows explanatory tooltip (e.g. `Missing in BL`, `Conflicting candidates`).
3. **Evidence Access**: Clicking `[View Evidence]` opens the slide-out Source Evidence Inspector scoped directly to that field.
4. **Zero Hidden Rows**: All 7 mandatory fields are always rendered. If a field was missing in extraction, it shows `[Not Found in Document]` with an `UNRESOLVED` badge.

---

### 5.3 Source Evidence Inspector (Slide-out Drawer)

Triggered from any `[View Evidence]` button or review issue.

#### 5.3.1 Evidence Header
- Scoped Document ID, Role (`SI` or `BL`), and Field Name.
- Extracted raw candidate value and normalized canonical value.

#### 5.3.2 Evidence Cards
Renders structured `FieldEvidence` items without synthesizing ungrounded coordinates:
- **Text Span**: Displays exact quoted snippet (`quote`), highlighted within its enclosing sentence, with page number (`location.page`).
- **Table Cell**: Displays table identifier, row, column coordinates, and extracted cell text.
- **Page Region**: If bounding box coordinates exist (`[x0, y0, x1, y1]`), render coordinate metadata and page reference. *(If coordinates are absent, do NOT render fake bounding boxes).*
- **Document Metadata**: Displays document header strings, MIME metadata, and parser status.
- **Diagnostic / Error Context**: For parser/OCR failures, displays stage, error code, and diagnostic message.
- **Human Review Evidence**: For human-corrected values, displays operator ID, revision timestamp, and operator rationale.

---

### 5.4 Human Review Workspace (`/cases/:email_id/review`)

Dedicated operational workspace for resolving `NEEDS_REVIEW` cases.
Approved as the primary V1 design: **dedicated review route** (`/cases/:email_id/review`). Modals or drawers are NOT used as the primary container for the complete review workflow.

#### 5.4.1 Workspace Layout & Information Architecture
The review page uses a two-panel operational workspace that preserves continuous visibility of current comparison results while providing dedicated space for human review and corrections:

- **Left Panel (Reference & Preserved Work)**:
  - **Email & Context Summary**: Sender, subject, attachment usability status.
  - **Preserved Four-Column Comparison Matrix**: Displays all 7 mandatory fields. Fully highlights which fields are already resolved and reliable (green MATCH / rose MISMATCH badges), clearly separating them from fields requiring review (amber UNRESOLVED badges). Prevents operator fatigue by avoiding re-inspection of resolved fields.
  - **Quick Evidence Inspection**: Direct link to trigger the slide-out Evidence Inspector drawer without leaving the review workspace.
- **Right Panel (Interactive Review & Resolution)**:
  - **Review Issues Banner**: Active escalations from `review.issues` displayed with user-facing operational labels (see §5.4.2).
  - **Multi-Scope Correction Forms**: Tabs for Category, Document Roles, Field Corrections, and Confirmation.
  - **Concurrency & Revision Controls**: Displays current `revision` and binds `expected_revision` to prevent lost updates.
- **Evidence Drawer**: The Source Evidence Inspector slides out from the right over the workspace when `[View Evidence]` is triggered, providing deep source snippet inspection without losing form state.

#### 5.4.2 User-Facing Review Reason Labels
To maximize operator clarity, primary user-facing copy uses operational labels instead of raw system enums. Raw enum codes remain available in secondary tooltips and audit inspection views:

| Logical Reason Enum (`logical_reason`) | User-Facing Operational Label (Primary Copy) | Secondary Tooltip & Operational Context |
|---|---|---|
| `conflicting_candidate_values` | **Conflicting values found** | Multiple conflicting values were detected for this field. Select the authoritative source candidate. |
| `wrong_or_uncertain_document_type` | **Document type needs confirmation** | Attachment classification or role binding (SI vs BL) is ambiguous. Confirm or reassign document roles. |
| `missing_attachment` | **Required document missing** | One or both mandatory documents (SI or BL) are missing from the email attachments. |
| `unreadable_document` | **Document content unreadable** | Parser and OCR extraction could not extract usable text. Manual verification required. |
| `missing_required_value` | **Required field value missing** | Mandatory comparison field was not located in document content. Supply candidate if present. |
| `uncertain_result` | **Result uncertain / Ambiguous intent** | Email classification confidence or comparison normalization is ambiguous. Confirm intent. |
| `processing_or_provider_failure` | **System processing error** | Upstream parser or extraction failure encountered. Retry or provide manual input. |

#### 5.4.3 Structured Review Actions & Forms (DC-07 Scope)
The operator selects from the following supported review tabs and actions:

1. **Classification Tab**:
   - Only displayed if `classification.category == null` or flagged for intent re-evaluation.
   - Radio group of the 5 canonical categories:
     - `document_comparison`
     - `new_shipping_instruction`
     - `invoice_query`
     - `general`
     - `spam`
   - Evidence Citation: Grounded in any valid source-grounded email context supported by `FieldEvidence` (e.g. email subject line, body text span, sender domain, or metadata); not restricted to email body.

2. **Document Role Assignment Tab**:
   - Displayed when attachments could not be uniquely bound to SI/BL.
   - Dropdown selectors:
     - `Shipping Instruction (SI)`: Select attachment from email attachments list.
     - `Draft Bill of Lading (BL)`: Select attachment from email attachments list.
   - Form Validation: Prevents assigning the same attachment to both roles.

3. **Field Candidate Correction Tab (`action = "CORRECT"`)**:
   - For unresolved, conflicting, or mis-extracted fields.
   - Form fields:
     - Target Document: `SI` or `BL` (with associated filename).
     - Field Name: Dropdown of 7 mandatory fields.
     - Correct Raw Value: Text input for the exact candidate value found in the source document.
     - Evidence Citation: Grounded in `FieldEvidence` format (e.g. text span quote, table cell [table, row, col], document section, page number, or OCR region). Does **NOT** mandate page numbers when the source document format (e.g. docx, txt, table) or parser lacks page coordinates; source location is included only when it actually exists.
     - Operator Rationale: Required brief explanation of why this candidate is selected.
   - Payload: Submits `ReviewUpdate` with `action = "CORRECT"` and populated `corrections[]` array.

4. **Confirmation Action (`action = "CONFIRM"`)**:
   - Implements `action = "CONFIRM"` from `ReviewUpdate` ([`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md) §7).
   - Used when the operator confirms that automated findings or classifications are accurate as-is (e.g. confirming that an email is non-comparison, or confirming that an extracted value is correct despite lower model confidence).
   - **Safety Guardrail**: `action = "CONFIRM"` records the operator's assessment, but **cannot force unresolved fields into reliability** if the underlying extracted fields are missing, unreadable, or ambiguous. If a required comparison field remains unextracted, submitting `CONFIRM` will NOT force the case into `COMPLETE` — the backend will reject premature resolution or maintain the state as `NEEDS_REVIEW`.

#### 5.4.4 Submission & Optimistic Concurrency Control
- Hidden input contains `expected_revision = audit.revision`.
- `[Submit Correction]` / `[Confirm As-Is]`:
  - Disables form inputs and displays deterministic progress: *"Submitting review update → Running deterministic normalization & comparison..."*
  - **On Success (HTTP 200)**: Displays toast notification *"Revision r{N+1} created successfully"*, redirects to updated Case Detail.
  - **On Conflict (HTTP 409)**: Displays in-place collision alert banner:
    > **Revision Conflict Detected**
    > This case was updated by another operator (current server revision: `r{server_revision}`) while you were editing.
    > Your unsubmitted changes have been preserved in browser memory.
    > Actions: `[Reload Latest Revision]` `[View Side-by-Side Diff]`
  - **On Validation Error (HTTP 422)**: Displays inline form errors (e.g. missing evidence citation, invalid field name).

---

### 5.5 Evaluation Export Interface (`/export` Modal / Drawer)

Accessed from the Cases Queue view.

#### 5.5.1 Status Check
- **Ready State**: When 100% of cases are in `COMPLETE` state (`MATCH`, `MISMATCH`, or `NOT_APPLICABLE`).
  - Button: `[Download submission.json]`
- **Blocked State (`EXPORT_BLOCKED`)**:
  - Prominent warning banner: *"Evaluation Export Blocked (Safety Invariant DC-08)"*.
  - Explanatory message: *"Official evaluation export requires complete, unambiguous resolution. Current run contains unresolved records that cannot be losslessly mapped without guessing."*
  - Summary metrics:
    - `Cases requiring human review`: N
    - `Cases with unresolved category`: N
  - Actionable table listing blocking `email_id`s with direct links: `[Resolve in Review Workspace]`.

---

## 6. Status & Outcome Representation Matrix

The UI enforces strict visual separation between **Processing State** and **Business Outcome**:

| Processing State (`state`) | Business Outcome (`outcome`) | Mismatch Indicator (`mismatch_detected`) | Badge Label & Color | Summary Text Rule |
|---|---|---|---|---|
| `COMPLETE` | `MATCH` | `false` | **MATCH OK** (Solid Emerald) | Exactly `"No mismatch detected"`. |
| `COMPLETE` | `MISMATCH` | `true` | **MISMATCH** (Solid Rose) | Lists mismatched fields and values (e.g. `container_count (SI: 2 / BL: 3)`). |
| `COMPLETE` | `NOT_APPLICABLE` | `null` | **NON-COMPARISON** (Slate/Gray) | States non-comparison intent (e.g. `General inquiry; verification not applicable`). |
| `NEEDS_REVIEW` | `null` | `null` | **NEEDS REVIEW** (Amber / Warning Stripes) | Summary explains unresolved issue; **NEVER** says "No mismatch detected". |
| `FAILED` | `null` | `null` | **SYSTEM ERROR** (Solid Red) | Technical failure details; requires retry. |

---

## 7. Responsive Behavior & Accessibility

### 7.1 Responsive Layouts
- **Desktop (>= 1280px)**: Primary operational workstation layout. Case Detail displays 3-column layout (Context on left, 7-Field diff in center, Evidence Inspector on right).
- **Tablet / Small Desktop (1024px – 1279px)**: Case Detail 2-column layout; Evidence Inspector opens as a slide-over drawer.
- **Narrow Screens (< 1024px)**: Table transforms into stacked field cards:
  ```
  ┌─────────────────────────────────────────────────┐
  │ FIELD: container_count               [MISMATCH] │
  ├─────────────────────────────────────────────────┤
  │ SI:       2   (raw: "2 X 40HC")                 │
  │ Draft BL: 3   (raw: "3 CONTAINERS")             │
  ├─────────────────────────────────────────────────┤
  │ [View Evidence]             [Correct Field]     │
  └─────────────────────────────────────────────────┘
  ```
  *(Never horizontally squish 7 fields into unreadable narrow columns).*

### 7.2 Accessibility (WCAG 2.1 AA Compliance)
- **No Color-Only Meaning**: All outcome badges combine color with distinct icons (Checkmark, Triangle Alert, Clock) and explicit text labels.
- **Keyboard Navigation**: Full Tab/Shift-Tab navigation across queues, comparison rows, evidence drawers, and modal dialogs. Visible `:focus-visible` focus rings on all interactive elements.
- **Screen Reader Support**: Semantic HTML (`<table>`, `<th>`, `<section>`, `<article>`, `<dialog>`). `aria-expanded` on accordions, `aria-live="polite"` on status updates.
- **Contrast**: Minimum 4.5:1 text-to-background contrast ratio for all badges and diff panels.

---

## 8. Screen State Matrix

| Screen / View | State | UI Representation & Behavior |
|---|---|---|
| **Queue** | `LOADING` | Skeleton rows in grid, disabled search/filter inputs. |
| **Queue** | `READY` | Full data grid populated with dynamic counts in scorecard. |
| **Queue** | `EMPTY` | Clean empty state graphic: *"No cases found matching filter criteria"*, with `[Clear Filters]` button. |
| **Queue** | `ERROR` | Banner: *"Unable to load audit cases from server"*, with `[Retry]` button. |
| **Case Detail** | `LOADING` | Center spinner and skeleton header. |
| **Case Detail** | `COMPLETE_MATCH` | All 7 field rows green/neutral, header shows emerald MATCH badge, summary `"No mismatch detected"`. |
| **Case Detail** | `COMPLETE_MISMATCH` | Mismatched rows highlighted with rose background; summary lists differing values. |
| **Case Detail** | `NEEDS_REVIEW_PARTIAL` | Resolved fields show MATCH/MISMATCH; unresolved fields show amber warning stripes; prominent review button active. |
| **Case Detail** | `NON_COMPARISON` | Context shown; comparison table replaced with informative card: *"Email classified as [Category]. Verification not applicable."* |
| **Review Workspace** | `READY` | Issue summary at top, reliable fields card, active correction tabs. |
| **Review Workspace** | `SUBMITTING` | Form disabled, inline progress spinner: *"Recomputing deterministic comparisons..."* |
| **Review Workspace** | `REVISION_CONFLICT` | Modal alert indicating revision mismatch; option to reload latest or inspect diff. |
| **Export Dialog** | `READY` | Green checkmark, download link active for `submission.json`. |
| **Export Dialog** | `EXPORT_BLOCKED` | Amber warning, lists blocking email IDs with click-to-resolve links. |

---

## 9. User Action Matrix

| User Action | Trigger UI Element | API Interaction | Success UI Behavior | Failure UI Behavior | Confirmation Required? |
|---|---|---|---|---|---|
| **Open Case** | Queue row `[Inspect]` button | `GET /audit/{email_id}` | Navigates to `/cases/{email_id}`, renders detail. | Error toast: *"Case not found"*. | No |
| **Filter Queue** | Filter dropdown / search bar | Client-side filter or `GET /audit?category=...` | Updates grid rows dynamically; updates URL query params. | Empty state if no rows match. | No |
| **Inspect Evidence** | Field row `[View Evidence]` | Uses cached `AuditRecord.evidence` | Opens slide-out Evidence Inspector focused on field. | Toast: *"No evidence available for this field"*. | No |
| **Open Review** | Header `[Review Case]` button | Navigates to `/cases/{email_id}/review` | Opens Review Workspace with issues loaded. | None. | No |
| **Reassign Role** | Document role dropdown in Review | Local form state | Updates draft payload with `RoleCorrection`. | Prevents assigning same document to both roles. | No |
| **Submit Correction** | `[Submit ReviewUpdate]` button | `POST /audit/{email_id}/review` (`action=CORRECT`) | Toast: *"Revision updated"*, reloads Case Detail with new outcome. | **409**: Conflict modal.<br>**422**: Form validation error alert. | Yes (Summary prompt) |
| **Confirm As-Is** | `[Confirm System Findings]` | `POST /audit/{email_id}/review` (`action=CONFIRM`) | Updates review state to RESOLVED if all required fields are complete and reliable. | **422**: Error toast; `action=CONFIRM` cannot force unresolved/missing fields into reliability per DC-07. | Yes |
| **Reload Conflict** | `[Reload Latest Revision]` | `GET /audit/{email_id}` | Refreshes workspace with new `expected_revision`. | Error toast if network fails. | No |
| **Export Submission** | `[Export Official Submission]` | `GET /submission` | Prompts browser download of `submission.json`. | **409**: Opens `EXPORT_BLOCKED` modal. | No |

---

## 10. UI → Data Contract Traceability Matrix

Every UI component is directly grounded in baselined contracts ([`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md)):

| UI Component | Data Contract Model | Source Field(s) | REST Route |
|---|---|---|---|
| Queue Card / Scorecard | Dynamic aggregation | Derived from `AuditRecord[]` count | `GET /audit` |
| Queue Grid Rows | `AuditRecord` | `email_id`, `state`, `outcome`, `mismatch_detected`, `revision` | `GET /audit` |
| Email Context Panel | `EmailRecord`, `AttachmentReference` | `email.sender`, `email.subject`, `email.body`, `email.attachments` | `GET /audit/{email_id}` |
| Document Roles Card | `DocumentReference` | `documents[].document_id`, `documents[].role` | `GET /audit/{email_id}` |
| Parser Usability Badge | `ParserResult` | `parsers[].status`, `parsers[].usable_for_extraction` | `GET /audit/{email_id}` |
| Comparison Table Rows | `FieldComparison`, `ExtractedField` | `partial_result.comparisons[]`, `extractions[].fields{}` | `GET /audit/{email_id}` |
| Discrepancy Badges | `Discrepancy` | `discrepancies[].field`, `si_value`, `bl_value` | `GET /audit/{email_id}` |
| Evidence Drawer | `FieldEvidence`, `EvidenceLocation` | `evidence[].kind`, `quote`, `location`, `detail` | `GET /audit/{email_id}` |
| Review Trigger Card | `ReviewCase`, `ReviewIssue` | `review.issues[].logical_reason`, `suggested_action` | `GET /audit/{email_id}` |
| Category Correction Form | `ReviewUpdate` | `ReviewUpdate.category`, `classification_evidence_ids` | `POST /audit/{email_id}/review` |
| Role Correction Form | `RoleCorrection` | `ReviewUpdate.role_corrections[].document_id`, `assigned_role` | `POST /audit/{email_id}/review` |
| Field Correction Form | `FieldCorrection` | `ReviewUpdate.corrections[].field`, `raw_value`, `evidence_ids` | `POST /audit/{email_id}/review` |
| Concurrency Lock | Concurrency metadata | `ReviewUpdate.expected_revision`, `AuditRecord.revision` | `POST /audit/{email_id}/review` |
| Export Blocked Modal | `ErrorResponse` | `code=="EXPORT_BLOCKED"`, `details[]` | `GET /submission` |

---

## 11. Approved Frontend Technology Decision

| Dimension | Option A: Vanilla JavaScript + Tailwind CSS | Option B (APPROVED): React + Vite + TypeScript + Tailwind CSS |
|---|---|---|
| **State Complexity** | High manual DOM maintenance; synchronizing multi-tab review forms, evidence drawers, and optimistic revision locks requires bespoke event buses. | Native declarative state; UI reactivity cleanly manages queue filtering, 7-field diff tables, and multi-step review forms. |
| **Component Reusability** | Low; HTML templates duplicated across queue rows and drawer views. | High; modular `<ComparisonMatrix />`, `<EvidenceDrawer />`, `<ReviewWorkspace />`, `<StatusBadge />`. |
| **Tooling & Build** | Zero build step possible, but fragile for large SPAs. | Standard modern Vite pipeline with fast HMR and strict TypeScript type safety matching backend schemas. |
| **Alignment with Design** | Suitable only for basic read-only tables. | Strongly aligns with operational requirements of a production verification workspace. |

**Decision (APPROVED UI IMPLEMENTATION DECISION)**:
Adopt **React + Vite + TypeScript + Tailwind CSS** as the approved frontend stack for the Shipping Document Verification Console.
- **Rationale**: The operational requirements for optimistic concurrency control (`expected_revision`), side-by-side evidence inspection, dynamic diff matrices, and structured multi-scope review forms (`ReviewUpdate`) necessitate a declarative component model to eliminate regression and state synchronization bugs. TypeScript guarantees compile-time contract alignment with backend API schemas.
- **Deployment Simplicity**: Compiles to static HTML/JS/CSS assets that can be served directly from FastAPI's static mount or any static hosting environment without introducing separate frontend server infrastructure.

---

## 12. Removed Stale Content & Corrected Assumptions

The prior version of `04_UI_UX_SPEC.md` contained numerous outdated assumptions that have been eliminated:

1. **Removed Hardcoded Dataset Metrics**:
   - Removed `Total Audited: 520`
   - Removed `Discrepancies Caught: 21`
   - Removed `HITL Escalations: 63`
   - Removed `False Alarm Rate: 0.0%`
   - Removed hardcoded tab counts `Matched OK (436)`, `Vetoed Non-Comp (395)`.
2. **Removed Unapproved Marketing Slogans**:
   - Removed `"Zero False Alarms • Golden SI Benchmark • HITL Fallback"`.
3. **Removed Oversimplified JSON Viewer Concept**:
   - Replaced the passive "JSON viewer drawer" with a full operational 7-field comparison diff matrix and structured evidence inspector.
4. **Corrected Review Reason Assumptions**:
   - Eliminated reliance on an unverified "official four reason codes" taxonomy; fully integrated the 7 baselined `LogicalReason` types.
5. **Removed Direct Boolean Override**:
   - Explicitly forbade UI controls that attempt to toggle `mismatch_detected` directly; corrections strictly flow through source candidate inputs and backend deterministic re-evaluation.
6. **Integrated Tri-State Mismatch Model**:
   - Replaced naive boolean toggles with explicit support for `mismatch_detected == null` during human review.

---

## 13. Resolved UI Architectural Decisions & Scope Boundaries

The following frontend architectural decisions have been formally resolved and baselined:

1. **Review Workspace Layout**:
   - **APPROVED (V1)**: **Dedicated review route** (`/cases/:email_id/review`).
   - The review workspace uses a two-panel layout preserving immediate access to the 4-column comparison matrix, email context, and document status on the left, with review issues, multi-scope correction forms, and concurrency controls on the right. Modals or drawers are NOT used as the primary container for the complete review workflow (evidence inspection continues to use a slide-out drawer).

2. **Comparison Matrix Diff Style**:
   - **APPROVED (V1)**: **Four-Column Comparison Matrix** (`Field Name` + `Shipping Instruction (SI)` + `Draft Bill of Lading (BL)` + `Outcome / Result`).
   - Synchronized full-document split viewer is categorized as **FUTURE / ADVANCED UX** and is excluded from V1 scope.

3. **Batch Review Actions**:
   - **DECISION**: Categorized as **FUTURE / OUT OF V1 SCOPE**.
   - V1 human review operates strictly on one case and one revision at a time to ensure strict auditability, deterministic traceability, and collision prevention.

4. **Preserved Business TBDs**:
   - `DEC-P06C` (Port equivalence), `DEC-P06D` (Org name equivalence), and `DEC-P06E` (Numeric tolerance) remain TBD per [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md) and [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md). The UI presents exact normalized values and system-computed discrepancies without inventing client-side fuzzy matching or custom tolerances.

---

## 14. Document Governance & Baseline Gate

- **Document Status**: `APPROVED / BASELINED`
- **Revision**: `2.0-baselined (2026-09-22)`
- **Authority**: Baselined against [`specs/00_PRODUCT_SPEC.md`](00_PRODUCT_SPEC.md), [`specs/01_PROJECT_DESIGN.md`](01_PROJECT_DESIGN.md), [`specs/02_AI_PIPELINE_SPEC.md`](02_AI_PIPELINE_SPEC.md), and [`specs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md).
- **Baseline Sign-off**: All 10 user review decisions, screen architectures, interaction matrices, and data contract mappings have been verified and formally baselined.
- **Next Stage**: [`specs/05_TEST_PLAN.md`](05_TEST_PLAN.md), followed by [`specs/06_TASKS.md`](06_TASKS.md).
