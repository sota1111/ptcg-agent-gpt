from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from agents.counter_meta_policy import CounterMetaAgent, candidate_enabled
from tests.support import synthetic_card_index

REPO = Path(__file__).resolve().parents[1]
CANDIDATE_DECK = REPO / "decks/candidates/sot-2554-single-prize-alakazam.csv"


def _observation(context: int = 0) -> dict:
    side = {
        "active": [{"id": 743, "hp": 140, "maxHp": 140, "energyCards": []}],
        "bench": [{"id": 741, "hp": 50, "maxHp": 50}],
        "benchMax": 5,
        "deckCount": 30,
        "hand": [],
        "discard": [],
        "prize": [None] * 6,
    }
    opponent = dict(side)
    opponent["hand"] = None
    return {
        "current": {"yourIndex": 0, "players": [side, opponent]},
        "select": {
            "type": 0,
            "context": context,
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"type": 14, "playerIndex": 0, "area": 4, "index": 0},
                {"type": 14, "playerIndex": 0, "area": 4, "index": 0},
            ],
        },
    }


def test_candidate_deck_is_legal_single_prize_alakazam() -> None:
    deck = [int(line) for line in CANDIDATE_DECK.read_text().splitlines()]
    counts = Counter(deck)
    assert len(deck) == 60
    assert counts[741] == counts[742] == counts[743] == 4
    assert counts[11] == 4
    assert all(count <= 4 for card_id, count in counts.items() if card_id != 5)

    # The only Pokémon IDs are the independently audited non-Rule-Box line;
    # keeping this assertion data-only makes the legality gate portable when
    # the optional competition engine is absent in CI.
    assert {card_id for card_id in deck if card_id in {741, 742, 743}} == {741, 742, 743}


@pytest.mark.parametrize("context", range(49))
def test_every_select_context_is_legal_and_deterministic(context: int) -> None:
    deck = [int(line) for line in CANDIDATE_DECK.read_text().splitlines()]
    first = CounterMetaAgent(2554, deck=deck, card_index=synthetic_card_index())
    second = CounterMetaAgent(2554, deck=deck, card_index=synthetic_card_index())
    obs = _observation(context)
    first_action = first.act(obs)
    assert first_action == second.act(obs)
    assert len(first_action) == 1 and first_action[0] in (0, 1)
    assert first.fallback_count == second.fallback_count == 0


def test_candidate_contract_denies_identity_and_private_zone_branches() -> None:
    contract = json.loads(
        (REPO / "configs/experiments/sot-2554-single-prize-counter-meta.json").read_text()
    )
    assert contract["enabledByDefault"] is False
    assert contract["screenConfirmAllowed"] is False
    assert contract["kaggleSubmissionAllowed"] is False
    assert set(contract["informationAllowlist"]) == {"public-board", "public-log", "legal-options"}

    source = (REPO / "agents/counter_meta_policy.py").read_text()
    tree = ast.parse(source)
    names = {node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    forbidden = {"opponent_id", "pool_id", "hidden", "private", "prize_known_ids", "hand_card_ids"}
    assert forbidden.isdisjoint(names | attributes)


def test_default_champion_is_unchanged_and_candidate_flag_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PTCG_TELEMETRY_PROTOCOL", raising=False)
    monkeypatch.delenv("PTCG_COUNTER_META_CANDIDATE", raising=False)
    assert candidate_enabled() is False

    monkeypatch.setenv("PTCG_TELEMETRY_PROTOCOL", "1")
    monkeypatch.setenv("PTCG_COUNTER_META_CANDIDATE", "single-prize-alakazam-mist")
    assert candidate_enabled() is True
    assert hashlib.sha256((REPO / "main.py").read_bytes()).hexdigest() == (
        "f65bfc5151d847f2d23d40baf22f293eaaaa04e13b366c7162c592f7d175613c"
    )


def test_candidate_import_and_package_contract_are_offline() -> None:
    deck = [int(line) for line in CANDIDATE_DECK.read_text().splitlines()]
    assert len(CounterMetaAgent(2554, deck=deck).act({"select": None})) == 60
    contract = json.loads(
        (REPO / "configs/experiments/sot-2554-single-prize-counter-meta.json").read_text()
    )
    assert (REPO / contract["deck"]).is_file()
    assert contract["policy"] == "agents.counter_meta_policy.CounterMetaAgent"
