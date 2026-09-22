export type Verdict = 'buy' | 'hold' | 'sell'

export interface Jev {
  breadth: number
  breadth_conf: number
  power: number
  power_conf: number
  commander_draw: number
  set_locked: number
}

export interface Card {
  id: string
  name: string
  set: string
  set_name: string
  released: string
  rarity: 'rare' | 'mythic'
  type_line: string
  mana_cost: string
  color_identity: string[]
  oracle_text: string
  variants: number
  image: { small?: string; normal?: string; art?: string }
  scryfall_url?: string
  edhrec_url?: string | null
  edh_decks: number | null
  edh_inclusion: number | null
  price: number | null
  as_of?: string
  change_7d?: number | null
  change_30d?: number | null
  peak?: number
  peak_day?: string
  off_peak?: number | null
  /** true when our price history covers preorders, so the peak is the preorder peak */
  peak_is_preorder?: boolean
  buylist_ratio?: number | null
  history: [string, number][]
  jev?: Jev
  outlook?: { verdict: Verdict; demand: number; reasons: string[] }
}

export interface SetMeta {
  code: string
  name: string
  released: string
  icon: string
}

export interface CardsDoc {
  generated: string
  sets: SetMeta[]
  cards: Card[]
}
