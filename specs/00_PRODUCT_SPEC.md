# 00_PRODUCT_SPEC.md — Shipping Document Verification Product Specification

> **Status**: Approved & Protected  
> **Origin**: Derived directly from [`Shipping Document Verification Use Case.pdf`](file:///d:/ship/Shipping%20Document%20Verification%20Use%20Case.pdf) and [`sdoc-hackathon-bundle/README.md`](file:///d:/ship/sdoc-hackathon-bundle/README.md).

---

## 1. Context & Business Background

A shipping operations team receives diverse messages in a central shared inbox:
- Requests to verify shipment documents before final release.
- Requests to prepare or submit new Shipping Instructions (SI).
- Inquiries regarding local port charges, THC, telex releases, and freight invoices.
- Routine operational updates, vessel schedule notices, and shipment status summaries.
- Unsolicited spam, marketing solicitations, and promotional emails.

For document verification requests, staff must compare a **Shipping Instruction (SI)** — which defines the intended shipment details (the reference ground truth) — against a **draft Bill of Lading (BL)** received from the carrier. The goal is to detect and correct discrepancies *before* the carrier issues the final negotiable Bill of Lading.

### Core Operational Problems:
1. **Inbox Triage Bottleneck**: Reading each message manually is slow; missed verification requests cause downstream container delays and financial penalties.
2. **Manual Discrepancy Errors**: Comparing multi-page documents line-by-line is error-prone. A missed defect leads to customs detention, costly amendments, and delayed cargo release.
3. **Semantic Label Variation**: Different parties and shipping lines use different headers for the same concept (e.g. `Port of Loading` vs `Load Port` vs `POL`; `Gross Weight` vs `G.W.`). The system must match by semantic meaning, not naive string equality.

---

## 2. The Four Mandatory Capabilities

| Capability | Requirement |
|---|---|
| **Classify** | Accurately distinguish the 5 email categories: `document_comparison` (`BL_COMPARISON`), `new_si_request` (`SI_REQUEST`), `invoice_query` (`INVOICE_QUERY`), `general_message` (`GENERAL`), and `spam` (`SPAM`). |
| **Extract data** | For document-comparison emails only, extract the shipment fields from both the reference SI and candidate BL attachments across formats (`.txt`, `.pdf`, `.docx`, `.xlsx`). |
| **Compare** | Compare values across the 7 mandatory fields, surface differences with side-by-side evidence (`SI: <val> / BL: <val>`), and declare `"No mismatch detected"` if all 7 fields match. |
| **Ask for help (HITL)** | When a document cannot be reliably processed (missing attachments, corrupted files, unreadable image scans, missing mandatory values), escalate to human review with evidence rather than guessing or failing silently. |

---

## 3. The 7 Mandatory Comparison Fields

The system MUST audit exactly and only these seven fields:

1. **`shipper`**: Exporter / Consignor entity name and physical address.
2. **`consignee`**: Receiving party / Consignee entity name and physical address.
3. **`notify_party`**: Party to be notified on vessel arrival.
4. **`port_of_loading`**: Origin port (POL), resolving city, country, and UN/LOCODE (e.g. `MYPKG`).
5. **`port_of_discharge`**: Destination port (POD), resolving city, country, and UN/LOCODE (e.g. `PECLL`).
6. **`container_count`**: Total numeric count of shipping containers (pure Arabic integer).
7. **`gross_weight_kg`**: Cargo gross weight normalized to numeric kilograms (kg).

---

## 4. Normalization Rules (Zero False Alarms)

1. **Semantic Aliases**:
   - POL: `Port of Loading`, `Load Port`, `POL`, `Loading Port`, `Port of Load`.
   - POD: `Port of Discharge`, `Discharge Port`, `POD`, `Discharging Port`, `Destination Port`.
   - Weight: `Gross Weight`, `Total Weight`, `G.W.`, `Cargo Weight`, `Gross Wt`, `Weight (KG)`.
   - Containers: `Container Count`, `Total Containers`, `Qty of Units`, `No. of Containers`, `Quantity of Containers`, `Containers or Packages`.
2. **Numbers & Units**:
   - Convert Metric Tons (MT) to kg ($\text{MT} \times 1000$).
   - Strip commas, whitespace, and units (`KG`, `KGS`).
   - Parse spelled-out numbers (`"Three (3) Containers"` $\rightarrow 3$).
3. **Corporate Entity Casing & Suffixes**:
   - Strip minor corporate suffixes (`SDN BHD`, `LTD`, `LIMITED`, `LLC`, `INC`, `CORP`, `GMBH`, `PTE LTD`) and punctuation when evaluating entity equality. Core entity alignment represents a Match.

---

## 5. Escalation & HITL Criteria

When a reliable decision cannot be formed, the system MUST escalate with `requires_human_review: true` and one of four exact reasons:

- **`wrong_doc_type`**: Attachment is not an SI or draft BL (e.g. general photos, customs release invoices).
- **`missing_attachment`**: Email contains fewer than 2 attachments (e.g. `email_507`, `email_509`).
- **`unreadable`**: Attachment stream is corrupt (e.g. `email_511_BL.pdf` EOF stream error) or scanned image with unextractable text.
- **`missing_value`**: A mandatory field cannot be found or is blank in either document.

---

## 6. Official Evaluation & Scoring Metric

$$\text{Final Score} = 0.50 \times \text{End-to-End Defect Accuracy} + 0.30 \times \text{Stage-1 Macro-F1} + 0.20 \times \text{Stage-3 Defect-F1}$$

- **Reliability Axis**: HITL escalations are tracked as an independent reliability score to heavily penalize hallucinations and silent failures.
