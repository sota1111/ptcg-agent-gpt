"""Fail-closed audit for the SOT-2571 population distillation contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("train", "screen", "confirm", "blind")
IDENTITIES = ("policyEntity", "deckEntity", "evidenceId", "submissionLineage")
LICENSES = {"Apache-2.0", "repository-local"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load_pinned(contract: dict[str, Any], path_key: str, hash_key: str) -> dict[str, Any]:
    path = ROOT / contract[path_key]
    if not path.is_file() or sha256(path) != contract[hash_key]:
        raise ValueError(f"fingerprint drift: {path_key}")
    return json.loads(path.read_text())


def audit_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text())
    if not contract.get("preregistered"):
        raise ValueError("contract must be preregistered")
    if contract.get("candidateDefaultEnabled") or contract.get("kaggleSubmissionAllowed"):
        raise ValueError("candidate and Kaggle submission must remain disabled")

    source = _load_pinned(contract, "sourceContract", "sourceContractSha256")
    population = _load_pinned(contract, "populationSnapshot", "populationSnapshotSha256")
    split_contract = contract["splitContract"]
    if tuple(split_contract["names"]) != SPLITS or not split_contract["inheritSourceWindows"]:
        raise ValueError("all inherited splits are required")
    if split_contract["popularityFitSplit"] != "train" or split_contract[
        "popularityReadAllowedSplits"
    ] != ["train"]:
        raise ValueError("popularity weights must be train-only")

    members = population["members"]
    if not members or len({row["id"] for row in members}) != len(members):
        raise ValueError("population members must be non-empty and unique")
    if {row["split"] for row in members} != set(SPLITS):
        raise ValueError("population must cover every split")
    if {row["popularityClass"] for row in members} != {"established", "emerging"}:
        raise ValueError("population must include established and emerging archetypes")

    source_members = {
        (row["id"], split)
        for split in SPLITS
        for row in source["opponents"]
        if row["id"] in source["splits"][split]["opponents"]
    }
    source_evidence = {row["evidence"]["id"] for row in source["opponents"]}
    for row in members:
        if row["evidenceId"] not in source_evidence:
            raise ValueError(f"population evidence is not inherited: {row['id']}")
    overlaps: dict[str, dict[str, list[str]]] = {}
    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1 :]:
            pair = f"{left}:{right}"
            overlaps[pair] = {}
            for field in IDENTITIES:
                left_values = {row[field] for row in members if row["split"] == left}
                right_values = {row[field] for row in members if row["split"] == right}
                overlaps[pair][field] = sorted(left_values & right_values)
            if any(overlaps[pair].values()):
                raise ValueError(f"cross-split population overlap: {pair}")

    features = contract["features"]
    if not features["allow"] or not features["deny"]:
        raise ValueError("feature allow-list and deny-list are required")
    forbidden = {"opponent_identity", "match_seed", "evaluation_split", "future_replay"}
    if not forbidden <= set(features["deny"]) or forbidden & set(features["allow"]):
        raise ValueError("public feature boundary is incomplete")
    if features["unknownArchetype"] != "unknown":
        raise ValueError("unseen archetypes must fail closed to unknown")

    for asset in contract["assets"]:
        if asset["portable"] and asset["license"] not in LICENSES:
            raise ValueError(f"portable asset license is not allowed: {asset['id']}")
        if not asset["provenance"]:
            raise ValueError(f"asset provenance is missing: {asset['id']}")
        if not asset["portable"] and asset["runtimeAllowed"]:
            raise ValueError(f"non-portable runtime asset is forbidden: {asset['id']}")

    protocol = contract["protocol"]
    if (
        tuple(protocol["order"]) != SPLITS
        or not protocol["confirmRequiresIndependentPassingScreenReceipt"]
    ):
        raise ValueError("screen-confirm-blind protocol is not strict")
    gate = contract["promotionGate"]
    required_true = (
        "pooledWinRateStrictlyImproves",
        "everyArchetypeNonRegression",
        "everyMatchupNonRegression",
        "bothSeatsNonRegression",
        "artifactFingerprintRequired",
        "offlineImportRequired",
        "execCompatibilityRequired",
    )
    if not all(gate.get(key) is True for key in required_true):
        raise ValueError("strict promotion gate is incomplete")
    if contract["budget"]["seats"] != [0, 1] or not contract["budget"]["equalChampionCandidate"]:
        raise ValueError("equal budget and both seats are required")

    return {
        "passed": True,
        "contractSha256": canonical_sha256(contract),
        "populationSha256": contract["populationSnapshotSha256"],
        "members": len(members),
        "sourceAssignments": len(source_members),
        "overlaps": overlaps,
        "kaggleSubmissionAllowed": False,
    }


def compare_gate(champion: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate["poolWinRate"] <= champion["poolWinRate"]:
        reasons.append("pooled win rate did not strictly improve")
    for dimension in ("archetypes", "matchups", "seats"):
        for key, value in champion[dimension].items():
            if candidate[dimension].get(key, -1.0) < value:
                reasons.append(f"{dimension} regression: {key}")
    if candidate["faults"] > 0 or candidate["unfinished"] > 0:
        reasons.append("reliability regression")
    if candidate["meanRuntimeSeconds"] > champion["meanRuntimeSeconds"] * 1.10:
        reasons.append("runtime regression")
    return {"passed": not reasons, "reasons": reasons}


def authorize_phase(phase: str, receipt: dict[str, Any]) -> None:
    prerequisite = {"confirm": "screen", "blind": "confirm"}.get(phase)
    if (
        prerequisite is None
        or receipt.get("phase") != prerequisite
        or not receipt.get("gate", {}).get("passed")
    ):
        raise ValueError(f"{phase} forbidden without passing independent prerequisite")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_contract(args.manifest), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
