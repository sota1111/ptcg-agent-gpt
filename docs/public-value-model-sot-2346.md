# SOT-2346 public-state value-model screen → confirm decision

## Candidate and frozen protocol

The candidate is a ridge-regularized logistic model trained only on the SOT-2345 `train` split's
seven public count features. Its probability receives a fixed 0.25 blend weight against the champion
heuristic. The artifact lives at `agents/public_value_model.json`, so it is submission-local; it has no
card IDs, hidden-world values, or opponent identity features.

Before opening confirm, `eval/manifests/sot-2346-public-value.json` froze the artifact and corpus
hashes, three opponent commits/decks, both-seat reversal, screen seed 2346101, independent confirm
seeds 2346201–2346203, and the gate. Champion and candidate used the same deck, world count, root
budget, and fallback chain; only the leaf evaluator changed. Confirm opened only after screen passed.

## Results

| Phase / identity | Aggregate | Seat 0 | Seat 1 | matsu | take | ume | Fault / unfinished | Max runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| screen champion | 3/6 | 1/3 | 2/3 | 1/2 | 2/2 | 0/2 | 0 / 0 | 15.50s |
| screen candidate | 4/6 | 2/3 | 2/3 | 1/2 | 2/2 | 1/2 | 0 / 0 | 15.57s |
| confirm champion | 11/18 | 4/9 | 7/9 | 4/6 | 4/6 | 3/6 | 0 / 0 | 37.48s |
| confirm candidate | 11/18 | 5/9 | 6/9 | 2/6 | 4/6 | 5/6 | 0 / 0 | 24.85s |

Raw matchup/seat/runtime/fault reports and their SHA-256 fingerprints are retained under
`artifacts/sot-2346-public-value/`; `decision.json` contains the machine-readable gate result.

## Decision

Rejected. The candidate passed screen but failed independent confirm because aggregate win rate did
not strictly improve, the matsu matchup regressed from 4/6 to 2/6, and seat 1 regressed from 7/9 to
6/9. Normal execution therefore retains the champion evaluator. The candidate can only be activated
by the real-engine telemetry protocol's explicit evaluation environment switch, so submission behavior
is unchanged. No Kaggle submission was made.
