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
- **Study behind the rules (scratchpad, not in repo):** every site card × week, next-14-day return;
  rules picked on Jul 21–Aug 4, checked on Aug 12–Sep 3. Consistent tells: weekly move reverses
  (IC −0.19), distance above low (−0.16), price level (−0.13), Jev commander_draw (−0.10); demand ~0.

## Jev lab exploration (`oracle.explore`)

- **2026-09-22 — tested locally:** reproduces the published backtest groups exactly (guard in code);
  21 HOC cards judged once (16.5k input tokens, cached in `data/jev_newcards.json`). Rule A (Jev-linked,
  2+ links, under $3): 40.2% rose 25%+ (n=92) vs 17.2% market under $3. Exploratory; locked for the
  next set. Live page checked in Chrome (table 467/92 rows, no console errors, no overflow at 390px).

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
