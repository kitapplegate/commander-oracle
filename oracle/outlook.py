"""Combine Jev's judgments with price/EDHREC facts into a buy/hold/sell outlook.

These weights are a starting guess, NOT validated. SPEC principle 3: nothing
gets trusted until the backtest against a previous set says it earns its weight.
"""
from __future__ import annotations

DEMAND_WEIGHTS = {
    "breadth": 0.30,
    "power": 0.20,
    "commander_draw": 0.15,
    "edh_adoption": 0.35,
}
SET_LOCKED_PENALTY = 0.15
EDH_FULL_MARKS = 5.0  # inclusion % at which EDHREC adoption scores 1.0

MIN_SELL_PRICE = 2.0  # below this, selling isn't worth the postage


def demand(card: dict) -> float:
    j = card["jev"]
    edh = min((card.get("edh_inclusion") or 0) / EDH_FULL_MARKS, 1.0)
    parts = {"breadth": j["breadth"], "power": j["power"], "commander_draw": j["commander_draw"],
             "edh_adoption": edh}
    raw = sum(DEMAND_WEIGHTS[k] * v for k, v in parts.items()) - SET_LOCKED_PENALTY * j["set_locked"]
    return round(max(0.0, min(1.0, raw)), 3)


def outlook(card: dict) -> dict:
    d = demand(card)
    j = card["jev"]
    price = card.get("price") or 0
    wk = card.get("change_7d") or 0
    off_peak = card.get("off_peak") or 0
    bl = card.get("buylist_ratio")

    reasons = []
    if j["breadth"] >= 0.7:
        reasons.append("Fits a wide range of Commander decks")
    elif j["breadth"] <= 0.3:
        reasons.append("Narrow: only a few decks want it")
    if j["commander_draw"] >= 0.6:
        reasons.append("Players will build decks around it as a commander")
    if j["set_locked"] >= 0.6:
        reasons.append("Leans on this set's mechanics, which caps long-term demand")
    if (card.get("edh_inclusion") or 0) >= 3:
        reasons.append(f"Already in {card['edh_inclusion']}% of eligible EDHREC decks")
    if off_peak <= -60:
        # Only call it the preorder peak when our price history actually covers preorders.
        since = "its preorder peak" if card.get("peak_is_preorder") else "its 90-day high"
        reasons.append(f"Down {abs(off_peak):.0f}% from {since}")
    if wk >= 5:
        reasons.append(f"Up {wk:.0f}% this week")
    elif wk <= -10:
        reasons.append(f"Still sliding: {wk:.0f}% this week")
    if bl is not None and bl >= 0.6:
        reasons.append("Dealers are paying a strong buylist price")

    stabilizing = wk >= -5
    if d >= 0.55 and off_peak <= -50 and stabilizing:
        verdict = "buy"
    elif d < 0.35 and price >= MIN_SELL_PRICE:
        verdict = "sell"
    elif d < 0.45 and wk <= -10 and price >= MIN_SELL_PRICE:
        verdict = "sell"
    else:
        verdict = "hold"

    return {"verdict": verdict, "demand": d, "reasons": reasons}
