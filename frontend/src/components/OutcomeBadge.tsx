import type { AuditRecord } from '../types/api';
import { StatusBadge } from './StatusBadge';

export function OutcomeBadge({ record }: { record: AuditRecord }) {
  if (record.state === 'NEEDS_REVIEW') return <StatusBadge label="NEEDS REVIEW" tone="amber" icon="◷" />;
  if (record.outcome === 'MISMATCH') return <StatusBadge label="MISMATCH" tone="rose" icon="⚠" />;
  if (record.outcome === 'MATCH') return <StatusBadge label="MATCH OK" tone="green" icon="✓" />;
  return <StatusBadge label="NON-COMPARISON" tone="slate" icon="—" />;
}
