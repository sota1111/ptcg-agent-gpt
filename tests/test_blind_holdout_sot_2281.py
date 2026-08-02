import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_holdout_seeds_are_isolated_and_both_seats_are_preregistered() -> None:
    manifest = load_json("eval/manifests/sot-2281-blind-holdout.json")
    holdout = set(manifest["isolation"]["holdout_seeds"])
    prior = {2279101} | set(range(2280101, 2280106))
    assert holdout.isdisjoint(prior)
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["isolation"]["seat_reversal"] is True
    assert manifest["isolation"]["matches_per_opponent"] == 2 * len(holdout)


def test_report_provenance_and_aggregation() -> None:
    manifest = load_json("eval/manifests/sot-2281-blind-holdout.json")
    reports = {
        row["label"]: load_json(f"artifacts/sot-2281/holdout/{row['label']}.json")
        for row in manifest["opponents"]
    }
    expected_seeds = [seed for seed in manifest["isolation"]["holdout_seeds"] for _ in range(2)]
    for opponent in manifest["opponents"]:
        report = reports[opponent["label"]]
        assert [match["agent_seed"] for match in report["matches"]] == expected_seeds
        assert [match["semantic_seat"] for match in report["matches"]] == [0, 1] * 5
        assert report["opponent_repo"] == opponent["repo"]
    summary = load_json("artifacts/sot-2281/summary.json")
    assert summary["terminal"]["validated"] is True
    assert summary["pool"]["matches"] == 50
    assert summary["pool"]["faults"] == 0
    assert summary["pool"]["unfinished"] == 0
    assert summary["pool"]["illegal_actions"] == 0
    assert summary["pool"]["runtime_s"]["max"] < 600
    assert summary["decision"]["terminal_identity"] == "champion"
    assert summary["decision"]["promotion_outcome"] == "champion_retained"
    assert summary["decision"]["operational_audit_passed"] is True


def test_handoff_uniquely_maps_audited_artifact_without_submission() -> None:
    handoff = load_json("artifacts/sot-2281/handoff.json")
    fingerprint = load_json("artifacts/sot-2281/submission-fingerprint.json")
    assert handoff["terminal"]["identity"] == "champion"
    assert handoff["terminal"]["outcome"] == "champion_retained"
    assert handoff["verification"]["holdout_passed"] is True
    assert handoff["verification"]["deterministic_rebuild_passed"] is True
    assert handoff["verification"]["exec_compatibility_passed"] is True
    assert handoff["artifact"]["archive_sha256"] == fingerprint["archive_sha256"]
    assert handoff["artifact"]["content_sha256"] == fingerprint["canonical_content_sha256"]
    assert handoff["submission"]["kaggle_submitted"] is False
    assert handoff["submission"]["next_action"] == "parent_may_run_approved_helper"
