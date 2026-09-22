interface Props {
  label: string;
  tone?: 'green' | 'rose' | 'amber' | 'slate' | 'blue';
  icon?: string;
}

const toneClasses = {
  green: 'border-emerald-700 bg-emerald-950 text-emerald-300',
  rose: 'border-rose-700 bg-rose-950 text-rose-300',
  amber: 'border-amber-700 bg-amber-950 text-amber-300',
  slate: 'border-slate-700 bg-slate-800 text-slate-300',
  blue: 'border-blue-700 bg-blue-950 text-blue-300',
};

export function StatusBadge({ label, tone = 'slate', icon }: Props) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-semibold ${toneClasses[tone]}`}>
      {icon ? <span aria-hidden="true">{icon}</span> : null}
      <span>{label}</span>
    </span>
  );
}
