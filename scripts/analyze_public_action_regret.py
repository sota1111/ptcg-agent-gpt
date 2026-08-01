"""Reproduce SOT-2240 public-state action-regret telemetry and clusters."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(state: dict[str, Any], allowlist: list[str]) -> str:
    public = {key: state[key] for key in allowlist if key in state}
    payload = json.dumps(public, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def action_key(action: list[int]) -> str:
    return ",".join(str(value) for value in action)


def candidate_values(event: dict[str, Any]) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for world in event.get("world_roots", []):
        for row in world.get("actions", []):
            if row.get("value_mean") is not None:
                values[action_key(row["action"])].append(float(row["value_mean"]))
    return {key: statistics.fmean(rows) for key, rows in sorted(values.items())}


def classify(state: dict[str, Any]) -> tuple[str, str, str]:
    own = state.get("own") or {}
    opponent = state.get("opponent") or {}
    turn = int(state.get("turn_index", 0))
    phase = "early" if turn <= 5 else "mid" if turn <= 12 else "late"
    selected = set(state.get("selected_option_types") or [])
    action_type = "attack" if 13 in selected else "end-turn" if 14 in selected else "setup"
    if state.get("attack_ready") and state.get("selected_end_turn"):
        factor = "ready-attack-skipped"
    elif int(own.get("active_energy_count", 0)) < int(opponent.get("active_energy_count", 0)):
        factor = "active-energy-tempo"
    elif int(own.get("board_energy_count", 0)) < int(opponent.get("board_energy_count", 0)):
        factor = "board-energy-tempo"
    elif int(state.get("bench_count_delta", 0)) < 0:
        factor = "bench-tempo"
    elif int(state.get("prize_count_delta", 0)) > 0:
        factor = "prize-tempo"
    else:
        factor = "neutral-public-tempo"
    return phase, action_type, factor


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    allowlist = manifest["privacy"]["public_state_allowlist"]
    points: list[dict[str, Any]] = []
    report_hashes: dict[str, str] = {}
    for opponent in manifest["opponents"]:
        report_path = (manifest_path.parent / opponent["loss_trace_report"]).resolve()
        report_hashes[opponent["id"]] = sha256(report_path)
        report = json.loads(report_path.read_text())
        for match in report["matches"]:
            if match["semantic_won"]:
                continue
            for event in match["determinization_telemetry"]:
                state = event.get("public_state") or {}
                values = candidate_values(event)
                if not event.get("selected_action"):
                    continue
                selected = action_key(event["selected_action"])
                if selected not in values or len(values) < 2:
                    continue
                best_action, best_value = max(values.items(), key=lambda row: (row[1], row[0]))
                selected_value = values[selected]
                phase, action_type, factor = classify(state)
                points.append(
                    {
                        "opponent": opponent["id"],
                        "seed": int(match["agent_seed"]),
                        "seat": int(match["semantic_seat"]),
                        "match_outcome": "win" if match["semantic_won"] else "loss",
                        "step": int(event["step"]),
                        "public_state_fingerprint": fingerprint(state, allowlist),
                        "public_state": {key: state[key] for key in allowlist if key in state},
                        "legal_actions": [
                            {"action": key, "outcome": values[key]} for key in sorted(values)
                        ],
                        "selected_action": selected,
                        "selected_outcome": selected_value,
                        "best_counterfactual_action": best_action,
                        "best_counterfactual_outcome": best_value,
                        "action_regret": max(0.0, best_value - selected_value),
                        "cluster": {
                            "turn_phase": phase,
                            "action_type": action_type,
                            "factor": factor,
                        },
                    }
                )
    points.sort(key=lambda row: (row["opponent"], row["seed"], row["seat"], row["step"]))
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for point in points:
        cluster = point["cluster"]
        grouped[(cluster["turn_phase"], cluster["action_type"], cluster["factor"])].append(point)
    clusters = []
    for key, rows in grouped.items():
        opponents = sorted({row["opponent"] for row in rows})
        regrets = [row["action_regret"] for row in rows]
        clusters.append(
            {
                "turn_phase": key[0],
                "action_type": key[1],
                "factor": key[2],
                "scope": "common"
                if opponents == ["claude", "matsu"]
                else f"{opponents[0]}-specific",
                "opponents": opponents,
                "support": len(rows),
                "positive_regret_support": sum(value > 0 for value in regrets),
                "mean_regret": statistics.fmean(regrets),
                "max_regret": max(regrets),
            }
        )
    clusters.sort(key=lambda row: (-row["max_regret"], -row["support"], row["factor"]))
    evidence = {
        (row["turn_phase"], row["factor"]): {
            "support": row["support"],
            "mean_regret": row["mean_regret"],
            "max_regret": row["max_regret"],
            "scope": row["scope"],
        }
        for row in clusters
    }
    hypotheses = [
        {
            "id": "mid-active-energy-deficit-leaf-penalty",
            "one_change": "add one bounded leaf penalty for a public midgame active-energy deficit",
            "action_point": "leaf evaluation",
            "difference_from_prior": (
                "midgame active-slot deficit only; not SOT-2232 generic "
                "total-board/readiness weighting"
            ),
            "evidence": evidence[("mid", "active-energy-tempo")],
        },
        {
            "id": "early-bench-deficit-setup-priority",
            "one_change": (
                "raise one setup action only during a public early-game bench-count deficit"
            ),
            "action_point": "setup action ordering",
            "difference_from_prior": (
                "bench development ordering, separate from prior board/active-energy calibration"
            ),
            "evidence": evidence[("early", "bench-tempo")],
        },
        {
            "id": "matsu-mid-neutral-root-tiebreak",
            "one_change": (
                "apply one public-state root tiebreak in the isolated midgame neutral-tempo cluster"
            ),
            "action_point": "root action selection",
            "difference_from_prior": (
                "opponent identity is not an input; the cluster is selected by public "
                "phase/tempo and was not tested by SOT-2232"
            ),
            "evidence": evidence[("mid", "neutral-public-tempo")],
        },
    ]
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "provenance": {
            "manifest_sha256": sha256(manifest_path),
            "report_sha256": report_hashes,
            "champion": manifest["champion"],
            "fixed_conditions": manifest["fixed_conditions"],
        },
        "decision_points": points,
        "clusters": clusters,
        "hypotheses": hypotheses,
        "privacy_audit": {
            "public_state_only": True,
            "hidden_information_leakage": False,
            "opponent_identity_branching": False,
        },
        "champion_behavior_changed": False,
        "promotion_performed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
