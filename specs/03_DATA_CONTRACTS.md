# 03_DATA_CONTRACTS.md — Data Contracts & Interface Schemas

> **Status**: APPROVED / BASELINED
> **Revision**: 2.0-baselined (2026-09-22)
> **Authority**: Original use case → [00](00_PRODUCT_SPEC.md) → [01](01_PROJECT_DESIGN.md) → [02](02_AI_PIPELINE_SPEC.md)
> **Context**: [Approved synchronization amendment](AMENDMENT_2026-09-22.md) & Human Decision Review (2026-09-22)
> **Scope**: Authoritative data contracts and interface schemas; baseline established for UI/UX and test planning.

## 1. Approval boundary and preflight

The human reviewer approved DC-01, DC-03, DC-05, and DC-07; approved with modifications DC-04, DC-06, and DC-08; and corrected DC-02. Existing approved behaviors are carried forward. New representations and compatibility choices below reflect these decisions while keeping the document under human review until baseline approval.

| Check | Evidence | Treatment in this draft | Approval status |
|---|---|---|---|
| Category names (DC-01) | Approved handoff, `00` EC-001, `02` §4.1; 5 canonical categories | `category=null` allowed ONLY as an internal unresolved classification state. Downstream/export contracts requiring 5 categories reject unresolved records until review resolves it. | APPROVED (DC-01) |
| HITL reasons & official schema (DC-02) | `sample_submission.json` defines template with `review_reason: null`; bundle README illustrates `review_reason` examples. | Do NOT label reasons as an "official four reason taxonomy". Maintain rich internal `LogicalReason` taxonomy. Evaluation Adapter maps only verified official fields; unmappable states block export. | CORRECTED & APPROVED (DC-02) |
| Evidence and audit model (DC-03) | Tri-state mismatch behavior and workflow observability | `mismatch_detected` is `true` (resolved mismatch), `false` (resolved no mismatch), `null` (unresolved / review required). Explicit `state` and `review.state` prevent inferring workflow solely from null. | APPROVED (DC-03) |
| Decimal internal & serialization (DC-04) | Exact equality requires `Decimal`; `02` §16 uses illustrative floats | Canonical internal representation for `gross_weight_kg` is `Decimal`. Serialization is adapter-specific: lossless plain decimal string internally, API schema compliant, and evaluation export conforms strictly to `sample_submission.json` (`defect_fields`). Container count remains strict integer. | APPROVED WITH MODIFICATION (DC-04) |
| Evidence provenance (DC-05) | Strict source grounding | Structured source-grounded evidence retained. No fabricated coordinates, OCR regions, or metadata. | APPROVED (DC-05) |
| Total attempt limits (DC-06) | Avoid "retry" ambiguity | Explicit total attempt limits: `technical_attempt_limit` and `semantic_attempt_limit`. Limit explicitly includes the initial attempt. Maximum budget = `technical_attempt_limit × semantic_attempt_limit`. | APPROVED WITH MODIFICATION (DC-06) |
| Human review scope (DC-07) | Review capability requires full correction scope | `POST /audit/{email_id}/review` with `expected_revision`. Reviewers cannot set mismatch booleans directly; corrections re-run normalization and comparison. Scope covers classification, SI/BL roles, extracted fields, and evidence. | APPROVED WITH MODIFICATION (DC-07) |
| Safe export blocking (DC-08) | Lossless evaluation contract compliance | Evaluation export MUST be blocked (`EXPORT_BLOCKED`) whenever an unresolved or internal state cannot be truthfully and losslessly represented under the verified official evaluation contract. | APPROVED WITH MODIFICATION (DC-08) |

These decisions clarify the boundaries without premature implementation. No changes to `00`, `01`, `02`, `AGENTS.md`, deployment, or application code are made in this stage.

## 2. Contract conventions

All rules in §§2–10 are proposed schema realizations of the approved behaviors unless explicitly marked SOURCE or APPROVED.

- UTF-8 JSON; snake_case keys; enums are case-sensitive. Missing and null differ: a field without a Pydantic default is required even when nullable.
- `extra="forbid"` applies to trusted application/API contracts. Provider responses first follow `02` §16 (including its existing extra-field discard policy), then an adapter builds and validates the trusted record.
- IDs are opaque, non-empty strings. Document IDs identify source artifacts, not inferred document roles. Paths are references, never authorization for arbitrary filesystem access or network fetching.
- Types are strict. Booleans are not container integers. No maximum weight/count or shipping-industry range is introduced.
- `container_count` canonical values are strict integers. `gross_weight_kg` canonical values use `Decimal` internally for exact equality comparison without floating-point arithmetic or rounding. Serialization is adapter-specific: lossless plain decimal string internally (e.g. `"22000"`, `"22500.5"`), API schema compliant, and evaluation export follows `sample_submission.json` exactly (reporting `defect_fields` list).
- Company/port canonical strings use only approved deterministic formatting rules. Rule-version references record the rules actually applied. DEC-P06C/D/E remain TBD.
- Source strings and source documents remain immutable. Unit conversion precedes comparison, with the raw value, evidence and normalization-rule version retained.
- Empty extraction is explicitly unsuccessful/unreadable, not success with `""`. Parser `PARTIAL` may still yield reliable mandatory fields.
- A candidate may be missing or ungrounded. A **reliable** selected candidate must be grounded, unambiguous, schema-valid, and successfully normalized. A confidence label cannot make it reliable.
- Attempt limits (`technical_attempt_limit`, `semantic_attempt_limit`) explicitly include the initial attempt.

## 3. Models and ownership

