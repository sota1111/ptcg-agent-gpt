# SOT-1939 current-state baseline

Recorded on 2026-07-25 UTC from `main` commit `394f092`.

## Agent and submission inventory

- Kaggle entry point: `main.py`, exporting `agent(obs_dict) -> list[int]`.
- Champion policy: `SubmissionAgent`, with determinized MCTS, greedy, rule-policy, and
  random-legal fallback layers. `SOL_CONFIG` uses four worlds, a one-ply tree, 100 rollout turns,
  and a 0.8-second initial decision budget.
- Time governor: MCTS steps down at 300/420/510 seconds of cumulative think time and hands off to
  greedy after 510 seconds, below the 600-second match allowance.
- Deck: `deck.csv`, 60 cards. Its SHA-256 is
  `e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.
- Champion entry-point SHA-256:
  `4f571aec2aaac0068d43585c95f4fb1d4ad61dc2c1d991c502779f8e179ae7be`.
- Frozen comparison submission: `eval/hash_baseline/main.py` and
  `eval/hash_baseline/deck.csv`.
- A generated `submission.tar.gz` is intentionally not tracked. It can be reproduced with
  `bash scripts/build_submission.sh` after installing the competition runtime; the archive-layout
  check passed during this inventory.

## Local baseline

Command:

```bash
python3 eval/battle_vs.py \
  --seeds 20 \
  --base-seed 20260725 \
  --json artifacts/sot-1939-baseline-vs-hash.json
```

The real competition engine ran 20 fixed agent seeds twice with seats reversed (40 matches total).
The champion beat the frozen pre-SOT-1838 hash policy 39–1, with no draws, unfinished matches, or
agent faults.

| Measure | Result |
| --- | ---: |
| Champion win rate (draws excluded) | 97.5% (39/40) |
| Wilson 95% confidence interval | 87.12%–99.56% |
| Champion wins when first | 19/20 |
| Champion / opponent faults | 0 / 0 |
| Maximum champion think time per match | 30.57 s |

The machine-readable result is
[`artifacts/sot-1939-baseline-vs-hash.json`](../artifacts/sot-1939-baseline-vs-hash.json).
This is a regression baseline against the repository's frozen hash policy, not an estimate of win
rate against the live Kaggle field.

## Kaggle submission history

The authenticated Kaggle CLI query
`kaggle competitions submissions -c pokemon-tcg-ai-battle --csv` returned the latest submission
identified as this repository:

| ref | submitted (UTC) | description | status | public score |
| --- | --- | --- | --- | ---: |
| `54894166` | 2026-07-22 04:47:20 | SOT-1838 semantic MCTS; commit `c05d096`; 125 tests; A/B 39-1 | COMPLETE | 536.8 |

An earlier Sol retry, ref `54882738`, completed with public score 279.5; ref `54882669` ended in
ERROR without a score.

Kaggle does not expose the historical rank of an individual past submission through the
submissions API. The downloadable leaderboard is current and team-level, so it cannot reconstruct
the rank held by ref `54894166` when it completed. At inventory time the account's currently selected
team result was rank 4,771 with score 434.6; that row reflects a later submission from another
repository and must not be attributed to the Sol champion.
