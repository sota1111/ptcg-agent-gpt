# SOT-1996 MCTS budget decision and final champion submission

The frozen baseline is the SOT-1995 terminal champion at merge commit
`961fa5ec7af1bb1c73de0bf64b2dec184d72ea91`. Its search configuration is four
worlds, one-ply tree search, 100 rollout turns, and a 0.8-second initial
budget. The full configuration and results are recorded in
`artifacts/sot-1996-budget-decision.json`.

## Predefined candidates

All screens used `base_seed=20260726`, five agent seeds, seat reversal, the
unchanged `deck.csv`, and the same frozen `eval/hash_baseline` opponent pool.
Only the search-budget allocation changed.

| candidate | worlds | rollout turns | initial budget | pool result | mean match runtime |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 4 | 100 | 0.8 s | 10–0 | 9.21 s |
| fewer worlds / longer rollout | 2 | 200 | 0.8 s | 8–2 | 9.01 s |
| more worlds / shorter rollout | 8 | 50 | 0.8 s | 9–1 | 10.22 s |
| shorter initial budget | 4 | 100 | 0.6 s | 10–0 | 5.06 s |

The 0.6-second candidate was the only candidate that tied the champion's pool
KPI and it had the lowest runtime, so it alone advanced to confirm.

## Confirm and promotion gate

The confirm used the same pool and seed base with 20 seeds and seat reversal
(40 matches). The 0.6-second candidate finished 40–0, with zero policy faults,
zero unfinished matches, and mean runtime 7.02 seconds. The frozen champion's
SOT-1995 same-pool confirm was also 40–0 with mean runtime 8.70 seconds, making
the candidate's runtime ratio 80.74%. Maximum candidate think time was 14.93
seconds, safely below the 600-second allowance.

The candidate met the fault, timeout, runtime ≤110%, and 600-second gates, but
did not demonstrate the required strictly better pool KPI: both confirms were
40–0. Therefore it was **not promoted**. All experimental `main.py` and time
governor changes were reverted; the SOT-1995 champion configuration remains
the root champion.

## Final champion archive and submission

`scripts/build_submission.sh` and the standalone
`scripts/verify_submission_exec.py` gate both passed. The unchanged champion
archive has SHA-256
`bac0bc46fc13e786eec7972f4f93333682a5ea57d31413b3aa83f4c1d1d9f41e`.
It was submitted to Kaggle as submission `55008332`, which completed with a
public score of **600.0**.
