from agents.planner import PlannerConfig
from agents.public_belief import _public_opponent_ids, public_belief_weights, weighted_shuffle
from agents.rng import Rng
from tests.support import synthetic_card_index


def _observation(hidden_hand=None, hidden_deck_id=103):
    return {
        "current": {
            "yourIndex": 0,
            "players": [
                {},
                {
                    "hand": hidden_hand,
                    "deck": [{"id": hidden_deck_id}],
                    "prize": [None, {"id": 101}],
                    "discard": [{"id": 101}],
                    "active": [{"id": 101, "energyCards": [], "tools": []}],
                    "bench": [],
                },
            ],
            "stadium": [],
        }
    }


def test_public_evidence_excludes_hidden_zone_identities() -> None:
    first = _observation([{"id": 102}], 102)
    second = _observation([{"id": 103}], 103)
    assert _public_opponent_ids(first) == _public_opponent_ids(second) == [101, 101, 101]


def test_observed_public_archetype_increases_matching_bucket_weight() -> None:
    index = synthetic_card_index()
    weights = public_belief_weights(_observation(), [101, 103], [101, 102, 103], index)
    assert weights[0] > weights[1]


def test_weighted_world_sampling_is_seed_deterministic() -> None:
    left = [101, 102, 103]
    right = list(left)
    weighted_shuffle(left, [4.0, 1.0, 0.25], Rng(2400))
    weighted_shuffle(right, [4.0, 1.0, 0.25], Rng(2400))
    assert left == right


def test_candidate_is_disabled_without_telemetry(monkeypatch) -> None:
    monkeypatch.setenv("PTCG_PUBLIC_BELIEF_CANDIDATE", "1")
    monkeypatch.delenv("PTCG_TELEMETRY_PROTOCOL", raising=False)
    assert PlannerConfig().public_belief is False


def test_candidate_can_only_be_enabled_in_evaluation_harness(monkeypatch) -> None:
    monkeypatch.setenv("PTCG_PUBLIC_BELIEF_CANDIDATE", "1")
    monkeypatch.setenv("PTCG_TELEMETRY_PROTOCOL", "1")
    assert PlannerConfig().public_belief is True
