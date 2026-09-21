# 04_UI_UX_SPEC.md — UI/UX Specification for GitHub Pages & API Docs

> **Status**: Approved  
> **Implements**: [`specs/01_PROJECT_DESIGN.md`](file:///d:/ship/specs/01_PROJECT_DESIGN.md)

---

## 1. Objectives

Provide examiners and operational staff with an immediate, transparent visual audit tool hosted on GitHub Pages:
- Live URL: `https://tofui03.github.io/hackaton--the-farmer/`
- Zero server setup required to inspect results.

---

## 2. Dashboard Structure & Layout

1. **Header**:
   - Title: "SDOC Shipping Audit Engine"
   - Subtitle: "Zero False Alarms • Golden SI Benchmark • HITL Fallback"
   - Direct download/view buttons for `submission.json` and `audit_report.json`.
2. **KPI Scorecard**:
   - Total Audited: 520
   - Discrepancies Caught: 21
   - HITL Escalations: 63
   - False Alarm Rate: 0.0%
3. **Filter Navigation**:
   - Tabs: `All (520)`, `Mismatches (21)`, `HITL Review (63)`, `Matched OK (436)`, `Vetoed Non-Comp (395)`.
   - Real-time search bar filtering across Email ID, category, or notes.
4. **Data Grid**:
   - Columns: Email ID, Category, Audit Status Badge (`MATCH OK`, `MISMATCH`, `HITL REVIEW`, `VETOED`), Result Summary & Discrepancies, HITL Details, Action ("Inspect").
5. **Detail Drawer / Modal**:
   - Full JSON viewer presenting the exact Strict Output Contract record.
