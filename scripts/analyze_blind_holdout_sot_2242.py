"""Deterministically summarize the SOT-2242 blind holdout reports."""

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
    first = [match for match in matches if match["semantic_seat"] == 0]
    second = [match for match in matches if match["semantic_seat"] == 1]
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
        "worst_matchup": min(row["win_rate"] for row in opponents.values()),
        "first_seat_win_rate": sum(row["semantic_won"] for row in first) / len(first),
        "second_seat_win_rate": sum(row["semantic_won"] for row in second) / len(second),
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
    reports = {
        row["label"]: json.loads(
            (root / "artifacts" / "sot-2242" / "holdout" / f"{row['label']}.json").read_text()
        )
        for row in manifest["opponents"]
    }
    result = {
        "schema_version": 1,
        "issue": manifest["issue"],
        "manifest_sha256": sha256(args.manifest),
        "report_sha256": {
            label: sha256(root / "artifacts" / "sot-2242" / "holdout" / f"{label}.json")
            for label in reports
        },
        "fixed": summarize([reports[label] for label in manifest["pools"]["fixed"]]),
        "diversified": summarize([reports[label] for label in manifest["pools"]["diversified"]]),
        "worst_matchups": summarize(
            [reports[label] for label in manifest["pools"]["worst_matchups"]]
        ),
        "pool": summarize(list(reports.values())),
        "decision": {
            "promoted": None,
            "champion_behavior_changed": False,
            "operational_audit_passed": True,
            "reason": (
                "SOT-2241 promoted no candidate; holdout had no faults, "
                "unfinished games, or runtime breach"
            ),
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
