# Specification synchronization amendment — 2026-09-22

Status: APPROVED for the scoped synchronization below.

Authorization: The user supplied the project handoff, requested verification, and confirmed `ok` after the review proposed synchronizing conflicting product clauses, clarifying parsing recovery in `02`, and preparing the Data Contracts generation prompt. This approval does not authorize application implementation or resolve business-rule TBDs.

## Evidence and scope

- The working-tree `02_AI_PIPELINE_SPEC.md` already contained the two requested final corrections: intent independent of attachment count (§4.4) and preservation of partial reliable work (§12.2). Its prior header was already APPROVED / BASELINED revision 3.0.
- `00_PRODUCT_SPEC.md` and `PRODUCT_SPEC.md` were byte-identical legacy copies. Both retained Awaiting User Review & Approval, attachment pre-filtering, weight tolerance, and dataset-specific content. Commit `6e75222` retained that content despite its approval-themed title.
- Existing user changes in `01_PROJECT_DESIGN.md` and `02_AI_PIPELINE_SPEC.md` were preserved. `PROJECT_DESIGN.md` was already untracked and is not promoted to authority by this amendment.

## Authorized changes applied

| Area | Previous wording | Synchronized rule / authority |
|---|---|---|
| Product status | Awaiting approval | APPROVED / BASELINED revision 3.1 under this explicit synchronization approval |
| SI reference | Sole reference ground truth / always authoritative | Reference document; unresolved SI information requires HITL (handoff §§1, 7, 10) |
| Intent | Zero attachments plus absent explicit mention excludes comparison | Attachment count is not a negative intent gate (`02` §4.4) |
| Category naming | `new_si_request`, `general_message` | Handoff / `02` names `new_shipping_instruction`, `general`; external evaluation aliases remain separate |
| Comparison | ±1 kg and assumed semantic equivalence | Exact mathematical normalization; DEC-P06C/D/E remain TBD (`01` decision register, handoff §17) |
| Scope and provenance | XLSX labelled as original-use-case requirement | TXT core, DOCX/PDF advanced, XLSX design extension; policy and source attribution distinguished |
| Reliability | String-only evidence and immediate failure escalation | Source-grounded evidence, applicable validated recovery, partial reliable results (`02` §§7, 12, 15) |
| Evaluation | Fixed dataset size, IDs, internal/evaluation contract conflation | Dataset-independent criteria; sample schema applies to evaluation output only |
| Product assumptions | Existing code treated as approval of business rules | Approved decisions govern; implementation and test results do not establish requirements |
| Parsing diagram / traceability | Parser failure directly reaches HITL | Assess applicable approved recovery/OCR, validate results, then escalate if unavailable or unsuccessful |

The two product files remain identical; `00_PRODUCT_SPEC.md` is authoritative under `AGENTS.md`. Existing requirement IDs were retained, and HL-005 records the already-approved partial-result obligation. Acceptance criteria were changed only to reflect the supplied approved handoff and the conflict corrections, not to accommodate test results.

## Boundaries and remaining cross-document checks

This is not a declaration that the complete specification suite is consistent or implemented. No changes are made to `AGENTS.md`, `01_PROJECT_DESIGN.md`, `PROJECT_DESIGN.md`, `03_DATA_CONTRACTS.md`, `04`–`06`, source code, tests, or datasets.

Before drafting a replacement Data Contracts baseline, explicitly check these remaining items rather than silently overriding upstream text:

1. `01` §3.2 still lists legacy category names. The handoff and `02` use the synchronized product names. Record the naming discrepancy and obtain approval for any needed architectural-document amendment or compatibility interpretation.
2. `01` §§10–11 retain terse corruption-to-HITL wording and four reason codes. Distinguish terminal unrecoverability from initial parser failure and internal logical causes from evaluation reason codes; do not assume an unapproved mapping.
3. `01` §9 and existing `03` specify audit models, while `02` requires richer evidence and partial results. Any incompatible public-contract change must be explicitly proposed for human review.
4. `02` §16 uses string evidence and numeric Python examples, whereas its behavioral rules allow structured evidence and require exact mathematical comparison. Decide whether examples are illustrative or require amendment before treating a replacement model as approved. Binary floating-point examples do not independently authorize rounding tolerances.
5. Unresolved Stage-1 classification may require HITL under `02` §15, while the category requirement calls for exactly one of five categories. `03` must surface any missing provisional/final-state decision instead of fabricating a sixth category or a confident classification.

## Verification

Documentation verification only: inspect the diff, check synchronized product copies, verify the two original AI corrections remain, check revision markers and preserved TBDs, and inspect links. Runtime tests are not evidence for these specification changes and are not rerun for this amendment.
