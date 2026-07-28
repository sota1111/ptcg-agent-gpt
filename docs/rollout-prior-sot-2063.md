# SOT-2063 rollout and action-prior promotion decision

The frozen champion is the SOT-2062 terminal Sol MCTS at merge commit
`dbdd945` (`main.py` `SOL_CONFIG` with `max_root_actions=6`, one-ply tree,
100 rollout turns, four worlds, 0.8-second budget, `deviate_margin=0.1`, and
`prior_temperature=40`). The deck, total search budget, and processed fallback
rules were held fixed; only the root candidate-prior lever changed. This
follows SOT-2062, whose blind loss analysis ranked **root candidate
prior/pruning** as the largest loss bucket and required isolating the prior
score from the root cap under a common screen/confirm gate.

## Predefined candidates (one hypothesis each)

The SOT-2062 analysis named two independent root-prior levers. Each was
pre-registered as a single-hypothesis candidate; nothing else changed.

| candidate | lever | value | hypothesis |
| --- | --- | --- | --- |
| champion | `max_root_actions` | 6 | frozen baseline |
| root-cap-12 | `max_root_actions` | 6 → 12 | keep more root candidates so pruning drops fewer winning lines |
| prior-temp-20 | `prior_temperature` | 40 → 20 | sharpen the softmax prior so search concentrates on top-scored roots |

Leaf-value relearning was deliberately excluded: prior non-promotion results
(SOT-1865/SOT-1837) give no new reason to reopen it, so only publicly observed
action-prior levers were screened.

## Fixed-seed screen (base seed 2063101, 3 seeds × seat reversal = 6 matches)

| config | matsu | take | ume | pool |
| --- | ---: | ---: | ---: | ---: |
| champion (cap=6) | 4–2 | 4–2 | 2–4 | 10–8 |
| root-cap-12 | 3–3 | 5–1 | 1–5 | 9–9 |
| prior-temp-20 | 1–5 | 2–4 | 4–2 | 7–11 |

`prior-temp-20` had the worst pool KPI (7–11) and regressed both matsu and
take, so it was rejected at screen. `root-cap-12` tied the champion pool at
the noisy small-N width but carried the single strongest matchup (take 5–1),
so it alone advanced to confirm.

## Independent-seed confirm (base seed 2063201, 20 seeds × seat reversal = 40 matches)

The confirm re-measured the champion at the same seed base for a direct
apples-to-apples KPI comparison. All runs had zero faults, zero unfinished
matches, and maximum think time far below the 600-second allowance.

| config | matsu | take | ume | pool KPI | mean runtime |
| --- | ---: | ---: | ---: | ---: | ---: |
| champion (cap=6) | 20–20 (.500) | 30–10 (.750) | 21–19 (.525) | **71–49 (.592)** | 9.9–12.5 s |
| root-cap-12 | 20–20 (.500) | 23–17 (.575) | 23–17 (.575) | 66–54 (.550) | 10.4–15.3 s |

Per-matchup Wilson 95% lower bounds for `root-cap-12` are matsu 0.352, take
0.422, ume 0.422 — none exceeds 0.50 — and no matchup reaches the 60% win-rate
gate. Against the champion, the candidate is tied on matsu, **worse on take
(.575 vs .750)**, and marginally better on ume (.575 vs .525); its pool KPI
0.550 is below the champion's 0.592. It also did not improve mean runtime.

## Promotion decision

`root-cap-12` fails the common gate: it does not exceed the champion's
same-pool KPI (it is worse), and its per-matchup Wilson lower bounds do not
clear 50%. `prior-temp-20` was rejected earlier at screen. **Neither
root-prior lever is promoted.** The SOT-2062 "root candidate prior/pruning"
association is therefore diagnostic, not causal: widening the root cap does not
convert those losses — it regresses the take matchup while leaving matsu
unchanged.

The champion configuration is unchanged (`max_root_actions=6`). The
experimental `main.py` diff was reverted, so the champion state and this
non-promotion conclusion agree. Because the submission entry point and deck are
byte-identical to the already-submitted champion, no new Kaggle submission is
warranted (an unchanged archive is a duplicate).

## Reproduction

With `main.py` at the champion `max_root_actions=6`, the champion confirm is:

```bash
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-matsu --label matsu \
  --seeds 20 --base-seed 2063201 --json artifacts/sot-2063/confirm-baseline-matsu.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-take --label take \
  --seeds 20 --base-seed 2063201 --json artifacts/sot-2063/confirm-baseline-take.json
python3 eval/battle_vs.py --opponent /workspaces/ptcg-agent-ume --label ume \
  --seeds 20 --base-seed 2063201 --json artifacts/sot-2063/confirm-baseline-ume.json
```

Setting `SOL_CONFIG["max_root_actions"] = 12` and repeating with the same seed
base reproduces the `confirm-root-cap-12-*` reports. The raw per-match reports
for both configs and all screens are under `artifacts/sot-2063/` (git-ignored
telemetry). The champion `main.py` and `deck.csv` were not modified.
