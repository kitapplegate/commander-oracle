"""Code-side candidate generation: for each new card, which older cards might it
make better? Jev judges the pairs afterward; this step only has to avoid missing
the real partners while keeping the list short.

Two signals, both text-only (no prices, so the backtest stays honest):
  - TF-IDF similarity of rules text (shared mechanics: Treasure, +1/+1 counters, ...)
  - tribal links: one card's text names a creature type the other card has
"""
from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

TRIBAL_BONUS = 0.25
COMMON_TRIBE_SHARE = 0.03  # types on more than 3% of cards (Human, Soldier...) are too broad to count


def _clean(card: dict) -> str:
    text = card["text"].replace(card["name"].split(" // ")[0], "CARDNAME")
    return re.sub(r"\([^)]*\)", "", text)  # drop reminder text


def _subtypes(card: dict) -> set[str]:
    return {s.strip() for s in card["subtypes"].split(",") if s.strip()}


def find_candidates(new_cards: list[dict], pool: list[dict], k: int = 30) -> dict[str, list[tuple[str, float]]]:
    """new oracle_id -> [(older oracle_id, candidate score)], best first."""
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, stop_words="english")
    matrix = vec.fit_transform([_clean(c) for c in pool + new_cards])
    pool_m, new_m = matrix[: len(pool)], matrix[len(pool):]
    sims = (new_m @ pool_m.T).toarray()

    tribe_counts: dict[str, int] = {}
    for c in pool:
        for t in _subtypes(c):
            tribe_counts[t] = tribe_counts.get(t, 0) + 1
    rare_tribes = {t for t, n in tribe_counts.items() if n <= COMMON_TRIBE_SHARE * len(pool)}
    pool_types = [_subtypes(c) & rare_tribes for c in pool]
    pool_text = [c["text"] for c in pool]

    out = {}
    for i, new in enumerate(new_cards):
        new_types = _subtypes(new) & rare_tribes
        new_text = new["text"]
        mentioned = {t for t in rare_tribes if re.search(rf"\b{re.escape(t)}s?\b", new_text)}
        score = sims[i].copy()
        for j, types in enumerate(pool_types):
            if (types & mentioned) or any(re.search(rf"\b{re.escape(t)}s?\b", pool_text[j]) for t in new_types):
                score[j] += TRIBAL_BONUS
        top = np.argsort(-score)[:k]
        out[new["oracle_id"]] = [(pool[j]["oracle_id"], round(float(score[j]), 4)) for j in top]
    return out
