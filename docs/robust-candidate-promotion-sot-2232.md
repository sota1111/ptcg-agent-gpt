# SOT-2232 distribution-robust candidate decision

## Preregistered comparison

The SOT-2231 terminal champion, diversified pool, diagnosis, hashes, and used
seeds were frozen before this experiment in
`eval/manifests/sot-2232-robust-candidates.json`. Two one-change candidates
used only public board attributes: total-board energy calibration `0.2 -> 0.3`
and active-energy calibration `0.0 -> 0.1`. Their smaller half-step retries
were justified by the new SOT-2231 trace evidence assigning 8/10 diversified
losses to public board/readiness calibration. Deck, search budget, rollout,
world aggregation, root cap, fallback semantics, and champion files stayed
fixed.

Every screen used agent seeds `2232101..2232103`, the same five-opponent pool,
and both seats: 30 real-engine matches per identity. Confirm seeds
`2232201..2232210` were independently preregistered but correctly not run
because neither candidate passed screen.

## Screen result

| Identity | Fixed pool | Fixed worst | Diversified pool | Diversified worst | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| champion | 72.2% | 66.7% | 75.0% | 66.7% | retain |
| board calibration | 61.1% | 50.0% | 75.0% | 50.0% | reject |
| active calibration | 66.7% | 33.3% | 75.0% | 66.7% | reject |

Board calibration did not improve diversified aggregate and regressed both
fixed and diversified worst-matchup. Active calibration also did not improve
diversified aggregate, regressed fixed-pool worst-matchup, and used 129.8% of
champion mean runtime on the diversified screen, above the 110% gate. All 90
matches completed with zero semantic faults, unfinished games, or illegal
actions; every observed match runtime remained below 600 seconds. Wilson 95%
intervals, seat splits, per-opponent results, mean/p95 runtime, report hashes,
and rejection reasons are retained in `artifacts/sot-2232-summary.json`.

## Promotion decision

No candidate is promoted. The evaluation-only candidate behavior was reverted,
so `main.py` and `deck.csv` retain the SOT-2231 champion SHA-256 values
`043fa984...` and `e92d5717...`. The retained traces contain public-state
telemetry only, no hidden-world fingerprint, hidden-zone feature, opponent
identity branch, or Kaggle leaderboard adaptation.
