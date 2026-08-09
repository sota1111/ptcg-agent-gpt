import hashlib
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_blind_split_is_fully_disjoint_and_preregistered() -> None:
    manifest = load("eval/manifests/sot-2540-blind-holdout.json")
    summary = load("artifacts/sot-2540/summary.json")
    assert manifest["preregisteredBeforeExperiment"] is True
    assert manifest["isolation"]["seatReversal"] is True
    assert manifest["isolation"]["window"]["start"] > "2026-08-09T23:59:59Z"
    assert set(summary["isolation"].values()) == {0}


def test_all_opponents_and_seats_are_reliable() -> None:
    summary = load("artifacts/sot-2540/summary.json")
    result = summary["result"]
    assert result["matches"] == 50
    assert len(result["opponents"]) == 5
    assert set(result["seatWinRate"]) == {"0", "1"}
    assert result["faults"] == result["illegalActions"] == result["unfinished"] == 0
    assert result["runtimeSeconds"]["max"] < 600
    assert summary["operationalAuditPassed"] is True
    assert summary["kaggleSubmitted"] is False


def test_handoff_is_exact_and_records_no_submission() -> None:
    handoff = load("artifacts/sot-2540/handoff.json")
    fingerprint = load("artifacts/sot-2540/submission-fingerprint.json")
    assert handoff["terminal"]["identity"] == "champion"
    assert handoff["terminal"]["candidate"] is None
    assert handoff["artifact"]["contentSha256"] == fingerprint["canonical_content_sha256"]
    assert (
        handoff["artifact"]["mainSha256"]
        == hashlib.sha256(Path("main.py").read_bytes()).hexdigest()
    )
    assert all(handoff["verification"].values())
    assert handoff["newArtifact"] is True
    assert handoff["kaggleSubmitted"] is False
