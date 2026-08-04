import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def test_blind_protocol_is_independent_and_preregistered():
    manifest = load("eval/manifests/sot-2401-blind-holdout.json")
    seeds = set(manifest["isolation"]["holdout_seeds"])
    assert seeds.isdisjoint({2399101} | set(range(2399201, 2399206)))
    assert manifest["preregistered_before_experiment"] is True
    assert manifest["isolation"]["seat_reversal"] is True
    assert manifest["isolation"]["matches_per_opponent"] == 10
    assert len(manifest["opponents"]) == 5


def test_terminal_and_operational_gates_are_machine_readable():
    summary = load("artifacts/sot-2401/summary.json")
    assert summary["terminal"]["validated"] is True
    assert summary["pool"]["matches"] == 50
    assert summary["pool"]["faults"] == 0
    assert summary["pool"]["unfinished"] == 0
    assert summary["pool"]["illegal_actions"] == 0
    assert summary["pool"]["runtime_s"]["max"] < 600
    assert set(summary["pool"]["seat_win_rate"]) == {"0", "1"}
    assert summary["decision"]["operational_audit_passed"] is True
    assert summary["decision"]["terminal_identity"] == "champion"
    assert summary["decision"]["candidate_behavior_reverted"] is True
    assert summary["decision"]["kaggle_submitted"] is False


def test_handoff_binds_exact_exec_compatible_archive():
    handoff = load("artifacts/sot-2401/handoff.json")
    fingerprint = load("artifacts/sot-2401/submission-fingerprint.json")
    assert handoff["terminal"] == {
        "identity": "champion",
        "candidate": None,
        "source_decision": "champion_retained",
    }
    assert all(handoff["verification"].values())
    assert handoff["artifact"]["archive_sha256"] == fingerprint["archive_sha256"]
    assert handoff["artifact"]["content_sha256"] == fingerprint["canonical_content_sha256"]
    main_sha256 = hashlib.sha256(Path("main.py").read_bytes()).hexdigest()
    deck_sha256 = hashlib.sha256(Path("deck.csv").read_bytes()).hexdigest()
    assert handoff["artifact"]["main_sha256"] == main_sha256
    assert handoff["artifact"]["deck_sha256"] == deck_sha256
    assert handoff["submission"] == {
        "eligible_for_parent_submission": True,
        "kaggle_submitted": False,
        "submission_owner": "SOT-2398",
    }
