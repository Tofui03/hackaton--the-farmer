# Dependency Audit & Environment Isolation Report (Task T00-02)

> **Task ID**: `T00-02` — Dependency Audit & Environment Isolation  
> **Status**: COMPLETED  
> **Authority**: [`AGENTS.md`](../AGENTS.md) §8, [`specs/06_TASKS.md`](../specs/06_TASKS.md) §5  
> **Execution Date**: 2026-09-22  
> **Governance Constraint**: No production behavior modified; no existing tests modified; no package upgrades/removals applied; recommendations recorded without premature implementation.

---

## 1. Python Environment & Execution Context

### Current State
- **Python Executable**: `C:\Users\tofui\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe`
- **Python Version**: `3.12.10` (tags/v3.12.10:0cc8128, MSC v.1943 64-bit AMD64)
- **Virtual Environment Status**: `In venv: False` (executing in Windows User-Site Python 3.12 environment)
- **Site-Packages Path**: `C:\Users\tofui\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\site-packages`
- **Pip Check Status**: `No broken requirements found` (Exit Code 0)

### Risks
- Running without a dedicated `.venv` in the workspace means development relies on user-level package state. While all required dependencies are installed and passing, global user packages (`matplotlib`, `cycler`, etc.) are present in the site-packages context.

### Recommended Later Action
- For standalone containerized CI/CD or production deployment (e.g. Render/Docker), spin up an isolated virtual environment (`python -m venv .venv`) and install `requirements.txt`.
- For current local execution, preserve the active user environment as instructed by governance rules.

---

## 2. Declared vs. Installed Dependency Comparison

| Package Name | Declared in `requirements.txt` | Currently Installed | Classification | Role in System |
|---|---|---|---|---|
| `fastapi` | `>=0.110.0` | `0.141.1` | DIRECT RUNTIME | REST API framework, routes, CORS middleware. |
| `uvicorn` | `>=0.28.0` | `0.53.0` | DIRECT RUNTIME | ASGI web server for local & production hosting. |
| `pydantic` | `>=2.0.0` | `2.13.5` (core `2.46.5`) | DIRECT RUNTIME | Data contracts, validation schemas (`ConfigDict`, `model_validator`). |
| `pypdf` | `>=5.0.0` | `6.16.1` | DIRECT RUNTIME | PDF document text extraction and stream error detection. |
| `python-docx`| `>=1.1.0` | `1.2.0` | DIRECT RUNTIME | Word `.docx` table and text block extraction. |
| `openpyxl` | `>=3.1.2` | `3.1.5` | DIRECT RUNTIME | Excel `.xlsx` workbook parsing. |
| `python-dotenv`| `>=1.0.0` | `1.2.3` | DIRECT RUNTIME | Environment configuration loading (`.env`). |
| `tqdm` | `>=4.66.0` | `4.70.1` | DIRECT RUNTIME | Batch CLI progress visualization in `src/run_pipeline.py`. |
| `gunicorn` | `>=21.2.0` | `26.2.0` | DIRECT RUNTIME | WSGI/ASGI process manager (optional production deployment). |
| `google-genai`| `>=0.1.1` | `2.24.0` | OPTIONAL PROVIDER | Google Gemini AI client SDK (calls gated behind API key). |
| `google-auth` | *Undeclared (transitive)* | `2.58.0` | OPTIONAL PROVIDER | GCP token and service account credential support. |
| `pytest` | `>=8.0.0` | `9.1.1` | DEV / TEST | Test execution runner and assertion framework. |
| `httpx` | *Undeclared (transitive)* | `0.28.1` | DEV / TEST | HTTP client utilized by `fastapi.testclient.TestClient`. |
| `starlette` | *Transitive (`fastapi`)* | `1.6.0` | TRANSITIVE RUNTIME | Core ASGI toolkit underlying FastAPI. |
| `anyio` | *Transitive (`fastapi/starlette`)* | `4.15.1` | TRANSITIVE RUNTIME | Async networking and concurrency library. |

### Pydantic v2 Compatibility Verification:
- Executed synthetic validation using `pydantic>=2.0.0` features (`ConfigDict(extra='forbid')`, `@field_validator`, `@model_validator(mode='after')`).
- **Result**: 0 warnings, 0 deprecation notices. Environment is 100% compliant with Pydantic v2 data contract requirements.

---

## 3. Deprecation Warning Diagnosis

