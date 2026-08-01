# SOT-2241 action-regret-targeted policy promotion

## Frozen experiment

The SOT-2240 terminal champion and behavior hashes, deck, search and fallback semantics, unused
screen seeds `2241101..2241102`, independent confirm seeds `2241201..2241205`, five-opponent pool,
seat reversal, three one-change hypotheses, and all promotion gates were committed before the first
match in `eval/manifests/sot-2241-regret-policy-promotion.json`.

Every candidate is gated only by public turn phase and public board counts. No hidden-zone value,
opponent identity, or evaluation-pool identity is an input. Unlike the rejected SOT-2175/SOT-2232
generic readiness axes, these corrections only apply inside the SOT-2240 regret clusters.

## Screen result and decision

The champion and all candidates completed four matches per opponent (two fixed agent seeds, both
seats), 80 real-engine matches total. There were zero semantic faults and zero unfinished games.
Wilson 95% intervals and opponent/seat/runtime breakdowns are recorded in the machine-readable
summary and source reports.

No candidate passed. The active-energy and early-bench candidates tied the champion's diversified
aggregate rather than improving it; both also failed at least one fixed-pool non-regression gate.
The neutral tiebreak regressed both the diversified aggregate and the Claude worst matchup. Therefore
confirm was not run, no candidate was promoted, and the evaluation-only behavior switches were
reverted. The retained champion hash and Kaggle behavior are unchanged.

## Reproduction

```bash
.venv/bin/python scripts/analyze_regret_policy_sot_2241.py \
  eval/manifests/sot-2241-regret-policy-promotion.json \
  --output artifacts/sot-2241-summary.json
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
.venv/bin/python scripts/verify_submission_exec.py
```
