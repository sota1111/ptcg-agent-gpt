import json
from pathlib import Path

import pytest

from scripts.validate_tactical_contract import (
    REQUIRED_FORBIDDEN,
    require_confirm_authorization,
    screen_gate,
    validate_manifest,
)

MANIFEST = Path("eval/manifests/sot-2439-public-tactical-contract.json")


def _metrics(aggregate: float = 0.5) -> dict:
    opponents = {name: 0.5 for name in ("matsu", "take", "ume", "claude", "obo", "meta-proxy")}
    return {
        "aggregate": aggregate,
        "opponents": opponents,
        "seat1": 0.5,
        "faults": 0,
        "unfinished": 0,
        "runtime": 10.0,
    }


def test_manifest_freezes_public_only_features_and_sot_2399_pool() -> None:
    manifest = validate_manifest(MANIFEST)
    assert set(manifest["policyFeatures"]["forbidden"]) == REQUIRED_FORBIDDEN
    assert manifest["inheritedReanchoringContract"]["opponents"] == [
        "matsu",
        "take",
        "ume",
        "claude",
        "obo",
        "meta-proxy",
    ]
    assert manifest["candidate"]["sameSearchAndRuntimeBudgetAsChampion"] is True
    assert manifest["kaggleSubmissionAllowed"] is False


def test_manifest_drift_fails_closed(tmp_path: Path) -> None:
    drifted = tmp_path / "manifest.json"
    drifted.write_text(MANIFEST.read_text().replace('"baseSeed": 2439101', '"baseSeed": 1'))
    with pytest.raises(ValueError, match="manifest fingerprint drifted"):
        validate_manifest(drifted, MANIFEST.with_suffix(".sha256"))


def test_failed_screen_deterministically_forbids_confirm() -> None:
    decision = screen_gate(_metrics(), _metrics())
    assert decision == {
        "passed": False,
        "reasons": ["aggregate did not strictly improve"],
        "confirmAuthorized": False,
    }
    with pytest.raises(ValueError, match="confirm is forbidden"):
        require_confirm_authorization(decision)


def test_every_screen_constraint_must_pass_before_confirm() -> None:
    champion = _metrics()
    candidate = _metrics(aggregate=0.6)
    decision = screen_gate(champion, candidate)
    require_confirm_authorization(decision)
    assert decision["passed"] is True

    regressed = json.loads(json.dumps(candidate))
    regressed["opponents"]["take"] = 0.4
    regressed["seat1"] = 0.4
    regressed["faults"] = 1
    regressed["unfinished"] = 1
    regressed["runtime"] = 10.1
    assert screen_gate(champion, regressed)["reasons"] == [
        "opponent regression: take",
        "seat1 regression",
        "faults regression",
        "unfinished regression",
        "runtime regression",
    ]
