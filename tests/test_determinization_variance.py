import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "determinization_variance", ROOT / "scripts" / "analyze_determinization_variance.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def match(won: bool, seat: int) -> dict:
    return {
        "agent_seed": 2116101,
        "semantic_seat": seat,
        "semantic_won": won,
        "winner": "semantic" if won else "hard",
        "unfinished": False,
        "fault": None,
        "runtime_s": 1.0,
        "determinization_telemetry": [
            {
                "generated_worlds": 4,
                "selected_action_index": 0,
                "world_roots": [
                    {
                        "fingerprint": f"world-{index}",
                        "actions": [
                            {"visits": 2, "value_mean": value},
                            {"visits": 1, "value_mean": 1.0 - value},
                        ],
                    }
                    for index, value in enumerate((0.1, 0.8, 0.2, 0.9))
                ],
            }
        ],
    }


def test_analysis_is_deterministic_and_classifies_outlier_sensitivity(tmp_path: Path) -> None:
    (tmp_path / "hard.json").write_text(
        json.dumps({"matches": [match(False, 0), match(True, 1)]})
    )
    manifest = {
        "issue": "TEST-1",
        "provenance": {"champion_commit": "abc"},
        "evaluation": {"agent_seeds": [2116101]},
        "opponents": [{"id": "hard", "report": "hard.json"}],
        "explicit_exclusions": ["n_worlds"],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))

    first = MODULE.analyze(path)
    assert first == MODULE.analyze(path)
    assert first["classified_losses"][0]["category"] == (
        "world_aggregation_outlier_sensitivity"
    )
    assert first["champion_behavior_changed"] is False
