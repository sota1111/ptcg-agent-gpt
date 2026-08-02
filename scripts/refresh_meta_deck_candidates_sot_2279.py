"""Generate and screen the preregistered SOT-2279 one-change deck candidates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ptcg_agent.deck_preselection import load_cards, load_deck
from ptcg_agent.meta_deck_candidates import OneChange, generate_one_change_candidates, sha256_file

ROOT = Path(__file__).resolve().parents[1]


def validate_provenance(manifest: dict[str, Any]) -> None:
    """Fail closed if a frozen champion or opponent input has drifted."""
    champion = manifest["champion"]
    for key, relative_path in (("deck_sha256", champion["deck"]), ("main_sha256", "main.py")):
        actual = sha256_file(ROOT / relative_path)
        if actual != champion[key]:
            raise ValueError(f"champion {relative_path} fingerprint drift: {actual}")
    for opponent in manifest["opponents"]:
        repository = Path(opponent["repo"])
        actual_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual_commit != opponent["commit"]:
            raise ValueError(f"opponent {opponent['label']} commit drift: {actual_commit}")
        actual_deck = sha256_file(repository / "deck.csv")
        if actual_deck != opponent["deck_sha256"]:
            raise ValueError(f"opponent {opponent['label']} deck fingerprint drift: {actual_deck}")


def generate(manifest: dict[str, Any], output: Path) -> dict[str, Any]:
    validate_provenance(manifest)
    champion_path = ROOT / manifest["champion"]["deck"]
    cards_path = ROOT / manifest["inputs"]["card_database"]
    cards = load_cards(cards_path)
    changes = [
        OneChange(
            candidate_id=row["id"],
            remove_card_id=int(row["remove_card_id"]),
            add_card_id=int(row["add_card_id"]),
            role=row["role"],
            rationale=row["rationale"],
        )
        for row in manifest["candidate_changes"]
    ]
    result = generate_one_change_candidates(
        champion=load_deck(champion_path), changes=changes, cards=cards
    )
    result["provenance"] = {
        "manifest_sha256": sha256_file(ROOT / manifest["manifest_path"]),
        "champion_deck_sha256": sha256_file(champion_path),
        "card_database_sha256": sha256_file(cards_path),
        "opponents": manifest["opponents"],
    }
    deck_dir = output / "decks"
    deck_dir.mkdir(parents=True, exist_ok=True)
    for row in result["candidates"]:
        (deck_dir / f"{row['id']}.csv").write_text(
            "\n".join(map(str, row["cards"])) + "\n", encoding="utf-8"
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "candidates.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    matches = report["matches"]
    return {
        "matches": report["n_matches"],
        "wins": report["wins_semantic"],
        "win_rate": report["winrate_semantic_excl_draws"],
        "faults": report["faults_semantic"],
        "unfinished": report["unfinished"],
        "first_seat_wins": sum(
            bool(row["semantic_won"]) for row in matches if row["semantic_seat"] == 0
        ),
        "second_seat_wins": sum(
            bool(row["semantic_won"]) for row in matches if row["semantic_seat"] == 1
        ),
    }


def screen(manifest: dict[str, Any], generated: dict[str, Any], output: Path) -> dict[str, Any]:
    raw_dir = output / "screen"
    raw_dir.mkdir(parents=True, exist_ok=True)
    decks = [("champion", ROOT / manifest["champion"]["deck"])] + [
        (row["id"], output / "decks" / f"{row['id']}.csv")
        for row in generated["candidates"]
    ]
    by_deck: dict[str, dict[str, Any]] = {}
    for deck_id, deck_path in decks:
        reports = []
        for opponent in manifest["opponents"]:
            report_path = raw_dir / f"{deck_id}-vs-{opponent['label']}.json"
            if not report_path.exists():
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "eval/battle_vs.py"),
                        "--opponent",
                        opponent["repo"],
                        "--label",
                        opponent["label"],
                        "--seeds",
                        str(manifest["screen"]["seeds_per_opponent"]),
                        "--base-seed",
                        str(manifest["screen"]["base_seed"]),
                        "--semantic-deck",
                        str(deck_path),
                        "--json",
                        str(report_path),
                    ],
                    cwd=ROOT,
                    check=True,
                )
            reports.append(json.loads(report_path.read_text(encoding="utf-8")))
        rows = [_summary(report) for report in reports]
        by_deck[deck_id] = {
            "matches": sum(row["matches"] for row in rows),
            "wins": sum(row["wins"] for row in rows),
            "win_rate": sum(row["wins"] for row in rows) / sum(row["matches"] for row in rows),
            "faults": sum(row["faults"] for row in rows),
            "unfinished": sum(row["unfinished"] for row in rows),
            "opponents": {
                opponent["label"]: row
                for opponent, row in zip(manifest["opponents"], rows, strict=True)
            },
        }
    baseline = by_deck["champion"]
    gate = manifest["screen"]["gate"]
    decisions = []
    for candidate in generated["candidates"]:
        row = by_deck[candidate["id"]]
        worst_labels = manifest["pools"]["worst_matchups"]
        candidate_worst = sum(row["opponents"][label]["wins"] for label in worst_labels)
        champion_worst = sum(baseline["opponents"][label]["wins"] for label in worst_labels)
        passed = (
            row["wins"] - baseline["wins"] >= gate["minimum_total_win_delta"]
            and candidate_worst - champion_worst >= gate["minimum_worst_matchup_win_delta"]
            and row["faults"] <= baseline["faults"]
            and row["unfinished"] <= baseline["unfinished"]
        )
        decisions.append(
            {
                "id": candidate["id"],
                "passed": passed,
                "total_win_delta": row["wins"] - baseline["wins"],
                "worst_matchup_win_delta": candidate_worst - champion_worst,
                "reason": (
                    "all preregistered screen gates passed"
                    if passed
                    else "one or more preregistered screen gates missed"
                ),
            }
        )
    passing = sorted(
        (row for row in decisions if row["passed"]),
        key=lambda row: (-row["worst_matchup_win_delta"], -row["total_win_delta"], row["id"]),
    )[: int(manifest["screen"]["max_confirm_candidates"])]
    result = {
        "schema_version": 1,
        "issue": manifest["issue"],
        "protocol": manifest["screen"],
        "results": by_deck,
        "decisions": decisions,
        "confirm_candidates": [row["id"] for row in passing],
        "outcome": "advance_to_confirm" if passing else "no_promotion_candidates",
    }
    (output / "screen-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "eval/manifests/sot-2279-meta-deck-candidates.json"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/sot-2279-meta-deck-candidates",
    )
    parser.add_argument("--screen", action="store_true")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_path"] = manifest_path.relative_to(ROOT).as_posix()
    generated = generate(manifest, args.output.resolve())
    if args.screen:
        screen(manifest, generated, args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
