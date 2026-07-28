import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "analyze_world_aggregation.py"


def _module():
    spec = importlib.util.spec_from_file_location("world_aggregation_analysis", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_summarize_reports_pool_seat_fault_and_runtime(tmp_path):
    reports = []
    for opponent, first_won, second_won in (("matsu", True, False), ("take", True, True)):
        path = tmp_path / f"{opponent}.json"
        path.write_text(
            json.dumps(
                {
                    "opponent": opponent,
                    "wins_semantic": int(first_won) + int(second_won),
                    "wins_opp": 2 - int(first_won) - int(second_won),
                    "faults_semantic": 0,
                    "unfinished": 0,
                    "max_think_s": {"semantic": 2.0},
                    "matches": [
                        {
                            "semantic_first": True,
                            "semantic_won": first_won,
                            "runtime_s": 3.0,
                        },
                        {
                            "semantic_first": False,
                            "semantic_won": second_won,
                            "runtime_s": 5.0,
                        },
                    ],
                }
            )
        )
        reports.append(path)

    result = _module().summarize(reports)
    assert result["pool_kpi"] == 0.75
    assert result["seat"]["paired_gap"] == 0.5
    assert result["runtime_s"]["mean"] == 4.0
    assert result["faults"] == result["timeouts"] == 0
