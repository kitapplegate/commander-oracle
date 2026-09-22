"""Log when MTGJSON publishes a new price day, so the daily timer can be set to match.

    python -m oracle.watch          # append one line (what the hourly timer calls)
    python -m oracle.watch --report # summarize the log: first poll that saw each day

Each poll appends a tab-separated line to data/mtgjson-watch.tsv:
    polled_utc  meta_date  prices_last_modified_utc
meta_date is Meta.json's build date; the Last-Modified header on AllPricesToday
gives the exact publish time, so hourly polls are enough.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from .sources import DATA, HEADERS

sys.stdout.reconfigure(encoding="utf-8")

META_URL = "https://mtgjson.com/api/v5/Meta.json"
TODAY_URL = "https://mtgjson.com/api/v5/AllPricesToday.json.gz"
LOG = DATA / "mtgjson-watch.tsv"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def poll() -> str:
    polled = _iso(datetime.now(timezone.utc))
    meta = requests.get(META_URL, headers=HEADERS, timeout=30)
    meta.raise_for_status()
    meta_date = meta.json()["meta"]["date"]
    head = requests.head(TODAY_URL, headers=HEADERS, timeout=30, allow_redirects=True)
    head.raise_for_status()
    modified = head.headers.get("Last-Modified")
    modified = _iso(parsedate_to_datetime(modified)) if modified else "-"
    line = f"{polled}\t{meta_date}\t{modified}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def report() -> None:
    if not LOG.exists():
        print(f"no log yet at {LOG}")
        return
    first_seen: dict[str, tuple[str, str]] = {}
    for row in LOG.read_text(encoding="utf-8").splitlines():
        polled, meta_date, modified = row.split("\t")
        first_seen.setdefault(meta_date, (polled, modified))
    print("meta_date   first_poll_seen       prices_last_modified")
    for day, (polled, modified) in sorted(first_seen.items()):
        print(f"{day}  {polled}  {modified}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="summarize the log")
    args = ap.parse_args()
    if args.report:
        report()
    else:
        print(poll())
    return 0


if __name__ == "__main__":
    sys.exit(main())
