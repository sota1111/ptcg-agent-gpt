"""Validate and summarize the preregistered SOT-2347 terminal blind audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(wins: int, total: int) -> list[float]:
    z = 1.96
    p = wins / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z / denominator * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2))
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [match for report in reports for match in report["matches"]]
    if not matches:
        raise ValueError("holdout contains no matches")
    wins = sum(bool(match["semantic_won"]) for match in matches)
    runtimes = [float(match["runtime_s"]) for match in matches]
    seats = {
        str(seat): [match for match in matches if match["semantic_seat"] == seat] for seat in (0, 1)
    }
    opponents = {
        report["opponent"]: {
            "matches": report["n_matches"],
            "wins": report["wins_semantic"],
            "win_rate": report["winrate_semantic_excl_draws"],
            "wilson95": report["wilson95_excl_draws"],
            "faults": report["faults_semantic"],
            "unfinished": report["unfinished"],
        }
        for report in reports
    }
    return {
        "matches": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "win_rate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "worst_matchup": min(opponents, key=lambda label: opponents[label]["win_rate"]),
        "worst_matchup_win_rate": min(row["win_rate"] for row in opponents.values()),
        "seat_win_rate": {
            seat: sum(bool(row["semantic_won"]) for row in rows) / len(rows)
            for seat, rows in seats.items()
        },
        "faults": sum(report["faults_semantic"] for report in reports),
        "unfinished": sum(report["unfinished"] for report in reports),
        "illegal_actions": sum(
            1
            for match in matches
            if match.get("fault") and "illegal" in str(match["fault"]).lower()
        ),
        "runtime_s": {
            "mean": statistics.fmean(runtimes),
            "p50": statistics.median(runtimes),
            "p95": sorted(runtimes)[math.ceil(0.95 * len(runtimes)) - 1],
            "max": max(runtimes),
        },
        "opponents": opponents,
    }


def validate_provenance(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    provenance = manifest["provenance"]
    paths = {
        "main_sha256": root / "main.py",
        "deck_sha256": root / "deck.csv",
        "candidate_artifact_sha256": root / "agents/public_value_model.json",
        "decision_sha256": root / "artifacts/sot-2346-public-value/decision.json",
        "source_manifest_sha256": root / "eval/manifests/sot-2346-public-value.json",
    }
    actual = {key: sha256(path) for key, path in paths.items()}
    for key, value in actual.items():
        expected = (
            provenance[f"terminal_{key}"]
            if key in {"main_sha256", "deck_sha256"}
            else provenance[key]
        )
        if value != expected:
            raise ValueError(f"frozen provenance drift: {key}")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", provenance["sot_2346_terminal_commit"], "HEAD"],
        cwd=root,
        check=True,
    )
    opponents = {}
    for opponent in manifest["opponents"]:
        opponent_root = Path(opponent["repo"])
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=opponent_root, text=True
        ).strip()
        deck = sha256(opponent_root / "deck.csv")
        if commit != opponent["commit"] or deck != opponent["deck_sha256"]:
            raise ValueError(f"{opponent['label']}: frozen opponent provenance changed")
        opponents[opponent["label"]] = {"commit": commit, "deck_sha256": deck}
    return {**actual, "opponents": opponents, "validated": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.parents[2]
    report_dir = root / "artifacts/sot-2347/holdout"
    reports = {
        row["label"]: json.loads((report_dir / f"{row['label']}.json").read_text())
        for row in manifest["opponents"]
    }
    expected_seeds = [seed for seed in manifest["isolation"]["holdout_seeds"] for _ in range(2)]
    for opponent in manifest["opponents"]:
        report = reports[opponent["label"]]
        if [match["agent_seed"] for match in report["matches"]] != expected_seeds:
            raise ValueError(f"{opponent['label']}: seed contract mismatch")
        if [match["semantic_seat"] for match in report["matches"]] != [0, 1] * 5:
            raise ValueError(f"{opponent['label']}: seat contract mismatch")
        if report["opponent_repo"] != opponent["repo"]:
            raise ValueError(f"{opponent['label']}: opponent contract mismatch")
    pool = summarize(list(reports.values()))
    gate = manifest["gate"]
    passed = (
        pool["faults"] == gate["faults"]
        and pool["unfinished"] == gate["unfinished"]
        and pool["illegal_actions"] == gate["illegal_actions"]
        and pool["runtime_s"]["max"] < gate["match_runtime_seconds_max"]
    )
    result = {
        "schema_version": 1,
        "issue": manifest["issue"],
        "manifest_sha256": sha256(args.manifest),
        "report_sha256": {label: sha256(report_dir / f"{label}.json") for label in reports},
        "terminal": validate_provenance(root, manifest),
        "fixed": summarize([reports[label] for label in manifest["pools"]["fixed"]]),
        "diversified": summarize([reports[label] for label in manifest["pools"]["diversified"]]),
        "worst_matchups": summarize(
            [reports[label] for label in manifest["pools"]["worst_matchups"]]
        ),
        "pool": pool,
        "decision": {
            "terminal_identity": "champion",
            "promotion_outcome": "champion_retained",
            "promoted_candidate": None,
            "candidate_behavior_reverted": True,
            "operational_audit_passed": passed,
            "kaggle_submitted": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
