import { motion } from 'motion/react'
import type { Card } from '../types'
import { money, signedPct, verdictOf } from '../format'
import { ColorPips } from './ColorPips'
import { Sparkline } from './Sparkline'
import { VerdictBadge } from './VerdictBadge'

interface Props {
  card: Card
  index: number
  onOpen: (c: Card) => void
}

export function CardTile({ card, index, onOpen }: Props) {
  const verdict = verdictOf(card)
  const wk = card.change_7d
  const demand = card.outlook?.demand
  return (
    <motion.button
      layout
      className={`tile tile-${verdict}`}
      onClick={() => onOpen(card)}
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.35, delay: Math.min(index * 0.025, 0.5), ease: [0.2, 0.8, 0.2, 1] }}
      whileHover={{ y: -6 }}
      whileTap={{ scale: 0.97 }}
    >
      <div className="tile-art" style={{ backgroundImage: card.image.art ? `url(${card.image.art})` : undefined }}>
        <div className="tile-art-fade" />
        <VerdictBadge verdict={verdict} />
        <span className={`rarity rarity-${card.rarity}`} title={card.rarity} />
      </div>
      <div className="tile-body">
        <div className="tile-title">
          <h3>{card.name.split(' // ')[0]}</h3>
          <ColorPips colors={card.color_identity} />
        </div>
        <div className="tile-stats">
          <div>
            <div className="price">{money(card.price)}</div>
            <div className={`delta ${wk == null ? '' : wk >= 0 ? 'up' : 'down'}`}>
              {wk == null ? '' : wk >= 0 ? '▲ ' : '▼ '}{signedPct(wk)} <span className="muted">7d</span>
            </div>
          </div>
          <Sparkline points={card.history} />
        </div>
        <div className="meter" title="Commander demand">
          <span className="meter-label">Demand</span>
          <div className="meter-track">
            <motion.div className="meter-fill" initial={{ width: 0 }}
                        animate={{ width: `${(demand ?? 0) * 100}%` }}
                        transition={{ duration: 0.8, delay: 0.2 + Math.min(index * 0.025, 0.5) }} />
          </div>
          <span className="meter-val">{demand == null ? '—' : Math.round(demand * 100)}</span>
        </div>
      </div>
    </motion.button>
  )
}
