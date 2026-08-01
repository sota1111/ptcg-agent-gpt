import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2241-regret-policy-promotion.json")
SPEC = importlib.util.spec_from_file_location(
    "regret_policy", Path("scripts/analyze_regret_policy_sot_2241.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_preregisters_public_state_candidates_and_independent_seeds() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["screen"]["base_seed"] != manifest["confirm"]["base_seed"]
    assert manifest["screen"]["seat_reversal"] is True
    assert len(manifest["candidates"]) == 3
    assert all(
        row["one_change"] and row["difference_from_prior_axes"] for row in manifest["candidates"]
    )
    assert manifest["privacy"]["hidden_zone_features"] is False
    assert manifest["privacy"]["opponent_identity_branching"] is False


def test_screen_reports_are_complete_seat_reversed_and_fault_free() -> None:
    manifest = json.loads(MANIFEST.read_text())
    identities = ["champion", *[row["id"] for row in manifest["candidates"]]]
    opponents = [*manifest["pools"]["fixed"], *manifest["pools"]["diversified"]]
    for identity in identities:
        for opponent in opponents:
            report = json.loads(
                Path(f"artifacts/sot-2241/screen/{identity}-{opponent}.json").read_text()
            )
            assert report["faults_semantic"] == 0
            assert report["unfinished"] == 0
            assert {row["agent_seed"] for row in report["matches"]} == {2241101, 2241102}
            for seed in (2241101, 2241102):
                assert {
                    row["semantic_seat"] for row in report["matches"] if row["agent_seed"] == seed
                } == {0, 1}
            assert all(
                "fingerprint" not in root
                for match in report["matches"]
                for event in match["determinization_telemetry"]
                for root in event.get("world_roots", [])
            )


def test_failed_screens_skip_confirm_and_preserve_champion() -> None:
    result = MODULE.analyze(MANIFEST)
    assert result["screen_passing_candidates"] == []
    assert result["confirm"] == {}
    assert result["promoted"] is None
    assert result["champion_behavior_changed"] is False
    assert result["hidden_information_leakage"] is False
    assert all(
        not row["screen_pass"] and not row["confirm_run"] for row in result["decisions"].values()
    )
