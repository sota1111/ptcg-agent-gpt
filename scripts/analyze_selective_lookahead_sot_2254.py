"""Measure bounded setup-sequence value using public telemetry only."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action_values(event: dict[str, Any]) -> dict[tuple[int, ...], float]:
    rows: dict[tuple[int, ...], list[float]] = {}
    for root in event.get("world_roots", []):
        for action in root.get("actions", []):
            if action.get("value_mean") is not None:
                rows.setdefault(tuple(action["action"]), []).append(float(action["value_mean"]))
    return {key: statistics.fmean(values) for key, values in rows.items()}


def selected_value(event: dict[str, Any]) -> float | None:
    selected = event.get("selected_action")
    if selected is None:
        return None
    return action_values(event).get(tuple(selected))


def is_setup(event: dict[str, Any]) -> bool:
    types = set((event.get("public_state") or {}).get("selected_option_types") or [])
    return bool(types) and not bool(types & {13, 14})


def analyze(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    allowlist = set(manifest["privacy"]["public_state_allowlist"])
    cfg = manifest["fixed_conditions"]["lookahead"]
    sequences: list[dict[str, Any]] = []
    report_hashes: dict[str, str] = {}
    audit = {"matches": 0, "losses": 0, "faults": 0, "unfinished": 0, "max_runtime_s": 0.0}
    for opponent in manifest["opponents"]:
        path = (manifest_path.parent / opponent["report"]).resolve()
        report_hashes[opponent["id"]] = digest(path)
        report = json.loads(path.read_text())
        audit["matches"] += len(report["matches"])
        audit["faults"] += int(report["faults_semantic"])
        audit["unfinished"] += int(report["unfinished"])
        for match in report["matches"]:
            audit["max_runtime_s"] = max(audit["max_runtime_s"], float(match["runtime_s"]))
            if match["semantic_won"]:
                continue
            audit["losses"] += 1
            events = match["determinization_telemetry"]
            for first, second in zip(events, events[1:], strict=False):
                a, b = selected_value(first), selected_value(second)
                sa, sb = first.get("public_state") or {}, second.get("public_state") or {}
                if a is None or b is None or not (is_setup(first) and is_setup(second)):
                    continue
                if cfg["same_turn_only"] and sa.get("turn_index") != sb.get("turn_index"):
                    continue
                if int(second["step"]) - int(first["step"]) > int(cfg["max_step_gap"]):
                    continue
                public = {key: sa[key] for key in sorted(allowlist) if key in sa}
                sequence_score = statistics.fmean([a, b])
                sequences.append(
                    {
                        "seed": int(match["agent_seed"]),
                        "seat": int(match["semantic_seat"]),
                        "step": int(first["step"]),
                        "turn_index": int(sa.get("turn_index", 0)),
                        "public_state": public,
                        "one_ply_score": a,
                        "next_setup_score": b,
                        "two_decision_score": sequence_score,
                        "horizon_effect": sequence_score - a,
                        "supported": sequence_score > a,
                    }
                )
    sequences.sort(key=lambda row: (row["seed"], row["seat"], row["step"]))
    effects = [row["horizon_effect"] for row in sequences]
    support = sum(row["supported"] for row in sequences)
    candidate = None
    if support >= 3 and effects and statistics.fmean(effects) > 0:
        candidate = {
            "id": "bounded-public-setup-continuation",
            "one_change": (
                "at setup-only public decision points, use a two-decision "
                "continuation tie-break under the existing root budget"
            ),
            "evidence": {
                "support": support,
                "total": len(effects),
                "mean_effect": statistics.fmean(effects),
            },
            "screen_confirm_gate": manifest["promotion_gate"],
        }
    return {
        "schema_version": 1,
        "issue": manifest["issue"],
        "provenance": {
            "manifest_sha256": digest(manifest_path),
            "report_sha256": report_hashes,
            "champion": manifest["provenance"],
        },
        "method": {
            "comparison": (
                "selected one-ply root mean versus mean of the observed bounded "
                "two-setup-decision continuation"
            ),
            "diagnostic_only": True,
            "lookahead": cfg,
        },
        "sequences": sequences,
        "horizon_shortfall": {
            "support": support,
            "total": len(effects),
            "support_rate": support / len(effects) if effects else 0.0,
            "mean_effect": statistics.fmean(effects) if effects else 0.0,
            "median_effect": statistics.median(effects) if effects else 0.0,
            "max_effect": max(effects) if effects else 0.0,
        },
        "runtime": audit,
        "privacy_audit": {
            "public_state_only": True,
            "hidden_information_leakage": False,
            "opponent_identity_branching": False,
            "allowlist": sorted(allowlist),
        },
        "candidates": [candidate] if candidate else [],
        "excluded_prior_families": manifest["excluded_prior_families"],
        "champion_behavior_changed": False,
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
