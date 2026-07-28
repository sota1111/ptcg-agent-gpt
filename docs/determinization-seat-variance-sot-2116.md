# SOT-2116 determinization / seat variance diagnosis

## Frozen provenance and method

The machine-readable manifest is
`eval/manifests/sot-2116-determinization-seat.json`. It freezes the current
`origin/main` commit (`dd8592c`), champion entry point and deck hashes, and the
matsu/take/ume opponent commits plus their `main.py` and deck hashes. Agent
seeds `2116101..2116103` are disjoint from SOT-2062/2063/2064 and each is run
from both seats.

The real engine has no seed API, so engine shuffle reproducibility cannot be
claimed. Agent-side determinization is reproducible from `AGENT_SEED`, and the
committed raw reports preserve the actual engine outcomes. Opt-in evaluation
telemetry records every hidden-zone fill fingerprint, generated world count,
world-by-world root action visits/value means, and selected action. It does
not alter action selection or the submission protocol used outside evaluation.

## Results

| Opponent | Paired matches | W-L | Fault | Unfinished | Mean runtime |
| --- | ---: | ---: | ---: | ---: | ---: |
| matsu | 6 | 4-2 | 0 | 0 | 11.30s |
| take | 6 | 6-0 | 0 | 0 | 13.93s |
| ume | 6 | 3-3 | 0 | 0 | 11.92s |
| **Pool** | **18** | **13-5** | **0** | **0** | **12.38s** |

Seat results were 9/9 as first player and 4/9 as second player, a 55.6
percentage-point gap in this small paired sample. Hidden-zone fingerprints
were unique in 100% of generated worlds. The mean per-match selected-action
world value spread was 0.432.

The five losses classify exclusively as:

| Category | Losses | Interpretation |
| --- | ---: | --- |
| sample duplicate / low diversity | 0 | no fingerprint duplication observed |
| world aggregation outlier sensitivity | 5 | all losses crossed value-spread or world-majority disagreement threshold |
| seat-specific public state difference | 0 | lower-priority exclusive class; pool-level seat gap remains material |
| unclassified | 0 | every loss had an observable category |

The classification is diagnostic, not causal: small N and non-seedable engine
shuffle do not support a promotion decision.

## Next independent hypotheses

1. **Robust world aggregation.** Compare median or trimmed root aggregation
   against the champion's summed visit/value rule while holding `n_worlds=4`
   and the total search budget fixed. Basis: 5/5 losses show aggregation
   sensitivity and mean selected-action world spread is 0.432.
2. **Seat-conditioned public-state calibration.** Change only observable
   turn/board-tempo evaluation terms, not hidden sampling. Basis: first-seat
   9/9 versus second-seat 4/9 in paired matches.

Structured sampling is not selected: fingerprint uniqueness was 1.000, so the
new evidence does not support a sample-duplication bottleneck. The prior
`n_worlds=2/8`, root cap/prior temperature, fallback semantics, and deck
restructuring axes remain explicitly excluded.

## Reproduction and behavior invariance

```bash
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-matsu --label matsu \
  --seeds 3 --base-seed 2116101 --json artifacts/sot-2116/paired-matsu.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-take --label take \
  --seeds 3 --base-seed 2116101 --json artifacts/sot-2116/paired-take.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-ume --label ume \
  --seeds 3 --base-seed 2116101 --json artifacts/sot-2116/paired-ume.json
python3 scripts/analyze_determinization_variance.py \
  --manifest eval/manifests/sot-2116-determinization-seat.json \
  --output artifacts/sot-2116-summary.json
```

Before and after, `main.py` is
`db3389926560a8fb037d70e60e6b8ff6230d2c2489833f77960aecc5274afb73`
and `deck.csv` is
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.
Champion behavior is unchanged.
