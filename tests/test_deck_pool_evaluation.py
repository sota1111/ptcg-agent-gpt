from pathlib import Path

import pytest

from ptcg_agent.deck_pool_evaluation import finalize_pool, summarize_reports


def _report(opponent: str, wins: tuple[bool, bool, bool, bool]) -> dict:
    matches = []
    for index, won in enumerate(wins):
        matches.append(
            {
                "agent_seed": 100 + index // 2,
                "semantic_first": index % 2 == 0,
                "semantic_won": won,
                "winner": "semantic" if won else opponent,
                "steps": 20 + index,
                "fault": None,
                "unfinished": False,
            }
        )
    return {"opponent": opponent, "archetype": f"{opponent}-archetype", "matches": matches}


def _deck(path: Path, card: int) -> Path:
    path.write_text("\n".join(map(str, [card] * 60)) + "\n")
    return path


def test_summary_records_required_metrics_by_seat_and_archetype() -> None:
    result = summarize_reports(
        [_report("top", (True, False, True, True)), _report("counter", (False,) * 4)]
    )
    assert result["seeds"] == [100, 101]
    assert result["overall"] == {
        "matches": 8,
        "wins": 3,
        "losses": 5,
        "draws": 0,
        "winRate": 0.375,
        "averageDecisions": 21.5,
        "averageTurns": 10.75,
        "invalidActions": 0,
        "errors": 0,
    }
    assert result["bySeat"]["first"]["matches"] == 4
    assert result["bySeat"]["second"]["matches"] == 4
    assert result["byOpponent"]["top"]["winRate"] == 0.75
    assert result["byArchetype"]["top-archetype"]["winRate"] == 0.75
    assert result["byArchetype"]["counter-archetype"]["winRate"] == 0.0


def test_summary_rejects_single_seed() -> None:
    report = _report("top", (True, False, True, False))
    for match in report["matches"]:
        match["agent_seed"] = 100
    with pytest.raises(ValueError, match="multiple seeds"):
        summarize_reports([report])


def test_final_pool_is_bounded_and_records_every_reason(tmp_path: Path) -> None:
    baseline = _deck(tmp_path / "baseline.csv", 1)
    duplicate = _deck(tmp_path / "duplicate.csv", 1)
    winner = _deck(tmp_path / "winner.csv", 2)
    extra = _deck(tmp_path / "extra.csv", 3)
    result = finalize_pool(
        baseline=baseline,
        candidates=[
            ("duplicate", duplicate, ("top",)),
            ("winner", winner, ("emerging", "diversity")),
            ("extra", extra, ("counter",)),
        ],
        evaluations={
            key: {"overall": {"winRate": 0.75, "invalidActions": 0, "errors": 0}}
            for key in ("duplicate", "winner", "extra")
        },
        max_additions=1,
    )
    assert result["beforeCount"] == 1
    assert result["afterCount"] == 2
    by_id = {row["id"]: row for row in result["decisions"]}
    assert by_id["baseline"]["decision"] == "keep"
    assert by_id["duplicate"]["decision"] == "remove"
    assert by_id["winner"]["decision"] == "add"
    assert by_id["extra"]["reason"] == "bounded replacement limit reached"
    assert all(row["reason"] for row in result["decisions"])
