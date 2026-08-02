"""Run the preregistered SOT-2280 screen -> confirm deck-promotion protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_report(report: dict[str, Any], *, base_seed: int, seeds: int) -> None:
    expected = set(range(base_seed, base_seed + seeds))
    actual = {int(row["agent_seed"]) for row in report["matches"]}
    if actual != expected:
        raise ValueError(
            f"seed provenance mismatch: expected {sorted(expected)}, got {sorted(actual)}"
        )
    for seed in expected:
        seats = {
            int(row["semantic_seat"]) for row in report["matches"] if int(row["agent_seed"]) == seed
        }
        if seats != {0, 1}:
            raise ValueError(f"seed {seed} does not cover both seats")


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [row for report in reports for row in report["matches"]]
    runtimes = [float(row["runtime_s"]) for row in matches]
    opponents = {
        str(report["opponent"]): {
            "matches": int(report["n_matches"]),
            "wins": int(report["wins_semantic"]),
            "win_rate": int(report["wins_semantic"]) / int(report["n_matches"]),
            "faults": int(report["faults_semantic"]),
            "unfinished": int(report["unfinished"]),
        }
        for report in reports
    }
    first = [row for row in matches if int(row["semantic_seat"]) == 0]
    second = [row for row in matches if int(row["semantic_seat"]) == 1]
    wins = sum(bool(row["semantic_won"]) for row in matches)
    return {
        "matches": len(matches),
        "wins": wins,
        "win_rate": wins / len(matches),
        "first_seat_win_rate": sum(bool(row["semantic_won"]) for row in first) / len(first),
        "second_seat_win_rate": sum(bool(row["semantic_won"]) for row in second) / len(second),
        "faults": sum(int(report["faults_semantic"]) for report in reports),
        "unfinished": sum(int(report["unfinished"]) for report in reports),
        "runtime_s": {
            "mean": statistics.fmean(runtimes),
            "p95": sorted(runtimes)[math.ceil(0.95 * len(runtimes)) - 1],
            "max": max(runtimes),
        },
        "opponents": opponents,
    }


def apply_gate(
    champion: dict[str, Any], candidate: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate["win_rate"] <= champion["win_rate"]:
        reasons.append("pool win rate did not strictly improve")
    for label in manifest["pools"]["worst_matchups"]:
        if candidate["opponents"][label]["win_rate"] < champion["opponents"][label]["win_rate"]:
            reasons.append(f"{label} win rate regressed")
    if candidate["faults"] > champion["faults"]:
        reasons.append("faults increased")
    if candidate["unfinished"] > champion["unfinished"]:
        reasons.append("unfinished matches increased")
    ratio = candidate["runtime_s"]["mean"] / champion["runtime_s"]["mean"]
    if candidate["runtime_s"]["max"] >= float(manifest["gate"]["match_runtime_seconds_max"]):
        reasons.append("match runtime reached limit")
    return {"passed": not reasons, "runtime_ratio": ratio, "reasons": reasons}


def validate_provenance(manifest: dict[str, Any]) -> None:
    if sha256(ROOT / manifest["champion"]["deck"]) != manifest["champion"]["deck_sha256"]:
        raise ValueError("champion deck fingerprint drift")
    if sha256(ROOT / "main.py") != manifest["champion"]["main_sha256"]:
        raise ValueError("champion main.py fingerprint drift")
    for opponent in manifest["opponents"]:
        repo = Path(opponent["repo"])
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()
        if commit != opponent["commit"] or sha256(repo / "deck.csv") != opponent["deck_sha256"]:
            raise ValueError(f"opponent {opponent['label']} provenance drift")


def load_phase(
    manifest: dict[str, Any], identities: list[str], directory: Path, phase: str
) -> tuple[dict[str, Any], dict[str, str]]:
    directory = directory.resolve()
    protocol = manifest[phase]
    results: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for identity in identities:
        reports = []
        for opponent in manifest["opponents"]:
            path = directory / f"{identity}-vs-{opponent['label']}.json"
            report = json.loads(path.read_text(encoding="utf-8"))
            validate_report(
                report,
                base_seed=int(protocol["base_seed"]),
                seeds=int(protocol["seeds_per_opponent"]),
            )
            reports.append(report)
            hashes[path.relative_to(ROOT).as_posix()] = sha256(path)
        results[identity] = summarize(reports)
    return results, hashes


def phase_decisions(
    results: dict[str, Any], candidates: list[str], manifest: dict[str, Any]
) -> dict[str, Any]:
    return {
        candidate: apply_gate(results["champion"], results[candidate], manifest)
        for candidate in candidates
    }


def run_confirm(manifest: dict[str, Any], candidates: list[str], output: Path) -> None:
    directory = output / "confirm"
    directory.mkdir(parents=True, exist_ok=True)
    source_decks = ROOT / "artifacts/sot-2279-meta-deck-candidates/decks"
    identities = [("champion", ROOT / manifest["champion"]["deck"])] + [
        (candidate, source_decks / f"{candidate}.csv") for candidate in candidates
    ]
    for identity, deck in identities:
        for opponent in manifest["opponents"]:
            destination = directory / f"{identity}-vs-{opponent['label']}.json"
            if destination.exists():
                continue
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "eval/battle_vs.py"),
                    "--opponent",
                    opponent["repo"],
                    "--label",
                    opponent["label"],
                    "--seeds",
                    str(manifest["confirm"]["seeds_per_opponent"]),
                    "--base-seed",
                    str(manifest["confirm"]["base_seed"]),
                    "--semantic-deck",
                    str(deck),
                    "--json",
                    str(destination),
                ],
                cwd=ROOT,
                check=True,
            )


def decide(manifest_path: Path, output: Path, *, execute_confirm: bool) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_provenance(manifest)
    candidates_artifact = ROOT / manifest["source"]["candidate_artifact"]
    candidates_data = json.loads(candidates_artifact.read_text(encoding="utf-8"))
    candidates = [str(row["id"]) for row in candidates_data["candidates"]]
    screen_dir = ROOT / manifest["source"]["screen_artifact_dir"]
    screen_results, screen_hashes = load_phase(
        manifest, ["champion", *candidates], screen_dir, "screen"
    )
    screen_decisions = phase_decisions(screen_results, candidates, manifest)
    confirm_candidates = sorted(
        (candidate for candidate in candidates if screen_decisions[candidate]["passed"]),
        key=lambda candidate: (
            -(screen_results[candidate]["win_rate"] - screen_results["champion"]["win_rate"]),
            candidate,
        ),
    )
    output.mkdir(parents=True, exist_ok=True)
    screen_summary = {
        "schema_version": 1,
        "phase": "screen",
        "protocol": manifest["screen"],
        "results": screen_results,
        "decisions": screen_decisions,
        "report_sha256": screen_hashes,
        "confirm_candidates": confirm_candidates,
    }
    (output / "screen-summary.json").write_text(
        json.dumps(screen_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if confirm_candidates and not execute_confirm:
        raise ValueError("screen passed candidates; rerun with --execute-confirm")
    if confirm_candidates:
        run_confirm(manifest, confirm_candidates, output)
        confirm_results, confirm_hashes = load_phase(
            manifest, ["champion", *confirm_candidates], output / "confirm", "confirm"
        )
        confirm_decisions = phase_decisions(confirm_results, confirm_candidates, manifest)
    else:
        confirm_results, confirm_hashes, confirm_decisions = {}, {}, {}
    promoted = next(
        (candidate for candidate in confirm_candidates if confirm_decisions[candidate]["passed"]),
        None,
    )
    champion_before = manifest["champion"]["deck_sha256"]
    if promoted:
        shutil.copyfile(
            ROOT / "artifacts/sot-2279-meta-deck-candidates/decks" / f"{promoted}.csv",
            ROOT / manifest["champion"]["deck"],
        )
    result = {
        "schema_version": 1,
        "issue": manifest["issue"],
        "manifest_sha256": sha256(manifest_path),
        "candidate_artifact_sha256": sha256(candidates_artifact),
        "screen": screen_summary,
        "confirm": {
            "protocol": manifest["confirm"],
            "results": confirm_results,
            "decisions": confirm_decisions,
            "report_sha256": confirm_hashes,
        },
        "promoted": promoted,
        "champion_deck_sha256_before": champion_before,
        "champion_deck_sha256_after": sha256(ROOT / manifest["champion"]["deck"]),
        "champion_changed": promoted is not None,
        "outcome": "promoted" if promoted else "champion_retained",
    }
    (output / "decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "eval/manifests/sot-2280-deck-promotion.json",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/sot-2280-deck-promotion")
    parser.add_argument("--execute-confirm", action="store_true")
    args = parser.parse_args()
    result = decide(
        args.manifest.resolve(),
        args.output.resolve(),
        execute_confirm=args.execute_confirm,
    )
    print(json.dumps({"outcome": result["outcome"], "promoted": result["promoted"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
