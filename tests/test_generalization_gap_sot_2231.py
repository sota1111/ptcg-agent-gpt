import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2231-generalization-gap.json")
SPEC = importlib.util.spec_from_file_location(
    "generalization_gap", Path("scripts/analyze_generalization_gap.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_freezes_unknown_submission_fingerprints_without_guessing() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert (
        manifest["champion"]["main_sha256"]
        == "043fa98468f10dc1d4490df6ef2c908866fa77bdd1bcd61fab4a73f873d62816"
    )
    assert (
        manifest["champion"]["deck_sha256"]
        == "e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997"
    )
    assert all(row["source_commit"] == "unknown" for row in manifest["submissions"])
    assert [row["public_score"] for row in manifest["submissions"]] == [571.7, 557.9, 521.0]


def test_diversified_traces_are_complete_public_and_seat_reversed() -> None:
    manifest = json.loads(MANIFEST.read_text())
    expected_seeds = set(manifest["seed_policy"]["seeds"])
    for opponent in manifest["diversified_pool"]:
        path = (MANIFEST.parent / opponent["report"]).resolve()
        report = json.loads(path.read_text())
        assert report["faults_semantic"] == 0
        assert report["unfinished"] == 0
        assert {row["agent_seed"] for row in report["matches"]} == expected_seeds
        assert all(
            {row["semantic_seat"] for row in report["matches"] if row["agent_seed"] == seed}
            == {0, 1}
            for seed in expected_seeds
        )
        assert all(
            "fingerprint" not in root
            for row in report["matches"]
            for event in row["determinization_telemetry"]
            for root in event.get("world_roots", [])
        )


def test_summary_reproduces_gap_and_exclusive_loss_classification() -> None:
    summary = MODULE.analyze(MANIFEST)
    pool = summary["diversified_pool"]
    assert pool["matches"] == 20
    assert pool["wins"] + pool["losses"] == 20
    assert summary["generalization_gap_pp"] == 7.5
    assert sum(summary["loss_explanations"]["counts"].values()) == pool["losses"]
    assert len(summary["candidates"]) == 3
    assert summary["champion_behavior_changed"] is False
    assert summary["hidden_information_leakage"] is False
