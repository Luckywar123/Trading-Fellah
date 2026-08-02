import { useMemo } from 'react'

const START_ANGLE = -135
const END_ANGLE = 135
const SPAN = END_ANGLE - START_ANGLE

function polar(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function arcPath(cx, cy, r, a0, a1) {
  const p0 = polar(cx, cy, r, a0)
  const p1 = polar(cx, cy, r, a1)
  const largeArc = a1 - a0 > 180 ? 1 : 0
  return `M ${p0.x} ${p0.y} A ${r} ${r} 0 ${largeArc} 1 ${p1.x} ${p1.y}`
}

/**
 * Dial "scope reticle" — dipakai buat nampilin margin utilization (%
 * free margin yang lagi kepakai) relatif ke ceiling yang user set sendiri
 * di Risk Settings. Tick besar tiap 25%, tick kecil tiap 5%, dan ada
 * marker terpisah nunjukin posisi ceiling (bukan cuma dekorasi — itu
 * data asli dari risk_settings.max_margin_pct_per_trade).
 */
export default function RiskGauge({ valuePct = 0, ceilingPct = 100, label = 'MARGIN USE', size = 220 }) {
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.38
  const clamped = Math.max(0, Math.min(100, valuePct))
  const valueAngle = START_ANGLE + (clamped / 100) * SPAN
  const ceilingAngle = START_ANGLE + (Math.max(0, Math.min(100, ceilingPct)) / 100) * SPAN

  const danger = clamped >= ceilingPct * 0.9
  const arcColor = danger ? '#F2545B' : '#F0A030'

  const ticks = useMemo(() => {
    const items = []
    for (let v = 0; v <= 100; v += 5) {
      const major = v % 25 === 0
      const a = START_ANGLE + (v / 100) * SPAN
      const inner = r - (major ? 12 : 6)
      const p0 = polar(cx, cy, r, a)
      const p1 = polar(cx, cy, inner, a)
      items.push(
        <line
          key={v}
          x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y}
          stroke={major ? '#5A6166' : '#2A3035'}
          strokeWidth={major ? 2 : 1}
        />,
      )
    }
    return items
  }, [cx, cy, r])

  const needleTip = polar(cx, cy, r - 18, valueAngle)
  const ceilingTip = polar(cx, cy, r + 6, ceilingAngle)
  const ceilingBase = polar(cx, cy, r - 4, ceilingAngle)

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${label} ${clamped}%`}>
      {/* base ring */}
      <path d={arcPath(cx, cy, r, START_ANGLE, END_ANGLE)} fill="none" stroke="#2A3035" strokeWidth={3} strokeLinecap="round" />
      {/* filled value arc */}
      <path d={arcPath(cx, cy, r, START_ANGLE, valueAngle)} fill="none" stroke={arcColor} strokeWidth={3} strokeLinecap="round" />
      {ticks}
      {/* ceiling marker (user's configured cap) */}
      <line x1={ceilingBase.x} y1={ceilingBase.y} x2={ceilingTip.x} y2={ceilingTip.y} stroke="#F2545B" strokeWidth={2} />
      {/* crosshair needle */}
      <line x1={cx} y1={cy} x2={needleTip.x} y2={needleTip.y} stroke="#E8E6E1" strokeWidth={1.5} />
      <circle cx={cx} cy={cy} r={3} fill="#E8E6E1" />
      {/* reticle crosshair ticks at center, purely signature/brand flourish, kept tiny */}
      <line x1={cx - 5} y1={cy} x2={cx + 5} y2={cy} stroke="#5A6166" strokeWidth={1} opacity={0.5} />
      <line x1={cx} y1={cy - 5} x2={cx} y2={cy + 5} stroke="#5A6166" strokeWidth={1} opacity={0.5} />

      <text x={cx} y={cy + r * 0.55} textAnchor="middle" fill="#E8E6E1" fontSize={size * 0.14}
            fontFamily="'IBM Plex Mono', monospace" fontWeight={600}>
        {clamped.toFixed(0)}%
      </text>
      <text x={cx} y={cy + r * 0.55 + size * 0.08} textAnchor="middle" fill="#8A8F93" fontSize={size * 0.05}
            fontFamily="'IBM Plex Mono', monospace" letterSpacing="0.15em">
        {label}
      </text>
    </svg>
  )
}
