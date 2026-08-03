# SOT-2377 pairwise action-ranking root-prior decision

## Isolation and training

The candidate in `eval/manifests/sot-2377-action-ranking.json` replaces only the root candidate
ordering and PUCT prior. Deck, 0.8-second search budget, four determinizations, six-action cap, greedy
rollout, `sum` world aggregation, leaf evaluator, deviation margin, and fallback chain remain the
champion settings. The switch is accepted only inside the real-engine telemetry protocol; normal and
Kaggle execution do not load the model.

`artifacts/sot-2377-action-ranking/public_action_ranker.json` was trained only from the 140 `train`
rows of the frozen SOT-2376
oracle with SHA-256 `7f1808c55f7430b423b4f4c0b42f2fb68ed4895287b0aff92812edfc7a8cbd0e`.
Its features are public selection context and legal action option-type signatures. It contains no
opponent/pool identity, seed, seat, match ID, card/hidden-zone identity, or world fingerprint.

## Screen decision

The real-engine screen used fresh seed 2377201, both seats, fixed opponents `matsu`/`take`, and
diversified opponents `claude`/`obo`. Raw per-match reports and their hashes are recorded under
`artifacts/sot-2377-action-ranking/screen/`; the machine-readable decision is
`artifacts/sot-2377-action-ranking/screen-decision.json`.

| Gate | Champion | Candidate | Result |
| --- | ---: | ---: | --- |
| fixed-pool win rate | 0.50 | 0.25 | fail (strict improvement required) |
| diversified-pool win rate | 0.75 | 0.50 | fail (strict improvement required) |
| first-seat win rate | 0.75 | 0.75 | pass |
| second-seat win rate | 0.50 | 0.00 | fail |
| faults / unfinished | 0 / 0 | 0 / 0 | pass |
| mean runtime ratio | 1.00 | 0.5323 | pass (maximum 1.10) |
| maximum match runtime | 43.94s | 18.00s | pass (<600s) |

The candidate is **rejected**. Confirm was not run because screen did not pass. Champion behavior is
unchanged; the evaluation-only ranker, manifest, and evidence remain archived for the blind terminal
audit in SOT-2378. No Kaggle submission was performed.
