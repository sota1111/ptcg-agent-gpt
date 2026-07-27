import json
from pathlib import Path

from ptcg_agent.deck_preselection import load_cards, load_deck, validate_deck
from ptcg_agent.meta_deck_candidates import (
    DeckTemplate,
    MetaEntry,
    MetaSnapshot,
    analyze_meta,
    composition_similarity,
    load_meta_snapshots,
    select_candidates,
    write_selected_decks,
)


def _snapshots() -> list[MetaSnapshot]:
    return [
        MetaSnapshot(
            "2026-07-01",
            (
                MetaEntry("alpha", 18, 0.04, 0.08),
                MetaEntry("beta", 8, 0.08, 0.13),
                MetaEntry("niche", 70, 0.02, 0.03),
            ),
        ),
        MetaSnapshot(
            "2026-07-08",
            (
                MetaEntry("alpha", 10, 0.07, 0.12),
                MetaEntry("beta", 12, 0.06, 0.10),
                MetaEntry("niche", 66, 0.02, 0.03),
            ),
        ),
        MetaSnapshot(
            "2026-07-15",
            (
                MetaEntry("alpha", 4, 0.11, 0.18),
                MetaEntry("beta", 19, 0.04, 0.07),
                MetaEntry("niche", 61, 0.02, 0.03),
            ),
        ),
    ]


def _deck(primary: int, secondary: int) -> tuple[int, ...]:
    return tuple(sorted([1] * 40 + [primary] * 4 + [secondary] * 4 + [3] * 4 + [4] * 4 + [5] * 4))


def _write_card_data(directory: Path) -> Path:
    path = directory / "cards.csv"
    rows = [
        "Card ID,Card Name,Expansion,Collection No.,"
        "Stage (Pokémon)/Type (Energy and Trainer),Rule,Category,Previous stage,"
        "HP,Type,Weakness,Resistance (Type),Retreat,Move Name,Cost,Damage,"
        "Effect Explanation",
        "1,Basic Energy,SVE,1,Basic Energy,n/a,n/a,n/a,n/a,{W},,,n/a,,n/a,n/a,",
        "2,Alpha,TEST,1,Basic Pokémon,n/a,n/a,n/a,60,{G},,,1,Tackle,{C},10,",
        "3,Research,TEST,2,Supporter,n/a,n/a,n/a,n/a,n/a,,,n/a,,n/a,n/a,Draw cards",
        "4,Ball,TEST,3,Item,n/a,n/a,n/a,n/a,n/a,,,n/a,,n/a,n/a,Search your deck",
        "5,Switch,TEST,4,Item,n/a,n/a,n/a,n/a,n/a,,,n/a,,n/a,n/a,Switch",
        "6,Beta,TEST,5,Basic Pokémon,n/a,n/a,n/a,60,{W},,,1,Splash,{W},10,",
        "7,Gamma,TEST,6,Basic Pokémon,n/a,n/a,n/a,60,{R},,,1,Heat,{R},10,",
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_meta_analysis_is_deterministic_and_uses_all_signals(tmp_path: Path) -> None:
    source = tmp_path / "meta.json"
    source.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "date": snapshot.date,
                        "entries": [
                            {
                                "archetype": entry.archetype,
                                "rank": entry.rank,
                                "usage": entry.usage,
                                "concentration": entry.concentration,
                            }
                            for entry in snapshot.entries
                        ],
                    }
                    for snapshot in reversed(_snapshots())
                ]
            }
        )
    )
    snapshots = load_meta_snapshots(source)
    first = analyze_meta(snapshots)
    second = analyze_meta(snapshots)
    assert first == second
    assert first["alpha"]["rank"] == 4
    assert first["alpha"]["trend"] == 0.07
    assert first["alpha"]["persistence"] == 1.0
    assert first["alpha"]["concentration"] == 0.18
    assert first["alpha"]["top10"] == 2
    assert first["alpha"]["top20"] == 3
    assert first["alpha"]["top100"] == 3
    assert first["alpha"]["score"] > first["beta"]["score"]


def test_selection_records_reasons_legality_and_duplicates(tmp_path: Path) -> None:
    cards_path = _write_card_data(tmp_path)
    cards = load_cards(cards_path)
    baseline = DeckTemplate("baseline", _deck(2, 6), roles=("baseline",))
    alpha = DeckTemplate("alpha", _deck(2, 7), source="local alpha template")
    exact = DeckTemplate("exact-baseline", baseline.cards)
    near = DeckTemplate("alpha-near", tuple(sorted((*alpha.cards[:-1], 6))))
    niche = DeckTemplate("niche", _deck(6, 7), roles=("diversity",))
    illegal = DeckTemplate("broken", tuple([999] * 60), roles=("counter",))
    result = select_candidates(
        snapshots=_snapshots(),
        templates=[alpha, exact, near, niche, illegal],
        existing=[baseline],
        cards=cards,
        max_additions=3,
    )
    assert result == select_candidates(
        snapshots=_snapshots(),
        templates=[alpha, exact, near, niche, illegal],
        existing=[baseline],
        cards=cards,
        max_additions=3,
    )
    by_archetype = {row["archetype"]: row for row in result["decisions"]}
    assert by_archetype["alpha"]["decision"] == "add"
    assert {"top", "emerging"} <= set(by_archetype["alpha"]["roles"])
    assert by_archetype["baseline"]["decision"] == "keep"
    assert by_archetype["exact-baseline"]["duplicate"]["exact"]
    assert by_archetype["exact-baseline"]["decision"] == "remove"
    assert by_archetype["alpha-near"]["duplicate"]["near"]
    assert by_archetype["alpha-near"]["decision"] == "remove"
    assert by_archetype["broken"]["legal"] is False
    assert by_archetype["broken"]["decision"] == "remove"
    assert all(row["reasons"] for row in result["decisions"])
    assert "low usage alone" in by_archetype["baseline"]["reasons"][0]

    output = tmp_path / "decks"
    paths = write_selected_decks(result, output)
    assert paths
    assert all(validate_deck(load_deck(path), cards) == [] for path in paths)


def test_similarity_detects_exact_and_near_identical_compositions() -> None:
    original = _deck(2, 6)
    near = tuple(sorted((*original[:-2], 7, 7)))
    assert composition_similarity(original, original) == 1.0
    assert composition_similarity(original, near) >= 0.9
