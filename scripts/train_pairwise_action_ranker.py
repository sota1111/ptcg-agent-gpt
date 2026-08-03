"""Train and export the SOT-2377 ranker from the frozen oracle train split."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


def signature(types: list[int]) -> str:
    return ",".join(str(value) for value in types)


def train(oracle: Path, oracle_sha256: str, iterations: int = 400, rate: float = 0.08) -> dict:
    actual = hashlib.sha256(oracle.read_bytes()).hexdigest()
    if actual != oracle_sha256:
        raise ValueError(f"oracle fingerprint mismatch: {actual}")
    rows = [json.loads(line) for line in oracle.read_text().splitlines() if line]
    train_rows = [row for row in rows if row["split"] == "train"]
    global_scores: defaultdict[str, float] = defaultdict(float)
    context_scores: defaultdict[str, defaultdict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for _ in range(iterations):
        for row in train_rows:
            label = float(row["relativeOutcome"])
            if label == 0:
                continue
            left = signature(row["leftActionTypes"])
            right = signature(row["rightActionTypes"])
            context = str(row["publicFeatures"]["selection_context"])
            target = 1.0 if label > 0 else -1.0
            confidence = min(abs(label), 1.0)
            margin = (global_scores[left] - global_scores[right]) + (
                context_scores[context][left] - context_scores[context][right]
            )
            error = target - max(-1.0, min(1.0, margin))
            step = rate * confidence * error / len(train_rows)
            global_scores[left] += step
            global_scores[right] -= step
            context_scores[context][left] += step
            context_scores[context][right] -= step
    return {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2377",
        "trainedAt": datetime.now(UTC).isoformat(),
        "trainingSplit": "train",
        "trainingRows": len(train_rows),
        "oracleSha256": actual,
        "featureContract": ["selection_context", "legal_action_option_types"],
        "forbiddenFeatures": [
            "opponent_identity",
            "pool_identity",
            "seed",
            "seat",
            "match_id",
            "hidden_hand_identity",
            "hidden_deck_identity",
            "world_fingerprint",
        ],
        "globalScores": dict(sorted(global_scores.items())),
        "contextScores": {
            context: dict(sorted(scores.items()))
            for context, scores in sorted(context_scores.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--oracle-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    model = train(args.oracle, args.oracle_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
