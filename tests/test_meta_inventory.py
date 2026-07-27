import csv
import json
from pathlib import Path

import pytest

from ptcg_agent.deck_preselection import Card
from ptcg_agent.meta_inventory import (
    DeckSpec,
    analyze_snapshot_document,
    inventory_decks,
    load_snapshot_document,
    write_inventory_csv,
)

ROOT = Path(__file__).parents[1]


def test_fixture_preserves_independent_signals_and_is_deterministic() -> None:
    document = load_snapshot_document(ROOT / "data/meta/snapshots.json")
    first = analyze_snapshot_document(document)
    second = analyze_snapshot_document(document)

    assert first == second
    assert first["snapshotCount"] == 3
    assert set(first["signals"]) == {"top10", "top20", "top100"}
    dragapult = first["signals"]["top100"]["archetypes"]["Dragapult ex"]
    assert len(dragapult["history"]) == 3
    assert dragapult["rankChange"] == 3
    assert dragapult["usageChange"] == 0.02
    assert dragapult["persistence"] == 1.0
    assert first["lowUsageTop100"] == [
        {"archetype": "Festival Lead", "rank": 54, "usage": 0.021, "persistence": 1.0}
    ]
    assert all(
        set(row) == {"capturedAt", "sourceUrl", "targetDate", "deckCountBeforeUpdate"}
        for row in first["provenance"]
    )


def test_snapshot_requires_three_complete_provenance_records(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"snapshots": [{}, {}, {}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata missing"):
        load_snapshot_document(path)


def test_all_current_decks_are_inventoried_and_duplicates_detected(tmp_path: Path) -> None:
    deck_ids = {int(row) for row in (ROOT / "deck.csv").read_text().splitlines()}
    cards = {
        card_id: Card(
            card_id,
            f"fixture-{card_id}",
            "fixture",
            "Basic Energy" if card_id == 3 else "Basic Pokémon" if card_id == 721 else "Item",
            "Basic Energy" if card_id == 3 else "Basic Pokémon" if card_id == 721 else "Item",
            "",
            "",
            "",
        )
        for card_id in deck_ids
    }
    specs = [
        DeckSpec("submission", ROOT / "deck.csv", "Miraidon ex", "submission", "baseline", "top"),
        DeckSpec(
            "hash-baseline",
            ROOT / "eval/hash_baseline/deck.csv",
            "Miraidon ex",
            "regression opponent",
            "baseline",
            "baseline",
        ),
    ]
    rows = inventory_decks(specs, cards)
    assert len(rows) == 2
    assert all(row["loadable"] and row["legal"] for row in rows)
    assert all(row["cardCount"] == 60 for row in rows)
    assert all(row["compositionHash"] for row in rows)
    assert all(row["duplicate"] for row in rows)

    output = tmp_path / "inventory.csv"
    write_inventory_csv(rows, output)
    written = list(csv.DictReader(output.open(encoding="utf-8")))
    assert {row["deckId"] for row in written} == {"submission", "hash-baseline"}
