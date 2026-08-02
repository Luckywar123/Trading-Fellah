export default function StatCard({ label, value, sub, tone = 'neutral' }) {
  const toneColor = {
    neutral: 'text-ink',
    positive: 'text-long',
    negative: 'text-short',
    amber: 'text-amber',
  }[tone]

  return (
    <div className="panel p-4">
      <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono">{label}</div>
      <div className={`mt-1.5 text-2xl font-mono font-semibold ${toneColor} font-tabular`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-ink-faint font-mono">{sub}</div>}
    </div>
  )
}
