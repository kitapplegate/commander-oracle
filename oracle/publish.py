"""Publish data/cards.json and data/stats.json to the website, atomically, only
if they look sane.

    python -m oracle.publish /var/www/oracle.marzipan-solutions.com/data

A bad build (empty, unjudged, unparseable) exits non-zero and leaves the live
files alone, so the site keeps showing the last good data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .sources import DATA

MIN_CARDS = 10


def check_cards(doc: dict) -> str | None:
    cards = doc.get("cards", [])
    if len(cards) < MIN_CARDS:
        return f"only {len(cards)} cards"
    unjudged = [c["name"] for c in cards if "outlook" not in c]
    if unjudged:
        return f"{len(unjudged)} cards have no outlook (e.g. {unjudged[0]})"
    return None


def check_stats(doc: dict) -> str | None:
    missing = [k for k in ("backtest", "crash", "pipeline", "set") if k not in doc]
    return f"missing sections: {missing}" if missing else None


def main() -> None:
    dest_dir = Path(sys.argv[1])
    staged = []
    for name, check in (("cards.json", check_cards), ("stats.json", check_stats)):
        raw = (DATA / name).read_bytes()
        problem = check(json.loads(raw))
        if problem:
            sys.exit(f"refusing to publish {name}: {problem}")
        staged.append((name, raw))
    # Only replace anything once both files have passed their checks.
    for name, raw in staged:
        tmp = dest_dir / f".{name}.tmp"
        tmp.write_bytes(raw)
        tmp.chmod(0o644)
        os.replace(tmp, dest_dir / name)
    cards = json.loads(staged[0][1])
    print(f"published {len(cards['cards'])} cards + stats (generated {cards['generated']}) to {dest_dir}")


if __name__ == "__main__":
    main()
