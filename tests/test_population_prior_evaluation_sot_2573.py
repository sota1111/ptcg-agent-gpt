import json
from pathlib import Path

import pytest

from scripts.evaluate_population_prior_sot_2573 import gate_result, verify_fingerprints

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "eval/manifests/sot-2573-population-prior-paired.json"


def summary(wins=2, seat_wins=(1, 1), faults=0, unfinished=0, runtime=1.0):
    return {
        "opponents": {
            "a": {"wins": wins // 2, "matches": 2, "winRate": (wins // 2) / 2},
            "b": {"wins": wins - wins // 2, "matches": 2, "winRate": (wins - wins // 2) / 2},
        },
        "seats": {
            "0": {"wins": seat_wins[0], "matches": 2, "winRate": seat_wins[0] / 2},
            "1": {"wins": seat_wins[1], "matches": 2, "winRate": seat_wins[1] / 2},
        },
        "pool": {
            "wins": wins,
            "matches": 4,
            "faults": faults,
            "unfinished": unfinished,
            "runtimeSeconds": {"mean": runtime, "p95": runtime, "max": runtime},
        },
    }


def test_manifest_fingerprints_splits_and_default_disabled():
    manifest = json.loads(MANIFEST.read_text())
    assert verify_fingerprints(ROOT, manifest)
    population_contract = json.loads((ROOT / manifest["sourceContract"]).read_text())
    cv_contract = json.loads((ROOT / population_contract["sourceContract"]).read_text())
    assert {"screen", "confirm"} <= cv_contract["splits"].keys()
    assert manifest["candidateDefaultEnabled"] is False
    assert manifest["phases"]["screen"]["sourceSplit"] == "screen"
    assert manifest["phases"]["confirm"]["sourceSplit"] == "confirm"
    assert set(manifest["phases"]["screen"]["opponents"]).isdisjoint(
        manifest["phases"]["confirm"]["opponents"]
    )
    assert manifest["phases"]["screen"]["seats"] == [0, 1]
    assert manifest["budget"]["equal"] is True
    assert manifest["kaggleSubmissionAllowed"] is False


@pytest.mark.parametrize(
    ("candidate", "candidate_archetypes", "reason"),
    [
        (summary(wins=2), {"x": {"winRate": 0.5}}, "pooled wins did not strictly improve"),
        (summary(wins=3, seat_wins=(2, 1)), {"x": {"winRate": 0.0}}, "archetype regression: x"),
        (
            summary(wins=3, seat_wins=(2, 1), faults=1),
            {"x": {"winRate": 0.5}},
            "candidate fault observed",
        ),
        (
            summary(wins=3, seat_wins=(2, 1), unfinished=1),
            {"x": {"winRate": 0.5}},
            "candidate unfinished match observed",
        ),
        (
            summary(wins=3, seat_wins=(2, 1), runtime=1.2),
            {"x": {"winRate": 0.5}},
            "mean runtime ratio exceeded",
        ),
    ],
)
def test_strict_gate_rejects_each_failure(candidate, candidate_archetypes, reason):
    manifest = json.loads(MANIFEST.read_text())
    champion = summary()
    result = gate_result(
        champion,
        candidate,
        {"x": {"winRate": 0.5}},
        candidate_archetypes,
        manifest["promotionGate"],
    )
    assert result["passed"] is False
    assert reason in result["reasons"]


def test_strict_gate_accepts_only_complete_non_regressing_improvement():
    manifest = json.loads(MANIFEST.read_text())
    result = gate_result(
        summary(),
        summary(wins=3, seat_wins=(2, 1)),
        {"x": {"winRate": 0.5}},
        {"x": {"winRate": 0.5}},
        manifest["promotionGate"],
    )
    assert result["passed"] is True
    assert all(result["checks"].values())
