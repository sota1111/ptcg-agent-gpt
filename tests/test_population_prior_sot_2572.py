import hashlib
import json
import subprocess
from pathlib import Path

from agents.observation import OptionView, SelectView, SideView, View
from agents.planner import MctsPlanner, PlannerConfig
from agents.population_prior import PopulationPrior

ROOT = Path(__file__).resolve().parents[1]


def side(*, discard=(), prizes=6, active=(), bench=()):
    return SideView(
        active=list(active),
        bench=list(bench),
        bench_max=5,
        deck_count=40,
        hand_count=5,
        hand_card_ids=None,
        discard_card_ids=list(discard),
        prize_count=prizes,
        prize_known_ids=[],
    )


def view(option_types=(7, 13, 14), opp_discard=()):
    select = SelectView(
        type=0,
        context=0,
        min_count=1,
        max_count=1,
        remain_damage_counter=0,
        remain_energy_cost=0,
        options=[OptionView(i, kind, {}) for i, kind in enumerate(option_types)],
        deck_card_ids=None,
        context_card_id=None,
        effect_card_id=None,
    )
    return View(
        your_index=0,
        turn=4,
        turn_action_count=1,
        first_player=0,
        result=-1,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        stadium_card_ids=[],
        looking_card_ids=None,
        me=side(prizes=5),
        opp=side(discard=opp_discard, prizes=6),
        select=select,
        logs=[],
        raw={},
    )


def test_candidate_is_default_disabled_and_double_gated(monkeypatch):
    monkeypatch.delenv("PTCG_TELEMETRY_PROTOCOL", raising=False)
    monkeypatch.delenv("PTCG_POPULATION_PRIOR_CANDIDATE", raising=False)
    assert PlannerConfig().population_prior is False
    monkeypatch.setenv("PTCG_POPULATION_PRIOR_CANDIDATE", "1")
    assert PlannerConfig().population_prior is False
    monkeypatch.setenv("PTCG_TELEMETRY_PROTOCOL", "1")
    assert PlannerConfig().population_prior is True


def test_artifact_hash_size_and_public_contract():
    path = ROOT / "agents/population_prior_sot_2572.json"
    model = json.loads(path.read_text())
    expected = model.pop("contentSha256")
    actual = hashlib.sha256(
        json.dumps(model, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert actual == expected
    assert path.stat().st_size < 32_000
    assert model["publicOnly"] is True
    assert model["trainSplitOnly"] is True
    deny = set(model["featureDenylist"])
    assert {"opponent_hidden_hand", "opponent_identity", "hidden_prize_ids"} <= deny


def test_training_is_fixed_seed_reproducible_and_train_only():
    tracked = [
        ROOT / "agents/population_prior_sot_2572.json",
        ROOT / "artifacts/sot-2572/distillation-checkpoint.json",
        ROOT / "artifacts/sot-2572/training-receipt.json",
    ]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
    subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            "scripts/train_population_prior_sot_2572.py",
            "--seed",
            "2572",
        ],
        cwd=ROOT,
        check=True,
    )
    after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
    assert after == before
    checkpoint = json.loads(tracked[1].read_text())
    assert checkpoint["trainSplitOnly"] is True
    assert checkpoint["trainPopulationMembers"] == ["matsu-fixed"]
    assert json.loads(tracked[2].read_text())["kaggleSubmitted"] is False


def test_prior_is_deterministic_and_uses_revealed_archetype_only():
    prior = PopulationPrior()
    first = prior.score_options(view(opp_discard=[673]))
    assert first == prior.score_options(view(opp_discard=[673]))
    assert first != prior.score_options(view(opp_discard=[1102]))
    assert 0.0 <= prior.value(view()) <= 1.0


def test_missing_or_corrupt_artifact_falls_back_neutrally(tmp_path):
    prior = PopulationPrior(tmp_path / "missing.json")
    assert prior.available is False
    assert prior.score_options(view()) == [0.0, 0.0, 0.0]
    bad = tmp_path / "bad.json"
    bad.write_text('{"schemaVersion":"1.0.0","publicOnly":true,"contentSha256":"bad"}')
    assert PopulationPrior(bad).available is False


class Cards:
    pass


def test_opt_in_changes_only_legal_root_prior_order(monkeypatch):
    monkeypatch.setenv("PTCG_TELEMETRY_PROTOCOL", "1")
    monkeypatch.setenv("PTCG_POPULATION_PRIOR_CANDIDATE", "1")
    planner = MctsPlanner([1] * 60, config=PlannerConfig(), card_index=Cards())
    candidates, priors = planner._root_candidates(view(option_types=(14, 12)), object())
    assert sorted(action[0] for action in candidates) == [0, 1]
    assert abs(sum(priors) - 1.0) < 1e-12
