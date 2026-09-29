# Verification

## Event backtest: The Hobbit release (does Jev spot the cards a new set pumps?)

- **2026-09-21 — tested locally:** `.venv/Scripts/python -m oracle.backtest` with windows and groups
  fixed before running. 2,520 pairs, 1.72M input tokens, 72 s. Jev-linked (n=467): median +5.6%,
  23.6% rose 25%+, 17.6% spiked 50%+; text-only (n=1045): +3.3% / 15.2% / 9.9%; market (n=5169):
  +2.5% / 13.6% / 8.6%. Permutation p = 0.0093 (linked vs text-only). Spearman ρ = 0.092. One event only.

## Daily price pipeline (`oracle.daily`)

- **2026-09-21 — tested locally:** normal run priced 31,697 cards in 5.6 s; an immediate re-run logged
  `stale`; a bad URL exited 1 and logged `failed`; the backtest re-ran with identical numbers.
- **2026-09-22 — verified in the real environment (manual trigger):** fresh clone on the VPS failed
  first (`data/` missing on a clean clone), fixed in `8804fd0`; then `systemctl start
  commander-oracle-daily.service` → `Result=success`; backfill → 89 days (2026-06-23 → 2026-09-21).
- **2026-09-22 — verified in the real environment (unattended):** timer fired 07:01:49 UTC on its own,
  rebuilt and published (`generated 07:02:13`), but `runs` = `stale` for 2026-09-21: MTGJSON's
  `Meta.json` still said 2026-09-21 at 10:00 and 11:00 UTC (AllPricesToday Last-Modified 2026-09-21
  06:13). So the timer works; the 07:00 time is too early on late-publish days.
- **Not yet verified:** a first-run `ok` for a new price day (depends on retiming, see NEXT.md).

## MTGJSON publish-time watch (`oracle.watch`, temporary)

- **2026-09-22 — verified in the real environment:** hourly timer installed; manual run 10:06 UTC and
  the unattended 11:00 UTC poll both appended a row to `data/mtgjson-watch.tsv`; `--report` works.

## Buy/Hold/Sell accuracy (`oracle.replay`, weekly Mon 09:00 UTC)

- **2026-09-22 — verified in the real environment:** replay as of Aug 22 / Sep 7 vs Sep 21 prices.
  Old rules: Buy 0 of 5 profitable after the spike fix removed 3 (`47b3450`). New rules (`bea384a`):
  Sell median −21% vs −7.5% market (Aug 22), Sep 7 Sells 26 of 26 fell; Buy −4.2%/−4.8% vs −7.5%/−7.1%.
  **In-sample**: same weeks the rules were chosen on. The first fair replay is 2026-09-28.
- **2026-09-28 — the scheduled replay was NOT the fair one:** it scored as of Aug 28 and Sep 13 (30/14
  days before the latest day), both inside the tuning window, so it was in-sample again. Its
  `Result=success` only proves the unit ran.
- **2026-09-29 — fair replay, verified in the real environment (`oracle.fair`, run on the VPS's live DB
  read-only; reports in `reports/fair-replay-2026-09-29-h7.md` and `-h14.md`, the results of record):**
  rules `bea384a`, fingerprint `8defba803279` (same locally and on the VPS), cutoff 2026-09-21, universe
  hob/msh/sos/tmt/ecl frozen. Sep 21 verdicts were 54 Buy / 332 Hold / 2 Sell, identical to what the site
  published on Sep 22. **Interim 7-day horizon** (the rules were picked on 14): Buy median +1.2% vs −1.2%
  for its eligible pool (n=191), permutation p = 0.016; Sell n=2 (−22%, −10%), p = 0.074; all cards +0.0%.
  All 388 cards were 28+ days past release, so **the crash-window Sell rule has no out-of-sample test yet**.
  14-day result: not yet due; needs price day 2026-10-05. Code check: `oracle.fair`'s functions reproduce the
  recorded in-sample Sep 7 → Sep 21 numbers exactly (Sell 26/26 fell, median −20.9%; Buy −4.8%).
- **Study behind the rules (scratchpad, not in repo):** every site card × week, next-14-day return;
  rules picked on Jul 21–Aug 4, checked on Aug 12–Sep 3. Consistent tells: weekly move reverses
  (IC −0.19), distance above low (−0.16), price level (−0.13), Jev commander_draw (−0.10); demand ~0.

## Jev lab exploration (`oracle.explore`)

- **2026-09-22 — tested locally:** reproduces the published backtest groups exactly (guard in code);
  21 HOC cards judged once (16.5k input tokens, cached in `data/jev_newcards.json`). Rule A (Jev-linked,
  2+ links, under $3): 40.2% rose 25%+ (n=92) vs 17.2% market under $3. Exploratory; locked for the
  next set. Live page checked in Chrome (table 467/92 rows, no console errors, no overflow at 390px).

## Rule A Watch list, Reality Fracture (`oracle.rule_a`, pre-registered)

- **2026-09-29 — frozen before release (tested locally):** `python -m oracle.rule_a` froze 31 cards at
  07:18:51 UTC, three days before FRA releases on Oct 2 (`reports/rule-a-fra-2026-09-29.md`). 102 new FRA/FRC
  rares/mythics, older pool 6,716, 3,060 Jev pairs (2.09M input tokens), groups linked 339 / text-only 1,684 /
  market 4,693. Baseline Jul 6–19 is before the first FRA preorder price (Jul 20; bulk from Sep 1). The Hobbit
  backtest still reproduces exactly afterwards (`oracle.explore` guard). **Not yet scored:** after-window
  Oct 27 – Nov 9; primary test is share up 25%+ vs 2,788 market cards under $3 (Hobbit 40.2% vs 17.2%).

## Site data refresh (build → judge → stats → publish)

- **2026-09-22 — verified in the real environment:** the full chain via systemd published 388 cards +
  stats; live `/data/cards.json` = 388 cards, sets hob/msh/sos/tmt/ecl; verdicts match the local
  build (5 buy / 356 hold / 27 sell). `oracle.publish` refused an unjudged build locally (exit 1).
- **2026-09-22 — verified in the real environment:** after the new verdict rules, VPS build → judge →
  replay → stats → publish gave 54 buy / 332 hold / 2 sell, identical to the local run; live
  cards.json matched (`generated 10:59:34`).

## TypeSafe key exposure

- **2026-09-22 — verified in the real environment:** key absent from every served file (page, JS,
  CSS, cards.json), from a fresh clone of the public repo's full history, and from the journal;
  11 probe paths (`/.env`, `/.git/config`, `/data/jev_cache.json`, …) → 404; neither `caddy` nor
  `nobody` can read `/opt/commander-oracle/app/.env` (mode 600, owner `oracle`).

## Website (oracle.marzipan-solutions.com)

- **2026-09-22 — verified in the real environment:** cards page, set picker, "Showing X of Y · Show
  all", detail panel ("Off 90-day high" on a Marvel card), and the stats page all checked in Chrome,
  with no console errors. Other sites on the box returned their usual codes after the Caddy reload.
- **Phone width:** 390px iframe, no horizontal overflow (the window itself wouldn't resize this pass).
- **2026-09-22 — verified in the real environment:** Jev lab (`#/jev`), stats-page voice rewrite,
  replay + price-study sections, and the "looks back" Hobbit wording all served (checked JS bundle
  text and Chrome), no console errors; Kit confirmed the Jev lab in an incognito window.
