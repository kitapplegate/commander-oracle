import type { Card, Verdict } from './types'

export const money = (n: number | null | undefined) =>
  n == null ? '—' : n >= 100 ? `$${n.toFixed(0)}` : `$${n.toFixed(2)}`

export const signedPct = (n: number | null | undefined) =>
  n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(0)}%`

export const shortDate = (iso: string) =>
  new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export type VerdictKey = Verdict | 'pending'

// Status colors carry meaning only alongside an icon + label, never alone.
export const VERDICTS: Record<VerdictKey, { label: string; icon: string; blurb: string }> = {
  buy: { label: 'Buy', icon: '▲', blurb: 'Past the release crash and just dropped. A better time to pick it up.' },
  hold: { label: 'Hold', icon: '◆', blurb: 'No strong signal either way. Keep it and watch.' },
  sell: { label: 'Sell', icon: '▼', blurb: 'In the release crash, or riding a spike that tends to fade. Sell while it is up.' },
  pending: { label: 'Awaiting Jev', icon: '…', blurb: 'Not judged yet' },
}

export const verdictOf = (c: Card): VerdictKey => c.outlook?.verdict ?? 'pending'
