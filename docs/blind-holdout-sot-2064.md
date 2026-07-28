# SOT-2064 terminal champion blind holdout and Kaggle submission

## Frozen provenance and isolation

The terminal second-cycle champion is commit
`fd09f651ba9ed11648a6e5ac3a80fa2f16749130`. SOT-2063 rejected both
root-prior candidates and reverted their behavior changes, so the root
champion remains `main.py` SHA-256
`db3389926560a8fb037d70e60e6b8ff6230d2c2489833f77960aecc5274afb73`
with deck SHA-256
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.

The holdout manifest is
`eval/manifests/sot-2064-blind-holdout.json`. It freezes the three hard
opponent commits and decks, uses 20 agent seeds (`2064101..2064120`), and
reverses seats for 40 matches per opponent. These seeds are disjoint from
SOT-2062 blind analysis (`2062301..2062306`) and SOT-2063 screen/confirm
(`2063101..2063103`, `2063201..2063220`); they were not inspected or used
during candidate selection.

## Real-engine holdout

| opponent | W-L | win rate | Wilson 95% CI |
| --- | ---: | ---: | ---: |
| matsu | 24-16 | 60.0% | 44.6%-73.7% |
| take | 26-14 | 65.0% | 49.5%-77.9% |
| ume | 27-13 | 67.5% | 52.0%-79.9% |
| **pool** | **77-43** | **64.2%** | per-matchup above |

All 120 matches completed. The champion recorded zero faults, zero unfinished
matches, and zero illegal-action faults. Whole-match runtime was p50 10.55s,
p95 24.27s, and max 40.79s; maximum champion think time was 32.73s, safely
inside the 600-second allowance. Raw per-match reports are committed under
`artifacts/sot-2064/`, and the compact machine-readable conclusion is
`artifacts/sot-2064-summary.json`.

The holdout passes the terminal audit. No candidate was under evaluation in
this stage, so there is no new promotion: the frozen champion is retained and
the recorded conclusion agrees with the repository's behavior state.

## Archive, exec compatibility, and Kaggle

`bash scripts/build_submission.sh` and the standalone
`python3 scripts/verify_submission_exec.py` both passed. The submit-ready
archive SHA-256 is
`309d50625ec64dbcf9ee8593180aad469e624ae852de207fb18a2610a520e8eb`;
the gate loads from an extracted archive with an unknown current working
directory and without relying on `__file__`.

The archive was submitted to `pokemon-tcg-ai-battle` on 2026-07-28 as Kaggle
submission ref **55050021**, description
`SOT-2064 blind holdout PASS 77-43; exec PASS; champion fd09f65`.
The submission reached **COMPLETE** with public score **600.0**. The
submission ref, archive hash, status, and score make the asynchronous result
reproducible.

## Reproduction

```bash
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-matsu --label matsu \
  --seeds 20 --base-seed 2064101 --json artifacts/sot-2064/holdout-matsu.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-take --label take \
  --seeds 20 --base-seed 2064101 --json artifacts/sot-2064/holdout-take.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-ume --label ume \
  --seeds 20 --base-seed 2064101 --json artifacts/sot-2064/holdout-ume.json
bash scripts/build_submission.sh
python3 scripts/verify_submission_exec.py
```
