import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_blind_population_is_fully_disjoint_and_both_seats_complete() -> None:
    manifest = load("eval/manifests/sot-2574-terminal-population-blind.json")
    summary = load("artifacts/sot-2574/summary.json")
    assert manifest["preregisteredBeforeExperiment"] is True
    assert manifest["isolation"]["seatReversal"] is True
    assert set(summary["isolation"].values()) == {0}
    assert summary["result"]["matches"] == 20
    assert set(summary["result"]["seats"]) == {"0", "1"}
    assert all(row["matches"] == 10 for row in summary["result"]["seats"].values())


def test_archetype_reliability_wilson_and_runtime_are_recorded() -> None:
    result = load("artifacts/sot-2574/summary.json")["result"]
    assert {row["archetype"] for row in result["opponents"].values()} == {
        "diversified-policy-deck",
        "top-emerging-reanchoring",
    }
    assert result["faults"] == result["illegalActions"] == result["unfinished"] == 0
    assert len(result["wilson95"]) == 2
    assert set(result["runtimeSeconds"]) == {"mean", "p95", "max"}
    assert result["runtimeSeconds"]["max"] < 600


def test_terminal_handoff_maps_retained_champion_to_exact_new_artifact() -> None:
    handoff = load("artifacts/sot-2574/handoff.json")
    fingerprint = load("artifacts/sot-2574/submission-fingerprint.json")
    assert handoff["terminal"] == {
        "candidate": None,
        "identity": "champion",
        "sourceDecision": "retain-champion",
    }
    assert handoff["newArtifact"] is True
    assert handoff["artifact"]["contentSha256"] == fingerprint["canonical_content_sha256"]
    assert handoff["archiveSha256"] == fingerprint["archive_sha256"]
    assert all(handoff["verification"].values())
    assert handoff["kaggleSubmitted"] is False


def test_rejected_candidates_are_absent_from_exec_archive() -> None:
    paths = {
        entry["path"] for entry in load("artifacts/sot-2574/submission-fingerprint.json")["entries"]
    }
    assert "agents/population_prior.py" not in paths
    assert "agents/population_prior_sot_2572.json" not in paths
    assert "agents/counter_meta_policy.py" not in paths