| Model | Producer → consumer | Required meaning |
|---|---|---|
| EmailRecord | Input adapter → classification | Original message context, attachment references; input `from` maps explicitly to `sender` |
| AttachmentReference | Loader → identification/parser | ID, relative source path, optional declared MIME; no role assumption |
| ClassificationResult | Validated classifier → gate | Resolved category plus evidence, or proposed unresolved review state |
| DocumentReference | Identification → parser/extractor | Observed role SI/BL/unknown, reference to attachment and identification evidence |
| ParserResult | Parser/OCR → extractor | Explicit status, available content, usability, diagnostic evidence and attempt references |
| FieldEvidence | Source adapter → validation/review | Source identity plus verifiable text/cell/page/region/metadata/error context |
| FieldCandidate | Extractor → reliability gate | Raw candidate and supporting evidence, without an equality judgment |
| NormalizedField | Deterministic normalizer → gate/comparator | Typed canonical value and rule version, or explicit unsuccessful state |
| ExtractedField | Reliability gate → comparator/review | Candidates, selection, reliability, normalized value and explanation |
| DocumentExtraction | Extractor/gate → comparator/review | Seven named fields for one identified document; unresolved entries retained |
| FieldComparison / PartialResult | Deterministic comparator → report | Comparisons only where both fields are reliable; unresolved field partition |
| Discrepancy | Comparator → report | Confirmed inequality with SI/BL values; may be partial during review |
| ReviewCase / ReviewIssue | Gate/failure handler → operator | Context, logical cause, affected document/role/field, evidence and suggested action |
| ProcessingMetadata / AttemptRecord | Stage controller → audit | Actual bounded attempts, fallback outcomes, optional provider metadata |
| AuditRecord | Report assembler → API/review | Overall outcome, preserved source context, extraction, comparisons and review |
| ReviewUpdate / FieldCorrection | Human operator → validation | Proposed source-grounded correction; never an operator-authored match boolean |
| SubmissionRecord | Evaluation adapter → evaluation service | External-only schema; never the internal source of truth |

### 3.1 Pydantic v2 reference definitions

The following self-contained model block is a **documentation reference**, not production code. It makes type and representative cross-model rules executable for document checking. Source grounding and approved normalization still require deterministic validation against the actual source; Pydantic cannot establish truth from a non-empty evidence string. Service-level invariants in §§4–8 remain mandatory parts of the proposal.

