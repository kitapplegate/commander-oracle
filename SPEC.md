# Commander Oracle — SPEC

The standing authority for this project. Amend it deliberately; don't let one
change quietly override it.

## What it is

A web app that answers, for the cards a normal person pulls from the newest
Magic sets: **what should I hold or buy, and what should I sell before it drops?**
The focus is **Commander demand**, not tournament play and not power/reserved-list
cards.

## Principles

1. **Jev judges, code decides.** Jev (TypeSafe's System One model) turns text
   (rules text, EDHREC context, and later news) into typed scores and
   probabilities. Price math, thresholds, and the final buy/sell ranking stay in
   code, where they can be read and re-weighted without re-running inference.
2. **Probabilities, not promises.** The app shows likelihoods and the signals
   behind them. It never claims to know a price will move.
3. **Prove it with a backtest.** Before a signal gets weight in the ranking,
   check it against a previous set whose outcome we already know.
4. **Free, public data only.** Scryfall (card data and images), MTGJSON (about
   90 days of daily prices), and EDHREC (Commander deck inclusion). Be polite:
   cache everything and rate-limit.

## Scope: "cards a normal person has"

Rares and mythics from the most recent expansion(s). The main printing only
(no showcase, borderless, or promo variants) for the first slices. There's no
price floor at ingest; the UI filters.

## Architecture

- `oracle/` is the Python pipeline. It fetches, caches, computes signals, asks
  Jev, and writes `data/cards.json`.
- The web frontend reads `cards.json`. The stack is chosen in its own slice.
- Secrets: `TYPESAFE_API_KEY` goes in `.env`, which is gitignored. This project
  has its own key, never shared with another project.

## Status log

- 2026-09-21: Repo created. Slice 1: data pipeline without Jev (The Hobbit, 68
  cards, all priced, 64 with EDHREC data). Slice 2: four Jev questions over
  the rules text only (`oracle/jev.py`), plus a code-side outlook (`oracle/outlook.py`,
  weights UNVALIDATED). Result: 4 buy / 59 hold / 5 sell. Jev's "power" Score
  clusters between 0.50 and 0.69, so watch whether it earns its weight. Slice 3:
  React + Vite + motion web app (`web/`) reading `cards.json`, checked in Chrome at
  desktop and 400px widths. Prepared to become a public repo (MIT, with the WotC
  Fan Content Policy notice).
- 2026-09-21: Event backtest #1, The Hobbit release. Built `oracle/universe.py`
  (31,781 Commander-legal cards with cheapest-printing daily prices from MTGJSON
  AllPrintings.sqlite + AllPrices). Code picks 30 text/tribal candidates per new
  card (`oracle/candidates.py`), and Jev scores each pair (`oracle/pair_jev.py`):
  2,520 pairs, 1.72M input tokens, 72 seconds. Rules fixed before running: older
  pool = pre-Jun-15 cards, not common-only, not reprinted since Jun 15,
  baseline >= $0.50 (6,681 cards). "Jev-linked" means synergy >= 0.5.
  Result: Jev-linked cards (n=467) had median +5.6% vs +3.3% for text-only
  candidates and +2.5% for the market; 23.6% rose 25% or more (vs 15.2% / 13.6%);
  17.6% peaked 50% or more (vs 9.9% / 8.6%). Permutation p = 0.009 vs text-only.
  Spearman rho is only 0.09, so it raises the odds rather than predicting any one
  card. The text candidate finder alone barely beats the market; Jev's
  judgment is where the signal comes from. This is ONE event, so it needs
  replication before any weights depend on it.
- Next: store our own daily prices (MTGJSON keeps only 90 days) so every future
  set release or ban becomes a new test; then replicate on the next event.
