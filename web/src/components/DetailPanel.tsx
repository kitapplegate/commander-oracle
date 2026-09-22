import { motion, useMotionValue, useSpring, useTransform } from 'motion/react'
import { useEffect } from 'react'
import type { Card } from '../types'
import { money, signedPct, VERDICTS, verdictOf } from '../format'
import { PriceChart } from './PriceChart'
import { VerdictBadge } from './VerdictBadge'

function HoloCard({ card }: { card: Card }) {
  const mx = useMotionValue(0.5)
  const my = useMotionValue(0.5)
  const rx = useSpring(useTransform(my, [0, 1], [12, -12]), { stiffness: 200, damping: 18 })
  const ry = useSpring(useTransform(mx, [0, 1], [-14, 14]), { stiffness: 200, damping: 18 })
  const sheen = useTransform(mx, [0, 1], ['0%', '100%'])
  return (
    <motion.div
      className="holo"
      style={{ rotateX: rx, rotateY: ry, '--sheen-x': sheen } as never}
      onPointerMove={e => {
        const r = e.currentTarget.getBoundingClientRect()
        mx.set((e.clientX - r.left) / r.width)
        my.set((e.clientY - r.top) / r.height)
      }}
      onPointerLeave={() => { mx.set(0.5); my.set(0.5) }}
    >
      {card.image.normal && <img src={card.image.normal} alt={card.name} />}
      <div className={`holo-sheen${card.rarity === 'mythic' ? ' holo-mythic' : ''}`} />
    </motion.div>
  )
}

function Gauge({ label, value, hint, invert = false }: { label: string; value: number; hint: string; invert?: boolean }) {
  const pctVal = Math.round(value * 100)
  return (
    <div className="gauge">
      <div className="gauge-top">
        <span>{label}</span>
        <strong>{pctVal}</strong>
      </div>
      <div className="gauge-track">
        <motion.div className={`gauge-fill${invert ? ' gauge-invert' : ''}`}
                    initial={{ width: 0 }} animate={{ width: `${pctVal}%` }}
                    transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }} />
      </div>
      <p className="muted small">{hint}</p>
    </div>
  )
}

export function DetailPanel({ card, onClose }: { card: Card; onClose: () => void }) {
  const verdict = verdictOf(card)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const j = card.jev
  return (
    <>
      <motion.div className="scrim" onClick={onClose}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
      <motion.aside className="panel" role="dialog" aria-label={card.name}
                    initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
                    transition={{ type: 'spring', stiffness: 260, damping: 30 }}>
        <button className="close" onClick={onClose} aria-label="Close">✕</button>
        <div className="panel-hero">
          <HoloCard card={card} />
          <div className="panel-summary">
            <p className="eyebrow">{card.set_name} · {card.rarity}</p>
            <h2>{card.name}</h2>
            <p className="muted">{card.type_line}</p>
            <div className="verdict-block">
              <VerdictBadge verdict={verdict} big />
              <p>{VERDICTS[verdict].blurb}</p>
            </div>
            <div className="kpis">
              <div><span className="muted small">Price</span><strong>{money(card.price)}</strong></div>
              <div><span className="muted small">7 days</span><strong>{signedPct(card.change_7d)}</strong></div>
              <div><span className="muted small">Off peak</span><strong>{signedPct(card.off_peak)}</strong></div>
              <div><span className="muted small">EDHREC decks</span><strong>{card.edh_decks?.toLocaleString() ?? '—'}</strong></div>
            </div>
          </div>
        </div>

        {card.outlook && card.outlook.reasons.length > 0 && (
          <section>
            <h3>Why</h3>
            <ul className="reasons">
              {card.outlook.reasons.map((r, i) => (
                <motion.li key={r} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
                           transition={{ delay: 0.15 + i * 0.06 }}>{r}</motion.li>
              ))}
            </ul>
          </section>
        )}

        <section>
          <PriceChart points={card.history} peakDay={card.peak_day} />
        </section>

        <section>
          <h3>What Jev sees <span className="muted">judged from the rules text alone</span></h3>
          {j ? (
            <div className="gauges">
              <Gauge label="Deck breadth" value={j.breadth} hint="How many kinds of Commander decks want it" />
              <Gauge label="Power" value={j.power} hint="Strength for its cost at a Commander table" />
              <Gauge label="Build-around commander" value={j.commander_draw} hint="Chance players build a deck around it" />
              <Gauge label="Set-locked" value={j.set_locked} hint="Chance it only works with this set's cards" invert />
            </div>
          ) : <p className="muted">Jev hasn't judged this card yet. Run <code>python -m oracle.judge</code>.</p>}
        </section>

        <section className="oracle-text">
          <h3>Rules text</h3>
          {card.oracle_text.split('\n').map((line, i) => <p key={i}>{line}</p>)}
        </section>

        <footer className="panel-links">
          {card.scryfall_url && <a href={card.scryfall_url} target="_blank" rel="noreferrer">Scryfall ↗</a>}
          {card.edhrec_url && <a href={card.edhrec_url} target="_blank" rel="noreferrer">EDHREC ↗</a>}
        </footer>
      </motion.aside>
    </>
  )
}