```python
from __future__ import annotations
from decimal import Decimal
from typing import Annotated, Literal, Self
import re
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Text = Annotated[str, Field(min_length=1)]
Category = Literal['document_comparison', 'new_shipping_instruction', 'invoice_query', 'general', 'spam']
FieldName = Literal['shipper', 'consignee', 'notify_party', 'port_of_loading', 'port_of_discharge', 'container_count', 'gross_weight_kg']
FIELD_NAMES = ('shipper', 'consignee', 'notify_party', 'port_of_loading', 'port_of_discharge', 'container_count', 'gross_weight_kg')
Role = Literal['SI', 'BL']
Stage = Literal['ingestion', 'classification', 'identification', 'parsing', 'ocr', 'extraction', 'normalization', 'reliability', 'comparison', 'review', 'serialization']
LogicalReason = Literal['missing_attachment', 'unreadable_document', 'wrong_or_uncertain_document_type', 'missing_required_value', 'uncertain_result', 'conflicting_candidate_values', 'processing_or_provider_failure']
Canonical = str | StrictInt

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def validate_canonical(field: str, value: object) -> None:
    if field == 'container_count':
        require(type(value) is int, 'container_count must be an integer, not bool')
    else:
        require(isinstance(value, str) and bool(value.strip()), 'canonical text must be non-empty')
        if field == 'gross_weight_kg':
            require(re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value) is not None, 'weight must be a finite plain decimal string')

def canonical_equal(field: str, left: Canonical, right: Canonical) -> bool:
    validate_canonical(field, left)
    validate_canonical(field, right)
    return Decimal(left) == Decimal(right) if field == 'gross_weight_kg' else left == right

class AttachmentReference(Contract):
    document_id: Text
    path: Text
    mime_type: str | None = None

class EmailRecord(Contract):
    email_id: Text
    sender: str
    subject: str
    body: str
    attachments: list[AttachmentReference]

class EvidenceLocation(Contract):
    section: str | None = None
    page: Annotated[int, Field(ge=1)] | None = None
    table: str | None = None
    row: Annotated[int, Field(ge=0)] | None = None
    column: Annotated[int, Field(ge=0)] | None = None
    bbox: Annotated[list[Annotated[float, Field(ge=0, le=1)]], Field(min_length=4, max_length=4)] | None = None

    @model_validator(mode='after')
    def coordinates(self) -> Self:
        if self.bbox is not None:
            require(self.page is not None, 'region requires page')
            x0, y0, x1, y1 = self.bbox
            require(x0 < x1 and y0 < y1, 'bbox must be an ordered non-empty region')
        return self

class FieldEvidence(Contract):
    evidence_id: Text
    source_type: Literal['email', 'document', 'processing', 'human_review']
    source_id: Text
    kind: Literal['text_span', 'table_cell', 'page_region', 'document_metadata', 'processing_error', 'human_review']
    quote: Text | None = None
    location: EvidenceLocation | None = None
    detail: Text | None = None

    @model_validator(mode='after')
    def payload(self) -> Self:
        if self.kind in ('text_span', 'table_cell'):
            require(self.quote is not None, 'text/cell evidence requires source text')
        if self.kind == 'table_cell':
            require(self.location is not None and self.location.table is not None and self.location.row is not None and self.location.column is not None, 'cell requires table and coordinates')
        if self.kind == 'page_region':
            require(self.location is not None and self.location.bbox is not None, 'region requires coordinates')
        if self.kind in ('document_metadata', 'processing_error', 'human_review'):
            require(self.detail is not None, 'context evidence requires detail')
        return self

class ClassificationResult(Contract):
    state: Literal['RESOLVED', 'NEEDS_REVIEW']
    category: Category | None
    reason: Text
    evidence_ids: list[Text]
    confidence_indicator: Literal['HIGH', 'MEDIUM', 'LOW'] | None = None

    @model_validator(mode='after')
    def resolution(self) -> Self:
        require((self.category is not None) == (self.state == 'RESOLVED'), 'category exists only when resolved')
        if self.state == 'RESOLVED':
            require(bool(self.evidence_ids), 'resolved intent requires evidence')
        return self

class DocumentReference(Contract):
    document_id: Text
    role: Literal['SI', 'BL', 'UNKNOWN']
    identification_evidence_ids: list[Text]

class ParserResult(Contract):
    document_id: Text
    status: Literal['SUCCESS', 'PARTIAL', 'UNREADABLE', 'UNSUPPORTED']
    text: str | None
    usable_for_extraction: bool
    diagnostic_evidence_ids: list[Text]
    attempt_ids: list[Text]

    @model_validator(mode='after')
    def content_state(self) -> Self:
        if self.status in ('SUCCESS', 'PARTIAL'):
            require(self.text is not None and bool(self.text.strip()), 'empty extraction is not success/partial')
        if self.status in ('UNREADABLE', 'UNSUPPORTED'):
            require(not self.usable_for_extraction and bool(self.diagnostic_evidence_ids), 'failed parsing needs diagnostic context')
        return self

class FieldCandidate(Contract):
    raw_value: Text
    source_unit: str | None = None
    evidence_ids: list[Text]

class NormalizedField(Contract):
    field: FieldName
    state: Literal['VALID', 'INVALID', 'NOT_ATTEMPTED']
    value: Canonical | None
    rule_version: Text | None

    @model_validator(mode='after')
    def canonical(self) -> Self:
        if self.state == 'VALID':
            require(self.value is not None and self.rule_version is not None, 'valid normalization requires value and rules')
            validate_canonical(self.field, self.value)
        else:
            require(self.value is None, 'unsuccessful normalization has no trusted value')
        return self

class ExtractedField(Contract):
    field: FieldName
    reliability: Literal['NOT_PROCESSED', 'RELIABLE', 'MISSING', 'UNCERTAIN', 'CONFLICTING', 'UNREADABLE']
    candidates: list[FieldCandidate]
    selected_candidate: Annotated[int, Field(ge=0)] | None
    normalized: NormalizedField | None
    explanation: Text

    @model_validator(mode='after')
    def reliability_gate(self) -> Self:
        if self.selected_candidate is not None:
            require(self.selected_candidate < len(self.candidates), 'candidate index must exist')
        if self.normalized is not None:
            require(self.normalized.field == self.field, 'normalization field differs')
        if self.reliability == 'RELIABLE':
            require(self.selected_candidate is not None, 'reliable field requires selection')
            require(bool(self.candidates[self.selected_candidate].evidence_ids), 'reliable field requires evidence')
            require(self.normalized is not None and self.normalized.state == 'VALID', 'reliable field requires valid normalization')
        else:
            require(self.selected_candidate is None, 'unresolved field must not select a trusted candidate')
        if self.reliability == 'MISSING':
            require(not self.candidates, 'missing field cannot have candidate values')
        if self.reliability == 'CONFLICTING':
            require(len(self.candidates) >= 2, 'conflict requires multiple candidates')
        return self

class DocumentExtraction(Contract):
    document_id: Text
    role: Role
    fields: dict[FieldName, ExtractedField]

    @model_validator(mode='after')
    def seven_fields(self) -> Self:
        require(set(self.fields) == set(FIELD_NAMES), 'document field map must cover exactly seven fields')
        require(all(key == value.field for key, value in self.fields.items()), 'field key mismatch')
        return self

class FieldComparison(Contract):
    field: FieldName
    si_value: Canonical
    bl_value: Canonical
    outcome: Literal['MATCH', 'MISMATCH']
    rule_version: Text

    @model_validator(mode='after')
    def deterministic_outcome(self) -> Self:
        expected = 'MATCH' if canonical_equal(self.field, self.si_value, self.bl_value) else 'MISMATCH'
        require(self.outcome == expected, 'outcome disagrees with exact comparison')
        return self

class Discrepancy(Contract):
    field: FieldName
    si_value: Canonical
    bl_value: Canonical

class PartialResult(Contract):
    comparisons: list[FieldComparison]
    unresolved_fields: list[FieldName]

    @model_validator(mode='after')
    def partition(self) -> Self:
        compared = [item.field for item in self.comparisons]
        require(len(compared) == len(set(compared)), 'duplicate comparison')
        require(len(self.unresolved_fields) == len(set(self.unresolved_fields)), 'duplicate unresolved field')
        require(not set(compared).intersection(self.unresolved_fields), 'compared field cannot be unresolved')
        require(set(compared).union(self.unresolved_fields) == set(FIELD_NAMES), 'partial result must partition seven fields')
        return self

class AttemptRecord(Contract):
    attempt_id: Text
    operation_id: Text
    stage: Stage
    kind: Literal['primary', 'technical_retry', 'semantic_repair', 'fallback', 'ocr']
    attempt_number: Annotated[int, Field(ge=1)]
    outcome: Literal['SUCCEEDED', 'FAILED', 'INVALID']
    error_code: str | None = None
    provider_adapter: str | None = None
    model_identifier: str | None = None
    prompt_version: str | None = None
    token_usage: dict[str, Annotated[int, Field(ge=0)]] | None = None
    latency_ms: Annotated[int, Field(ge=0)] | None = None

class ProcessingMetadata(Contract):
    technical_attempt_limit: Annotated[int, Field(ge=1)] = 3
    semantic_attempt_limit: Annotated[int, Field(ge=1)] = 2
    attempts: list[AttemptRecord]

class ReviewIssue(Contract):
    issue_id: Text
    stage: Stage
    logical_reason: LogicalReason
    evaluation_reason: str | None = None
    document_ids: list[Text]
    expected_role: Role | None = None
    fields: list[FieldName]
    evidence_ids: Annotated[list[Text], Field(min_length=1)]
    suggested_action: Text
    recovery_state: Literal['NOT_APPLICABLE', 'UNAVAILABLE', 'EXHAUSTED', 'UNRELIABLE']
    recovery_detail: Text
    attempt_ids: list[Text]

class ReviewCase(Contract):
    review_id: Text
    state: Literal['OPEN', 'RESOLVED']
    issues: Annotated[list[ReviewIssue], Field(min_length=1)]

class AuditRecord(Contract):
    schema_version: Literal['1.0-draft'] = '1.0-draft'
    email_id: Text
    revision: Annotated[int, Field(ge=1)]
    previous_revision: Annotated[int, Field(ge=1)] | None = None
    email: EmailRecord
    classification: ClassificationResult
    state: Literal['COMPLETE', 'NEEDS_REVIEW']
    outcome: Literal['MATCH', 'MISMATCH', 'NOT_APPLICABLE'] | None
    mismatch_detected: bool | None
    result_summary: Text
    documents: list[DocumentReference]
    parsers: list[ParserResult]
    extractions: list[DocumentExtraction]
    evidence: list[FieldEvidence]
    partial_result: PartialResult | None
    discrepancies: list[Discrepancy]
    review: ReviewCase | None
    processing: ProcessingMetadata

    @model_validator(mode='after')
    def audit_invariants(self) -> Self:
        require(self.email_id == self.email.email_id, 'email identity mismatch')
        require(self.previous_revision is None or self.previous_revision < self.revision, 'invalid revision lineage')
        evidence = {e.evidence_id: e for e in self.evidence}
        require(len(evidence) == len(self.evidence), 'duplicate evidence ID')
        attachments = {a.document_id for a in self.email.attachments}
        require(len(attachments) == len(self.email.attachments), 'duplicate attachment ID')
        documents = {d.document_id: d for d in self.documents}
        require(len(documents) == len(self.documents), 'duplicate document reference')
        require(set(documents) <= attachments, 'document reference must identify an attachment')
        attempts = {a.attempt_id for a in self.processing.attempts}
        require(len(attempts) == len(self.processing.attempts), 'duplicate attempt ID')
        def refs(ids):
            require(set(ids) <= set(evidence), 'dangling evidence reference')
        refs(self.classification.evidence_ids)
        for d in self.documents:
            refs(d.identification_evidence_ids)
        for p in self.parsers:
            require(p.document_id in documents, 'parser source missing')
            refs(p.diagnostic_evidence_ids)
            require(set(p.attempt_ids) <= attempts, 'parser attempt missing')
        by_role = {}
        for extraction in self.extractions:
            require(extraction.document_id in documents and documents[extraction.document_id].role == extraction.role, 'extraction document/role mismatch')
            require(extraction.role not in by_role, 'ambiguous roles cannot enter trusted extraction')
            by_role[extraction.role] = extraction
            for f in extraction.fields.values():
                for candidate in f.candidates:
                    refs(candidate.evidence_ids)
                if f.reliability == 'RELIABLE':
                    selected = f.candidates[f.selected_candidate]
                    require(any(evidence[e].source_type == 'document' and evidence[e].source_id == extraction.document_id and evidence[e].kind != 'processing_error' for e in selected.evidence_ids), 'reliable value lacks evidence from its document')
        for item in self.evidence:
            if item.source_type == 'document':
                require(item.source_id in attachments, 'evidence document missing')
            if item.source_type == 'email':
                require(item.source_id == self.email_id, 'evidence email mismatch')
        if self.review is not None:
            for issue in self.review.issues:
                refs(issue.evidence_ids)
                require(set(issue.document_ids) <= attachments, 'review document missing')
                require(set(issue.attempt_ids) <= attempts, 'review attempt missing')
        category = self.classification.category
        if category != 'document_comparison':
            require(not self.documents and not self.parsers and not self.extractions and self.partial_result is None and not self.discrepancies, 'non-comparison/unresolved intent must not process attachments')
        else:
            require(self.partial_result is not None, 'comparison request requires explicit partial state')
            eligible = {}
            if 'SI' in by_role and 'BL' in by_role:
                for field in FIELD_NAMES:
                    si, bl = by_role['SI'].fields[field], by_role['BL'].fields[field]
                    if si.reliability == bl.reliability == 'RELIABLE':
                        eligible[field] = (si.normalized.value, bl.normalized.value)
            comparisons = {c.field: c for c in self.partial_result.comparisons}
            require(set(comparisons) == set(eligible), 'all and only reliable pairs must retain comparisons')
            for field, comparison in comparisons.items():
                require((comparison.si_value, comparison.bl_value) == eligible[field], 'comparison differs from normalized source values')
            expected = [(c.field, c.si_value, c.bl_value) for c in self.partial_result.comparisons if c.outcome == 'MISMATCH']
            require([(d.field, d.si_value, d.bl_value) for d in self.discrepancies] == expected, 'discrepancies must exactly preserve confirmed inequalities')
        if self.state == 'NEEDS_REVIEW':
            require(self.outcome is None and self.mismatch_detected is None, 'review is not a final outcome')
            require(self.review is not None and self.review.state == 'OPEN', 'review state requires an open case')
            require(self.result_summary != 'No mismatch detected', 'unresolved case cannot receive a clean pass')
        else:
            require(self.classification.state == 'RESOLVED', 'complete audit needs resolved category')
            require(self.review is None or self.review.state == 'RESOLVED', 'complete audit has open review')
            if category == 'document_comparison':
                require(not self.partial_result.unresolved_fields, 'complete comparison requires all seven pairs')
                expected_outcome = 'MISMATCH' if self.discrepancies else 'MATCH'
                require(self.outcome == expected_outcome and self.mismatch_detected == bool(self.discrepancies), 'incorrect final outcome')
                if expected_outcome == 'MATCH':
                    require(self.result_summary == 'No mismatch detected', 'match summary must be exact')
            else:
                require(self.outcome == 'NOT_APPLICABLE' and self.mismatch_detected is None, 'non-comparison is not a clean comparison')
                require(self.result_summary != 'No mismatch detected', 'non-comparison summary implies checking occurred')
        return self

class FieldCorrection(Contract):
    document_id: Text
    field: FieldName
    raw_value: Text
    evidence_ids: Annotated[list[Text], Field(min_length=1)]
    rationale: Text

class RoleCorrection(Contract):
    document_id: Text
    assigned_role: Literal['SI', 'BL', 'UNKNOWN']
    evidence_ids: Annotated[list[Text], Field(min_length=1)]
    rationale: Text

class ReviewUpdate(Contract):
    review_id: Text
    expected_revision: Annotated[int, Field(ge=1)]
    actor_id: Text
    action: Literal['CONFIRM', 'CORRECT']
    rationale: Text
    category: Category | None = None
    classification_evidence_ids: list[Text] = Field(default_factory=list)
    role_corrections: list[RoleCorrection] = Field(default_factory=list)
    corrections: list[FieldCorrection] = Field(default_factory=list)
    added_evidence: list[FieldEvidence] = Field(default_factory=list)

class DynamicVerifyRequest(Contract):
    email_id: Text = 'example-on-demand'
    si_text: str
    bl_text: str

class ErrorResponse(Contract):
    code: Text
    message: Text
    details: list[str]
    retryable: bool

class SubmissionRecord(Contract):
    category: Literal['BL_COMPARISON', 'SI_REQUEST', 'INVOICE_QUERY', 'GENERAL', 'SPAM']
    status: Literal['OK', 'MISMATCH', 'NEEDS_REVIEW']
    review_reason: str | None = None
    has_defect: bool
    defect_fields: list[FieldName]

    @model_validator(mode='after')
    def evaluation_invariants(self) -> Self:
        require(len(self.defect_fields) == len(set(self.defect_fields)), 'duplicate defect fields')
        if self.category != 'BL_COMPARISON':
            require(self.status == 'OK', 'non-comparison evaluation record uses OK sentinel')
        if self.status == 'MISMATCH':
            require(self.category == 'BL_COMPARISON' and self.has_defect and bool(self.defect_fields) and self.review_reason is None, 'invalid mismatch submission')
        else:
            require(not self.has_defect and not self.defect_fields, 'non-mismatch submission cannot claim definitive defects')
            require((self.review_reason is not None) == (self.status == 'NEEDS_REVIEW'), 'review reason/status mismatch')
        return self
```

