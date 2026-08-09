# SOT-2553 replay/lineage-disjoint metagame CV calibration

`eval/manifests/sot-2553-replay-lineage-cv.json` extends the frozen SOT-2538 field without changing
the champion or permitting a Kaggle submission. Every opponent snapshot records an evidence ID,
collection timestamp, provenance, license evidence, offline-portability flag, submission lineage, and
metagame family. The public Search-Audited Alakazam v12 snapshot remains pinned to Kaggle source version
19, its Apache-2.0 notice, and exact executable policy/deck hashes.

The audit fails closed unless train/screen/confirm/blind have zero overlap in entity, policy, deck,
match unit, seed, time window, evidence ID, and submission lineage. Each collection timestamp must fall
inside its split's frozen window. Every v2 opponent payload must be locally available, fingerprinted,
licensed, and offline portable. Metagame family is recorded for stratified reporting; it is not treated
as an identity because distinct policies from the same family are a valid future generalization test.

## CV/public gap rule

The output records CV order, optional public-rating order, shared-order agreement, selected order, and
selection basis. Public rating is a sanity signal only. Missing public data retains CV; any direction or
ordering disagreement selects the CV order (`cv-pessimistic-on-disagreement`). Public rating can never
open confirm or promote a candidate.

## Reproduce

```bash
python3 scripts/audit_metagame_cv.py eval/manifests/sot-2553-replay-lineage-cv.json
python3 scripts/run_metagame_cv.py \
  --manifest eval/manifests/sot-2553-replay-lineage-cv.json \
  --raw-dir artifacts/sot-2553/raw \
  --output artifacts/sot-2553/baseline-summary.json
pytest -q tests/test_replay_lineage_cv_sot_2553.py
```

The real-engine baseline runs every field member in both semantic seats at one frozen seed per opponent.
The acceptance receipt is `artifacts/sot-2553/baseline-summary.json`; it must report zero faults and zero
unfinished matches. No command in this procedure submits to Kaggle.
