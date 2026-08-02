import importlib.util
import json
from pathlib import Path

MANIFEST = Path("eval/manifests/sot-2280-deck-promotion.json")
SPEC = importlib.util.spec_from_file_location(
    "deck_promotion", Path("scripts/decide_deck_promotion_sot_2280.py")
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _summary(win_rate: float, matsu: float, claude: float, runtime: float = 10.0) -> dict:
    return {
        "win_rate": win_rate,
        "faults": 0,
        "unfinished": 0,
        "runtime_s": {"mean": runtime, "max": runtime},
        "opponents": {"matsu": {"win_rate": matsu}, "claude": {"win_rate": claude}},
    }


def test_manifest_separates_screen_and_confirm_provenance() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["preregistered_before_confirm"] is True
    assert manifest["screen"]["base_seed"] != manifest["confirm"]["base_seed"]
    assert manifest["screen"]["seat_reversal"] is True
    assert manifest["confirm"]["seat_reversal"] is True
    assert manifest["pools"]["fixed"] == ["matsu", "take", "ume"]
    assert manifest["pools"]["diversified"] == ["claude", "obo"]


def test_gate_is_strict_deterministic_and_checks_each_worst_matchup() -> None:
    manifest = json.loads(MANIFEST.read_text())
    champion = _summary(0.5, 0.5, 0.25)
    passing = _summary(0.6, 0.5, 0.25)
    assert MODULE.apply_gate(champion, passing, manifest)["passed"] is True
    assert MODULE.apply_gate(champion, _summary(0.5, 0.5, 0.25), manifest)["passed"] is False
    regressed = MODULE.apply_gate(champion, _summary(0.6, 0.25, 0.5), manifest)
    assert regressed["passed"] is False
    assert "matsu win rate regressed" in regressed["reasons"]
    too_slow = MODULE.apply_gate(champion, _summary(0.6, 0.5, 0.25, 600.0), manifest)
    assert too_slow["passed"] is False


def test_real_screen_is_same_pool_seed_both_seats_and_deterministically_gated() -> None:
    manifest = json.loads(MANIFEST.read_text())
    candidates = json.loads(Path(manifest["source"]["candidate_artifact"]).read_text())[
        "candidates"
    ]
    identities = ["champion", *[row["id"] for row in candidates]]
    results, hashes = MODULE.load_phase(
        manifest,
        identities,
        Path(manifest["source"]["screen_artifact_dir"]),
        "screen",
    )
    decisions = MODULE.phase_decisions(results, identities[1:], manifest)
    assert set(hashes) == {
        f"{manifest['source']['screen_artifact_dir']}/{identity}-vs-{opponent['label']}.json"
        for identity in identities
        for opponent in manifest["opponents"]
    }
    assert decisions["wellspring-bench-pressure"]["passed"] is True
    assert decisions["kyogre-consistency"]["passed"] is False
    assert "matsu win rate regressed" in decisions["kyogre-consistency"]["reasons"]


def test_terminal_decision_matches_deck_hash() -> None:
    path = Path("artifacts/sot-2280-deck-promotion/decision.json")
    assert path.exists()
    decision = json.loads(path.read_text())
    assert decision["champion_changed"] == (decision["promoted"] is not None)
    assert MODULE.sha256(Path("deck.csv")) == decision["champion_deck_sha256_after"]
    assert decision["outcome"] == "champion_retained"
    assert decision["promoted"] is None
    assert decision["confirm"]["decisions"]["wellspring-bench-pressure"]["passed"] is False
