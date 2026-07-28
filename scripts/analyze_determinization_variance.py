"""Aggregate paired-seat determinization traces for SOT-2116."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

CATEGORIES = (
    "sample_duplicate_or_low_diversity",
    "world_aggregation_outlier_sensitivity",
    "seat_specific_public_state_difference",
    "unclassified",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision_metrics(match: dict[str, Any]) -> dict[str, Any]:
    events = match["determinization_telemetry"]
    fingerprints = [
        root["fingerprint"] for event in events for root in event.get("world_roots", [])
    ]
    generated = sum(int(event.get("generated_worlds", 0)) for event in events)
    selected_spreads = []
    majority_disagreements = 0
    measurable = 0
    for event in events:
        selected = int(event.get("selected_action_index", 0))
        roots = event.get("world_roots", [])
        values = []
        per_world_best = []
        for root in roots:
            actions = root.get("actions", [])
            if selected < len(actions) and actions[selected].get("value_mean") is not None:
                values.append(float(actions[selected]["value_mean"]))
            if actions:
                per_world_best.append(
                    max(
                        range(len(actions)),
                        key=lambda index: (
                            int(actions[index]["visits"]),
                            actions[index].get("value_mean") or 0.0,
                            -index,
                        ),
                    )
                )
        if len(values) >= 2:
            measurable += 1
            selected_spreads.append(max(values) - min(values))
        if per_world_best and Counter(per_world_best).most_common(1)[0][0] != selected:
            majority_disagreements += 1
    return {
        "decisions": len(events),
        "generated_worlds": generated,
        "unique_fingerprints": len(set(fingerprints)),
        "fingerprint_unique_rate": (
            len(set(fingerprints)) / len(fingerprints) if fingerprints else 0.0
        ),
        "measurable_value_decisions": measurable,
        "selected_value_spread_mean": (
            statistics.fmean(selected_spreads) if selected_spreads else 0.0
        ),
        "selected_value_spread_max": max(selected_spreads, default=0.0),
        "world_majority_disagreements": majority_disagreements,
    }


def classify(match: dict[str, Any], pair: dict[int, dict[str, Any]]) -> dict[str, Any]:
    metrics = decision_metrics(match)
    if metrics["generated_worlds"] and metrics["fingerprint_unique_rate"] < 0.75:
        category = CATEGORIES[0]
        evidence = f"fingerprint_unique_rate={metrics['fingerprint_unique_rate']:.3f}"
    elif (
        metrics["selected_value_spread_max"] >= 0.35
        or metrics["world_majority_disagreements"] > 0
    ):
        category = CATEGORIES[1]
        evidence = (
            f"max_value_spread={metrics['selected_value_spread_max']:.3f}; "
            f"majority_disagreements={metrics['world_majority_disagreements']}"
        )
    elif pair.get(1 - int(match["semantic_seat"]), {}).get("semantic_won"):
        category = CATEGORIES[2]
        evidence = "same agent seed won from reversed seat"
    else:
        category = CATEGORIES[3]
        evidence = "no exclusive threshold met"
    return {"category": category, "evidence": evidence, "metrics": metrics}


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    matchups = []
    classified_losses = []
    all_matches = []
    for opponent in manifest["opponents"]:
        report_path = (manifest_path.parent / opponent["report"]).resolve()
        matches = json.loads(report_path.read_text())["matches"]
        all_matches.extend(matches)
        pairs: dict[int, dict[int, dict[str, Any]]] = {}
        for match in matches:
            pairs.setdefault(int(match["agent_seed"]), {})[int(match["semantic_seat"])] = match
        losses = []
        for match in matches:
            if match["semantic_won"] or match["winner"] in ("draw", "unfinished"):
                continue
            item = {
                "opponent": opponent["id"],
                "agent_seed": match["agent_seed"],
                "semantic_seat": match["semantic_seat"],
                **classify(match, pairs[int(match["agent_seed"])]),
            }
            losses.append(item)
            classified_losses.append(item)
        matchups.append(
            {
                "opponent": opponent["id"],
                "report": opponent["report"],
                "report_sha256": sha256(report_path),
                "matches": len(matches),
                "wins": sum(bool(row["semantic_won"]) for row in matches),
                "losses": len(losses),
                "faults": sum(row.get("fault") == "semantic" for row in matches),
                "unfinished": sum(bool(row["unfinished"]) for row in matches),
                "mean_runtime_s": statistics.fmean(float(row["runtime_s"]) for row in matches),
            }
        )
    counts = Counter(item["category"] for item in classified_losses)
    metric_rows = [decision_metrics(match) for match in all_matches]
    first_matches = [row for row in all_matches if int(row["semantic_seat"]) == 0]
    second_matches = [row for row in all_matches if int(row["semantic_seat"]) == 1]
    first_wins = sum(bool(row["semantic_won"]) for row in first_matches)
    second_wins = sum(bool(row["semantic_won"]) for row in second_matches)
    candidates = [
        {
            "id": "robust-world-aggregation",
            "trigger": CATEGORIES[1],
            "change": "compare median/trimmed root aggregation at fixed total search budget",
            "evidence_losses": counts[CATEGORIES[1]],
            "quantitative_basis": "classified loss count and selected-action value spread",
        },
        {
            "id": "seat-conditioned-public-state-calibration",
            "trigger": CATEGORIES[2],
            "change": "calibrate observable turn/board tempo terms without changing sampling count",
            "evidence_losses": counts[CATEGORIES[2]],
            "quantitative_basis": (
                f"first-seat {first_wins}/{len(first_matches)} vs "
                f"second-seat {second_wins}/{len(second_matches)}"
            ),
        },
    ]
    total_worlds = sum(row["generated_worlds"] for row in metric_rows)
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "provenance": {
            **manifest["provenance"],
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
        },
        "evaluation": {
            "seat_reversal": True,
            "agent_seeds": manifest["evaluation"]["agent_seeds"],
            "matches": len(all_matches),
            "wins": sum(bool(row["semantic_won"]) for row in all_matches),
            "losses": len(classified_losses),
            "faults": sum(row.get("fault") == "semantic" for row in all_matches),
            "unfinished": sum(bool(row["unfinished"]) for row in all_matches),
            "fingerprint_unique_rate": (
                sum(row["unique_fingerprints"] for row in metric_rows) / total_worlds
                if total_worlds
                else 0.0
            ),
            "selected_value_spread_mean": (
                statistics.fmean(row["selected_value_spread_mean"] for row in metric_rows)
                if metric_rows
                else 0.0
            ),
            "seat_results": {
                "first": {"wins": first_wins, "matches": len(first_matches)},
                "second": {"wins": second_wins, "matches": len(second_matches)},
                "win_rate_gap": (
                    first_wins / len(first_matches) - second_wins / len(second_matches)
                    if first_matches and second_matches
                    else 0.0
                ),
            },
        },
        "matchups": matchups,
        "classified_losses": classified_losses,
        "classification": {
            "exclusive_order": list(CATEGORIES),
            "counts": {category: counts[category] for category in CATEGORIES},
        },
        "next_candidates": candidates[:3],
        "explicit_exclusions": manifest["explicit_exclusions"],
        "champion_behavior_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["evaluation"], sort_keys=True))


if __name__ == "__main__":
    main()
