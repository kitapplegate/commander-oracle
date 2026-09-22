"""Commander judgments from Jev (TypeSafe System One).

Jev reads only the card itself: name, type, cost, rules text. Prices and EDHREC
counts stay out of its state on purpose. Those are facts code already has, and
keeping them out means each judgment is an independent signal we can backtest
against price outcomes, not an echo of the numbers.
"""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, Noul, Score

load_dotenv()

CONCURRENCY = 8

QUESTIONS = {
    "breadth": Score(
        instructions=(
            "In the Commander format, how many different kinds of decks would want to play the card "
            "described in `card`? Judge from its rules text: effects that any deck can use (ramp, card "
            "draw, removal, protection, mana fixing) fit many decks; effects that need a specific creature "
            "type, mechanic, or strategy fit few."
        ),
        criteria=[
            "Only a deck built around this exact card's narrow mechanic or creature type would play it",
            "Fits one specific archetype or tribe, and is played there but rarely elsewhere",
            "Fits several common strategies, such as tokens, counters, artifacts, or spellslinger",
            "Useful in most decks of its colors regardless of strategy",
            "A staple-style effect that nearly every deck in its colors would consider",
        ],
    ),
    "power": Score(
        instructions=(
            "How strong is the card described in `card` for casual-to-focused Commander play, weighing "
            "its effect against its mana cost and how quickly it affects the game?"
        ),
        criteria=[
            "Too weak or too expensive to make a Commander deck even when on-theme",
            "Playable filler that gets replaced once the owner upgrades the deck",
            "A solid card that stays in the deck after upgrades",
            "A strong card that players notice at the table and that often wins or swings games",
            "A card with an effect so efficient or unique that competitive players seek it out",
        ],
    ),
    "commander_draw": Noul(
        instructions=(
            "The card described in `card` can be a Commander deck's commander (a legendary creature, or a "
            "card whose text says it can be your commander), and its abilities give a clear, appealing "
            "strategy that players would build a whole deck around."
        ),
    ),
    "set_locked": Noul(
        instructions=(
            "The card described in `card` depends on a mechanic, keyword, or creature type that mostly "
            "appears in its own set or in a single franchise's cards, so it is weak outside decks built "
            "from that set."
        ),
    ),
}


def _state(card: dict) -> dict:
    return {"card": {
        "name": card["name"],
        "type_line": card["type_line"],
        "mana_cost": card["mana_cost"],
        "color_identity": "".join(card["color_identity"]) or "colorless",
        "rarity": card["rarity"],
        "rules_text": card["oracle_text"],
    }}


def _norm(score) -> float:
    return round(score.score / max(int(k) for k in score.legend), 3)


async def _judge_one(client: AsyncTypeSafeClient, sem: asyncio.Semaphore, card: dict) -> dict:
    async with sem:
        r = await client.system_one(state=_state(card), questions=QUESTIONS)
    return {
        "breadth": _norm(r.scores["breadth"]),
        "breadth_conf": round(r.scores["breadth"].confidence, 3),
        "power": _norm(r.scores["power"]),
        "power_conf": round(r.scores["power"].confidence, 3),
        "commander_draw": round(r.nouls["commander_draw"].noul, 3),
        "set_locked": round(r.nouls["set_locked"].noul, 3),
        "tokens": r.usage.input_tokens or 0,
    }


async def _judge_all(cards: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with AsyncTypeSafeClient() as client:
        return await asyncio.gather(*(_judge_one(client, sem, c) for c in cards))


def judge_all(cards: list[dict]) -> list[dict]:
    return asyncio.run(_judge_all(cards))
