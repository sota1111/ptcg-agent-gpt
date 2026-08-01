import json
from pathlib import Path

from agents.planner import MctsPlanner, PlannerConfig

MANIFEST = Path("eval/manifests/sot-2255-selective-lookahead-promotion.json")


class Option:
    def __init__(self, option_type: int):
        self.type = option_type


class Select:
    def __init__(self, *types: int):
        self.option = [Option(value) for value in types]


class Obs:
    def __init__(self, *types: int):
        self.select = Select(*types)


def test_manifest_preregisters_one_change_and_independent_seeds() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["screen"]["base_seed"] != manifest["confirm"]["base_seed"]
    assert manifest["screen"]["seat_reversal"] is True
    assert len(manifest["candidates"]) == 1
    assert manifest["privacy"]["hidden_zone_features"] is False
    assert manifest["privacy"]["opponent_identity_branching"] is False


def test_candidate_defaults_off_and_recognizes_setup_only_actions() -> None:
    assert PlannerConfig().selective_setup_lookahead is False
    assert MctsPlanner._is_setup_action(Obs(7, 8, 14), [0]) is True
    assert MctsPlanner._is_setup_action(Obs(7, 8, 14), [2]) is False
    assert MctsPlanner._is_setup_action(Obs(7, 13), [0, 1]) is False
    assert MctsPlanner._is_setup_action(Obs(7), []) is False
