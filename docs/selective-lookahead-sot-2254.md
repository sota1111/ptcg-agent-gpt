# SOT-2254 selective-lookahead diagnosis

## Frozen provenance and protocol

The diagnosis freezes the SOT-2242 terminal merge `6c2468e`, retained behavior
commit `fd09f65`, champion entry-point/deck hashes, matsu and Claude opponent
commits/decks, the existing four-world/0.8-second root budget, and fresh seeds
`2254101..2254103`. The seeds do not overlap SOT-2240 diagnosis, SOT-2241
screen/confirm, or SOT-2242 holdout seeds. Each seed was run from both seats.

The two-decision diagnostic uses only allowlisted public snapshots and the
public root action/value telemetry. It compares the selected one-ply root mean
with the mean of that decision and the immediately observed next setup-only
decision in the same turn (maximum step gap two). This is a bounded,
diagnostic continuation estimate, not a causal counterfactual or promotion
result. Hidden hand/deck identity and opponent identity are neither stored in
the decision rows nor used as a branch condition.

## Result

Twelve real-engine matches completed with zero semantic faults and zero
unfinished games; six losses supplied the diagnostic branches. Maximum match
runtime was 39.78 seconds, below the frozen 600-second constraint. Across 45
eligible two-setup-decision sequences, 28 (62.2%) had a positive continuation
effect. The mean effect was +0.0177, median +0.0165, and maximum +0.2300 in the
root value scale. These are modest but repeatable signs that the one-ply score
can understate value realized across a short setup sequence.

One independent candidate is preregistered: `bounded-public-setup-continuation`.
Its only proposed change is a two-decision continuation tie-break at setup-only
public decision points under the existing root budget. It does not retry
public-state weights, action-regret correction, root cap/prior temperature, or
median/trimmed aggregation.

The screen uses fresh seeds `2255101..2255102`, both seats, and the frozen
matsu/take/ume/Claude/obo pool. Only a screen pass proceeds to confirm seeds
`2255201..2255205`. Promotion requires strictly higher pool win rate,
non-regressing worst matchup, no added fault/timeout, mean runtime at most 110%
of champion, and maximum runtime below 600 seconds. SOT-2254 itself changes no
champion or submission behavior.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent /workspaces/ptcg-agent-matsu \
  --label matsu --seeds 3 --base-seed 2254101 --public-telemetry-only \
  --json artifacts/sot-2254/traces/matsu.json
.venv/bin/python eval/battle_vs.py \
  --opponent /workspaces/ai-dev-control-plane/.targets/ptcg-agent-claude \
  --label claude --seeds 3 --base-seed 2254101 --public-telemetry-only \
  --json artifacts/sot-2254/traces/claude.json
.venv/bin/python scripts/analyze_selective_lookahead_sot_2254.py \
  eval/manifests/sot-2254-selective-lookahead.json \
  --output artifacts/sot-2254-summary.json
```
