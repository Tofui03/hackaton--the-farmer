import type { AuditRecord, FieldEvidence } from '../types/api';
import { FIELD_NAMES, fieldEvidence, fieldExtraction, fieldOutcome, normalizedValue, selectedRawValue, type FieldName } from '../utils';
import { StatusBadge } from './StatusBadge';

interface Props {
  record: AuditRecord;
  onEvidence: (field: FieldName, evidence: FieldEvidence[]) => void;
}

function outcomeBadge(outcome: 'MATCH' | 'MISMATCH' | 'UNRESOLVED') {
  if (outcome === 'MATCH') return <StatusBadge label="MATCH" tone="green" icon="✓" />;
  if (outcome === 'MISMATCH') return <StatusBadge label="MISMATCH" tone="rose" icon="⚠" />;
  return <StatusBadge label="UNRESOLVED" tone="amber" icon="◷" />;
}

function ValueCell({ record, role, field }: { record: AuditRecord; role: 'SI' | 'BL'; field: FieldName }) {
  const extraction = fieldExtraction(record, role, field);
  const value = normalizedValue(extraction);
  const raw = selectedRawValue(extraction);
  const missing = value === '[Not Found in Document]';
  return (
    <div>
      <div className={missing ? 'font-medium text-amber-300' : 'font-semibold text-slate-100'}>{value}</div>
      <div className="mt-1 text-xs text-slate-500">raw: {raw ?? '—'}</div>
      {extraction ? <div className="mt-1 text-[11px] text-slate-600">{extraction.reliability}</div> : null}
    </div>
  );
}

export function ComparisonMatrix({ record, onEvidence }: Props) {
  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-800 bg-slate-950/80 text-xs uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-4 py-3">Field</th>
              <th className="px-4 py-3">Shipping Instruction (SI)</th>
              <th className="px-4 py-3">Draft Bill of Lading (BL)</th>
              <th className="px-4 py-3">Outcome / Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {FIELD_NAMES.map((field) => {
              const outcome = fieldOutcome(record, field);
              const evidence = fieldEvidence(record, field);
              const discrepancy = record.discrepancies.find((item) => item.field === field);
              return (
                <tr key={field} data-testid={`comparison-row-${field}`} className={outcome === 'MISMATCH' ? 'bg-rose-950/15' : outcome === 'UNRESOLVED' ? 'bg-amber-950/10' : ''}>
                  <td className="px-4 py-4 font-mono text-xs font-semibold text-blue-200">{field}</td>
                  <td className="px-4 py-4"><ValueCell record={record} role="SI" field={field} /></td>
                  <td className="px-4 py-4"><ValueCell record={record} role="BL" field={field} /></td>
                  <td className="px-4 py-4">
                    <div className="flex flex-col items-start gap-2">
                      {outcomeBadge(outcome)}
                      {discrepancy ? (
                        <div className="text-xs text-rose-300">SI: {String(discrepancy.si_value)} · BL: {String(discrepancy.bl_value)}</div>
                      ) : null}
                      {outcome === 'UNRESOLVED' ? <div className="text-xs text-amber-300">A required value is missing or not reliable.</div> : null}
                      <button className="text-xs font-semibold text-blue-400 hover:text-blue-300" onClick={() => onEvidence(field, evidence)}>
                        View Evidence ({evidence.length})
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
