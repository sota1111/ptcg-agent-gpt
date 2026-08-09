"""Run the preregistered SOT-2555 paired screen and conditional confirm."""

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
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from evaluate_forward_planning_sot_2539 import compare
    from run_metagame_cv import summarize


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_fingerprints(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    paths = {
        "sourceContract": Path(manifest["sourceContract"]),
        "evaluator": Path("eval/agent_server.py"),
        "championPolicy": Path("main.py"),
        "championDeck": Path(manifest["champion"]["deck"]),
        "candidatePolicy": Path("agents/counter_meta_policy.py"),
        "candidateDeck": Path(manifest["candidate"]["deck"]),
        "candidateContract": Path(manifest["candidate"]["sourceContract"]),
    }
    expected = {
        "sourceContract": manifest["sourceContractSha256"],
        "evaluator": manifest["evaluatorSha256"],
        "championPolicy": manifest["champion"]["policySha256"],
        "championDeck": manifest["champion"]["deckSha256"],
        "candidatePolicy": manifest["candidate"]["policySha256"],
        "candidateDeck": manifest["candidate"]["deckSha256"],
        "candidateContract": manifest["candidate"]["sourceContractSha256"],
    }
    actual = {name: sha256(root / path) for name, path in paths.items()}
    mismatches = [name for name in actual if actual[name] != expected[name]]
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
    candidate: dict[str, Any],
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
        command.extend(["--semantic-deck", str(root / candidate["deck"])])
        for key, value in candidate["environment"].items():
            if key == "PTCG_COUNTER_META_DECK":
                value = str(root / value)
            command.extend(["--semantic-env", f"{key}={value}"])
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
    parser.add_argument("--public-order", nargs="*")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.resolve().parents[2]
    fingerprints = verify_fingerprints(root, manifest)
    source = json.loads((root / manifest["sourceContract"]).read_text())
    if args.phase == "confirm":
        if args.screen_decision is None:
            raise SystemExit("confirm requires --screen-decision")
        screen = json.loads(args.screen_decision.read_text())
        if screen.get("phase") != "screen" or not screen.get("gate", {}).get("passed"):
            raise SystemExit("confirm forbidden: screen gate did not pass")
    phase = manifest["phases"][args.phase]
    source_split = source["splits"][phase["sourceSplit"]]
    if phase["opponents"] != source_split["opponents"]:
        raise ValueError("phase opponents must match the preregistered source split")
    opponents = [
        next(row for row in source["opponents"] if row["id"] == opponent_id)
        for opponent_id in phase["opponents"]
    ]
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    reports = {
        identity: [
            run_report(
                root,
                opponent,
                phase,
                identity,
                manifest["candidate"],
                args.raw_dir / f"{args.phase}-{identity}-{opponent['id']}.json",
            )
            for opponent in opponents
        ]
        for identity in ("champion", "candidate")
    }
    champion = summarize(reports["champion"])
    candidate = summarize(reports["candidate"])
    gate = compare(champion, candidate, manifest["promotionGate"])
    cv_order = [
        name
        for name, _ in sorted(
            candidate["opponents"].items(), key=lambda row: (row[1]["winRate"], row[0])
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
        "champion": champion,
        "candidate": candidate,
        "rawReportSha256": {
            identity: {
                report["opponent"]: sha256(
                    args.raw_dir / f"{args.phase}-{identity}-{report['opponent']}.json"
                )
                for report in reports[identity]
            }
            for identity in reports
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
        "candidateArtifact": manifest["candidate"]["deck"] if gate["passed"] else None,
        "nextPhase": "confirm" if args.phase == "screen" and gate["passed"] else None,
        "decision": (
            "eligible-for-promotion"
            if args.phase == "confirm" and gate["passed"]
            else "retain-champion"
        ),
        "kaggleSubmitted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"gate": gate, "decision": result["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
