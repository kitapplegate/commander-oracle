import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import type { Card, CardsDoc } from './types'
import { money, VERDICTS, verdictOf, type VerdictKey } from './format'
import { CardTile } from './components/CardTile'
import { DetailPanel } from './components/DetailPanel'
import { JevPage } from './components/JevPage'
import { StatsPage } from './components/StatsPage'

type Sort = 'demand' | 'price' | 'week' | 'edh'
const SORTS: Record<Sort, { label: string; key: (c: Card) => number }> = {
  demand: { label: 'Commander demand', key: c => c.outlook?.demand ?? -1 },
  price: { label: 'Price', key: c => c.price ?? -1 },
  week: { label: 'This week', key: c => c.change_7d ?? -999 },
  edh: { label: 'EDHREC decks', key: c => c.edh_decks ?? -1 },
}
const MIN_PRICES = [0, 1, 5, 10]
const TILES: VerdictKey[] = ['buy', 'hold', 'sell']

function CardsPage() {
  const [doc, setDoc] = useState<CardsDoc | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [verdict, setVerdict] = useState<VerdictKey | 'all'>('all')
  const [minPrice, setMinPrice] = useState(1)
  const [sort, setSort] = useState<Sort>('demand')
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState<Card | null>(null)
  const [setCode, setSetCode] = useState<string>('all')

  useEffect(() => {
    // Rebuilt daily on the server; no-cache makes the browser revalidate instead of guessing.
    fetch('/data/cards.json', { cache: 'no-cache' })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setDoc)
      .catch(e => setError(String(e)))
  }, [])

  const inSet = useMemo(
    () => (doc?.cards ?? []).filter(c => setCode === 'all' || c.set === setCode),
    [doc, setCode],
  )
  const inRange = useMemo(() => inSet.filter(c => (c.price ?? 0) >= minPrice), [inSet, minPrice])
  const setIcons = useMemo(() => Object.fromEntries((doc?.sets ?? []).map(s => [s.code, s.icon])), [doc])
  const counts = useMemo(() => {
    const out: Record<string, number> = {}
    inRange.forEach(c => { const v = verdictOf(c); out[v] = (out[v] ?? 0) + 1 })
    return out
  }, [inRange])
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return inRange
      .filter(c => verdict === 'all' || verdictOf(c) === verdict)
      .filter(c => !q || c.name.toLowerCase().includes(q) || c.type_line.toLowerCase().includes(q))
      .sort((a, b) => SORTS[sort].key(b) - SORTS[sort].key(a))
  }, [inRange, verdict, query, sort])

  const topPick = useMemo(
    () => inRange.filter(c => verdictOf(c) === 'buy').sort((a, b) => b.outlook!.demand - a.outlook!.demand)[0],
    [inRange],
  )

  if (error) return <div className="state">Couldn't load cards.json ({error}). Run <code>python -m oracle.build</code> first.</div>
  if (!doc) return <div className="state"><div className="orb" /> Consulting the oracle…</div>

  return (
    <>
      <header className="hero">
        <motion.p className="eyebrow" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          The {doc.sets.length} newest sets · rares &amp; mythics
        </motion.p>
        <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          Commander <span>Oracle</span>
        </motion.h1>
        <motion.p className="lede" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }}>
          You cracked a pack. Hold it, buy more, or sell it before it drops?
        </motion.p>
      </header>

      <section className="set-picker" aria-label="Choose a set">
        <button className={`set-chip${setCode === 'all' ? ' on' : ''}`} onClick={() => setSetCode('all')} aria-pressed={setCode === 'all'}>
          <span className="set-chip-name">All sets</span>
          <span className="set-chip-sub">{doc.cards.length} cards</span>
        </button>
        {doc.sets.map(s => (
          <button key={s.code} className={`set-chip${setCode === s.code ? ' on' : ''}`}
                  onClick={() => setSetCode(setCode === s.code ? 'all' : s.code)} aria-pressed={setCode === s.code}>
            <img src={s.icon} alt="" width={22} height={22} className="set-icon" />
            <span className="set-chip-text">
              <span className="set-chip-name">{s.name}</span>
              <span className="set-chip-sub">{new Date(s.released + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</span>
            </span>
          </button>
        ))}
      </section>

      <section className="summary">
        {TILES.map((v, i) => (
          <motion.button key={v} className={`sum sum-${v}${verdict === v ? ' active' : ''}`}
                         onClick={() => setVerdict(verdict === v ? 'all' : v)}
                         initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                         transition={{ delay: 0.3 + i * 0.08 }} whileHover={{ y: -3 }}
                         aria-pressed={verdict === v}>
            <span className="sum-icon" aria-hidden="true">{VERDICTS[v].icon}</span>
            <span className="sum-count">{counts[v] ?? 0}</span>
            <span className="sum-label">{VERDICTS[v].label}</span>
          </motion.button>
        ))}
        {topPick && (
          <motion.button className="sum sum-pick" onClick={() => setOpen(topPick)}
                         initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                         transition={{ delay: 0.55 }} whileHover={{ y: -3 }}
                         style={{ backgroundImage: topPick.image.art ? `url(${topPick.image.art})` : undefined }}>
            <span className="sum-pick-fade" />
            <span className="sum-pick-text">
              <span className="eyebrow">Top pick</span>
              <strong>{topPick.name.split(' // ')[0]}</strong>
              <span>{money(topPick.price)}</span>
            </span>
          </motion.button>
        )}
      </section>

      <section className="controls">
        <input className="search" placeholder="Search cards or types…" value={query}
               onChange={e => setQuery(e.target.value)} aria-label="Search" />
        <div className="seg" role="group" aria-label="Minimum price">
          {MIN_PRICES.map(p => (
            <button key={p} className={minPrice === p ? 'on' : ''} onClick={() => setMinPrice(p)}>
              {p === 0 ? 'All' : `$${p}+`}
            </button>
          ))}
        </div>
        <select value={sort} onChange={e => setSort(e.target.value as Sort)} aria-label="Sort by">
          {Object.entries(SORTS).map(([k, s]) => <option key={k} value={k}>{s.label}</option>)}
        </select>
        {verdict !== 'all' && <button className="link-btn" onClick={() => setVerdict('all')}>Clear filter</button>}
      </section>

      <p className="showing" aria-live="polite">
        Showing <strong>{shown.length}</strong> of {inSet.length} cards
        {minPrice > 0 && inSet.length > inRange.length && (
          <> · {inSet.length - inRange.length} under ${minPrice} hidden · <button className="link-btn inline" onClick={() => setMinPrice(0)}>Show all</button></>
        )}
      </p>

      <motion.main className="grid" layout>
        <AnimatePresence mode="popLayout">
          {shown.map((c, i) => <CardTile key={c.id} card={c} index={i} setIcon={setIcons[c.set]} onOpen={setOpen} />)}
        </AnimatePresence>
      </motion.main>
      {shown.length === 0 && <p className="state">No cards match. Try lowering the price floor.</p>}

      <footer className="foot">
        <p>Prices: TCGplayer via MTGJSON · Commander data: EDHREC · Card images: Scryfall · Judgments: TypeSafe Jev</p>
        <p>Probabilities, not promises. The per-card verdict weights haven't been backtested yet (<a href="#/stats">see the stats</a>). Updated {new Date(doc.generated).toLocaleString()}.</p>
      </footer>

      <AnimatePresence>{open && <DetailPanel key={open.id} card={open} onClose={() => setOpen(null)} />}</AnimatePresence>
    </>
  )
}

type Route = 'cards' | 'stats' | 'jev'
const routeOf = (): Route => {
  const h = window.location.hash
  return h.startsWith('#/stats') ? 'stats' : h.startsWith('#/jev') ? 'jev' : 'cards'
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeOf)
  useEffect(() => {
    const onHash = () => { setRoute(routeOf()); window.scrollTo({ top: 0 }) }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <div className="app">
      <div className="bg-glow" aria-hidden="true" />
      <nav className="nav">
        <a href="#/" className="nav-brand">Commander <span>Oracle</span></a>
        <div className="nav-links">
          <a href="#/" className={route === 'cards' ? 'on' : ''}>Cards</a>
          <a href="#/stats" className={route === 'stats' ? 'on' : ''}>How it works &amp; stats</a>
          <a href="#/jev" className={route === 'jev' ? 'on' : ''}>Jev lab</a>
        </div>
      </nav>
      {route === 'stats' ? <StatsPage /> : route === 'jev' ? <JevPage /> : <CardsPage />}
      <footer className="foot">
        <p>Unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.</p>
      </footer>
    </div>
  )
}
