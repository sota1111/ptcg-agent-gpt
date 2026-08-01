import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_holdout_seeds_are_isolated_and_seat_reversed() -> None:
    manifest = load_json("eval/manifests/sot-2256-blind-holdout.json")
    holdout = set(manifest["isolation"]["holdout_seeds"])
    used = (
        set(range(2254101, 2254104)) | set(range(2255101, 2255103)) | set(range(2255201, 2255206))
    )
    assert holdout.isdisjoint(used)
    assert manifest["isolation"]["seat_reversal"] is True
    assert manifest["isolation"]["matches_per_opponent"] == 2 * len(holdout)


def test_terminal_provenance_and_holdout_audit() -> None:
    manifest = load_json("eval/manifests/sot-2256-blind-holdout.json")
    summary = load_json("artifacts/sot-2256-summary.json")
    assert manifest["provenance"]["terminal_identity"] == "champion"
    assert manifest["provenance"]["champion_main_sha256"] == (
        "043fa98468f10dc1d4490df6ef2c908866fa77bdd1bcd61fab4a73f873d62816"
    )
    assert manifest["provenance"]["champion_deck_sha256"] == (
        "e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997"
    )
    assert summary["pool"]["matches"] == 50
    assert summary["pool"]["faults"] == 0
    assert summary["pool"]["unfinished"] == 0
    assert summary["pool"]["illegal_actions"] == 0
    assert summary["pool"]["runtime_s"]["max"] < 600
    assert summary["decision"]["terminal_identity"] == "champion"
    assert summary["decision"]["operational_audit_passed"] is True


def test_submission_record_uniquely_maps_audited_artifact() -> None:
    submission = load_json("artifacts/sot-2256/submission.json")
    assert submission["terminal"]["identity"] == "champion"
    assert submission["holdout"]["operational_audit_passed"] is True
    assert submission["exec_compatibility"]["passed"] is True
    assert submission["fingerprint_gate"]["passed"] is True
    assert submission["submission"]["helper_executed"] is True
    assert submission["submission"]["submitted_this_run"] is False
    assert submission["submission"]["outcome"] == "skip_duplicate_fingerprint"
    assert submission["submission"]["existing_ref"] == "55154527"
    assert submission["submission"]["existing_status"] == "COMPLETE"
    assert submission["submission"]["existing_public_score"] == 529.4
