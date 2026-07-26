# SOT-1995 draw-count and bench-context promotion decision

The baseline is the SOT-1994 terminal champion at merge commit `986798d`
(feature commit `96ec61f`). Its root `main.py`, search parameters, attachment
rules, and `deck.csv` are unchanged by this experiment.

## Candidate semantics

- `DRAW_COUNT` ranks the available draw quantities toward a seven-card hand,
  capped by the existing six-card deck reserve. At or below the reserve it
  explicitly takes the smallest offered draw.
- `SETUP_BENCH` ranks public card attributes by expansion value (attack
  output and ability) minus exposure risk (extra prizes, attack-energy cost,
  and low HP).
- Search, attachment rules, and the deck are unchanged.

## Fixed-seed screen

Both runs used `base_seed=20260726`, five agent seeds, the frozen
`eval/hash_baseline` opponent pool, and seat reversal for ten matches.

```bash
uv run --extra dev python eval/battle_vs.py --seeds 5 --base-seed 20260726 \
  --json artifacts/sot-1995-screen-before.json
uv run --extra dev python eval/battle_vs.py --seeds 5 --base-seed 20260726 \
  --json artifacts/sot-1995-screen-after.json
```

| measure | champion before | candidate after |
| --- | ---: | ---: |
| target generic-ordering fallbacks | 10 | 0 |
| wins / matches vs hash baseline | 10 / 10 | 10 / 10 |
| semantic faults | 0 | 0 |
| unfinished matches | 0 | 0 |
| max think time per match | 34.44 s | 15.37 s |

The screen passed: target fallbacks fell to zero, the same-pool KPI held,
faults and unfinished matches did not increase, and runtime improved.

## Confirm

The gated confirm used the same opponent, seed base, and seat reversal with
20 agent seeds (40 matches):

```bash
uv run --extra dev python eval/battle_vs.py --seeds 20 --base-seed 20260726 \
  --json artifacts/sot-1995-confirm-after.json
```

The candidate finished 40–0 (100%), with a Wilson 95% interval of
91.24%–100%, zero faults, zero unfinished matches, and 28.05 seconds maximum
think time per match against the 600-second allowance. The machine promotion
gate returned `{"promote": true, "reasons": []}`.

## Decision

**Promote.** The explicit draw-count and bench-setup semantics remain in the
root champion. The before/after and confirm JSON artifacts are committed with
this decision. `scripts/verify_submission_exec.py submission.tar.gz` passed.
Kaggle submission `55006489` completed with public score **600.0**, improving
the SOT-1994 terminal champion submission `55005907` score of 399.1. Champion
behavior and the conclusion agree.
