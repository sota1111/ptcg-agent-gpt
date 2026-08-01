"""Summarize the preregistered SOT-2255 screen and promotion decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(wins: int, total: int) -> list[float]:
    if not total:
        return [0.0, 1.0]
    z = 1.96
    p = wins / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z / denominator * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2))
    return [centre - margin, centre + margin]


def summarize(reports: dict[str, dict[str, Any]], names: list[str]) -> dict[str, Any]:
    selected = [reports[name] for name in names]
    matches = [match for report in selected for match in report["matches"]]
    wins = sum(bool(match["semantic_won"]) for match in matches)
    runtimes = [float(match["runtime_s"]) for match in matches]
    opponents = {
        name: {
            "wins": int(reports[name]["wins_semantic"]),
            "matches": int(reports[name]["n_matches"]),
            "win_rate": float(reports[name]["winrate_semantic_excl_draws"]),
            "wilson95": reports[name]["wilson95_excl_draws"],
        }
        for name in names
    }
    first = [row for row in matches if row["semantic_seat"] == 0]
    second = [row for row in matches if row["semantic_seat"] == 1]
    return {
        "matches": len(matches),
        "wins": wins,
        "win_rate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "first_seat_win_rate": sum(row["semantic_won"] for row in first) / len(first),
        "second_seat_win_rate": sum(row["semantic_won"] for row in second) / len(second),
        "faults": sum(int(report["faults_semantic"]) for report in selected),
        "unfinished": sum(int(report["unfinished"]) for report in selected),
        "runtime_s": {"mean": statistics.fmean(runtimes), "max": max(runtimes)},
        "opponents": opponents,
    }


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parents[2]
    artifact_root = root / "artifacts" / "sot-2255" / "screen"
    candidate_id = manifest["candidates"][0]["id"]
    identities = ["champion", candidate_id]
    opponents = [*manifest["pools"]["fixed"], *manifest["pools"]["diversified"]]
    results = {}
    report_hashes = {}
    for identity in identities:
        reports = {}
        for opponent in opponents:
            path = artifact_root / f"{identity}-{opponent}.json"
            reports[opponent] = json.loads(path.read_text())
            report_hashes[str(path.relative_to(root))] = digest(path)
        results[identity] = {
            "fixed": summarize(reports, manifest["pools"]["fixed"]),
            "diversified": summarize(reports, manifest["pools"]["diversified"]),
            "worst_matchups": summarize(reports, manifest["pools"]["worst_matchups"]),
        }

    champion, candidate = results["champion"], results[candidate_id]
    reasons = []
    if candidate["diversified"]["win_rate"] <= champion["diversified"]["win_rate"]:
        reasons.append("diversified pool KPI did not improve")
    for opponent in manifest["pools"]["worst_matchups"]:
        before = champion["worst_matchups"]["opponents"][opponent]["win_rate"]
        after = candidate["worst_matchups"]["opponents"][opponent]["win_rate"]
        if after < before:
            reasons.append(f"worst matchup {opponent} regressed")
    if candidate["fixed"]["win_rate"] < champion["fixed"]["win_rate"]:
        reasons.append("fixed pool aggregate regressed")
    if candidate["fixed"]["faults"] or candidate["diversified"]["faults"]:
        reasons.append("fault observed")
    if candidate["fixed"]["unfinished"] or candidate["diversified"]["unfinished"]:
        reasons.append("unfinished match observed")
    champion_runtime = statistics.fmean(
        [champion[pool]["runtime_s"]["mean"] for pool in ("fixed", "diversified")]
    )
    candidate_runtime = statistics.fmean(
        [candidate[pool]["runtime_s"]["mean"] for pool in ("fixed", "diversified")]
    )
    runtime_ratio = candidate_runtime / champion_runtime
    if runtime_ratio > manifest["promotion_gate"]["mean_runtime_ratio_max"]:
        reasons.append("mean runtime exceeded 110% gate")
    if max(candidate[pool]["runtime_s"]["max"] for pool in ("fixed", "diversified")) >= 600:
        reasons.append("600 second runtime constraint exceeded")
    screen_pass = not reasons
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "manifest_sha256": digest(manifest_path),
        "report_sha256": report_hashes,
        "evaluation_fingerprint": {
            "commit": "5418e86d5eda21d858d73dc8a5d57d0aaea8ac99",
            "candidate_main_sha256": (
                "028ff692e4d2371a3a87c90ab9666ffbbd8020c78625acb232dec568b0028f79"
            ),
            "candidate_planner_sha256": (
                "7e1542c716769b76af7a49c96297f7d97dc087d8cbbbf804eda7461dda55deb4"
            ),
            "deck_sha256": manifest["baseline"]["deck_sha256"],
        },
        "terminal_fingerprint": {
            "identity": "champion",
            "behavior_commit": manifest["baseline"]["behavior_commit"],
            "main_sha256": manifest["baseline"]["main_sha256"],
            "deck_sha256": manifest["baseline"]["deck_sha256"],
        },
        "results": results,
        "decision": {
            "candidate": candidate_id,
            "screen_pass": screen_pass,
            "confirm_required": screen_pass,
            "confirm_run": False,
            "runtime_ratio": runtime_ratio,
            "reasons": reasons,
        },
        "confirm": {},
        "promoted": None,
        "champion_behavior_changed": False,
        "hidden_information_leakage": False,
        "conclusion": "candidate failed screen; confirm skipped and champion retained",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.manifest), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
