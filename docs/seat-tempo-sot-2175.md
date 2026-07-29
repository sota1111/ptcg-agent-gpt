# SOT-2175 public-state seat-tempo promotion decision

## Frozen baseline and hypotheses

The preregistration manifest
`eval/manifests/sot-2175-seat-tempo.json` fixes the SOT-2174 terminal merge
commit `d3c2807`, champion behavior commit `fd09f65`, entry-point/deck hashes,
matsu/take/ume opponent commits, `n_worlds=4`, the 0.8-second budget, rollout
limits, root cap, prior temperature, summed world aggregation, deck, and
fallback semantics.

Two one-change candidates were defined before collection:

1. `board-energy`: raise the existing public total-board energy weight from
   0.2 to 0.4.
2. `active-energy`: add a 0.2 term for publicly attached active Pokémon
   energy as an attack-readiness proxy.

Neither candidate uses seat identity, hidden zones, opponent private card
identities, or search-world fingerprints. The previously rejected
median/trimmed-mean aggregations were explicitly excluded.

## Fixed-seed paired-seat screen

The screen used agent seeds `2175101..2175102`, each from both seats against
the same frozen opponent pool (12 matches per policy).

| Policy | Pool | matsu / take / ume | First / second | Paired gap | Fault / timeout | Mean / p95 runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| champion | 5-7 (.417) | 2-2 / 2-2 / 1-3 | .667 / .167 | .500 | 0 / 0 | 13.12s / 31.01s |
| board-energy | 7-5 (.583) | 2-2 / 1-3 / 4-0 | .667 / .500 | .167 | 0 / 0 | 8.19s / 14.83s |
| active-energy | 7-5 (.583) | 1-3 / 3-1 / 3-1 | .833 / .333 | .500 | 0 / 0 | 10.43s / 19.98s |

Both candidates exceeded the screen champion pool KPI while satisfying the
fault, timeout, paired-gap, runtime, and 600-second gates, so both advanced.

## Independent-seed confirm

The confirm used disjoint agent seeds `2175201..2175205`, again with seat
reversal and the same frozen pool (30 matches per policy).

| Policy | Pool | matsu / take / ume | First / second | Paired gap | Fault / timeout | Mean / p95 runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| champion | 17-13 (.567) | 3-7 / 7-3 / 7-3 | .800 / .333 | .467 | 0 / 0 | 10.54s / 23.08s |
| board-energy | 18-12 (.600) | 4-6 / 5-5 / 9-1 | .733 / .467 | .267 | 0 / 0 | 12.56s / 30.13s |
| active-energy | 17-13 (.567) | 6-4 / 6-4 / 5-5 | .667 / .467 | .200 | 0 / 0 | 13.53s / 22.89s |

## Decision

**Do not promote.** `board-energy` improved pool and second-seat KPIs, but its
mean runtime was 119.2% of champion and exceeded the preregistered 110% gate.
`active-energy` tied rather than exceeded the champion pool KPI and also
exceeded the runtime gate (128.4%). All matches completed without a semantic
fault or timeout and maximum think time remained far below 600 seconds.

The candidates remain telemetry-harness-only switches for reproducibility.
Normal and Kaggle execution ignore `PTCG_TEMPO_CANDIDATE`, so the default
champion evaluation weights, deck, world aggregation, and action behavior
remain unchanged. Machine-readable screen, confirm, and decision records are
in `artifacts/sot-2175/` and `artifacts/sot-2175-summary.json`.

Regenerate the decision with:

```bash
python scripts/analyze_seat_tempo.py \
  --manifest eval/manifests/sot-2175-seat-tempo.json \
  --output artifacts/sot-2175-summary.json
```
