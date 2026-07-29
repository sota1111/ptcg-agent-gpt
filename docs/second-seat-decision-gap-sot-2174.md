# SOT-2174 second-seat decision-gap diagnosis

## Frozen provenance and method

The machine-readable manifest is
`eval/manifests/sot-2174-second-seat-gap.json`. It freezes `origin/main`
commit `61a7f14`, champion behavior commit `fd09f65`, `main.py` SHA-256
`41c178d95f21edfcacb1705bc8de4d998bffc5f0f62bc4aae32a477fa14f74b3`,
and `deck.csv` SHA-256
`e92d5717fd04865b0b528307df7a9d9aecc2c7b917bfbd5042fe58e3d1f26997`.
It also freezes the matsu/take/ume commits and entry-point/deck hashes.

Agent seeds `2174101..2174103` are unused by SOT-2116/2117/2118. Each seed was
run from both seats against every opponent using the real engine. The engine
has no shuffle-seed API, so replaying the command does not promise identical
shuffle outcomes; the committed raw reports preserve the actual games, and
the fixed manifest regenerates the aggregate deterministically.

The opt-in trace adds no policy input. For each champion decision it records
only public counts and flags: turn/action index, hand/bench/prize deltas,
board and active energy counts, attachment availability, attack readiness,
end-turn/attack selection, selected root rank, and world-root leaf values.
Opponent hand/prize identities and `search_begin_input` are never copied.

## Real-engine results

| Opponent | Paired matches | W-L | First-seat wins | Second-seat wins | Fault / unfinished | Mean runtime |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| matsu | 6 | 4-2 | 3/3 | 1/3 | 0 / 0 | 11.04s |
| take | 6 | 6-0 | 3/3 | 3/3 | 0 / 0 | 10.60s |
| ume | 6 | 3-3 | 2/3 | 1/3 | 0 / 0 | 11.92s |
| **Pool** | **18** | **13-5** | **8/9 (88.9%)** | **5/9 (55.6%)** | **0 / 0** | **11.19s** |

The diagnostic sample reproduces a 33.3 percentage-point first/second gap.
All 18 games have outcome, seat, fault, unfinished, runtime, public state,
selected action rank, and root leaf-evaluation traces.

## Exclusive second-seat loss classification

All four second-seat losses fall into **setup/energy tempo**. Their mean
early public board-energy deficits were `-0.600`, `-0.667`, `-0.500`, and
`-0.500`. Every loss also had a negative early active-energy
delta. No loss reached the later exclusive classes: attack timing, resource
conservation, seat-independent, or unclassifiable.

This is evidence for an observable tempo gap, not proof of causality. The
sample is deliberately small and the engine shuffle is not seedable.

## Next independent one-change candidates

1. **Public board-energy tempo evaluation.** Add only the early observable
   board-energy delta to leaf evaluation. Basis: 4/4 second-seat losses had a
   negative mean early board-energy delta.
2. **Public attack-readiness pressure evaluation.** Add only the opponent's
   observable active-energy/attack-readiness pressure to leaf evaluation.
   Basis: 4/4 losses had a negative mean early active-energy delta.

These are separate evaluation terms and should be screened one at a time.
Median/trimmed-mean aggregation, `n_worlds` allocation, root cap/prior
temperature, fallback semantics, and deck restructuring remain excluded
because this trace adds no evidence for retrying them.

## Reproduction and invariance

Check out the opponent commits from the manifest, then run:

```bash
python3 eval/battle_vs.py --public-telemetry-only --opponent <matsu-worktree> --label matsu \
  --seeds 3 --base-seed 2174101 --json artifacts/sot-2174/paired-matsu.json
python3 eval/battle_vs.py --public-telemetry-only --opponent <take-worktree> --label take \
  --seeds 3 --base-seed 2174101 --json artifacts/sot-2174/paired-take.json
python3 eval/battle_vs.py --public-telemetry-only --opponent <ume-worktree> --label ume \
  --seeds 3 --base-seed 2174101 --json artifacts/sot-2174/paired-ume.json
python3 scripts/analyze_second_seat_gap.py \
  --manifest eval/manifests/sot-2174-second-seat-gap.json \
  --output artifacts/sot-2174-summary.json
```

After collection, `main.py` and `deck.csv` retain their frozen hashes.
Champion action selection and deck composition are unchanged; only
evaluation telemetry, raw artifacts, aggregation, tests, and this diagnosis
were added.
