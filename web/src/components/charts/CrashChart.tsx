import { useRef, useState } from 'react'
import type { CrashPoint } from '../../statsTypes'
import { shortDate } from '../../format'

const W = 720
const H = 260
const PAD = { top: 16, right: 20, bottom: 30, left: 44 }

/** Median % of peak with the middle-half band, by day. One series, so no legend: the title names it. */
export function CrashChart({ series }: { series: CrashPoint[] }) {
  const [hover, setHover] = useState<number | null>(null)
  const ref = useRef<SVGSVGElement>(null)
  const iw = W - PAD.left - PAD.right
  const ih = H - PAD.top - PAD.bottom
  const x = (i: number) => PAD.left + (i / (series.length - 1)) * iw
  const y = (v: number) => PAD.top + ih - (v / 100) * ih
  const line = series.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.median).toFixed(1)}`).join('')
  const band = series.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.p75).toFixed(1)}`).join('')
    + [...series].reverse().map((p, k) => `L${x(series.length - 1 - k).toFixed(1)},${y(p.p25).toFixed(1)}`).join('') + 'Z'
  const releaseIdx = series.findIndex(p => p.since_release >= 0)
  const last = series[series.length - 1]
  const xTicks = [0, releaseIdx, series.length - 1].filter(i => i >= 0)

  const onMove = (e: React.PointerEvent) => {
    const r = ref.current!.getBoundingClientRect()
    const i = Math.round((((e.clientX - r.left) / r.width) * W - PAD.left) / iw * (series.length - 1))
    setHover(Math.max(0, Math.min(series.length - 1, i)))
  }
  const h = hover !== null ? series[hover] : null

  return (
    <div className="chart-wrap">
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} className="chart-svg" onPointerMove={onMove} onPointerLeave={() => setHover(null)}
           role="img" aria-label={`Median Hobbit rare fell to ${last.median}% of its peak price`}>
        {[0, 25, 50, 75, 100].map(t => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="gridline" />
            <text x={PAD.left - 8} y={y(t) + 4} className="axis" textAnchor="end">{t}%</text>
          </g>
        ))}
        {xTicks.map((i, k) => (
          <text key={i} x={x(i)} y={H - 8} className="axis" textAnchor={k === 0 ? 'start' : k === xTicks.length - 1 ? 'end' : 'middle'}>
            {i === releaseIdx ? 'Release' : shortDate(series[i].day)}
          </text>
        ))}
        {releaseIdx > 0 && <line x1={x(releaseIdx)} x2={x(releaseIdx)} y1={PAD.top} y2={PAD.top + ih} className="release-line" />}
        <path d={band} className="band" />
        <path d={line} className="chart-line" />
        <circle cx={x(series.length - 1)} cy={y(last.median)} r={4} className="chart-dot" />
        <text x={x(series.length - 1) - 8} y={y(last.median) - 10} className="axis strong" textAnchor="end">{last.median}% of peak</text>
        {h && hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + ih} className="crosshair" />
            <circle cx={x(hover)} cy={y(h.median)} r={5} className="chart-dot" />
          </g>
        )}
      </svg>
      {h && hover !== null && (
        <div className="tooltip" style={{ left: `${(x(hover) / W) * 100}%`, top: `${(y(h.median) / H) * 100}%` }}>
          <strong>{h.median}% of peak</strong>
          <span>{shortDate(h.day)} · {h.since_release >= 0 ? `${h.since_release}d after release` : `${-h.since_release}d before`}</span>
          <span className="muted">middle half: {h.p25}–{h.p75}%</span>
        </div>
      )}
    </div>
  )
}
