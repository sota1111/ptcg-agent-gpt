import hashlib
import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_blind_protocol_is_independent_and_preregistered() -> None:
    manifest = load_json("eval/manifests/sot-2347-blind-holdout.json")
    holdout = set(manifest["isolation"]["holdout_seeds"])
    prior = {2346101} | set(range(2346201, 2346204))
    assert holdout.isdisjoint(prior)
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["isolation"]["seat_reversal"] is True
    assert manifest["isolation"]["matches_per_opponent"] == 2 * len(holdout)
    assert set(manifest["isolation"]["excluded_artifacts"]) == {
        "artifacts/sot-2346-public-value/screen",
        "artifacts/sot-2346-public-value/confirm",
    }


def test_terminal_decision_and_all_blind_gates_are_machine_readable() -> None:
    summary = load_json("artifacts/sot-2347/summary.json")
    assert summary["terminal"]["validated"] is True
    assert summary["pool"]["matches"] == 50
    assert summary["pool"]["faults"] == 0
    assert summary["pool"]["unfinished"] == 0
    assert summary["pool"]["illegal_actions"] == 0
    assert summary["pool"]["runtime_s"]["max"] < 600
    assert set(summary["pool"]["seat_win_rate"]) == {"0", "1"}
    assert summary["decision"] == {
        "candidate_behavior_reverted": True,
        "kaggle_submitted": False,
        "operational_audit_passed": True,
        "promoted_candidate": None,
        "promotion_outcome": "champion_retained",
        "terminal_identity": "champion",
    }


def test_handoff_uniquely_identifies_exec_compatible_artifact() -> None:
    handoff = load_json("artifacts/sot-2347/handoff.json")
    fingerprint = load_json("artifacts/sot-2347/submission-fingerprint.json")
    assert handoff["terminal"]["identity"] == "champion"
    assert handoff["terminal"]["candidate"] is None
    assert handoff["verification"] == {
        "blind_holdout_passed": True,
        "deterministic_rebuild_passed": True,
        "exec_compatibility_passed": True,
    }
    assert handoff["artifact"]["archive_sha256"] == fingerprint["archive_sha256"]
    assert handoff["artifact"]["content_sha256"] == fingerprint["canonical_content_sha256"]
    for key, path in {"main_sha256": "main.py", "deck_sha256": "deck.csv"}.items():
        assert handoff["artifact"][key] == hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert handoff["submission"]["kaggle_submitted"] is False
    assert handoff["submission"]["eligible_for_parent_submission"] is True
