# SOT-2240 public-state action-regret diagnosis

## Frozen experiment

The retained SOT-2233 champion behavior (`fd09f65`), matsu/Claude opponent commits and decks,
unused validation seeds `2240101..2240103`, seat reversal, four sampled worlds, 0.8-second root
budget, six-action cap, and one-root-decision counterfactual horizon were fixed in
`eval/manifests/sot-2240-public-action-regret.json`. The new validation run completed six matches per
opponent with zero semantic faults and zero unfinished matches. This issue performs diagnosis only:
it neither promotes a candidate nor changes champion behavior.

## Reproducible telemetry

The analyzer reads the frozen SOT-2233 losing-match real-engine traces and records 205 branching
decision points. Every row contains the legal action candidates observed across the same four sampled
worlds, the selected action, candidate outcome means, selected-vs-best action-regret, seat/seed/step,
and a SHA-256 fingerprint of an explicit public-state allowlist. Hidden hand identities, deck order,
world fingerprints, and opponent identity are absent from features and branching.

## Exclusive clusters and effect sizes

The largest common cluster is midgame setup under an active-energy deficit (support 18, positive
regret support 10, mean regret 0.0395, max 0.2748). Early-game setup under a bench deficit is also
common (support 37, positive 20, mean 0.0249, max 0.2652). The largest opponent-specific cluster is
matsu midgame setup in otherwise neutral public tempo (support 8, positive 2, mean 0.0571, max
0.4455). Classification is exclusive across turn phase, chosen action type, and one public tempo
factor; the full distribution is in `artifacts/sot-2240-summary.json`.

## Next independent hypotheses

1. `mid-active-energy-deficit-leaf-penalty`: one bounded leaf penalty only for the public midgame
   active-slot energy deficit. This is narrower than SOT-2232's generic board/readiness weights.
2. `early-bench-deficit-setup-priority`: one setup-ordering change only for an early public bench
   deficit, a different action point from energy evaluation.
3. `matsu-mid-neutral-root-tiebreak`: one public phase/tempo root tiebreak for the isolated midgame
   cluster. Opponent identity must not be an input despite the evidence currently being matsu-specific.

Each hypothesis is one change and must pass the inherited fixed-pool, seat-reversed small-N screen,
then an independent-seed large-N confirm. This diagnosis does not promote any hypothesis.

## Reproduction

```bash
.venv/bin/python scripts/analyze_public_action_regret.py \
  eval/manifests/sot-2240-public-action-regret.json \
  --output artifacts/sot-2240-summary.json
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
.venv/bin/python scripts/verify_submission_exec.py
```
