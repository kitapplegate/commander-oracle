import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { ExploreDoc, Idea, JevExample, StatsDoc } from '../statsTypes'
import { money } from '../format'
import { ColumnChart } from './charts/ColumnChart'
import { HBarChart } from './charts/HBarChart'

const pct = (v: number | null) => (v == null ? '—' : `${v}%`)
const signed = (v: number) => `${v > 0 ? '+' : ''}${Math.round(v * 100)}%`

const reveal = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.5 },
}

// What each idea means, in plain words. Keys match oracle/explore.py.
const IDEA_NOTES: Record<string, string> = {
  link_count: 'Some older cards got linked to more than one new Hobbit card. If a whole set pushes toward the same card, more decks want it.',
  played: "Jev's link, multiplied by how likely Jev thinks players are to build a deck around the new card. A great partner for a commander nobody builds shouldn't move much.",
  base: "The older card's price before preorders showed up. This is the one market number I let in, because I'd have it before the set comes out.",
}

function Example({ ex, ladder }: { ex: JevExample; ladder: string[] }) {
  return (
    <>
      <div className="pair">
        <div className="pair-card"><span>New Hobbit card</span><strong>{ex.new}</strong></div>
        <div className="pair-x" aria-hidden="true">×</div>
        <div className="pair-card"><span>Older card</span><strong>{ex.older}</strong></div>
      </div>
      <p className="muted">The question: <em>how much does the new card make the older one more worth playing in Commander?</em> Jev picks one rung:</p>
      <ol className="ladder">
        {ladder.map((rung, i) => (
          <li key={i} className={i === ex.rung ? 'on' : ''} aria-current={i === ex.rung ? 'true' : undefined}>
            <b>{i}</b><span>{rung}{i === ex.rung && <> · <strong>Jev's answer, {Math.round(ex.confidence * 100)}% confident</strong></>}</span>
          </li>
        ))}
      </ol>
      <p className="chart-note">It also answered a yes/no question, "do these two make an infinite combo or win on the spot?", and put that at {Math.round(ex.combo * 100)}%.</p>
    </>
  )
}

function IdeaChart({ idea, market }: { idea: Idea; market: number }) {
  return (
    <div className="chart-card">
      <div className="chart-card-head"><h3>{idea.name}</h3><span className="muted small">ρ = {idea.rho.toFixed(2)}</span></div>
      {IDEA_NOTES[idea.key] && <p className="muted">{IDEA_NOTES[idea.key]}</p>}
      <ColumnChart
        ariaLabel={`Share rising 25% by ${idea.name}`}
        format={v => `${v}%`}
        baseline={{ value: market, label: 'Market' }}
        columns={idea.buckets.filter(b => b.n > 0).map(b => ({
          label: b.label, value: b.share_up_25 ?? 0, sub: `${b.n} cards`,
          detail: `${b.label}: ${b.share_up_25}% rose 25%+ · median ${b.median_change}%`,
        }))}
      />
    </div>
  )
}

export function JevPage() {
  const [x, setX] = useState<ExploreDoc | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/data/stats.json', { cache: 'no-cache' })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((s: StatsDoc) => (s.explore ? setX(s.explore) : setError('no exploration data yet')))
      .catch(e => setError(String(e)))
  }, [])

  if (error) return <div className="state">Couldn't load the Jev lab ({error}).</div>
  if (!x) return <div className="state"><div className="orb" /> Asking Jev…</div>

  const { hit, miss } = x.examples
  const market = x.market.share_up_25 ?? 0
  const ideas = x.ideas.filter(i => i.key in IDEA_NOTES)
  const best = x.combos[x.combos.length - 1]

  return (
    <div className="stats">
      <header className="hero">
        <motion.p className="eyebrow" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>The Jev lab</motion.p>
        <motion.h1 className="h1-small" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          What <span>Jev</span> can do
        </motion.h1>
        <p className="lede">Jev is a model from TypeSafe that answers narrow questions with a number instead of a paragraph. This page is me poking at it to see how far that goes.</p>
      </header>

      <motion.section className="kpi-row" {...reveal}>
        <div className="kpi-tile"><strong>{x.pairs.toLocaleString()}</strong><span>card pairs I asked Jev about</span></div>
        <div className="kpi-tile"><strong>{x.new_cards}</strong><span>new Hobbit rares and mythics</span></div>
        <div className="kpi-tile"><strong>0</strong><span>prices Jev got to see</span></div>
        <div className="kpi-tile"><strong>{pct(best.share_up_25)}</strong><span>best mix so far, vs {pct(x.under3_market.share_up_25)} for the market</span></div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>One question, one answer</h2>
        <p>This is a real one. I hand Jev the rules text of two cards and it has to pick a rung on a ladder I wrote. It doesn't write me an essay about it. It picks the rung and tells me how sure it is, and that's something plain code can do math with.</p>
        <Example ex={hit} ladder={x.ladder} />
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>Same answer, two different endings</h2>
        <p>Here's the problem with judging one card at a time. Both of these got the same rung from Jev, from the same new card, and they went opposite ways.</p>
        <div className="twin">
          {[hit, miss].map(ex => (
            <div key={ex.older} className="callout">
              <strong>{ex.older}</strong>
              Linked to {ex.new}, rung {ex.rung}. Went from {money(ex.base)} to {money(ex.after)},{' '}
              <em className={ex.change >= 0 ? 'up' : 'down'}><span aria-hidden="true">{ex.change >= 0 ? '▲' : '▼'}</span> {signed(ex.change)}</em>.
              {' '}Jev linked it to {ex.link_count} new cards in all.
            </div>
          ))}
        </div>
        <p className="chart-note">Across all {x.linked} cards Jev linked, it helps a lot as a group and it's weak on any single card. So I went looking for things that could tell those two apart before the set ever came out.</p>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <p className="eyebrow">The experiment</p>
        <h2>Three ideas, all of them shown</h2>
        <p>The rule was that I could only use stuff I'd actually have before a set releases. No prices from after, because that's just reading the answer off the back of the book. I wrote the three ideas down before I ran anything, and every one of them is on this page, including the parts that didn't help much.</p>
        <p>The dashed line is the market, the {x.market.n.toLocaleString()} older cards nobody linked: {pct(market)} of them went up 25% or more.</p>
        {ideas.map(idea => <IdeaChart key={idea.key} idea={idea} market={market} />)}
        <p className="chart-note">Only {x.overlap.both} cards are in both "4+ links" ({x.overlap.four_plus_links}) and "very high" build-around ({x.overlap.very_high_played}), so those two are picking up different things.</p>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>Cheap cards move more anyway</h2>
        <p>Price was the strongest of the three, but cheap cards jump more everywhere, Jev or no Jev. So I checked Jev against the market at the same price. It still about doubles the odds under $10. Over $10 it barely does anything.</p>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Price before preorders</th><th>Market rose 25%+</th><th>Jev-linked rose 25%+</th></tr></thead>
            <tbody>
              {x.by_price.map(r => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td className="muted">{pct(r.market.share_up_25)} <span className="small">of {r.market.n.toLocaleString()}</span></td>
                  <td>{pct(r.linked.share_up_25)} <span className="small muted">of {r.linked.n}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>Putting them together</h2>
        <div className="chart-card">
          <h3>Share that rose 25%+ after The Hobbit</h3>
          <HBarChart
            ariaLabel="Share rising 25% for each combination"
            format={v => `${v}%`}
            bars={[
              { label: 'Market under $3', value: x.under3_market.share_up_25 ?? 0, detail: `${x.under3_market.n.toLocaleString()} cards` },
              ...x.combos.map((c, i) => ({ label: c.name, value: c.share_up_25 ?? 0, emphasis: i === x.combos.length - 1, detail: `${c.n} cards` })),
            ]}
          />
          <p className="chart-note">The last bar is only {best.n} cards, and I picked it after seeing the Hobbit numbers. That's exactly how you fool yourself, so it doesn't count as proof of anything yet.</p>
        </div>
        <div className="lock">
          <h3>Locked in for the next set</h3>
          <p>Before the next set releases, the Oracle flags every older card that is <strong>Jev-linked, linked to 2 or more of the new cards, and under $3</strong> before preorders. Same price windows as the Hobbit test, same 25% bar. Then I compare it to the market under $3 and post whatever happens here, good or bad.</p>
          <p className="muted small">On the Hobbit that mix hit {pct(best.share_up_25)} against {pct(x.under3_market.share_up_25)}. I expect it to come in lower next time, since I tuned it on this one set.</p>
        </div>
      </motion.section>
    </div>
  )
}
