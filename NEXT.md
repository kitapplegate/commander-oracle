# Next

**Action:** Confirm the first unattended daily run (07:00 UTC 2026-09-22) ingested Sep 22 and republished the site.
**Why now:** Every run so far was started by hand; the timer firing on its own is the last unproven link.
**Start here:** `ssh root@217.15.170.26 "systemctl list-timers 'commander-oracle-*'; journalctl -u commander-oracle-daily --since today -o cat | tail -8"`
**Verify with:** `runs` has an `ok` row with `price_day = 2026-09-22` (query in `deploy/README.md`), and `https://oracle.marzipan-solutions.com/data/cards.json` `generated` is after 07:00 UTC today.
**Watch out for:** an early run may log `stale` if MTGJSON hasn't published yet; that's fine only if a later run gets `ok`.
