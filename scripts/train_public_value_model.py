"""Fit the SOT-2346 count-only logistic value model from the train split."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ptcg_agent.runtime_dataset import PUBLIC_FEATURE_ALLOWLIST, load_runtime_dataset  # noqa: E402


def fit(corpus: Path, *, steps: int = 4000, rate: float = 0.05, penalty: float = 0.03) -> dict:
    rows = list(load_runtime_dataset(corpus, "train"))
    if not rows:
        raise ValueError("training split is empty")
    columns = list(zip(*(row.features for row in rows), strict=True))
    means = [sum(column) / len(column) for column in columns]
    scales = [
        max(1.0, math.sqrt(sum((x - mean) ** 2 for x in column) / len(column)))
        for column, mean in zip(columns, means, strict=True)
    ]
    matrix = [
        [
            (value - mean) / scale
            for value, mean, scale in zip(row.features, means, scales, strict=True)
        ]
        for row in rows
    ]
    weights = [0.0] * len(means)
    wins = sum(row.value for row in rows)
    intercept = math.log((wins + 0.5) / (len(rows) - wins + 0.5))
    for _ in range(steps):
        grad_b = 0.0
        grad_w = [0.0] * len(weights)
        for row, features in zip(rows, matrix, strict=True):
            logit = intercept + sum(w * x for w, x in zip(weights, features, strict=True))
            prediction = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit))))
            error = prediction - row.value
            grad_b += error
            for index, value in enumerate(features):
                grad_w[index] += error * value
        intercept -= rate * grad_b / len(rows)
        for index in range(len(weights)):
            weights[index] -= rate * (grad_w[index] / len(rows) + penalty * weights[index])
    return {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2346",
        "model": "ridge-logistic-public-state-blend",
        "featureAllowlist": list(PUBLIC_FEATURE_ALLOWLIST),
        "trainingSplit": "train",
        "trainingSamples": len(rows),
        "featureMeans": means,
        "featureScales": scales,
        "intercept": intercept,
        "weights": weights,
        "blendWeight": 0.25,
        "regularization": penalty,
        "optimizationSteps": steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact = fit(args.corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
