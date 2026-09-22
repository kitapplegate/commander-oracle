import { motion } from 'motion/react'
import { useState } from 'react'

export interface Column {
  label: string
  value: number
  sub: string
  detail: string
}

interface Props {
  columns: Column[]
  format: (v: number) => string
  baseline?: { value: number; label: string }
  ariaLabel: string
}

const H = 220

/** Ordered columns on one sequential ramp: darker = higher bucket. */
export function ColumnChart({ columns, format, baseline, ariaLabel }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  const max = Math.max(...columns.map(c => c.value), baseline?.value ?? 0) * 1.15
  const y = (v: number) => (v / max) * H
  return (
    <div className="cols" role="img" aria-label={ariaLabel}>
      <div className="cols-plot" style={{ height: H }}>
        {baseline && (
          <div className="cols-baseline" style={{ bottom: y(baseline.value) }}>
            <span>{baseline.label} {format(baseline.value)}</span>
          </div>
        )}
        {columns.map((c, i) => (
          <div key={c.label} className="col" onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
            <span className="col-value">{format(c.value)}</span>
            <motion.div className="col-bar" style={{ '--step': i / Math.max(1, columns.length - 1) } as never}
                        initial={{ height: 0 }} whileInView={{ height: y(c.value) }}
                        viewport={{ once: true }} transition={{ duration: 0.7, delay: i * 0.08, ease: [0.2, 0.8, 0.2, 1] }} />
            {hover === i && <div className="chart-tip">{c.detail}</div>}
          </div>
        ))}
      </div>
      <div className="cols-axis">
        {columns.map(c => (
          <div key={c.label}><strong>{c.label}</strong><span className="muted small">{c.sub}</span></div>
        ))}
      </div>
    </div>
  )
}
