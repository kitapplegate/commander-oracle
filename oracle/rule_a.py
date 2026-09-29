"""Rule A, run forward: freeze the Watch list for a new set BEFORE it releases.

    python -m oracle.rule_a            # freeze the list for EVENT (refuses on/after release day)

Rule A was found on The Hobbit (oracle.explore) and locked on 2026-09-22:
a Jev-linked older card (synergy >= "real synergy" with a new card) that links to
2+ new cards and cost under $3 before preorders. Hobbit: 40.2% rose 25%+ (n=92) vs
17.2% of the market under $3. That was one event, found looking back; this is the
real test.

Same pipeline and pool rules as oracle.backtest, shifted to this event's dates.
Only rules text and baseline prices (from before any preorder) go in, so the
list can't lean on the outcome. The card list comes from a fresh AllPrintings in
data/raw/fra/ (new cards only get Commander legality near release), and baseline
prices from data/universe.sqlite, opened read-only, so the Hobbit backtest's
inputs stay untouched.

Writes reports/rule-a-<code>-<today>.md and .json. The committed file is the
pre-registration; scoring later reads its "pool" block and only adds prices.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from . import backtest, candidates, universe
from .sources import DATA

sys.stdout.reconfigure(encoding="utf-8")

EVENT = {
    "name": "Reality Fracture release",
    "code": "fra",
    "sets": ["FRA", "FRC"],
    "release": "2026-10-02",
    # 14 days ending the day before the first Reality Fracture card got a preorder price (Jul 20).
    # Bulk preorders started Sep 1; a few mythics were revealed from Jul 20.
    "base": ["2026-07-06", "2026-07-19"],
    # Same offsets from release as the Hobbit backtest: 25-38 days after.
    "after": ["2026-10-27", "2026-11-09"],
    "peak": ["2026-07-20", "2026-11-09"],
    # Older pool: out of its own release crash by the baseline (28+ days), and not reprinted since.
    "pool_cutoff": "2026-06-08",
}
MAX_RULE_A_BASE = 3.0
MIN_LINKS = 2
PRINTINGS = DATA / "raw" / "fra" / "AllPrintings.sqlite"
REPORTS = Path(__file__).resolve().parent.parent / "reports"


def load(prices: sqlite3.Connection) -> tuple[list[dict], list[dict], dict]:
    cards, _ = universe.load_printings(PRINTINGS)
    meta = sqlite3.connect(f"file:{PRINTINGS.as_posix()}?mode=ro", uri=True).execute(
        "SELECT date, version FROM meta").fetchone()
    new_cards, pool = [], []
    lo, hi = EVENT["base"]
    for c in cards.values():
        c["sets"] = sorted(c["sets"])
        if c["first_release"] == EVENT["release"] and c["max_rarity"] >= 2 and set(c["sets"]) & set(EVENT["sets"]):
            new_cards.append(c)
        elif (c["first_release"] < EVENT["pool_cutoff"] and c["last_release"] < EVENT["pool_cutoff"]
              and c["max_rarity"] >= 1):
            pool.append(c)
    base = dict(prices.execute("SELECT oracle_id, AVG(price) FROM prices WHERE day BETWEEN ? AND ? GROUP BY oracle_id",
                               (lo, hi)))
    for c in pool:
        c["base"] = base.get(c["oracle_id"])
    pool = [c for c in pool if c["base"] and c["base"] >= backtest.MIN_BASE_PRICE]
    return new_cards, pool, {"mtgjson_date": meta[0], "mtgjson_version": meta[1]}


def main() -> None:
    today = str(date.today())
    if today >= EVENT["release"]:
        sys.exit(f"{EVENT['name']} is out ({EVENT['release']}): a list frozen now isn't a pre-registration")
    out = REPORTS / f"rule-a-{EVENT['code']}-{today}"
    if out.with_suffix(".json").exists():
        sys.exit(f"{out}.json already exists; a frozen list is never overwritten")

    prices = sqlite3.connect(f"file:{universe.UNIVERSE.as_posix()}?mode=ro", uri=True)
    new_cards, pool, source = load(prices)
    print(f"{len(new_cards)} new {EVENT['code'].upper()} rares/mythics; older pool {len(pool)} cards")
    cand = candidates.find_candidates(new_cards, pool, k=backtest.K)
    pairs = backtest.judge(new_cards, pool, cand)
    names = {c["oracle_id"]: c["name"] for c in new_cards}

    links: dict[str, list[dict]] = {}
    for n, olds in cand.items():
        for o, _ in olds:
            links.setdefault(o, []).append({**pairs[f"{n}|{o}"], "partner": n})
    for c in pool:
        ls = links.get(c["oracle_id"])
        if not ls:
            c["group"], c["link_count"] = "market", 0
            continue
        best = max(r["synergy"] for r in ls)
        c["group"] = "linked" if best >= backtest.LINK_THRESHOLD else "text_only"
        c["link_count"] = sum(r["synergy"] >= backtest.LINK_THRESHOLD for r in ls)
        c["links"] = sorted((r for r in ls if r["synergy"] >= backtest.LINK_THRESHOLD),
                            key=lambda r: (-r["synergy"], -r["synergy_conf"]))
    watch = sorted((c for c in pool if c["group"] == "linked" and c["link_count"] >= MIN_LINKS
                    and c["base"] < MAX_RULE_A_BASE), key=lambda c: (-c["link_count"], c["name"]))
    counts = {g: sum(c["group"] == g for c in pool) for g in ("market", "text_only", "linked")}
    under3_market = sum(c["group"] == "market" and c["base"] < MAX_RULE_A_BASE for c in pool)

    frozen = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc = {
        "frozen_at": frozen, "event": EVENT, "source": source,
        "rule": {"name": "A", "locked": "2026-09-22", "link_threshold": backtest.LINK_THRESHOLD,
                 "min_links": MIN_LINKS, "max_base": MAX_RULE_A_BASE, "min_base": backtest.MIN_BASE_PRICE,
                 "k": backtest.K},
        "counts": {"new_cards": len(new_cards), "pool": len(pool), "pairs": sum(len(v) for v in cand.values()),
                   **counts, "rule_a": len(watch), "market_under_3": under3_market},
        "watch": [{"name": c["name"], "oracle_id": c["oracle_id"], "base": round(c["base"], 2),
                   "link_count": c["link_count"],
                   "links": [{"new": names[r["partner"]], "rung": round(r["synergy"] * 4),
                              "confidence": r["synergy_conf"], "combo": r["combo"]} for r in c["links"]]}
                  for c in watch],
        # Every pool card's group, fixed now: scoring only adds the after-window prices.
        "pool": {c["oracle_id"]: [c["group"], round(c["base"], 4), c["link_count"]] for c in pool},
    }
    REPORTS.mkdir(exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1), encoding="utf-8")

    e = EVENT
    md = [f"# Rule A Watch list — {e['name']} — frozen {frozen}", "",
          f"Pre-registered before {e['code'].upper()} releases on {e['release']}. Nothing here may change after this "
          "file is committed; the score is computed later from this file plus after-window prices.", "",
          "| | |", "|---|---|",
          f"| Rule | A (locked 2026-09-22 on The Hobbit): Jev-linked (best synergy ≥ {backtest.LINK_THRESHOLD}, "
          f"\"real synergy\"), links to {MIN_LINKS}+ new cards, baseline under ${MAX_RULE_A_BASE:.0f} |",
          f"| New cards | {len(new_cards)} rare/mythic cards first printed in {', '.join(e['sets'])} |",
          f"| Older pool | {len(pool)} Commander-legal cards: first printed and last reprinted before "
          f"{e['pool_cutoff']}, not common-only, baseline ≥ ${backtest.MIN_BASE_PRICE:.2f} |",
          f"| Baseline price | mean {e['base'][0]} .. {e['base'][1]}, before the first {e['code'].upper()} preorder "
          "price (Jul 20); bulk preorders began Sep 1 |",
          f"| Candidates | top {backtest.K} older cards per new card (text + tribal), "
          f"{doc['counts']['pairs']:,} pairs judged by Jev on rules text only |",
          f"| Groups | Jev-linked {counts['linked']}, text-only {counts['text_only']}, market {counts['market']} |",
          f"| Source | MTGJSON AllPrintings {source['mtgjson_version']} ({source['mtgjson_date']}) |", "",
          "## How it will be scored (fixed now)", "",
          f"- After price: mean {e['after'][0]} .. {e['after'][1]} (25-38 days after release, same as Hobbit).",
          f"- **Primary:** share of the Watch list rising 25%+ vs the market cards under ${MAX_RULE_A_BASE:.0f} "
          f"(n={under3_market}). Hobbit: 40.2% vs 17.2%.",
          "- Secondary, the backtest replication: median change and share up 25%+ for Jev-linked vs text-only vs "
          "market, permutation p for linked vs text-only.",
          "- Cards with no price in the after window are reported, not dropped silently.", "",
          f"## The list ({len(watch)} cards)", "",
          "| Card | Baseline | Links | Best links (new card, rung 0-4) |", "|---|---|---|---|"]
    md += [f"| {c['name']} | ${c['base']:.2f} | {c['link_count']} | "
           + "; ".join(f"{names[r['partner']]} ({round(r['synergy'] * 4)})" for r in c["links"][:3]) + " |"
           for c in watch]
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:24]))
    print(f"\nwrote {out}.md and .json: {len(watch)} cards on the Watch list")


if __name__ == "__main__":
    main()
