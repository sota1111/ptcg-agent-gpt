"""Aggregate SOT-2175 public-state tempo promotion trials."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def summarize(paths: list[Path]) -> dict:
    reports = [json.loads(path.read_text()) for path in paths]
    matches = [match for report in reports for match in report["matches"]]
    first = [match for match in matches if match["semantic_first"]]
    second = [match for match in matches if not match["semantic_first"]]
    runtimes = [float(match["runtime_s"]) for match in matches]
    wins = sum(bool(match["semantic_won"]) for match in matches)
    return {
        "matches": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "pool_kpi": wins / len(matches),
        "matchups": {
            report["opponent"]: {
                "wins": report["wins_semantic"],
                "losses": report["wins_opp"],
            }
            for report in reports
        },
        "seat": {
            "first_win_rate": sum(bool(match["semantic_won"]) for match in first) / len(first),
            "second_win_rate": sum(bool(match["semantic_won"]) for match in second) / len(second),
            "paired_gap": (
                sum(bool(match["semantic_won"]) for match in first) / len(first)
                - sum(bool(match["semantic_won"]) for match in second) / len(second)
            ),
        },
        "faults": sum(report["faults_semantic"] for report in reports),
        "timeouts": sum(report["unfinished"] for report in reports),
        "runtime_s": {
            "mean": statistics.fmean(runtimes),
            "p95": sorted(runtimes)[min(len(runtimes) - 1, int(len(runtimes) * 0.95))],
            "max_think": max(report["max_think_s"]["semantic"] for report in reports),
        },
    }


def passes(candidate: dict, champion: dict) -> bool:
    return (
        candidate["pool_kpi"] > champion["pool_kpi"]
        and candidate["seat"]["paired_gap"] <= champion["seat"]["paired_gap"] + 0.1
        and candidate["faults"] <= champion["faults"]
        and candidate["timeouts"] <= champion["timeouts"]
        and candidate["runtime_s"]["mean"] <= champion["runtime_s"]["mean"] * 1.1
        and candidate["runtime_s"]["max_think"] < 600
    )


def analyze(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parents[2]
    modes = ["champion", *[candidate["id"] for candidate in manifest["candidates"]]]
    screen = {
        mode: summarize(
            [
                root / "artifacts" / "sot-2175" / "screen" / f"{mode}-{opp['id']}.json"
                for opp in manifest["opponents"]
            ]
        )
        for mode in modes
    }
    passing = [mode for mode in modes[1:] if passes(screen[mode], screen["champion"])]
    confirm = {}
    for mode in passing:
        candidate_paths = [
            root / "artifacts" / "sot-2175" / "confirm" / f"{mode}-{opp['id']}.json"
            for opp in manifest["opponents"]
        ]
        champion_paths = [
            root / "artifacts" / "sot-2175" / "confirm" / f"champion-{opp['id']}.json"
            for opp in manifest["opponents"]
        ]
        if all(path.exists() for path in candidate_paths + champion_paths):
            confirm[mode] = summarize(candidate_paths)
            confirm["champion"] = summarize(champion_paths)
    promoted = next(
        (
            mode
            for mode in passing
            if mode in confirm and passes(confirm[mode], confirm["champion"])
        ),
        None,
    )
    return {
        "issue": manifest["issue"],
        "manifest": str(manifest_path),
        "baseline": manifest["baseline"],
        "frozen_search": manifest["frozen_search"],
        "candidates": manifest["candidates"],
        "screen": screen,
        "screen_passing_candidates": passing,
        "confirm": confirm,
        "decision": {
            "promote": promoted is not None,
            "candidate": promoted,
            "reason": (
                "candidate passed independent confirm"
                if promoted
                else "no candidate passed all preregistered screen and confirm gates"
            ),
            "champion_behavior_changed": promoted is not None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
