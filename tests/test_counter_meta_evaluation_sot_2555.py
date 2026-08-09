import json
from pathlib import Path

import pytest

from scripts.evaluate_counter_meta_sot_2555 import verify_fingerprints

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "eval/manifests/sot-2555-counter-meta-paired.json"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_manifest_freezes_fingerprints_split_seed_seat_budget_and_gate() -> None:
    contract = manifest()
    assert verify_fingerprints(REPO, contract)
    assert contract["preregisteredBeforeScreen"] is True
    assert contract["budget"]["equal"] is True
    assert contract["phases"]["screen"]["seats"] == [0, 1]
    assert contract["phases"]["confirm"]["seats"] == [0, 1]
    assert contract["phases"]["screen"]["baseSeed"] != 2553201
    assert contract["phases"]["confirm"]["baseSeed"] != 2553301
    gate = contract["promotionGate"]
    assert gate["pooledWinRateStrictlyImproves"] is True
    assert gate["everyOpponentNonRegression"] is True
    assert gate["bothSeatsNonRegression"] is True
    assert gate["faultsMax"] == gate["unfinishedMax"] == 0


def test_screen_and_confirm_are_independent_and_source_aligned() -> None:
    contract = manifest()
    source = json.loads((REPO / contract["sourceContract"]).read_text())
    screen = contract["phases"]["screen"]
    confirm = contract["phases"]["confirm"]
    assert set(screen["opponents"]) == set(source["splits"]["screen"]["opponents"])
    assert set(confirm["opponents"]) == set(source["splits"]["confirm"]["opponents"])
    assert set(screen["opponents"]).isdisjoint(confirm["opponents"])
    assert screen["baseSeed"] != confirm["baseSeed"]


def test_candidate_stays_fail_closed_and_public_best_is_forbidden() -> None:
    contract = manifest()
    assert contract["candidate"]["defaultEnabled"] is False
    assert contract["failureBehavior"].startswith("retain champion")
    assert contract["cvPublicGap"]["disagreementRule"] == "prefer-cv"
    assert contract["cvPublicGap"]["publicBestSelectionAllowed"] is False
    assert contract["kaggleSubmissionAllowed"] is False


def test_fingerprint_drift_fails_before_execution(tmp_path: Path) -> None:
    contract = manifest()
    contract["candidate"]["deckSha256"] = "0" * 64
    with pytest.raises(ValueError, match="candidateDeck"):
        verify_fingerprints(REPO, contract)


def test_confirm_rejects_a_failed_screen_receipt(tmp_path: Path) -> None:
    receipt = tmp_path / "screen.json"
    receipt.write_text(json.dumps({"phase": "screen", "gate": {"passed": False}}))
    source = (REPO / "scripts/evaluate_counter_meta_sot_2555.py").read_text()
    assert "confirm forbidden: screen gate did not pass" in source
    assert '"candidateArtifact"' in source
    assert '"rawReportSha256"' in source
