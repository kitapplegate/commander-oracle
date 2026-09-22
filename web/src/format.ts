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
  buy: { label: 'Buy', icon: '▲', blurb: 'Strong Commander demand, price looks like it has bottomed' },
  hold: { label: 'Hold', icon: '◆', blurb: 'No strong signal either way. Keep it and watch.' },
  sell: { label: 'Sell', icon: '▼', blurb: 'Weak long-term demand. Sell while it is still worth something.' },
  pending: { label: 'Awaiting Jev', icon: '…', blurb: 'Not judged yet' },
}

export const verdictOf = (c: Card): VerdictKey => c.outlook?.verdict ?? 'pending'
