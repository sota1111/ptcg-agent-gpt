"""Explainable, deterministic selection of legal meta deck candidates.

The module deliberately consumes aggregated archetype statistics and locally-authored
deck templates.  It never reconstructs a competitor's private list from replays.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ptcg_agent.deck_preselection import Card, deck_hash, validate_deck

Role = Literal["top", "counter", "emerging", "low_usage_top", "baseline", "diversity"]
Decision = Literal["add", "keep", "remove"]


@dataclass(frozen=True)
class OneChange:
    """A single, explainable card replacement relative to the champion deck."""

    candidate_id: str
    remove_card_id: int
    add_card_id: int
    role: str
    rationale: str


@dataclass(frozen=True)
class MetaEntry:
    archetype: str
    rank: int
    usage: float
    concentration: float


@dataclass(frozen=True)
class MetaSnapshot:
    date: str
    entries: tuple[MetaEntry, ...]


@dataclass(frozen=True)
class DeckTemplate:
    archetype: str
    cards: tuple[int, ...]
    roles: tuple[Role, ...] = ()
    counters: tuple[str, ...] = ()
    source: str = "repository template"


def sha256_file(path: Path) -> str:
    """Return a stable provenance fingerprint for an input file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_one_change_candidates(
    *, champion: tuple[int, ...], changes: Iterable[OneChange], cards: dict[int, Card]
) -> dict[str, Any]:
    """Generate deterministic, legal, composition-distinct one-change candidates."""
    champion_errors = validate_deck(champion, cards)
    if champion_errors:
        raise ValueError("champion is illegal: " + "; ".join(champion_errors))
    champion_hash = deck_hash(champion)
    seen_hashes = {champion_hash}
    candidates: list[dict[str, Any]] = []
    for change in sorted(changes, key=lambda item: item.candidate_id):
        if change.remove_card_id not in champion:
            raise ValueError(
                f"{change.candidate_id}: remove card {change.remove_card_id} is absent"
            )
        candidate = list(champion)
        candidate.remove(change.remove_card_id)
        candidate.append(change.add_card_id)
        candidate_cards = tuple(sorted(candidate))
        errors = validate_deck(candidate_cards, cards)
        candidate_hash = deck_hash(candidate_cards)
        if candidate_hash in seen_hashes:
            raise ValueError(f"{change.candidate_id}: duplicate composition")
        seen_hashes.add(candidate_hash)
        candidates.append(
            {
                "id": change.candidate_id,
                "cards": list(candidate_cards),
                "composition_sha256": candidate_hash,
                "one_change": {
                    "remove": {
                        "card_id": change.remove_card_id,
                        "name": cards[change.remove_card_id].name,
                    },
                    "add": {
                        "card_id": change.add_card_id,
                        "name": cards[change.add_card_id].name,
                    },
                },
                "role": change.role,
                "rationale": change.rationale,
                "card_count": len(candidate_cards),
                "legal": not errors,
                "loadable": True,
                "errors": errors,
            }
        )
    if not 2 <= len(candidates) <= 3:
        raise ValueError("exactly two or three candidates are required")
    return {
        "schema_version": 1,
        "champion_composition_sha256": champion_hash,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def load_meta_snapshots(path: Path) -> list[MetaSnapshot]:
    """Load normalized public meta snapshots from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    snapshots: list[MetaSnapshot] = []
    for item in raw["snapshots"]:
        entries = tuple(
            MetaEntry(
                archetype=str(row["archetype"]),
                rank=int(row["rank"]),
                usage=float(row["usage"]),
                concentration=float(row.get("concentration", row["usage"])),
            )
            for row in item["entries"]
        )
        snapshots.append(MetaSnapshot(date=str(item["date"]), entries=entries))
    if len(snapshots) < 3:
        raise ValueError("at least three meta snapshots are required")
    invalid = (
        entry.rank < 1 or entry.usage < 0 or entry.concentration < 0
        for snapshot in snapshots
        for entry in snapshot.entries
    )
    if any(invalid):
        raise ValueError("rank must be positive and usage/concentration non-negative")
    return sorted(snapshots, key=lambda snapshot: snapshot.date)


def analyze_meta(snapshots: list[MetaSnapshot]) -> dict[str, dict[str, Any]]:
    """Score rank, usage, concentration, trend, and persistence separately."""
    if len(snapshots) < 3:
        raise ValueError("at least three meta snapshots are required")
    names = sorted({entry.archetype for snapshot in snapshots for entry in snapshot.entries})
    analysis: dict[str, dict[str, Any]] = {}
    for name in names:
        history = [
            next((entry for entry in snapshot.entries if entry.archetype == name), None)
            for snapshot in snapshots
        ]
        present = [entry for entry in history if entry is not None]
        latest = history[-1]
        latest_rank = latest.rank if latest is not None else 101
        latest_usage = latest.usage if latest is not None else 0.0
        latest_concentration = latest.concentration if latest is not None else 0.0
        first_usage = next((entry.usage for entry in history if entry is not None), 0.0)
        trend = latest_usage - first_usage
        persistence = len(present) / len(snapshots)
        rank_signal = max(0.0, 1.0 - (latest_rank - 1) / 100)
        usage_signal = min(1.0, latest_usage / 0.20)
        concentration_signal = min(1.0, latest_concentration / 0.25)
        trend_signal = max(0.0, min(1.0, 0.5 + trend / 0.10))
        score = (
            rank_signal * 0.30
            + usage_signal * 0.20
            + concentration_signal * 0.15
            + trend_signal * 0.15
            + persistence * 0.20
        )
        analysis[name] = {
            "rank": latest_rank,
            "usage": round(latest_usage, 6),
            "concentration": round(latest_concentration, 6),
            "trend": round(trend, 6),
            "persistence": round(persistence, 6),
            "top10": sum(entry.rank <= 10 for entry in present),
            "top20": sum(entry.rank <= 20 for entry in present),
            "top100": sum(entry.rank <= 100 for entry in present),
            "score": round(score, 6),
        }
    return analysis


def composition_similarity(left: Iterable[int], right: Iterable[int]) -> float:
    """Multiset Jaccard similarity; 1.0 is an exact duplicate."""
    left_counts, right_counts = Counter(left), Counter(right)
    union = sum((left_counts | right_counts).values())
    return sum((left_counts & right_counts).values()) / union if union else 1.0


def select_candidates(
    *,
    snapshots: list[MetaSnapshot],
    templates: list[DeckTemplate],
    existing: list[DeckTemplate],
    cards: dict[int, Card],
    max_additions: int = 6,
    max_per_archetype: int = 2,
    near_duplicate_threshold: float = 0.90,
) -> dict[str, Any]:
    """Return legal add/keep/remove decisions with stable reasons and duplicate data."""
    if max_additions < 1 or max_per_archetype < 1:
        raise ValueError("selection limits must be positive")
    meta = analyze_meta(snapshots)
    existing_hashes = {deck_hash(item.cards) for item in existing}
    ranked = sorted(
        templates,
        key=lambda item: (
            -float(meta.get(item.archetype, {}).get("score", 0.0)),
            item.archetype,
            deck_hash(item.cards),
        ),
    )
    decisions: list[dict[str, Any]] = []
    selected: list[DeckTemplate] = list(existing)
    archetype_counts = Counter(item.archetype for item in existing)
    additions = 0
    for template in ranked:
        errors = validate_deck(template.cards, cards)
        exact = deck_hash(template.cards) in {deck_hash(item.cards) for item in selected}
        closest = max(
            ((composition_similarity(template.cards, item.cards), item) for item in selected),
            default=(0.0, template),
            key=lambda pair: pair[0],
        )
        is_near = not exact and closest[0] >= near_duplicate_threshold
        signals = meta.get(template.archetype, _empty_signals())
        roles = _roles(template, signals)
        reasons = _reasons(signals, roles)
        if errors:
            decision: Decision = "remove"
            reasons = ["illegal local template: " + "; ".join(errors)]
        elif exact:
            decision = "remove"
            reasons = ["exact composition already retained; duplicate candidate omitted", *reasons]
        elif is_near:
            decision = "remove"
            reasons = [f"near-duplicate composition ({closest[0]:.3f})", *reasons]
        elif additions >= max_additions:
            decision = "remove"
            reasons = ["bounded replacement limit reached", *reasons]
        elif archetype_counts[template.archetype] >= max_per_archetype:
            decision = "remove"
            reasons = ["archetype concentration limit reached", *reasons]
        elif roles:
            decision = "add"
            additions += 1
            selected.append(template)
            archetype_counts[template.archetype] += 1
        else:
            decision = "remove"
            reasons = [
                "insufficient combined rank, trend, persistence, or strategic coverage",
                *reasons,
            ]
        decisions.append(
            {
                "archetype": template.archetype,
                "hash": deck_hash(template.cards),
                "decision": decision,
                "roles": roles,
                "reasons": reasons,
                "legal": not errors,
                "duplicate": {"exact": exact, "near": is_near, "similarity": round(closest[0], 6)},
                "signals": signals,
                "source": template.source,
                "cards": list(template.cards),
            }
        )
    # Existing lists are never removed merely because their usage is low.
    for item in existing:
        if any(
            row["archetype"] == item.archetype and row["hash"] == deck_hash(item.cards)
            for row in decisions
        ):
            continue
        signals = meta.get(item.archetype, _empty_signals())
        decisions.append(
            {
                "archetype": item.archetype,
                "hash": deck_hash(item.cards),
                "decision": "keep",
                "roles": _roles(item, signals) or ["baseline"],
                "reasons": ["existing baseline retained; low usage alone is not a removal reason"],
                "legal": not validate_deck(item.cards, cards),
                "duplicate": {"exact": True, "near": False, "similarity": 1.0},
                "signals": signals,
                "source": item.source,
                "cards": list(item.cards),
            }
        )
    decisions.sort(key=lambda row: (str(row["decision"]), str(row["archetype"]), str(row["hash"])))
    return {
        "schemaVersion": "1.0.0",
        "snapshotDates": [snapshot.date for snapshot in snapshots],
        "limits": {
            "maxAdditions": max_additions,
            "maxPerArchetype": max_per_archetype,
            "nearDuplicateThreshold": near_duplicate_threshold,
        },
        "existingCount": len(existing),
        "selectedCount": sum(row["decision"] in {"add", "keep"} for row in decisions),
        "decisions": decisions,
        "inputHashes": sorted(existing_hashes),
    }


def write_selected_decks(result: dict[str, Any], directory: Path) -> list[Path]:
    """Write selected legal candidates as loadable one-card-id-per-row CSV files."""
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    selected = (
        item
        for item in result["decisions"]
        if item["decision"] in {"add", "keep"} and item["legal"]
    )
    for index, row in enumerate(
        selected,
        start=1,
    ):
        safe_name = "".join(
            char if char.isalnum() else "-" for char in str(row["archetype"])
        ).strip("-")
        path = directory / f"{index:02d}-{safe_name.lower()}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerows((card_id,) for card_id in row["cards"])
        written.append(path)
    return written


def _roles(template: DeckTemplate, signals: dict[str, Any]) -> list[Role]:
    roles = set(template.roles)
    if signals["rank"] <= 20 or signals["top20"] >= 2:
        roles.add("top")
    if signals["trend"] >= 0.02:
        roles.add("emerging")
    if signals["rank"] <= 100 and signals["usage"] <= 0.03 and signals["persistence"] >= 2 / 3:
        roles.add("low_usage_top")
    if template.counters:
        roles.add("counter")
    return sorted(roles)


def _reasons(signals: dict[str, Any], roles: list[Role]) -> list[str]:
    return [
        (
            f"meta score {signals['score']:.3f}: rank {signals['rank']}, "
            f"usage {signals['usage']:.3f}, concentration {signals['concentration']:.3f}, "
            f"trend {signals['trend']:+.3f}, persistence {signals['persistence']:.3f}"
        ),
        "coverage: " + ", ".join(roles) if roles else "coverage: none",
    ]


def _empty_signals() -> dict[str, Any]:
    return {
        "rank": 101,
        "usage": 0.0,
        "concentration": 0.0,
        "trend": 0.0,
        "persistence": 0.0,
        "top10": 0,
        "top20": 0,
        "top100": 0,
        "score": 0.0,
    }
