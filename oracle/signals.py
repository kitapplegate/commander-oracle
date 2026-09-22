"""Pure price math. No network, no model: easy to test and to re-weight."""
from __future__ import annotations

from datetime import date, timedelta


def _price_on_or_before(points: list[tuple[str, float]], day: str) -> float | None:
    best = None
    for d, p in points:
        if d <= day:
            best = p
        else:
            break
    return best


def pct(new: float | None, old: float | None) -> float | None:
    if new is None or not old:
        return None
    return round((new - old) / old * 100, 1)


def price_signals(retail: list[tuple[str, float]], bl_now: float | None = None,
                  ck_now: float | None = None) -> dict:
    """retail: sorted (day, price) points. bl_now/ck_now: today's Card Kingdom buylist and retail."""
    if not retail:
        return {"price": None, "history": []}
    last_day, price = retail[-1]
    ago = lambda n: str(date.fromisoformat(last_day) - timedelta(days=n))
    peak_day, peak = max(retail, key=lambda x: x[1])
    return {
        "price": price,
        "as_of": last_day,
        "change_7d": pct(price, _price_on_or_before(retail, ago(7))),
        "change_30d": pct(price, _price_on_or_before(retail, ago(30))),
        "peak": peak,
        "peak_day": peak_day,
        "off_peak": pct(price, peak),
        # Card Kingdom's buylist as a share of its own retail: how badly a dealer
        # wants the card. Around 0.5+ is strong demand; low means they're stocked up.
        "buylist_ratio": round(bl_now / ck_now, 2) if bl_now and ck_now else None,
        "history": [[d, p] for d, p in retail],
    }


def commander_signals(edh: dict | None) -> dict:
    if not edh or not edh.get("potential_decks"):
        return {"edh_decks": None, "edh_inclusion": None}
    return {
        "edh_decks": edh["num_decks"],
        "edh_inclusion": round(edh["num_decks"] / edh["potential_decks"] * 100, 2),
    }
