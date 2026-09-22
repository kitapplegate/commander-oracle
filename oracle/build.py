"""Build data/cards.json for the newest expansions (or the set codes given).

    python -m oracle.build            # the RECENT_SETS newest expansions
    python -m oracle.build hob msh    # just these

Prices come from our own history in data/universe.sqlite (kept current by
oracle.daily), cheapest non-foil printing per card. Card Kingdom buylist/retail
come from the newest archived daily MTGJSON file. Run oracle.daily first.
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timezone

from . import daily, signals, sources, universe

sys.stdout.reconfigure(encoding="utf-8")

VARIANT_FRAMES = {"showcase", "extendedart", "inverted", "etched"}


def _is_main_printing(c: dict) -> bool:
    return (not c.get("promo") and not c.get("full_art") and c.get("border_color") == "black"
            and not VARIANT_FRAMES & set(c.get("frame_effects", [])))


def _collector_key(c: dict) -> tuple[int, str]:
    num = "".join(ch for ch in c["collector_number"] if ch.isdigit())
    return (int(num) if num else 99999, c["collector_number"])


def _oracle_id(c: dict) -> str:
    # Reversible printings carry oracle_id on their faces, not at the top level.
    return c.get("oracle_id") or c.get("card_faces", [{}])[0].get("oracle_id") or c["name"]


def main_printings(cards: list[dict]) -> list[dict]:
    # Group by oracle id, not name: a reversible variant is named "X // X".
    by_card: dict[str, list[dict]] = {}
    for c in cards:
        by_card.setdefault(_oracle_id(c), []).append(c)
    picked = []
    for prints in by_card.values():
        mains = sorted(filter(_is_main_printing, prints), key=_collector_key)
        chosen = (mains or sorted(prints, key=_collector_key))[0]
        chosen["_variant_count"] = len(prints)
        picked.append(chosen)
    return picked


def _image(c: dict) -> dict:
    uris = c.get("image_uris") or c.get("card_faces", [{}])[0].get("image_uris", {})
    return {"small": uris.get("small"), "normal": uris.get("normal"), "art": uris.get("art_crop")}


def _oracle_text(c: dict) -> str:
    if c.get("oracle_text"):
        return c["oracle_text"]
    return "\n//\n".join(f.get("oracle_text", "") for f in c.get("card_faces", []))


def _latest(vendor: dict, kind: str) -> float | None:
    points = vendor.get(kind, {}).get("normal", {})
    return float(points[max(points)]) if points else None


def _todays_prices() -> dict[str, dict]:
    """uuid -> paper prices from the newest archived AllPricesToday file."""
    files = sorted(p for p in daily.ARCHIVE.glob("????-??-??.json.gz"))
    if not files:
        sys.exit("no archived daily price file; run `python -m oracle.daily` first")
    with gzip.open(files[-1], "rb") as f:
        return {uuid: p.get("paper", {}) for uuid, p in json.load(f)["data"].items()}


def build(sets: list[dict]) -> list[dict]:
    db = universe.connect()
    if not db.execute("SELECT 1 FROM prices LIMIT 1").fetchone():
        sys.exit("price history is empty; run `python -m oracle.daily` first")
    today = _todays_prices()
    rows = []
    for s in sets:
        code = s["code"]
        cards = main_printings(sources.scryfall_set_cards(code))
        uuid_of = sources.mtgjson_uuid_map(code)
        print(f"{code}: {len(cards)} rare/mythic cards (main printings)")
        for i, c in enumerate(cards, 1):
            edh = sources.edhrec_card(c["name"])
            history = db.execute("SELECT day, price FROM prices WHERE oracle_id = ? ORDER BY day",
                                 (_oracle_id(c),)).fetchall()
            ck = today.get(uuid_of.get(c["id"], ""), {}).get("cardkingdom", {})
            rows.append({
                "id": c["id"],
                "name": c["name"],
                "set": code,
                "set_name": c["set_name"],
                "released": c["released_at"],
                "rarity": c["rarity"],
                "type_line": c.get("type_line", ""),
                "mana_cost": c.get("mana_cost") or c.get("card_faces", [{}])[0].get("mana_cost", ""),
                "color_identity": c.get("color_identity", []),
                "oracle_text": _oracle_text(c),
                "legal_commander": c.get("legalities", {}).get("commander") == "legal",
                "variants": c["_variant_count"],
                "image": _image(c),
                "scryfall_url": c.get("scryfall_uri"),
                "edhrec_url": edh["url"] if edh else None,
                **signals.commander_signals(edh),
                **signals.price_signals(history, c["released_at"], _latest(ck, "buylist"), _latest(ck, "retail")),
            })
            if i % 20 == 0:
                print(f"  {i}/{len(cards)}")
    return rows


RECENT_SETS = 5  # newest expansions shown; a new release rotates in automatically


def main() -> None:
    sets = sources.recent_expansions(RECENT_SETS)
    if sys.argv[1:]:  # explicit set codes override, e.g. `python -m oracle.build hob msh`
        wanted = [c.lower() for c in sys.argv[1:]]
        sets = [s for s in sources.recent_expansions(50) if s["code"] in wanted]
    rows = build(sets)
    out = sources.DATA / "cards.json"
    out.write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "sets": sets, "cards": rows}, separators=(",", ":")), encoding="utf-8")
    priced = [r for r in rows if r["price"] is not None]
    edh = [r for r in rows if r["edh_decks"] is not None]
    print(f"wrote {out}: {len(rows)} cards, {len(priced)} priced, {len(edh)} with EDHREC data")


if __name__ == "__main__":
    main()
