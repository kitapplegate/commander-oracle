"""How accurate is Buy/Hold/Sell? Replay today's verdict logic as of past dates
and check what prices did afterward.

    python -m oracle.replay               # as of 30 and 14 days before the latest price day
    python -m oracle.replay --days 45 30  # other look-backs

Price signals are recomputed from the history in data/cards.json, cut off at the
replay date. Jev's answers never involve prices, so they are the same at any date.
EDHREC numbers are today's, which the replay could not have known: that flatters
the result a little, so treat it as a best case.

Writes data/replay.json.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date, datetime, timedelta, timezone

from . import outlook, signals
from .sources import DATA

sys.stdout.reconfigure(encoding="utf-8")

CARDS = DATA / "cards.json"
OUT = DATA / "replay.json"


def replay(cards: list[dict], as_of: str) -> dict:
    rows = []
    for c in cards:
        hist = [(d, p) for d, p in c.get("history") or [] if d <= as_of]
        if not hist or hist[-1][0] < as_of or c["released"] > as_of or not c.get("price"):
            continue
        sig = signals.price_signals(hist, c["released"])
        verdict = outlook.outlook({**c, **sig, "buylist_ratio": None})["verdict"]
        rows.append({"name": c["name"], "set": c["set"], "verdict": verdict, "then": sig["price"],
                     "now": c["price"], "change": round(c["price"] / sig["price"] - 1, 4)})
    groups = {}
    for v in ("buy", "hold", "sell", "all"):
        ch = [r["change"] for r in rows if v == "all" or r["verdict"] == v]
        groups[v] = {"n": len(ch),
                     "median_change": round(statistics.median(ch) * 100, 1) if ch else None,
                     "rose": round(sum(x > 0 for x in ch) / len(ch) * 100) if ch else None,
                     "fell": round(sum(x < 0 for x in ch) / len(ch) * 100) if ch else None,
                     "fell_20": round(sum(x <= -0.2 for x in ch) / len(ch) * 100) if ch else None}
    calls = sorted((r for r in rows if r["verdict"] != "hold"), key=lambda r: (r["verdict"], r["change"]))
    return {"as_of": as_of, "groups": groups, "calls": calls}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, nargs="+", default=[30, 14], help="look-backs in days")
    args = ap.parse_args()
    doc = json.loads(CARDS.read_text(encoding="utf-8"))
    latest = max(c["as_of"] for c in doc["cards"] if c.get("as_of"))
    runs = [replay(doc["cards"], str(date.fromisoformat(latest) - timedelta(days=n))) for n in args.days]

    for run in runs:
        print(f"\nverdicts as of {run['as_of']} -> prices on {latest}")
        print(f"{'verdict':8}{'n':>5}{'median':>9}{'rose':>7}{'fell':>7}{'fell 20%+':>11}")
        for v, g in run["groups"].items():
            if g["n"]:
                print(f"{v:8}{g['n']:5}{g['median_change']:8.1f}%{g['rose']:6}%{g['fell']:6}%{g['fell_20']:10}%")
            else:
                print(f"{v:8}{0:5}")
        for r in run["calls"]:
            if r["verdict"] == "buy":
                print(f"  buy  {r['name'][:36]:36} ${r['then']:.2f} -> ${r['now']:.2f} ({r['change']*100:+.0f}%)")

    OUT.write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "prices_to": latest, "runs": runs}, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
