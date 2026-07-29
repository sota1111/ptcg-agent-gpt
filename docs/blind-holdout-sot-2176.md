# SOT-2176 fourth-cycle terminal champion audit and Kaggle submission

## Frozen provenance and seed isolation

The SOT-2175 terminal repository state is merge commit
`43af2571328b07fbe7180559e0b11989b8cda0cb`. SOT-2175 rejected both
public-state seat-tempo candidates, so the last gate-passing champion behavior
remains commit `fd09f651ba9ed11648a6e5ac3a80fa2f16749130`. The submitted
entry point is `main.py` SHA-256
`043fa98468f10dc1d4490df6ef2c908866fa77bdd1bcd61fab4a73f873d62816`;
the deck SHA-256 is
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.

The preregistered manifest is
`eval/manifests/sot-2176-blind-holdout.json`. It freezes the matsu/take/ume
opponent commits and decks before evaluation and assigns 20 previously unused
agent seeds (`2176101..2176120`), each run from both seats. The range is
disjoint from SOT-2174 diagnosis (`2174101..2174103`), SOT-2175 screen
(`2175101..2175102`), SOT-2175 confirm (`2175201..2175205`), and the prior
terminal holdout (`2118101..2118120`). No holdout result was used during
candidate selection.

## Real-engine blind holdout

| Opponent | W-L | Win rate | First / second seat wins |
| --- | ---: | ---: | ---: |
| matsu | 25-15 | 62.5% | 17 / 8 |
| take | 22-18 | 55.0% | 16 / 6 |
| ume | 22-18 | 55.0% | 14 / 8 |
| **Pool** | **69-51** | **57.5%** | **47 / 22** |

All 120 matches completed with zero agent faults, zero unfinished matches, and
zero illegal-action faults. Whole-match runtime was mean 12.17s, p50 9.57s,
p95 27.71s, and max 34.07s. Maximum champion think time was 26.83s, safely
below the 600-second allowance. The paired-seat win-rate difference was 41.7
percentage points (78.3% first versus 36.7% second), so seat sensitivity
remains the principal measured weakness even though the operational audit
passed.

Raw reports are under `artifacts/sot-2176/`; the compact machine-readable
result is `artifacts/sot-2176-summary.json`.

## Champion decision

There is **no new promotion**. SOT-2175 had already rejected both candidates,
and this blind holdout found no fault, unfinished match, illegal action, or
runtime violation that would invalidate the retained champion. The final
champion therefore remains behavior commit `fd09f65`, and its entry-point and
deck hashes match the frozen and submitted state.

## Quality gates, archive, and Kaggle

Ruff lint and formatting, strict mypy, and all 158 pytest tests passed. Both
`scripts/build_submission.sh` and `scripts/verify_submission_exec.py` passed
the isolated exec contract from an unrelated working directory without
`PYTHONPATH` or `__file__`.

The submit-ready `submission.tar.gz` SHA-256 is
`c1a9c99b36827c37fb740823ad61204370ea1b37da866f0709688966ae43e0be`.
It was submitted to `pokemon-tcg-ai-battle` on 2026-07-29 with submission ref
**55091718**. Kaggle reported **COMPLETE** with public score **600.0**.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent /workspaces/ptcg-agent-matsu \
  --label matsu --seeds 20 --base-seed 2176101 \
  --json artifacts/sot-2176/holdout-matsu.json
.venv/bin/python eval/battle_vs.py --opponent /workspaces/ptcg-agent-take \
  --label take --seeds 20 --base-seed 2176101 \
  --json artifacts/sot-2176/holdout-take.json
.venv/bin/python eval/battle_vs.py --opponent /workspaces/ptcg-agent-ume \
  --label ume --seeds 20 --base-seed 2176101 \
  --json artifacts/sot-2176/holdout-ume.json
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
bash scripts/build_submission.sh
.venv/bin/python scripts/verify_submission_exec.py
```
