import { VERDICTS, type VerdictKey } from '../format'

export function VerdictBadge({ verdict, big = false }: { verdict: VerdictKey; big?: boolean }) {
  const v = VERDICTS[verdict]
  return (
    <span className={`badge badge-${verdict}${big ? ' badge-big' : ''}`}>
      <span aria-hidden="true">{v.icon}</span> {v.label}
    </span>
  )
}
