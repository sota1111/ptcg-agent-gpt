"""Aggregate fixed-seed, seat-reversed battles and finalize a bounded deck pool."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ptcg_agent.deck_preselection import deck_hash, load_deck


def summarize_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce overall, seat, and opponent metrics from battle_vs reports."""
    if not reports:
        raise ValueError("at least one battle report is required")
    matches = [match for report in reports for match in report["matches"]]
    seeds = sorted({int(match["agent_seed"]) for match in matches})
    if len(seeds) < 2:
        raise ValueError("evaluation requires multiple seeds")
    if {bool(match["semantic_first"]) for match in matches} != {False, True}:
        raise ValueError("evaluation requires both first and second seat")

    def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
        decided = [row for row in rows if not row["unfinished"] and row["winner"] != "draw"]
        wins = sum(bool(row["semantic_won"]) for row in decided)
        return {
            "matches": len(rows),
            "wins": wins,
            "losses": len(decided) - wins,
            "draws": sum(row["winner"] == "draw" for row in rows),
            "winRate": round(wins / len(decided), 6) if decided else None,
            "averageDecisions": round(sum(int(row["steps"]) for row in rows) / len(rows), 3),
            "averageTurns": round(sum(int(row["steps"]) for row in rows) / (2 * len(rows)), 3),
            "invalidActions": sum(row["fault"] == "semantic" for row in rows),
            "errors": sum(bool(row["unfinished"]) for row in rows),
        }

    by_opponent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_archetype: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        by_opponent[str(report["opponent"])].extend(report["matches"])
        by_archetype[str(report.get("archetype", report["opponent"]))].extend(report["matches"])
    return {
        "schemaVersion": "1.0.0",
        "seeds": seeds,
        "overall": metrics(matches),
        "bySeat": {
            "first": metrics([row for row in matches if row["semantic_first"]]),
            "second": metrics([row for row in matches if not row["semantic_first"]]),
        },
        "byOpponent": {opponent: metrics(rows) for opponent, rows in sorted(by_opponent.items())},
        "byArchetype": {
            archetype: metrics(rows) for archetype, rows in sorted(by_archetype.items())
        },
    }


def finalize_pool(
    *,
    baseline: Path,
    candidates: list[tuple[str, Path, tuple[str, ...]]],
    evaluations: dict[str, dict[str, Any]],
    max_additions: int = 2,
    minimum_win_rate: float = 0.5,
) -> dict[str, Any]:
    """Keep the baseline and add only evaluated, legal, non-duplicate candidates."""
    baseline_cards = load_deck(baseline)
    retained_hashes = {deck_hash(baseline_cards)}

    def recorded_path(path: Path) -> str:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    decisions: list[dict[str, Any]] = [
        {
            "id": "baseline",
            "path": recorded_path(baseline),
            "hash": deck_hash(baseline_cards),
            "decision": "keep",
            "roles": ["baseline", "top"],
            "reason": "existing legal baseline retained",
        }
    ]
    additions = 0
    for candidate_id, path, roles in candidates:
        cards = load_deck(path)
        candidate_hash = deck_hash(cards)
        evaluation = evaluations[candidate_id]
        win_rate = evaluation["overall"]["winRate"]
        if candidate_hash in retained_hashes:
            decision, reason = "remove", "exact duplicate of a retained deck"
        elif additions >= max_additions:
            decision, reason = "remove", "bounded replacement limit reached"
        elif win_rate is None or float(win_rate) < minimum_win_rate:
            decision, reason = "remove", f"evaluation win rate {win_rate} below {minimum_win_rate}"
        elif evaluation["overall"]["invalidActions"] or evaluation["overall"]["errors"]:
            decision, reason = "remove", "invalid action or unfinished match observed"
        else:
            decision = "add"
            reason = f"multi-seed seat-reversed win rate {float(win_rate):.3f}"
            additions += 1
            retained_hashes.add(candidate_hash)
        decisions.append(
            {
                "id": candidate_id,
                "path": recorded_path(path),
                "hash": candidate_hash,
                "decision": decision,
                "roles": list(roles),
                "reason": reason,
            }
        )
    return {
        "schemaVersion": "1.0.0",
        "beforeCount": 1,
        "afterCount": 1 + additions,
        "limits": {
            "maxAdditions": max_additions,
            "minimumWinRate": minimum_win_rate,
        },
        "decisions": decisions,
    }


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_pool_csv(pool: dict[str, Any], path: Path) -> None:
    """Write a stable, human-reviewable final-pool decision table."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("id", "path", "hash", "decision", "roles", "reason"),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in pool["decisions"]:
            writer.writerow({**row, "roles": "|".join(row["roles"])})
