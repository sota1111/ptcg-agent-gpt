import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_holdout_seeds_are_isolated_and_seat_reversed() -> None:
    manifest = load_json("eval/manifests/sot-2233-blind-holdout.json")
    holdout = set(manifest["isolation"]["holdout_seeds"])
    used = (
        set(range(2231101, 2231106)) | set(range(2232101, 2232104)) | set(range(2232201, 2232211))
    )
    assert holdout.isdisjoint(used)
    assert manifest["isolation"]["seat_reversal"] is True
    assert manifest["isolation"]["matches_per_opponent"] == 2 * len(holdout)


def test_summary_records_required_operational_audit() -> None:
    summary = load_json("artifacts/sot-2233-summary.json")
    assert summary["pool"]["matches"] == 50
    assert summary["pool"]["faults"] == 0
    assert summary["pool"]["unfinished"] == 0
    assert summary["pool"]["illegal_actions"] == 0
    assert summary["pool"]["runtime_s"]["max"] < 600
    assert summary["decision"]["champion_behavior_changed"] is False
