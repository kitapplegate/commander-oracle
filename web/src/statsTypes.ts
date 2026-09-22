export interface GroupRow {
  group: string
  n: number
  median_change: number
  mean_change: number
  share_up_25: number
  share_peak_50: number
}

export interface Bucket {
  label: string
  n: number
  share_up_25: number
  median_change: number
}

export interface Link {
  name: string
  partner: string
  synergy: number
  combo?: number
  base: number
  after: number
  change: number
  peak_change?: number
}

export interface CrashPoint {
  day: string
  since_release: number
  median: number
  p25: number
  p75: number
}

export interface StatsDoc {
  generated: string
  backtest: {
    event: { name: string; date: string; windows: { base: [string, string]; after: [string, string] } }
    counts: { new_cards: number; pool: number; pairs: number; link_threshold: number; min_base_price: number }
    groups: GroupRow[]
    spearman: { rho: number; p: number }
    permutation_p: { linked_vs_text: number; linked_vs_market: number }
    buckets: Bucket[]
    top_links: Link[]
    biggest_wins: Link[]
  }
  crash: { release: string; cards: number; series: CrashPoint[] }
  pipeline: { cards_tracked: number; history_from: string; history_to: string; days: number; price_rows: number; last_ok_run: string | null }
  set: { name: string; cards: number; verdicts: Record<string, number>; under_1: number }
  explore: ExploreDoc | null
}

export interface Share { n: number; share_up_25: number | null; median_change: number | null }

export interface Idea {
  key: string
  name: string
  rho: number
  buckets: (Share & { label: string })[]
}

export interface JevExample {
  older: string
  new: string
  rung: number
  confidence: number
  combo: number
  base: number
  after: number
  change: number
  link_count: number
  new_card_build_around: number
}

export interface ExploreDoc {
  event: string
  market: Share
  candidates: number
  linked: number
  new_cards: number
  pairs: number
  ideas: Idea[]
  by_price: { label: string; market: Share; linked: Share }[]
  under3_market: Share
  combos: (Share & { name: string })[]
  overlap: { four_plus_links: number; very_high_played: number; both: number }
  ladder: string[]
  examples: { hit: JevExample; miss: JevExample }
}
