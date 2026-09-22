"""The card universe: every Commander-legal paper card, one row per oracle card,
with its cheapest non-foil daily price across all printings.

    python -m oracle.universe

Inputs (download into data/raw/):
  AllPrintings.sqlite  https://mtgjson.com/api/v5/AllPrintings.sqlite.xz  (unxz it)
  AllPrices.json.gz    https://mtgjson.com/api/v5/AllPrices.json.gz

Output: data/universe.sqlite with tables `cards` and `prices`.
"""
from __future__ import annotations

import gzip
import json
import sqlite3
import sys
from collections import defaultdict

import ijson

from .sources import ALL_PRICES, DATA

sys.stdout.reconfigure(encoding="utf-8")

PRINTINGS = DATA / "raw" / "AllPrintings.sqlite"
UNIVERSE = DATA / "universe.sqlite"
RARITY_RANK = {"common": 0, "uncommon": 1, "rare": 2, "mythic": 3, "special": 2, "bonus": 2}


def load_printings() -> tuple[dict[str, dict], dict[str, str]]:
    """Group paper, Commander-legal printings by oracle id."""
    src = sqlite3.connect(PRINTINGS)
    rows = src.execute("""
        SELECT c.uuid, i.scryfallOracleId, c.name, c.type, c.text, c.keywords, c.subtypes,
               c.colorIdentity, c.manaValue, c.rarity, s.releaseDate, c.setCode, c.side, c.faceName
        FROM cards c
        JOIN cardIdentifiers i ON i.uuid = c.uuid
        JOIN cardLegalities l ON l.uuid = c.uuid
        JOIN sets s ON s.code = c.setCode
        WHERE l.commander = 'Legal' AND c.availability LIKE '%paper%'
          AND COALESCE(c.isFunny, 0) = 0 AND COALESCE(c.isOnlineOnly, 0) = 0
          AND i.scryfallOracleId IS NOT NULL
    """)
    cards: dict[str, dict] = {}
    uuid_to_oracle: dict[str, str] = {}
    for (uuid, oid, name, typ, text, kw, subtypes, ci, mv, rarity, released, set_code, side, face) in rows:
        uuid_to_oracle[uuid] = oid
        c = cards.get(oid)
        if c is None:
            c = cards[oid] = {"oracle_id": oid, "name": name, "faces": {}, "keywords": kw or "",
                              "subtypes": subtypes or "", "color_identity": ci or "",
                              "mana_value": mv or 0, "max_rarity": 0, "first_release": released,
                              "last_release": released, "sets": set()}
        # Double-faced cards have one row per face (side a/b); keep each face once.
        c["faces"].setdefault(side or "a", (typ, text or ""))
        c["max_rarity"] = max(c["max_rarity"], RARITY_RANK.get(rarity, 0))
        c["first_release"] = min(c["first_release"], released)
        c["last_release"] = max(c["last_release"], released)
        c["sets"].add(set_code)
    for c in cards.values():
        faces = [c["faces"][k] for k in sorted(c["faces"])]
        c["type"] = " // ".join(t for t, _ in faces)
        c["text"] = "\n//\n".join(x for _, x in faces)
    return cards, uuid_to_oracle


def cheapest_daily(uuid_to_oracle: dict[str, str]) -> dict[str, dict[str, float]]:
    """oracle id -> {date: cheapest TCGplayer non-foil retail price that day}."""
    out: dict[str, dict[str, float]] = defaultdict(dict)
    with gzip.open(ALL_PRICES, "rb") as f:
        for uuid, prices in ijson.kvitems(f, "data"):
            oid = uuid_to_oracle.get(uuid)
            if not oid:
                continue
            normal = prices.get("paper", {}).get("tcgplayer", {}).get("retail", {}).get("normal", {})
            day_prices = out[oid]
            for day, p in normal.items():
                p = float(p)
                if p > 0 and (day not in day_prices or p < day_prices[day]):
                    day_prices[day] = p
    return out


def main() -> None:
    cards, uuid_to_oracle = load_printings()
    print(f"{len(cards)} Commander-legal paper cards from {len(uuid_to_oracle)} printings")
    prices = cheapest_daily(uuid_to_oracle)
    print(f"price history for {sum(1 for p in prices.values() if p)} cards")

    UNIVERSE.unlink(missing_ok=True)
    db = sqlite3.connect(UNIVERSE)
    db.executescript("""
        CREATE TABLE cards (oracle_id TEXT PRIMARY KEY, name TEXT, type TEXT, text TEXT, keywords TEXT,
                            subtypes TEXT, color_identity TEXT, mana_value REAL, max_rarity INTEGER,
                            first_release TEXT, last_release TEXT, sets TEXT);
        CREATE TABLE prices (oracle_id TEXT, day TEXT, price REAL, PRIMARY KEY (oracle_id, day));
    """)
    db.executemany("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        (c["oracle_id"], c["name"], c["type"], c["text"], c["keywords"], c["subtypes"], c["color_identity"],
         c["mana_value"], c["max_rarity"], c["first_release"], c["last_release"], json.dumps(sorted(c["sets"])))
        for c in cards.values()])
    db.executemany("INSERT INTO prices VALUES (?,?,?)",
                   ((oid, d, p) for oid, days in prices.items() for d, p in days.items()))
    db.commit()
    n_days = db.execute("SELECT MIN(day), MAX(day), COUNT(DISTINCT day) FROM prices").fetchone()
    print(f"wrote {UNIVERSE}: prices {n_days[0]} -> {n_days[1]} ({n_days[2]} days)")


if __name__ == "__main__":
    main()
