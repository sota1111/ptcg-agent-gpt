"""Reproducible public-meta snapshots and repository deck inventory."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ptcg_agent.deck_preselection import Card, deck_hash, load_deck, validate_deck


@dataclass(frozen=True)
class DeckSpec:
    deck_id: str
    path: Path
    primary_archetype: str
    purpose: str
    evaluation: str
    role: str


def load_snapshot_document(path: Path) -> dict[str, Any]:
    """Load and validate a normalized, provenance-bearing snapshot document."""
    document = json.loads(path.read_text(encoding="utf-8"))
    snapshots = document.get("snapshots")
    if not isinstance(snapshots, list) or len(snapshots) < 3:
        raise ValueError("at least three meta snapshots are required")
    required_metadata = ("capturedAt", "sourceUrl", "targetDate", "deckCountBeforeUpdate")
    normalized: list[dict[str, Any]] = []
    for snapshot in snapshots:
        missing = [key for key in required_metadata if key not in snapshot]
        if missing:
            raise ValueError("snapshot metadata missing: " + ", ".join(missing))
        signals = snapshot.get("signals")
        if not isinstance(signals, dict) or set(signals) != {"top10", "top20", "top100"}:
            raise ValueError("signals must contain separate top10, top20, and top100 lists")
        normalized_signals: dict[str, list[dict[str, Any]]] = {}
        for signal, limit in (("top10", 10), ("top20", 20), ("top100", 100)):
            rows = signals[signal]
            if not isinstance(rows, list):
                raise ValueError(f"{signal} must be a list")
            normalized_rows: list[dict[str, Any]] = [
                {
                    "archetype": str(row["archetype"]),
                    "rank": int(row["rank"]),
                    "usage": round(float(row["usage"]), 6),
                }
                for row in rows
            ]
            if any(
                row["rank"] < 1 or row["rank"] > limit or row["usage"] < 0
                for row in normalized_rows
            ):
                raise ValueError(f"{signal} contains an invalid rank or usage")
            normalized_signals[signal] = sorted(
                normalized_rows, key=lambda row: (row["rank"], row["archetype"])
            )
        normalized.append(
            {
                "capturedAt": str(snapshot["capturedAt"]),
                "sourceUrl": str(snapshot["sourceUrl"]),
                "targetDate": str(snapshot["targetDate"]),
                "deckCountBeforeUpdate": int(snapshot["deckCountBeforeUpdate"]),
                "signals": normalized_signals,
            }
        )
    return {
        "schemaVersion": str(document.get("schemaVersion", "1.0.0")),
        "snapshots": sorted(normalized, key=lambda row: row["targetDate"]),
    }


def analyze_snapshot_document(document: dict[str, Any]) -> dict[str, Any]:
    """Analyze each cutoff independently and retain complete per-snapshot history."""
    snapshots = document["snapshots"]
    if len(snapshots) < 3:
        raise ValueError("at least three meta snapshots are required")
    signals: dict[str, dict[str, Any]] = {}
    for signal in ("top10", "top20", "top100"):
        archetypes = sorted(
            {row["archetype"] for snapshot in snapshots for row in snapshot["signals"][signal]}
        )
        entries: dict[str, Any] = {}
        for archetype in archetypes:
            history = []
            for snapshot in snapshots:
                match = next(
                    (row for row in snapshot["signals"][signal] if row["archetype"] == archetype),
                    None,
                )
                history.append(
                    {
                        "targetDate": snapshot["targetDate"],
                        "rank": match["rank"] if match else None,
                        "usage": match["usage"] if match else 0.0,
                    }
                )
            present = [row for row in history if row["rank"] is not None]
            first_usage = present[0]["usage"] if present else 0.0
            latest_usage = history[-1]["usage"]
            entries[archetype] = {
                "history": history,
                "latestRank": history[-1]["rank"],
                "latestUsage": latest_usage,
                "usageChange": round(latest_usage - first_usage, 6),
                "rankChange": (present[0]["rank"] - present[-1]["rank"] if present else 0),
                "persistence": round(len(present) / len(snapshots), 6),
            }
        signals[signal] = {"archetypes": entries}

    top100 = signals["top100"]["archetypes"]
    low_usage_top = sorted(
        (
            {
                "archetype": archetype,
                "rank": row["latestRank"],
                "usage": row["latestUsage"],
                "persistence": row["persistence"],
            }
            for archetype, row in top100.items()
            if row["latestRank"] is not None and row["latestUsage"] <= 0.03
        ),
        key=lambda row: (row["rank"], row["archetype"]),
    )
    return {
        "schemaVersion": "1.0.0",
        "snapshotCount": len(snapshots),
        "provenance": [
            {
                key: snapshot[key]
                for key in ("capturedAt", "sourceUrl", "targetDate", "deckCountBeforeUpdate")
            }
            for snapshot in snapshots
        ],
        "signals": signals,
        "lowUsageTop100": low_usage_top,
    }


def inventory_decks(specs: list[DeckSpec], cards: dict[int, Card]) -> list[dict[str, Any]]:
    """Record loadability, legality, hashes, and exact duplicate groups for every deck."""
    rows: list[dict[str, Any]] = []
    hashes: dict[str, list[str]] = defaultdict(list)
    for spec in specs:
        try:
            recorded_path = spec.path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            recorded_path = spec.path.as_posix()
        try:
            deck = load_deck(spec.path)
            composition_hash = deck_hash(deck)
            errors = validate_deck(deck, cards)
            loadable = True
        except (OSError, UnicodeError, ValueError) as error:
            deck = ()
            composition_hash = ""
            errors = [str(error)]
            loadable = False
        if composition_hash:
            hashes[composition_hash].append(spec.deck_id)
        rows.append(
            {
                "deckId": spec.deck_id,
                "path": recorded_path,
                "primaryArchetype": spec.primary_archetype,
                "compositionHash": composition_hash,
                "purpose": spec.purpose,
                "evaluation": spec.evaluation,
                "role": spec.role,
                "cardCount": len(deck),
                "legal": loadable and not errors,
                "loadable": loadable,
                "errors": errors,
            }
        )
    for row in rows:
        duplicate_ids = [
            deck_id
            for deck_id in hashes.get(str(row["compositionHash"]), [])
            if deck_id != row["deckId"]
        ]
        row["duplicate"] = bool(duplicate_ids)
        row["duplicateOf"] = duplicate_ids
    return sorted(rows, key=lambda row: row["deckId"])


def write_inventory_csv(rows: list[dict[str, Any]], path: Path) -> None:
    """Write the stable, human-reviewable inventory artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "deckId",
        "path",
        "primaryArchetype",
        "compositionHash",
        "purpose",
        "evaluation",
        "role",
        "cardCount",
        "duplicate",
        "duplicateOf",
        "legal",
        "loadable",
        "errors",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "duplicateOf": "|".join(row["duplicateOf"]),
                    "errors": "|".join(row["errors"]),
                }
            )


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