### 3.2 Required, nullable and absent fields

Every field in the reference block without `= ...` or a default factory is required on the wire. In particular, `category`, normalized `value`, `selected_candidate`, `outcome`, `mismatch_detected`, `partial_result`, `review`, parser `text`, and submission `review_reason` are explicitly present with null when unavailable. Lists are arrays, including empty arrays; required arrays are never null. Optional provider metadata may be omitted or null. Serialization includes explicit nulls for required nullable fields and uses JSON arrays for coordinates.

No candidate is synthesized for a missing attachment. A missing role is represented by a ReviewIssue `expected_role`, not a fake DocumentReference. If a document exists but a field is unreadable, keep that document and its seven-field extraction map, with the affected field unresolved.

## 4. Evidence, parsing and normalization invariants

Evidence is a reference to verifiable source content, not an AI explanation promoted to truth. The source adapter must validate the referenced page/cell/span/region against the preserved source. Page numbers are one-based; cell rows/columns are zero-based; normalized bbox coordinates are `[x0,y0,x1,y1]`. These are structural coordinates, not business thresholds. Do not fabricate a location when the parser does not supply one: a grounded text span without location is allowed.

Document metadata can establish role or path, but cannot alone prove an arbitrary shipment value. Processing errors support failure reasons, not extracted field values. Human review evidence identifies the action and rationale; corrected shipment values must still point to the document or a separately supplied source reference. Merely setting `source_type='document'` does not satisfy source validation.

