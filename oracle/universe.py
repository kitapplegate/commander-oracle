"""The card universe: every Commander-legal paper card, one row per oracle card,
with its cheapest non-foil daily price across all printings.

    python -m oracle.universe          # (re)build cards + seed ~90 days of price history

Inputs (data/raw/):
  AllPrintings.sqlite  https://mtgjson.com/api/v5/AllPrintings.sqlite.xz  (fetched by oracle.daily)
  AllPrices.json.gz    https://mtgjson.com/api/v5/AllPrices.json.gz       (only needed to seed history)

data/universe.sqlite tables:
  cards      one row per oracle card (replaced on every card refresh)
  printings  uuid -> oracle_id (replaced on every card refresh)
  prices     oracle_id, day, cheapest price; append-only, never wiped
  runs       one row per daily pipeline run (see oracle.daily)
"""
from __future__ import annotations

import gzip
import json
import sqlite3
import sys
from collections import defaultdict
from typing import Iterable

import ijson

from .sources import ALL_PRICES, DATA

sys.stdout.reconfigure(encoding="utf-8")

PRINTINGS = DATA / "raw" / "AllPrintings.sqlite"
UNIVERSE = DATA / "universe.sqlite"
RARITY_RANK = {"common": 0, "uncommon": 1, "rare": 2, "mythic": 3, "special": 2, "bonus": 2}

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (oracle_id TEXT PRIMARY KEY, name TEXT, type TEXT, text TEXT, keywords TEXT,
                                  subtypes TEXT, color_identity TEXT, mana_value REAL, max_rarity INTEGER,
                                  first_release TEXT, last_release TEXT, sets TEXT);
CREATE TABLE IF NOT EXISTS printings (uuid TEXT PRIMARY KEY, oracle_id TEXT);
CREATE TABLE IF NOT EXISTS prices (oracle_id TEXT, day TEXT, price REAL, PRIMARY KEY (oracle_id, day));
CREATE TABLE IF NOT EXISTS runs (started TEXT, price_day TEXT, status TEXT, cards_priced INTEGER,
                                 unknown_uuids INTEGER, cards_refreshed INTEGER, seconds REAL, note TEXT);
"""


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(UNIVERSE)
    db.executescript(SCHEMA)
    return db


def load_printings() -> tuple[dict[str, dict], dict[str, str]]:
    """Group paper, Commander-legal printings by oracle id."""
    src = sqlite3.connect(PRINTINGS)
    rows = src.execute("""
        SELECT c.uuid, i.scryfallOracleId, c.name, c.type, c.text, c.keywords, c.subtypes,
               c.colorIdentity, c.manaValue, c.rarity, s.releaseDate, c.setCode, c.side
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
    for (uuid, oid, name, typ, text, kw, subtypes, ci, mv, rarity, released, set_code, side) in rows:
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


def refresh_cards(db: sqlite3.Connection) -> int:
    """Replace cards + printings from AllPrintings.sqlite. Prices are untouched."""
    cards, uuid_to_oracle = load_printings()
    with db:
        db.execute("DELETE FROM cards")
        db.execute("DELETE FROM printings")
        db.executemany("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
            (c["oracle_id"], c["name"], c["type"], c["text"], c["keywords"], c["subtypes"], c["color_identity"],
             c["mana_value"], c["max_rarity"], c["first_release"], c["last_release"], json.dumps(sorted(c["sets"])))
            for c in cards.values()])
        db.executemany("INSERT INTO printings VALUES (?,?)", uuid_to_oracle.items())
    return len(cards)


def uuid_map(db: sqlite3.Connection) -> dict[str, str]:
    return dict(db.execute("SELECT uuid, oracle_id FROM printings"))


def cheapest_daily(items: Iterable[tuple[str, dict]], uuid_to_oracle: dict[str, str]) -> tuple[dict, int]:
    """(uuid, prices) pairs -> ({oracle_id: {day: cheapest TCGplayer non-foil retail}}, unknown uuid count).
    Unknown = has a TCGplayer non-foil price but isn't in our printings map (new set, or not Commander-legal)."""
    out: dict[str, dict[str, float]] = defaultdict(dict)
    unknown = 0
    for uuid, prices in items:
        normal = prices.get("paper", {}).get("tcgplayer", {}).get("retail", {}).get("normal", {})
        oid = uuid_to_oracle.get(uuid)
        if not oid:
            unknown += bool(normal)
            continue
        day_prices = out[oid]
        for day, p in normal.items():
            p = float(p)
            if p > 0 and (day not in day_prices or p < day_prices[day]):
                day_prices[day] = p
    return {oid: days for oid, days in out.items() if days}, unknown


def upsert_prices(db: sqlite3.Connection, prices: dict[str, dict[str, float]]) -> int:
    rows = [(oid, d, p) for oid, days in prices.items() for d, p in days.items()]
    with db:
        db.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?)", rows)
    return len(rows)


def main() -> None:
    db = connect()
    n = refresh_cards(db)
    print(f"{n} Commander-legal paper cards")
    with gzip.open(ALL_PRICES, "rb") as f:
        prices, unknown = cheapest_daily(ijson.kvitems(f, "data"), uuid_map(db))
    rows = upsert_prices(db, prices)
    lo, hi, days = db.execute("SELECT MIN(day), MAX(day), COUNT(DISTINCT day) FROM prices").fetchone()
    print(f"seeded {rows:,} price rows ({unknown} unmapped printings); history {lo} -> {hi} ({days} days)")


if __name__ == "__main__":
    main()
