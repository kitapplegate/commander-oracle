# Next

**Action:** Read the MTGJSON publish-time watch and move the daily timer to just after MTGJSON's real publish time.
**Why now:** The daily timer fires at 07:00 UTC on the assumption MTGJSON publishes ~06:15. On 2026-09-22 it hadn't published by 11:00 UTC, so the 07:01 run logged `stale` and the site skipped a day. The hourly watcher (installed 2026-09-22 10:06 UTC) records when each new day actually appears.
**Start here:** `ssh root@217.15.170.26 "cd /opt/commander-oracle/app && sudo -u oracle .venv/bin/python -m oracle.watch --report"` (one row per MTGJSON day: first poll that saw it, and the file's Last-Modified).
**Decide:** wait for about 5–7 days of rows. Take the latest usual Last-Modified time and set `OnCalendar` in `deploy/commander-oracle-daily.timer` about 30–60 min after it. If the time swings a lot from day to day, add a second daily run instead (a `stale` run does no harm). Then `cp` the timer to `/etc/systemd/system/`, `systemctl daemon-reload`, and `systemctl disable --now commander-oracle-watch.timer`.
**Verify with:** the next day's `runs` row is `ok` for that day's `price_day` on the first run, with no `stale` first (query: `sudo -u oracle .venv/bin/python -c "import sqlite3; ..."`; the README's `sqlite3` CLI line doesn't work, there's no sqlite3 on the VPS).
**Watch out for:** the watcher only logs; it changes nothing. Until the timer moves, any day MTGJSON publishes late gets skipped. The Oct 1 monthly backfill recovers those days.
