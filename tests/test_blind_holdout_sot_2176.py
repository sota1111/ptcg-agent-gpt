import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_blind_holdout_seeds_are_isolated_from_prior_stages() -> None:
    manifest = load_json("eval/manifests/sot-2176-blind-holdout.json")
    seeds = set(manifest["isolation"]["holdout_seeds"])
    prior = set(range(2174101, 2174104))
    prior.update(range(2175101, 2175103))
    prior.update(range(2175201, 2175206))
    prior.update(range(2118101, 2118121))
    assert seeds.isdisjoint(prior)
    assert len(seeds) == 20
    assert manifest["isolation"]["seat_reversal"] is True


def test_blind_holdout_summary_matches_raw_reports() -> None:
    summary = load_json("artifacts/sot-2176-summary.json")
    reports = [
        load_json(f"artifacts/sot-2176/holdout-{opponent}.json")
        for opponent in ("matsu", "take", "ume")
    ]
    assert sum(report["wins_semantic"] for report in reports) == summary["pool"]["wins"]
    assert sum(report["wins_opp"] for report in reports) == summary["pool"]["losses"]
    assert sum(report["faults_semantic"] for report in reports) == 0
    assert sum(report["unfinished"] for report in reports) == 0
    assert summary["decision"]["champion_behavior_changed"] is False
