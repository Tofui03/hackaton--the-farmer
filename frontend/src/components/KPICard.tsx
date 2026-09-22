interface Props {
  label: string;
  value: number;
  hint: string;
}

export function KPICard({ label, value, hint }: Props) {
  return (
    <div className="panel p-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-bold text-white">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{hint}</div>
    </div>
  );
}
