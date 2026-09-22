"""Exploration on the Hobbit backtest: can pre-release information sharpen Jev's
per-card signal? EXPLORATORY: every idea tried here is reported, and whatever
looks best is only a hypothesis until it is locked in and tested on the next set.

    python -m oracle.explore

Uses cached Jev answers (data/pair_cache.json, data/jev_cache.json). The Hobbit
Commander-deck cards (HOC) aren't in the site's card list, so the first run asks
Jev the same four card questions about them, with the same card fields (read from
local AllPrintings), and caches the answers in data/jev_newcards.json.
Nothing here may use prices from after the event as an input; the
older card's baseline price (before preorders) is the only market number allowed.

Ideas, fixed before running:
  1. link count     how many new Hobbit cards Jev linked to the older card (synergy >= 0.5)
  2. played partner best link weighted by how likely players are to build around the
                    new card (Jev's price-blind commander_draw answer for that card)
  3. price level    the older card's baseline price

Writes data/explore_hob.json for the website's Jev page.
"""
from __future__ import annotations

import json
import sqlite3
import statistics
import sys

from scipy.stats import spearmanr

from . import backtest, candidates, jev, pair_jev, universe
from .sources import DATA

sys.stdout.reconfigure(encoding="utf-8")

SITE_CARDS = DATA / "cards.json"
JEV_CARDS = DATA / "jev_cache.json"
NEW_CARD_CACHE = DATA / "jev_newcards.json"
OUT = DATA / "explore_hob.json"


def _card_fields(card: dict) -> dict:
    """The fields jev.judge_all reads (as the site's Scryfall data has them), from local AllPrintings."""
    db = sqlite3.connect(universe.PRINTINGS)
    uuid = db.execute("""SELECT c.uuid FROM cards c JOIN cardIdentifiers i ON i.uuid = c.uuid
                         WHERE i.scryfallOracleId = ? ORDER BY c.setCode = 'HOC' DESC LIMIT 1""",
                      (card["oracle_id"],)).fetchone()[0]
    # Faces of one printing share its scryfallId; side orders them a, b.
    faces = db.execute("""SELECT c.name, c.manaCost, c.rarity, c.type, c.text, c.colorIdentity FROM cards c
                          JOIN cardIdentifiers i ON i.uuid = c.uuid
                          WHERE i.scryfallId = (SELECT scryfallId FROM cardIdentifiers WHERE uuid = ?)
                          ORDER BY c.side""", (uuid,)).fetchall()
    name, mana, rarity, _, _, colors = faces[0]
    return {"name": name, "mana_cost": mana or "", "rarity": rarity,
            "type_line": " // ".join(f[3] for f in faces), "oracle_text": "\n//\n".join(f[4] or "" for f in faces),
            "color_identity": [x.strip() for x in (colors or "").split(",") if x.strip()]}


def new_card_judgments(new_cards: list[dict]) -> dict[str, dict]:
    """oracle_id -> Jev card judgment, for every new Hobbit card."""
    site = {c["name"]: c["id"] for c in json.loads(SITE_CARDS.read_text(encoding="utf-8"))["cards"]}
    judged = json.loads(JEV_CARDS.read_text(encoding="utf-8"))["cards"]
    extra = json.loads(NEW_CARD_CACHE.read_text(encoding="utf-8")) if NEW_CARD_CACHE.exists() else {}
    out, todo = {}, []
    for c in new_cards:
        if c["name"] in site and site[c["name"]] in judged:
            out[c["oracle_id"]] = judged[site[c["name"]]]
        elif c["oracle_id"] in extra:
            out[c["oracle_id"]] = extra[c["oracle_id"]]
        else:
            todo.append(c)
    if todo:
        print(f"asking Jev about {len(todo)} new card(s) missing from the site's card list...")
        fetched = [_card_fields(c) for c in todo]
        for c, judgment in zip(todo, jev.judge_all(fetched)):
            extra[c["oracle_id"]] = out[c["oracle_id"]] = judgment
        NEW_CARD_CACHE.write_text(json.dumps(extra, indent=1), encoding="utf-8")
        print(f"  input tokens: {sum(extra[c['oracle_id']]['tokens'] for c in todo):,}")
    return out


