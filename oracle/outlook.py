"""Buy/hold/sell for a card, from price behavior that was checked against real outcomes.

The rules come from the 2026-09-22 study of the site's cards (every card, every week
of our price history, next-14-day price; rules chosen on early dates and checked on
later ones). What held up:
  - weeks 2-4 after release are the post-release crash: almost everything falls
  - new cards snap back: a 10%+ drop in a week tends to rebound, a 10%+ jump that
    leaves the card well above its low tends to give it back
  - build-around commanders (Jev's commander_draw) drift down: a warning, not a plus
The demand score (Jev + EDHREC) did not predict 14-day prices, so it no longer picks
the verdict; it stays as the site's "Commander demand" meter. oracle.replay re-scores
these rules every week.
"""
from __future__ import annotations

from datetime import date

DEMAND_WEIGHTS = {
    "breadth": 0.30,
    "power": 0.20,
    "commander_draw": 0.15,
    "edh_adoption": 0.35,
}
SET_LOCKED_PENALTY = 0.15
EDH_FULL_MARKS = 5.0  # inclusion % at which EDHREC adoption scores 1.0

MIN_SELL_PRICE = 2.0   # below this, selling isn't worth the postage
MIN_BUY_PRICE = 0.50   # the study ignored cheaper cards: a dime is a 20% move
CRASH_DAYS = (14, 28)  # days after release when new cards reliably fall
BUY_AFTER_DAYS = 28    # never call Buy before the crash window is over
DIP, SPIKE = -10, 10   # this week's move, %
WELL_OFF_LOW = 25      # % above the 90-day low


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
    off_low = card.get("off_low") or 0
    off_peak = card.get("off_peak") or 0
    bl = card.get("buylist_ratio")
    as_of = card.get("as_of")
    age = (date.fromisoformat(as_of) - date.fromisoformat(card["released"])).days if as_of else 999

    in_crash = CRASH_DAYS[0] <= age < CRASH_DAYS[1]
    spiked_high = wk >= SPIKE and off_low >= WELL_OFF_LOW
    if price >= MIN_SELL_PRICE and (in_crash or spiked_high):
        verdict = "sell"
    elif age >= BUY_AFTER_DAYS and wk <= DIP and price >= MIN_BUY_PRICE:
        verdict = "buy"
    else:
        verdict = "hold"

    reasons = []
    if in_crash:
        reasons.append(f"{age} days after release: weeks 2 to 4 are when new cards crash")
    elif age < CRASH_DAYS[0]:
        reasons.append("Just released: the post-release crash usually starts in week 2")
    if wk <= DIP:
        reasons.append(f"Dropped {abs(wk):.0f}% this week: new cards tend to bounce back after a drop like that")
    elif spiked_high:
        reasons.append(f"Up {wk:.0f}% this week and {off_low:.0f}% above its low: spikes like that tend to fade")
    elif wk >= 5:
        reasons.append(f"Up {wk:.0f}% this week")
    if j["commander_draw"] >= 0.5:
        reasons.append("Jev expects players to build around it; so far those cards have drifted down after the hype")
    if off_peak <= -60:
        # Only call it the preorder peak when our price history actually covers preorders.
        since = "its preorder peak" if card.get("peak_is_preorder") else "its 90-day high"
        reasons.append(f"Down {abs(off_peak):.0f}% from {since}")
    if j["breadth"] >= 0.7:
        reasons.append("Fits a wide range of Commander decks")
    if (card.get("edh_inclusion") or 0) >= 3:
        reasons.append(f"Already in {card['edh_inclusion']}% of eligible EDHREC decks")
    if bl is not None and bl >= 0.6:
        reasons.append("Dealers are paying a strong buylist price")

    return {"verdict": verdict, "demand": d, "reasons": reasons}
