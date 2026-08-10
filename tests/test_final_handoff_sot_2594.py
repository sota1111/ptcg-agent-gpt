import copy
import json
import tarfile
from pathlib import Path

import pytest

from scripts.freeze_final_handoff_sot_2594 import ROOT, audit_archive, freeze

HANDOFF = ROOT / "artifacts/sot-2594/handoff.json"


def test_handoff_freezes_two_distinct_exec_compatible_slots(tmp_path: Path) -> None:
    result = freeze(tmp_path)
    assert [slot["issue"] for slot in result["slots"]] == ["SOT-2556", "SOT-2574"]
    assert len({slot["contentSha256"] for slot in result["slots"]}) == 2
    assert all(all(slot["checks"].values()) for slot in result["slots"])
    assert result["slots"][0]["newArtifact"] is False
    assert result["slots"][1]["newArtifact"] is True


def test_committed_handoff_is_parent_only_and_fail_closed() -> None:
    handoff = json.loads(HANDOFF.read_text())
    assert handoff["submission"]["kaggleSubmittedByChild"] is False
    assert handoff["submission"]["authorizedIssue"] == "SOT-2591"
    assert handoff["submission"]["childDecision"] == "hold"
    assert handoff["submission"]["dropDeadUtc"] == "2026-08-16T21:29:00Z"
    assert handoff["checklist"]["completeForParentDecision"] is True


def test_corrupt_missing_stale_and_duplicate_inputs_are_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing.tar.gz"
    with pytest.raises(FileNotFoundError):
        audit_archive(missing)
    corrupt = tmp_path / "corrupt.tar.gz"
    corrupt.write_bytes(b"not an archive")
    with pytest.raises(tarfile.ReadError):
        audit_archive(corrupt)
    handoff = json.loads(HANDOFF.read_text())
    stale = copy.deepcopy(handoff)
    stale["slots"][1]["contentSha256"] = stale["slots"][0]["contentSha256"]
    assert len({slot["contentSha256"] for slot in stale["slots"]}) != 2
    incomplete = copy.deepcopy(handoff)
    incomplete["checklist"]["completeForParentDecision"] = False
    assert not incomplete["checklist"]["completeForParentDecision"]
