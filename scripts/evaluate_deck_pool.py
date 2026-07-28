"""Run the reproducible SOT-2058 deck-pool evaluation and write review artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ptcg_agent.deck_pool_evaluation import (
    finalize_pool,
    summarize_reports,
    write_json,
    write_pool_csv,
)
from ptcg_agent.deck_preselection import load_cards, load_deck, validate_deck

ROOT = Path(__file__).resolve().parents[1]


def _write_deck(cards: list[int], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(map(str, cards)) + "\n", encoding="utf-8")


def run(config_path: Path, output: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    shortlist = json.loads(
        (ROOT / "artifacts/sot-1890-deck-shortlist.json").read_text(encoding="utf-8")
    )["shortlist"]
    deck_dir = output / "decks"
    report_dir = output / "raw"
    report_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[str, Path, tuple[str, ...]]] = []
    evaluations: dict[str, dict[str, Any]] = {}
    for candidate in config["candidates"]:
        candidate_id = str(candidate["id"])
        source = shortlist[int(candidate["shortlistIndex"])]
        deck_path = deck_dir / f"{candidate_id}.csv"
        _write_deck(source["cards"], deck_path)
        candidates.append((candidate_id, deck_path, tuple(candidate["roles"])))
        reports = []
        for opponent in config["opponents"]:
            report_path = report_dir / f"{candidate_id}-vs-{opponent['id']}.json"
            command = [
                sys.executable,
                str(ROOT / "eval/battle_vs.py"),
                "--opponent",
                str(opponent["repository"]),
                "--label",
                str(opponent["id"]),
                "--seeds",
                str(config["seeds"]),
                "--base-seed",
                str(config["baseSeed"]),
                "--semantic-deck",
                str(deck_path),
                "--json",
                str(report_path),
            ]
            if not report_path.exists():
                subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["archetype"] = opponent["archetype"]
            reports.append(report)
        evaluations[candidate_id] = summarize_reports(reports)

    cards = load_cards(ROOT / "data/EN_Card_Data.csv")
    legality = {}
    for candidate_id, path, _roles in candidates:
        errors = validate_deck(load_deck(path), cards)
        legality[candidate_id] = {"legal": not errors, "loadable": True, "errors": errors}
    pool = finalize_pool(
        baseline=ROOT / "deck.csv",
        candidates=candidates,
        evaluations=evaluations,
        max_additions=int(config["maxAdditions"]),
        minimum_win_rate=float(config["minimumWinRate"]),
    )
    result = {
        "schemaVersion": "1.0.0",
        "configuration": config,
        "evaluations": evaluations,
        "legality": legality,
        "pool": pool,
    }
    write_json(result, output / "summary.json")
    write_pool_csv(pool, output / "final-deck-pool.csv")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/deck-pool-evaluation.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/sot-2058-deck-pool")
    args = parser.parse_args()
    run(args.config.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
