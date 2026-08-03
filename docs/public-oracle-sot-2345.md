# SOT-2345 diversified public-state oracle

The frozen manifest runs the champion against three composition-distinct repositories with one fixed
agent seed per split and seat reversal. `train`, `screen`, and unseen `confirm` use disjoint seeds.
Opponent IDs and hidden cards never enter the seven-feature model vector; only an opaque SHA-256 of
seed, seat, and opponent content fingerprint remains as provenance for leakage checks.

Reproduce the checked-in corpus and heuristic baseline from the repository root:

```bash
.venv/bin/python scripts/build_public_oracle_corpus.py \
  --manifest eval/manifests/sot-2345-public-oracle.json \
  --output artifacts/sot-2345/public-oracle.jsonl \
  --diagnostics artifacts/sot-2345/diagnostics.json
```

The diagnostics file records the corpus SHA-256, split overlap audit, Brier calibration error, ROC AUC
when both outcome classes are present, and matchup/seat provenance-unit counts. A candidate may be
screened only on `train`/`screen`; `confirm` remains unseen until the screen contract passes. A rejected
candidate must revert behavioral changes while retaining its manifest, corpus fingerprint, diagnostics,
and experiment-ledger entry. A promoted candidate must additionally preserve the submission's
`main.agent` exec-style import compatibility. This issue builds evidence only and never submits to Kaggle.
