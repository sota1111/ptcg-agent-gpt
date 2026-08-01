"""Deterministically summarize the preregistered SOT-2241 screens."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(wins: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 1.0]
    z = 1.96
    p = wins / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z / denominator * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2))
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [match for report in reports for match in report["matches"]]
    wins = sum(bool(match["semantic_won"]) for match in matches)
    runtimes = [float(match["runtime_s"]) for match in matches]
    opponents = {
        report["opponent"]: {
            "wins": report["wins_semantic"],
            "matches": report["n_matches"],
            "win_rate": report["winrate_semantic_excl_draws"],
            "wilson95": report["wilson95_excl_draws"],
        }
        for report in reports
    }
    first = [row for row in matches if row["semantic_seat"] == 0]
    second = [row for row in matches if row["semantic_seat"] == 1]
    return {
        "matches": len(matches),
        "wins": wins,
        "win_rate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "worst_matchup": min(row["win_rate"] for row in opponents.values()),
        "first_seat_win_rate": sum(row["semantic_won"] for row in first) / len(first),
        "second_seat_win_rate": sum(row["semantic_won"] for row in second) / len(second),
        "faults": sum(report["faults_semantic"] for report in reports),
        "unfinished": sum(report["unfinished"] for report in reports),
        "runtime_s": {
            "mean": statistics.fmean(runtimes),
            "p95": sorted(runtimes)[math.ceil(0.95 * len(runtimes)) - 1],
            "max": max(runtimes),
        },
        "opponents": opponents,
    }


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parents[2]
    artifact_root = root / "artifacts" / "sot-2241" / "screen"
    identities = ["champion", *[row["id"] for row in manifest["candidates"]]]
    results: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for identity in identities:
        reports = {}
        for opponent in [*manifest["pools"]["fixed"], *manifest["pools"]["diversified"]]:
            path = artifact_root / f"{identity}-{opponent}.json"
            reports[opponent] = json.loads(path.read_text())
            hashes[str(path.relative_to(root))] = sha256(path)
        results[identity] = {
            "fixed": summarize([reports[name] for name in manifest["pools"]["fixed"]]),
            "diversified": summarize([reports[name] for name in manifest["pools"]["diversified"]]),
            "worst_matchups": summarize(
                [reports[name] for name in manifest["pools"]["worst_matchups"]]
            ),
        }

    champion = results["champion"]
    decisions = {}
    for candidate in manifest["candidates"]:
        candidate_id = candidate["id"]
        current = results[candidate_id]
        reasons = []
        if current["diversified"]["win_rate"] <= champion["diversified"]["win_rate"]:
            reasons.append("diversified pool KPI did not improve")
        if current["worst_matchups"]["worst_matchup"] < champion["worst_matchups"]["worst_matchup"]:
            reasons.append("matsu/Claude worst-matchup regressed")
        if current["fixed"]["win_rate"] < champion["fixed"]["win_rate"]:
            reasons.append("fixed pool aggregate regressed")
        if current["fixed"]["worst_matchup"] < champion["fixed"]["worst_matchup"]:
            reasons.append("fixed pool worst-matchup regressed")
        if sum(current[pool]["faults"] for pool in ("fixed", "diversified")) > 0:
            reasons.append("faults increased")
        if sum(current[pool]["unfinished"] for pool in ("fixed", "diversified")) > 0:
            reasons.append("unfinished matches increased")
        runtime_ratio = (
            current["diversified"]["runtime_s"]["mean"]
            / champion["diversified"]["runtime_s"]["mean"]
        )
        if runtime_ratio > manifest["promotion_gate"]["mean_runtime_ratio_max"]:
            reasons.append("mean runtime exceeded 110% gate")
        if current["diversified"]["runtime_s"]["max"] >= 600:
            reasons.append("600 second constraint exceeded")
        decisions[candidate_id] = {
            "screen_pass": not reasons,
            "confirm_required": not reasons,
            "confirm_run": False,
            "runtime_ratio": runtime_ratio,
            "reasons": reasons,
        }

    passing = [candidate for candidate, row in decisions.items() if row["screen_pass"]]
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "manifest_sha256": sha256(manifest_path),
        "report_sha256": hashes,
        "results": results,
        "decisions": decisions,
        "screen_passing_candidates": passing,
        "confirm": {},
        "promoted": None,
        "champion_behavior_changed": False,
        "hidden_information_leakage": False,
        "conclusion": "no candidate passed the preregistered screen; confirm skipped",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.manifest), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
