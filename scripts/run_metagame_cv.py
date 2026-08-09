"""Run the frozen SOT-2538 baseline pool through the real engine."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.audit_metagame_cv import audit_manifest
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from audit_metagame_cv import audit_manifest


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [match for report in reports for match in report["matches"]]
    runtimes = sorted(match["runtime_s"] for match in matches)
    p95_index = max(0, (95 * len(runtimes) + 99) // 100 - 1)
    seats = {
        str(seat): {
            "wins": sum(m["semantic_won"] for m in matches if m["semantic_seat"] == seat),
            "matches": sum(m["semantic_seat"] == seat for m in matches),
        }
        for seat in (0, 1)
    }
    for value in seats.values():
        value["winRate"] = value["wins"] / value["matches"] if value["matches"] else 0.0
    return {
        "opponents": {
            report["opponent"]: {
                "wins": report["wins_semantic"],
                "matches": report["n_matches"],
                "winRate": report["wins_semantic"] / report["n_matches"],
            }
            for report in reports
        },
        "seats": seats,
        "pool": {
            "wins": sum(m["semantic_won"] for m in matches),
            "matches": len(matches),
            "faults": sum(r["faults_semantic"] + r["faults_opp"] for r in reports),
            "unfinished": sum(r["unfinished"] for r in reports),
            "runtimeSeconds": {
                "mean": sum(m["runtime_s"] for m in matches) / len(matches),
                "p95": runtimes[p95_index],
                "max": max(m["runtime_s"] for m in matches),
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    audit = audit_manifest(args.manifest)
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.resolve().parents[2]
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for split_name, split in manifest["splits"].items():
        for opponent_id in split["opponents"]:
            opponent = next(row for row in manifest["opponents"] if row["id"] == opponent_id)
            repo = Path(opponent["repo"])
            if not repo.is_absolute():
                repo = root / repo
            raw = args.raw_dir / f"{split_name}-{opponent_id}.json"
            command = [
                sys.executable,
                "eval/battle_vs.py",
                "--opponent",
                str(repo),
                "--label",
                opponent_id,
                "--seeds",
                str(split["seedsPerOpponent"]),
                "--base-seed",
                str(split["baseSeed"]),
                "--json",
                str(raw),
            ]
            if opponent.get("deckPath"):
                deck = Path(opponent["deckPath"])
                if not deck.is_absolute():
                    deck = root / deck
                command.extend(["--opponent-deck", str(deck)])
            report = json.loads(raw.read_text()) if raw.is_file() else None
            reusable = bool(
                report
                and report.get("opponent") == opponent_id
                and report.get("base_seed") == split["baseSeed"]
                and report.get("seeds") == split["seedsPerOpponent"]
            )
            if not reusable:
                subprocess.run(command, cwd=root, check=True)
                report = json.loads(raw.read_text())
            assert report is not None
            report["cvSplit"] = split_name
            reports.append(report)
    summary = {
        "schemaVersion": "1.0.0",
        "issue": manifest["issue"],
        "audit": audit,
        "baseline": summarize(reports),
        "screenConfirmGateFailClosed": True,
        "candidateChanged": False,
        "kaggleSubmitted": False,
    }
    if summary["baseline"]["pool"]["faults"] or summary["baseline"]["pool"]["unfinished"]:
        raise RuntimeError("baseline must finish with zero faults and zero unfinished matches")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["baseline"]["pool"], sort_keys=True))


if __name__ == "__main__":
    main()
