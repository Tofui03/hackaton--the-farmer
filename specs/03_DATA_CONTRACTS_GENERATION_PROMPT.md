# Prompt for the Data Contracts stage

Copy the text below into the next task when ready to begin the Data Contracts specification review.

---

Continue this Shipping Document Verification project using Spec-Driven Development. This is documentation work only. Prepare a reviewed revision of `specs/03_DATA_CONTRACTS.md`; do not begin implementation or generate `06_TASKS.md` tasks.

## 1. Read the authoritative context

Read `AGENTS.md`, the original `Shipping Document Verification Use Case.pdf`, `specs/00_PRODUCT_SPEC.md`, `specs/01_PROJECT_DESIGN.md`, `specs/02_AI_PIPELINE_SPEC.md`, and `specs/AMENDMENT_2026-09-22.md`. Read the existing `specs/03_DATA_CONTRACTS.md` as a prior contract to assess, not as an empty destination. Use the bundle README and sample submission only to establish the evaluation interface, never business rules or expected answers.

Use the numbered product and architecture files as the authorities. Do not assume an unnumbered copy or a commit title establishes a newer approval. Preserve all existing user changes.

## 2. Preflight before generating contracts

First produce a short consistency table with source sections, current rules, conflicts, and the minimum human decision needed. Check the remaining cross-document items listed in the amendment, especially:

- Legacy versus current category names in `01`, `02`, and existing `03`.
- Internal HITL causes versus the four evaluation reason codes and the governance requirements.
- Parser recovery versus direct terminal escalation wording.
- Existing audit API shapes versus richer evidence and partial results.
- String/float examples in `02` versus structured evidence and exact numeric semantics.
- How unresolved classification is represented while preserving the final five-category requirement.

Where authoritative requirements conflict or an unresolved business decision is needed, STOP and ask one consolidated, concrete clarification. Do not rewrite a baseline to hide the conflict. The amendment explicitly does not claim the entire suite is reconciled. Do not treat suggestions below as approval for new requirements or mappings.

If preflight is clear or the necessary decisions are approved, draft the revised `03` with status `DRAFT / UNDER HUMAN REVIEW`, documenting which previous contract sections it proposes to supersede. Do not mark it APPROVED / BASELINED without human approval. Changes to `00`, `01`, `02`, or `AGENTS.md` require separately authorized amendments.

## 3. Preserve approved behavioral boundaries

- Classify into exactly five operational categories; only document-comparison requests enter attachment checking. Missing attachments never negate comparison intent.
- Compare exactly `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, and `gross_weight_kg`.
- SI is the reference document, not infallible truth.
- AI may classify, identify documents, extract fields, map field labels, or perform OCR/Vision on demand. Final normalization, validation, equality, and mismatch decisions are deterministic.
- Use the provider-agnostic adapter architecture, deterministic processing where sufficient, and AI on demand. Do not introduce a two-model router, database, framework, or cloud provider.
- Preserve DEC-P06C, DEC-P06D, and DEC-P06E as TBD. No automatic port/code/terminal equivalence, broad company-suffix stripping, implicit numeric tolerance, or invented numeric business ranges.
- Reliability is field-level and source-grounded. Model-reported confidence is diagnostic only.
- Preserve reliable extracted values, evidence, and comparisons when other fields require review. An unresolved case must never be serialized as a definitive clean pass.
- Recovery and fallbacks are stage-specific, validated, and bounded. Technical and semantic attempt defaults are configurable; define attempts versus retries consistently without changing the approved limits.
- Keep source facts, approved design decisions, proposed contract decisions, configurable defaults, and TBDs explicitly distinguishable.

## 4. Required coverage in the draft

Define the following concepts where needed; combine models where justified rather than introducing unnecessary entities:

`EmailRecord`, `ClassificationResult`, `AttachmentReference` / `DocumentReference`, `ParserResult`, `ExtractedField`, `FieldEvidence`, `DocumentExtraction`, `NormalizedField`, `FieldComparison`, `Discrepancy`, `HITLCase` / `ReviewCase`, `PartialResult`, `AuditRecord`, `SubmissionRecord`, and `ProcessingMetadata`.

For each model specify field names, types, required versus optional fields, nullability, enum meanings, invariants, lifecycle stage, producer/consumer, and serialization. Supply coherent JSON examples and Pydantic v2 definitions within the document only. Model definitions must agree with the prose and examples. Any new schema choice must be labelled as proposed contract design until approved.

Address these details explicitly:

1. Separate raw candidates, normalized values, reliability state, per-field comparison outcome, overall processing/review status, and final business outcome. Do not collapse not-compared, unresolved, and matched into the same boolean meaning.
2. Preserve document identity and field identity with source evidence. Define appropriate evidence variants for text spans, table cells, page/section references, OCR regions, metadata, and processing-error context. Do not require unavailable snippets or treat an exception message as proof of a shipment value.
3. Preserve ambiguous/conflicting candidates without selecting one silently. Represent missing, unreadable, uncertain, and conflicting fields consistently across stages.
4. Define exact numeric representation and JSON serialization for normalized weight, distinguish integer container counts, and prevent coercion or floating-point artifacts from changing equality semantics. Do not invent a tolerance.
5. Define cross-field validation for complete match, complete mismatch, review with partial results, and non-comparison cases. Preserve confirmed partial discrepancies without publishing an unresolved overall case as complete.
6. Define human review confirmation/correction inputs, evidence/provenance retention, revalidation, deterministic recomparison, and updated report outputs. Separate proposed API details from already-approved capabilities; do not create unrelated workflows or storage architecture.
7. Specify retry/fallback metadata, source/processing references, prompt/model metadata where available, and error contracts. Do not fabricate provider-reported metadata.
8. Cover approved REST endpoints: `/health`, `/audit`, `/audit/{email_id}`, `/verify`, `/submission`, and `/docs`. Define requests, responses, filters, validation failures, and relevant error states. Any new review endpoint or incompatible payload change is a proposal requiring review.
9. Separate internal models from evaluation serialization. Define category mappings and the `sample_submission.json` shape, but surface unsupported or lossy HITL mappings for human decision. Include every input email ID when producing an evaluation submission; never copy template defaults as inferred outcomes.
10. Use synthetic examples independent of actual dataset IDs, answers, or statistics. Do not claim an official scoring formula or measured accuracy without evidence.

## 5. Deliverables and checks

After preflight conflicts have been resolved, deliver:

- The revised `specs/03_DATA_CONTRACTS.md` as a review draft.
- A concise compatibility/change table against the existing `03` and public API examples in `01`.
- Traceability to relevant approved requirements and `02` behavioral sections.
- A proposed-decision/TBD table identifying which choices need human approval.
- Synthetic examples of complete match, complete mismatch, missing attachment, unreadable source, conflicting field with preserved partial results, non-comparison, validated fallback success, exhausted recovery, and human correction followed by recomparison.

Check consistency of enums, nullability, numeric serialization, evidence references, and cross-model invariants. Ensure no example exposes unresolved work as `No mismatch detected`. Do not run the application, call live providers, modify source documents or datasets, alter tests, implement models in `src`, change `04`–`06`, or claim runtime conformance. Summarize actual documentation validation and remaining decisions accurately.
