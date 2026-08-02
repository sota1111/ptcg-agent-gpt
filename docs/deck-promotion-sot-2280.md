# SOT-2280 deck candidate screen → confirm decision

## Frozen protocol

SOT-2279 produced three legal, composition-distinct one-card deck candidates. This decision
reuses its frozen screen reports and opponent fingerprints, then applies one gate consistently:
the candidate must strictly improve aggregate pool win rate, must not regress either reproduced
worst matchup (`matsu` and `claude`), must not increase faults or unfinished matches, and every
match must remain below 600 seconds. Champion and candidates use the same fixed pool
(`matsu`, `take`, `ume`), diversified pool (`claude`, `obo`), seeds, and both seats within each
phase. Confirm uses fresh seeds `2280101..2280105`, disjoint from screen seed `2279101`.

The manifest, input hashes, raw-report hashes, phase protocol, per-seat KPI, per-opponent KPI,
runtime KPI, and gate reasons are machine-readable in
`artifacts/sot-2280-deck-promotion/decision.json`.

## Screen

| Candidate | Pool wins | matsu | Claude | Gate |
| --- | ---: | ---: | ---: | --- |
| champion | 4/10 | 1/2 | 0/2 | reference |
| Kyogre consistency | 5/10 | 0/2 | 1/2 | reject: matsu regressed |
| Suicune energy scaling | 3/10 | 0/2 | 1/2 | reject: pool and matsu regressed |
| Wellspring bench pressure | 7/10 | 2/2 | 0/2 | confirm |

Only Wellspring advanced. This is stricter than the source SOT-2279 preliminary summary because
the two named worst matchups are checked individually rather than pooled together.

## Independent confirm

Each identity ran 50 real-engine matches: five opponents × five fresh seeds × both seats.

| Identity | Pool | First seat | Second seat | matsu | Claude | Fault / unfinished | Max runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| champion | 28/50 (56%) | 68% | 44% | 6/10 | 4/10 | 0 / 0 | 44.08s |
| Wellspring | 32/50 (64%) | 72% | 56% | 3/10 | 7/10 | 0 / 0 | 43.15s |

Wellspring strictly improved the aggregate KPI and Claude matchup, with no fault, timeout, or
seat regression. It nevertheless failed the preregistered gate because matsu fell from 60% to
30%. The confirm result therefore does not generalize across both reproduced worst matchups.

## Decision

No candidate is promoted. `deck.csv` was never replaced and remains the champion with SHA-256
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`, identical before and
after the decision. Submission build and exec-style loading are verified separately by the
quality gate; this Issue performs no Kaggle submission.
