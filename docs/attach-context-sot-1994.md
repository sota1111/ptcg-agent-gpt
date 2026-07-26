# SOT-1994 attach-context promotion decision

`ATTACH_FROM` and `ATTACH_TO` were the remaining high-frequency attachment
contexts that delegated ordering to generic card value. This experiment uses
only public observation fields: board area, attached Energy count, HP, and
card-master attack costs.

## Candidate semantics

- `ATTACH_FROM` preserves the Active attacker, prefers a benched source, and
  then prefers Energy surplus beyond that Pokémon's cheapest attack cost.
- `ATTACH_TO` first completes an attack-ready recipient, then prefers the
  Active and the smallest remaining visible attack-energy gap. HP is only a
  deterministic tie-break.
- An unresolved/non-board option retains the prior deterministic card-value
  ordering. Other contexts and the search implementation are unchanged.

## Fixed-seed screen

Both runs used `base_seed=20260726`, five agent seeds, the frozen
`eval/hash_baseline` opponent pool, and seat reversal for ten matches.

```bash
venv/bin/python eval/battle_vs.py --seeds 5 --base-seed 20260726 \
  --json artifacts/sot-1994-screen-before.json
venv/bin/python eval/battle_vs.py --seeds 5 --base-seed 20260726 \
  --json artifacts/sot-1994-screen-after.json
```

| measure | champion before | candidate after |
| --- | ---: | ---: |
| target generic-ordering fallbacks | 18 | 0 |
| wins / matches vs hash baseline | 9 / 10 | 10 / 10 |
| semantic faults | 0 | 0 |
| unfinished matches | 0 | 0 |
| max think time per match | 20.49 s | 20.17 s |

The screen passed: the target fallback count fell to zero, the same-pool KPI
improved, and fault, timeout, and runtime gates did not regress.

## Confirm

The gated confirm used the same opponent, seed base, and seat reversal with
20 agent seeds (40 matches):

```bash
venv/bin/python eval/battle_vs.py --seeds 20 --base-seed 20260726 \
  --json artifacts/sot-1994-confirm-after.json
```

The candidate finished 39–1 (97.5%), with a Wilson 95% interval of
87.12%–99.56%, zero faults, zero unfinished matches, and 29.27 seconds maximum
think time per match against the 600-second allowance. The machine promotion
gate returned `{"promote": true, "reasons": []}`.

## Decision

**Promote.** The explicit attachment semantics remain in the root champion.
The before/after and confirm JSON artifacts are committed with this decision.
`scripts/verify_submission_exec.py submission.tar.gz` passed. Kaggle
submission `55005907` completed with public score **600.0**, improving the
previous ptcg-agent-gpt score of 545.7. This confirms that champion behavior
and the promotion conclusion agree.
