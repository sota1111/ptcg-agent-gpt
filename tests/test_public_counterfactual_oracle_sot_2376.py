import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2376-public-counterfactual-oracle.json")
SPEC = importlib.util.spec_from_file_location(
    "public_counterfactual_oracle", Path("scripts/build_public_counterfactual_oracle.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_reports() -> dict:
    reports = {}
    for offset, split in enumerate(("train", "screen", "confirm")):
        event = {
            "step": 7,
            "public_state": {
                "turn_index": offset,
                "turn_action_count": 1,
                "selection_context": 2,
                "own": {"hand_count": 5, "deck_count": 40},
                "opponent": {"hand_count": 6, "deck_count": 39},
                "option_count": 2,
                "legal_option_types": [8, 14],
                "hidden_hand_identity": [999],
                "opponent_identity": "forbidden",
            },
            "world_roots": [
                {
                    "actions": [
                        {"action": [0], "value_mean": 0.8},
                        {"action": [1], "value_mean": 0.4},
                    ]
                },
                {
                    "actions": [
                        {"action": [0], "value_mean": 0.7},
                        {"action": [1], "value_mean": 0.5},
                    ]
                },
            ],
        }
        reports[split] = [
            {
                "matches": [
                    {
                        "agent_seed": 2376101 + offset * 100,
                        "semantic_seat": offset % 2,
                        "determinization_telemetry": [event],
                    }
                ]
            }
        ]
    return reports


def test_manifest_freezes_disjoint_splits_budget_privacy_and_no_submission() -> None:
    manifest = json.loads(MANIFEST.read_text())
    seed_sets = [set(phase["seeds"]) for phase in manifest["splits"].values()]
    assert all(
        not (left & right) for i, left in enumerate(seed_sets) for right in seed_sets[i + 1 :]
    )
    assert manifest["searchBudget"]["determinizations"] == 4
    assert manifest["searchBudget"]["timeBudgetSeconds"] == 0.8
    assert manifest["promotionContract"]["kaggleSubmission"] is False
    assert "opponent_identity" in manifest["forbiddenLearningFeatures"]
    assert "hidden_hand_identity" in manifest["forbiddenLearningFeatures"]


def test_oracle_is_deterministic_public_only_and_split_disjoint(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text())
    first = MODULE.build_rows(manifest, fixture_reports())
    second = MODULE.build_rows(manifest, fixture_reports())
    assert first == second
    assert {row["split"] for row in first} == {"train", "screen", "confirm"}
    assert all(row["leftActionTypes"] == [8] for row in first)
    assert all(row["rightActionTypes"] == [14] for row in first)
    assert all(row["relativeOutcome"] > 0 for row in first)
    serialized = json.dumps(first)
    assert "opponent_identity" not in serialized
    assert "hidden_hand_identity" not in serialized

    oracle = tmp_path / "oracle.jsonl"
    oracle.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in first))
    result = MODULE.diagnostics(manifest, first, oracle)
    assert result["splitLeakagePassed"] is True
    assert all(not overlap for overlap in result["splitOverlap"].values())
    assert all(not overlap for overlap in result["seedOverlap"].values())
    assert result["screenEligible"] is True
    assert result["artifactFingerprint"]
    assert MODULE.coverage_metrics(manifest, fixture_reports())["coverage"] == 1.0


def test_pairs_require_common_determinization_support() -> None:
    event = {
        "world_roots": [
            {"actions": [{"action": [0], "value_mean": 1.0}]},
            {"actions": [{"action": [1], "value_mean": 0.0}]},
        ]
    }
    assert MODULE.paired_values(event, shared_worlds_required=2) == []
