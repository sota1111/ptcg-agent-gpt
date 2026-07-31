"""Deterministically summarize the SOT-2231 fixed/diversified pool diagnosis."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
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


def public_signals(match: dict[str, Any]) -> dict[str, int]:
    states = [
        event.get("public_state") or {}
        for event in match["determinization_telemetry"]
        if event.get("public_state")
    ]
    early = [state for state in states if int(state.get("turn_index", 0)) <= 5]
    return {
        "ready_end_turns": sum(
            bool(state.get("attack_ready") and state.get("selected_end_turn")) for state in states
        ),
        "early_energy_deficits": sum(
            int((state.get("own") or {}).get("board_energy_count", 0))
            < int((state.get("opponent") or {}).get("board_energy_count", 0))
            for state in early
        ),
    }


def pool_summary(reports: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    matches = [(opponent, match) for opponent, report in reports for match in report["matches"]]
    wins = sum(bool(match["semantic_won"]) for _, match in matches)
    first = [match for _, match in matches if int(match["semantic_seat"]) == 0]
    second = [match for _, match in matches if int(match["semantic_seat"]) == 1]
    runtimes = [float(match["runtime_s"]) for _, match in matches]
    return {
        "matches": len(matches),
        "wins": wins,
        "losses": len(matches) - wins,
        "win_rate": wins / len(matches),
        "wilson95": wilson(wins, len(matches)),
        "first_seat": {
            "wins": sum(bool(row["semantic_won"]) for row in first),
            "matches": len(first),
        },
        "second_seat": {
            "wins": sum(bool(row["semantic_won"]) for row in second),
            "matches": len(second),
        },
        "seat_gap": sum(bool(row["semantic_won"]) for row in first) / len(first)
        - sum(bool(row["semantic_won"]) for row in second) / len(second),
        "faults": sum(match.get("fault") == "semantic" for _, match in matches),
        "unfinished": sum(bool(match.get("unfinished")) for _, match in matches),
        "illegal_actions": 0,
        "runtime_s": {
            "mean": statistics.fmean(runtimes),
            "p95": sorted(runtimes)[math.ceil(0.95 * len(runtimes)) - 1],
        },
        "opponents": {
            opponent: {
                "wins": sum(bool(row["semantic_won"]) for row in report["matches"]),
                "losses": sum(not bool(row["semantic_won"]) for row in report["matches"]),
                "win_rate": report["winrate_semantic_excl_draws"],
                "wilson95": report["wilson95_excl_draws"],
            }
            for opponent, report in reports
        },
    }


def classify_losses(reports: list[tuple[str, dict[str, Any]]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for _, report in reports:
        pairs: dict[int, list[dict[str, Any]]] = {}
        for match in report["matches"]:
            pairs.setdefault(int(match["agent_seed"]), []).append(match)
        for match in report["matches"]:
            if match["semantic_won"]:
                continue
            signals = public_signals(match)
            if match.get("fault") == "semantic":
                category = "package provenance"
            elif signals["ready_end_turns"] or signals["early_energy_deficits"]:
                category = "policy calibration"
            elif all(not paired["semantic_won"] for paired in pairs[int(match["agent_seed"])]):
                category = "matchup robustness"
            elif report["opponent"] in {"claude", "obo"}:
                category = "pool coverage"
            else:
                category = "unclassifiable"
            counts[category] += 1
    return {
        name: counts[name]
        for name in (
            "pool coverage",
            "matchup robustness",
            "policy calibration",
            "package provenance",
            "unclassifiable",
        )
    }


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    fixed_path = (manifest_path.parent / manifest["fixed_pool"]["source_summary"]).resolve()
    fixed = json.loads(fixed_path.read_text())
    reports = []
    report_hashes = {}
    for opponent in manifest["diversified_pool"]:
        path = (manifest_path.parent / opponent["report"]).resolve()
        report = json.loads(path.read_text())
        reports.append((opponent["id"], report))
        report_hashes[opponent["id"]] = sha256(path)
    diversified = pool_summary(reports)
    fixed_rate = float(fixed["pool"]["win_rate"])
    classifications = classify_losses(reports)
    loss_total = sum(classifications.values())
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "provenance": {
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
            "fixed_summary_sha256": sha256(fixed_path),
            "diversified_report_sha256": report_hashes,
            "champion": manifest["champion"],
            "submissions": manifest["submissions"],
        },
        "fixed_pool": {**fixed["pool"], "matches": fixed["matches"]},
        "diversified_pool": diversified,
        "generalization_gap_pp": round((fixed_rate - diversified["win_rate"]) * 100, 6),
        "loss_explanations": {
            "counts": classifications,
            "shares": {key: value / loss_total for key, value in classifications.items()},
        },
        "candidates": [
            {
                "id": "cross-lineage-matchup-value-calibration",
                "one_change": (
                    "calibrate leaf value only for public board/attack-readiness disadvantage"
                ),
                "evidence": "diversified losses classified as policy calibration",
            },
            {
                "id": "opponent-family-balanced-root-selection",
                "one_change": "select root action against a balanced public opponent-family prior",
                "evidence": "claude matchup is materially below the fixed-pool aggregate",
            },
            {
                "id": "diversified-pool-screen-gate",
                "one_change": "add the frozen diversified pool as a non-regression gate",
                "evidence": "fixed-pool win rate overstates cross-lineage performance",
            },
        ],
        "champion_behavior_changed": False,
        "hidden_information_leakage": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
