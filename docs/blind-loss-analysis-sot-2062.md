# SOT-2062 blind champion loss analysis

The frozen champion is `0d652a59a206bf9cce61453645741e60adafd3e1`.
Its submission entry point, deck, engine, search configuration, opponent
commits/decks, and previously unused agent seeds `2062301..2062306` are fixed
in `eval/manifests/sot-2062-blind.json`. Each seed was evaluated from both
seats against the frozen matsu, take, and ume opponents.

## Result

The real-engine run completed all 36 matches: 23 wins and 13 losses, with no
draws, faults, or unfinished matches. Runtime was 14.03 seconds mean, 14.99
seconds p50, 23.57 seconds p95, and 27.17 seconds maximum. The machine-readable
classification is `artifacts/sot-2062-blind-loss-analysis.json`; its SHA-256 is
`4c83def2b1b68296fd244ba72f7c51c155ec549d8dbca116c3de05bbb5cdcc27`.

| Opponent | Result | Faults | Unfinished |
| --- | ---: | ---: | ---: |
| matsu | 7–5 | 0 | 0 |
| take | 8–4 | 0 | 0 |
| ume | 8–4 | 0 | 0 |

## Loss classification

Classification uses only observable trace evidence and assigns one category
per loss. The raw reports retain matchup, seat, seed, terminal state,
selection-context counts, root option width, think time, and runtime. Rules
are evaluated from direct evidence toward progressively weaker proxies, and
each loss records its confidence and evidence.

| Category | Losses | Loss share | Estimated all-match contribution |
| --- | ---: | ---: | ---: |
| candidate prior / root pruning | 9 | 69.23% | 25.00% |
| determinization / seat bias | 3 | 23.08% | 8.33% |
| unclassified | 1 | 7.69% | 2.78% |
| fallback/fault, deck-out, time governor, rollout-value proxy | 0 | 0% | 0% |

The maximum observed bottleneck is therefore **root candidate prior/pruning**:
9 of 13 losses contained at least three decisions whose legal option count
exceeded the champion's `max_root_actions=6`. This is a diagnostic association,
not a causal promotion claim; the next issue must isolate prior scoring from
the root cap under the common screen/confirm gate.

The unclassified rate is 7.69%. Three additional losses changed outcome for
the same agent seed under seat reversal and are assigned to the
determinization/seat-bias candidate with medium confidence. No observed loss
supports reopening rollout-value calibration in this run.

## Ranked next candidates

1. `root-candidate-prior`: compare root prior scoring and
   `max_root_actions` independently while leaving the total search budget
   frozen.
2. `determinization-diversity`: compare world-sampling diversity at the same
   total budget and the same pool.

Fallback semantics from SOT-1994/SOT-1995 are excluded because faults and
fallback evidence are zero. The SOT-1996 search-budget/time-governor work is
excluded because cumulative think time remained far below its 300-second
threshold and there were no timeouts. SOT-2054/SOT-2056/SOT-2057 meta-deck
reconfiguration remains an independent in-progress workstream; this
diagnostic does not change decks or use deck composition as a candidate.

## Reproduction and behavior integrity

Regenerate the byte-identical aggregate from the frozen raw reports:

```bash
python3 scripts/analyze_blind_losses.py \
  --manifest eval/manifests/sot-2062-blind.json \
  --output artifacts/sot-2062-blind-loss-analysis.json
```

Two consecutive regenerations were compared byte-for-byte. The champion
entry point and deck were not modified; only evaluation telemetry, analysis,
tests, raw reports, and this conclusion document were added.
