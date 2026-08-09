import json
from pathlib import Path

import pytest

from scripts.audit_archetype_population_sot_2571 import (
    audit_contract,
    authorize_phase,
    compare_gate,
)

MANIFEST = Path("eval/manifests/sot-2571-archetype-population.json")


def load_contract() -> dict:
    return json.loads(MANIFEST.read_text())


def write_contract(tmp_path: Path, contract: dict) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract))
    return path


def test_contract_is_reproducible_and_all_population_boundaries_are_disjoint() -> None:
    first = audit_contract(MANIFEST)
    second = audit_contract(MANIFEST)
    assert first == second
    assert first["passed"] is True
    assert first["members"] >= 7
    assert first["kaggleSubmissionAllowed"] is False
    for pair in first["overlaps"].values():
        assert all(not values for values in pair.values())


def test_popularity_estimation_is_train_only(tmp_path: Path) -> None:
    contract = load_contract()
    contract["splitContract"]["popularityReadAllowedSplits"].append("screen")
    with pytest.raises(ValueError, match="popularity weights must be train-only"):
        audit_contract(write_contract(tmp_path, contract))


def test_private_or_future_feature_boundary_fails_closed(tmp_path: Path) -> None:
    contract = load_contract()
    contract["features"]["allow"].append("future_replay")
    with pytest.raises(ValueError, match="public feature boundary is incomplete"):
        audit_contract(write_contract(tmp_path, contract))


def test_nonportable_asset_cannot_enter_runtime(tmp_path: Path) -> None:
    contract = load_contract()
    contract["assets"][2]["runtimeAllowed"] = True
    with pytest.raises(ValueError, match="non-portable runtime asset is forbidden"):
        audit_contract(write_contract(tmp_path, contract))


def test_confirm_and_blind_require_independent_passing_receipts() -> None:
    with pytest.raises(ValueError, match="confirm forbidden"):
        authorize_phase("confirm", {"phase": "screen", "gate": {"passed": False}})
    authorize_phase("confirm", {"phase": "screen", "gate": {"passed": True}})
    with pytest.raises(ValueError, match="blind forbidden"):
        authorize_phase("blind", {"phase": "screen", "gate": {"passed": True}})
    authorize_phase("blind", {"phase": "confirm", "gate": {"passed": True}})


def test_unchanged_champion_never_false_positively_passes_gate() -> None:
    champion = {
        "poolWinRate": 0.5,
        "archetypes": {"established": 0.5, "emerging": 0.5},
        "matchups": {"take": 0.5},
        "seats": {"0": 0.5, "1": 0.5},
        "faults": 0,
        "unfinished": 0,
        "meanRuntimeSeconds": 10.0,
    }
    decision = compare_gate(champion, dict(champion))
    assert decision["passed"] is False
    assert decision["reasons"] == ["pooled win rate did not strictly improve"]
