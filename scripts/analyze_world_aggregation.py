"""Aggregate SOT-2117 world-aggregation promotion trials."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def summarize(paths: list[Path]) -> dict:
    reports = [json.loads(path.read_text()) for path in paths]
    matches = [match for report in reports for match in report["matches"]]
    wins = sum(report["wins_semantic"] for report in reports)
    losses = sum(report["wins_opp"] for report in reports)
    first = [match for match in matches if match["semantic_first"]]
    second = [match for match in matches if not match["semantic_first"]]
    runtimes = [float(match["runtime_s"]) for match in matches]
    return {
        "matches": len(matches),
        "wins": wins,
        "losses": losses,
        "pool_kpi": wins / (wins + losses) if wins + losses else None,
        "matchups": {
            report["opponent"]: {
                "wins": report["wins_semantic"],
                "losses": report["wins_opp"],
            }
            for report in reports
        },
        "seat": {
            "first_win_rate": sum(match["semantic_won"] for match in first) / len(first),
            "second_win_rate": sum(match["semantic_won"] for match in second) / len(second),
            "paired_gap": (
                sum(match["semantic_won"] for match in first) / len(first)
                - sum(match["semantic_won"] for match in second) / len(second)
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


def analyze(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parents[2]
    modes = [manifest["baseline"]["aggregation"]] + [
        candidate["id"] for candidate in manifest["candidates"]
    ]
    screen = {
        mode: summarize(
            [
                root / "artifacts" / "sot-2117" / "screen" / f"{mode}-{opponent['id']}.json"
                for opponent in manifest["opponents"]
            ]
        )
        for mode in modes
    }
    champion = screen[manifest["baseline"]["aggregation"]]
    passing = [
        mode
        for mode in modes[1:]
        if screen[mode]["pool_kpi"] > champion["pool_kpi"]
        and screen[mode]["faults"] <= champion["faults"]
        and screen[mode]["timeouts"] <= champion["timeouts"]
        and screen[mode]["runtime_s"]["mean"] <= champion["runtime_s"]["mean"] * 1.1
        and screen[mode]["runtime_s"]["max_think"] < 600
    ]
    return {
        "issue": manifest["issue"],
        "manifest": str(manifest_path),
        "baseline": manifest["baseline"],
        "frozen_search": manifest["frozen_search"],
        "screen": screen,
        "screen_passing_candidates": passing,
        "confirm": {},
        "decision": {
            "promote": False,
            "candidate": None,
            "reason": (
                "no candidate exceeded champion pool KPI at the preregistered screen gate"
                if not passing
                else "confirm required"
            ),
            "champion_aggregation": manifest["baseline"]["aggregation"],
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
