"""Run and gate the preregistered SOT-2539 forward-planning candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.run_metagame_cv import summarize


def compare(champion: dict, candidate: dict, gate: dict) -> dict:
    reasons: list[str] = []
    cp, xp = champion["pool"], candidate["pool"]
    if candidate["pool"]["wins"] <= champion["pool"]["wins"]:
        reasons.append("pooled wins did not strictly improve")
    for opponent, baseline in champion["opponents"].items():
        if candidate["opponents"][opponent]["winRate"] < baseline["winRate"]:
            reasons.append(f"opponent regression: {opponent}")
    for seat, baseline in champion["seats"].items():
        if candidate["seats"][seat]["winRate"] < baseline["winRate"]:
            reasons.append(f"seat regression: {seat}")
    if xp["faults"] > gate["faultsMax"]:
        reasons.append("candidate fault observed")
    if xp["unfinished"] > gate["unfinishedMax"]:
        reasons.append("candidate unfinished match observed")
    ratio = xp["runtimeSeconds"]["mean"] / max(cp["runtimeSeconds"]["mean"], 1e-9)
    if ratio > gate["meanRuntimeRatioMax"]:
        reasons.append("mean runtime ratio exceeded")
    if xp["runtimeSeconds"]["max"] >= gate["matchRuntimeSecondsMaxExclusive"]:
        reasons.append("match runtime limit exceeded")
    return {"passed": not reasons, "reasons": reasons, "meanRuntimeRatio": ratio}


def run_report(root: Path, opponent: dict, phase: dict, identity: str, raw: Path) -> dict:
    repo = Path(opponent["repo"])
    if not repo.is_absolute():
        repo = root / repo
    command = [
        sys.executable, "eval/battle_vs.py", "--opponent", str(repo),
        "--label", opponent["id"], "--seeds", str(phase["seedsPerOpponent"]),
        "--base-seed", str(phase["baseSeed"]), "--public-telemetry-only",
        "--json", str(raw),
    ]
    if identity == "candidate":
        command.extend(["--semantic-env", "PTCG_FORCED_ROOT_EXPLORATION_CANDIDATE=1"])
    if opponent.get("deckPath"):
        deck = Path(opponent["deckPath"])
        command.extend(["--opponent-deck", str(deck if deck.is_absolute() else root / deck)])
    subprocess.run(command, cwd=root, check=True)
    report = json.loads(raw.read_text())
    report["evaluationIdentity"] = identity
    raw.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--phase", choices=("screen", "confirm"), required=True)
    parser.add_argument("--screen-decision", type=Path)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.resolve().parents[2]
    source = json.loads((root / manifest["sourceContract"]).read_text())
    if args.phase == "confirm":
        if args.screen_decision is None:
            raise SystemExit("confirm requires --screen-decision")
        receipt = json.loads(args.screen_decision.read_text())
        if receipt.get("phase") != "screen" or not receipt.get("gate", {}).get("passed"):
            raise SystemExit("confirm forbidden: screen gate did not pass")
    phase = manifest["phases"][args.phase]
    opponents = [next(row for row in source["opponents"] if row["id"] == oid) for oid in phase["opponents"]]
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    reports = {}
    for identity in ("champion", "candidate"):
        reports[identity] = [
            run_report(root, opponent, phase, identity, args.raw_dir / f"{identity}-{opponent['id']}.json")
            for opponent in opponents
        ]
    champion = summarize(reports["champion"])
    candidate = summarize(reports["candidate"])
    result = {
        "schemaVersion": "1.0.0", "issue": "SOT-2539", "axis": manifest["axis"],
        "phase": args.phase, "champion": champion, "candidate": candidate,
        "gate": compare(champion, candidate, manifest["promotionGate"]),
        "candidateDefaultEnabled": False, "kaggleSubmitted": False,
    }
    result["nextPhase"] = "confirm" if args.phase == "screen" and result["gate"]["passed"] else None
    result["decision"] = "eligible-for-promotion" if args.phase == "confirm" and result["gate"]["passed"] else "retain-champion"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["gate"], sort_keys=True))


if __name__ == "__main__":
    main()
