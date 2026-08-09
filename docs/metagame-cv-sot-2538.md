# SOT-2538 entity/time-disjoint metagame CV

This contract re-anchors local evaluation without modifying the candidate or submitting to Kaggle.
`eval/manifests/sot-2538-entity-time-cv.json` freezes the champion, seven opponents, source/license
metadata, split membership, collection windows, match units, and seeds. The entity key is the pair of
policy and deck SHA-256 fingerprints. Train, screen, confirm, and blind are machine-audited for zero
entity, policy, deck, match-unit, seed, and time-window overlap. Frozen deck overrides broaden archetype
coverage and ensure deck identity is disjoint as well as the composite entity.

The pool adds the Apache-2.0 public Search-Audited Alakazam v12 payload. Its Ruff-normalized policy
imports and executes offline against the repository's official engine, and carries source, upstream,
version, license, upstream/executable payload fingerprints in its NOTICE and the manifest. No private
observations, hidden information, external weights, or network access are used.

## Reproduce

```bash
python3 scripts/audit_metagame_cv.py eval/manifests/sot-2538-entity-time-cv.json
python3 scripts/run_metagame_cv.py \
  --manifest eval/manifests/sot-2538-entity-time-cv.json \
  --raw-dir artifacts/sot-2538/raw \
  --output artifacts/sot-2538/baseline-summary.json
```

The baseline runs every assigned opponent in both semantic seats at equal one-seed budget. Confirm is
authorized only by a passing screen receipt. The gate requires strict pooled improvement, no per-opponent
or per-seat regression, zero faults and unfinished matches, mean runtime within 1.10x, and every match
below 600 seconds. An identical candidate therefore fails closed and can never open confirm.
