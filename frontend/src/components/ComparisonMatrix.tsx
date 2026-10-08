import type { AuditRecord, FieldEvidence } from '../types/api';
import {
  FIELD_NAMES,
  fieldEvidence,
  fieldExtraction,
  fieldOutcome,
  normalizedValue,
  selectedRawValue,
  type FieldName,
} from '../utils';

interface Props {
  record: AuditRecord;
  onEvidence: (field: FieldName, evidence: FieldEvidence[]) => void;
}

function OutcomeChip({ outcome }: { outcome: 'MATCH' | 'MISMATCH' | 'UNRESOLVED' }) {
  if (outcome === 'MATCH') {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400 shadow-[0_0_12px_-2px_rgba(16,185,129,0.3)]">
        <span>✓</span>
        <span>EXACT MATCH</span>
      </div>
    );
  }
  if (outcome === 'MISMATCH') {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-400 shadow-[0_0_12px_-2px_rgba(244,63,94,0.3)]">
        <span>⚠</span>
        <span>MISMATCH</span>
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 shadow-[0_0_12px_-2px_rgba(245,158,11,0.3)]">
      <span>◷</span>
      <span>UNRESOLVED</span>
    </div>
  );
}

function ValueCell({
  record,
  role,
  field,
}: {
  record: AuditRecord;
  role: 'SI' | 'BL';
  field: FieldName;
}) {
  const extraction = fieldExtraction(record, role, field);
  const value = normalizedValue(extraction);
  const raw = selectedRawValue(extraction);
  const missing = value === '[Not Found in Document]';
  return (
    <div className="space-y-1">
      <div
        className={
          missing
            ? 'font-mono text-xs font-semibold text-amber-300'
            : 'font-semibold text-slate-100'
        }
      >
        {value}
      </div>
      <div className="font-mono text-xs text-slate-500">
        raw: <span className="text-slate-400">{raw ?? '—'}</span>
      </div>
      {extraction ? (
        <div className="inline-flex items-center gap-1.5 font-mono text-[11px] text-slate-500">
          <span className="h-1 w-1 rounded-full bg-slate-500" />
          <span>{extraction.reliability}</span>
        </div>
      ) : null}
    </div>
  );
}

export function ComparisonMatrix({ record, onEvidence }: Props) {
  return (
    <div className="glass-panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-white/[0.06] bg-carbon-950/80 font-mono text-xs uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-5 py-4 w-1/6">
                <span className="text-slate-400">Field</span>
              </th>
              <th className="px-5 py-4 w-1/3 border-l border-white/[0.04]">
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono tracking-widest text-blue-400 uppercase">
                    Left Wing Axis
                  </span>
                  <span className="font-semibold text-slate-200">
                    Shipping Instruction (SI)
                  </span>
                </div>
              </th>
              <th className="px-5 py-4 w-1/3 border-l border-white/[0.04]">
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono tracking-widest text-blue-400 uppercase">
                    Right Wing Axis
                  </span>
                  <span className="font-semibold text-slate-200">
                    Draft Bill of Lading (BL)
                  </span>
                </div>
              </th>
              <th className="px-5 py-4 w-1/4 border-l border-white/[0.04]">
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono tracking-widest text-blue-400 uppercase">
                    Verification Axis
                  </span>
                  <span className="font-semibold text-slate-200">
                    Outcome / Result
                  </span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {FIELD_NAMES.map((field) => {
              const outcome = fieldOutcome(record, field);
              const evidence = fieldEvidence(record, field);
              const discrepancy = record.discrepancies.find((item) => item.field === field);
              return (
                <tr
                  key={field}
                  data-testid={`comparison-row-${field}`}
                  className={`group spotlight-border transition-colors duration-150 ${
                    outcome === 'MISMATCH'
                      ? 'bg-rose-950/15 hover:bg-rose-950/25'
                      : outcome === 'UNRESOLVED'
                      ? 'bg-amber-950/10 hover:bg-amber-950/20'
                      : 'hover:bg-carbon-800/40'
                  }`}
                >
                  <td className="px-5 py-4 font-mono text-xs font-semibold text-blue-300">
                    {field}
                  </td>
                  <td className="px-5 py-4 border-l border-white/[0.04]">
                    <ValueCell record={record} role="SI" field={field} />
                  </td>
                  <td className="px-5 py-4 border-l border-white/[0.04]">
                    <ValueCell record={record} role="BL" field={field} />
                  </td>
                  <td className="px-5 py-4 border-l border-white/[0.04]">
                    <div className="flex flex-col items-start gap-2">
                      <OutcomeChip outcome={outcome} />
                      {discrepancy ? (
                        <div className="rounded-lg border border-rose-500/20 bg-rose-950/30 p-2 font-mono text-xs text-rose-300">
                          <div className="text-[10px] uppercase tracking-wider text-rose-400/80">
                            ⚠ Discrepancy
                          </div>
                          <div className="mt-0.5">
                            SI: <span className="text-white">{String(discrepancy.si_value)}</span> · BL:{' '}
                            <span className="text-white">{String(discrepancy.bl_value)}</span>
                          </div>
                        </div>
                      ) : null}
                      {outcome === 'UNRESOLVED' ? (
                        <div className="text-xs text-amber-300/90">
                          A required value is missing or not reliable.
                        </div>
                      ) : null}
                      <button
                        className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-600/10 px-2.5 py-1 text-xs font-semibold text-blue-400 transition hover:bg-blue-600/20 hover:text-blue-300"
                        onClick={() => onEvidence(field, evidence)}
                      >
                        <span>Evidence Trace</span>
                        <span className="font-mono text-[11px] text-blue-300">
                          ({evidence.length})
                        </span>
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
