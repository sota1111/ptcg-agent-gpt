# SOT-2399 leaderboard-reanchored evaluation contract

## Why the pool is re-anchored

The previous terminal holdout was locally balanced while the public leaderboard remained out of range.
This is treated as oracle drift: local win rate is a screening proxy, not sufficient promotion evidence.
The frozen pool therefore retains matsu/take/ume plus Claude/obo and adds a portable `meta-proxy`.
The proxy crosses the pinned champion policy with a frozen diversified archetype deck. This follows the
public competition discussion's evidence that agents should be evaluated across popular archetypes,
rather than against one locally convenient policy/deck combination:
<https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/727816>.

`eval/manifests/sot-2399-lb-reanchoring.json` pins all six identities, champion hashes, and phase seeds.
The proxy is repository-local, so the re-anchoring unit remains runnable without a sixth sibling checkout.

## Preregistered sequential gate

Screen uses seed `2399101`, both seats, and every opponent. Confirm reserves independent seeds
`2399201..2399205` and is rejected by the evaluator unless a machine-readable screen decision passed.
A candidate must strictly improve pooled win rate while preserving every opponent, both seats, faults,
unfinished games, and runtime (mean ratio at most 1.10; every match below 600 seconds). A failed screen
means confirm is not run and candidate behavior is reverted. A confirm winner must still pass the inherited
submission exec-compatibility contract before promotion. This child never submits to Kaggle.

The evaluator writes opponent, seat, worst-matchup, fault, unfinished, and mean/p95/max runtime metrics:

```bash
python3 scripts/evaluate_reanchoring.py \
  --manifest eval/manifests/sot-2399-lb-reanchoring.json --phase screen \
  --champion artifacts/sot-2399/screen/champion/*.json \
  --candidate artifacts/sot-2399/screen/candidate/*.json \
  --output artifacts/sot-2399/screen-decision.json
```

For confirm, add `--screen-decision artifacts/sot-2399/screen-decision.json`. The command fails closed
when seed counts, opponent coverage, seat reversal, champion fingerprint, or screen authorization drift.

## Baseline contract check

The committed baseline replays the unchanged champion as both sides of the paired comparison. Its purpose
is to prove all six opponents start, the schema is complete, and a non-improving candidate cannot open
confirm. All 12 real-engine matches completed: champion went 7-5 (58.3%), seat 0/1 were 66.7%/50.0%,
Claude was the worst matchup at 0-2, faults and unfinished games were both zero, and maximum whole-match
runtime was 83.94 seconds. The identical paired replay did not strictly improve, so the screen failed,
confirm was not executed, champion behavior was retained, and `kaggleSubmitted=false` was recorded in
`artifacts/sot-2399/screen-decision.json`.
