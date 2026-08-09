# SOT-2571 archetype-conditioned population distillation contract

This change freezes an experiment contract; it does not train or enable a candidate and does not submit
to Kaggle. The population snapshot covers established and emerging archetypes across multiple policy
and deck entities. It inherits SOT-2553's entity, policy, deck, match, seed, time, evidence, replay, and
submission-lineage isolation. The snapshot additionally makes archetype, policy entity, deck entity,
evidence, lineage, and split membership machine-readable.

Only facts reconstructible from the current public observation may condition archetype features. The
allow-list includes public boards, discard, stadium, revealed cards, legal actions, turn/prize/zone
counts, and deterministic inference from revealed card IDs. Hidden cards or order, opponent/policy/deck
identity, evaluation metadata, seeds, lineage, future replay/popularity, and private ratings are denied.
An unrecognized public pattern maps to `unknown` rather than guessing an identity.

Replay popularity weights may be fitted and read only in `train`. Screen, confirm, and blind use the
frozen population uniformly and cannot access fitted popularity. Portable assets require an allowed
license and provenance. Raw replay inputs are explicitly non-portable training-only evidence and cannot
enter the runtime artifact.

The candidate stays disabled. Screen must independently pass before confirm, and confirm must pass
before blind. Champion and candidate use the same budget and both seats. Promotion requires strict
pooled improvement, no archetype/matchup/seat regression, zero faults and unfinished matches, bounded
runtime, and a fingerprinted offline-importable exec-compatible artifact. Any failed gate retains the
champion and preserves the contract and decision documentation.

## Reproduce

```bash
.venv/bin/python scripts/audit_archetype_population_sot_2571.py \
  eval/manifests/sot-2571-archetype-population.json
.venv/bin/pytest -q tests/test_archetype_population_sot_2571.py
```

The audit output includes deterministic canonical contract and byte-exact population fingerprints plus
every cross-split overlap set. No command in this contract performs a Kaggle submission.
