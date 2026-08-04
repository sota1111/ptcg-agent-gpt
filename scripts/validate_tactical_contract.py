"""Fail-closed validation for the preregistered SOT-2439 tactical contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_FORBIDDEN = {
    "hidden_hand_identity",
    "hidden_deck_identity_or_order",
    "hidden_prize_identity",
    "opponent_identity",
    "opponent_pool_identity",
    "evaluation_seed",
    "match_seed",
    "seat_as_matchup_proxy",
    "hidden_world_fingerprint",
}
IDENTITY_TOKENS = {"identity", "fingerprint", "seed", "pool"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(root: Path, value: str) -> Path:
    return root / value


def validate_manifest(manifest_path: Path, lock_path: Path | None = None) -> dict[str, Any]:
    root = manifest_path.parents[2]
    lock = lock_path or manifest_path.with_suffix(".sha256")
    expected_manifest_hash = lock.read_text().strip().split()[0]
    if sha256(manifest_path) != expected_manifest_hash:
        raise ValueError("tactical contract manifest fingerprint drifted")

    manifest = json.loads(manifest_path.read_text())
    features = manifest["policyFeatures"]
    allowlist = set(features["allowlist"])
    forbidden = set(features["forbidden"])
    if forbidden != REQUIRED_FORBIDDEN:
        raise ValueError("forbidden feature contract drifted")
    if allowlist & forbidden:
        raise ValueError("allowed and forbidden features overlap")
    for feature in allowlist:
        if any(token in feature for token in IDENTITY_TOKENS):
            raise ValueError(f"identity-bearing policy feature is not public-only: {feature}")

    for key in ("main", "deck"):
        path = _resolve(root, manifest["champion"][key])
        if sha256(path) != manifest["champion"][f"{key}Sha256"]:
            raise ValueError(f"champion {key} fingerprint drifted")

    inherited = manifest["inheritedReanchoringContract"]
    source_path = _resolve(root, inherited["sourceManifest"])
    if sha256(source_path) != inherited["sourceManifestSha256"]:
        raise ValueError("inherited reanchoring manifest fingerprint drifted")
    source = json.loads(source_path.read_text())
    if inherited["opponents"] != [row["id"] for row in source["opponents"]]:
        raise ValueError("opponent pool drifted from SOT-2399")

    screen = manifest["phases"]["screen"]
    confirm = manifest["phases"]["confirm"]
    if screen["baseSeed"] == confirm["baseSeed"] or not confirm["independentFromScreen"]:
        raise ValueError("screen and confirm seeds are not independent")
    if not screen["seatReversal"] or not confirm["seatReversal"]:
        raise ValueError("both phases must evaluate both seats")
    if not manifest["candidate"]["sameSearchAndRuntimeBudgetAsChampion"]:
        raise ValueError("candidate budget is not frozen to champion")
    if manifest["kaggleSubmissionAllowed"]:
        raise ValueError("child issue must forbid Kaggle submission")
    return manifest


def screen_gate(champion: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate["aggregate"] <= champion["aggregate"]:
        reasons.append("aggregate did not strictly improve")
    for opponent, rate in champion["opponents"].items():
        if candidate["opponents"][opponent] < rate:
            reasons.append(f"opponent regression: {opponent}")
    if candidate["seat1"] < champion["seat1"]:
        reasons.append("seat1 regression")
    for key in ("faults", "unfinished", "runtime"):
        if candidate[key] > champion[key]:
            reasons.append(f"{key} regression")
    return {"passed": not reasons, "reasons": reasons, "confirmAuthorized": not reasons}


def require_confirm_authorization(screen_decision: dict[str, Any]) -> None:
    if not screen_decision.get("confirmAuthorized") or not screen_decision.get("passed"):
        raise ValueError("confirm is forbidden until every screen gate passes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--lock", type=Path)
    args = parser.parse_args()
    manifest = validate_manifest(args.manifest, args.lock)
    print(json.dumps({"issue": manifest["issue"], "valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
