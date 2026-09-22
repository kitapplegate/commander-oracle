"""Fetchers for Scryfall, MTGJSON and EDHREC. Everything is cached under data/cache
so re-runs are cheap and we stay polite to free APIs."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
CACHE = DATA / "cache"
ALL_PRICES = DATA / "raw" / "AllPrices.json.gz"
HEADERS = {"User-Agent": "commander-oracle/0.1 (personal project)", "Accept": "application/json"}


def _cached_json(path: Path, url: str, max_age_hours: float = 24) -> dict:
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600:
        return json.loads(path.read_text(encoding="utf-8"))
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    return resp.json()


def scryfall_set_cards(set_code: str) -> list[dict]:
    """All rare/mythic printings in a set, following Scryfall's pagination."""
    cards, page = [], 1
    url = f"https://api.scryfall.com/cards/search?q=set:{set_code}+(r:rare+OR+r:mythic)&unique=prints"
    while url:
        data = _cached_json(CACHE / "scryfall" / f"{set_code}-{page}.json", url)
        cards.extend(data["data"])
        url = data.get("next_page")
        page += 1
        time.sleep(0.1)  # Scryfall asks for 50-100ms between requests
    return cards


def mtgjson_uuid_map(set_code: str) -> dict[str, str]:
    """scryfallId -> MTGJSON uuid, needed to look up today's Card Kingdom prices."""
    data = _cached_json(CACHE / "mtgjson" / f"{set_code}.json",
                        f"https://mtgjson.com/api/v5/{set_code.upper()}.json", max_age_hours=24 * 7)
    return {c["identifiers"]["scryfallId"]: c["uuid"] for c in data["data"]["cards"]
            if c["identifiers"].get("scryfallId")}


def edhrec_slug(name: str) -> str:
    front = name.split(" // ")[0].lower()
    front = re.sub(r"[',.!?:]", "", front)
    return re.sub(r"[^a-z0-9]+", "-", front).strip("-")


def edhrec_card(name: str) -> dict | None:
    """Commander deck counts. None if EDHREC has no page (common for brand-new cards)."""
    slug = edhrec_slug(name)
    path = CACHE / "edhrec" / f"{slug}.json"
    if not path.exists():
        time.sleep(1.0)  # unofficial endpoint: go slow
    try:
        data = _cached_json(path, f"https://json.edhrec.com/pages/cards/{slug}.json", max_age_hours=24 * 3)
    except requests.HTTPError:
        return None
    card = data.get("container", {}).get("json_dict", {}).get("card", {})
    if not card:
        return None
    return {
        "num_decks": card.get("num_decks"),
        "potential_decks": card.get("potential_decks"),
        "salt": card.get("salt"),
        "url": f"https://edhrec.com/cards/{slug}",
    }
