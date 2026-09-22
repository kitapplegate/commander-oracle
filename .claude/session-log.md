# Session Log

## 2026-09-21 22:50

**Summary:** New project, built end to end in one session: a Commander buy/hold/sell site for rares and mythics from the 5 newest expansions (388 cards), using TypeSafe's Jev to judge rules text only (no prices). Live at oracle.marzipan-solutions.com, public at github.com/kitapplegate/commander-oracle (MIT, WotC fan-content notice). Headline result: a pre-registered Hobbit backtest; Jev-linked older cards rose 25%+ at 23.6% vs a 13.6% market rate (p≈0.009 vs text-only), but that's one event. Wrong assumptions caught: MTGJSON's AllPrices only covers 90 days, so we now keep our own history in `data/universe.sqlite`; reversible "X // X" printings duplicated cards, so grouping is now by oracle id (`a741541`); older sets' "preorder peak" was really the 90-day high, and the wording is now honest. MTGGoldfish history was ruled out (terms say personal use only). The key lives only in the VPS `.env` (mode 600). Last commit `0819d51`.

**Status:**
- Hobbit event backtest — **tested locally**: `python -m oracle.backtest`, numbers in VERIFICATION.md
- Daily pipeline + site refresh on the VPS — **verified in the real environment**: manual systemd runs succeeded; the unattended timer isn't yet observed
- 5-set site + stats page — **verified in the real environment**: Chrome checks on the live URL; live cards.json has 388 cards
- Key exposure audit — **verified in the real environment**: 0 matches across the site, repo history and logs

**Open tasks:**
- [ ] next — confirm the 07:00 UTC 2026-09-22 run logged `ok` and republished (see NEXT.md)
- [ ] not-yet-verified — per-card Buy/Sell weights are unvalidated; Jev's "power" Score clusters 0.50–0.69
- [ ] next-after — replicate the event backtest on the next set release or ban using our own history

**Deferred:** reprint-risk/ban-news Jev signals; uncommons watch; `C:\AI\CLAUDE.md` map entry for this repo.
