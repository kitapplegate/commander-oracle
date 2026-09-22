"""Build data/cards.json for one or more sets.

    python -m oracle.build hob
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from . import signals, sources

sys.stdout.reconfigure(encoding="utf-8")

VARIANT_FRAMES = {"showcase", "extendedart", "inverted", "etched"}


def _is_main_printing(c: dict) -> bool:
    return (not c.get("promo") and not c.get("full_art") and c.get("border_color") == "black"
            and not VARIANT_FRAMES & set(c.get("frame_effects", [])))


def _collector_key(c: dict) -> tuple[int, str]:
    num = "".join(ch for ch in c["collector_number"] if ch.isdigit())
    return (int(num) if num else 99999, c["collector_number"])


def main_printings(cards: list[dict]) -> list[dict]:
    by_name: dict[str, list[dict]] = {}
    for c in cards:
        by_name.setdefault(c["name"], []).append(c)
    picked = []
    for name, prints in by_name.items():
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


def build(set_codes: list[str]) -> list[dict]:
    rows = []
    for code in set_codes:
        cards = main_printings(sources.scryfall_set_cards(code))
        uuid_of = sources.mtgjson_uuid_map(code)
        print(f"{code}: {len(cards)} rare/mythic cards (main printings)")
        histories = sources.price_histories({uuid_of[c["id"]] for c in cards if c["id"] in uuid_of})
        for i, c in enumerate(cards, 1):
            edh = sources.edhrec_card(c["name"])
            paper = histories.get(uuid_of.get(c["id"], ""), {})
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
                **signals.price_signals(paper),
            })
            if i % 20 == 0:
                print(f"  {i}/{len(cards)}")
    return rows


def main() -> None:
    set_codes = sys.argv[1:] or ["hob"]
    rows = build(set_codes)
    out = sources.DATA / "cards.json"
    out.write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "sets": set_codes, "cards": rows}, indent=1), encoding="utf-8")
    priced = [r for r in rows if r["price"] is not None]
    edh = [r for r in rows if r["edh_decks"] is not None]
    print(f"wrote {out}: {len(rows)} cards, {len(priced)} priced, {len(edh)} with EDHREC data")


if __name__ == "__main__":
    main()
