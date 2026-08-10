# SOT-2592 converged finalist inventory

This audit freezes existing terminal artifacts for the SOT-2591 converge cycle. It starts no new
improvement axis and makes no Kaggle submission. The machine-readable source of truth is
`artifacts/sot-2592/finalist-inventory.json`.

## Frozen comparison contract

- Rank candidates by leak-free blind-CV evidence, using the Wilson 95% lower bound as the pessimistic
  comparison metric. Public rating is never reconstructed or copied across fingerprints.
- A finalist must prove zero entity, time, seed, and submission-lineage overlap. Missing dimensions
  fail closed; this excludes SOT-2441 and SOT-2540 from the comparable set despite valid historical
  terminal audits.
- Only retained/promoted terminal behavior is eligible. All four audited handoffs retain the champion;
  rejected opt-in candidates remain disabled.
- Artifact, manifest, summary, and fingerprint bytes are pinned by SHA-256. The audit command detects
  any later mutation.
- The competition uses relative skill rating and only the latest two submissions remain active. The
  final two-slot choice belongs to SOT-2593/SOT-2594; this child only freezes inputs and prohibits
  submission.

## Frozen finalists

| Issue | Strategy lineage | Blind CV | Wilson 95% | Content SHA-256 | Public result | Submission history |
| --- | --- | ---: | --- | --- | --- | --- |
| SOT-2556 | counter-meta retained champion | 43/50 (86%) | 73.8–93.0% | `5fda6f…a24e` | unavailable (null) | matches prior submission |
| SOT-2574 | population-policy retained champion | 16/20 (80%) | 58.4–91.9% | `07bd55…dc5e` | unavailable (null) | new, not submitted by child |

SOT-2441 lacks explicit time and submission-lineage isolation. SOT-2540 lacks explicit
submission-lineage isolation. Neither is silently backfilled from public results or newer audits.

## Audit

```bash
.venv/bin/python scripts/audit_finalist_inventory_sot_2592.py \
  artifacts/sot-2592/finalist-inventory.json
```

The command exits non-zero on a source hash change, incomplete isolation, non-zero overlap, rejected
candidate activation, child submission, fingerprint mismatch, CV mismatch, or public-result imputation.
