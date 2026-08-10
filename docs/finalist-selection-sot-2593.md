# SOT-2593 final two-slot selection

This converge-mode decision selects exactly two already-validated terminal artifacts from the frozen
SOT-2592 inventory. It performs no retraining, rejected-axis retry, gameplay run, or Kaggle submission.
The machine-readable decision is `artifacts/sot-2593/finalist-selection.json`.

Immediately before selection, the SOT-2591 parent and its comments were retrieved again. There was no
newer human `cycle=` or `submit=` directive: converge mode and `submit=auto` remain effective. This child
still cannot submit; the later parent handoff owns that decision.

## Decision

| Role | Artifact | Strategy lineage | Leak-free CV | Wilson 95% | Worst matchup | Worst seat | Runtime mean / p95 / max |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| Primary | SOT-2556 (`5fda6f…a24e`) | counter-meta retained champion | 43/50 (86%) | 73.8–93.0% | search-emerging 6/10 | seat 1: 21/25 | 32.08 / 89.87 / 98.61 s |
| Hedge | SOT-2574 (`07bd55…dc5e`) | population-policy retained champion | 16/20 (80%) | 58.4–91.9% | meta-proxy 8/10 | seat 1: 7/10 | 24.04 / 37.65 / 41.06 s |

SOT-2556 is primary because its leak-free Wilson lower bound (73.8%) is the greatest pessimistic score.
The unequal sample counts are not compared by raw win rate. SOT-2574 is the only other comparable,
validated finalist and has both a distinct content fingerprint and a distinct frozen strategy lineage,
so it is the hedge. Missing or incomparable evidence fails closed.

## Risk record

- Public ratings for both exact fingerprints are unavailable. The CV/public gap is therefore unknown,
  remains explicit `null`, and is never imputed. Public best did not influence the selection.
- Relative skill rating can regress while a fixed local field remains stable. The selection preserves
  two lineages but does not claim live-field non-regression without a later official result.
- Aggregate win rate does not hide the heavy tails: worst matchup, worst seat, p95/max runtime, faults,
  illegal actions, and unfinished games are retained in the manifest. Both artifacts have zero recorded
  faults, illegal actions, and unfinished games; SOT-2556 has the heavier runtime tail, while SOT-2574
  has the weaker worst-seat rate.
- The competition retains only the latest two submissions. These two fingerprints fill those slots as
  a CV-best/hedge portfolio; SOT-2594 must verify the exact exec artifacts before any parent submission.

## Deterministic audit

```bash
.venv/bin/python scripts/select_finalists_sot_2593.py \
  artifacts/sot-2592/finalist-inventory.json
pytest -q tests/test_finalist_selection_sot_2593.py
```

The selector first re-audits every SOT-2592 provenance hash and isolation gate. It fails closed on a
missing independent hedge, reused fingerprint/lineage, missing risk dimensions, public-result
imputation, source mutation, or permission to submit from this child.
