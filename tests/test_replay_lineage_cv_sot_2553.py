import json
from pathlib import Path

import pytest

from scripts.audit_metagame_cv import audit_manifest, compare_cv_public

MANIFEST = Path("eval/manifests/sot-2553-replay-lineage-cv.json")


def test_all_identity_time_and_lineage_boundaries_are_disjoint() -> None:
    result = audit_manifest(MANIFEST)
    assert result["passed"] is True
    required = {
        "entity",
        "policy",
        "deck",
        "match",
        "seed",
        "time",
        "evidence",
        "submissionLineage",
    }
    for overlap in result["overlaps"].values():
        assert required == overlap.keys()
        assert all(not values for values in overlap.values())


@pytest.mark.parametrize("field", ["id", "submissionLineage"])
def test_reused_evidence_or_submission_lineage_fails_closed(tmp_path: Path, field: str) -> None:
    manifest = json.loads(MANIFEST.read_text())
    rows = {row["id"]: row for row in manifest["opponents"]}
    rows["ume"]["evidence"][field] = rows["take"]["evidence"][field]
    path = tmp_path / "leak.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="cross-split overlap"):
        audit_manifest(path)


def test_collection_timestamp_must_be_inside_its_frozen_window(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["opponents"][0]["evidence"]["collectedAt"] = "2026-08-09T12:00:00Z"
    path = tmp_path / "time-leak.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="outside split window"):
        audit_manifest(path)


def test_license_and_offline_portability_are_fail_closed(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["opponents"][0]["evidence"]["offlinePortable"] = False
    path = tmp_path / "not-portable.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="not licensed and offline portable"):
        audit_manifest(path)


def test_public_rating_is_sanity_only_and_cv_wins_on_disagreement() -> None:
    result = compare_cv_public(["a", "b"], ["b", "a"])
    assert result["sharedOrderAgreement"] is False
    assert result["selectedOrder"] == ["a", "b"]
    assert result["selectionBasis"] == "cv-pessimistic-on-disagreement"
    assert result["publicRole"] == "sanity-only"


def test_public_alakazam_provenance_is_pinned_and_portable() -> None:
    manifest = json.loads(MANIFEST.read_text())
    row = next(item for item in manifest["opponents"] if item["id"] == "search-alakazam-v12")
    evidence = row["evidence"]
    assert row["license"] == "Apache-2.0"
    assert row["sourceVersion"] == 19
    assert evidence["kind"] == "licensed-public-agent"
    assert evidence["offlinePortable"] is True
    assert Path(evidence["licenseEvidence"]).is_file()
