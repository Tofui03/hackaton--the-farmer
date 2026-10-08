# Shipping Document Verification System (SDOC) — Engineering & AI Playbook

## 1. Project Overview & Environment
- **Domain**: Automated verification and discrepancy detection between Shipping Instructions (SI) and draft Bills of Lading (BL) across maritime logistics documentation.
- **Dataset & Ground Truth**:
  - `sdoc-hackathon-bundle/inbox/`: 520 operational shipping emails (`email_001` to `email_520`).
  - `sdoc-hackathon-bundle/attachments/`: Associated SI and BL document attachments (`.txt`, `.pdf`, `.docx`, `.xlsx`).
  - `Shipping Document Verification Use Case.pdf` & `SPEC-shipping-verification.md`: Complete business domain specification.
- **Core Invariant**: Exact comparison of 7 mandatory fields:
  1. `shipper` (Entity text, suffix-insensitive, semantic match)
  2. `consignee` (Entity text, semantic match)
  3. `notify_party` (Entity text, semantic match)
  4. `port_of_loading` (Origin port / POL, UN/LOCODE e.g. MYPKG)
  5. `port_of_discharge` (Destination port / POD, UN/LOCODE e.g. PECLL)
  6. `container_count` (Integer container count)
  7. `gross_weight_kg` (Decimal weight in KG, unit normalization, $\pm 1$ kg tolerance)
- **Environment**: Linux, Python 3.14 (Virtualenv located at `.venv`).
- **Safety Net**:
  - Direct execution: `.venv/bin/pytest` (configured with `pytest.ini`).
  - Benchmark: Must strictly maintain **246/246 tests passing** at all times.

---

## 2. Architectural Paradigm: Strict Domain-Driven Design (DDD)

Every developer and AI agent working on this repo MUST adhere to:

### 1. Layering & Dependency Inversion
- **Domain Layer (`domain/` or `src/domain/`)**:
  - Must remain pure. NO dependencies on FastAPI, ORMs, databases, HTTP clients, external cloud SDKs.
  - Contains: Entities, Value Objects, Aggregates, Domain Events, Domain Services, and Repository Interfaces (ABCs/Protocols).
- **Application Layer (`application/` or `src/application/`)**:
  - Orchestration only: Load Aggregate -> Execute Aggregate Method -> Save Aggregate -> Publish Events.
  - NO business logic, calculations, or status transition checks here.
- **Infrastructure Layer (`infrastructure/` or `src/infrastructure/`)**:
  - Implements Repository interfaces, DB/cache storage, document parsers, and LLM adapters.
  - Translates between persistence/transport representations and rich domain models via Mappers.

### 2. Rich Domain Models (Anti-Anemic)
- **Zero Public Setters**: Never create public setters on Entities or Aggregates.
- **Business Methods Only**: State mutations must happen via explicit domain verbs (e.g. `verification.record_discrepancy(...)`, `verification.escalate_to_review(reason)`).
- **Encapsulate Invariants**: All business validation and state rules must be self-contained inside the Aggregate/Value Object. Raise explicit domain exceptions when invariants fail.
- **Avoid Primitive Obsession**: Wrap domain concepts into Value Objects (e.g., `WeightKg`, `PortCode`, `ContainerCount`, `PartyName`).

### 3. Aggregate Boundary Rules
- Outside layers may only reference the **Aggregate Root**. Never mutate internal child entities directly.
- Aggregates must reference other Aggregates strictly by their **ID**, not by direct object references.

### 4. Code Review Rule
If any proposed code introduces business `if/else` checks into an Application Service or adds a generic setter to an Entity, immediately reject and refactor it into the domain model.

---

## 3. Core Refactoring Priority: `src/comparator/`
- Transform procedural/monolithic field comparison (`src/comparator/field_comparator.py`) into **Strategy Pattern + Clean Architecture**.
- Dedicated, extensible comparison strategies per field type:
  - `EntityTextStrategy` (shipper, consignee, notify_party)
  - `PortLocationStrategy` (port_of_loading, port_of_discharge)
  - `ContainerCountStrategy` (container_count)
  - `WeightToleranceStrategy` (gross_weight_kg)
- Zero regression against existing 246 pytest tests and 101 business fixtures.

---

## 4. Engineering & Git Collaboration Workflow
- Never commit directly to `main`. Always work on isolated feature branches (`refactor/...`, `feat/...`).
- Small, atomic commits following **Conventional Commits** (`feat:`, `refactor:`, `test:`, `chore:`).
- AI Pair-Programming Cycle:
  1. Define Contract / Interface
  2. Test First (TDD)
  3. Micro-implementation
  4. Run `.venv/bin/pytest` (246 passed)
  5. Git Commit & Push
