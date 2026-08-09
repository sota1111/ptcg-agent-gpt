import hashlib
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_blind_split_is_entity_time_lineage_and_seed_disjoint() -> None:
    manifest = load("eval/manifests/sot-2556-blind-holdout.json")
    summary = load("artifacts/sot-2556/summary.json")
    assert manifest["preregisteredBeforeExperiment"] is True
    assert manifest["isolation"]["seatReversal"] is True
    assert manifest["isolation"]["window"]["start"] > "2026-08-09T23:59:59Z"
    assert set(summary["isolation"].values()) == {0}


def test_all_opponents_seats_reliability_and_runtime_are_recorded() -> None:
    summary = load("artifacts/sot-2556/summary.json")
    result = summary["result"]
    assert result["matches"] == 50
    assert len(result["opponents"]) == 5
    assert set(result["seats"]) == {"0", "1"}
    assert all(row["matches"] == 10 for row in result["opponents"].values())
    assert all(row["matches"] == 25 for row in result["seats"].values())
    assert result["faults"] == result["illegalActions"] == result["unfinished"] == 0
    assert set(result["runtimeSeconds"]) == {"mean", "p95", "max"}
    assert result["runtimeSeconds"]["max"] < 600
    assert len(result["wilson95"]) == 2
    assert summary["operationalAuditPassed"] is True


def test_terminal_receipt_is_exact_and_records_no_submission() -> None:
    handoff = load("artifacts/sot-2556/handoff.json")
    manifest = load("eval/manifests/sot-2556-blind-holdout.json")
    fingerprint = load("artifacts/sot-2556/submission-fingerprint.json")
    assert handoff["terminal"] == {
        "candidate": None,
        "identity": "champion",
        "sourceDecision": "retain-champion",
    }
    assert (
        hashlib.sha256(Path("main.py").read_bytes()).hexdigest()
        == manifest["terminal"]["mainSha256"]
    )
    assert handoff["currentContentSha256"] == fingerprint["canonical_content_sha256"]
    assert handoff["archiveSha256"] == fingerprint["archive_sha256"]
    assert all(handoff["verification"].values())
    assert handoff["newArtifact"] is False
    assert handoff["artifact"] is None
    assert handoff["kaggleSubmitted"] is False


def test_rejected_candidate_is_absent_from_retained_archive() -> None:
    fingerprint = load("artifacts/sot-2556/submission-fingerprint.json")
    paths = {entry["path"] for entry in fingerprint["entries"]}
    assert "agents/counter_meta_policy.py" not in paths
