import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.evaluator import HeuristicEvaluator, PublicValueEvaluator
from ptcg_agent.runtime_dataset import PUBLIC_FEATURE_ALLOWLIST

SPEC = importlib.util.spec_from_file_location(
    "decide_public_value_model", Path("scripts/decide_public_value_model.py")
)
assert SPEC and SPEC.loader
DECISION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DECISION)


def player(*, hand: int, deck: int, prizes: int, hidden: object = None) -> SimpleNamespace:
    return SimpleNamespace(
        handCount=hand,
        deckCount=deck,
        prize=[None] * prizes,
        active=[],
        bench=[],
        hidden=hidden,
    )


def observation(hidden: object = None) -> SimpleNamespace:
    return SimpleNamespace(
        current=SimpleNamespace(
            result=-1,
            turn=7,
            players=[
                player(hand=5, deck=31, prizes=3, hidden=hidden),
                player(hand=8, deck=28, prizes=4),
            ],
        )
    )


def summary(win_rate: float = 0.5) -> dict:
    return {
        "winRate": win_rate,
        "seatWinRate": {"0": win_rate, "1": win_rate},
        "matchups": {"matsu": {"winRate": win_rate}},
        "faults": 0,
        "unfinished": 0,
        "runtimeSeconds": {"max": 10.0},
    }


def test_artifact_is_count_only_and_submission_local() -> None:
    artifact = json.loads(Path("agents/public_value_model.json").read_text())
    assert artifact["featureAllowlist"] == list(PUBLIC_FEATURE_ALLOWLIST)
    assert artifact["trainingSplit"] == "train"
    assert len(artifact["weights"]) == len(PUBLIC_FEATURE_ALLOWLIST)


def test_public_value_ignores_hidden_payload_and_is_bounded() -> None:
    evaluator = PublicValueEvaluator()
    first = evaluator.evaluate(observation(hidden={"cards": [1, 2, 3]}), 0)
    second = evaluator.evaluate(observation(hidden={"cards": [999]}), 0)
    assert first == pytest.approx(second)
    assert 0.0 <= first <= 1.0


def test_zero_blend_exactly_reproduces_champion() -> None:
    artifact = json.loads(Path("agents/public_value_model.json").read_text())
    artifact["blendWeight"] = 0.0
    candidate = PublicValueEvaluator(artifact=artifact)
    champion = HeuristicEvaluator()
    assert candidate.evaluate(observation(), 0) == pytest.approx(
        champion.evaluate(observation(), 0)
    )


def test_gate_requires_aggregate_matchup_and_both_seats() -> None:
    manifest = {"gate": {"matchRuntimeSecondsMax": 600.0}}
    assert DECISION.gate(summary(0.5), summary(0.6), manifest)["passed"] is True
    candidate = summary(0.6)
    candidate["seatWinRate"]["1"] = 0.4
    result = DECISION.gate(summary(0.5), candidate, manifest)
    assert result["passed"] is False
    assert "seat 1 regressed" in result["reasons"]


def test_manifest_preregisters_disjoint_screen_confirm_and_no_kaggle() -> None:
    manifest = json.loads(Path("eval/manifests/sot-2346-public-value.json").read_text())
    assert manifest["preregisteredBeforeConfirm"] is True
    assert manifest["screen"]["baseSeed"] != manifest["confirm"]["baseSeed"]
    assert manifest["screen"]["seatReversal"] is True
    assert manifest["confirm"]["seatReversal"] is True
    assert manifest["kaggleSubmission"] is False
