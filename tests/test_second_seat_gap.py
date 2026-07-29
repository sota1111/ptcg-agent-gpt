import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATTLE_SPEC = importlib.util.spec_from_file_location("battle_vs", ROOT / "eval" / "battle_vs.py")
assert BATTLE_SPEC and BATTLE_SPEC.loader
BATTLE_MODULE = importlib.util.module_from_spec(BATTLE_SPEC)
BATTLE_SPEC.loader.exec_module(BATTLE_MODULE)

SPEC = importlib.util.spec_from_file_location(
    "second_seat_gap", ROOT / "scripts" / "analyze_second_seat_gap.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _match(seat: int, won: bool, energy_delta: int = 0) -> dict:
    return {
        "agent_seed": 2174101,
        "semantic_seat": seat,
        "semantic_won": won,
        "winner": "semantic" if won else "hard",
        "fault": None,
        "unfinished": False,
        "runtime_s": 1.0,
        "determinization_telemetry": [
            {
                "selected_action_index": 0,
                "world_roots": [{"actions": [{"visits": 1, "value_mean": 0.4}]}],
                "public_state": {
                    "turn_index": 3,
                    "turn_action_count": 2,
                    "selection_context": 0,
                    "hand_count_delta": 0,
                    "bench_count_delta": 0,
                    "prize_count_delta": 0,
                    "own": {
                        "board_energy_count": max(energy_delta, 0),
                        "active_energy_count": max(energy_delta, 0),
                    },
                    "opponent": {
                        "board_energy_count": max(-energy_delta, 0),
                        "active_energy_count": max(-energy_delta, 0),
                    },
                    "energy_attachment_available": False,
                    "attack_ready": False,
                    "selected_end_turn": True,
                    "selected_attack": False,
                },
            }
        ],
    }


def test_public_snapshot_excludes_hidden_card_identity() -> None:
    obs = {
        "select": {"context": 0, "option": [{"type": 13}, {"type": 14}]},
        "search_begin_input": "hidden-engine-state",
        "current": {
            "turn": 4,
            "turnActionCount": 3,
            "energyAttached": True,
            "players": [
                {
                    "handCount": 7,
                    "hand": [{"id": 999}],
                    "prize": [None] * 5,
                    "deckCount": 40,
                    "discard": [{"id": 1}],
                    "active": [{"id": 10, "energies": [3]}],
                    "bench": [],
                },
                {
                    "handCount": 4,
                    "hand": None,
                    "prize": [None] * 6,
                    "deckCount": 42,
                    "discard": [],
                    "active": [{"id": 20, "energies": []}],
                    "bench": [],
                },
            ],
        },
    }
    snapshot = BATTLE_MODULE.public_decision_snapshot(obs, 0, [1])
    encoded = json.dumps(snapshot)
    assert "999" not in encoded
    assert "hidden-engine-state" not in encoded
    assert snapshot["attack_ready"] is True
    assert snapshot["selected_end_turn"] is True


def test_public_telemetry_removes_hidden_world_fingerprints() -> None:
    contestant = BATTLE_MODULE.Contestant("test", ".", 1, public_telemetry_only=True)
    contestant.last_telemetry = {
        "world_roots": [{"fingerprint": "hidden", "actions": [{"visits": 1}]}]
    }
    assert contestant.telemetry() == {"world_roots": [{"actions": [{"visits": 1}]}]}


def test_analysis_is_deterministic_and_exclusive(tmp_path: Path) -> None:
    report = {"matches": [_match(0, True), _match(1, False, -1)]}
    (tmp_path / "hard.json").write_text(json.dumps(report))
    manifest = {
        "issue": "TEST-1",
        "provenance": {"champion_commit": "abc"},
        "evaluation": {"agent_seeds": [2174101]},
        "opponents": [{"id": "hard", "report": "hard.json"}],
        "explicit_exclusions": ["world aggregation"],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))

    first = MODULE.analyze(path)
    assert first == MODULE.analyze(path)
    assert first["classified_second_seat_losses"][0]["category"] == "setup/energy tempo"
    assert sum(first["classification"]["counts"].values()) == 1
    assert first["telemetry_contract"]["hidden_information_leakage"] is False
