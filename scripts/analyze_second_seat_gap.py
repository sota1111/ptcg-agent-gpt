"""Classify SOT-2174 second-seat losses from public decision telemetry."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

CATEGORIES = (
    "setup/energy tempo",
    "attack timing",
    "resource conservation",
    "seat-independent",
    "unclassifiable",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    selected_ranks = [
        int(event["selected_action_index"])
        for event in events
        if event.get("selected_action_index") is not None
    ]
    selected_values: list[float] = []
    prior_values: list[float] = []
    for event in events:
        selected = event.get("selected_action_index")
        for root in event.get("world_roots", []):
            actions = root.get("actions", [])
            if actions and actions[0].get("value_mean") is not None:
                prior_values.append(float(actions[0]["value_mean"]))
            if selected is not None and int(selected) < len(actions):
                value = actions[int(selected)].get("value_mean")
                if value is not None:
                    selected_values.append(float(value))
    return {
        "selected_action_rank_mean": (statistics.fmean(selected_ranks) if selected_ranks else 0.0),
        "non_prior_selections": sum(rank > 0 for rank in selected_ranks),
        "selected_leaf_value_mean": (
            statistics.fmean(selected_values) if selected_values else None
        ),
        "prior_leaf_value_mean": statistics.fmean(prior_values) if prior_values else None,
    }


def _tempo_metrics(match: dict[str, Any]) -> dict[str, Any]:
    states = [
        event["public_state"]
        for event in match["determinization_telemetry"]
        if event.get("public_state")
    ]
    action_states = [state for state in states if state["selection_context"] == 0]
    attacks = [state for state in action_states if state["selected_attack"]]
    ready_passes = [
        state for state in action_states if state["attack_ready"] and state["selected_end_turn"]
    ]
    early = [state for state in action_states if int(state["turn_index"]) <= 5]
    return {
        "public_decisions": len(states),
        "action_menu_decisions": len(action_states),
        "first_attack_turn": min(
            (int(state["turn_index"]) for state in attacks),
            default=None,
        ),
        "attacks": len(attacks),
        "attack_ready_end_turns": len(ready_passes),
        "early_energy_delta_mean": (
            statistics.fmean(
                state["own"]["board_energy_count"] - state["opponent"]["board_energy_count"]
                for state in early
            )
            if early
            else 0.0
        ),
        "early_active_energy_delta_mean": (
            statistics.fmean(
                state["own"]["active_energy_count"] - state["opponent"]["active_energy_count"]
                for state in early
            )
            if early
            else 0.0
        ),
        "early_bench_delta_mean": (
            statistics.fmean(state["bench_count_delta"] for state in early) if early else 0.0
        ),
        "final_hand_delta": states[-1]["hand_count_delta"] if states else 0,
        **_root_metrics(match["determinization_telemetry"]),
    }


def classify(
    match: dict[str, Any], pair: dict[int, dict[str, Any]]
) -> tuple[str, str, dict[str, Any]]:
    metrics = _tempo_metrics(match)
    reversed_match = pair.get(0)
    reversed_metrics = _tempo_metrics(reversed_match) if reversed_match else None
    if metrics["early_energy_delta_mean"] < 0 or metrics["early_bench_delta_mean"] < 0:
        category = "setup/energy tempo"
        evidence = (
            f"early_energy_delta_mean={metrics['early_energy_delta_mean']:.3f}; "
            f"early_bench_delta_mean={metrics['early_bench_delta_mean']:.3f}"
        )
    elif metrics["attack_ready_end_turns"] > 0 or (
        reversed_metrics
        and metrics["first_attack_turn"] is not None
        and reversed_metrics["first_attack_turn"] is not None
        and metrics["first_attack_turn"] >= reversed_metrics["first_attack_turn"] + 2
    ):
        category = "attack timing"
        evidence = (
            f"ready_end_turns={metrics['attack_ready_end_turns']}; "
            f"first_attack_turn={metrics['first_attack_turn']} vs "
            f"paired_first={reversed_metrics['first_attack_turn'] if reversed_metrics else None}"
        )
    elif metrics["final_hand_delta"] >= 3 or metrics["non_prior_selections"] >= 3:
        category = "resource conservation"
        evidence = (
            f"final_hand_delta={metrics['final_hand_delta']}; "
            f"non_prior_selections={metrics['non_prior_selections']}"
        )
    elif reversed_match and not reversed_match["semantic_won"]:
        category = "seat-independent"
        evidence = "same seed also lost from first seat"
    else:
        category = "unclassifiable"
        evidence = "no preregistered public-state threshold met"
    return category, evidence, metrics


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    matches: list[dict[str, Any]] = []
    matchups = []
    for opponent in manifest["opponents"]:
        path = (manifest_path.parent / opponent["report"]).resolve()
        report = json.loads(path.read_text())
        opponent_matches = report["matches"]
        matches.extend({**match, "_opponent": opponent["id"]} for match in opponent_matches)
        matchups.append(
            {
                "opponent": opponent["id"],
                "report": opponent["report"],
                "report_sha256": sha256(path),
                "matches": len(opponent_matches),
                "wins": sum(bool(row["semantic_won"]) for row in opponent_matches),
                "faults": sum(row.get("fault") == "semantic" for row in opponent_matches),
                "unfinished": sum(bool(row["unfinished"]) for row in opponent_matches),
                "mean_runtime_s": statistics.fmean(
                    float(row["runtime_s"]) for row in opponent_matches
                ),
            }
        )

    pairs: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    for match in matches:
        pairs.setdefault((match["_opponent"], int(match["agent_seed"])), {})[
            int(match["semantic_seat"])
        ] = match
    classified = []
    for match in matches:
        if int(match["semantic_seat"]) != 1 or match["semantic_won"]:
            continue
        category, evidence, metrics = classify(
            match, pairs[(match["_opponent"], int(match["agent_seed"]))]
        )
        classified.append(
            {
                "opponent": match["_opponent"],
                "agent_seed": match["agent_seed"],
                "category": category,
                "evidence": evidence,
                "metrics": metrics,
            }
        )

    counts = Counter(row["category"] for row in classified)
    first = [row for row in matches if int(row["semantic_seat"]) == 0]
    second = [row for row in matches if int(row["semantic_seat"]) == 1]
    candidates = [
        {
            "id": "public-board-energy-tempo-evaluation",
            "trigger": "setup/energy tempo",
            "evidence_losses": counts["setup/energy tempo"],
            "quantitative_basis": (
                "second-seat losses with negative early public board-energy delta"
            ),
            "one_change": "add only public early board-energy delta to leaf evaluation",
        },
        {
            "id": "public-attack-readiness-pressure-evaluation",
            "trigger": "setup/energy tempo",
            "evidence_losses": counts["setup/energy tempo"],
            "quantitative_basis": (
                "second-seat losses with negative early public active-energy delta"
            ),
            "one_change": (
                "add only opponent public active-energy/attack-readiness pressure "
                "to leaf evaluation"
            ),
        },
        {
            "id": "attack-readiness-tempo-evaluation",
            "trigger": "attack timing",
            "evidence_losses": counts["attack timing"],
            "quantitative_basis": "attack-ready end-turn or paired first-attack delay count",
            "one_change": (
                "add only public attack-ready and first-attack timing terms to leaf evaluation"
            ),
        },
        {
            "id": "public-resource-conversion-evaluation",
            "trigger": "resource conservation",
            "evidence_losses": counts["resource conservation"],
            "quantitative_basis": "retained-hand or non-prior-selection loss count",
            "one_change": "penalize retained public action economy only when board tempo trails",
        },
        {
            "id": "public-threat-pressure-evaluation",
            "trigger": "seat-independent",
            "evidence_losses": counts["seat-independent"],
            "quantitative_basis": "same-seed losses from both seats",
            "one_change": ("add only public opponent attack-readiness pressure to leaf evaluation"),
        },
    ]
    candidates = [row for row in candidates if int(row["evidence_losses"]) > 0]
    candidates.sort(key=lambda row: (-int(row["evidence_losses"]), row["id"]))
    public_fields = sorted(
        {
            key
            for match in matches
            for event in match["determinization_telemetry"]
            for key in (event.get("public_state") or {})
        }
    )
    required = {
        "turn_index",
        "turn_action_count",
        "hand_count_delta",
        "bench_count_delta",
        "prize_count_delta",
        "energy_attachment_available",
        "attack_ready",
        "selected_end_turn",
        "selected_attack",
    }
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
            "matches": len(matches),
            "wins": sum(bool(row["semantic_won"]) for row in matches),
            "faults": sum(row.get("fault") == "semantic" for row in matches),
            "unfinished": sum(bool(row["unfinished"]) for row in matches),
            "seat_results": {
                "first": {
                    "wins": sum(bool(row["semantic_won"]) for row in first),
                    "matches": len(first),
                },
                "second": {
                    "wins": sum(bool(row["semantic_won"]) for row in second),
                    "matches": len(second),
                },
            },
        },
        "matchups": matchups,
        "classified_second_seat_losses": classified,
        "classification": {
            "exclusive_order": list(CATEGORIES),
            "counts": {category: counts[category] for category in CATEGORIES},
        },
        "next_candidates": candidates[:3],
        "telemetry_contract": {
            "public_fields": public_fields,
            "required_fields_complete": required.issubset(public_fields),
            "forbidden_hidden_fields": [
                "opponent.hand",
                "opponent.prize identities",
                "search_begin_input",
                "world fingerprint values",
            ],
            "hidden_information_leakage": False,
        },
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
