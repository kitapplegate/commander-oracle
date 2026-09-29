"""Fair Buy/Hold/Sell replay: score the locked rules only on prices they never saw.

    python -m oracle.fair                 # the study's 14-day horizon
    python -m oracle.fair --horizon 7     # an interim look, labeled as one

oracle.replay re-scores dates the rules were picked on, so it can only flatter them.
This one keeps a trading-backtest discipline (TuringTrader-style): every report
states the rule version, the universe, the cutoff, the horizon and each call's
event window, and the only verdict dates that count are on or after the cutoff,
so every outcome price is one the rules never saw.

Reads data/universe.sqlite (read-only) and the Scryfall set lists (cached). Needs no
Jev and no cards.json: the verdict uses prices and release dates only.
Writes reports/fair-replay-<today>-h<horizon>.md (the result of record) and .json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

from . import build, outlook, signals, sources, universe

sys.stdout.reconfigure(encoding="utf-8")

# The rules under test. Editing outlook.py or signals.py makes a new version: lock it
# here (commit, fingerprint, cutoff = newest price day it was tuned on) and start a new record.
RULES = {"version": "bea384a", "locked": "2026-09-22", "cutoff": "2026-09-21", "fingerprint": "8defba803279"}
# The site's five sets when the rules were locked. Frozen so a new release rotating onto
# the site doesn't quietly change what is being tested.
UNIVERSE = ["hob", "msh", "sos", "tmt", "ecl"]
STUDY_HORIZON = 14  # days: the horizon the rules were picked on
STEP_DAYS = 7       # one verdict date per week, like the site's weekly rhythm
PERMUTATIONS = 10_000
REPORTS = Path(__file__).resolve().parent.parent / "reports"


def fingerprint() -> str:
    h = hashlib.sha256()
    for mod in (outlook, signals):
        h.update(Path(mod.__file__).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def event_window(age: int) -> str:
    """Where a card sits in its release cycle. A drop means different things in each."""
    if age < outlook.CRASH_DAYS[0]:
        return "release weeks (0-13 days)"
    if age < outlook.CRASH_DAYS[1]:
        return "crash window (14-27 days)"
    return "after the crash (28+ days)"


def load_cards(db: sqlite3.Connection) -> list[dict]:
    last_release = dict(db.execute("SELECT oracle_id, last_release FROM cards"))
    cards = []
    for code in UNIVERSE:
        for c in build.main_printings(sources.scryfall_set_cards(code)):
            oid = build._oracle_id(c)
            cards.append({"name": c["name"], "set": code, "released": c["released_at"],
                          "last_release": last_release.get(oid),
                          "history": db.execute("SELECT day, price FROM prices WHERE oracle_id = ? ORDER BY day",
                                                (oid,)).fetchall()})
    return cards


def verdicts(cards: list[dict], as_of: str, end: str) -> tuple[list[dict], int]:
    rows, unpriced = [], 0
    for c in cards:
        if c["released"] > as_of:
            continue
        hist = [(d, p) for d, p in c["history"] if d <= as_of]
        after = dict(c["history"]).get(end)
        if not hist or hist[-1][0] != as_of or not after:
            unpriced += 1
            continue
        sig = signals.price_signals(hist, c["released"])
        v = outlook.outlook({**sig, "released": c["released"], "jev": {"commander_draw": 0, "breadth": 0,
                                                                     "power": 0, "set_locked": 0},
                             "buylist_ratio": None})["verdict"]
        age = (date.fromisoformat(as_of) - date.fromisoformat(c["released"])).days
        rows.append({"name": c["name"], "set": c["set"], "released": c["released"], "age": age,
                     "window": event_window(age), "verdict": v, "then": sig["price"], "after": after,
                     "change": round(after / sig["price"] - 1, 4),
                     # A new printing after the verdict date lowers the cheapest price for reasons the rules can't see.
                     "new_printing": bool(c["last_release"] and c["last_release"] > as_of)})
    return rows, unpriced


def summary(changes: list[float]) -> dict:
    if not changes:
        return {"n": 0}
    return {"n": len(changes), "median": round(statistics.median(changes) * 100, 1),
            "rose": round(sum(x > 0 for x in changes) / len(changes) * 100),
            "fell": round(sum(x < 0 for x in changes) / len(changes) * 100),
            "fell_20": round(sum(x <= -0.2 for x in changes) / len(changes) * 100)}


def permutation_p(group: list[float], pool: list[float], higher: bool) -> float | None:
    """How often a random pick of the same size from the eligible pool does at least as well."""
    if not group or len(group) >= len(pool):
        return None
    rng = random.Random(0)
    obs = statistics.median(group)
    hits = 0
    for _ in range(PERMUTATIONS):
        m = statistics.median(rng.sample(pool, len(group)))
        hits += m >= obs if higher else m <= obs
    return round((hits + 1) / (PERMUTATIONS + 1), 4)


def score(rows: list[dict]) -> dict:
    ch = lambda f: [r["change"] for r in rows if f(r)]
    # Each call is compared with the cards it could have been called on, not with the whole market.
    buy_pool = ch(lambda r: r["age"] >= outlook.BUY_AFTER_DAYS and r["then"] >= outlook.MIN_BUY_PRICE)
    sell_pool = ch(lambda r: r["then"] >= outlook.MIN_SELL_PRICE)
    buys, sells = ch(lambda r: r["verdict"] == "buy"), ch(lambda r: r["verdict"] == "sell")
    windows = sorted({r["window"] for r in rows})
    return {
        "verdicts": {v: summary(ch(lambda r, v=v: r["verdict"] == v)) for v in ("buy", "hold", "sell")},
        "all": summary(ch(lambda r: True)),
        "buy_vs_pool": {"pool": summary(buy_pool), "p": permutation_p(buys, buy_pool, higher=True)},
        "sell_vs_pool": {"pool": summary(sell_pool), "p": permutation_p(sells, sell_pool, higher=False)},
        "by_window": {w: {v: summary(ch(lambda r, w=w, v=v: r["window"] == w and (v == "all" or r["verdict"] == v)))
                          for v in ("buy", "hold", "sell", "all")} for w in windows},
        "new_printing": sum(r["new_printing"] for r in rows),
    }


def next_watch_event() -> dict | None:
    """The next expansion rule A (the Watch rule) will be tested on."""
    data = sources._cached_json(sources.CACHE / "scryfall" / "sets.json", "https://api.scryfall.com/sets")
    upcoming = sorted((s for s in data["data"] if s["set_type"] == "expansion" and not s.get("digital")
                       and s.get("released_at", "") > max(RULES["cutoff"], str(date.today() - timedelta(days=60)))),
                      key=lambda s: s["released_at"])
    return {"code": upcoming[0]["code"], "name": upcoming[0]["name"], "released": upcoming[0]["released_at"]} \
        if upcoming else None


def fmt(s: dict) -> str:
    if not s.get("n"):
        return "| 0 | | | | |"
    return f"| {s['n']} | {s['median']:+.1f}% | {s['rose']}% | {s['fell']}% | {s['fell_20']}% |"


def markdown(doc: dict) -> str:
    r, h = doc["rules"], doc["horizon"]
    out = [f"# Fair replay — {doc['run_date']} — {h}-day horizon", "",
           "Result of record for the Buy/Hold/Sell rules. `oracle.replay` and the stats page's replay are "
           "in-sample; where they disagree with this file, this file wins.", "",
           "| | |", "|---|---|",
           f"| Rule version | `{r['version']}` (fingerprint `{r['fingerprint']}`), locked {r['locked']} |",
           f"| Cutoff | {r['cutoff']}: the newest price day the rules were tuned on. Only verdict dates on or "
           "after it count, so every outcome price is unseen |",
           f"| Universe | {', '.join(UNIVERSE)}: the site's sets at lock time, frozen; rare/mythic main printings, "
           "cheapest non-foil price across all printings |",
           f"| Horizon | {h} days" + ("" if h == STUDY_HORIZON else
                                       f" (**interim**: the rules were picked on {STUDY_HORIZON}-day returns)") + " |",
           f"| Verdict dates | {', '.join(doc['as_of_dates']) or 'none yet'} (every {STEP_DAYS} days from the "
           "cutoff whose horizon has closed) |",
           f"| Prices through | {doc['prices_to']} |", ""]
    if not doc["runs"]:
        out += [f"**No fair result yet.** The first {h}-day result needs price day {doc['first_due']}.", ""]
    for run in doc["runs"]:
        s = run["score"]
        out += [f"## Verdicts as of {run['as_of']} → prices on {run['end']}", "",
                f"{s['all']['n']} cards scored, {run['unpriced']} skipped (no price on one of the two days). "
                f"{s['new_printing']} got a new printing after {run['as_of']} (a reprint can drop the cheapest price).",
                "", "| Call | n | Median | Rose | Fell | Fell 20%+ |", "|---|---|---|---|---|---|"]
        for v in ("buy", "hold", "sell"):
            out.append(f"| {v.title()} " + fmt(s["verdicts"][v]))
        out.append("| All cards " + fmt(s["all"]))
        bp, sp = s["buy_vs_pool"], s["sell_vs_pool"]
        out += ["", "Against the cards each call could have been made on:", "",
                "| Comparison | n | Median | Rose | Fell | Fell 20%+ |", "|---|---|---|---|---|---|",
                "| Buy-eligible (28+ days out, $0.50+) " + fmt(bp["pool"]),
                "| Sell-eligible ($2+) " + fmt(sp["pool"]), "",
                f"- Buy: p = {bp['p']}, the share of random same-size picks from its pool whose median did at "
                "least as well." if bp["p"] is not None else "- Buy: too few calls to test.",
                f"- Sell: p = {sp['p']}, the share of random same-size picks from its pool whose median fell at "
                "least as far." if sp["p"] is not None else "- Sell: too few calls to test.",
                "", "### By event window", "",
                "The same price move means different things by card age: in the crash window almost "
                "everything falls, so a drop there is not a Buy signal (the rules never Buy before day "
                f"{outlook.BUY_AFTER_DAYS}).", "",
                "| Window (age at verdict) | Call | n | Median | Rose | Fell | Fell 20%+ |",
                "|---|---|---|---|---|---|---|"]
        for w, g in s["by_window"].items():
            for v in ("buy", "hold", "sell", "all"):
                if g[v].get("n"):
                    out.append(f"| {w} | {v} " + fmt(g[v]))
        empty = [w for w in map(event_window, (0, outlook.CRASH_DAYS[0], outlook.CRASH_DAYS[1]))
                 if w not in s["by_window"]]
        if empty:
            out += ["", f"**Untested on this date:** no cards were in {' or '.join(empty)}, so the rules for "
                        "those windows (e.g. the crash-window Sell) have no fair result here."]
        calls = sorted((c for c in run["rows"] if c["verdict"] != "hold"), key=lambda c: (c["verdict"], c["change"]))
        out += ["", "<details><summary>Every Buy and Sell call</summary>", "",
                "| Call | Card | Set | Age | Then | After | Change | New printing |", "|---|---|---|---|---|---|---|---|"]
        out += [f"| {c['verdict']} | {c['name']} | {c['set']} | {c['age']}d | ${c['then']:.2f} | ${c['after']:.2f} | "
                f"{c['change'] * 100:+.0f}% | {'yes' if c['new_printing'] else ''} |" for c in calls]
        out += ["", "</details>", ""]
    w = doc["watch"]
    out += ["## Watch (rule A)", "",
            "Rule A (Jev-linked older card, links to 2+ new cards, under $3) was locked on 2026-09-22 for the next "
            "set. It has not been run on a new set yet, so it has **no fair result**."
            + (f" Next event: {w['name']} (`{w['code']}`), released {w['released']}. The list counts only if it is "
               "frozen, from pre-release prices and rules text, before the outcome window; score about 5 weeks "
               "after release." if w else ""), ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizon", type=int, default=STUDY_HORIZON, help="days from verdict to outcome")
    ap.add_argument("--db", type=Path, default=universe.UNIVERSE, help="price history (opened read-only)")
    args = ap.parse_args()

    fp = fingerprint()
    if fp != RULES["fingerprint"]:
        sys.exit(f"outlook.py/signals.py fingerprint {fp} != locked {RULES['fingerprint']}: "
                 "these are new rules; lock them in RULES before a fair replay means anything")
    db = sqlite3.connect(f"file:{args.db.as_posix()}?mode=ro", uri=True)
    prices_to = db.execute("SELECT max(day) FROM prices").fetchone()[0]
    cards = load_cards(db)

    cutoff, h = date.fromisoformat(RULES["cutoff"]), args.horizon
    as_of_dates, d = [], cutoff
    while d + timedelta(days=h) <= date.fromisoformat(prices_to):
        as_of_dates.append(str(d))
        d += timedelta(days=STEP_DAYS)
    runs = []
    for a in as_of_dates:
        end = str(date.fromisoformat(a) + timedelta(days=h))
        rows, unpriced = verdicts(cards, a, end)
        runs.append({"as_of": a, "end": end, "unpriced": unpriced, "score": score(rows), "rows": rows})

    today = str(date.today())
    doc = {"run_date": today, "rules": RULES, "universe": UNIVERSE, "horizon": h, "prices_to": prices_to,
           "as_of_dates": as_of_dates, "first_due": str(cutoff + timedelta(days=h)),
           "watch": next_watch_event(), "runs": runs}
    REPORTS.mkdir(exist_ok=True)
    stem = REPORTS / f"fair-replay-{today}-h{h}"
    stem.with_suffix(".json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    stem.with_suffix(".md").write_text(markdown(doc), encoding="utf-8")
    print(markdown(doc))
    print(f"\nwrote {stem}.md and .json")


if __name__ == "__main__":
    main()
