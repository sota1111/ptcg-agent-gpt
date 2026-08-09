"""Fail-closed audit and gate for the metagame CV contracts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SPLITS = ("train", "screen", "confirm", "blind")
LICENSE_ALLOW_LIST = {"Apache-2.0", "repository-local"}
DISJOINT_KEYS = (
    "entity",
    "policy",
    "deck",
    "match",
    "seed",
    "time",
    "evidence",
    "submissionLineage",
)
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
        evidence_ids: set[str] = set()
        submission_lineages: set[str] = set()
        for opponent_id in split["opponents"]:
            opponent = opponents[opponent_id]
            evidence = opponent.get("evidence")
            if manifest.get("schemaVersion", "1.0.0") >= "2.0.0":
                if not isinstance(evidence, dict):
                    raise ValueError(f"evidence metadata is required: {opponent_id}")
                required = {
                    "id",
                    "kind",
                    "collectedAt",
                    "provenance",
                    "licenseEvidence",
                    "offlinePortable",
                    "submissionLineage",
                    "metagameFamily",
                }
                if required - evidence.keys():
                    raise ValueError(f"incomplete evidence metadata: {opponent_id}")
                collected_at = datetime.fromisoformat(
                    evidence["collectedAt"].replace("Z", "+00:00")
                )
                if not start <= collected_at <= end:
                    raise ValueError(f"evidence timestamp outside split window: {opponent_id}")
                if not evidence["offlinePortable"] or not evidence["licenseEvidence"]:
                    raise ValueError(
                        f"evidence is not licensed and offline portable: {opponent_id}"
                    )
                evidence_ids.add(evidence["id"])
                submission_lineages.add(evidence["submissionLineage"])
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
            "evidence": evidence_ids,
            "submissionLineage": submission_lineages,
        }

    overlaps: dict[str, dict[str, list[str]]] = {}
    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1 :]:
            key = f"{left}:{right}"
            overlaps[key] = {
                boundary: sorted(boundaries[left][boundary] & boundaries[right][boundary])
                for boundary in DISJOINT_KEYS
            }
            if any(overlaps[key][item] for item in DISJOINT_KEYS):
                raise ValueError(f"cross-split overlap: {key}")
    public = [row for row in manifest["opponents"] if row["license"] == "Apache-2.0"]
    if not public or not all(row.get("source") and row.get("offline") for row in public):
        raise ValueError("at least one portable Apache-2.0 public opponent is required")
    gap_schema = manifest.get("cvPublicGap")
    if manifest.get("schemaVersion", "1.0.0") >= "2.0.0":
        if not isinstance(gap_schema, dict):
            raise ValueError("CV/public gap schema is required")
        if gap_schema.get("publicRole") != "sanity-only":
            raise ValueError("public rating must remain sanity-only")
        if gap_schema.get("disagreementRule") != "prefer-cv":
            raise ValueError("CV must be selected when CV and public rating disagree")
    return {
        "manifestSha256": manifest_fingerprint(manifest),
        "splits": {name: len(manifest["splits"][name]["opponents"]) for name in SPLITS},
        "overlaps": overlaps,
        "publicOpponents": [row["id"] for row in public],
        "unavailableExternalOpponents": sorted(unavailable_external),
        "cvPublicGap": gap_schema,
        "passed": True,
    }


def compare_cv_public(cv_order: list[str], public_order: list[str] | None) -> dict[str, Any]:
    """Record direction/order agreement without allowing public rating to select a policy."""
    public = public_order or []
    shared = [item for item in cv_order if item in public]
    public_shared = [item for item in public if item in shared]
    agreement = shared == public_shared if len(shared) >= 2 else None
    return {
        "cvOrder": cv_order,
        "publicOrder": public_order,
        "sharedOrderAgreement": agreement,
        "selectedOrder": cv_order,
        "selectionBasis": "cv" if agreement is not False else "cv-pessimistic-on-disagreement",
        "publicRole": "sanity-only",
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
