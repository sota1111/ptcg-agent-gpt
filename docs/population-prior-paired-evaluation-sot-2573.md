# SOT-2573 population-prior paired evaluation

The evaluation contract was frozen in commit `744566c` before any real-engine result was opened. It
pins the unchanged champion, the default-disabled SOT-2572 prior code/artifact/config/training receipt,
the SOT-2571 population and CV contracts, independent screen/confirm windows and entities, fresh phase
seeds, both seats, equal resource budgets, and the full strict gate. Kaggle submission is forbidden.

## Screen: passed

Screen seed `2573201` ran champion and candidate for both seats against `take` (prize-race-mewtwo) and
`search-alakazam-v12` (search-alakazam). The champion won 2/4 and the candidate won 3/4. The candidate
did not regress either opponent/archetype or either seat, recorded zero faults and zero unfinished
matches, and used a 0.854 mean-runtime ratio (candidate 19.556 s, champion 22.910 s). The machine gate
passed, authorizing confirm. The screen decision SHA-256 is
`0e7a178377955aa02cf82790f92700ff5ede209e18827310a669f80f76508627`.

## Independent confirm: rejected

Confirm seed `2573301` used the independent confirm window and fresh entities: `ume`
(stw-energy-25) and `claude` (kyogre-consistency). The champion won 3/4 while the candidate won 2/4.
The candidate regressed against ume/stw-energy-25 (1/2 versus 2/2), regressed from seat 1 (0/2 versus
1/2), and had a 1.424 mean-runtime ratio, above the 1.10 limit. Both identities still completed every
match with zero faults and zero unfinished games. Confirm therefore rejected the candidate. The confirm
decision SHA-256 is `ffeeb385dcdd75fcd8d55cfd16021c99cb815b8c1c174c12dab78edc14354a14`.

## Decision, lineage, and revert

The champion remains active and the candidate remains default-disabled; no code revert is required
because evaluation activation was environment-gated and never changed the default. No candidate
handoff was emitted. Each raw report records phase, opponent, archetype, policy/deck entity,
submission lineage, agent seeds, and semantic seats, and each decision embeds all raw-report hashes.
No compatible public ordering was supplied, so CV controlled pessimistically. No Kaggle submission was
performed.

Evidence is stored under `artifacts/sot-2573/`: `screen-decision.json`, `confirm-decision.json`, and the
eight raw real-engine reports in `raw/`.
