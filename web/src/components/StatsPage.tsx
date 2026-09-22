import { motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { Link, ReplayDoc, StatsDoc } from '../statsTypes'
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

const VERDICT_ROWS = [
  { key: 'buy', label: '▲ Buy', cls: 'v v-buy' },
  { key: 'hold', label: '◆ Hold', cls: 'v v-hold' },
  { key: 'sell', label: '▼ Sell', cls: 'v v-sell' },
  { key: 'all', label: 'Every card', cls: 'muted' },
] as const

function ReplaySection({ r }: { r: ReplayDoc }) {
  const buys = r.runs.flatMap(run => run.calls.filter(c => c.verdict === 'buy').map(c => ({ ...c, as_of: run.as_of })))
  const buyWins = buys.filter(b => b.change > 0).length
  return (
    <motion.section className="block" {...reveal}>
      <p className="eyebrow">Checking my own work</p>
      <h2>Is Buy / Hold / Sell any good?</h2>
      <p>Every Monday the server replays the verdict logic as if it ran {r.runs.map(run => shortDate(run.as_of)).join(' and ')}, using only the prices it would have had on that day, and then checks what those cards actually did up to {shortDate(r.prices_to)}.
        Jev's answers never involve prices, so they come out the same on any date. The EDHREC numbers are today's though, which the replay couldn't have known back then, so if anything this makes the logic look a little better than it is.</p>
      {r.runs.map(run => (
        <div key={run.as_of} className="chart-card">
          <h3>Verdicts as of {shortDate(run.as_of)}, prices on {shortDate(r.prices_to)}</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Verdict</th><th>Cards</th><th>Median change</th><th>Went up</th><th>Went down</th><th>Down 20%+</th></tr></thead>
              <tbody>
                {VERDICT_ROWS.map(v => {
                  const g = run.groups[v.key]
                  return (
                    <tr key={v.key}>
                      <td><span className={v.cls}>{v.label}</span></td>
                      <td>{g.n}</td>
                      <td>{g.median_change == null ? '—' : `${g.median_change > 0 ? '+' : ''}${g.median_change}%`}</td>
                      <td>{g.rose == null ? '—' : `${g.rose}%`}</td>
                      <td>{g.fell == null ? '—' : `${g.fell}%`}</td>
                      <td>{g.fell_20 == null ? '—' : `${g.fell_20}%`}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      {buys.length > 0 && (
        <div className="chart-card">
          <h3>Every Buy call in the replay</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Card</th><th>Called on</th><th>Price then</th><th>Price now</th><th>Change</th></tr></thead>
              <tbody>
                {buys.map(b => (
                  <tr key={b.name + b.as_of}>
                    <td>{b.name}</td>
                    <td className="muted">{shortDate(b.as_of)}</td>
                    <td>{money(b.then)}</td>
                    <td>{money(b.now)}</td>
                    <td className={b.change >= 0 ? 'pos' : 'neg'}><span aria-hidden="true">{b.change >= 0 ? '▲' : '▼'}</span> {signed(b.change * 100)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="chart-note">That's {buyWins} of {buys.length} Buy calls that went up. Treat Buy as the weakest part of the site until that number gets better.</p>
        </div>
      )}
      <div className="caveats">
        <ul>
          <li><strong>The old Buy was buying bounces.</strong> The first replay on Sep 22 caught it: a card that jumped 30 to 67% in a week counted as "stable", and those picks fell 27 to 45% afterward. That led to the study above and the new rules.</li>
          <li><strong>The replay covers the same weeks the new rules came from</strong>, so for now it mostly shows they do what the study said. It only becomes a fair test as new weeks come in.</li>
          <li><strong>It's a short window.</strong> The price history only goes back about 90 days, so each replay covers a few weeks. The tables above rebuild every week as more history comes in.</li>
        </ul>
      </div>
    </motion.section>
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
        <p className="lede">This is what goes in, what I ask Jev, and whether any of it works. I checked it against real prices and put all the numbers here, the misses too.</p>
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
            <p>Once a day the server pulls prices for {s.pipeline.cards_tracked.toLocaleString()} Commander-legal cards from MTGJSON, card text and art from Scryfall, and how many Commander decks run each card from EDHREC. MTGJSON only keeps 90 days of prices, so I keep my own history and it gets a day longer every morning.</p></div>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <div className="flow-step"><span className="flow-n">2</span><strong>Judge</strong>
            <p>TypeSafe's <em>Jev</em> reads the rules text on each card and answers a few narrow questions with a probability. It never sees a price, only the words on the card.</p></div>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <div className="flow-step"><span className="flow-n">3</span><strong>Decide</strong>
            <p>Then plain old code with no AI in it looks at how the card's price has been acting and how long it's been out, and turns that into Buy, Hold or Sell. Jev's answers feed the demand meter and the warnings on each card.</p></div>
          <div className="flow-arrow" aria-hidden="true">→</div>
          <div className="flow-step"><span className="flow-n">4</span><strong>Test</strong>
            <p>Every signal gets checked against what prices really did after something happened, like a new set coming out. So far that's one set.</p></div>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>What Jev is asked</h2>
        <p className="muted">Jev is what TypeSafe calls a "System One" model. I ask it a question and I get back an answer and a probability instead of a paragraph. Every card gets the same four questions and all it has to go on is the rules text:</p>
        <div className="q-grid">
          <div className="q-card"><h3>Deck breadth</h3><p>Would nearly every deck in its colors want it, or only one narrow tribe?</p><span className="q-type">Score, 5 levels</span></div>
          <div className="q-card"><h3>Power</h3><p>How strong is it for its cost at a casual-to-focused Commander table?</p><span className="q-type">Score, 5 levels</span></div>
          <div className="q-card"><h3>Build-around commander</h3><p>Will players build a whole deck around it as their commander?</p><span className="q-type">Yes/no probability</span></div>
          <div className="q-card"><h3>Set-locked</h3><p>Does it only work with its own set's mechanics? This lowers the score.</p><span className="q-type">Yes/no probability</span></div>
        </div>
        <div className="formula">
          <h3>From price behavior to a verdict</h3>
          <ul>
            <li><span className="v v-sell">▼ Sell</span> worth at least $2, and either it's 2 to 4 weeks after release (the crash), or it jumped 10%+ this week and sits 25%+ above its 90-day low</li>
            <li><span className="v v-buy">▲ Buy</span> at least 4 weeks after release, dropped 10%+ this week, and worth at least 50 cents</li>
            <li><span className="v v-hold">◆ Hold</span> everything else</li>
          </ul>
          <p><strong>Demand meter</strong> = 30% deck breadth + 20% power + 15% build-around + 35% EDHREC adoption − 15% set-locked. It still shows on every card, but it doesn't pick the verdict anymore, because it didn't predict prices (see below).</p>
          <p className="muted small">Buy here means "a better time to buy a card you want," not "this is going to go up." And none of these edges are big enough to flip cards for profit once TCGplayer fees and shipping come out.</p>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <p className="eyebrow">Where the rules came from</p>
        <h2>What the price data actually says</h2>
        <p>The first version of Buy was losing money, so on Sep 22 I went looking for tells. I took every card on the site on every week of the price history and looked at what its price did over the next 14 days. I picked the rules using the early weeks (Jul 21 to Aug 4) and then checked them on the later weeks (Aug 12 to Sep 3), which they'd never seen.</p>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Checked on the later weeks</th><th>Cards</th><th>Median, next 14 days</th><th>Rose 10%+</th><th>Fell 10%+</th></tr></thead>
            <tbody>
              <tr><td className="muted">Every card</td><td>778</td><td>−2.0%</td><td>21%</td><td>31%</td></tr>
              <tr><td><span className="v v-buy">▲</span> Old Buy rule</td><td>4</td><td>−5.5%</td><td>25%</td><td>50%</td></tr>
              <tr><td><span className="v v-buy">▲</span> Dropped 10%+ this week, 4+ weeks after release</td><td>122</td><td>+1.4%</td><td>32%</td><td>26%</td></tr>
              <tr><td><span className="v v-sell">▼</span> 2 to 4 weeks after release</td><td>35</td><td>−29%</td><td>3%</td><td>94%</td></tr>
              <tr><td><span className="v v-sell">▼</span> Jumped 10%+ this week and 25%+ above its low</td><td>173</td><td>−9.5%</td><td>17%</td><td>47%</td></tr>
            </tbody>
          </table>
        </div>
        <div className="caveats">
          <ul>
            <li><strong>Weeks 2 to 4 after release are the crash.</strong> Both sets that came out inside my price history, Marvel and The Hobbit, fell hard in that stretch. The old Buy rule was firing right in the middle of it.</li>
            <li><strong>New cards snap back.</strong> A card that dropped 10% or more in a week tended to bounce. One that spiked tended to give it back. That's the opposite of the whole market, where cards that are going up tend to keep going up for a while.</li>
            <li><strong>The hype drains out of commanders.</strong> Cards Jev expects people to build around, and legendaries in general, drifted down over the next couple of weeks. So Jev's answer shows up on those cards as a warning now.</li>
            <li><strong>The demand score didn't predict anything</strong> over 14 days. It might over months, but I only have 90 days of history, so I can't test that yet.</li>
            <li><strong>It's still thin.</strong> That's 7 weeks and 5 sets, and the crash rule rests on two releases. The weekly replay below is the real test from here on.</li>
          </ul>
        </div>
      </motion.section>

      {s.replay && <ReplaySection r={s.replay} />}

      {/* ---------------- backtest ---------------- */}
      <motion.section className="block" {...reveal}>
        <p className="eyebrow">The test</p>
        <h2>Testing it on The Hobbit</h2>
        <p>When <strong>The Hobbit</strong> came out on {shortDate(bt.event.date)}, code found {bt.counts.pairs.toLocaleString()} possible pairings between its {bt.counts.new_cards} new rares and older cards,
          and Jev scored every pair on one question: <em>how much does the new card make the older one worth playing?</em> Then I compared prices from before preorders
          ({shortDate(bt.event.windows.base[0])}–{shortDate(bt.event.windows.base[1])}) to about a month after release ({shortDate(bt.event.windows.after[0])}–{shortDate(bt.event.windows.after[1])}).
          I wrote the rules down before I looked at a single result, so I couldn't keep tweaking them until the chart looked good.</p>

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
            <strong>Market</strong> is the other {market.n.toLocaleString()} older cards that weren't reprinted and were worth at least 50 cents.
            <strong> Text match only</strong> means the code flagged them but Jev said the link was weak.
            <strong> Jev-linked</strong> means Jev called it real synergy or better.
          </p>
        </div>

        <div className="callouts">
          <div className="callout"><strong>{linked.share_up_25}%</strong> of the cards Jev linked went up 25% or more. For the rest of the market it was {market.share_up_25}%.</div>
          <div className="callout"><strong>{odds(bt.permutation_p.linked_vs_text)}</strong> odds that plain luck made the gap between the Jev-linked cards and the text-only ones.</div>
          <div className="callout"><strong>Matching on text alone barely beat the market.</strong> The cards that pulled ahead were the ones Jev picked out.</div>
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
          <p className="chart-note">Each column is every candidate card whose best Jev score landed in that range. The strongest links went up 25% or more at about twice the market rate.</p>
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
        <p className="chart-note">I left the misses in the strongest links list. Most of the high scorers only moved a little and some of them went down.</p>
      </motion.section>

      <motion.section className="block caveats" {...reveal}>
        <h2>Where this falls short</h2>
        <ul>
          <li><strong>It helps across a group of cards, and it's weak on any one card.</strong> {Math.round(100 - linked.share_up_25)}% of the Jev-linked cards didn't go up 25%, and card by card the correlation is weak (ρ = {bt.spearman.rho.toFixed(2)}). It's a watch list.</li>
          <li><strong>It's one event.</strong> The Hobbit leans hard on tribes like Dwarves and Wolves. The server saves prices every day now, so every new set and every ban is another chance to test it.</li>
          <li><strong>I threw out reprints</strong>, because a reprint drops a card's price for reasons that have nothing to do with synergy.</li>
          <li><strong>Not financial advice.</strong> Card prices are noisy and the markets are thin.</li>
        </ul>
      </motion.section>

      {/* ---------------- crash ---------------- */}
      <motion.section className="block" {...reveal}>
        <p className="eyebrow">Why timing matters</p>
        <h2>The preorder crash</h2>
        <div className="chart-card">
          <h3>A typical {s.set.name} rare's price, as a % of its own peak</h3>
          <CrashChart series={s.crash.series} />
          <p className="chart-note">The line is the median of all {s.crash.cards} rares and mythics, and the shaded band is the middle half of them.
            {` ${lastCrash.since_release}`} days after release the typical card sells for {lastCrash.median}% of its preorder peak, and {s.set.under_1} of the {s.set.cards} are under $1.
            That's why the Oracle waits for a card to bottom out before it calls it a Buy.</p>
        </div>
      </motion.section>

      <motion.section className="block" {...reveal}>
        <h2>Data freshness</h2>
        <div className="kpi-row small">
          <Kpi value={s.pipeline.price_rows.toLocaleString()} label="daily price points stored" />
          <Kpi value={`${shortDate(s.pipeline.history_from)} – ${shortDate(s.pipeline.history_to)}`} label="price history range" />
          <Kpi value={s.pipeline.last_ok_run ? new Date(s.pipeline.last_ok_run).toLocaleDateString() : '—'} label="last successful price run" />
        </div>
        <p className="muted small">The data comes from MTGJSON (TCGplayer and Card Kingdom prices), Scryfall (card data and images), EDHREC (Commander deck counts) and TypeSafe's Jev (the judging). I looked at MTGGoldfish for older price history, but their terms say personal use only, so none of it is in here. All the code is on{' '}
          <a href="https://github.com/kitapplegate/commander-oracle" target="_blank" rel="noreferrer">GitHub</a>.</p>
      </motion.section>
    </div>
  )
}
