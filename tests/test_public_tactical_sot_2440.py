from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from agents.cards import CardIndex
from agents.observation import adapt
from agents.planner import MctsPlanner, PlannerConfig
from agents.tactical_controller import PublicTacticalAgent
from scripts.evaluate_public_tactical_sot_2440 import evaluation_manifest


def _card(card_id, *, energy_type=0, weakness=None, attacks=(), retreat=1, ex=False):
    return SimpleNamespace(
        cardId=card_id,
        cardType=0,
        hp=120,
        retreatCost=retreat,
        weakness=weakness,
        resistance=None,
        energyType=energy_type,
        basic=True,
        stage1=False,
        stage2=False,
        ex=ex,
        megaEx=False,
        tera=False,
        aceSpec=False,
        attacks=attacks,
        skills=(),
    )


def _view(hidden_marker="a"):
    def pokemon(card, hp, energies=()):
        return {
            "id": card,
            "hp": hp,
            "maxHp": 120,
            "energies": list(energies),
            "energyCards": [],
            "tools": [],
            "preEvolution": [],
        }

    raw = {
        "select": {
            "type": 0,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"type": 13, "attackId": 10},
                {"type": 13, "attackId": 11},
            ],
        },
        "current": {
            "yourIndex": 0,
            "turn": 5,
            "players": [
                {"active": [pokemon(1, 120, (0,))], "bench": [], "hand": [], "prize": [None] * 3},
                {
                    "active": [pokemon(2, 70)],
                    "bench": [],
                    "handCount": 5,
                    "deckCount": 30,
                    "prize": [None] * 2,
                    "hiddenTestMarker": hidden_marker,
                },
            ],
            "evaluationSeed": hidden_marker,
            "opponentIdentity": hidden_marker,
        },
    }
    return adapt(raw)


def test_tactical_attack_plan_prefers_public_ko_and_prize_value():
    cards = CardIndex(
        [_card(1, energy_type=0, attacks=(10, 11)), _card(2, weakness=0, ex=True)],
        [
            SimpleNamespace(attackId=10, damage=40, energies=(0,)),
            SimpleNamespace(attackId=11, damage=20, energies=(0,)),
        ],
    )
    agent = PublicTacticalAgent(seed=1, card_index=cards)
    scores = agent.score_options(_view())
    assert scores[0] > scores[1]


def test_tactical_scores_ignore_hidden_identity_pool_seed_and_seat_proxy():
    cards = CardIndex(
        [_card(1, energy_type=0, attacks=(10, 11)), _card(2, weakness=0, ex=True)],
        [
            SimpleNamespace(attackId=10, damage=40, energies=(0,)),
            SimpleNamespace(attackId=11, damage=20, energies=(0,)),
        ],
    )
    agent = PublicTacticalAgent(seed=1, card_index=cards)
    assert agent.score_options(_view("private-a")) == agent.score_options(_view("private-b"))


def test_feature_flag_changes_only_planner_root_scorer(monkeypatch):
    monkeypatch.delenv("PTCG_TELEMETRY_PROTOCOL", raising=False)
    monkeypatch.setenv("PTCG_PUBLIC_TACTICAL_CANDIDATE", "1")
    assert PlannerConfig().public_tactical_controller is False
    monkeypatch.setenv("PTCG_TELEMETRY_PROTOCOL", "1")
    config = PlannerConfig()
    assert config.public_tactical_controller is True
    planner = MctsPlanner([1] * 60, config=config, card_index=CardIndex())
    assert isinstance(planner._greedy, PublicTacticalAgent)
    champion = replace(config, public_tactical_controller=False)
    assert champion.n_worlds == config.n_worlds
    assert champion.time_budget_s == config.time_budget_s


def test_evaluation_inherits_frozen_six_opponent_screen_confirm_contract():
    manifest = evaluation_manifest(Path("eval/manifests/sot-2439-public-tactical-contract.json"))
    assert [row["id"] for row in manifest["opponents"]] == [
        "matsu",
        "take",
        "ume",
        "claude",
        "obo",
        "meta-proxy",
    ]
    assert manifest["phases"]["screen"] == {
        "baseSeed": 2439101,
        "seedsPerOpponent": 2,
        "seatReversal": True,
    }
    assert manifest["phases"]["confirm"]["baseSeed"] == 2439201
    assert manifest["kaggleSubmissionAllowed"] is False
