#!/usr/bin/env python3
"""Deterministically select the CV-best finalist and an independent hedge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.audit_finalist_inventory_sot_2592 import audit as audit_inventory
except ModuleNotFoundError:  # Direct script execution puts scripts/ on sys.path.
    from audit_finalist_inventory_sot_2592 import audit as audit_inventory


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _risk_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    result = summary.get("result", {})
    opponents = result.get("opponents", {})
    seats = result.get("seats", {})
    runtime = result.get("runtimeSeconds", {})
    if not opponents or not seats:
        raise ValueError("risk audit requires matchup and seat results")
    worst_matchup_name, worst_matchup = min(
        opponents.items(), key=lambda item: (item[1].get("winRate", -1), item[0])
    )
    worst_seat_name, worst_seat = min(
        seats.items(), key=lambda item: (item[1].get("winRate", -1), item[0])
    )
    required_runtime = {"mean", "p95", "max"}
    if set(runtime) != required_runtime:
        raise ValueError("risk audit requires mean/p95/max runtime")
    return {
        "worstMatchup": {
            "id": worst_matchup_name,
            "matches": worst_matchup["matches"],
            "wins": worst_matchup["wins"],
            "winRate": worst_matchup["winRate"],
        },
        "worstSeat": {
            "seat": worst_seat_name,
            "matches": worst_seat["matches"],
            "wins": worst_seat["wins"],
            "winRate": worst_seat["winRate"],
        },
        "reliability": {
            "faults": result.get("faults"),
            "illegalActions": result.get("illegalActions"),
            "unfinished": result.get("unfinished"),
        },
        "runtimeSeconds": runtime,
    }


def select(inventory_path: Path, repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    if not inventory_path.is_absolute():
        inventory_path = repo_root / inventory_path
    inventory_path = inventory_path.resolve()
    audit_inventory(inventory_path, repo_root)
    inventory = _load(inventory_path)
    contract = inventory["selectionContract"]
    if contract.get("primaryMetric") != "leak_free_blind_cv_wilson95_lower":
        raise ValueError("primary must be selected by leak-free CV Wilson lower bound")
    if contract.get("kaggleSubmissionAllowed") is not False:
        raise ValueError("child selection must prohibit Kaggle submission")

    candidates = [
        record
        for record in inventory["auditedTerminalArtifacts"]
        if record.get("status") == "finalist"
    ]
    if len(candidates) < 2:
        raise ValueError("selection requires at least two comparable finalists")
    candidates.sort(key=lambda row: (-row["cv"]["wilson95"][0], row["issue"]))
    primary = candidates[0]
    hedge_pool = [
        row
        for row in candidates[1:]
        if row["strategyLineage"] != primary["strategyLineage"]
        and row["fingerprint"]["contentSha256"] != primary["fingerprint"]["contentSha256"]
    ]
    if not hedge_pool:
        raise ValueError("no fingerprint- and strategy-lineage-independent hedge")
    hedge = hedge_pool[0]

    def selected(role: str, record: dict[str, Any]) -> dict[str, Any]:
        summary_path = repo_root / record["paths"]["summary"]
        summary = _load(summary_path)
        return {
            "role": role,
            "issue": record["issue"],
            "strategyLineage": record["strategyLineage"],
            "fingerprint": record["fingerprint"],
            "cv": record["cv"],
            "public": record["public"],
            "risk": _risk_metrics(summary),
            "sourceSummary": {
                "path": record["paths"]["summary"],
                "sha256": _sha256(summary_path),
            },
        }

    return {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2593",
        "mode": "converge",
        "sourceInventory": {
            "path": str(inventory_path.relative_to(repo_root)),
            "sha256": _sha256(inventory_path),
            "issue": inventory["issue"],
        },
        "directiveSnapshot": {
            "parentIssue": "SOT-2591",
            "checkedAt": "2026-08-10T04:34:00Z",
            "effectiveCycle": "converge",
            "effectiveSubmit": "auto",
            "newerHumanDirective": False,
        },
        "selectionContract": {
            "primaryMetric": "leak_free_blind_cv_wilson95_lower",
            "hedgeRequirement": "distinct_content_fingerprint_and_strategy_lineage",
            "unequalPopulationPolicy": "compare_wilson95_lower_not_raw_win_rate",
            "missingOrIncomparablePolicy": "fail_closed",
            "publicResultPolicy": "sanity_only_null_never_imputed",
            "activeSubmissionSlots": 2,
            "kaggleSubmissionAllowed": False,
            "retrainingAllowed": False,
            "rejectedAxisRetryAllowed": False,
        },
        "selected": [selected("primary", primary), selected("hedge", hedge)],
        "lineageIndependent": True,
        "contentFingerprintsDistinct": True,
        "relativeRatingRisk": (
            "A fixed-field holdout can overstate live relative-rating performance "
            "as the field evolves."
        ),
        "publicCvGap": (
            "Public ratings are unavailable for both exact fingerprints; the gap is unknown and is "
            "not imputed. Leak-free CV therefore controls pessimistically."
        ),
        "heavyTailPolicy": (
            "Retain worst-matchup, worst-seat, p95/max runtime, faults, illegal actions, and "
            "unfinished counts; aggregate win rate cannot hide these tails."
        ),
        "decision": {
            "primary": primary["issue"],
            "hedge": hedge["issue"],
            "reason": (
                "Primary has the highest leak-free Wilson 95% lower bound. Hedge is the remaining "
                "validated finalist with a distinct content fingerprint and strategy lineage."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "inventory",
        type=Path,
        default=Path("artifacts/sot-2592/finalist-inventory.json"),
        nargs="?",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = select(args.inventory, args.repo_root)
    encoded = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
