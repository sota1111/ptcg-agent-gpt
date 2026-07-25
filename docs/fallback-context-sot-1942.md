# SOT-1942 fallback-context trace and promotion decision

The SOT-1939 real-engine A/B harness was extended to count every decision
context made by the semantic agent. A context is reported as a fallback hole
when option ordering still delegates to generic card scoring rather than an
explicit context rule. Selection counts were already explicit for all 49
shipped contexts.

## Screen

Command:

```bash
venv/bin/python eval/battle_vs.py \
  --seeds 5 \
  --base-seed 20260725 \
  --json artifacts/sot-1942-screen-before.json
```

The 10-match before screen observed 51 generic-ordering decisions. The two
most frequent holes were:

| context | before fallback decisions |
| --- | ---: |
| `TO_HAND` (7) | 25 |
| `DISCARD_ENERGY` (30) | 13 |

The patch makes both intentions explicit: `TO_HAND` takes the highest-value
card, while `DISCARD_ENERGY` pays the smallest Energy count. These rules
preserve the prior safe ordering while removing ambiguity from the fallback
path.

The 10-match after screen observed both target contexts 46 times
(`TO_HAND` 28, `DISCARD_ENERGY` 18) with zero target-context fallbacks. It
finished 10-0 against the frozen hash baseline, with no faults or unfinished
matches.

## Confirm

Command:

```bash
venv/bin/python eval/battle_vs.py \
  --seeds 20 \
  --base-seed 20260725 \
  --json artifacts/sot-1942-confirm-after.json
```

The confirm trace provides a same-run before/after coverage comparison:

| measure | before rules (derived) | after rules |
| --- | ---: | ---: |
| `TO_HAND` fallback | 85 | 0 |
| `DISCARD_ENERGY` fallback | 40 | 0 |
| all generic-ordering fallbacks | 198 | 73 |

The remaining 73 decisions are lower-frequency contexts (`ATTACH_FROM`,
`ATTACH_TO`, `DRAW_COUNT`, and `SETUP_BENCH`) and are intentionally out of
scope for this minimal patch.

The candidate beat the frozen SOT-1939 hash baseline 38-2 over 40 matches:
95.0% win rate, Wilson 95% CI 83.50%-98.62%, zero agent faults, and zero
unfinished matches. The existing promotion gate passed, so the two rules are
promoted.
