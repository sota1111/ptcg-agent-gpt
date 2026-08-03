import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def test_blind_protocol_is_independent_and_preregistered():
    m = load("eval/manifests/sot-2378-blind-holdout.json")
    seeds = set(m["isolation"]["holdout_seeds"])
    assert seeds.isdisjoint({2377201} | set(range(2376101, 2376307)))
    assert m["preregistered_before_experiment"] is True
    assert m["isolation"]["seat_reversal"] is True
    assert m["isolation"]["matches_per_opponent"] == 10


def test_terminal_and_operational_gates_are_machine_readable():
    s = load("artifacts/sot-2378/summary.json")
    assert s["terminal"]["validated"] is True
    assert s["pool"]["matches"] == 50
    assert s["pool"]["faults"] == s["pool"]["unfinished"] == s["pool"]["illegal_actions"] == 0
    assert s["pool"]["runtime_s"]["max"] < 600
    assert set(s["pool"]["seat_win_rate"]) == {"0", "1"}
    assert s["decision"]["operational_audit_passed"] is True
    assert s["decision"]["terminal_identity"] == "champion"
    assert s["decision"]["candidate_behavior_reverted"] is True
    assert s["decision"]["kaggle_submitted"] is False


def test_handoff_binds_exact_exec_compatible_archive():
    h = load("artifacts/sot-2378/handoff.json")
    f = load("artifacts/sot-2378/submission-fingerprint.json")
    assert h["terminal"] == {
        "identity": "champion",
        "candidate": None,
        "source_decision": "champion_retained",
    }
    assert all(h["verification"].values())
    assert h["artifact"]["archive_sha256"] == f["archive_sha256"]
    assert h["artifact"]["content_sha256"] == f["canonical_content_sha256"]
    assert h["artifact"]["main_sha256"] == hashlib.sha256(Path("main.py").read_bytes()).hexdigest()
    assert h["artifact"]["deck_sha256"] == hashlib.sha256(Path("deck.csv").read_bytes()).hexdigest()
    assert h["submission"] == {
        "eligible_for_parent_submission": True,
        "kaggle_submitted": False,
        "submission_owner": "SOT-2364",
    }
