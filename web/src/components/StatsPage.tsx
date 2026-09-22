import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { Link, StatsDoc } from '../statsTypes'
import { money, shortDate } from '../format'
import { ColumnChart } from './charts/ColumnChart'
import { CrashChart } from './charts/CrashChart'
import { HBarChart } from './charts/HBarChart'

type Metric = 'share_up_25' | 'share_peak_50' | 'median_change'
const METRICS: Record<Metric, { label: string; long: string }> = {
  share_up_25: { label: 'Rose 25%+', long: 'Share of cards whose price rose 25% or more' },
  share_peak_50: { label: 'Spiked 50%+', long: 'Share of cards that spiked 50% or more at some point' },
  median_change: { label: 'Median change', long: 'Median price change, before vs after release' },
}
const GROUP_NAMES = ['Market (not a candidate)', 'Text match, Jev said weak', 'Jev-linked (real synergy+)']
const pct = (v: number) => `${v > 0 && v < 1 ? v.toFixed(1) : Math.round(v)}%`
const signed = (v: number) => `${v > 0 ? '+' : ''}${Math.round(v)}%`

function odds(p: number) {
  if (p <= 0.001) return 'under 1 in 1,000'
  return `about 1 in ${Math.round(1 / p)}`
}

const reveal = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.5 },
}

function Kpi({ value, label }: { value: string; label: string }) {
  return <div className="kpi-tile"><strong>{value}</strong><span>{label}</span></div>
}

