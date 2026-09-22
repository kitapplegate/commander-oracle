import { motion } from 'motion/react'
import { useState } from 'react'

export interface HBar {
  label: string
  value: number
  emphasis?: boolean
  detail?: string
}

interface Props {
  bars: HBar[]
  format: (v: number) => string
  max?: number
  ariaLabel: string
}

/** Horizontal bars for comparing a few named groups. One emphasized bar, the rest neutral. */
export function HBarChart({ bars, format, max, ariaLabel }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  const top = max ?? Math.max(...bars.map(b => b.value)) * 1.1
  return (
    <div className="hbars" role="img" aria-label={ariaLabel}>
      {bars.map((b, i) => (
        <div key={b.label} className={`hbar-row${hover === i ? ' hot' : ''}`}
             onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
          <div className="hbar-label">{b.label}</div>
          <div className="hbar-track">
            <motion.div className={`hbar-fill${b.emphasis ? ' emph' : ''}`}
                        initial={{ width: 0 }} whileInView={{ width: `${Math.max(0, b.value) / top * 100}%` }}
                        viewport={{ once: true }} transition={{ duration: 0.8, delay: i * 0.1, ease: [0.2, 0.8, 0.2, 1] }} />
            <span className="hbar-value">{format(b.value)}</span>
          </div>
          {hover === i && b.detail && <div className="chart-tip">{b.detail}</div>}
        </div>
      ))}
    </div>
  )
}