Provider-output adaptation preserves raw text, attaches only known source references and validates candidates. Invalid model output follows bounded semantic repair; an adapter cannot silently change a candidate to make it validate. Invalid enum, missing keys and non-grounded content remain visible.

Parser usability and field reliability are different. Successful PDF text extraction does not mean all fields exist; partial parsing does not mean no fields are usable. Initial parser failure and later successful OCR are separate ParserResult/AttemptRecord events for the same document. Prior failures remain in the record.

Normalization records the exact rule version and unit interpretation. Unrecognized or ambiguous units/separators produce an invalid or uncertain field, not a guessed conversion. Exact decimal normalization must avoid implicit context rounding; any representation limit produces visible failure rather than an approximate equality decision. No normalization algorithm or alias table is newly approved by this schema.

Service validation additionally checks unique issue IDs, operations and evidence references; actual candidate ambiguity; document-role identification evidence; confidence-independent reliability; text usability; and the rule version used. The reference models do not substitute for these source-dependent checks.

## 5. State and partial-result behavior

| Situation | Audit state | Outcome | mismatch_detected | Required retained work |
|---|---|---|---|---|
| All seven reliable pairs match | COMPLETE | MATCH | false | Seven comparisons and their evidence; exact clean summary |
| All seven reliable, at least one differs | COMPLETE | MISMATCH | true | Seven comparisons; each discrepancy with SI/BL values |
| Any mandatory pair unresolved | NEEDS_REVIEW | null | null | Every reliable pair comparison; confirmed partial discrepancies; unresolved fields and review |
| Resolved non-comparison category | COMPLETE | NOT_APPLICABLE | null | Classification and evidence only; no parser or comparison execution |
| Intent unresolved (DC-01 proposal) | NEEDS_REVIEW | null | null | Message context, classification failure evidence and review; no attachment parsing |

For comparison requests, comparisons and unresolved fields form an exact disjoint partition of seven fields. A field may be reliable on one side and unresolved on the other; preserve that extraction but do not compare the pair. Partial results are not discarded on missing attachments, parsing failures, provider exhaustion, or review transitions.

An audit's `mismatch_detected` is a **final outcome indicator** with tri-state internal behavior (DC-03):
- `true` = resolved mismatch (at least one discrepancy confirmed across 7 reliable pairs)
- `false` = resolved no mismatch (all 7 pairs reliable and match)
- `null` = unresolved / review required (workflow incomplete or non-comparison)

