"""Daily price pipeline. Safe to run any number of times a day.

    python -m oracle.daily            # normal run (what the timer calls)
    python -m oracle.daily --refresh  # also force a card-list refresh

Each run:
  1. downloads MTGJSON's AllPricesToday (~5 MB) and archives the raw file under
     data/raw/daily/<price day>.json.gz, so history can always be recomputed
  2. if that price day is already ingested, records "stale" and stops
  3. refreshes the card list (AllPrintings, ~130 MB) when it is over a week old,
     or when too many priced printings are unknown (a new set just landed)
  4. upserts the cheapest non-foil price per card for that day
  5. records the run in the `runs` table

Exits non-zero on failure so systemd/cron shows it failed instead of going quiet.
"""
from __future__ import annotations

import argparse
import gzip
import json
import lzma
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone

import requests

from . import universe
from .sources import DATA, HEADERS

sys.stdout.reconfigure(encoding="utf-8")

TODAY_URL = "https://mtgjson.com/api/v5/AllPricesToday.json.gz"
PRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.sqlite.xz"
ARCHIVE = DATA / "raw" / "daily"
CARD_REFRESH_DAYS = 7
# ~5,400 priced printings are always unmapped (Alchemy, non-Commander-legal). A new
# set shows up as a jump over the last good run, not as an absolute count.
UNKNOWN_JUMP_THRESHOLD = 300


def _download(url: str, dest) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def refresh_printings() -> None:
    xz = universe.PRINTINGS.with_suffix(".sqlite.xz")
    _download(PRINTINGS_URL, xz)
    tmp = universe.PRINTINGS.with_suffix(".sqlite.part")
    with lzma.open(xz) as src, open(tmp, "wb") as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    tmp.replace(universe.PRINTINGS)
    xz.unlink()


def printings_age_days() -> float:
    if not universe.PRINTINGS.exists():
        return float("inf")
    return (time.time() - universe.PRINTINGS.stat().st_mtime) / 86400


def fetch_today() -> tuple[str, dict]:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    tmp = ARCHIVE / "latest.json.gz"
    _download(TODAY_URL, tmp)
    with gzip.open(tmp, "rb") as f:
        doc = json.load(f)
    day = doc["meta"]["date"]
    tmp.replace(ARCHIVE / f"{day}.json.gz")
    return day, doc["data"]


def run(force_refresh: bool = False) -> int:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.time()
    db = universe.connect()
    record = {"price_day": None, "status": "failed", "cards_priced": 0, "unknown_uuids": 0,
              "cards_refreshed": 0, "note": ""}
    try:
        day, data = fetch_today()
        record["price_day"] = day
        already = db.execute("SELECT 1 FROM runs WHERE price_day = ? AND status = 'ok'", (day,)).fetchone()
        if already and not force_refresh:
            record.update(status="stale", note="MTGJSON has not published a newer day yet")
            print(f"{day}: already ingested; nothing to do")
            return 0

        if force_refresh or printings_age_days() > CARD_REFRESH_DAYS or not universe.uuid_map(db):
            refresh_printings()
            record["cards_refreshed"] = universe.refresh_cards(db)

        prices, unknown = universe.cheapest_daily(data.items(), universe.uuid_map(db))
        last = db.execute("SELECT unknown_uuids FROM runs WHERE status = 'ok' ORDER BY started DESC LIMIT 1").fetchone()
        if last and unknown - last[0] > UNKNOWN_JUMP_THRESHOLD and not record["cards_refreshed"]:
            print(f"unmapped printings jumped {last[0]} -> {unknown}: refreshing the card list")
            refresh_printings()
            record["cards_refreshed"] = universe.refresh_cards(db)
            prices, unknown = universe.cheapest_daily(data.items(), universe.uuid_map(db))

        universe.upsert_prices(db, prices)
        record.update(status="ok", cards_priced=len(prices), unknown_uuids=unknown)
        print(f"{day}: priced {len(prices):,} cards ({unknown} unmapped printings)"
              + (f"; refreshed {record['cards_refreshed']:,} cards" if record["cards_refreshed"] else ""))
        return 0
    except Exception as e:
        record["note"] = f"{type(e).__name__}: {e}"[:500]
        traceback.print_exc()
        return 1
    finally:
        with db:
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                       (started, record["price_day"], record["status"], record["cards_priced"],
                        record["unknown_uuids"], record["cards_refreshed"], round(time.time() - t0, 1), record["note"]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="force a card-list refresh")
    sys.exit(run(force_refresh=ap.parse_args().refresh))


if __name__ == "__main__":
    main()