def share(changes: list[float]) -> dict:
    return {"n": len(changes),
            "share_up_25": round(sum(x >= 0.25 for x in changes) / len(changes) * 100, 1) if changes else None,
            "median_change": round(statistics.median(changes) * 100, 1) if changes else None}


def bucketed(cards: list[dict], key, edges: list[tuple[float, float, str]]) -> list[dict]:
    return [{"label": label, **share([c["change"] for c in cards if lo <= key(c) < hi])}
            for lo, hi, label in edges]


def main() -> None:
    db = sqlite3.connect(backtest.UNIVERSE)
    new_cards, pool = backtest.load(db)
    cand = candidates.find_candidates(new_cards, pool, k=backtest.K)
    pairs = json.loads(backtest.PAIR_CACHE.read_text())["pairs"]
    missing = [f"{n}|{o}" for n, olds in cand.items() for o, _ in olds if f"{n}|{o}" not in pairs]
    if missing:
        sys.exit(f"{len(missing)} pairs not in the cache; run python -m oracle.backtest first")
    jev_cards = new_card_judgments(new_cards)
    names = {c["oracle_id"]: c["name"] for c in new_cards}

    links: dict[str, list[dict]] = {}
    for n, olds in cand.items():
        for o, _ in olds:
            links.setdefault(o, []).append({**pairs[f"{n}|{o}"], "partner": n,
                                            "draw": jev_cards[n]["commander_draw"]})
    for c in pool:
        ls = links.get(c["oracle_id"])
        if not ls:
            c["group"] = "market"
            continue
        best = max(ls, key=lambda r: r["synergy"])
        c["best"] = best["synergy"]
        c["best_link"] = best
        c["group"] = "linked" if best["synergy"] >= backtest.LINK_THRESHOLD else "text_only"
        c["link_count"] = sum(r["synergy"] >= backtest.LINK_THRESHOLD for r in ls)
        c["played"] = max(r["synergy"] * r["draw"] for r in ls)

    # Guard: the groups must match the published backtest exactly before anything new counts.
    published = {g["group"]: g for g in json.loads(backtest.OUT.read_text(encoding="utf-8"))["groups"]}
    groups = {g: [c for c in pool if c["group"] == g] for g in ("market", "text_only", "linked")}
    for key, label in (("market", "market (not a candidate)"), ("text_only", "text match, Jev said weak"),
                       ("linked", "Jev-linked (real synergy+)")):
        mine = backtest.summarize(label, groups[key])
        if mine != published[label]:
            sys.exit(f"does not reproduce the backtest for {label}: {mine} vs {published[label]}")
    print("reproduces the published backtest groups exactly")

    cands = groups["text_only"] + groups["linked"]
    linked = groups["linked"]
    market = backtest.summarize("market", groups["market"])

    def rho(key) -> float:
        return round(float(spearmanr([key(c) for c in cands], [c["change"] for c in cands])[0]), 3)

    ideas = [
        {"key": "best", "name": "Jev's best link (today)", "rho": rho(lambda c: c["best"]),
         "buckets": bucketed(cands, lambda c: c["best"],
                             [(0, 0.5, "Weak"), (0.5, 0.6, "Real"), (0.6, 1.01, "Strong")])},
        {"key": "link_count", "name": "How many new cards it links to", "rho": rho(lambda c: c["link_count"]),
         "buckets": bucketed(cands, lambda c: c["link_count"],
                             [(0, 1, "0"), (1, 2, "1"), (2, 4, "2-3"), (4, 999, "4+")])},
        {"key": "played", "name": "Best link x will people build the new card",
         "rho": rho(lambda c: c["played"]),
         "buckets": bucketed(cands, lambda c: c["played"],
                             [(0, 0.1, "Low"), (0.1, 0.25, "Some"), (0.25, 0.5, "High"), (0.5, 9, "Very high")])},
        {"key": "base", "name": "Price before preorders", "rho": rho(lambda c: c["base"]),
         "buckets": bucketed(cands, lambda c: c["base"],
                             [(0, 1, "Under $1"), (1, 3, "$1-3"), (3, 10, "$3-10"), (10, 1e9, "$10+")])},
        {"key": "base_linked", "name": "Price before preorders, Jev-linked cards only",
         "rho": round(float(spearmanr([c["base"] for c in linked], [c["change"] for c in linked])[0]), 3),
         "buckets": bucketed(linked, lambda c: c["base"],
                             [(0, 1, "Under $1"), (1, 3, "$1-3"), (3, 10, "$3-10"), (10, 1e9, "$10+")])},
    ]

    print(f"\nmarket: {market['share_up_25']}% rose 25%+ (n={market['n']})")
    for idea in ideas:
        print(f"\n{idea['name']}  (Spearman rho vs change = {idea['rho']})")
        for b in idea["buckets"]:
            print(f"  {b['label']:10} n={b['n']:4}  up25%={b['share_up_25']}  median={b['median_change']}")

    # Control: cheap cards rise more everywhere, so compare Jev-linked to the market at the same price.
    price_bands = [(0, 1, "Under $1"), (1, 3, "$1-3"), (3, 10, "$3-10"), (10, 1e9, "$10+")]
    by_price = [{"label": label,
                 "market": share([c["change"] for c in groups["market"] if lo <= c["base"] < hi]),
                 "linked": share([c["change"] for c in linked if lo <= c["base"] < hi])}
                for lo, hi, label in price_bands]
    # Combinations of the ideas above. Tuned on this one event, so expect them to shrink next time.
    under3_market = share([c["change"] for c in groups["market"] if c["base"] < 3])
    combos = [{"name": name, **share([c["change"] for c in linked if f(c)])} for name, f in (
        ("Jev-linked", lambda c: True),
        ("Jev-linked, links to 2+ new cards", lambda c: c["link_count"] >= 2),
        ("Jev-linked, under $3", lambda c: c["base"] < 3),
        ("Jev-linked, links to 2+ new cards, under $3", lambda c: c["link_count"] >= 2 and c["base"] < 3),
    )]
    print(f"\nmarket under $3: {under3_market}")
    for row in combos:
        print(f"  {row['name']:45} n={row['n']:4}  up25%={row['share_up_25']}")

    # One hit and one miss, to show what a single Jev judgment looks like.
    def example(c: dict) -> dict:
        b = c["best_link"]
        return {"older": c["name"], "new": names[b["partner"]], "rung": round(b["synergy"] * 4),
                "confidence": b["synergy_conf"], "combo": b["combo"], "base": round(c["base"], 2),
                "after": round(c["after"], 2), "change": round(c["change"], 4), "link_count": c["link_count"],
                "new_card_build_around": jev_cards[b["partner"]]["commander_draw"]}
    rank = lambda c: (c["best"], c["best_link"]["synergy_conf"])
    hit = max((c for c in linked if c["change"] >= 0.25), key=rank)
    miss = max((c for c in linked if c["change"] < 0), key=rank)

    OUT.write_text(json.dumps({
        "event": "The Hobbit release", "market": market, "candidates": len(cands), "linked": len(linked),
        "new_cards": len(new_cards), "pairs": sum(len(v) for v in cand.values()),
        "ideas": ideas, "by_price": by_price, "under3_market": under3_market, "combos": combos,
        "overlap": {"four_plus_links": sum(c.get("link_count", 0) >= 4 for c in pool),
                    "very_high_played": sum(c.get("played", 0) >= 0.5 for c in pool),
                    "both": sum(c.get("link_count", 0) >= 4 and c.get("played", 0) >= 0.5 for c in pool)},
        "ladder": pair_jev.QUESTIONS["synergy"].criteria,
        "examples": {"hit": example(hit), "miss": example(miss)},
    }, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
