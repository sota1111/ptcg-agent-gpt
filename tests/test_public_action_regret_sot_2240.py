import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2240-public-action-regret.json")
SPEC = importlib.util.spec_from_file_location(
    "action_regret", Path("scripts/analyze_public_action_regret.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_freezes_champion_opponents_unused_seeds_and_budget() -> None:
    manifest = json.loads(MANIFEST.read_text())
    fixed = manifest["fixed_conditions"]
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["champion"]["behavior_commit"] == "fd09f651ba9ed11648a6e5ac3a80fa2f16749130"
    assert [row["id"] for row in manifest["opponents"]] == ["matsu", "claude"]
    assert fixed["seeds"] == [2240101, 2240102, 2240103]
    assert fixed["seat_reversal"] is True
    assert fixed["search_budget"] == {"max_root_actions": 6, "n_worlds": 4, "time_budget_s": 0.8}


def test_traces_pair_seats_and_contain_complete_public_counterfactuals() -> None:
    manifest = json.loads(MANIFEST.read_text())
    for opponent in manifest["opponents"]:
        report = json.loads((MANIFEST.parent / opponent["validation_report"]).resolve().read_text())
        assert report["base_seed"] == 2240101
        assert report["seeds"] == 3
        assert report["faults_semantic"] == report["unfinished"] == 0
        for seed in manifest["fixed_conditions"]["seeds"]:
            assert {
                row["semantic_seat"] for row in report["matches"] if row["agent_seed"] == seed
            } == {0, 1}
        assert all(
            "fingerprint" not in root
            for match in report["matches"]
            for event in match["determinization_telemetry"]
            for root in event["world_roots"]
        )


def test_summary_is_deterministic_exclusive_and_behavior_preserving() -> None:
    first = MODULE.analyze(MANIFEST)
    second = MODULE.analyze(MANIFEST)
    assert first == second
    assert first["decision_points"]
    assert all(len(row["legal_actions"]) >= 2 for row in first["decision_points"])
    assert all(row["action_regret"] >= 0 for row in first["decision_points"])
    assert sum(row["support"] for row in first["clusters"]) == len(first["decision_points"])
    assert {row["scope"] for row in first["clusters"]} <= {
        "common",
        "matsu-specific",
        "claude-specific",
    }
    assert len(first["hypotheses"]) == 3
    assert first["privacy_audit"]["hidden_information_leakage"] is False
    assert first["champion_behavior_changed"] is False
    assert first["promotion_performed"] is False
