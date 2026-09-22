"""Jev judges a (new card, existing card) pair: does the new card make the older
one more valuable in Commander? Rules text only; prices never enter the state."""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, Noul, Score

load_dotenv()

CONCURRENCY = 8
PAIR_VERSION = 1

QUESTIONS = {
    "synergy": Score(
        instructions=(
            "`new_card` was just released for Magic: The Gathering. In the Commander format, how much does "
            "`new_card` make `existing_card` more worth playing? Consider direct interactions between their rules "
            "text, shared strategies, and whether a deck led by `new_card` would want `existing_card`."
        ),
        criteria=[
            "No meaningful interaction: neither card helps the other",
            "Loose overlap: they share a theme, but neither makes the other noticeably better",
            "Real synergy: a deck built around one would happily include the other",
            "Strong synergy: the new card gives the existing card a new role or makes it a key piece of a deck",
            "Together they form a combo that wins the game or creates a repeatable, unbounded loop",
        ],
    ),
    "combo": Noul(
        instructions=(
            "`new_card` and `existing_card` together create an infinite or unbounded loop, or an interaction "
            "that wins the game on the spot, in a Commander game."
        ),
    ),
}


def _card(c: dict) -> dict:
    return {"name": c["name"], "type_line": c["type"], "color_identity": c["color_identity"] or "colorless",
            "rules_text": c["text"]}


async def _one(client, sem, new: dict, old: dict) -> dict:
    async with sem:
        r = await client.system_one(state={"new_card": _card(new), "existing_card": _card(old)},
                                    questions=QUESTIONS)
    s = r.scores["synergy"]
    return {"synergy": round(s.score / max(int(k) for k in s.legend), 3),
            "synergy_conf": round(s.confidence, 3),
            "combo": round(r.nouls["combo"].noul, 3),
            "tokens": r.usage.input_tokens or 0}


async def _all(pairs: list[tuple[dict, dict]]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with AsyncTypeSafeClient() as client:
        return await asyncio.gather(*(_one(client, sem, n, o) for n, o in pairs))


def judge_pairs(pairs: list[tuple[dict, dict]]) -> list[dict]:
    return asyncio.run(_all(pairs))