Consumers do not have to infer workflow state solely from `null`: the explicit `state` (`COMPLETE` vs `NEEDS_REVIEW`), `outcome` (`MATCH`, `MISMATCH`, `NOT_APPLICABLE`, or `null`), and `review.state` (`OPEN` vs `RESOLVED`) provide unambiguous workflow observability. `discrepancies` and `partial_result.comparisons` preserve confirmed partial discrepancies explicitly. The UI must not translate null to false. A review state has priority over a complete match/mismatch until all required work is dependable.

`result_summary` for mismatches lists each field and `SI: <value> / BL: <value>`. Review summaries identify unresolved work and may mention confirmed partial discrepancies, but never emit the exact clean result. Non-comparison summaries say that the message was classified and document verification was not applicable.

## 6. Recovery and processing metadata

Each actual stage attempt has an ID, operation ID, kind, ordinal and outcome. Parser/OCR failure events and recovery events are retained independently. Absent provider token/model/latency metadata is null or omitted, never estimated as provider-reported truth.

**Total-attempt limits (DC-06)**:
Remove ambiguous concepts such as "3 retries" or "2 retries". The system defines explicit total-attempt limits:
- `technical_attempt_limit` (default: 3)
- `semantic_attempt_limit` (default: 2)

The attempt limit explicitly includes the initial attempt.
A semantic response cycle includes its initial call and up to `technical_attempt_limit` total attempts. A semantic repair opens the next cycle up to `semantic_attempt_limit` total cycles.
If `technical_attempt_limit = 3` and `semantic_attempt_limit = 2`, the maximum nested provider-call budget is unambiguously 6 (3 × 2).
`attempt_number` is the monotonically increasing actual call ordinal within the operation; `kind` records why the call occurred. These limits are configurable operational defaults, not immutable business rules.

Provider failure becomes a review issue only when applicable attempts and approved fallbacks cannot supply a validated required result. Record why recovery is unavailable, exhausted or unreliable. Validated fallback success allows continuation while preserving earlier failures. No additional provider is approved by the availability of a `fallback` event kind.

## 7. Human review update proposal

The approved capability is human confirmation/correction followed by report update. **DC-07 specifies** `POST /audit/{email_id}/review` with `ReviewUpdate` and optimistic concurrency control (`expected_revision`).

Human reviewers must NOT directly set final mismatch booleans. Corrections must feed back through normalization and deterministic comparison.

The human review contract supports the full operational correction scope (DC-07):
1. **Classification correction**: `category` (one of the 5 canonical categories) + `classification_evidence_ids`.
2. **SI/BL role correction**: `role_corrections` assigning or reassigning source attachments to `SI` or `BL` with evidence and rationale.
3. **Extracted field correction**: `corrections` with `FieldCorrection` supplying source-backed candidate values, evidence IDs, and rationale.
4. **Evidence correction**: `added_evidence` registering newly cited document or message excerpts.

Human review is not prematurely restricted to field values only.

Processing sequence:

1. Resolve the email and open review case; reject a mismatched `review_id` or stale `expected_revision`.
2. Validate all added evidence and correction targets against preserved source context. Reject duplicate corrections for the same document/field, unknown references, and attempted changes to the seven-field set. Preserve original candidate values and evidence.
3. `CONFIRM` records the human assessment but cannot force unresolved fields into reliability. `CORRECT` supplies source-backed candidates, roles, or category information, not `mismatch_detected`, status overrides or pre-normalized answers. A supplied category requires message evidence; a field correction requires source-document evidence and rationale; a role assignment requires document evidence.
4. Re-run applicable deterministic validation, approved normalization, the reliability gate and comparison. No direct Boolean override is accepted. Unresolved work leaves the case OPEN.
5. Emit a new AuditRecord revision linked to the previous revision. Retain review action provenance and original source values in the available revision history. Mark the review RESOLVED only when relevant unresolved work is resolved. No source SI/BL document is overwritten.

Evidence supplied during a correction cannot retroactively erase a contradictory source value. A human selection must explain how the conflicting candidate was adjudicated. If the source itself needs replacement, the replacement must be explicitly identified; the current text-verification API does not silently replace attachments. A general replacement/upload workflow is outside this draft pending its own interface decision.

## 8. REST payload proposal and compatibility

Routes listed as approved retain the architecture's capability. Their richer payloads are proposed, not currently implemented. Do not deploy an incompatible replacement until DC-03 is approved and consumers are accounted for. The `schema_version` below identifies the draft shape; release versioning is a review decision.

| Route | Status | Request | Response | Failure states |
|---|---|---|---|---|
| GET `/health` | Approved route | None | `{"status":"healthy"}` | Liveness only; does not certify model availability or audit accuracy |
| GET `/audit` | Approved route, proposed payload | Optional canonical `category`, Boolean `mismatch_only`, Boolean `hitl_only` | Array of AuditRecord | 422 invalid filter; empty array for no matches |
| GET `/audit/{email_id}` | Approved route, proposed payload | Opaque email ID | AuditRecord | 404 absent record |
| POST `/verify` | Approved route | DynamicVerifyRequest | AuditRecord | 422 malformed/missing/type-invalid request; inability to verify valid content yields NEEDS_REVIEW, not HTTP success with a fabricated match |
| GET `/submission` | Approved route | None | Object keyed by email_id, values SubmissionRecord | 404 no run/output; 409 EXPORT_BLOCKED if run cannot be fully and losslessly exported |
| GET `/docs` | Approved route | None | OpenAPI HTML | Must describe effective approved contract at implementation time |
| POST `/audit/{email_id}/review` | Proposed DC-07 | ReviewUpdate | New AuditRecord revision | 404 missing record; 409 stale revision/case conflict; 422 invalid correction/evidence |

Filters combine with AND. Proposed `mismatch_only` selects confirmed discrepancies, including partial discrepancies in review cases; `hitl_only` selects open review. This filter behavior is a visible compatibility decision under DC-03. Category filters use resolved categories; unresolved intent is accessible through `hitl_only` without inventing a category.

