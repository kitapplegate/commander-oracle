"""Assemble data/stats.json for the website's stats page.

    python -m oracle.stats

Reads: data/backtest_hob.json (from oracle.backtest; fixed, since the event is past),
data/explore_hob.json (from oracle.explore, for the Jev page; optional, also fixed),
data/cards.json (from oracle.build/judge), data/universe.sqlite (pipeline health).
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date, datetime, timezone

from . import universe
from .sources import DATA

sys.stdout.reconfigure(encoding="utf-8")

BACKTEST = DATA / "backtest_hob.json"
EXPLORE = DATA / "explore_hob.json"
CARDS = DATA / "cards.json"
OUT = DATA / "stats.json"
# Synergy buckets for the "hit rate climbs with Jev's score" chart.
BUCKETS = [(0.0, 0.3, "No real link"), (0.3, 0.4, "Loose"), (0.4, 0.5, "Some"),
           (0.5, 0.6, "Real synergy"), (0.6, 1.01, "Strong")]


def backtest_section() -> dict:
    bt = json.loads(BACKTEST.read_text(encoding="utf-8"))
    buckets = []
    for lo, hi, label in BUCKETS:
        changes = [c[1] for c in bt["candidates"] if lo <= c[0] < hi]
        if changes:
            buckets.append({"label": label, "n": len(changes),
                            "share_up_25": round(sum(x >= 0.25 for x in changes) / len(changes) * 100, 1),
                            "median_change": round(statistics.median(changes) * 100, 1)})
    top = bt["linked"][:15]
    return {
        "event": bt["event"], "counts": bt["counts"], "groups": bt["groups"],
        "spearman": bt["spearman"], "permutation_p": bt["permutation_p"], "buckets": buckets,
        "top_links": [{k: t[k] for k in ("name", "partner", "synergy", "combo", "base", "after", "change",
                                         "peak_change")} for t in top],
        "biggest_wins": [{k: t[k] for k in ("name", "partner", "synergy", "base", "after", "change")}
                         for t in sorted(bt["linked"], key=lambda t: -t["change"])[:6]],
    }


def crash_section(cards: list[dict], release: str) -> dict:
    """Median (and middle-half band) of each card's price as a % of its own peak, by day."""
    rel = date.fromisoformat(release)
    by_day: dict[str, list[float]] = {}
    for c in cards:
        hist = c.get("history") or []
        if not hist:
            continue
        peak = max(p for _, p in hist)
        for d, p in hist:
            by_day.setdefault(d, []).append(p / peak * 100)
    series = []
    for d in sorted(by_day):
        vals = sorted(by_day[d])
        if len(vals) < len(cards) * 0.8:  # skip thin early preorder days
            continue
        q = statistics.quantiles(vals, n=4)
        series.append({"day": d, "since_release": (date.fromisoformat(d) - rel).days,
                       "median": round(statistics.median(vals), 1), "p25": round(q[0], 1), "p75": round(q[2], 1)})
    return {"release": release, "cards": len(cards), "series": series}


def pipeline_section() -> dict:
    db = universe.connect()
    lo, hi, days = db.execute("SELECT MIN(day), MAX(day), COUNT(DISTINCT day) FROM prices").fetchone()
    tracked = db.execute("SELECT COUNT(*) FROM prices WHERE day = ?", (hi,)).fetchone()[0]
    last_ok = db.execute("SELECT started, price_day FROM runs WHERE status = 'ok' ORDER BY started DESC LIMIT 1").fetchone()
    return {"cards_tracked": tracked, "history_from": lo, "history_to": hi, "days": days,
            "price_rows": db.execute("SELECT COUNT(*) FROM prices").fetchone()[0],
            "last_ok_run": last_ok[0] if last_ok else None}


def set_summary(name: str, cards: list[dict]) -> dict:
    verdicts: dict[str, int] = {}
    for c in cards:
        v = c.get("outlook", {}).get("verdict", "pending")
        verdicts[v] = verdicts.get(v, 0) + 1
    return {"name": name, "cards": len(cards), "verdicts": verdicts,
            "under_1": sum((c.get("price") or 0) < 1 for c in cards)}


def main() -> None:
    doc = json.loads(CARDS.read_text(encoding="utf-8"))
    newest = max(doc["sets"], key=lambda s: s["released"])
    newest_cards = [c for c in doc["cards"] if c["set"] == newest["code"]]
    stats = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backtest": backtest_section(),
        # The crash chart needs the preorder period in our history, so newest set only.
        "crash": crash_section(newest_cards, newest["released"]),
        "pipeline": pipeline_section(),
        "set": set_summary(newest["name"], newest_cards),
        "sets": [set_summary(s["name"], [c for c in doc["cards"] if c["set"] == s["code"]]) for s in doc["sets"]],
        "explore": json.loads(EXPLORE.read_text(encoding="utf-8")) if EXPLORE.exists() else None,
    }
    OUT.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(f"wrote {OUT}: {len(stats['crash']['series'])} crash days, "
          f"{len(stats['backtest']['buckets'])} synergy buckets, {stats['pipeline']['days']} days of history")


if __name__ == "__main__":
    main()
