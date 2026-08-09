import copy
import json
from pathlib import Path

import pytest

from scripts.audit_metagame_cv import audit_manifest, authorize_confirm, compare

MANIFEST = Path("eval/manifests/sot-2538-entity-time-cv.json")


def test_manifest_has_zero_required_overlap_and_pins_public_opponent() -> None:
    result = audit_manifest(MANIFEST)
    assert result["passed"] is True
    assert result["publicOpponents"] == ["search-alakazam-v12"]
    for pair in result["overlaps"].values():
        assert all(not pair[key] for key in ("entity", "policy", "deck", "match", "seed", "time"))


def test_intentional_entity_leak_is_rejected(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["splits"]["confirm"]["opponents"].append("take")
    path = tmp_path / "leaked.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="cross-split overlap"):
        audit_manifest(path)


def test_public_opponent_is_offline_license_allowlisted_and_fingerprinted() -> None:
    manifest = json.loads(MANIFEST.read_text())
    opponent = next(row for row in manifest["opponents"] if row["id"] == "search-alakazam-v12")
    assert opponent["offline"] is True
    assert opponent["license"] == "Apache-2.0"
    assert len(opponent["policySha256"]) == len(opponent["deckSha256"]) == 64
    assert Path(opponent["repo"], "NOTICE.md").is_file()


def test_identical_candidate_fails_screen_and_cannot_open_confirm() -> None:
    champion = {
        "poolWinRate": 0.5,
        "opponents": {"take": 0.5},
        "seats": {"0": 0.5, "1": 0.5},
        "faults": 0,
        "unfinished": 0,
        "meanRuntimeSeconds": 1.0,
        "maxRuntimeSeconds": 2.0,
    }
    manifest = json.loads(MANIFEST.read_text())
    decision = {
        "phase": "screen",
        "gate": compare(champion, copy.deepcopy(champion), manifest["promotionGate"]),
    }
    assert decision["gate"]["passed"] is False
    with pytest.raises(ValueError, match="confirm is forbidden"):
        authorize_confirm(decision)


def test_gate_rejects_opponent_seat_reliability_and_runtime_regressions() -> None:
    champion = {
        "poolWinRate": 0.5,
        "opponents": {"a": 0.5},
        "seats": {"0": 0.5, "1": 0.5},
        "faults": 0,
        "unfinished": 0,
        "meanRuntimeSeconds": 1.0,
        "maxRuntimeSeconds": 2.0,
    }
    candidate = {
        "poolWinRate": 0.6,
        "opponents": {"a": 0.4},
        "seats": {"0": 0.6, "1": 0.4},
        "faults": 1,
        "unfinished": 1,
        "meanRuntimeSeconds": 1.2,
        "maxRuntimeSeconds": 600.0,
    }
    gate = compare(champion, candidate, json.loads(MANIFEST.read_text())["promotionGate"])
    assert gate["passed"] is False
    assert len(gate["reasons"]) == 6
