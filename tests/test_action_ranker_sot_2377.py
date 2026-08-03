import hashlib
import importlib.util
import json
from pathlib import Path

ORACLE = Path("artifacts/sot-2376-public-counterfactual-oracle/oracle.jsonl")
MODEL = Path("artifacts/sot-2377-action-ranking/public_action_ranker.json")
MANIFEST = Path("eval/manifests/sot-2377-action-ranking.json")
SPEC = importlib.util.spec_from_file_location(
    "train_pairwise_action_ranker", Path("scripts/train_pairwise_action_ranker.py")
)
assert SPEC and SPEC.loader
TRAINER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAINER)


def test_model_is_train_only_and_pins_oracle_fingerprint() -> None:
    manifest = json.loads(MANIFEST.read_text())
    model = json.loads(MODEL.read_text())
    assert model["trainingSplit"] == "train"
    assert model["oracleSha256"] == manifest["oracle"]["sha256"]
    assert hashlib.sha256(ORACLE.read_bytes()).hexdigest() == model["oracleSha256"]
    assert model["trainingRows"] == sum(
        json.loads(line)["split"] == "train" for line in ORACLE.read_text().splitlines()
    )


def test_training_is_deterministic_except_timestamp() -> None:
    expected = json.loads(MODEL.read_text())
    rebuilt = TRAINER.train(ORACLE, expected["oracleSha256"])
    rebuilt["trainedAt"] = expected["trainedAt"]
    assert rebuilt == expected


def test_model_excludes_forbidden_information() -> None:
    model = json.loads(MODEL.read_text())
    encoded = json.dumps({"scores": [model["globalScores"], model["contextScores"]]})
    for forbidden in model["forbiddenFeatures"]:
        assert forbidden not in encoded
    assert model["featureContract"] == ["selection_context", "legal_action_option_types"]


def test_rejected_candidate_is_not_in_submission_behavior() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["kaggleSubmission"] is False
    assert "PTCG_ACTION_RANKER_MODEL" not in Path("main.py").read_text()
    assert "root_prior_model" not in Path("agents/planner.py").read_text()


def test_screen_rejects_candidate_and_skips_confirm() -> None:
    decision = json.loads(
        Path("artifacts/sot-2377-action-ranking/screen-decision.json").read_text()
    )
    assert decision["passed"] is False
    assert decision["confirmRequired"] is False
    assert decision["promoted"] is False
    assert decision["championBehaviorChanged"] is False
    assert decision["kaggleSubmissionPerformed"] is False
    assert decision["results"]["candidate"]["all"]["faults"] == 0
    assert decision["results"]["candidate"]["all"]["unfinished"] == 0
