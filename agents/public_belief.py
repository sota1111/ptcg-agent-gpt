"""Public-history belief used by evaluation-only determinizations (SOT-2400).

The model deliberately consumes a narrow allow-list: cards currently visible
on the opponent board, discard, face-up prizes, and an opponent-owned stadium.
It never reads hand/prize/deck identities, opponent identity, or evaluation
pool metadata.  Card IDs are converted immediately to attribute buckets so
the posterior is portable across deck lists rather than an identity lookup.
"""

from __future__ import annotations

import math
from collections import Counter


def _public_opponent_ids(raw_obs: dict) -> list[int]:
    current = raw_obs.get("current") or {}
    players = current.get("players") or ({}, {})
    own_index = current.get("yourIndex", 0)
    opponent_index = 1 - own_index
    opponent = players[opponent_index] if len(players) > opponent_index else {}
    ids: list[int] = []

    def add(cards) -> None:
        ids.extend(
            card["id"]
            for card in (cards or ())
            if isinstance(card, dict) and card.get("id") is not None
        )

    add(opponent.get("discard"))
    add(card for card in (opponent.get("prize") or ()) if isinstance(card, dict))
    for pokemon in list(opponent.get("active") or ()) + list(opponent.get("bench") or ()):
        if not isinstance(pokemon, dict):
            continue
        add([pokemon])
        add(pokemon.get("energyCards"))
        add(pokemon.get("tools"))
        add(pokemon.get("preEvolution"))
    add(
        card
        for card in (current.get("stadium") or ())
        if isinstance(card, dict) and card.get("playerIndex") == opponent_index
    )
    return ids


def _bucket(card) -> tuple[int, int, bool, bool, bool]:
    """Attribute-level card/archetype bucket; never contains card identity."""
    return (card.card_type, card.energy_type, card.basic, card.stage1 or card.stage2, card.ex)


def public_belief_weights(raw_obs: dict, candidate_ids: list[int], own_deck: list[int], card_index):
    """Return smoothed likelihood ratios for candidate hidden-zone cards."""
    deck_buckets = Counter(_bucket(card_index.card(card_id)) for card_id in own_deck)
    seen_buckets = Counter(
        _bucket(card_index.card(card_id)) for card_id in _public_opponent_ids(raw_obs)
    )
    total_deck = max(1, sum(deck_buckets.values()))
    total_seen = sum(seen_buckets.values())
    alpha = 6.0
    weights = []
    for card_id in candidate_ids:
        bucket = _bucket(card_index.card(card_id))
        prior = deck_buckets[bucket] / total_deck
        posterior = (seen_buckets[bucket] + alpha * prior) / (total_seen + alpha)
        weights.append(max(0.25, min(4.0, posterior / max(prior, 1 / total_deck))))
    return weights


def weighted_shuffle(items: list[int], weights: list[float], rng) -> None:
    """Seeded weighted sampling without replacement via exponential keys."""
    keyed = [
        (-math.log(max(rng.random(), 1e-12)) / max(weight, 1e-9), index, item)
        for index, (item, weight) in enumerate(zip(items, weights, strict=True))
    ]
    keyed.sort()
    items[:] = [item for _, _, item in keyed]


def apply_public_belief(raw_obs: dict, pool: list[int], own_deck: list[int], rng, card_index):
    """Reorder a MIRROR candidate pool according to public-only evidence."""
    weighted_shuffle(pool, public_belief_weights(raw_obs, pool, own_deck, card_index), rng)
