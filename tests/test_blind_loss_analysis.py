import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "blind_loss_analysis", ROOT / "scripts" / "analyze_blind_losses.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def match(*, won: bool, seat: int, seed: int, branching: int = 0, deck: int = 10) -> dict:
    return {
        "agent_seed": seed,
        "semantic_seat": seat,
        "semantic_won": won,
        "winner": "semantic" if won else "hard",
        "unfinished": False,
        "fault": None,
        "steps": 42,
        "runtime_s": 2.0,
        "think_s": {"semantic": 1.0, "hard": 0.5},
        "semantic_telemetry": {
            "decisions": 10,
            "branching_decisions": branching,
            "max_options": 9 if branching else 3,
            "min_deck_count": deck,
            "min_prize_count": 3,
        },
        "semantic_contexts": {"0": 10},
        "final": {
            "semantic": {"deck_count": deck, "prize_count": 3},
            "hard": {"deck_count": 12, "prize_count": 4},
        },
    }


def test_analysis_is_reproducible_and_classifies_observable_loss(tmp_path: Path) -> None:
    report = {
        "matches": [
            match(won=False, seat=0, seed=101, branching=4),
            match(won=True, seat=1, seed=101),
        ]
    }
    report_path = tmp_path / "hard.json"
    report_path.write_text(json.dumps(report))
    manifest = {
        "issue": "TEST-1",
        "provenance": {"champion_commit": "abc", "deck_sha256": "def"},
        "evaluation": {"seat_reversal": True, "agent_seeds": [101]},
        "opponents": [{"id": "hard", "report": "hard.json"}],
        "explicit_exclusions": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    first = MODULE.analyze(manifest_path)
    second = MODULE.analyze(manifest_path)

    assert first == second
    assert first["classification"]["largest_bottleneck"] == "candidate_prior_or_pruning"
    assert first["evaluation"]["unclassified_rate"] == 0
    assert first["champion_behavior_changed"] is False
