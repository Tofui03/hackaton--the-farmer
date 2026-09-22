import type { AuditRecord, ExtractedField } from '../types/api';
import { FIELD_NAMES, type FieldName } from '../utils';

function extracted(field: FieldName, value: string | number, evidenceId: string): ExtractedField {
  return {
    field,
    reliability: 'RELIABLE',
    candidates: [{ raw_value: String(value), evidence_ids: [evidenceId] }],
    selected_candidate: 0,
    normalized: { field, state: 'VALID', value, rule_version: 'norm-v1.0' },
    explanation: 'Synthetic frontend test value',
  };
}

export function makeAuditRecord(overrides: Partial<AuditRecord> = {}): AuditRecord {
  const evidence = FIELD_NAMES.flatMap((field) => [
    { evidence_id: `ev-si-${field}`, source_type: 'document' as const, source_id: 'si.txt', kind: 'text_span' as const, quote: `${field}: value` },
    { evidence_id: `ev-bl-${field}`, source_type: 'document' as const, source_id: 'bl.txt', kind: 'text_span' as const, quote: `${field}: value` },
  ]);
  const siFields = Object.fromEntries(FIELD_NAMES.map((field, index) => [field, extracted(field, field === 'container_count' ? 2 : `VALUE-${index}`, `ev-si-${field}`)]));
  const blFields = Object.fromEntries(FIELD_NAMES.map((field, index) => [field, extracted(field, field === 'container_count' ? 2 : `VALUE-${index}`, `ev-bl-${field}`)]));
  const comparisons = FIELD_NAMES.map((field, index) => ({
    field,
    si_value: field === 'container_count' ? 2 : `VALUE-${index}`,
    bl_value: field === 'container_count' ? 2 : `VALUE-${index}`,
    outcome: 'MATCH' as const,
    rule_version: 'norm-v1.0',
  }));

  const base: AuditRecord = {
    schema_version: '1.0-draft',
    email_id: 'email-test-001',
    revision: 1,
    previous_revision: null,
    email: {
      email_id: 'email-test-001',
      sender: 'ops@example.com',
      subject: 'Compare SI and draft BL',
      body: 'Please compare the shipping documents.',
      attachments: [
        { document_id: 'si.txt', path: 'si.txt', mime_type: 'text/plain' },
        { document_id: 'bl.txt', path: 'bl.txt', mime_type: 'text/plain' },
      ],
    },
    classification: { state: 'RESOLVED', category: 'document_comparison', reason: 'Explicit comparison request', evidence_ids: ['ev-email'] },
    state: 'COMPLETE',
    outcome: 'MATCH',
    mismatch_detected: false,
    result_summary: 'No mismatch detected',
    documents: [
      { document_id: 'si.txt', role: 'SI', identification_evidence_ids: ['ev-si-shipper'] },
      { document_id: 'bl.txt', role: 'BL', identification_evidence_ids: ['ev-bl-shipper'] },
    ],
    parsers: [
      { document_id: 'si.txt', status: 'SUCCESS', text: 'text', usable_for_extraction: true, diagnostic_evidence_ids: [], attempt_ids: [], is_scanned: false },
      { document_id: 'bl.txt', status: 'SUCCESS', text: 'text', usable_for_extraction: true, diagnostic_evidence_ids: [], attempt_ids: [], is_scanned: false },
    ],
    extractions: [
      { document_id: 'si.txt', role: 'SI', fields: siFields },
      { document_id: 'bl.txt', role: 'BL', fields: blFields },
    ],
    evidence: [{ evidence_id: 'ev-email', source_type: 'email', source_id: 'email-test-001', kind: 'text_span', quote: 'compare' }, ...evidence],
    partial_result: { comparisons, unresolved_fields: [] },
    discrepancies: [],
    review: null,
    processing: { technical_attempt_limit: 3, semantic_attempt_limit: 2, attempts: [] },
  };
  return { ...base, ...overrides };
}

export function makeReviewRecord(): AuditRecord {
  const record = makeAuditRecord();
  const missingField = record.extractions.find((item) => item.role === 'BL')!.fields.gross_weight_kg;
  missingField.reliability = 'MISSING';
  missingField.normalized = null;
  missingField.selected_candidate = null;
  record.partial_result = {
    comparisons: record.partial_result!.comparisons.filter((item) => item.field !== 'gross_weight_kg'),
    unresolved_fields: ['gross_weight_kg'],
  };
  record.state = 'NEEDS_REVIEW';
  record.outcome = null;
  record.mismatch_detected = null;
  record.result_summary = 'Gross weight requires human review';
  record.review = {
    review_id: 'review-email-test-001',
    state: 'OPEN',
    issues: [{
      issue_id: 'issue-weight',
      stage: 'extraction',
      logical_reason: 'conflicting_candidate_values',
      document_ids: ['bl.txt'],
      expected_role: 'BL',
      fields: ['gross_weight_kg'],
      evidence_ids: ['ev-bl-gross_weight_kg'],
      suggested_action: 'Select the authoritative gross weight value.',
      recovery_state: 'UNRELIABLE',
      recovery_detail: 'Two source readings conflict.',
      attempt_ids: [],
    }],
  };
  return record;
}
