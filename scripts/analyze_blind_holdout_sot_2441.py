"""Validate and summarize the preregistered SOT-2441 blind terminal audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(wins: int, total: int) -> list[float]:
    z = 1.96
    rate = wins / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z / denominator * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total))
    return [max(0, center - margin), min(1, center + margin)]


def summarize(reports: list[dict]) -> dict:
    matches = [match for report in reports for match in report["matches"]]
    wins = sum(bool(match["semantic_won"]) for match in matches)
    runtimes = [float(match["runtime_s"]) for match in matches]
    opponents = {
        report["opponent"]: {
            "matches": report["n_matches"],
            "wins": report["wins_semantic"],
            "win_rate": report["winrate_semantic_excl_draws"],
            "faults": report["faults_semantic"],
            "unfinished": report["unfinished"],
        }
        for report in reports
    }
    seats = {str(seat): [m for m in matches if m["semantic_seat"] == seat] for seat in (0, 1)}
    return {
        "matches": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "win_rate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "worst_matchup": min(opponents, key=lambda name: opponents[name]["win_rate"]),
        "worst_matchup_win_rate": min(row["win_rate"] for row in opponents.values()),
        "seat_win_rate": {
            seat: sum(bool(m["semantic_won"]) for m in rows) / len(rows)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.parents[2]
    report_dir = root / "artifacts/sot-2441/holdout"
    reports = {
        opponent["label"]: json.loads((report_dir / f"{opponent['label']}.json").read_text())
        for opponent in manifest["opponents"]
    }
    expected_seeds = [seed for seed in manifest["isolation"]["holdout_seeds"] for _ in range(2)]
    for opponent in manifest["opponents"]:
        report = reports[opponent["label"]]
        if (
            [match["agent_seed"] for match in report["matches"]] != expected_seeds
            or [match["semantic_seat"] for match in report["matches"]] != [0, 1] * 5
            or report["opponent_repo"] != opponent["repo"]
        ):
            raise ValueError(f"{opponent['label']}: holdout contract mismatch")
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=opponent["repo"], text=True
        ).strip()
        if (
            current_commit != opponent["commit"]
            or sha(Path(opponent["repo"]) / "deck.csv") != opponent["deck_sha256"]
        ):
            raise ValueError(f"{opponent['label']}: opponent provenance drift")
    provenance = manifest["provenance"]
    paths = {
        "main_sha256": root / "main.py",
        "deck_sha256": root / "deck.csv",
        "candidate_artifact_sha256": root / "agents/tactical_controller.py",
        "decision_sha256": root / "artifacts/sot-2440/screen-decision.json",
        "source_contract_sha256": root / "eval/manifests/sot-2439-public-tactical-contract.json",
    }
    actual = {name: sha(path) for name, path in paths.items()}
    for name, digest in actual.items():
        key = "terminal_" + name if name in {"main_sha256", "deck_sha256"} else name
        if digest != provenance[key]:
            raise ValueError(f"frozen provenance drift: {name}")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", provenance["sot_2440_terminal_commit"], "HEAD"],
        cwd=root,
        check=True,
    )
    pool = summarize(list(reports.values()))
    gate = manifest["gate"]
    passed = (
        pool["faults"] == gate["faults"]
        and pool["unfinished"] == gate["unfinished"]
        and pool["illegal_actions"] == gate["illegal_actions"]
        and pool["runtime_s"]["max"] < gate["match_runtime_seconds_max"]
    )
    output = {
        "schema_version": 1,
        "issue": "SOT-2441",
        "manifest_sha256": sha(args.manifest),
        "report_sha256": {name: sha(report_dir / f"{name}.json") for name in reports},
        "terminal": {
            **actual,
            "identity": "champion",
            "candidate": None,
            "source_decision": "champion_retained_after_screen_failure",
            "validated": True,
        },
        "fixed": summarize([reports[name] for name in manifest["pools"]["fixed"]]),
        "diversified": summarize([reports[name] for name in manifest["pools"]["diversified"]]),
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
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
