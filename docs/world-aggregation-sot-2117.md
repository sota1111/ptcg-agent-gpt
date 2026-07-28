# SOT-2117 world aggregation promotion decision

## Frozen baseline and hypotheses

The preregistration manifest is
`eval/manifests/sot-2117-world-aggregation.json`. It fixes the SOT-2116
terminal main commit `27a8f788`, entrypoint/deck hashes, matsu/take/ume
opponent commits, four worlds, 0.8-second budget, rollout limits, root cap,
prior temperature, deck, and fallback semantics. The champion remains summed
root visits/value. The two one-change candidates are median and trimmed-mean
aggregation of per-world normalized root statistics.

## Fixed-seed paired-seat screen

Each policy used agent seeds `2117101..2117102` against the same opponent pool
from both seats (12 matches per policy).

| Policy | Pool | matsu | take | ume | First | Second | Fault / unfinished | Mean / p95 runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| champion sum | 7-5 | 1-3 | 3-1 | 3-1 | 4/6 | 3/6 | 0 / 0 | 10.45s / 26.29s |
| median | 7-5 | 2-2 | 2-2 | 3-1 | 4/6 | 3/6 | 0 / 0 | 12.66s / 25.04s |
| trimmed mean | 5-7 | 2-2 | 2-2 | 1-3 | 4/6 | 1/6 | 0 / 0 | 12.66s / 30.05s |

Machine-readable mean/p95 runtime and paired-seat gaps are recorded in
`artifacts/sot-2117-summary.json`.

## Decision

Neither candidate exceeded the champion's 58.3% same-pool KPI: median tied it
and trimmed mean reached 41.7%. Both candidate mean runtimes also exceeded
the 110% gate (121.2% of champion). Therefore no candidate passed the
preregistered screen gate, and no independent-seed confirm was run. This is
the intended sequential design: only screen-passing candidates consume the
confirm pool.

The promotion decision is **no promotion**. `PTCG_WORLD_AGGREGATION` remains
an evaluation-only switch whose default is `sum`; champion behavior,
`main.py` default action selection, and `deck.csv` remain unchanged. The
committed implementation supports reproducing or extending the rejected
candidate study without changing the competition runtime's public-observation
contract.

Regenerate the aggregate with:

```bash
python scripts/analyze_world_aggregation.py \
  --manifest eval/manifests/sot-2117-world-aggregation.json \
  --output artifacts/sot-2117-summary.json
```
