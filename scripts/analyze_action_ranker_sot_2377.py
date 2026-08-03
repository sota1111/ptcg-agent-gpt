"""Apply the preregistered SOT-2377 screen/confirm promotion gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def summarize(reports: dict[str, dict]) -> dict:
    matches = [match for report in reports.values() for match in report["matches"]]
    seats = {
        str(seat): [match for match in matches if match["semantic_seat"] == seat] for seat in (0, 1)
    }
    return {
        "matches": len(matches),
        "wins": sum(bool(match["semantic_won"]) for match in matches),
        "winRate": sum(bool(match["semantic_won"]) for match in matches) / len(matches),
        "worstMatchupWinRate": min(
            report["winrate_semantic_draws_half"] for report in reports.values()
        ),
        "seatWinRates": {
            seat: sum(bool(match["semantic_won"]) for match in rows) / len(rows)
            for seat, rows in seats.items()
        },
        "faults": sum(report["faults_semantic"] for report in reports.values()),
        "unfinished": sum(report["unfinished"] for report in reports.values()),
        "runtime": {
            "mean": statistics.fmean(match["runtime_s"] for match in matches),
            "max": max(match["runtime_s"] for match in matches),
        },
        "opponents": {
            opponent: {
                "wins": report["wins_semantic"],
                "matches": report["n_matches"],
                "winRate": report["winrate_semantic_draws_half"],
            }
            for opponent, report in reports.items()
        },
    }


def analyze(manifest_path: Path, phase: str) -> dict:
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parents[2]
    artifact_root = root / "artifacts" / "sot-2377-action-ranking" / phase
    identities = ("champion", "candidate")
    pools = manifest["pools"]
    results = {}
    hashes = {}
    for identity in identities:
        reports = {}
        for opponent in [*pools["fixed"], *pools["diversified"]]:
            path = artifact_root / f"{identity}-{opponent}.json"
            reports[opponent] = json.loads(path.read_text())
            hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        results[identity] = {
            "all": summarize(reports),
            "fixed": summarize({name: reports[name] for name in pools["fixed"]}),
            "diversified": summarize({name: reports[name] for name in pools["diversified"]}),
        }
    champion, candidate = results["champion"], results["candidate"]
    reasons = []
    for pool in ("fixed", "diversified"):
        if candidate[pool]["winRate"] <= champion[pool]["winRate"]:
            reasons.append(f"{pool} pool win rate did not strictly improve")
    if candidate["all"]["worstMatchupWinRate"] < champion["all"]["worstMatchupWinRate"]:
        reasons.append("worst matchup regressed")
    for seat in ("0", "1"):
        if candidate["all"]["seatWinRates"][seat] < champion["all"]["seatWinRates"][seat]:
            reasons.append(f"seat {seat} regressed")
    if candidate["all"]["faults"] > champion["all"]["faults"]:
        reasons.append("faults increased")
    if candidate["all"]["unfinished"] > champion["all"]["unfinished"]:
        reasons.append("unfinished matches increased")
    runtime_ratio = candidate["all"]["runtime"]["mean"] / champion["all"]["runtime"]["mean"]
    if runtime_ratio > manifest["promotionGate"]["meanRuntimeRatioMax"]:
        reasons.append("mean runtime exceeded 110% of champion")
    if candidate["all"]["runtime"]["max"] >= 600:
        reasons.append("maximum match runtime reached 600 seconds")
    passed = not reasons
    return {
        "schemaVersion": "1.0.0",
        "issue": manifest["issue"],
        "phase": phase,
        "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "reportSha256": hashes,
        "results": results,
        "runtimeRatio": runtime_ratio,
        "passed": passed,
        "reasons": reasons,
        "confirmRequired": phase == "screen" and passed,
        "promoted": passed if phase == "confirm" else False,
        "championBehaviorChanged": phase == "confirm" and passed,
        "kaggleSubmissionPerformed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--phase", choices=("screen", "confirm"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.manifest, args.phase)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
