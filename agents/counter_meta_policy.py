"""Public-only policy for the SOT-2554 single-prize counter-meta candidate.

The policy is deliberately small and portable.  It extends the repository's
total SelectContext rule table, but couples its public board decisions to the
candidate deck's Alakazam line and Mist Energy protection.  It never receives
an opponent name, pool label, private prize identity, or unrevealed deck data.
"""

import os

from .base import BaseAgent
from .observation import View
from .rule_policy import CTX_SETUP_ACTIVE, CTX_SETUP_BENCH, RulePolicy

ABRA = 741
KADABRA = 742
ALAKAZAM = 743
MIST_ENERGY = 11

_OT_EVOLVE = 9
_AREA_ACTIVE = 4
_CANDIDATE_NAME = "single-prize-alakazam-mist"


def candidate_enabled() -> bool:
    """True only for an explicit evaluation-harness opt in."""
    return (
        os.environ.get("PTCG_TELEMETRY_PROTOCOL") == "1"
        and os.environ.get("PTCG_COUNTER_META_CANDIDATE") == _CANDIDATE_NAME
    )


class CounterMetaPolicy(RulePolicy):
    """Deterministic single-prize policy using legal options and public board."""

    def _ordering_override(self, view: View, context):
        if context in (CTX_SETUP_ACTIVE, CTX_SETUP_BENCH):
            # Establish the deck's only Basic deterministically.
            return lambda i: (
                1.0 if self._option_card_id(view, view.select.options[i]) == ABRA else 0.0
            )
        if context == 37:  # EVOLVE
            # Complete the draw engine/attacker before duplicate development.
            return lambda i: self._evolution_score(view, i)
        if context == 22:  # ATTACH_TO
            # Protect the developed single-prize attacker with Mist Energy
            # when the legal prompt offers a target.  Existing energy-card
            # identities and HP are public board attributes.
            return lambda i: self._protected_attacker_score(view, i)
        return super()._ordering_override(view, context)

    def _evolution_score(self, view: View, i: int) -> float:
        opt = view.select.options[i]
        card_id = self._option_card_id(view, opt)
        stage_score = {ALAKAZAM: 3000.0, KADABRA: 2000.0}.get(card_id, 0.0)
        return stage_score + (100.0 if opt.type == _OT_EVOLVE else 0.0) - i / 1000.0

    def _protected_attacker_score(self, view: View, i: int) -> float:
        opt = view.select.options[i]
        raw = opt.raw
        area = raw.get("area", raw.get("inPlayArea"))
        pokemon = view.find_pokemon(raw.get("playerIndex", view.your_index), area, raw.get("index"))
        if pokemon is None:
            return 0.0
        alakazam_bonus = 3000.0 if pokemon.card_id == ALAKAZAM else 0.0
        unprotected_bonus = 1000.0 if MIST_ENERGY not in pokemon.energy_card_ids else 0.0
        active_bonus = 500.0 if area == _AREA_ACTIVE else 0.0
        return alakazam_bonus + unprotected_bonus + active_bonus + pokemon.hp / 1000.0


class CounterMetaAgent(BaseAgent):
    """BaseAgent wrapper preserving legal random fallback on any exception."""

    def __init__(self, seed: int, deck=None, card_index=None):
        super().__init__(seed, deck)
        self._policy = CounterMetaPolicy(card_index=card_index)

    def choose(self, view: View) -> list:
        return self._policy.choose(view)
