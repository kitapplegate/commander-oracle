"""Add Jev judgments and the outlook to data/cards.json.

    python -m oracle.judge

Jev answers are cached in data/jev_cache.json by card id, so tweaking
outlook.py and re-running costs no inference. Bump QUESTION_VERSION when
jev.QUESTIONS changes, to force a re-judge.
"""
from __future__ import annotations

import json
import sys

from . import jev, outlook, sources

sys.stdout.reconfigure(encoding="utf-8")

QUESTION_VERSION = 1
CARDS = sources.DATA / "cards.json"
CACHE = sources.DATA / "jev_cache.json"


def main() -> None:
    doc = json.loads(CARDS.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    if cache.get("version") != QUESTION_VERSION:
        cache = {"version": QUESTION_VERSION, "cards": {}}

    todo = [c for c in doc["cards"] if c["id"] not in cache["cards"]]
    if todo:
        print(f"asking Jev about {len(todo)} card(s)...")
        for card, judgment in zip(todo, jev.judge_all(todo)):
            cache["cards"][card["id"]] = judgment
        CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        print(f"  input tokens: {sum(cache['cards'][c['id']]['tokens'] for c in todo)}")

    for card in doc["cards"]:
        card["jev"] = cache["cards"][card["id"]]
        card["outlook"] = outlook.outlook(card)
    CARDS.write_text(json.dumps(doc, indent=1), encoding="utf-8")

    counts = {}
    for c in doc["cards"]:
        counts[c["outlook"]["verdict"]] = counts.get(c["outlook"]["verdict"], 0) + 1
    print(f"outlook: {counts}")


if __name__ == "__main__":
    main()
