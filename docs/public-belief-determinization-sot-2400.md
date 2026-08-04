# SOT-2400 public-history belief determinization

## Candidate and leakage boundary

The candidate replaces the opponent MIRROR pool's uniform shuffle with seeded
weighted sampling without replacement. It builds a smoothed posterior over
portable card/archetype attributes (card type, Pokémon energy type, evolution
stage, and ex status) from an explicit public allow-list: opponent board,
discard, face-up prizes, and opponent-owned stadium. Opponent hand/deck and
face-down prize identities, opponent identity, and evaluation-pool identity
are never read. Unit tests vary hidden hand/deck identities and assert that the
belief evidence is unchanged.

The switch `PTCG_PUBLIC_BELIEF_CANDIDATE=1` is honored only together with the
existing real-engine `PTCG_TELEMETRY_PROTOCOL=1`. Normal and submission
execution therefore retain the champion's uniform MIRROR determinization.

## Paired screen and decision

The candidate was screened against SOT-2399's pinned re-anchoring pool with
seed `2399101`, one paired seed per opponent, both seats, and the identical
search budget. Machine-readable evidence is in
`artifacts/sot-2400/screen-decision.json`.

| Policy | Aggregate | Seat 0 | Seat 1 | Worst matchup | Fault / unfinished | Mean / max runtime |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| champion | 7/12 | 4/6 | 3/6 | claude 0/2 | 0 / 0 | 27.54s / 83.93s |
| public belief | 8/12 | 5/6 | 3/6 | take 0/2 | 0 / 0 | 20.68s / 64.76s |

Despite the aggregate improvement, take regressed from 1/2 to 0/2. The strict
every-opponent non-regression gate therefore failed. Independent confirm was
not run, candidate behavior remains disabled, and the champion is retained.
No Kaggle submission was made. Because the candidate was not promoted, exec
archive verification is not applicable; normal execution remains the already
verified champion artifact.

Rebuild the decision after reproducing the six candidate reports:

```bash
python scripts/evaluate_reanchoring.py \
  --manifest eval/manifests/sot-2399-lb-reanchoring.json --phase screen \
  --champion artifacts/sot-2399/screen/champion/*.json \
  --candidate artifacts/sot-2400/screen/candidate/*.json \
  --output artifacts/sot-2400/screen-decision.json
```
