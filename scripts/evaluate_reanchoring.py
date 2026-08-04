"""Validate and aggregate the preregistered SOT-2399 screen/confirm protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rate(wins: int | float, matches: int | float) -> float:
    return wins / matches if matches else 0.0


def summarize_reports(manifest: dict[str, Any], phase: str, paths: list[Path]) -> dict[str, Any]:
    """Validate provenance and emit opponent/seat/worst/fault/runtime metrics."""
    expected = manifest["phases"][phase]
    reports = [json.loads(path.read_text()) for path in paths]
    by_id = {report["opponent"]: report for report in reports}
    opponent_ids = [row["id"] for row in manifest["opponents"]]
    if sorted(by_id) != sorted(opponent_ids):
        raise ValueError(f"{phase} reports must cover exactly {opponent_ids}")

    runtimes: list[float] = []
    seats: dict[str, dict[str, int | float]] = {
        "0": {"wins": 0, "matches": 0},
        "1": {"wins": 0, "matches": 0},
    }
    opponents: dict[str, Any] = {}
    faults = unfinished = matches = wins = 0
    for opponent in manifest["opponents"]:
        report = by_id[opponent["id"]]
        if report["base_seed"] != expected["baseSeed"]:
            raise ValueError(f"{opponent['id']} has unexpected {phase} seed")
        if report["seeds"] != expected["seedsPerOpponent"]:
            raise ValueError(f"{opponent['id']} has unexpected seed count")
        report_matches = report["matches"]
        if {row["semantic_seat"] for row in report_matches} != {0, 1}:
            raise ValueError(f"{opponent['id']} is missing seat reversal")
        opponent_wins = sum(bool(row["semantic_won"]) for row in report_matches)
        opponent_n = len(report_matches)
        opponent_faults = report.get("faults_semantic", 0)
        opponent_unfinished = report.get("unfinished", 0)
        opponent_runtimes = [float(row["runtime_s"]) for row in report_matches]
        opponents[opponent["id"]] = {
            "pool": opponent["pool"],
            "wins": opponent_wins,
            "matches": opponent_n,
            "winRate": _rate(opponent_wins, opponent_n),
            "faults": opponent_faults,
            "unfinished": opponent_unfinished,
            "runtimeSeconds": {
                "mean": statistics.fmean(opponent_runtimes),
                "max": max(opponent_runtimes),
            },
        }
        for row in report_matches:
            seat = str(row["semantic_seat"])
            seats[seat]["matches"] += 1
            seats[seat]["wins"] += int(bool(row["semantic_won"]))
        wins += opponent_wins
        matches += opponent_n
        faults += opponent_faults
        unfinished += opponent_unfinished
        runtimes.extend(opponent_runtimes)

    for row in seats.values():
        row["winRate"] = _rate(row["wins"], row["matches"])
    worst_id = min(opponents, key=lambda item: (opponents[item]["winRate"], item))
    return {
        "phase": phase,
        "baseSeed": expected["baseSeed"],
        "opponents": opponents,
        "seats": seats,
        "worstMatchup": {"opponent": worst_id, **opponents[worst_id]},
        "pool": {
            "wins": wins,
            "matches": matches,
            "winRate": _rate(wins, matches),
            "faults": faults,
            "unfinished": unfinished,
            "runtimeSeconds": {
                "mean": statistics.fmean(runtimes),
                "p95": sorted(runtimes)[max(0, int(len(runtimes) * 0.95) - 1)],
                "max": max(runtimes),
            },
        },
    }


def compare(
    manifest: dict[str, Any], champion: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    gate = manifest["promotionGate"]
    reasons: list[str] = []
    if candidate["pool"]["winRate"] <= champion["pool"]["winRate"]:
        reasons.append("pool win rate did not strictly improve")
    for opponent in champion["opponents"]:
        if candidate["opponents"][opponent]["winRate"] < champion["opponents"][opponent]["winRate"]:
            reasons.append(f"opponent regression: {opponent}")
    for seat in ("0", "1"):
        if candidate["seats"][seat]["winRate"] < champion["seats"][seat]["winRate"]:
            reasons.append(f"seat regression: {seat}")
    if candidate["pool"]["faults"] > champion["pool"]["faults"]:
        reasons.append("fault regression")
    if candidate["pool"]["unfinished"] > champion["pool"]["unfinished"]:
        reasons.append("unfinished regression")
    champion_runtime = champion["pool"]["runtimeSeconds"]["mean"]
    if candidate["pool"]["runtimeSeconds"]["mean"] > champion_runtime * gate["meanRuntimeRatioMax"]:
        reasons.append("mean runtime ratio exceeded")
    if candidate["pool"]["runtimeSeconds"]["max"] >= gate["matchRuntimeSecondsMaxExclusive"]:
        reasons.append("match runtime limit exceeded")
    return {"passed": not reasons, "reasons": reasons}


def evaluate(
    manifest_path: Path,
    phase: str,
    champion_paths: list[Path],
    candidate_paths: list[Path],
    screen_decision_path: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    if manifest["champion"]["mainSha256"] != _sha256(Path(manifest["champion"]["main"])):
        raise ValueError("champion main fingerprint drifted")
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
        "issue": manifest["issue"],
        "phase": phase,
        "champion": champion,
        "candidate": candidate,
        "gate": gate,
        "nextPhase": "confirm" if phase == "screen" and gate["passed"] else None,
        "decision": (
            "eligible-for-promotion" if phase == "confirm" and gate["passed"] else "retain-champion"
        ),
        "candidateBehaviorRevertedOnFailure": not gate["passed"],
        "execCompatibilityRequiredOnPromotion": True,
        "kaggleSubmitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--phase", choices=("screen", "confirm"), required=True)
    parser.add_argument("--champion", nargs="+", type=Path, required=True)
    parser.add_argument("--candidate", nargs="+", type=Path, required=True)
    parser.add_argument("--screen-decision", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        args.manifest, args.phase, args.champion, args.candidate, args.screen_decision
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["gate"], sort_keys=True))


if __name__ == "__main__":
    main()
