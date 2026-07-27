"""Regenerate checked-in meta analysis and current deck inventory."""

from pathlib import Path

from ptcg_agent.deck_preselection import load_cards
from ptcg_agent.meta_inventory import (
    DeckSpec,
    analyze_snapshot_document,
    inventory_decks,
    load_snapshot_document,
    write_inventory_csv,
    write_json,
)

ROOT = Path(__file__).parents[1]


def main() -> None:
    document = load_snapshot_document(ROOT / "data/meta/snapshots.json")
    analysis = analyze_snapshot_document(document)
    cards = load_cards(ROOT / "data/EN_Card_Data.csv")
    inventory = inventory_decks(
        [
            DeckSpec(
                "submission",
                ROOT / "deck.csv",
                "Miraidon ex",
                "competition submission",
                "measured baseline",
                "top",
            ),
            DeckSpec(
                "hash-baseline",
                ROOT / "eval/hash_baseline/deck.csv",
                "Miraidon ex",
                "deterministic regression opponent",
                "hash baseline",
                "baseline",
            ),
        ],
        cards,
    )
    write_json(analysis, ROOT / "artifacts/meta-analysis.json")
    write_inventory_csv(inventory, ROOT / "docs/deck-inventory.csv")


if __name__ == "__main__":
    main()
