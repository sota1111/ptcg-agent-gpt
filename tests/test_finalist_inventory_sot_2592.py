from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_finalist_inventory_sot_2592 import audit

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "artifacts/sot-2592/finalist-inventory.json"


def test_frozen_inventory_passes_full_provenance_audit() -> None:
    result = audit(INVENTORY, ROOT)
    assert result == {
        "issue": "SOT-2592",
        "audited": 4,
        "finalists": ["SOT-2556", "SOT-2574"],
        "status": "PASS",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("isolation", {"entity": 0, "time": 0, "seed": 0}, "incomplete isolation"),
        ("public", {"rating": 723.4, "submissionId": None, "observedAt": None}, "explicit null"),
    ],
)
def test_audit_fails_closed_on_incomparable_or_imputed_data(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    inventory["auditedTerminalArtifacts"][2][field] = value
    changed = tmp_path / "inventory.json"
    changed.write_text(json.dumps(inventory), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        audit(changed, ROOT)


def test_audit_detects_source_artifact_mutation(tmp_path: Path) -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    inventory["auditedTerminalArtifacts"][2]["sha256"]["summary"] = "0" * 64
    changed = tmp_path / "inventory.json"
    changed.write_text(json.dumps(inventory), encoding="utf-8")
    with pytest.raises(ValueError, match="provenance hash mismatch"):
        audit(changed, ROOT)