For `/verify`, string inputs may be empty: this is valid request syntax but unavailable document content, so it enters reliability handling. Missing JSON keys are request errors. The service creates explicit synthetic in-memory document references for the submitted SI/BL strings and records their provenance. This endpoint is an explicit comparison operation, not general inbox classification. It must not accept arbitrary server filesystem paths or pretend to support multipart uploads until an upload contract is approved.

All structured errors use ErrorResponse; `retryable` describes a technical retry possibility, not permission to bypass review. Unexpected processing failures are recorded with context; no partial invalid record is emitted as COMPLETE. Proposed 503 is reserved for inability to execute/store a request at the service boundary; valid processed cases requiring review remain normal audit responses.

### 8.1 Compatibility with prior `03` / `01` §9

| Prior contract | Proposed representation | Migration implication |
|---|---|---|
| Top-level `category` with legacy names | `classification.category` with approved handoff names and explicit state | Breaking payload; explicit adapter/version decision required |
| Boolean `mismatch_detected` default false | Required nullable final indicator | Consumers must distinguish unresolved/not-applicable from clean match |
| `hitl_escalation.reason` with four codes | Review issues with rich logical reasons and optional evaluation reason | Do not collapse new causes or lose context |
| Single string `evidence` | Evidence registry and typed source references | Optional legacy display text cannot replace structured evidence |
| Discrepancies only, no field state | Seven-field extraction maps and partial comparisons | Preserves reliable work and unresolved work distinctly |
| Default clean summary | Explicit validated state-dependent summary | Prevents implicit success from missing data |
| No review request model | ReviewUpdate and revision linkage | Proposed advanced capability interface |

Legacy input aliases `new_si_request → new_shipping_instruction` and `general_message → general` are proposed adapter-only mappings; trusted outputs use canonical names. No silent dual-enum acceptance is embedded in the models. An old API response cannot faithfully represent every new state; do not fabricate a lossless adapter. DC-03 offers explicit consumer migration or an approved versioned endpoint strategy, to be selected before implementation.

## 9. Evaluation adapter

SOURCE: The original PDF makes self-evaluation optional and its submission shape external-only. `sample_submission.json` is the verified official evaluation format, establishing the schema structure:
- `category`: uppercase category string (`BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`)
- `status`: uppercase status string (`OK`, `MISMATCH`, `NEEDS_REVIEW`)
- `review_reason`: string or null (template defaults to `null`)
- `defect_fields`: list of mismatched field names
- `has_defect`: boolean indicating whether defects exist

### 9.1 Explicit category adapter mapping

The mapping from internal canonical categories to official evaluation categories is closed and deterministic:

| Internal canonical category | Official evaluation category | Export behavior |
|---|---|---|
| `document_comparison` | `BL_COMPARISON` | Mapped deterministically |
| `new_shipping_instruction` | `SI_REQUEST` | Mapped deterministically |
| `invoice_query` | `INVOICE_QUERY` | Mapped deterministically |
| `general` | `GENERAL` | Mapped deterministically |
| `spam` | `SPAM` | Mapped deterministically |
| `null` (unresolved internal state) | None | **EXPORT_BLOCKED** (no official category mapping exists) |

Any unresolved internal category MUST NOT be mapped to a guessed category; it unconditionally blocks evaluation export.

### 9.2 Verified defect field identifiers (1:1 Mapping)

The official field identifiers permitted in `defect_fields` have been verified directly against `sdoc-hackathon-bundle/README.md` §2, `sample_submission.json`, and `Shipping Document Verification Use Case.pdf` §3. They match the 7 internal canonical field names exactly (1:1 verified mapping):

| Internal canonical field name | Official `defect_fields` identifier | Verified 1:1 match |
|---|---|---|
| `shipper` | `shipper` | Verified exact match |
| `consignee` | `consignee` | Verified exact match |
| `notify_party` | `notify_party` | Verified exact match |
| `port_of_loading` | `port_of_loading` | Verified exact match |
| `port_of_discharge` | `port_of_discharge` | Verified exact match |
| `container_count` | `container_count` | Verified exact match |
| `gross_weight_kg` | `gross_weight_kg` | Verified exact match |

No runtime field name translation or renaming is required, and implementation must never infer or alias field names.

### 9.3 Safe NEEDS_REVIEW export semantics

For records with `status = NEEDS_REVIEW`:
1. Do NOT infer the values of `has_defect` and `defect_fields` from the internal AuditRecord unless the official `sample_submission.json` or `README.md` explicitly defines their semantics.
2. The authoritative `sdoc-hackathon-bundle/README.md` specifies `has_defect` + `defect_fields` *when it's a MISMATCH*, and `review_reason` *when it's NEEDS_REVIEW*. Neither `README.md` nor `sample_submission.json` defines how `has_defect` or `defect_fields` must be represented under `NEEDS_REVIEW`.
3. The Evaluation Adapter MUST NOT invent a value. Specifically:
   - Do NOT silently use `has_defect = false`.
   - Do NOT automatically convert partial known discrepancies into an official final defect declaration unless the official contract explicitly permits that representation.
4. In this situation:
   → **EXPORT_BLOCKED**

Evaluation export is safely allowed ONLY when every record is fully resolved (i.e. `COMPLETE` leading to `OK` or `MISMATCH`), or if an authoritative official schema update explicitly defines how `has_defect` and `defect_fields` must be serialized for `NEEDS_REVIEW`.

### 9.4 Generalized safe export blocking (DC-08)

| Internal state | Submission rule |
|---|---|
| Complete comparison match | `status="OK"`, `has_defect=false`, `defect_fields=[]`, `review_reason=null` |
| Complete comparison mismatch | `status="MISMATCH"`, `has_defect=true`, `defect_fields=[...]` (exactly confirmed mismatched field names), `review_reason=null` |
| Resolved non-comparison | `status="OK"` (eval sentinel), `has_defect=false`, `defect_fields=[]`, `review_reason=null` |
| Record in `NEEDS_REVIEW` | **EXPORT_BLOCKED** (undefined `has_defect`/`defect_fields` official semantics; §9.3) |
| Unresolved category (`category=null`) | **EXPORT_BLOCKED** (unresolved classification; §9.1) |

