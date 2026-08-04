"""Evaluate SOT-2440 under the frozen SOT-2439 screen/confirm contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.evaluate_reanchoring import compare, summarize_reports
    from scripts.validate_tactical_contract import validate_manifest
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from evaluate_reanchoring import compare, summarize_reports
    from validate_tactical_contract import validate_manifest


def evaluation_manifest(contract_path: Path) -> dict:
    contract = validate_manifest(contract_path)
    source_path = contract_path.parent / "sot-2399-lb-reanchoring.json"
    source = json.loads(source_path.read_text())
    return {
        "issue": "SOT-2440",
        "axis": contract["axis"],
        "champion": contract["champion"],
        "opponents": source["opponents"],
        "phases": contract["phases"],
        "promotionGate": contract["promotionGate"],
        "kaggleSubmissionAllowed": False,
    }


def evaluate(
    contract_path: Path,
    phase: str,
    champion_paths: list[Path],
    candidate_paths: list[Path],
    screen_decision_path: Path | None = None,
) -> dict:
    manifest = evaluation_manifest(contract_path)
    if phase == "confirm":
        if screen_decision_path is None:
            raise ValueError("confirm requires --screen-decision")
        screen = json.loads(screen_decision_path.read_text())
        if screen.get("phase") != "screen" or not screen.get("gate", {}).get("passed"):
            raise ValueError("confirm is forbidden until screen passes")
    champion = summarize_reports(manifest, phase, champion_paths)
    candidate = summarize_reports(manifest, phase, candidate_paths)
    gate = compare(manifest, champion, candidate)
    return {
        "schemaVersion": "1.0.0",
        "issue": "SOT-2440",
        "axis": manifest["axis"],
        "phase": phase,
        "champion": champion,
        "candidate": candidate,
        "gate": gate,
        "nextPhase": "confirm" if phase == "screen" and gate["passed"] else None,
        "decision": (
            "eligible-for-promotion" if phase == "confirm" and gate["passed"] else "retain-champion"
        ),
        "candidateBehaviorRevertedOnFailure": not gate["passed"],
        "kaggleSubmitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--phase", choices=("screen", "confirm"), required=True)
    parser.add_argument("--champion", nargs="+", type=Path, required=True)
    parser.add_argument("--candidate", nargs="+", type=Path, required=True)
    parser.add_argument("--screen-decision", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        args.contract,
        args.phase,
        args.champion,
        args.candidate,
        args.screen_decision,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["gate"], sort_keys=True))


if __name__ == "__main__":
    main()
