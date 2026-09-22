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
- **Not yet verified:** the 07:00 UTC timer firing unattended.

## Site data refresh (build → judge → stats → publish)

- **2026-09-22 — verified in the real environment:** the full chain via systemd published 388 cards +
  stats; live `/data/cards.json` = 388 cards, sets hob/msh/sos/tmt/ecl; verdicts match the local
  build (5 buy / 356 hold / 27 sell). `oracle.publish` refused an unjudged build locally (exit 1).

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
