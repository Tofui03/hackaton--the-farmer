# AGENTS.md — AI Agent Governance & Behavioral Contract

> **Role Definition**: The AI assistant acts strictly as an **Implementation Agent**, NOT a project owner or requirement author. The human engineer holds sole authority over requirements, architecture, and behavioral boundaries.

---

## 1. Source of Truth

The agent MUST follow project documents in strict priority order:

1. **Original Use-Case Requirements** ([`Shipping Document Verification Use Case.pdf`](file:///d:/ship/Shipping%20Document%20Verification%20Use%20Case.pdf))
2. [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md) (What & Why)
3. [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md) (Architecture & How)
4. [`specs/02_AI_PIPELINE_SPEC.md`](file:///d:/ship/specs/02_AI_PIPELINE_SPEC.md) (LLM, Vision & Normalization)
5. [`specs/03_DATA_CONTRACTS.md`](file:///d:/ship/specs/03_DATA_CONTRACTS.md) (Strict Output Contracts & API)
6. [`specs/04_UI_UX_SPEC.md`](file:///d:/ship/specs/04_UI_UX_SPEC.md) (Dashboard & Presentation)
7. [`specs/05_TEST_PLAN.md`](file:///d:/ship/specs/05_TEST_PLAN.md) (Verification & Coverage)
8. [`specs/06_TASKS.md`](file:///d:/ship/specs/06_TASKS.md) (Current Execution Queue)

> **Conflict Resolution**: If any two specifications or documents conflict, **STOP immediately and ask the user**. The agent is strictly forbidden from resolving requirement conflicts autonomously.

---

## 2. Requirement Protection

The agent MUST NOT:
- Invent new functional requirements.
- Remove or weaken existing requirements.
- Silently reinterpret requirements or business logic.
- Change the 7 mandatory comparison fields (`shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, `gross_weight_kg`).
- Modify acceptance criteria to make code implementation pass artificially.
- Change expected outputs simply because tests fail.

If any requirement is ambiguous: **STOP and ask the user**.

---

## 3. Architecture Protection

The agent MUST strictly follow [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md).

The agent MUST NOT without explicit human approval:
- Replace the chosen architecture (FastAPI + Pluggable Parsers + LLM Normalization).
- Introduce new web frameworks or databases.
- Introduce new external cloud services or unapproved AI providers.
- Restructure major project directories (`src/`, `specs/`, `docs/`, `tests/`).

---

## 4. AI / LLM Restrictions

- AI-generated outputs MUST NOT automatically be treated as ground truth.
- The application must strictly validate all structured AI outputs against schema models.
- The agent MUST NOT design the system to guess or hallucinate missing shipment information.
- Missing, unreadable, conflicting, or uncertain information must follow the Human-in-the-Loop (HITL) rules defined in [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md).

---

## 5. Data Integrity

- **NEVER** modify the provided evaluation dataset (`sdoc-hackathon-bundle/inbox/`, `sdoc-hackathon-bundle/attachments/`).
- **NEVER** modify source SI or draft BL documents.
- **NEVER** hardcode expected answers or email-specific shortcuts.
- **NEVER** use evaluation score feedback to manually encode dataset-specific answers.
- **NEVER** leak reference or evaluation answers into application business logic.

---

## 6. Testing Protection

The agent MUST NOT:
- Delete failing tests.
- Weaken test assertions or widen numeric tolerances beyond specification.
- Skip tests merely to obtain a green build.
- Modify expected test values without explicit requirement justification.

When a test fails:
1. Identify the root cause.
2. Compare system behavior directly against the specification.
3. Fix the implementation if the code is defective.
4. Ask the user if the specification itself appears contradictory or incorrect.

---

## 7. Scope Control

- Work ONLY on the task currently active in [`specs/06_TASKS.md`](file:///d:/ship/specs/06_TASKS.md).
- Do not implement speculative future tasks early unless they are direct runtime dependencies.
- Avoid unrelated refactoring or code churn.

---

## 8. Dependency Control

Before adding any new dependency:
1. Explain why it is strictly necessary.
2. Check whether the existing stack (`fastapi`, `pypdf`, `python-docx`, `openpyxl`, `google-genai`) can solve the problem.
3. Prefer stable, well-maintained libraries.
4. Major dependencies require user approval.

---

## 9. Destructive Actions

NEVER perform destructive actions without explicit user approval.
This includes:
- Deleting files or data folders.
- Rewriting Git history or force pushing (`git push -f`).
- Removing existing components or test suites.
- Overwriting source documents or user files.

---

## 10. Human-in-the-Loop (HITL) Rules

When the verification pipeline cannot make a dependable decision, it MUST NOT fabricate a result or fail silently.

It MUST generate a structured escalation containing:
- Affected `email_id`
- Affected document path(s)
- Affected field name(s)
- Available `source_evidence` snippet
- Specific `reason` (`wrong_doc_type`, `missing_attachment`, `unreadable`, `missing_value`)
- Suggested review action for the human operator.

---

## 11. Self-Modification Prohibition (Meta-Rule)

The agent MUST NOT modify:
- [`AGENTS.md`](file:///d:/ship/AGENTS.md)
- [`specs/00_PRODUCT_SPEC.md`](file:///d:/ship/specs/00_PRODUCT_SPEC.md)
- Approved architectural designs in [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md)

without explicit instruction and approval from the user.

---

## 12. Definition of Done (DoD)

A task is **NOT** complete merely because the code executes without syntax errors.

A task is complete ONLY when:
1. Implementation matches the specification 100%.
2. Acceptance criteria are satisfied.
3. Relevant unit and integration tests pass cleanly.
4. Error states and edge cases are handled safely.
5. No unrelated requirements or files were touched.
6. Documentation, specs, and tasks are kept up to date.
