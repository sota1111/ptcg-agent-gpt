import json
from pathlib import Path

import pytest

from scripts.evaluate_reanchoring import evaluate, summarize_reports

MANIFEST = Path("eval/manifests/sot-2399-lb-reanchoring.json")


def _report(opponent: str, wins: tuple[bool, bool], seed: int = 2399101) -> dict:
    return {
        "opponent": opponent,
        "base_seed": seed,
        "seeds": 1,
        "faults_semantic": 0,
        "unfinished": 0,
        "matches": [
            {"semantic_seat": seat, "semantic_won": win, "runtime_s": 1.0 + seat}
            for seat, win in enumerate(wins)
        ],
    }


def _write_reports(tmp_path: Path, wins: tuple[bool, bool]) -> list[Path]:
    manifest = json.loads(MANIFEST.read_text())
    paths = []
    for opponent in manifest["opponents"]:
        path = tmp_path / f"{opponent['id']}.json"
        path.write_text(json.dumps(_report(opponent["id"], wins)))
        paths.append(path)
    return paths


def test_manifest_freezes_old_and_reanchoring_pool_with_disjoint_seeds() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert [row["id"] for row in manifest["opponents"]] == [
        "matsu",
        "take",
        "ume",
        "claude",
        "obo",
        "meta-proxy",
    ]
    assert manifest["phases"]["screen"]["baseSeed"] != manifest["phases"]["confirm"]["baseSeed"]
    assert manifest["promotionGate"]["confirmOnlyAfterScreenPass"] is True
    assert manifest["kaggleSubmissionAllowed"] is False


def test_summary_is_machine_readable_by_opponent_seat_worst_fault_and_runtime(
    tmp_path: Path,
) -> None:
    manifest = json.loads(MANIFEST.read_text())
    summary = summarize_reports(manifest, "screen", _write_reports(tmp_path, (True, False)))
    assert set(summary["opponents"]) == {row["id"] for row in manifest["opponents"]}
    assert set(summary["seats"]) == {"0", "1"}
    assert summary["worstMatchup"]["opponent"] in summary["opponents"]
    assert summary["pool"]["faults"] == summary["pool"]["unfinished"] == 0
    assert set(summary["pool"]["runtimeSeconds"]) == {"mean", "p95", "max"}


def test_failed_screen_retains_champion_and_confirm_is_never_opened(tmp_path: Path) -> None:
    reports = _write_reports(tmp_path, (True, False))
    decision = evaluate(MANIFEST, "screen", reports, reports)
    assert decision["gate"]["passed"] is False
    assert decision["nextPhase"] is None
    assert decision["candidateBehaviorRevertedOnFailure"] is True
    screen_path = tmp_path / "screen.json"
    screen_path.write_text(json.dumps(decision))
    with pytest.raises(ValueError, match="confirm is forbidden"):
        evaluate(MANIFEST, "confirm", reports, reports, screen_path)
