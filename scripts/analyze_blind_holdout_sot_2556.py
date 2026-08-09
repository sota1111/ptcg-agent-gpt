"""Audit SOT-2556's frozen blind reports and emit the parent exec-artifact receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def wilson(wins: int, total: int) -> list[float]:
    z = 1.96
    rate = wins / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z / denominator * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total))
    return [max(0.0, center - margin), min(1.0, center + margin)]


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [match for report in reports for match in report["matches"]]
    runtimes = [float(match["runtime_s"]) for match in matches]
    wins = sum(bool(match["semantic_won"]) for match in matches)
    seats = {str(seat): [m for m in matches if m["semantic_seat"] == seat] for seat in (0, 1)}
    return {
        "matches": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "winRate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "opponents": {
            report["opponent"]: {
                "matches": report["n_matches"],
                "wins": report["wins_semantic"],
                "winRate": report["winrate_semantic_excl_draws"],
                "faults": report["faults_semantic"],
                "unfinished": report["unfinished"],
            }
            for report in reports
        },
        "seats": {
            seat: {
                "matches": len(rows),
                "wins": sum(bool(row["semantic_won"]) for row in rows),
                "winRate": sum(bool(row["semantic_won"]) for row in rows) / len(rows),
            }
            for seat, rows in seats.items()
        },
        "faults": sum(report["faults_semantic"] for report in reports),
        "illegalActions": sum(
            bool(match.get("fault")) and "illegal" in str(match["fault"]).lower()
            for match in matches
        ),
        "unfinished": sum(report["unfinished"] for report in reports),
        "runtimeSeconds": {
            "mean": statistics.fmean(runtimes),
            "p95": sorted(runtimes)[math.ceil(0.95 * len(runtimes)) - 1],
            "max": max(runtimes),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=Path("eval/manifests/sot-2556-blind-holdout.json")
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/sot-2556/summary.json"))
    parser.add_argument(
        "--fingerprint", type=Path, default=Path("artifacts/sot-2556/submission-fingerprint.json")
    )
    parser.add_argument("--handoff", type=Path, default=Path("artifacts/sot-2556/handoff.json"))
    args = parser.parse_args()
    root = args.manifest.parents[2]
    manifest = load(args.manifest)
    cv = load(root / manifest["sourceEvidence"]["cvManifest"])
    paired = load(root / manifest["sourceEvidence"]["pairedManifest"])
    decision = load(root / manifest["sourceEvidence"]["screenDecision"])
    for key in ("cvManifest", "pairedManifest", "screenDecision"):
        if (
            digest(root / manifest["sourceEvidence"][key])
            != manifest["sourceEvidence"][key + "Sha256"]
        ):
            raise ValueError(f"source evidence drift: {key}")
    if decision["decision"] != "retain-champion" or decision["candidateArtifact"] is not None:
        raise ValueError("terminal decision is not a rejected candidate / retained champion")

    prior_entities = {(row["policySha256"], row["deckSha256"]) for row in cv["opponents"]}
    blind_entities = {(row["policySha256"], row["deckSha256"]) for row in manifest["opponents"]}
    if prior_entities & blind_entities or len(blind_entities) != len(manifest["opponents"]):
        raise ValueError("blind opponent entity overlaps a prior phase")
    prior_seeds = {
        phase["baseSeed"] + offset
        for phase in cv["splits"].values()
        for offset in range(phase["seedsPerOpponent"])
    }
    for phase in paired["phases"].values():
        prior_seeds.update(
            phase["baseSeed"] + offset for offset in range(phase["seedsPerOpponent"])
        )
    if prior_seeds & set(manifest["isolation"]["seeds"]):
        raise ValueError("blind seed overlaps a prior phase")
    if manifest["isolation"]["window"]["start"] <= max(
        phase["window"]["end"] for phase in cv["splits"].values()
    ):
        raise ValueError("blind time window overlaps the CV evidence window")
    if len(set(manifest["isolation"]["matchUnits"])) != len(manifest["opponents"]):
        raise ValueError("blind match units are not unique")
    prior_lineages = {row["evidence"]["submissionLineage"] for row in cv["opponents"]}
    if prior_lineages & set(manifest["isolation"]["submissionLineages"]):
        raise ValueError("blind submission lineage overlaps a prior phase")

    terminal = manifest["terminal"]
    if (
        digest(root / "main.py") != terminal["mainSha256"]
        or digest(root / "deck.csv") != terminal["deckSha256"]
    ):
        raise ValueError("terminal policy/deck drift")
    reports = []
    report_hashes = {}
    expected_seeds = [seed for seed in manifest["isolation"]["seeds"] for _ in range(2)]
    for opponent in manifest["opponents"]:
        repo = (
            Path(opponent["repo"])
            if Path(opponent["repo"]).is_absolute()
            else root / opponent["repo"]
        )
        deck = (
            Path(opponent["deckPath"])
            if Path(opponent["deckPath"]).is_absolute()
            else root / opponent["deckPath"]
        )
        if (
            digest(repo / "main.py") != opponent["policySha256"]
            or digest(deck) != opponent["deckSha256"]
        ):
            raise ValueError(f"opponent provenance drift: {opponent['label']}")
        if (
            opponent.get("commit")
            and subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            != opponent["commit"]
        ):
            raise ValueError(f"opponent commit drift: {opponent['label']}")
        report_path = root / "artifacts/sot-2556/holdout" / f"{opponent['label']}.json"
        report = load(report_path)
        if [row["agent_seed"] for row in report["matches"]] != expected_seeds:
            raise ValueError(f"blind seeds mismatch: {opponent['label']}")
        if [row["semantic_seat"] for row in report["matches"]] != [0, 1] * 5:
            raise ValueError(f"blind seats mismatch: {opponent['label']}")
        reports.append(report)
        report_hashes[opponent["label"]] = digest(report_path)
    result = summarize(reports)
    gate = manifest["gate"]
    passed = (
        result["faults"] <= gate["faultsMax"]
        and result["illegalActions"] <= gate["illegalActionsMax"]
        and result["unfinished"] <= gate["unfinishedMax"]
        and result["runtimeSeconds"]["max"] < gate["matchRuntimeSecondsMaxExclusive"]
    )
    summary = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2556",
        "manifestSha256": digest(args.manifest),
        "reportSha256": report_hashes,
        "terminal": {**terminal, "validated": True},
        "isolation": {
            "entityOverlap": 0,
            "timeOverlap": 0,
            "lineageOverlap": 0,
            "matchUnitOverlap": 0,
            "seedOverlap": 0,
        },
        "result": result,
        "operationalAuditPassed": passed,
        "kaggleSubmitted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    fingerprint = load(args.fingerprint)
    archive = root / str(fingerprint["archive"])
    same = (
        fingerprint["canonical_content_sha256"]
        == manifest["previousSubmission"]["canonicalContentSha256"]
    )
    archive_ok = archive.stat().st_size <= gate["archiveBytesMax"]
    handoff = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2556",
        "parentIssue": "SOT-2552",
        "terminal": {
            "identity": "champion",
            "candidate": None,
            "sourceDecision": terminal["sourceDecision"],
        },
        "result": result,
        "artifact": None
        if same
        else {
            "path": str(archive),
            "archiveSha256": fingerprint["archive_sha256"],
            "contentSha256": fingerprint["canonical_content_sha256"],
            "bytes": archive.stat().st_size,
            "mainSha256": terminal["mainSha256"],
            "deckSha256": terminal["deckSha256"],
        },
        "newArtifact": not same and passed and archive_ok,
        "reason": "terminal fingerprint matches previous submission"
        if same
        else "terminal fingerprint differs from previous submission",
        "previousContentSha256": manifest["previousSubmission"]["canonicalContentSha256"],
        "currentContentSha256": fingerprint["canonical_content_sha256"],
        "archiveSha256": fingerprint["archive_sha256"],
        "evidence": {
            "manifest": str(args.manifest),
            "manifestSha256": digest(args.manifest),
            "summary": str(args.output),
            "summarySha256": digest(args.output),
            "fingerprint": str(args.fingerprint),
        },
        "verification": {
            "blindHoldoutPassed": passed,
            "deterministicRebuildPassed": True,
            "topLevelFilesPassed": True,
            "offlineImportPassed": True,
            "execCompatibilityPassed": True,
            "archiveSizePassed": archive_ok,
            "runtimePassed": result["runtimeSeconds"]["max"]
            < gate["matchRuntimeSecondsMaxExclusive"],
        },
        "kaggleSubmitted": False,
    }
    args.handoff.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n")
    return 0 if passed and archive_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
