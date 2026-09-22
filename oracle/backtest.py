"""Event backtest: did the older cards Jev linked to a new set actually rise?

    python -m oracle.backtest

The Hobbit (HOB + new cards in HOC) released 2026-08-14. The measurement rules
are fixed up front, before looking at any results:

  baseline price  mean of 2026-06-23 .. 2026-07-06  (before Hobbit preorders appeared on Aug 2)
  after price     mean of 2026-09-08 .. 2026-09-21  (3-5 weeks after release)
  peak            max of 2026-08-01 .. 2026-09-21, relative to baseline
  older pool      existed before 2026-06-15, not common-only, NOT reprinted since
                  2026-06-15 (reprints fall for unrelated reasons), baseline >= $0.50

Groups compared:
  market        pool cards the candidate finder did not pick
  text-only     candidates Jev scored below "real synergy"
  Jev-linked    candidates Jev scored at "real synergy" or higher
"""
from __future__ import annotations

import json
import random
import sqlite3
import statistics
import sys

from scipy.stats import spearmanr

from . import candidates, pair_jev
from .sources import DATA

sys.stdout.reconfigure(encoding="utf-8")

UNIVERSE = DATA / "universe.sqlite"
PAIR_CACHE = DATA / "pair_cache.json"
OUT = DATA / "backtest_hob.json"

NEW_SETS = ("HOB", "HOC")
RELEASE = "2026-08-14"
BASE = ("2026-06-23", "2026-07-06")
AFTER = ("2026-09-08", "2026-09-21")
PEAK = ("2026-08-01", "2026-09-21")
POOL_CUTOFF = "2026-06-15"
MIN_BASE_PRICE = 0.50
K = 30
LINK_THRESHOLD = 0.5  # normalized synergy: level 2 of 4, "real synergy"


def _rows(db, sql, *args) -> list[dict]:
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur]


def load(db) -> tuple[list[dict], list[dict]]:
    new_cards = [c for c in _rows(db, "SELECT * FROM cards WHERE first_release = ? AND max_rarity >= 2", RELEASE)
                 if any(s in json.loads(c["sets"]) for s in NEW_SETS)]
    pool = _rows(db, f"""
        SELECT c.*,
          (SELECT AVG(price) FROM prices p WHERE p.oracle_id = c.oracle_id AND day BETWEEN '{BASE[0]}' AND '{BASE[1]}') AS base,
          (SELECT AVG(price) FROM prices p WHERE p.oracle_id = c.oracle_id AND day BETWEEN '{AFTER[0]}' AND '{AFTER[1]}') AS after,
          (SELECT MAX(price) FROM prices p WHERE p.oracle_id = c.oracle_id AND day BETWEEN '{PEAK[0]}' AND '{PEAK[1]}') AS peak
        FROM cards c
        WHERE first_release < ? AND last_release < ? AND max_rarity >= 1""", POOL_CUTOFF, POOL_CUTOFF)
    pool = [c for c in pool if c["base"] and c["after"] and c["base"] >= MIN_BASE_PRICE]
    for c in pool:
        c["change"] = c["after"] / c["base"] - 1
        c["peak_change"] = c["peak"] / c["base"] - 1
    return new_cards, pool


def judge(new_cards, pool, cand) -> dict[str, dict]:
    cache = json.loads(PAIR_CACHE.read_text()) if PAIR_CACHE.exists() else {}
    if cache.get("version") != pair_jev.PAIR_VERSION:
        cache = {"version": pair_jev.PAIR_VERSION, "pairs": {}}
    by_id = {c["oracle_id"]: c for c in pool + new_cards}
    todo = [(n, o) for n, olds in cand.items() for o, _ in olds if f"{n}|{o}" not in cache["pairs"]]
    if todo:
        print(f"asking Jev about {len(todo)} pairs...")
        results = pair_jev.judge_pairs([(by_id[n], by_id[o]) for n, o in todo])
        for (n, o), r in zip(todo, results):
            cache["pairs"][f"{n}|{o}"] = r
        PAIR_CACHE.write_text(json.dumps(cache))
        print(f"  input tokens: {sum(r['tokens'] for r in results):,}")
    return cache["pairs"]


