import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.evaluator import HeuristicEvaluator  # noqa: E402


def player(active_energy: int, bench_energy: int = 0):
    card = lambda n: SimpleNamespace(hp=100, energies=[object()] * n)  # noqa: E731
    return SimpleNamespace(
        prize=[object()] * 6,
        active=[card(active_energy)],
        bench=[card(bench_energy)] if bench_energy else [],
        handCount=5,
        deckCount=30,
    )


def observation(left, right):
    return SimpleNamespace(current=SimpleNamespace(result=-1, players=[left, right]))


def test_active_energy_candidate_uses_only_public_active_attachments() -> None:
    baseline = HeuristicEvaluator()
    candidate = HeuristicEvaluator({"active_energy": 0.2})
    obs = observation(player(2), player(1))
    assert candidate.evaluate(obs, 0) > baseline.evaluate(obs, 0)


def test_board_energy_candidate_rewards_public_setup() -> None:
    baseline = HeuristicEvaluator()
    candidate = HeuristicEvaluator({"energy": 0.4})
    obs = observation(player(1, 2), player(1))
    assert candidate.evaluate(obs, 0) > baseline.evaluate(obs, 0)


def test_manifest_excludes_rejected_world_aggregation() -> None:
    manifest = Path("eval/manifests/sot-2175-seat-tempo.json").read_text()
    assert "median or trimmed-mean world aggregation" in manifest
