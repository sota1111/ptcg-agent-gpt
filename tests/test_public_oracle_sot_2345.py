import json
from pathlib import Path

import pytest

from ptcg_agent.runtime_dataset import (
    PUBLIC_FEATURE_ALLOWLIST,
    load_runtime_dataset,
    provenance_fingerprint,
    public_feature_vector,
)
from scripts.build_public_oracle_corpus import diagnostics


def test_public_allowlist_excludes_hidden_and_opponent_identity() -> None:
    state = {
        "turn_index": 3,
        "own": {"hand_count": 4, "deck_count": 40, "prize_count": 5, "hidden": [1]},
        "opponent": {"hand_count": 6, "deck_count": 38, "prize_count": 4},
        "opponent_identity": "must-not-leak",
        "world_fingerprint": "must-not-leak",
    }
    assert len(PUBLIC_FEATURE_ALLOWLIST) == 7
    assert public_feature_vector(state) == (3.0, 4.0, 40.0, 5.0, 6.0, 38.0, 4.0)


def test_provenance_units_separate_seed_seat_and_opponent() -> None:
    fingerprints = {
        provenance_fingerprint(seed, seat, opponent)
        for seed in (1, 2)
        for seat in (0, 1)
        for opponent in ("a", "b")
    }
    assert len(fingerprints) == 8


def test_diagnostics_rejects_split_leakage(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("{}\n", encoding="utf-8")
    rows = [
        {"split": split, "provenanceFingerprint": "same", "value": value, "heuristicValue": 0.5}
        for split, value in (("screen", 0.0), ("confirm", 1.0))
    ]
    result = diagnostics(rows, corpus)
    assert result["splitLeakagePassed"] is False


def test_v2_runtime_corpus_loads_and_validates(tmp_path: Path) -> None:
    row = {
        "schemaVersion": "2.0.0",
        "split": "confirm",
        "features": [1, 2, 3, 4, 5, 6, 7],
        "legalActions": [-1],
        "action": -1,
        "value": 1,
        "heuristicValue": 0.75,
        "provenanceFingerprint": "f" * 64,
    }
    path = tmp_path / "corpus.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    sample = next(load_runtime_dataset(path, "confirm"))
    assert sample.heuristic_value == pytest.approx(0.75)
    assert sample.provenance_fingerprint == "f" * 64


def test_manifest_freezes_independent_screen_confirm_and_no_submission() -> None:
    manifest = json.loads(Path("eval/manifests/sot-2345-public-oracle.json").read_text())
    seeds = [set(value["seeds"]) for value in manifest["splits"].values()]
    assert not (seeds[0] & seeds[1] or seeds[0] & seeds[2] or seeds[1] & seeds[2])
    assert len(manifest["opponents"]) >= 3
    assert manifest["seatReversal"] is True
    assert manifest["promotionContract"]["kaggleSubmission"] is False