Evaluation export MUST be blocked (`EXPORT_BLOCKED` / HTTP 409) whenever an unresolved or internal state cannot be truthfully and losslessly represented under the verified official evaluation contract. Never fabricate data merely to make an export possible. Partial internal results remain fully available in audit records.

The evaluation contract loses partial-field details during NEEDS_REVIEW. This loss is confined to export, never applied to the internal report. No official score formula, reference answer, dataset statistic, or empirical accuracy claim is introduced here.

## 10. Examples and document validation

The companion [03_DATA_CONTRACTS_EXAMPLES.json](03_DATA_CONTRACTS_EXAMPLES.json) contains **synthetic complete payloads** validated against the reference models, not evaluation outputs or actual customer documents. Each case contains its model name and payload. Repeated field data is intentional so each audit is independently reviewable.

| Example | Critical assertion |
|---|---|
| complete_match | Seven reliable pairs; exact clean summary |
| complete_mismatch | Only actual unequal canonical fields are discrepancies |
| missing_attachment | Resolved comparison intent; missing role; reliable SI retained |
| unreadable_source | Parser failure and unsuccessful OCR retained; no clean pass |
| conflicting_partial | Known partial mismatch retained alongside conflicting unresolved weight |
| non_comparison | No document processing; NOT_APPLICABLE |
| fallback_success | Earlier provider failure retained; validated fallback permits completion |
| exhausted_recovery | Exhausted configured attempts and unavailable fallback; review with no invented legacy code |
| unresolved_classification | Provisional null category, no parsing, explicit review (DC-01) |
| human_correction_request | Evidence-backed raw correction and expected revision; includes role/field corrections; no Boolean override |
| human_correction_result | New revision, prior conflicting candidates retained, deterministic recomparison |
| evaluation_match / evaluation_mismatch / evaluation_review | External shape only; reason/status/field invariants conforming to `sample_submission.json` |
| blocked_export_error | Explicit unsupported mapping prevents fabricated submission (DC-08) |

Minimal request example:

```json
{"email_id":"example-direct-check","si_text":"Container Count: 3","bl_text":"Container Count: 4"}
```

This request is syntactically valid but not a complete shipment: other mandatory fields are absent, so it must not become a complete mismatch or clean match. It can retain the reliable container difference while requesting review.

Verification of this draft checks model execution, JSON round-tripping, complete synthetic payload validation, invalid-state rejection, and traceability links. This is document/schema checking only; it does not certify current application conformance and does not run or modify the repository's application test suite.

## 11. Decision register and baseline gate

| ID | Choice / Unresolved boundary | Status |
|---|---|---|
| DC-01 | Provisional category null in NEEDS_REVIEW; five categories only when resolved; no parsing before resolution; export rejected until resolved | APPROVED |
| DC-02 | Rich internal HITL reason taxonomy; no invented official taxonomy; export only verified official schema fields | CORRECTED & APPROVED |
| DC-03 | Tri-state mismatch (true/false/null) + explicit workflow state (COMPLETE/NEEDS_REVIEW, OPEN/RESOLVED) | APPROVED |
| DC-04 | Canonical internal Decimal for gross_weight_kg; target-specific serialization; strict integer container count | APPROVED WITH MODIFICATION |
| DC-05 | Structured source-grounded evidence; no fabricated coordinates, OCR regions, or metadata | APPROVED |
| DC-06 | Explicit total-attempt limits (technical_attempt_limit, semantic_attempt_limit) including initial attempt (max budget = tech × sem = 6) | APPROVED WITH MODIFICATION |
| DC-07 | Review scope covers classification, SI/BL roles, field extraction, and evidence; feeds back through deterministic comparison | APPROVED WITH MODIFICATION |
| DC-08 | Generalized safe export blocking (EXPORT_BLOCKED) whenever internal state cannot be truthfully and losslessly exported | APPROVED WITH MODIFICATION |
| DEC-P06C | Port semantic equivalence mapping | TBD, unchanged |
| DEC-P06D | Organization semantic alias rules | TBD, unchanged |
| DEC-P06E | Business numeric tolerance | TBD, unchanged; exact normalized comparison remains approved default |

Baseline gate: Human reviewer completed decision review on 2026-09-22 (approving DC-01, DC-03, DC-05, DC-07; approving with modifications DC-04, DC-06, DC-08; correcting DC-02). All models, constraints, and synthetic examples have been updated and validated. Status is **APPROVED / BASELINED** (Revision 2.0-baselined). Next stage is `04_UI_UX_SPEC.md`, followed by `05_TEST_PLAN.md` and `06_TASKS.md`.

## 12. Traceability

| Source / approved decision | Contract sections |
|---|---|
| PDF p.1; `00` FR-001–004 / EC-001–003 | EmailRecord, ClassificationResult, §§5/9 |
| PDF p.1–2; `00` FR-009–012; `01` DEC-01 | ExtractedField, NormalizedField, FieldComparison, §§4–5 |
| `00` FR-006A/B/C; `02` §§6–7 | DocumentReference, ParserResult, evidence and recovery metadata |
| `00` HL-001–005; `02` §§12–13 | PartialResult, ReviewCase, §§4–7 |
| `02` §§14–16 / DEC-AI-P01/P02 | AttemptRecord, ProcessingMetadata, provider boundary, §6 |
| `02` DEC-AI-P03/P04/P05 | Ownership boundaries, reliability gate, typed source evidence |
| PDF p.2 human correction; `02` §13.3 | ReviewUpdate and proposed review lifecycle §7 |
| `01` §8 / DEC-P03 | REST contracts and compatibility §8 |
| PDF p.4; `00` NFR-005 / HL-002 | SubmissionRecord and evaluation adapter §9 |
| `01` DEC-P06C/D/E | Normalization restrictions §§2/4 and preserved TBDs §11 |
