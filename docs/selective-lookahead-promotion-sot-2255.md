# SOT-2255 selective-lookahead promotion decision

## Frozen experiment

The SOT-2254 diagnosis supplied exactly one candidate,
`bounded-public-setup-continuation`. Commit `5418e86` preregistered and
implemented its sole evaluation-only change: under the unchanged 0.8-second,
four-world, six-root-action budget, tree depth was extended by one edge only
when both the root and continuation actions were public setup actions.

Champion and candidate used the same deck, fallback chain, evaluator weights,
five-opponent pool, screen seeds `2255101..2255102`, and both seats. Confirm
seeds `2255201..2255205` were independently reserved and were not inspected.
No hidden-zone value, opponent identity, or pool identity entered the policy.

## Screen result

Across 40 real-engine matches there were zero semantic faults and zero
unfinished games. The candidate improved the fixed pool from 6/12 (50.0%) to
7/12 (58.3%) and the diversified pool from 3/8 (37.5%) to 5/8 (62.5%). Its
fixed-pool first/second-seat rates were 66.7%/50.0%, versus 50.0%/50.0% for
champion. Mean runtime ratio was 0.825 and maximum match runtime was 37.51
seconds, safely within both runtime gates.

The candidate nevertheless failed the preregistered all-worst-matchup
non-regression gate: matsu fell from 3/4 (75.0%) to 1/4 (25.0%). Claude rose
from 1/4 to 4/4, but improvement in one worst matchup cannot offset regression
in another. Therefore the screen failed, confirm was skipped, and the
candidate was not promoted.

## Terminal handoff

The evaluation-only switch was reverted. The terminal identity handed to
SOT-2256 is `champion`: behavior commit
`fd09f651ba9ed11648a6e5ac3a80fa2f16749130`, `main.py` SHA-256
`043fa98468f10dc1d4490df6ef2c908866fa77bdd1bcd61fab4a73f873d62816`,
and deck SHA-256
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.
The rejected candidate remains reproducible from commit `5418e86` and the
fingerprints in `artifacts/sot-2255-summary.json`.

## Reproduction

```bash
.venv/bin/python scripts/analyze_selective_lookahead_sot_2255.py \
  eval/manifests/sot-2255-selective-lookahead-promotion.json \
  --output artifacts/sot-2255-summary.json
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_submission_exec.py
```