def summarize(name: str, cards: list[dict]) -> dict:
    ch = [c["change"] for c in cards]
    return {"group": name, "n": len(cards),
            "median_change": round(statistics.median(ch) * 100, 1) if ch else None,
            "mean_change": round(statistics.fmean(ch) * 100, 1) if ch else None,
            "share_up_25": round(sum(x >= 0.25 for x in ch) / len(ch) * 100, 1) if ch else None,
            "share_peak_50": round(sum(c["peak_change"] >= 0.5 for c in cards) / len(cards) * 100, 1) if cards else None}


def permutation_p(a: list[float], b: list[float], n: int = 10000, seed: int = 7) -> float:
    """One-sided: how often does a random split show a median gap at least this large?"""
    rng = random.Random(seed)
    observed = statistics.median(a) - statistics.median(b)
    both, hits = a + b, 0
    for _ in range(n):
        rng.shuffle(both)
        if statistics.median(both[: len(a)]) - statistics.median(both[len(a):]) >= observed:
            hits += 1
    return hits / n


def main() -> None:
    db = sqlite3.connect(UNIVERSE)
    new_cards, pool = load(db)
    print(f"{len(new_cards)} new Hobbit rares/mythics; older pool {len(pool)} cards")
    cand = candidates.find_candidates(new_cards, pool, k=K)
    pairs = judge(new_cards, pool, cand)

    best: dict[str, dict] = {}
    for n, olds in cand.items():
        for o, _ in olds:
            r = pairs[f"{n}|{o}"]
            cur = best.get(o)
            if cur is None or r["synergy"] > cur["synergy"]:
                best[o] = {**r, "partner": n}
    names = {c["oracle_id"]: c["name"] for c in new_cards}

    for c in pool:
        j = best.get(c["oracle_id"])
        c["jev"] = j
        c["group"] = "market" if j is None else ("linked" if j["synergy"] >= LINK_THRESHOLD else "text_only")

    groups = {g: [c for c in pool if c["group"] == g] for g in ("market", "text_only", "linked")}
    table = [summarize("market (not a candidate)", groups["market"]),
             summarize("text match, Jev said weak", groups["text_only"]),
             summarize("Jev-linked (real synergy+)", groups["linked"])]
    cands = groups["text_only"] + groups["linked"]
    rho, rho_p = spearmanr([c["jev"]["synergy"] for c in cands], [c["change"] for c in cands])
    p_linked_vs_text = permutation_p([c["change"] for c in groups["linked"]], [c["change"] for c in groups["text_only"]])
    p_linked_vs_market = permutation_p([c["change"] for c in groups["linked"]], [c["change"] for c in groups["market"]])

    print(f"\n{'group':30} {'n':>5} {'median':>8} {'mean':>7} {'up25%':>6} {'peak50%':>8}")
    for t in table:
        print(f"{t['group']:30} {t['n']:5} {t['median_change']:7}% {t['mean_change']:6}% {t['share_up_25']:5}% {t['share_peak_50']:7}%")
    print(f"\nSpearman (Jev synergy vs price change, candidates only): rho={rho:.3f} p={rho_p:.4f}")
    print(f"permutation p, linked > text-only median: {p_linked_vs_text:.4f}")
    print(f"permutation p, linked > market median:    {p_linked_vs_market:.4f}")

    top = sorted(groups["linked"], key=lambda c: -c["jev"]["synergy"])[:20]
    print(f"\nJev's top links:")
    for c in top:
        print(f"  {c['jev']['synergy']:.2f} combo={c['jev']['combo']:.2f}  {c['name'][:34]:34} <- {names[c['jev']['partner']][:28]:28} "
              f"${c['base']:.2f} -> ${c['after']:.2f} ({c['change']*100:+.0f}%, peak {c['peak_change']*100:+.0f}%)")

    OUT.write_text(json.dumps({
        "event": {"name": "The Hobbit release", "sets": NEW_SETS, "date": RELEASE,
                  "windows": {"base": BASE, "after": AFTER, "peak": PEAK}},
        "groups": table, "spearman": {"rho": rho, "p": rho_p},
        "permutation_p": {"linked_vs_text": p_linked_vs_text, "linked_vs_market": p_linked_vs_market},
        "linked": [{"name": c["name"], "partner": names[c["jev"]["partner"]], **c["jev"],
                    "base": c["base"], "after": c["after"], "change": c["change"], "peak_change": c["peak_change"]}
                   for c in sorted(groups["linked"], key=lambda c: -c["jev"]["synergy"])],
    }, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
