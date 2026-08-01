import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_holdout_seeds_are_isolated_and_seat_reversed() -> None:
    manifest = load_json("eval/manifests/sot-2242-blind-holdout.json")
    holdout = set(manifest["isolation"]["holdout_seeds"])
    used = (
        set(range(2240101, 2240104)) | set(range(2241101, 2241103)) | set(range(2241201, 2241206))
    )
    assert holdout.isdisjoint(used)
    assert manifest["isolation"]["seat_reversal"] is True
    assert manifest["isolation"]["matches_per_opponent"] == 2 * len(holdout)


def test_summary_and_submission_record_required_audit() -> None:
    summary = load_json("artifacts/sot-2242-summary.json")
    submission = load_json("artifacts/sot-2242/submission.json")
    assert summary["pool"]["matches"] == 50
    assert summary["pool"]["faults"] == 0
    assert summary["pool"]["unfinished"] == 0
    assert summary["pool"]["illegal_actions"] == 0
    assert summary["pool"]["runtime_s"]["max"] < 600
    assert summary["decision"]["champion_behavior_changed"] is False
    assert submission["submission"]["submitted"] is True
    assert submission["submission"]["ref"] == "55154527"
    assert submission["submission"]["status"] == "COMPLETE"
    assert submission["submission"]["public_score"] == 600.0
    assert submission["artifact"]["archive_sha256"] == (
        "c3b9f8cc2b67b25e1be5b0d66230b0fbc2009316e72eb9817a87146b9d6b48c7"
    )
