interface Props {
  points: [string, number][]
  width?: number
  height?: number
}

export function Sparkline({ points, width = 120, height = 34 }: Props) {
  if (points.length < 2) return null
  const prices = points.map(p => p[1])
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const span = max - min || 1
  const x = (i: number) => (i / (points.length - 1)) * (width - 4) + 2
  const y = (p: number) => height - 3 - ((p - min) / span) * (height - 6)
  const d = prices.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join('')
  const last = prices.length - 1
  return (
    <svg className="spark" viewBox={`0 0 ${width} ${height}`} width={width} height={height} aria-hidden="true">
      <path d={`${d}L${x(last)},${height}L${x(0)},${height}Z`} className="spark-area" />
      <path d={d} className="spark-line" />
      <circle cx={x(last)} cy={y(prices[last])} r={3} className="spark-dot" />
    </svg>
  )
}
