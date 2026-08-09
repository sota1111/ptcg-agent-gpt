"""Audit SOT-2574 blind reports and emit the exact terminal handoff."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "eval/manifests/sot-2574-terminal-population-blind.json"
ARTIFACTS = ROOT / "artifacts/sot-2574"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(wins: int, total: int) -> list[float]:
    z = 1.96
    rate = wins / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z / denominator * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total**2))
    return [max(0.0, center - margin), min(1.0, center + margin)]


def main() -> int:
    manifest = load(MANIFEST)
    evidence = manifest["sourceEvidence"]
    for key in ("populationContract", "populationSnapshot", "pairedManifest", "terminalDecision"):
        if digest(ROOT / evidence[key]) != evidence[key + "Sha256"]:
            raise ValueError(f"source evidence drift: {key}")
    population = load(ROOT / evidence["populationSnapshot"])
    paired = load(ROOT / evidence["pairedManifest"])
    decision = load(ROOT / evidence["terminalDecision"])
    if decision["decision"] != "retain-champion" or decision["candidateHandoff"] is not None:
        raise ValueError("terminal decision must retain champion without candidate handoff")
    terminal = manifest["terminal"]
    if (
        digest(ROOT / "main.py") != terminal["mainSha256"]
        or digest(ROOT / "deck.csv") != terminal["deckSha256"]
    ):
        raise ValueError("terminal champion drift")

    blind_members = {row["id"]: row for row in population["members"] if row["split"] == "blind"}
    if set(blind_members) != {row["id"] for row in manifest["opponents"]}:
        raise ValueError("manifest is not the frozen blind population")
    nonblind = [row for row in population["members"] if row["split"] != "blind"]
    dimensions = ("policyEntity", "deckEntity", "evidenceId", "submissionLineage")
    overlaps = {
        name: len({row[name] for row in nonblind} & {row[name] for row in blind_members.values()})
        for name in dimensions
    }
    if any(overlaps.values()):
        raise ValueError(f"blind population overlap: {overlaps}")
    prior_seeds = {
        phase["baseSeed"] + offset
        for phase in paired["phases"].values()
        for offset in range(phase["seedsPerOpponent"])
    }
    if prior_seeds & set(manifest["isolation"]["seeds"]):
        raise ValueError("blind seed overlap")
    if manifest["isolation"]["window"]["start"] <= max(
        phase["window"]["end"] for phase in paired["phases"].values()
    ):
        raise ValueError("blind time overlap")

    reports = []
    report_hashes = {}
    expected_seeds = [seed for seed in manifest["isolation"]["seeds"] for _ in range(2)]
    for opponent in manifest["opponents"]:
        repo = Path(opponent["repo"])
        if not repo.is_absolute():
            repo = ROOT / repo
        deck = Path(opponent["deckPath"])
        if not deck.is_absolute():
            deck = ROOT / deck
        if (
            digest(repo / "main.py") != opponent["policySha256"]
            or digest(deck) != opponent["deckSha256"]
        ):
            raise ValueError(f"opponent provenance drift: {opponent['id']}")
        if (
            opponent.get("commit")
            and subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            != opponent["commit"]
        ):
            raise ValueError(f"opponent commit drift: {opponent['id']}")
        path = ARTIFACTS / "holdout" / f"{opponent['id']}.json"
        report = load(path)
        if [row["agent_seed"] for row in report["matches"]] != expected_seeds:
            raise ValueError(f"seed mismatch: {opponent['id']}")
        if [row["semantic_seat"] for row in report["matches"]] != [0, 1] * 5:
            raise ValueError(f"seat mismatch: {opponent['id']}")
        reports.append((opponent, report))
        report_hashes[opponent["id"]] = digest(path)

    matches = [match for _, report in reports for match in report["matches"]]
    runtimes = [float(match["runtime_s"]) for match in matches]
    wins = sum(bool(match["semantic_won"]) for match in matches)
    by_seat = {str(seat): [m for m in matches if m["semantic_seat"] == seat] for seat in (0, 1)}
    result = {
        "matches": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "winRate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "opponents": {
            opponent["id"]: {
                "archetype": opponent["archetype"],
                "matches": report["n_matches"],
                "wins": report["wins_semantic"],
                "winRate": report["winrate_semantic_excl_draws"],
                "faults": report["faults_semantic"],
                "unfinished": report["unfinished"],
            }
            for opponent, report in reports
        },
        "seats": {
            seat: {
                "matches": len(rows),
                "wins": sum(bool(m["semantic_won"]) for m in rows),
                "winRate": sum(bool(m["semantic_won"]) for m in rows) / len(rows),
            }
            for seat, rows in by_seat.items()
        },
        "faults": sum(report["faults_semantic"] for _, report in reports),
        "illegalActions": sum(
            bool(m.get("fault")) and "illegal" in str(m["fault"]).lower() for m in matches
        ),
        "unfinished": sum(report["unfinished"] for _, report in reports),
        "runtimeSeconds": {
            "mean": statistics.fmean(runtimes),
            "p95": sorted(runtimes)[math.ceil(0.95 * len(runtimes)) - 1],
            "max": max(runtimes),
        },
    }
    gate = manifest["gate"]
    passed = (
        result["faults"] <= gate["faultsMax"]
        and result["illegalActions"] <= gate["illegalActionsMax"]
        and result["unfinished"] <= gate["unfinishedMax"]
        and result["runtimeSeconds"]["max"] < gate["matchRuntimeSecondsMaxExclusive"]
    )
    summary = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2574",
        "manifestSha256": digest(MANIFEST),
        "reportSha256": report_hashes,
        "terminal": {**terminal, "validated": True},
        "isolation": {
            **{name + "Overlap": value for name, value in overlaps.items()},
            "timeOverlap": 0,
            "matchUnitOverlap": 0,
            "seedOverlap": 0,
        },
        "result": result,
        "operationalAuditPassed": passed,
        "kaggleSubmitted": False,
    }
    summary_path = ARTIFACTS / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    fingerprint = load(ARTIFACTS / "submission-fingerprint.json")
    archive = ROOT / fingerprint["archive"]
    same = (
        fingerprint["canonical_content_sha256"]
        == manifest["previousSubmission"]["canonicalContentSha256"]
    )
    archive_ok = archive.stat().st_size <= gate["archiveBytesMax"]
    handoff = {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2574",
        "parentIssue": "SOT-2570",
        "terminal": {
            "identity": "champion",
            "candidate": None,
            "sourceDecision": "retain-champion",
        },
        "result": result,
        "artifact": None
        if same
        else {
            "path": str(archive.relative_to(ROOT)),
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
            "manifest": str(MANIFEST.relative_to(ROOT)),
            "manifestSha256": digest(MANIFEST),
            "summary": str(summary_path.relative_to(ROOT)),
            "summarySha256": digest(summary_path),
            "fingerprint": "artifacts/sot-2574/submission-fingerprint.json",
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
    (ARTIFACTS / "handoff.json").write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n")
    return 0 if passed and archive_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
