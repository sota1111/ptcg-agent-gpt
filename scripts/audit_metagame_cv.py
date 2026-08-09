"""Fail-closed audit and gate for the SOT-2538 metagame CV contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SPLITS = ("train", "screen", "confirm", "blind")
LICENSE_ALLOW_LIST = {"Apache-2.0", "repository-local"}
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo(path: str, root: Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def manifest_fingerprint(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def audit_manifest(path: Path) -> dict[str, Any]:
    root = ROOT
    manifest = json.loads(path.read_text())
    if manifest.get("candidateChangesAllowed") or manifest.get("kaggleSubmissionAllowed"):
        raise ValueError("candidate changes and Kaggle submission must remain disabled")
    opponents = {row["id"]: row for row in manifest["opponents"]}
    if len(opponents) != len(manifest["opponents"]):
        raise ValueError("opponent ids must be unique")

    boundaries: dict[str, dict[str, set[str]]] = {}
    unavailable_external: set[str] = set()
    previous_end: datetime | None = None
    for split_name in SPLITS:
        split = manifest["splits"][split_name]
        start = datetime.fromisoformat(split["window"]["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(split["window"]["end"].replace("Z", "+00:00"))
        if start > end or (previous_end is not None and start <= previous_end):
            raise ValueError("split time windows must be ordered and disjoint")
        previous_end = end
        entities: set[str] = set()
        match_units: set[str] = set()
        seeds: set[str] = set()
        for opponent_id in split["opponents"]:
            opponent = opponents[opponent_id]
            repo = _repo(opponent["repo"], root)
            if opponent["license"] not in LICENSE_ALLOW_LIST:
                raise ValueError(f"license is not allowed: {opponent_id}")
            deck_path = _repo(opponent.get("deckPath", str(repo / "deck.csv")), root)
            if not (repo / "main.py").is_file() or not deck_path.is_file():
                if (
                    opponent["license"] != "repository-local"
                    or not Path(opponent["repo"]).is_absolute()
                ):
                    raise ValueError(f"required opponent is unavailable: {opponent_id}")
                unavailable_external.add(opponent_id)
            else:
                if sha256(repo / "main.py") != opponent["policySha256"]:
                    raise ValueError(f"policy fingerprint drift: {opponent_id}")
                if sha256(deck_path) != opponent["deckSha256"]:
                    raise ValueError(f"deck fingerprint drift: {opponent_id}")
            entity = f"{opponent['policySha256']}:{opponent['deckSha256']}"
            entities.add(entity)
            for offset in range(split["seedsPerOpponent"]):
                seed = str(split["baseSeed"] + offset)
                seeds.add(seed)
                match_units.add(f"{split_name}:{entity}:{seed}")
        boundaries[split_name] = {
            "entity": entities,
            "policy": {opponents[item]["policySha256"] for item in split["opponents"]},
            "deck": {opponents[item]["deckSha256"] for item in split["opponents"]},
            "match": match_units,
            "seed": seeds,
            "time": {split["window"]["start"], split["window"]["end"]},
        }

    overlaps: dict[str, dict[str, list[str]]] = {}
    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1 :]:
            key = f"{left}:{right}"
            overlaps[key] = {
                boundary: sorted(boundaries[left][boundary] & boundaries[right][boundary])
                for boundary in ("entity", "policy", "match", "seed", "time")
            }
            overlaps[key]["deck"] = sorted(boundaries[left]["deck"] & boundaries[right]["deck"])
            if any(
                overlaps[key][item]
                for item in ("entity", "policy", "deck", "match", "seed", "time")
            ):
                raise ValueError(f"cross-split overlap: {key}")
    public = [row for row in manifest["opponents"] if row["license"] == "Apache-2.0"]
    if not public or not all(row.get("source") and row.get("offline") for row in public):
        raise ValueError("at least one portable Apache-2.0 public opponent is required")
    return {
        "manifestSha256": manifest_fingerprint(manifest),
        "splits": {name: len(manifest["splits"][name]["opponents"]) for name in SPLITS},
        "overlaps": overlaps,
        "publicOpponents": [row["id"] for row in public],
        "unavailableExternalOpponents": sorted(unavailable_external),
        "passed": True,
    }


def compare(
    champion: dict[str, Any], candidate: dict[str, Any], gate: dict[str, Any]
) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate["poolWinRate"] <= champion["poolWinRate"]:
        reasons.append("pooled win rate did not strictly improve")
    for opponent, rate in champion["opponents"].items():
        if candidate["opponents"].get(opponent, -1.0) < rate:
            reasons.append(f"opponent regression: {opponent}")
    for seat, rate in champion["seats"].items():
        if candidate["seats"].get(seat, -1.0) < rate:
            reasons.append(f"seat regression: {seat}")
    if candidate["faults"] > gate["faultsMax"]:
        reasons.append("fault limit exceeded")
    if candidate["unfinished"] > gate["unfinishedMax"]:
        reasons.append("unfinished limit exceeded")
    if (
        candidate["meanRuntimeSeconds"]
        > champion["meanRuntimeSeconds"] * gate["meanRuntimeRatioMax"]
    ):
        reasons.append("mean runtime ratio exceeded")
    if candidate["maxRuntimeSeconds"] >= gate["matchRuntimeSecondsMaxExclusive"]:
        reasons.append("match runtime limit exceeded")
    return {"passed": not reasons, "reasons": reasons}


def authorize_confirm(screen_decision: dict[str, Any]) -> None:
    if screen_decision.get("phase") != "screen" or not screen_decision.get("gate", {}).get(
        "passed"
    ):
        raise ValueError("confirm is forbidden until an independent screen strictly passes")


def offline_import(repo: Path) -> None:
    spec = importlib.util.spec_from_file_location("audited_public_opponent", repo / "main.py")
    if spec is None or spec.loader is None:
        raise ValueError("public opponent cannot be imported")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_manifest(args.manifest)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
