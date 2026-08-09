"""Public-only lightweight policy/value prior distilled for SOT-2572.

The runtime encoder deliberately accepts only :class:`View` and the legal
options exposed by the engine.  It has no interface for opponent identity,
hidden zones, split names, replay ids, or seeds.  A malformed/missing artifact
fails closed by returning neutral scores, leaving the champion ordering intact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .observation import View

_DEFAULT_ARTIFACT = Path(__file__).with_name("population_prior_sot_2572.json")


class PopulationPrior:
    """Deterministic integer-linear prior over public state and legal actions."""

    def __init__(self, artifact_path: str | Path | None = None):
        self.path = Path(artifact_path) if artifact_path else _DEFAULT_ARTIFACT
        self.model: dict = {}
        try:
            raw = self.path.read_bytes()
            model = json.loads(raw)
            expected = model.pop("contentSha256")
            canonical = json.dumps(model, sort_keys=True, separators=(",", ":")).encode()
            if hashlib.sha256(canonical).hexdigest() != expected:
                return
            if model.get("schemaVersion") != "1.0.0" or not model.get("publicOnly"):
                return
            self.model = model
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return

    @property
    def available(self) -> bool:
        return bool(self.model)

    def archetype_posterior(self, view: View) -> dict[str, int]:
        """Integer posterior weights from revealed opponent cards only (sum 1000)."""
        signatures = self.model.get("archetypeSignatures", {})
        revealed = set(view.opp.discard_card_ids + view.opp.prize_known_ids)
        revealed.update(p.card_id for p in view.opp.active + view.opp.bench if p is not None)
        revealed.discard(None)
        votes = {
            name: sum(1 for card_id in ids if card_id in revealed)
            for name, ids in signatures.items()
        }
        total = sum(votes.values())
        if total == 0:
            return {"unknown": 1000}
        posterior = {name: votes[name] * 1000 // total for name in sorted(votes) if votes[name]}
        posterior[next(iter(posterior))] += 1000 - sum(posterior.values())
        return posterior

    def score_options(self, view: View) -> list[float]:
        """Return bounded additive policy logits for exactly the legal options."""
        if not self.available or view.select is None:
            return [0.0] * (len(view.select.options) if view.select else 0)
        posterior = self.archetype_posterior(view)
        weights = self.model.get("policyWeights", {})
        tempo = self._tempo_bucket(view)
        scores = []
        for option in view.select.options:
            action_key = str(option.type)
            weighted = 0
            for archetype, mass in posterior.items():
                row = weights.get(archetype, weights.get("unknown", {}))
                weighted += mass * int(row.get(action_key, 0))
            tempo_weight = int(self.model.get("tempoWeights", {}).get(tempo, {}).get(action_key, 0))
            # Artifact integers are milli-logits; clamp corrupt/extreme inputs.
            scores.append(max(-8.0, min(8.0, weighted / 1_000_000 + tempo_weight / 1000)))
        return scores

    def value(self, view: View) -> float:
        """Public board-tempo value in [0, 1], useful for offline calibration."""
        if not self.available:
            return 0.5
        value_weights = self.model.get("valueWeights", {})
        prize_delta = view.opp.prize_count - view.me.prize_count
        board_delta = (
            len(view.me.active) + len(view.me.bench) - len(view.opp.active) - len(view.opp.bench)
        )
        raw = 500 + int(value_weights.get("prizeDelta", 0)) * prize_delta
        raw += int(value_weights.get("boardDelta", 0)) * board_delta
        return max(0.0, min(1.0, raw / 1000))

    @staticmethod
    def _tempo_bucket(view: View) -> str:
        if view.me.prize_count < view.opp.prize_count:
            return "ahead"
        if view.me.prize_count > view.opp.prize_count:
            return "behind"
        return "even"
