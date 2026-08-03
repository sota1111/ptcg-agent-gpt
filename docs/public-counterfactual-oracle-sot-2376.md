# SOT-2376 public counterfactual action oracle

## Fixed contract

`eval/manifests/sot-2376-public-counterfactual-oracle.json` freezes the champion entrypoints,
hash-baseline opponent, seat reversal, disjoint train/screen/confirm seeds, four determinizations,
0.8-second search budget, six root actions, and a one-root-decision horizon. Each action pair is scored
only on determinizations shared by both actions; at least two shared worlds are required.

Learning rows contain an explicit public-state allowlist plus action **type** signatures and relative
outcome labels. They do not contain card/hand/deck identities, opponent or pool identity, seed, seat,
match ID, or hidden-world fingerprints. Opaque SHA-256 values exist only for state deduplication,
split-leakage checks, and artifact provenance.

## Reproducible artifact

Run from the repository root:

```bash
.venv/bin/python scripts/build_public_counterfactual_oracle.py \
  --manifest eval/manifests/sot-2376-public-counterfactual-oracle.json \
  --output artifacts/sot-2376-public-counterfactual-oracle/oracle.jsonl \
  --diagnostics artifacts/sot-2376-public-counterfactual-oracle/diagnostics.json \
  --write-reports artifacts/sot-2376-public-counterfactual-oracle/source-reports.json
```

For an exact deterministic rebuild from the frozen source report, add:

```bash
--reports artifacts/sot-2376-public-counterfactual-oracle/source-reports.json
```

The checked-in result has 348 identity-free action-type pairs across 72 public states (train 140/26,
screen 83/16, confirm 125/30). The underlying root search supports 971 of 1,071 legal action-index
pairs on at least two shared worlds (coverage 0.9066), with no match-unit or seed overlap and non-zero
labels in 272 identity-free pairs. Its oracle SHA-256 and combined artifact fingerprint are recorded in
`diagnostics.json`.

## Downstream screen/confirm contract

SOT-2377 may fit on `train` and evaluate on `screen` only. The preregistered screen entry gates are
coverage at least 0.50 and train pairwise-signal rate at least 0.05, where a signaled pair has absolute
relative outcome at least 0.05. `confirm` must remain unopened unless the screen gate passes. A rejected
candidate retains the evidence but leaves champion behavior unchanged; a promoted candidate must also
pass submission exec compatibility. This contract does not run a Kaggle submission.
