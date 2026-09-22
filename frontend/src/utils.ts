import type { AuditRecord, ExtractedField, FieldEvidence } from './types/api';

export const FIELD_NAMES = [
  'shipper',
  'consignee',
  'notify_party',
  'port_of_loading',
  'port_of_discharge',
  'container_count',
  'gross_weight_kg',
] as const;

export type FieldName = (typeof FIELD_NAMES)[number];

export const CATEGORY_OPTIONS = [
  'document_comparison',
  'new_shipping_instruction',
  'invoice_query',
  'general',
  'spam',
] as const;

export const REVIEW_REASON_LABELS: Record<string, string> = {
  conflicting_candidate_values: 'Conflicting values found',
  wrong_or_uncertain_document_type: 'Document type needs confirmation',
  missing_attachment: 'Required document missing',
  unreadable_document: 'Document content unreadable',
  missing_required_value: 'Required field value missing',
  uncertain_result: 'Result uncertain / Ambiguous intent',
  processing_or_provider_failure: 'System processing error',
};

export function humanizeReason(value: string): string {
  return REVIEW_REASON_LABELS[value] ?? value.replaceAll('_', ' ');
}

export function fieldExtraction(record: AuditRecord, role: 'SI' | 'BL', field: FieldName): ExtractedField | null {
  const extraction = record.extractions.find((item) => item.role === role);
  return extraction?.fields[field] ?? null;
}

export function selectedRawValue(field: ExtractedField | null): string | null {
  if (!field || field.selected_candidate == null) return null;
  return field.candidates[field.selected_candidate]?.raw_value ?? null;
}

export function normalizedValue(field: ExtractedField | null): string {
  const value = field?.normalized?.value;
  if (value === null || value === undefined || field?.reliability !== 'RELIABLE') {
    return '[Not Found in Document]';
  }
  return String(value);
}

export function fieldEvidence(record: AuditRecord, field: FieldName): FieldEvidence[] {
  const ids = new Set<string>();
  for (const role of ['SI', 'BL'] as const) {
    const extraction = fieldExtraction(record, role, field);
    extraction?.candidates.forEach((candidate) => candidate.evidence_ids.forEach((id) => ids.add(id)));
  }
  return record.evidence.filter((evidence) => ids.has(evidence.evidence_id));
}

export function fieldOutcome(record: AuditRecord, field: FieldName): 'MATCH' | 'MISMATCH' | 'UNRESOLVED' {
  const comparison = record.partial_result?.comparisons.find((item) => item.field === field);
  if (comparison) return comparison.outcome;
  if (record.discrepancies.some((item) => item.field === field)) return 'MISMATCH';
  return 'UNRESOLVED';
}

export function outcomeLabel(record: AuditRecord): string {
  if (record.state === 'NEEDS_REVIEW') return 'NEEDS REVIEW';
  if (record.outcome === 'MATCH') return 'MATCH OK';
  if (record.outcome === 'MISMATCH') return 'MISMATCH';
  return 'NON-COMPARISON';
}
