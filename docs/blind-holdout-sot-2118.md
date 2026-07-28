# SOT-2118 third-cycle terminal champion audit and Kaggle submission

## Frozen provenance and seed isolation

The SOT-2117 terminal repository state is commit
`56131d409cf1ac263fde5858d476d9f195d05eb4`. SOT-2117 rejected both robust
world-aggregation candidates, so the last gate-passing champion behavior
remains commit `fd09f651ba9ed11648a6e5ac3a80fa2f16749130` with default `sum`
aggregation. The submitted entry point is `main.py` SHA-256
`41c178d95f21edfcacb1705bc8de4d998bffc5f0f62bc4aae32a477fa14f74b3`;
the deck SHA-256 is
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.

The preregistered manifest is
`eval/manifests/sot-2118-blind-holdout.json`. It freezes the matsu/take/ume
opponent commits and decks before evaluation and assigns 20 previously unused
agent seeds (`2118101..2118120`), each run from both seats. The range is
disjoint from SOT-2116 diagnosis (`2116101..2116103`), SOT-2117 screen
(`2117101..2117102`), the reserved independent confirm range
(`2117201..2117205`), and the prior terminal holdout
(`2064101..2064120`). No holdout result was used during candidate selection.

## Real-engine blind holdout

| Opponent | W-L | Win rate | Wilson 95% CI | First / second seat wins |
| --- | ---: | ---: | ---: | ---: |
| matsu | 22-18 | 55.0% | 39.8%-69.3% | 16 / 6 |
| take | 24-16 | 60.0% | 44.6%-73.7% | 15 / 9 |
| ume | 24-16 | 60.0% | 44.6%-73.7% | 14 / 10 |
| **Pool** | **70-50** | **58.3%** | per-matchup above | **45 / 25** |

All 120 matches completed with zero agent faults, zero unfinished matches, and
zero illegal-action faults. Whole-match runtime was mean 12.57s, p50 10.15s,
p95 33.11s, and max 45.29s, safely below the 600-second allowance. The
paired-seat win-rate difference was 33.3 percentage points (75.0% first
versus 41.7% second), so the previously diagnosed seat sensitivity remains a
material risk even though the operational audit passed.

Raw reports are under `artifacts/sot-2118/`; the compact machine-readable
result is `artifacts/sot-2118-summary.json`.

## Champion decision

This terminal stage evaluated no new behavior candidate. SOT-2117 had already
rejected every candidate, and the holdout found no fault, unfinished match,
illegal action, or runtime violation that would invalidate the retained
champion. Therefore there is **no new promotion** and the last gate-passing
champion is retained. Its default behavior (`sum` aggregation), entry-point
hash, and deck hash match the frozen and submitted state.

## Quality gates, archive, and Kaggle

Ruff lint and formatting, strict mypy, and all 150 pytest tests passed. Both
`scripts/build_submission.sh` and the standalone
`scripts/verify_submission_exec.py` passed the isolated exec contract: the
archive loads from an unrelated working directory without `PYTHONPATH` or
`__file__`.

The submit-ready `submission.tar.gz` SHA-256 is
`8964d1fd2a04416528e22520faa7c9cbe4463b8fff09e83dbd224ae7e19bc4d5`.
It was submitted to `pokemon-tcg-ai-battle` on 2026-07-28 with submission ref
**55061703**. Kaggle reported **COMPLETE** with public score **600.0**. The
submission ref, archive hash, final status, and score make the asynchronous
result reproducible.

## Reproduction

```bash
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-matsu --label matsu \
  --seeds 20 --base-seed 2118101 --json artifacts/sot-2118/holdout-matsu.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-take --label take \
  --seeds 20 --base-seed 2118101 --json artifacts/sot-2118/holdout-take.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-ume --label ume \
  --seeds 20 --base-seed 2118101 --json artifacts/sot-2118/holdout-ume.json
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
bash scripts/build_submission.sh
.venv/bin/python scripts/verify_submission_exec.py
```
