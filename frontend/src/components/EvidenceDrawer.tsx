import { useEffect } from 'react';
import type { FieldEvidence } from '../types/api';

interface Props {
  open: boolean;
  field: string | null;
  evidence: FieldEvidence[];
  onClose: () => void;
}

function locationText(item: FieldEvidence): string {
  const loc = item.location;
  if (!loc) return 'No structural coordinates supplied by source';
  const parts: string[] = [];
  if (loc.page != null) parts.push(`page ${loc.page}`);
  if (loc.table != null) parts.push(`table ${loc.table}`);
  if (loc.row != null) parts.push(`row ${loc.row}`);
  if (loc.column != null) parts.push(`column ${loc.column}`);
  if (loc.section) parts.push(`section ${loc.section}`);
  if (loc.bbox) parts.push(`bbox [${loc.bbox.join(', ')}]`);
  return parts.length ? parts.join(' · ') : 'No structural coordinates supplied by source';
}

export function EvidenceDrawer({ open, field, evidence, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Source evidence inspector">
      <button className="absolute inset-0 bg-black/60" aria-label="Close evidence drawer" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-xl overflow-y-auto border-l border-slate-700 bg-slate-950 p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-blue-400">Source Evidence</div>
            <h2 className="mt-1 text-xl font-bold text-white">{field ?? 'Evidence'}</h2>
          </div>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
        <div className="mt-6 space-y-3">
          {evidence.length === 0 ? (
            <div className="panel p-4 text-sm text-slate-400">No grounded evidence is available for this field.</div>
          ) : evidence.map((item) => (
            <article key={item.evidence_id} className="panel p-4">
              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="font-mono text-blue-300">{item.evidence_id}</span>
                <span>{item.kind}</span>
                <span>{item.source_id}</span>
              </div>
              {item.quote ? <blockquote className="mt-3 border-l-2 border-blue-500 pl-3 text-sm text-slate-200">“{item.quote}”</blockquote> : null}
              <div className="mt-3 text-xs text-slate-500">{locationText(item)}</div>
              {item.detail ? <div className="mt-2 text-sm text-slate-300">{item.detail}</div> : null}
            </article>
          ))}
        </div>
      </aside>
    </div>
  );
}
