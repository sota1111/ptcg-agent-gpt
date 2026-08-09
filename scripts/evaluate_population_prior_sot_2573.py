"""Run the frozen SOT-2573 population-prior paired screen/confirm evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_forward_planning_sot_2539 import compare
    from scripts.run_metagame_cv import summarize
except ModuleNotFoundError:
    from evaluate_forward_planning_sot_2539 import compare
    from run_metagame_cv import summarize


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_fingerprints(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    paths = manifest["fingerprintedInputs"]
    actual = {name: sha256(root / row["path"]) for name, row in paths.items()}
    mismatches = [name for name, digest in actual.items() if digest != paths[name]["sha256"]]
    if mismatches:
        raise ValueError(f"fingerprint mismatch: {', '.join(mismatches)}")
    return actual


def reusable(raw: Path, identity: str, opponent: str, phase: dict[str, Any]) -> bool:
    if not raw.is_file():
        return False
    report = json.loads(raw.read_text())
    return (
        report.get("evaluationIdentity") == identity
        and report.get("opponent") == opponent
        and report.get("base_seed") == phase["baseSeed"]
        and report.get("seeds") == phase["seedsPerOpponent"]
    )


def run_report(
    root: Path,
    opponent: dict[str, Any],
    phase: dict[str, Any],
    identity: str,
    raw: Path,
) -> dict[str, Any]:
    if reusable(raw, identity, opponent["id"], phase):
        return json.loads(raw.read_text())
    repo = Path(opponent["repo"])
    if not repo.is_absolute():
        repo = root / repo
    command = [
        sys.executable,
        "eval/battle_vs.py",
        "--opponent",
        str(repo),
        "--label",
        opponent["id"],
        "--seeds",
        str(phase["seedsPerOpponent"]),
        "--base-seed",
        str(phase["baseSeed"]),
        "--public-telemetry-only",
        "--json",
        str(raw),
    ]
    if identity == "candidate":
        command.extend(
            [
                "--semantic-env",
                "PTCG_TELEMETRY_PROTOCOL=1",
                "--semantic-env",
                "PTCG_POPULATION_PRIOR_CANDIDATE=1",
            ]
        )
    if opponent.get("deckPath"):
        deck = Path(opponent["deckPath"])
        command.extend(["--opponent-deck", str(deck if deck.is_absolute() else root / deck)])
    subprocess.run(command, cwd=root, check=True)
    report = json.loads(raw.read_text())
    report["evaluationIdentity"] = identity
    report["lineage"] = {
        "opponentId": opponent["id"],
        "archetype": opponent["archetype"],
        "policyEntity": opponent["policyEntity"],
        "deckEntity": opponent["deckEntity"],
        "submissionLineage": opponent["submissionLineage"],
        "split": phase["sourceSplit"],
        "agentSeeds": [match["agent_seed"] for match in report["matches"]],
        "semanticSeats": [match["semantic_seat"] for match in report["matches"]],
    }
    raw.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def archetype_summary(reports: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for report in reports:
        archetype = report["lineage"]["archetype"]
        matches = report["n_matches"]
        wins = report["wins_semantic"]
        result[archetype] = {"wins": wins, "matches": matches, "winRate": wins / matches}
    return result


def gate_result(
    champion: dict[str, Any],
    candidate: dict[str, Any],
    champion_archetypes: dict[str, Any],
    candidate_archetypes: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    result = compare(champion, candidate, gate)
    for archetype, baseline in champion_archetypes.items():
        if candidate_archetypes[archetype]["winRate"] < baseline["winRate"]:
            result["reasons"].append(f"archetype regression: {archetype}")
    result["passed"] = not result["reasons"]
    result["checks"] = {
        "pooledStrictImprovement": candidate["pool"]["wins"] > champion["pool"]["wins"],
        "everyArchetypeNonRegression": all(
            candidate_archetypes[name]["winRate"] >= row["winRate"]
            for name, row in champion_archetypes.items()
        ),
        "everyMatchupNonRegression": all(
            candidate["opponents"][name]["winRate"] >= row["winRate"]
            for name, row in champion["opponents"].items()
        ),
        "bothSeatsNonRegression": all(
            candidate["seats"][name]["winRate"] >= row["winRate"]
            for name, row in champion["seats"].items()
        ),
        "faultsWithinLimit": candidate["pool"]["faults"] <= gate["faultsMax"],
        "unfinishedWithinLimit": candidate["pool"]["unfinished"] <= gate["unfinishedMax"],
        "runtimeWithinLimit": (
            result["meanRuntimeRatio"] <= gate["meanRuntimeRatioMax"]
            and candidate["pool"]["runtimeSeconds"]["max"] < gate["matchRuntimeSecondsMaxExclusive"]
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--phase", choices=("screen", "confirm"), required=True)
    parser.add_argument("--screen-decision", type=Path)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-order", nargs="*")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.resolve().parents[2]
    fingerprints = verify_fingerprints(root, manifest)
    population_contract = json.loads((root / manifest["sourceContract"]).read_text())
    contract = json.loads((root / population_contract["sourceContract"]).read_text())
    population = json.loads((root / manifest["populationSnapshot"]).read_text())
    if args.phase == "confirm":
        if args.screen_decision is None:
            raise SystemExit("confirm requires --screen-decision")
        screen = json.loads(args.screen_decision.read_text())
        if screen.get("phase") != "screen" or not screen.get("gate", {}).get("passed"):
            raise SystemExit("confirm forbidden: screen gate did not pass")
    phase = manifest["phases"][args.phase]
    source_split = contract["splits"][phase["sourceSplit"]]
    if phase["opponents"] != source_split["opponents"]:
        raise ValueError("phase opponents must match the preregistered source split")
    members = {row["id"]: row for row in population["members"]}
    opponents = []
    for opponent_id in phase["opponents"]:
        opponent = next(row for row in contract["opponents"] if row["id"] == opponent_id).copy()
        member = members[phase["populationMemberByOpponent"][opponent_id]]
        if member["split"] != phase["sourceSplit"]:
            raise ValueError(f"population split mismatch: {opponent_id}")
        opponent.update(
            {
                key: member[key]
                for key in ("archetype", "policyEntity", "deckEntity", "submissionLineage")
            }
        )
        opponents.append(opponent)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    reports = {
        identity: [
            run_report(
                root,
                opponent,
                phase,
                identity,
                args.raw_dir / f"{args.phase}-{identity}-{opponent['id']}.json",
            )
            for opponent in opponents
        ]
        for identity in ("champion", "candidate")
    }
    champion = summarize(reports["champion"])
    candidate = summarize(reports["candidate"])
    champion_archetypes = archetype_summary(reports["champion"])
    candidate_archetypes = archetype_summary(reports["candidate"])
    gate = gate_result(
        champion, candidate, champion_archetypes, candidate_archetypes, manifest["promotionGate"]
    )
    cv_order = [
        name
        for name, _ in sorted(
            candidate_archetypes.items(), key=lambda row: (row[1]["winRate"], row[0])
        )
    ]
    public_order = args.public_order or []
    shared = [name for name in cv_order if name in public_order]
    public_shared = [name for name in public_order if name in cv_order]
    result = {
        "schemaVersion": "1.0.0",
        "issue": manifest["issue"],
        "axis": manifest["axis"],
        "phase": args.phase,
        "fingerprints": fingerprints,
        "split": {
            "source": phase["sourceSplit"],
            "window": source_split["window"],
            "baseSeed": phase["baseSeed"],
            "seats": phase["seats"],
            "equalBudget": manifest["budget"]["equal"],
        },
        "champion": {**champion, "archetypes": champion_archetypes},
        "candidate": {**candidate, "archetypes": candidate_archetypes},
        "lineage": {
            identity: [report["lineage"] for report in rows] for identity, rows in reports.items()
        },
        "rawReportSha256": {
            identity: {
                report["opponent"]: sha256(
                    args.raw_dir / f"{args.phase}-{identity}-{report['opponent']}.json"
                )
                for report in rows
            }
            for identity, rows in reports.items()
        },
        "gate": gate,
        "cvPublicGap": {
            "cvOrder": cv_order,
            "publicOrder": public_order or None,
            "sharedOrderAgreement": shared == public_shared if shared else None,
            "selectedOrder": cv_order,
            "selectionBasis": "cv-pessimistic" if public_order else "cv-public-unavailable",
            "publicBestSelectionAllowed": False,
        },
        "candidateDefaultEnabled": False,
        "candidateHandoff": (
            manifest["candidateHandoff"] if args.phase == "confirm" and gate["passed"] else None
        ),
        "revert": {
            "required": False,
            "reason": "candidate was never enabled by default",
            "retainedDefault": "champion",
        },
        "nextPhase": "confirm" if args.phase == "screen" and gate["passed"] else None,
        "decision": "promote-candidate"
        if args.phase == "confirm" and gate["passed"]
        else "retain-champion",
        "kaggleSubmitted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"gate": gate, "decision": result["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
