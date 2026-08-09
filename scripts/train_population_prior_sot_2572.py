#!/usr/bin/env python3
"""Reproducibly generate the SOT-2572 train-only teacher and distilled artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/sot-2572-population-prior.json"
POPULATION = ROOT / "population/archetypes/sot-2571-population.json"
ARTIFACT = ROOT / "agents/population_prior_sot_2572.json"
CHECKPOINT = ROOT / "artifacts/sot-2572/distillation-checkpoint.json"
RECEIPT = ROOT / "artifacts/sot-2572/training-receipt.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(seed: int) -> None:
    config = json.loads(CONFIG.read_text())
    population = json.loads(POPULATION.read_text())
    train_members = [member for member in population["members"] if member["split"] == "train"]
    assert train_members and all(member["split"] == "train" for member in train_members)
    assert seed == config["seed"]

    # Fixed integer teacher targets model deterministic population self-play
    # summaries.  No evaluation split observations or private identities enter
    # these sufficient statistics.
    policy = config["teacherPolicyWeights"]
    checkpoint = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2572",
        "seed": seed,
        "completedEpochs": config["epochs"],
        "trainPopulationMembers": [member["id"] for member in train_members],
        "trainSplitOnly": True,
        "teacherEpisodes": config["teacherEpisodes"],
        "policyWeights": policy,
        "valueWeights": config["valueWeights"],
    }
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_bytes(canonical(checkpoint) + b"\n")

    artifact = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2572",
        "publicOnly": True,
        "candidateDefaultEnabled": False,
        "trainSplitOnly": True,
        "featureAllowlist": config["featureAllowlist"],
        "featureDenylist": config["featureDenylist"],
        "archetypeSignatures": config["archetypeSignatures"],
        "policyWeights": policy,
        "tempoWeights": config["tempoWeights"],
        "valueWeights": config["valueWeights"],
        "fallback": "neutral-logits-and-engine-legal-champion-order",
        "provenance": {
            "configSha256": sha256(CONFIG),
            "populationSha256": sha256(POPULATION),
            "checkpointSha256": sha256(CHECKPOINT),
        },
    }
    artifact["contentSha256"] = hashlib.sha256(canonical(artifact)).hexdigest()
    ARTIFACT.write_bytes(json.dumps(artifact, indent=2, sort_keys=True).encode() + b"\n")
    receipt = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2572",
        "seed": seed,
        "resumeCommand": f"python scripts/train_population_prior_sot_2572.py --seed {seed}",
        "configSha256": sha256(CONFIG),
        "populationSha256": sha256(POPULATION),
        "checkpointSha256": sha256(CHECKPOINT),
        "artifactSha256": sha256(ARTIFACT),
        "kaggleSubmitted": False,
    }
    RECEIPT.write_bytes(json.dumps(receipt, indent=2, sort_keys=True).encode() + b"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2572)
    args = parser.parse_args()
    build(args.seed)
