# SOT-2440 public tactical controller screen → confirm decision

## Candidate boundary

`agents/tactical_controller.py` re-expresses the portable tactical concepts frozen by SOT-2439 as
small public-only root/action-score bonuses: reachable attack and KO/prize ordering, energy readiness,
retreat/switch pressure, and public-board target/threat attributes. It receives only the adapted
`View` plus attribute-only card-master features. Hidden opponent zone identities and order, opponent or
pool identity, evaluation/match seed, and seat as a matchup proxy are not inputs.

The candidate is enabled only when both `PTCG_TELEMETRY_PROTOCOL=1` and
`PTCG_PUBLIC_TACTICAL_CANDIDATE=1` are present. Deck, search budget, determinization, evaluator, and
fallback chain remain the champion values. Normal, package, and Kaggle execution keep the candidate
disabled.

## Paired screen

The frozen screen used base seed `2439101`, two seeds per opponent, both seats, and all six pinned
SOT-2399 opponents. The champion and candidate each played 24 real-engine matches.

| Policy | Aggregate | Seat 0 | Seat 1 | Worst / regressed matchup | Fault / unfinished | Mean / max runtime |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| champion | 13/24 | 8/12 | 5/12 | claude 0/4 | 0 / 0 | 25.36s / 84.88s |
| tactical candidate | 15/24 | 10/12 | 5/12 | obo 3/4 (champion 4/4) | 0 / 0 | 25.57s / 94.24s |

## Decision

Rejected. Although aggregate win rate improved from 54.2% to 62.5%, the candidate violated two frozen
screen gates: `obo` regressed from 4/4 to 3/4, and candidate mean runtime exceeded the strict champion
ratio of 1.0. Independent confirm was therefore not run. Candidate behavior remains disabled and the
champion is retained. No Kaggle submission was made.

Machine-readable evidence is in `artifacts/sot-2440/screen-decision.json`. Rebuild the decision with:

```bash
python scripts/evaluate_public_tactical_sot_2440.py \
  --contract eval/manifests/sot-2439-public-tactical-contract.json --phase screen \
  --champion artifacts/sot-2440/screen/champion/*.json \
  --candidate artifacts/sot-2440/screen/candidate/*.json \
  --output artifacts/sot-2440/screen-decision.json
```