During pytest execution (`16 passed in 0.77s–0.89s`), two warnings are emitted:

### Warning 1: `StarletteDeprecationWarning`
- **Location**: `fastapi/testclient.py:1`
- **Text**: `Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.`
- **Origin**: Upstream Starlette package notice inside `starlette.testclient.TestClient`.
- **Impact on Correctness**: Zero impact. All test requests via `TestClient(app)` execute synchronously and return status codes and response models correctly.
- **Action**: Safe to defer. Speculative package upgrades or suppressing warnings are forbidden by governance.

### Warning 2: `DeprecationWarning: BlockingPortal`
- **Location**: `starlette/testclient.py:53`
- **Text**: `The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.`
- **Origin**: Upstream `anyio` 4.x relocation notice affecting Starlette 1.6.0 internal import.
- **Impact on Correctness**: Zero impact. Standard non-breaking alias notice.
- **Action**: Safe to defer.

---

## 4. Frontend Implementation Environment Pre-Check

Future Wave 5 frontend stack: **React + Vite + TypeScript + Tailwind CSS** (Task `T14-01`+).

### Current State
- **Node.js**: Installed, version **`v24.18.0`** (LTS/Current)
- **npm**: Installed, version **`11.16.0`**
- **Readiness**: Tooling is present and fully compatible with modern Vite 5+ and React 18/19 scaffolding.
- **Governance Invariant**: Zero frontend files initialized during `T00-02`. Frontend setup belongs exclusively to Wave 5 (`T14-01`).

---

## 5. Secret & Configuration Safety Audit

### Current State
- **Environment Loader**: `src/config.py` loads from root `.env` via `python-dotenv`.
- **Local Secret Storage**: `.env` file **does not exist** in the workspace.
- **Configuration Template**: `.env.example` is committed and contains only inert placeholder strings (`GEMINI_API_KEY=your_gemini_api_key_here`).
- **Git Ignore Protection**: `.gitignore` explicitly ignores `.env`, `*.env`, `venv/`, and `.pytest_cache/`.
- **Deterministic CI Independence**: The pipeline and test suite execute 100% deterministically without requiring `GEMINI_API_KEY` or external GCP credentials. If credentials are missing, system falls back safely without test failure.

---

## 6. Evaluation Dataset & Path Coupling Audit

Codebase inspection identified direct references to `sdoc-hackathon-bundle/` or path configurations:

| File & Line | Reference | Classification | Future Wave Action |
|---|---|---|---|
| `tests/test_parsers.py:11` | `BASE_DIR = Path(...) / "sdoc-hackathon-bundle" / "attachments"` | **LEGACY TEST DEPENDENCY** | Replaced with synthetic multi-format fixtures in `T01-02`. |
| `tests/test_pipeline.py:9` | `BUNDLE_DIR = Path(...) / "sdoc-hackathon-bundle"` | **LEGACY TEST DEPENDENCY** | Replaced with synthetic email fixtures in `T01-01`. |
| `src/run_pipeline.py:45, 181`| `--bundle default="sdoc-hackathon-bundle"` | **LEGACY RUNTIME DEPENDENCY** | Parameterized in `T11-02` / `T13-01` to accept arbitrary fixture bundles. |
| `sdoc-hackathon-bundle/loader.py` | SDOC inbox loading utility | **EVALUATION-ONLY DEPENDENCY** | Safe / intentional. Part of immutable evaluation bundle. |
| `src/pipeline/schema.py:40`| Docstring mentioning competition submission | **SAFE / INTENTIONAL** | Pure docstring comment. |

### Machine-Specific Path Check:
- Zero hardcoded drive letters (`C:\`, `D:\`) or developer-specific absolute paths exist in production code or tests.
- All paths are dynamically computed using `Path(__file__).resolve().parent`.

---

## 7. Summary of Risks & Governance Guardrails

1. **Test Isolation Risk**: Current tests in `tests/test_parsers.py` and `tests/test_pipeline.py` depend directly on evaluation files in `sdoc-hackathon-bundle/`.  
   *Guardrail*: Wave 0 Tasks `T01-01` through `T01-04` introduce isolated synthetic fixtures in `tests/fixtures/`, removing all live evaluation data dependencies from test suites.
2. **Deterministic CI Independence**: Live external AI credentials must remain optional.  
   *Guardrail*: Tasks `T07-01` through `T07-04` enforce abstract mock adapters so that offline suites execute with zero network calls.
