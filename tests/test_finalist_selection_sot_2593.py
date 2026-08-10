from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.select_finalists_sot_2593 import select

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "artifacts/sot-2592/finalist-inventory.json"
SELECTION = ROOT / "artifacts/sot-2593/finalist-selection.json"


def test_selection_is_deterministic_and_matches_frozen_manifest() -> None:
    actual = select(INVENTORY, ROOT)
    assert actual == json.loads(SELECTION.read_text(encoding="utf-8"))
    assert actual["decision"] == {
        "primary": "SOT-2556",
        "hedge": "SOT-2574",
        "reason": actual["decision"]["reason"],
    }


def test_primary_uses_pessimistic_cv_and_hedge_is_independent() -> None:
    result = select(INVENTORY, ROOT)
    primary, hedge = result["selected"]
    assert primary["cv"]["wilson95"][0] > hedge["cv"]["wilson95"][0]
    assert primary["strategyLineage"] != hedge["strategyLineage"]
    assert primary["fingerprint"]["contentSha256"] != hedge["fingerprint"]["contentSha256"]
    assert result["selectionContract"]["publicResultPolicy"] == "sanity_only_null_never_imputed"
    assert all(candidate["public"]["rating"] is None for candidate in result["selected"])


def test_worst_case_runtime_and_reliability_are_explicit() -> None:
    for candidate in select(INVENTORY, ROOT)["selected"]:
        risk = candidate["risk"]
        assert risk["worstMatchup"]["matches"] > 0
        assert risk["worstSeat"]["matches"] > 0
        assert set(risk["runtimeSeconds"]) == {"mean", "p95", "max"}
        assert risk["reliability"] == {"faults": 0, "illegalActions": 0, "unfinished": 0}


@pytest.mark.parametrize("field", ["strategyLineage", "fingerprint"])
def test_selection_fails_closed_without_independent_hedge(tmp_path: Path, field: str) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    primary, hedge = [
        row for row in inventory["auditedTerminalArtifacts"] if row["status"] == "finalist"
    ]
    if field == "strategyLineage":
        hedge[field] = primary[field]
    else:
        hedge[field]["contentSha256"] = primary[field]["contentSha256"]
    changed = tmp_path / "inventory.json"
    changed.write_text(json.dumps(inventory), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match="independent hedge|strategy lineages must be unique|content fingerprint mismatch",
    ):
        select(changed, ROOT)


def test_child_contract_prohibits_submission_and_new_experiments() -> None:
    contract = select(INVENTORY, ROOT)["selectionContract"]
    assert contract["kaggleSubmissionAllowed"] is False
    assert contract["retrainingAllowed"] is False
    assert contract["rejectedAxisRetryAllowed"] is False
