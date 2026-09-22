import { useRef, useState } from 'react'
import { money, shortDate } from '../format'

interface Props {
  points: [string, number][]
  peakDay?: string
}

const W = 560
const H = 200
const PAD = { top: 16, right: 16, bottom: 26, left: 44 }

export function PriceChart({ points, peakDay }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  const [asTable, setAsTable] = useState(false)
  const svgRef = useRef<SVGSVGElement>(null)
  if (points.length < 2) return <p className="muted">Not enough price history yet.</p>

  const prices = points.map(p => p[1])
  const max = Math.max(...prices) * 1.08
  const min = 0
  const iw = W - PAD.left - PAD.right
  const ih = H - PAD.top - PAD.bottom
  const x = (i: number) => PAD.left + (i / (points.length - 1)) * iw
  const y = (p: number) => PAD.top + ih - ((p - min) / (max - min)) * ih
  const line = prices.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join('')
  const ticks = [0, 0.5, 1].map(t => min + t * (max - min))
  const peakIdx = points.findIndex(p => p[0] === peakDay)
  const xTicks = [0, Math.floor((points.length - 1) / 2), points.length - 1]

  const onMove = (e: React.PointerEvent) => {
    const rect = svgRef.current!.getBoundingClientRect()
    const px = ((e.clientX - rect.left) / rect.width) * W
    const i = Math.round(((px - PAD.left) / iw) * (points.length - 1))
    setHover(Math.max(0, Math.min(points.length - 1, i)))
  }

  return (
    <div className="chart">
      <div className="chart-head">
        <h3>Price history <span className="muted">TCGplayer market, non-foil</span></h3>
        <button className="link-btn" onClick={() => setAsTable(t => !t)}>{asTable ? 'Chart' : 'Table'}</button>
      </div>
      {asTable ? (
        <div className="price-table">
          <table>
            <thead><tr><th>Date</th><th>Price</th></tr></thead>
            <tbody>
              {[...points].reverse().map(([d, p]) => <tr key={d}><td>{shortDate(d)}</td><td>{money(p)}</td></tr>)}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="chart-svg"
               onPointerMove={onMove} onPointerLeave={() => setHover(null)}
               role="img" aria-label={`Price from ${money(prices[0])} to ${money(prices[prices.length - 1])}`}>
            <defs>
              <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--series-1)" stopOpacity="0.35" />
                <stop offset="100%" stopColor="var(--series-1)" stopOpacity="0" />
              </linearGradient>
            </defs>
            {ticks.map(t => (
              <g key={t}>
                <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="gridline" />
                <text x={PAD.left - 8} y={y(t) + 4} className="axis" textAnchor="end">{money(t)}</text>
              </g>
            ))}
            {xTicks.map((i, k) => (
              <text key={i} x={x(i)} y={H - 6} className="axis"
                    textAnchor={k === 0 ? 'start' : k === 2 ? 'end' : 'middle'}>{shortDate(points[i][0])}</text>
            ))}
            <path d={`${line}L${x(points.length - 1)},${y(0)}L${x(0)},${y(0)}Z`} fill="url(#areaFill)" />
            <path d={line} className="chart-line" />
            {peakIdx >= 0 && hover === null && (
              <g>
                <circle cx={x(peakIdx)} cy={y(prices[peakIdx])} r={4} className="chart-dot" />
                <text x={x(peakIdx) + 8} y={y(prices[peakIdx]) + 4} className="axis strong">peak {money(prices[peakIdx])}</text>
              </g>
            )}
            {hover !== null && (
              <g>
                <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + ih} className="crosshair" />
                <circle cx={x(hover)} cy={y(prices[hover])} r={5} className="chart-dot" />
              </g>
            )}
          </svg>
          {hover !== null && (
            <div className="tooltip" style={{ left: `${(x(hover) / W) * 100}%`, top: `${(y(prices[hover]) / H) * 100}%` }}>
              <strong>{money(prices[hover])}</strong>
              <span>{shortDate(points[hover][0])}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