function LinkTable({ rows, showSynergy }: { rows: Link[]; showSynergy: boolean }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr><th>Older card</th><th>New Hobbit card</th>{showSynergy && <th>Jev synergy</th>}<th>Before</th><th>After</th><th>Change</th></tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.name + r.partner}>
              <td>{r.name}</td>
              <td className="muted">{r.partner}</td>
              {showSynergy && <td>{Math.round(r.synergy * 100)}</td>}
              <td>{money(r.base)}</td>
              <td>{money(r.after)}</td>
              <td className={r.change >= 0 ? 'pos' : 'neg'}>
                <span aria-hidden="true">{r.change >= 0 ? '▲' : '▼'}</span> {signed(r.change * 100)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function StatsPage() {
  const [s, setS] = useState<StatsDoc | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [metric, setMetric] = useState<Metric>('share_up_25')
  const [tab, setTab] = useState<'wins' | 'links'>('wins')

  useEffect(() => {
    fetch('/data/stats.json', { cache: 'no-cache' })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setS)
      .catch(e => setError(String(e)))
  }, [])

  if (error) return <div className="state">Couldn't load stats.json ({error}).</div>
  if (!s) return <div className="state"><div className="orb" /> Crunching numbers…</div>

  const bt = s.backtest
  const linked = bt.groups[2]
  const market = bt.groups[0]
  const lastCrash = s.crash.series[s.crash.series.length - 1]

  return (
    <div className="stats">
      <header className="hero">
        <motion.p className="eyebrow" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Methodology &amp; results</motion.p>
        <motion.h1 className="h1-small" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          How the <span>Oracle</span> decides
        </motion.h1>
        <p className="lede">What goes in, what Jev judges, and whether it works: tested against real prices.</p>
      </header>

      <motion.section className="kpi-row" {...reveal}>
        <Kpi value={s.pipeline.cards_tracked.toLocaleString()} label="Commander cards priced daily" />
        <Kpi value={`${s.pipeline.days}`} label="days of price history" />
        <Kpi value={bt.counts.pairs.toLocaleString()} label="card pairs judged by Jev" />
        <Kpi value={`${(linked.share_up_25 / market.share_up_25).toFixed(1)}×`} label="how much likelier Jev's picks were to rise 25%" />
      </motion.section>

      {/* ---------------- how it works ---------------- */}
      <motion.section className="block" {...reveal}>
        <h2>How it works</h2>
        <div className="flow">
          <div className="flow-step"><span className="flow-n">1</span><strong>Collect</strong>
            <p>Every day at 07:00 UTC: prices for {s.pipeline.cards_tracked.toLocaleString()} Commander-legal cards (MTGJSON / TCGplayer), card text and art (Scryfall), and Commander deck counts (EDHREC).</p></div>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <div className="flow-step"><span className="flow-n">2</span><strong>Judge</strong>
            <p>TypeSafe's <em>Jev</em> reads each card's rules text and answers narrow questions with calibrated probabilities. It never sees prices.</p></div>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <div className="flow-step"><span className="flow-n">3</span><strong>Decide</strong>
            <p>Plain code combines Jev's answers with price trends and EDHREC adoption into a demand score and a Buy / Hold / Sell call.</p></div>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <div className="flow-step"><span className="flow-n">4</span><strong>Test</strong>
            <p>Every signal is checked against what prices actually did after a real event, like a new set's release.</p></div>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>What Jev is asked</h2>
        <p className="muted">Jev is a "System One" model: it returns typed answers and probabilities, not paragraphs. Each card gets four questions, judged from its rules text alone:</p>
        <div className="q-grid">
          <div className="q-card"><h3>Deck breadth</h3><p>Would nearly every deck in its colors want it, or only one narrow tribe?</p><span className="q-type">Score, 5 levels</span></div>
          <div className="q-card"><h3>Power</h3><p>How strong is it for its cost at a casual-to-focused Commander table?</p><span className="q-type">Score, 5 levels</span></div>
          <div className="q-card"><h3>Build-around commander</h3><p>Will players build a whole deck around it as their commander?</p><span className="q-type">Yes/no probability</span></div>
          <div className="q-card"><h3>Set-locked</h3><p>Does it only work with its own set's mechanics? This lowers the score.</p><span className="q-type">Yes/no probability</span></div>
        </div>
        <div className="formula">
          <h3>From answers to a verdict</h3>
          <p><strong>Demand</strong> = 30% deck breadth + 20% power + 15% build-around + 35% EDHREC adoption − 15% set-locked</p>
          <ul>
            <li><span className="v v-buy">▲ Buy</span> demand ≥ 55, already down 50%+ from its preorder peak, and not still sliding this week</li>
            <li><span className="v v-sell">▼ Sell</span> demand under 35 (or under 45 and still sliding), and worth at least $2</li>
            <li><span className="v v-hold">◆ Hold</span> everything else</li>
          </ul>
          <p className="muted small">These per-card weights are a starting guess and haven't been validated yet. The test below checks a different Jev question: which <em>older</em> cards a new set makes better.</p>
        </div>
      </motion.section>

      {/* ---------------- backtest ---------------- */}
      <motion.section className="block" {...reveal}>
        <p className="eyebrow">The test</p>
        <h2>Does Jev spot the cards a new set pumps?</h2>
        <p>When <strong>The Hobbit</strong> released on {shortDate(bt.event.date)}, code found {bt.counts.pairs.toLocaleString()} possible pairings between its {bt.counts.new_cards} new rares and older cards,
          and Jev scored each pair: <em>how much does the new card make the older one worth playing?</em> Then we compared prices from before preorders
          ({shortDate(bt.event.windows.base[0])}–{shortDate(bt.event.windows.base[1])}) to a month after release ({shortDate(bt.event.windows.after[0])}–{shortDate(bt.event.windows.after[1])}).
          The rules were fixed before looking at any result.</p>

        <div className="chart-card">
          <div className="chart-card-head">
            <h3>{METRICS[metric].long}</h3>
            <div className="seg" role="group" aria-label="Metric">
              {(Object.keys(METRICS) as Metric[]).map(m => (
                <button key={m} className={metric === m ? 'on' : ''} onClick={() => setMetric(m)}>{METRICS[m].label}</button>
              ))}
            </div>
          </div>
          <HBarChart
            key={metric}
            ariaLabel={METRICS[metric].long}
            format={metric === 'median_change' ? (v => `${v > 0 ? '+' : ''}${v}%`) : pct}
            bars={bt.groups.map((g, i) => ({
              label: ['Market', 'Text match only', 'Jev-linked'][i],
              value: g[metric],
              emphasis: i === 2,
              detail: `${GROUP_NAMES[i]}: ${g.n.toLocaleString()} cards`,
            }))}
          />
          <p className="chart-note">
            <strong>Market</strong>: the other {market.n.toLocaleString()} older cards (not reprinted, worth $0.50+).
            <strong> Text match only</strong>: the code flagged them, but Jev said the link was weak.
            <strong> Jev-linked</strong>: Jev scored real synergy or better.
          </p>
        </div>

        <div className="callouts">
          <div className="callout"><strong>{linked.share_up_25}%</strong> of Jev-linked cards rose 25%+, versus {market.share_up_25}% of the market.</div>
          <div className="callout"><strong>{odds(bt.permutation_p.linked_vs_text)}</strong> chance that luck explains the gap between Jev-linked and text-only cards.</div>
          <div className="callout"><strong>The text match alone barely beat the market.</strong> Jev's judgment is what separated the winners.</div>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>The higher Jev's score, the better the odds</h2>
        <div className="chart-card">
          <h3>Share of candidate cards that rose 25%+, by Jev's synergy score</h3>
          <ColumnChart
            ariaLabel="Share rising 25% by Jev synergy bucket"
            format={pct}
            baseline={{ value: market.share_up_25, label: 'Market' }}
            columns={bt.buckets.map(b => ({
              label: b.label, value: b.share_up_25, sub: `${b.n} cards`,
              detail: `${b.label}: ${b.share_up_25}% rose 25%+ · median ${b.median_change > 0 ? '+' : ''}${b.median_change}%`,
            }))}
          />
          <p className="chart-note">Each column holds all candidate pairings whose best Jev score fell in that range. Jev's strongest links rose 25%+ at roughly twice the market rate.</p>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <div className="chart-card-head">
          <h2>The cards behind the numbers</h2>
          <div className="seg" role="group" aria-label="Table">
            <button className={tab === 'wins' ? 'on' : ''} onClick={() => setTab('wins')}>Biggest wins</button>
            <button className={tab === 'links' ? 'on' : ''} onClick={() => setTab('links')}>Jev's strongest links</button>
          </div>
        </div>
        {tab === 'wins'
          ? <LinkTable rows={bt.biggest_wins} showSynergy />
          : <LinkTable rows={bt.top_links} showSynergy />}
        <p className="chart-note">"Strongest links" shows the misses too: most high-scoring cards moved a little, and some fell.</p>
      </motion.section>

      <motion.section className="block caveats" {...reveal}>
        <h2>Honest caveats</h2>
        <ul>
          <li><strong>It raises the odds; it doesn't pick winners.</strong> {Math.round(100 - linked.share_up_25)}% of Jev-linked cards did <em>not</em> rise 25%. Per card, the correlation is weak (ρ = {bt.spearman.rho.toFixed(2)}). Treat it as a watch list.</li>
          <li><strong>One event so far.</strong> The Hobbit is heavy on tribes (Dwarves, Wolves). The pipeline now saves prices daily, so each new set and each ban becomes another test.</li>
          <li><strong>Reprints were excluded</strong>, because a reprint drops a card's price for reasons unrelated to synergy.</li>
          <li><strong>Not financial advice.</strong> Card prices are noisy, thin markets.</li>
        </ul>
      </motion.section>

      {/* ---------------- crash ---------------- */}
      <motion.section className="block" {...reveal}>
        <p className="eyebrow">Why timing matters</p>
        <h2>The preorder crash</h2>
        <div className="chart-card">
          <h3>A typical {s.set.name} rare's price, as a % of its own peak</h3>
          <CrashChart series={s.crash.series} />
          <p className="chart-note">The line is the median of all {s.crash.cards} rares and mythics; the shaded band covers the middle half.
            {` ${lastCrash.since_release}`} days after release, the typical card sells for {lastCrash.median}% of its preorder peak, and {s.set.under_1} of {s.set.cards} are under $1.
            That's why the Oracle waits for a card to bottom out before calling it a Buy.</p>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>Data freshness</h2>
        <div className="kpi-row small">
          <Kpi value={s.pipeline.price_rows.toLocaleString()} label="daily price points stored" />
          <Kpi value={`${shortDate(s.pipeline.history_from)} – ${shortDate(s.pipeline.history_to)}`} label="price history range" />
          <Kpi value={s.pipeline.last_ok_run ? new Date(s.pipeline.last_ok_run).toLocaleDateString() : '—'} label="last successful price run" />
        </div>
        <p className="muted small">Sources: MTGJSON (TCGplayer and Card Kingdom prices), Scryfall (card data and images), EDHREC (Commander deck counts), TypeSafe Jev (judgments). The code is open source on{' '}
          <a href="https://github.com/kitapplegate/commander-oracle" target="_blank" rel="noreferrer">GitHub</a>.</p>
      </motion.section>
    </div>
  )
}
