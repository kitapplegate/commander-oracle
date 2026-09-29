# Next

**Action:** After price day 2026-10-05 lands (the 07:00 UTC run on Oct 6), run `python -m oracle.fair` on the VPS for the first 14-day fair Buy/Sell result.
**Why now:** The 2026-09-29 fair result is a 7-day interim. The rules were picked on 14-day returns, so the 14-day report is the first one that tests them on their own terms.
**Start here:** `oracle.fair` isn't deployed yet. Push, `git pull` on the VPS, then `sudo -u oracle .venv/bin/python -m oracle.fair` from `/opt/commander-oracle/app`, and commit the new `reports/fair-replay-*` files. Optionally add it to `commander-oracle-replay.service` so it runs every Monday.
**Verify with:** the report lists verdict date 2026-09-21 → 2026-10-05, rule `bea384a` / fingerprint `8defba803279`, and the same 54/332/2 verdict counts as the 7-day report.
**Then:** score the Reality Fracture rule A list after 2026-11-09 (after window Oct 27 – Nov 9): read `reports/rule-a-fra-2026-09-29.json`'s `pool` block, add after-window prices, and apply the scoring written in the `.md`. Write a small scorer; don't edit the frozen files.
**Watch out for:** don't re-run `oracle.rule_a` for fra (it refuses on/after Oct 2 anyway). `oracle.fair` refuses if `outlook.py`/`signals.py` change. The local `universe.sqlite` was deliberately not refreshed: a refresh would move the Hobbit backtest's pool. Rule A's site display (Watch list vs Buy vs Jev lab) is still Kit's call. Retiming the daily timer is dropped (first-run `ok` every day Sep 23–29; the watcher was disabled 2026-09-29).
