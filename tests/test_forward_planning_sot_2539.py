import json
from pathlib import Path

import pytest

from agents.planner import MctsPlanner, PlannerConfig
from scripts.evaluate_forward_planning_sot_2539 import compare


def test_candidate_is_default_disabled_and_eval_guarded(monkeypatch) -> None:
    monkeypatch.delenv("PTCG_TELEMETRY_PROTOCOL", raising=False)
    monkeypatch.setenv("PTCG_FORCED_ROOT_EXPLORATION_CANDIDATE", "1")
    assert PlannerConfig().forced_root_exploration is False
    monkeypatch.setenv("PTCG_TELEMETRY_PROTOCOL", "1")
    assert PlannerConfig().forced_root_exploration is True


def test_forced_root_exploration_visits_each_legal_branch_stably() -> None:
    class Node:
        actor = 0
        priors = [0.99, 0.005, 0.005]
        edges = [[[0], None, 8, 4.0], [[1], None, 0, 0.0], [[2], None, 0, 0.0]]

    planner = object.__new__(MctsPlanner)
    planner.config = PlannerConfig(forced_root_exploration=True)
    assert planner._select_edge(Node(), 0, depth=0)[0] == [1]
    assert planner._select_edge(Node(), 0, depth=1)[0] == [0]


def test_manifest_audits_source_privacy_budget_and_disjoint_gate() -> None:
    manifest = json.loads(Path("eval/manifests/sot-2539-forward-planning.json").read_text())
    source = json.loads(Path(manifest["sourceContract"]).read_text())
    opponent = next(row for row in source["opponents"] if row["id"] == "search-alakazam-v12")
    assert manifest["source"]["version"] == opponent["sourceVersion"]
    assert manifest["source"]["license"] == opponent["license"]
    assert manifest["source"]["executablePolicySha256"] == opponent["policySha256"]
    assert manifest["candidate"]["budgetDelta"] == 0
    assert manifest["candidate"]["defaultEnabled"] is False
    assert all(not manifest["candidate"][key] for key in ("hiddenFeatures", "identityFeatures", "externalWeights"))
    assert set(manifest["phases"]["screen"]["opponents"]).isdisjoint(manifest["phases"]["confirm"]["opponents"])
    assert manifest["phases"]["screen"]["baseSeed"] != manifest["phases"]["confirm"]["baseSeed"]
    assert manifest["promotionGate"]["screenBeforeConfirm"] is True
    assert manifest["kaggleSubmissionAllowed"] is False


def test_gate_requires_strict_pool_and_no_slice_or_runtime_regression() -> None:
    summary = {
        "opponents": {"a": {"winRate": 0.5}},
        "seats": {"0": {"winRate": 0.5}, "1": {"winRate": 0.5}},
        "pool": {"wins": 1, "faults": 0, "unfinished": 0, "runtimeSeconds": {"mean": 10.0, "max": 20.0}},
    }
    gate = {"faultsMax": 0, "unfinishedMax": 0, "meanRuntimeRatioMax": 1.1, "matchRuntimeSecondsMaxExclusive": 600}
    assert compare(summary, summary, gate)["passed"] is False
    candidate = json.loads(json.dumps(summary))
    candidate["pool"]["wins"] = 2
    assert compare(summary, candidate, gate)["passed"] is True


def test_confirm_refuses_failed_screen(tmp_path) -> None:
    receipt = tmp_path / "screen.json"
    receipt.write_text('{"phase":"screen","gate":{"passed":false}}')
    assert json.loads(receipt.read_text())["gate"]["passed"] is False
