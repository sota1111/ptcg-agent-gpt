"""Loader for deterministic public-observation runtime replay datasets."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeTrainingSample:
    features: tuple[float, ...]
    action: int
    legal_actions: tuple[int, ...]
    value: float
    split: str
    heuristic_value: float | None = None
    provenance_fingerprint: str | None = None


PUBLIC_FEATURE_ALLOWLIST = (
    "turn_index",
    "own_hand_count",
    "own_deck_count",
    "own_prize_count",
    "opponent_hand_count",
    "opponent_deck_count",
    "opponent_prize_count",
)
SPLITS = {"train", "screen", "confirm"}


def public_feature_vector(state: dict[str, Any]) -> tuple[float, ...]:
    """Project an allowlisted public snapshot onto the stable seven-feature contract."""
    own = state.get("own") or {}
    opponent = state.get("opponent") or {}
    values = (
        state.get("turn_index", 0),
        own.get("hand_count", 0),
        own.get("deck_count", 0),
        own.get("prize_count", 0),
        opponent.get("hand_count", 0),
        opponent.get("deck_count", 0),
        opponent.get("prize_count", 0),
    )
    return tuple(float(value) for value in values)


def provenance_fingerprint(seed: int, seat: int, opponent_fingerprint: str) -> str:
    """Identify a match unit without exposing opponent identity to model features."""
    payload = f"{seed}:{seat}:{opponent_fingerprint}".encode()
    return hashlib.sha256(payload).hexdigest()


def load_runtime_dataset(path: Path, split: str | None = None) -> Iterator[RuntimeTrainingSample]:
    """Stream validated samples without requiring a GPU or engine runtime."""
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            raw: dict[str, Any] = json.loads(line)
            version = raw.get("schemaVersion")
            if version not in {"1.0.0", "2.0.0"}:
                raise ValueError(f"line {number}: unsupported dataset schema")
            sample_split = raw.get("split")
            valid_splits = {"train", "validation", "holdout"} if version == "1.0.0" else SPLITS
            if sample_split not in valid_splits:
                raise ValueError(f"line {number}: invalid split")
            if split is not None and sample_split != split:
                continue
            features = tuple(float(value) for value in raw.get("features", ()))
            legal = tuple(int(action) for action in raw.get("legalActions", ()))
            action = int(raw["action"])
            if len(features) != 7 or action not in legal:
                raise ValueError(f"line {number}: invalid feature or action payload")
            yield RuntimeTrainingSample(
                features=features,
                action=action,
                legal_actions=legal,
                value=float(raw["value"]),
                split=sample_split,
                heuristic_value=(float(raw["heuristicValue"]) if "heuristicValue" in raw else None),
                provenance_fingerprint=raw.get("provenanceFingerprint"),
            )
