# SOT-2555 counter-meta paired screen decision

The evaluation contract was frozen in commit `58eae07` before screen results were opened. It pins the
unchanged champion, the SOT-2554 candidate policy/deck/source hashes, the SOT-2553 recalibrated split,
fresh phase seeds, both seats, equal 2 vCPU / 12.2 GiB / 600-second budgets, and the complete strict
promotion gate. The candidate remains opt-in through the evaluation server and disabled in normal and
Kaggle execution.

## Real-engine screen

The fresh screen seed `2555201` ran one paired seed (both seats) against each opponent in the SOT-2553
screen split: `take` and `search-alakazam-v12`. The champion won 2/4 overall (take 2/2,
search-alakazam-v12 0/2; seat 0 1/2, seat 1 1/2). The candidate won 0/4 (0/2 against each opponent and
0/2 from each seat). Both identities completed all matches with zero faults and zero unfinished games.
Champion mean/max runtime was 17.947/31.428 seconds; candidate mean/max runtime was 0.038/0.054 seconds,
for a 0.0021 mean-runtime ratio.

The screen failed because pooled wins did not strictly improve, take regressed, and both seats
regressed. The machine decision is `retain-champion`; `nextPhase` and `candidateArtifact` are null.
Confirm was therefore not opened. The SOT-2554 configuration remains `enabledByDefault: false`; there
is no revert patch because no default behavior was changed.

## CV and public sanity

No compatible public rating was available for the frozen pair. The report records public sanity as
unavailable and selects the CV order pessimistically. Public-best selection is explicitly forbidden;
the real-engine CV rejection controls the decision.

## Evidence

- `artifacts/sot-2555/screen-decision.json` — SHA-256
  `85395d273c265f54bc89b69d81913a769a890ced64b3daae63cc413ca3226dfd`
- `artifacts/sot-2555/raw/` — four real-engine raw reports; their individual SHA-256 values are embedded
  in the decision artifact.
- Candidate status: rejected; champion retained; candidate default disabled.
- Confirm: skipped by the fail-closed screen gate.
- Kaggle submission: not performed.
