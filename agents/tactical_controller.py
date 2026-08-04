"""Public-only tactical root/action scoring for SOT-2440.

The controller deliberately operates on :class:`agents.observation.View`, not
the raw engine observation.  Consequently hidden-zone identities, match seed,
opponent identity, and evaluation-pool metadata are outside its input
boundary.  It only adds small, attribute-derived bonuses to the champion
GreedyAgent scores; legality and state transitions remain engine-owned.
"""

from .greedy_agent import GreedyAgent
from .observation import View

_OT_CARD = 3
_OT_ATTACH = 8
_OT_RETREAT = 12
_OT_ATTACK = 13
_AREA_ACTIVE = 4
_AREA_BENCH = 5


class PublicTacticalAgent(GreedyAgent):
    """Greedy scorer augmented with portable public tactical concepts."""

    def score_options(self, view: View) -> list:
        base = super().score_options(view)
        return [
            score + self._tactical_bonus(view, option.raw, option.type)
            for score, option in zip(base, view.select.options, strict=True)
        ]

    def choose(self, view: View) -> list:
        sel = view.select
        lo, hi = self._selection_count(view)
        scores = self.score_options(view)
        if lo == hi or sel.context in self._cost_contexts():
            count = lo
        elif self._prefer_max_count(sel.context):
            count = hi
        else:
            count = lo
        ranked = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
        return sorted(ranked[:count])

    @staticmethod
    def _selection_count(view: View) -> tuple[int, int]:
        from . import actions

        return actions.count_bounds(view.select)

    @staticmethod
    def _cost_contexts():
        from .greedy_agent import _COST_CONTEXTS

        return _COST_CONTEXTS

    def _prefer_max_count(self, context: int) -> bool:
        from .greedy_agent import _COUNT_MAX_CONTEXTS

        return context in _COUNT_MAX_CONTEXTS or self._is_known_context(context)

    def _tactical_bonus(self, view: View, raw: dict, option_type: int) -> float:
        if option_type == _OT_ATTACK:
            return self._attack_plan_bonus(view, raw.get("attackId"))
        if option_type == _OT_ATTACH:
            return self._energy_readiness_bonus(view, raw)
        if option_type == _OT_RETREAT:
            return self._switch_bonus(view)
        if option_type == _OT_CARD:
            return self._public_target_bonus(view, raw)
        return 0.0

    def _attack_plan_bonus(self, view: View, attack_id) -> float:
        attack = self.cards.attack(attack_id)
        defender = view.opp.active[0] if view.opp.active else None
        if defender is None:
            return 0.0
        damage = float(attack.damage)
        attacker = view.me.active[0] if view.me.active else None
        attacker_type = self.cards.card(attacker.card_id).energy_type if attacker else -1
        target = self.cards.card(defender.card_id)
        if target.weakness == attacker_type:
            damage *= 2.0
        elif target.resistance == attacker_type:
            damage = max(0.0, damage - 30.0)
        # Prefer reachable KOs, especially multi-prize targets and match wins.
        if 0 < defender.hp <= damage:
            match_win = target.prize_value >= view.opp.prize_count
            return 18.0 + 8.0 * target.prize_value + (20.0 if match_win else 0.0)
        # Otherwise reward progress toward the public active's remaining HP.
        return min(8.0, 8.0 * damage / max(1.0, float(defender.hp)))

    def _energy_readiness_bonus(self, view: View, raw: dict) -> float:
        pokemon = view.find_pokemon(
            raw.get("playerIndex", view.your_index), raw.get("inPlayArea"), raw.get("index")
        )
        if pokemon is None:
            return 0.0
        card = self.cards.card(pokemon.card_id)
        costs = [self.cards.attack(attack_id).energy_cost for attack_id in card.attack_ids]
        if not costs:
            return 0.0
        attached = len(pokemon.energies)
        missing_before = min(max(0, cost - attached) for cost in costs)
        missing_after = min(max(0, cost - attached - 1) for cost in costs)
        readiness = 9.0 if missing_before > 0 and missing_after == 0 else 3.0
        # Public matchup signal: prepare attackers that pressure the revealed active.
        defender = view.opp.active[0] if view.opp.active else None
        if defender is not None and self.cards.card(defender.card_id).weakness == card.energy_type:
            readiness += 4.0
        return readiness

    def _switch_bonus(self, view: View) -> float:
        active = view.me.active[0] if view.me.active else None
        if active is None or not view.me.bench:
            return 0.0
        active_card = self.cards.card(active.card_id)
        active_pressure = active_card.max_attack_damage - 8.0 * max(
            0, active_card.retreat_cost - len(active.energies)
        )
        bench_pressure = max(
            self.cards.card(pokemon.card_id).max_attack_damage
            - 8.0 * max(0, self.cards.card(pokemon.card_id).retreat_cost - len(pokemon.energies))
            for pokemon in view.me.bench
        )
        status_penalty = 20.0 if (view.me.asleep or view.me.paralyzed or view.me.confused) else 0.0
        return max(0.0, min(14.0, 0.08 * (bench_pressure - active_pressure) + status_penalty))

    def _public_target_bonus(self, view: View, raw: dict) -> float:
        player = raw.get("playerIndex", view.your_index)
        if player == view.your_index or raw.get("area") not in (_AREA_ACTIVE, _AREA_BENCH):
            return 0.0
        target = view.find_pokemon(player, raw.get("area"), raw.get("index"))
        if target is None:
            return 0.0
        features = self.cards.card(target.card_id)
        damage_fraction = 1.0 - target.hp / max(1.0, float(target.max_hp))
        threat = features.max_attack_damage / 100.0 + len(target.energies)
        # Generic gust/target choices: damaged multi-prize targets first, then
        # the strongest publicly revealed board threat.
        return 8.0 * features.prize_value + 12.0 * damage_fraction + 2.0 * threat
