# 02_AI_PIPELINE_SPEC.md — AI & Prompt Engineering Specification

> **Status**: Approved  
> **Implements**: [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md)

---

## 1. Model Configuration

- **Primary Model**: Google Gemini (`gemini-2.5-flash` or `gemini-1.5-flash`).
- **Client SDK**: `google-genai` official SDK.
- **Generation Parameters**:
  - `temperature`: 0.1 (deterministic extraction and verification)
  - `response_mime_type`: `"application/json"`
  - `max_retries`: 4 with exponential backoff ($1.0\text{s} \times 2.0^{\text{attempt}}$).

---

## 2. Stage 1: Batch Classification Strategy

- **Batch Size**: 25–50 emails per prompt.
- **Token Efficiency**: 520 emails are processed in approximately 12–15 API requests rather than 520 individual calls.
- **Input Snippet**: Includes `email_id`, `from`, `subject`, attachment file list, and body preview (first 300 characters).
- **Output Schema**:
  ```json
  [
    {
      "email_id": "email_001",
      "category": "BL_COMPARISON"
    }
  ]
  ```
- **Fallback Mechanism**: Deterministic keyword and header heuristics if API key is not configured or network fails.

---

## 3. Stage 3: Document Comparison Prompt

- **Golden Reference Principle**: The prompt explicitly anchors SI as the single source of truth.
- **Context Injection**:
  - Reference document: Clean text from SI.
  - Candidate document: Clean text from draft BL.
- **7-Field Output Schema**:
  Returns extracted SI values, extracted BL values, status (`OK`, `MISMATCH`, `NEEDS_REVIEW`), list of differing fields, and brief discrepancy explanation.
