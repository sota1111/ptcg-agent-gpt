import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2255-selective-lookahead-promotion.json")
SPEC = importlib.util.spec_from_file_location(
    "selective_lookahead", Path("scripts/analyze_selective_lookahead_sot_2255.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_preregisters_one_change_and_independent_seeds() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["screen"]["base_seed"] != manifest["confirm"]["base_seed"]
    assert manifest["screen"]["seat_reversal"] is True
    assert len(manifest["candidates"]) == 1
    assert manifest["privacy"]["hidden_zone_features"] is False
    assert manifest["privacy"]["opponent_identity_branching"] is False


def test_screen_is_complete_and_failed_candidate_preserves_champion() -> None:
    result = MODULE.analyze(MANIFEST)
    assert result["decision"]["screen_pass"] is False
    assert result["decision"]["confirm_run"] is False
    assert "worst matchup matsu regressed" in result["decision"]["reasons"]
    assert result["confirm"] == {}
    assert result["promoted"] is None
    assert result["champion_behavior_changed"] is False
    assert result["hidden_information_leakage"] is False
    for identity in ("champion", "bounded-public-setup-continuation"):
        assert result["results"][identity]["fixed"]["faults"] == 0
        assert result["results"][identity]["diversified"]["unfinished"] == 0
