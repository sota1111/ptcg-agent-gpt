import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2232-robust-candidates.json")
SPEC = importlib.util.spec_from_file_location(
    "robust_candidates", Path("scripts/analyze_robust_candidates.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_preregisters_independent_screen_and_confirm() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["screen"]["base_seed"] != manifest["confirm"]["base_seed"]
    assert manifest["screen"]["seat_reversal"] is True
    assert len(manifest["candidates"]) == 2
    assert all(row["one_change"] and row["retry_evidence"] for row in manifest["candidates"])
    assert manifest["privacy"]["hidden_zone_features"] is False
    assert manifest["privacy"]["pool_direct_branching"] is False


def test_screen_reports_cover_same_pools_seeds_and_both_seats() -> None:
    manifest = json.loads(MANIFEST.read_text())
    expected_seeds = {2232101, 2232102, 2232103}
    identities = ["champion", *[row["id"] for row in manifest["candidates"]]]
    for identity in identities:
        for opponent in [*manifest["pools"]["fixed"], *manifest["pools"]["diversified"]]:
            report = json.loads(
                Path(f"artifacts/sot-2232/screen/{identity}-{opponent}.json").read_text()
            )
            assert report["faults_semantic"] == 0
            assert report["unfinished"] == 0
            assert {row["agent_seed"] for row in report["matches"]} == expected_seeds
            assert all(
                {row["semantic_seat"] for row in report["matches"] if row["agent_seed"] == seed}
                == {0, 1}
                for seed in expected_seeds
            )
            assert all(
                "fingerprint" not in root
                for row in report["matches"]
                for event in row["determinization_telemetry"]
                for root in event.get("world_roots", [])
            )


def test_failed_screens_do_not_promote_or_run_confirm() -> None:
    result = MODULE.analyze(MANIFEST)
    assert result["promoted"] is None
    assert result["champion_behavior_changed"] is False
    assert result["hidden_information_leakage"] is False
    assert all(not row["screen_pass"] for row in result["decisions"].values())
    assert all(not row["confirm_run"] for row in result["decisions"].values())
