"""Run the preregistered SOT-2346 public-value screen -> confirm gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.battle_vs import run  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_provenance(manifest: dict[str, Any]) -> None:
    if sha256(ROOT / manifest["source"]["corpus"]) != manifest["source"]["corpusSha256"]:
        raise ValueError("oracle corpus fingerprint drift")
    if sha256(ROOT / manifest["champion"]["deck"]) != manifest["champion"]["deckSha256"]:
        raise ValueError("champion deck fingerprint drift")
    artifact = manifest["candidate"]
    if sha256(ROOT / artifact["artifact"]) != artifact["artifactSha256"]:
        raise ValueError("candidate artifact fingerprint drift")
    for opponent in manifest["opponents"]:
        repo = Path(opponent["repo"])
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()
        if commit != opponent["commit"] or sha256(repo / "deck.csv") != opponent["deckSha256"]:
            raise ValueError(f"opponent {opponent['label']} provenance drift")


def summarize(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    matches = [match for report in reports.values() for match in report["matches"]]
    seats = {
        str(seat): [match for match in matches if int(match["semantic_seat"]) == seat]
        for seat in (0, 1)
    }
    return {
        "matches": len(matches),
        "wins": sum(bool(match["semantic_won"]) for match in matches),
        "winRate": sum(bool(match["semantic_won"]) for match in matches) / len(matches),
        "seatWinRate": {
            seat: sum(bool(match["semantic_won"]) for match in rows) / len(rows)
            for seat, rows in seats.items()
        },
        "matchups": {
            label: {
                "matches": int(report["n_matches"]),
                "wins": int(report["wins_semantic"]),
                "winRate": int(report["wins_semantic"]) / int(report["n_matches"]),
            }
            for label, report in sorted(reports.items())
        },
        "faults": sum(int(report["faults_semantic"]) for report in reports.values()),
        "unfinished": sum(int(report["unfinished"]) for report in reports.values()),
        "runtimeSeconds": {
            "mean": sum(float(match["runtime_s"]) for match in matches) / len(matches),
            "max": max(float(match["runtime_s"]) for match in matches),
        },
    }


def gate(champion: dict[str, Any], candidate: dict[str, Any], manifest: dict[str, Any]) -> dict:
    reasons = []
    if candidate["winRate"] <= champion["winRate"]:
        reasons.append("aggregate win rate did not strictly improve")
    for label in champion["matchups"]:
        if candidate["matchups"][label]["winRate"] < champion["matchups"][label]["winRate"]:
            reasons.append(f"{label} matchup regressed")
    for seat in champion["seatWinRate"]:
        if candidate["seatWinRate"][seat] < champion["seatWinRate"][seat]:
            reasons.append(f"seat {seat} regressed")
    if candidate["faults"] > champion["faults"]:
        reasons.append("faults increased")
    if candidate["unfinished"] > champion["unfinished"]:
        reasons.append("unfinished matches increased")
    if candidate["runtimeSeconds"]["max"] >= float(manifest["gate"]["matchRuntimeSecondsMax"]):
        reasons.append("600 second match runtime limit reached")
    return {"passed": not reasons, "reasons": reasons}


def run_phase(
    manifest: dict[str, Any], phase: str, output: Path
) -> tuple[dict[str, Any], dict[str, str]]:
    protocol = manifest[phase]
    phase_dir = output / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for identity in ("champion", "candidate"):
        identity_reports = {}
        env = manifest["candidate"]["runtimeEnv"] if identity == "candidate" else {}
        for opponent in manifest["opponents"]:
            path = phase_dir / f"{identity}-vs-{opponent['label']}.json"
            if path.exists():
                report = json.loads(path.read_text(encoding="utf-8"))
            else:
                report = run(
                    opponent["repo"],
                    opponent["label"],
                    int(protocol["seedsPerOpponent"]),
                    int(protocol["baseSeed"]),
                    public_telemetry_only=True,
                    semantic_env=env,
                )
                path.write_text(
                    json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
            identity_reports[opponent["label"]] = report
            hashes[path.relative_to(ROOT).as_posix()] = sha256(path)
        reports[identity] = summarize(identity_reports)
    return reports, hashes


def decide(manifest_path: Path, output: Path, execute_confirm: bool) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_provenance(manifest)
    screen, screen_hashes = run_phase(manifest, "screen", output)
    screen_gate = gate(screen["champion"], screen["candidate"], manifest)
    screen_summary = {
        "phase": "screen",
        "protocol": manifest["screen"],
        "results": screen,
        "gate": screen_gate,
        "reportSha256": screen_hashes,
    }
    (output / "screen-summary.json").write_text(
        json.dumps(screen_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if screen_gate["passed"] and not execute_confirm:
        raise ValueError("screen passed; rerun with --execute-confirm")
    if screen_gate["passed"]:
        confirm, confirm_hashes = run_phase(manifest, "confirm", output)
        confirm_gate = gate(confirm["champion"], confirm["candidate"], manifest)
    else:
        confirm, confirm_hashes = {}, {}
        confirm_gate = {"passed": False, "reasons": ["candidate did not pass screen"]}
    promoted = bool(screen_gate["passed"] and confirm_gate["passed"])
    result = {
        "schemaVersion": "1.0.0",
        "issue": manifest["issue"],
        "manifestSha256": sha256(manifest_path),
        "screen": screen_summary,
        "confirm": {
            "opened": bool(screen_gate["passed"]),
            "protocol": manifest["confirm"],
            "results": confirm,
            "gate": confirm_gate,
            "reportSha256": confirm_hashes,
        },
        "promoted": promoted,
        "outcome": "promoted" if promoted else "champion_retained",
        "championBehaviorChanged": promoted,
        "kaggleSubmission": False,
    }
    (output / "decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute-confirm", action="store_true")
    args = parser.parse_args()
    print(json.dumps(decide(args.manifest, args.output, args.execute_confirm), indent=2))


if __name__ == "__main__":
    main()
