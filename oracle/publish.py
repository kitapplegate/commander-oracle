"""Publish data/cards.json to the website, atomically, only if it looks sane.

    python -m oracle.publish /var/www/oracle.marzipan-solutions.com/data

A bad build (empty, unjudged, unparseable) exits non-zero and leaves the live
file alone, so the site keeps showing the last good data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .sources import DATA

MIN_CARDS = 10


def main() -> None:
    dest_dir = Path(sys.argv[1])
    src = DATA / "cards.json"
    raw = src.read_bytes()
    doc = json.loads(raw)
    cards = doc.get("cards", [])
    if len(cards) < MIN_CARDS:
        sys.exit(f"refusing to publish: only {len(cards)} cards")
    unjudged = [c["name"] for c in cards if "outlook" not in c]
    if unjudged:
        sys.exit(f"refusing to publish: {len(unjudged)} cards have no outlook (e.g. {unjudged[0]})")
    tmp = dest_dir / ".cards.json.tmp"
    tmp.write_bytes(raw)
    tmp.chmod(0o644)
    os.replace(tmp, dest_dir / "cards.json")
    print(f"published {len(cards)} cards (generated {doc['generated']}) to {dest_dir}")


if __name__ == "__main__":
    main()
