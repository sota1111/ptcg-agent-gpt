"""Aggregate frozen real-engine traces and classify champion losses.

The classifier intentionally uses only observable trace evidence. Categories
are mutually exclusive and ordered from direct evidence to weaker proxies;
the emitted artifact records the rule and confidence for every loss.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

CATEGORIES = (
    "fallback_or_fault",
    "deck_out",
    "time_governor",
    "candidate_prior_or_pruning",
    "determinization_or_seat_bias",
    "rollout_value_error",
    "unclassified",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def classify_loss(match: dict[str, Any], pair: dict[int, dict[str, Any]]) -> dict[str, Any]:
    telemetry = match["semantic_telemetry"]
    final = match["final"]["semantic"]
    opponent = next(value for key, value in match["final"].items() if key != "semantic")
    if match.get("fault") == "semantic":
        return {"category": "fallback_or_fault", "confidence": "high", "evidence": ["fault"]}
    if final["deck_count"] == 0 or telemetry["min_deck_count"] == 0:
        return {"category": "deck_out", "confidence": "high", "evidence": ["deck_count=0"]}
    if match["think_s"]["semantic"] >= 300:
        return {
            "category": "time_governor",
            "confidence": "high",
            "evidence": [f"think_s={match['think_s']['semantic']:.6f}"],
        }
    if telemetry["branching_decisions"] >= 3 and telemetry["max_options"] > 6:
        return {
            "category": "candidate_prior_or_pruning",
            "confidence": "medium",
            "evidence": [
                f"branching_decisions={telemetry['branching_decisions']}",
                f"max_options={telemetry['max_options']}",
            ],
        }
    paired = pair.get(1 - int(match["semantic_seat"]))
    if paired and paired.get("semantic_won"):
        return {
            "category": "determinization_or_seat_bias",
            "confidence": "medium",
            "evidence": ["same agent seed won from reversed seat"],
        }
    if final["prize_count"] <= opponent["prize_count"]:
        return {
            "category": "rollout_value_error",
            "confidence": "low",
            "evidence": [
                f"final_prizes={final['prize_count']}:{opponent['prize_count']}",
                "loss despite non-worse final prize count",
            ],
        }
    return {
        "category": "unclassified",
        "confidence": "low",
        "evidence": ["no category threshold met"],
    }


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    reports = []
    for opponent in manifest["opponents"]:
        report_path = (manifest_path.parent / opponent["report"]).resolve()
        report = json.loads(report_path.read_text())
        reports.append((opponent, report_path, report))

    all_matches: list[dict[str, Any]] = []
    classified_losses = []
    matchup = []
    for opponent, report_path, report in reports:
        matches = report["matches"]
        all_matches.extend(matches)
        pairs: dict[int, dict[int, dict[str, Any]]] = {}
        for match in matches:
            pairs.setdefault(int(match["agent_seed"]), {})[int(match["semantic_seat"])] = match
        losses = []
        for match in matches:
            if match["semantic_won"] or match["winner"] in ("draw", "unfinished"):
                continue
            classification = classify_loss(match, pairs[int(match["agent_seed"])])
            item = {
                "opponent": opponent["id"],
                "agent_seed": match["agent_seed"],
                "semantic_seat": match["semantic_seat"],
                "state": {
                    "steps": match["steps"],
                    "runtime_s": match["runtime_s"],
                    "think_s": match["think_s"]["semantic"],
                    "final": match["final"],
                },
                "selection_layer": {
                    **match["semantic_telemetry"],
                    "contexts": match["semantic_contexts"],
                },
                **classification,
            }
            losses.append(item)
            classified_losses.append(item)
        matchup.append(
            {
                "opponent": opponent["id"],
                "report": str(Path(opponent["report"])),
                "report_sha256": sha256(report_path),
                "matches": len(matches),
                "wins": sum(bool(row["semantic_won"]) for row in matches),
                "losses": len(losses),
                "draws": sum(row["winner"] == "draw" for row in matches),
                "unfinished": sum(bool(row["unfinished"]) for row in matches),
                "faults": sum(row.get("fault") == "semantic" for row in matches),
            }
        )

    counts = Counter(item["category"] for item in classified_losses)
    loss_total = len(classified_losses)
    breakdown = [
        {
            "category": category,
            "losses": counts[category],
            "loss_share": counts[category] / loss_total if loss_total else 0.0,
            "estimated_win_contribution": (
                counts[category] / len(all_matches) if all_matches else 0.0
            ),
        }
        for category in CATEGORIES
    ]
    ranked = sorted(breakdown, key=lambda row: (-row["losses"], row["category"]))
    runtime = [float(row["runtime_s"]) for row in all_matches]
    candidates = [
        {
            "rank": 1,
            "id": "root-candidate-prior",
            "category": "candidate_prior_or_pruning",
            "next_issue_scope": "compare root prior and max_root_actions independently",
            "evidence_losses": counts["candidate_prior_or_pruning"],
        },
        {
            "rank": 2,
            "id": "rollout-leaf-calibration",
            "category": "rollout_value_error",
            "next_issue_scope": (
                "compare observable leaf-value terms without changing search budget"
            ),
            "evidence_losses": counts["rollout_value_error"],
        },
        {
            "rank": 3,
            "id": "determinization-diversity",
            "category": "determinization_or_seat_bias",
            "next_issue_scope": "compare world sampling diversity at the frozen total budget",
            "evidence_losses": counts["determinization_or_seat_bias"],
        },
    ]
    candidates = [row for row in candidates if row["evidence_losses"] > 0][:4]
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "provenance": {
            **manifest["provenance"],
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
        },
        "evaluation": {
            "seat_reversal": manifest["evaluation"]["seat_reversal"],
            "agent_seeds": manifest["evaluation"]["agent_seeds"],
            "matches": len(all_matches),
            "wins": sum(bool(row["semantic_won"]) for row in all_matches),
            "losses": loss_total,
            "draws": sum(row["winner"] == "draw" for row in all_matches),
            "faults": sum(row.get("fault") == "semantic" for row in all_matches),
            "unfinished": sum(bool(row["unfinished"]) for row in all_matches),
            "runtime_s": {
                "mean": statistics.fmean(runtime) if runtime else 0.0,
                "p50": percentile(runtime, 0.50),
                "p95": percentile(runtime, 0.95),
                "max": max(runtime, default=0.0),
            },
            "unclassified_rate": (counts["unclassified"] / loss_total if loss_total else 0.0),
        },
        "matchups": matchup,
        "losses": classified_losses,
        "classification": {
            "rules": [
                "fault > deck-out > cumulative think >=300s > >=3 root decisions with >6 options",
                "reversed-seat pair win > non-worse final prize count > unclassified",
            ],
            "breakdown": ranked,
            "largest_bottleneck": ranked[0]["category"] if loss_total else None,
        },
        "next_candidates": candidates,
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
