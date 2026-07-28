from types import SimpleNamespace

import pytest

from agents.planner import MctsPlanner


def _world(edges):
    return SimpleNamespace(root=SimpleNamespace(edges=edges))


def test_robust_aggregation_rejects_single_high_visit_outlier():
    candidates = [[0], [1]]
    worlds = [
        _world([(None, None, 97, 0.0), (None, None, 3, 3.0)]),
        _world([(None, None, 1, 0.0), (None, None, 9, 9.0)]),
        _world([(None, None, 1, 0.0), (None, None, 9, 9.0)]),
        _world([(None, None, 1, 0.0), (None, None, 9, 9.0)]),
    ]

    assert MctsPlanner._best_action(candidates, worlds, world_aggregation="sum") == [0]
    assert MctsPlanner._best_action(candidates, worlds, world_aggregation="median") == [1]
    assert MctsPlanner._best_action(candidates, worlds, world_aggregation="trimmed_mean") == [1]


def test_unknown_world_aggregation_is_rejected():
    with pytest.raises(ValueError, match="unknown world aggregation"):
        MctsPlanner._best_action([[0]], [], world_aggregation="mode")
