import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2254-selective-lookahead.json")
SPEC = importlib.util.spec_from_file_location(
    "lookahead", Path("scripts/analyze_selective_lookahead_sot_2254.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_freezes_terminal_provenance_unused_seeds_and_both_seats() -> None:
    data = json.loads(MANIFEST.read_text())
    assert data["preregistered_before_experiment"] is True
    assert data["fixed_conditions"]["seeds"] == [2254101, 2254102, 2254103]
    assert data["fixed_conditions"]["seat_reversal"] is True
    assert [row["id"] for row in data["opponents"]] == ["matsu", "claude"]


def test_real_traces_are_complete_paired_and_use_public_protocol() -> None:
    data = json.loads(MANIFEST.read_text())
    for opponent in data["opponents"]:
        report = json.loads((MANIFEST.parent / opponent["report"]).resolve().read_text())
        assert report["base_seed"] == 2254101
        assert report["faults_semantic"] == report["unfinished"] == 0
        for seed in data["fixed_conditions"]["seeds"]:
            assert {m["semantic_seat"] for m in report["matches"] if m["agent_seed"] == seed} == {
                0,
                1,
            }
        assert all(
            "fingerprint" not in root
            for m in report["matches"]
            for e in m["determinization_telemetry"]
            for root in e["world_roots"]
        )


def test_analysis_is_deterministic_allowlisted_and_behavior_preserving() -> None:
    first = MODULE.analyze(MANIFEST)
    second = MODULE.analyze(MANIFEST)
    assert first == second
    allowlist = set(first["privacy_audit"]["allowlist"])
    assert first["sequences"]
    assert all(set(row["public_state"]) <= allowlist for row in first["sequences"])
    assert len(first["candidates"]) <= 3
    assert first["runtime"]["faults"] == first["runtime"]["unfinished"] == 0
    assert first["champion_behavior_changed"] is False
