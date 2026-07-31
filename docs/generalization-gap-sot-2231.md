# SOT-2231 fixed-pool/Kaggle generalization-gap diagnosis

## Frozen provenance

The retained champion is behavior commit `fd09f65`; terminal `origin/main` was
`63f462d` before this diagnostic. `main.py`, `deck.csv`, and the submission
archive remain respectively SHA-256 `043fa984…`, `e92d5717…`, and
`c1a9c99b…`. The complete values and the frozen opponent identities are in
`eval/manifests/sot-2231-generalization-gap.json`.

Kaggle's live submission ledger reports the last three automated GPT-lineage
submissions as 571.7 (`55058190`), 557.9 (`55085406`), and 521.0 (`55130939`).
This replaces the issue's provisional 550.7 endpoint with the authoritative
completed submission value. Those automated rows did not preserve artifact
fingerprints, so source commit and `main.py`/deck/archive hashes are explicitly
`unknown`; they are not inferred from the current archive.

## Reproducible diversified pool

The public seven-repository runtime inventory was deduplicated by
`(main.py SHA-256, deck.csv SHA-256)`. Matsu, Take, and Ume remain the fixed
baseline. Claude and Obo are the two additional runnable, distinct public
variants. Zero is recorded but excluded because its public checkout cannot
start without the uninstalled NumPy dependency.

Five previously unused seeds (`2231101..2231105`) were run from both seats
against each new opponent. Planner fingerprints were stripped during capture;
the retained trace contains public-state telemetry only.

| Pool / opponent | W-L | Win rate | Wilson 95% CI | First / second wins |
| --- | ---: | ---: | ---: | ---: |
| fixed matsu/take/ume | 69-51 | 57.5% | prior summary | 47 / 22 |
| Claude | 3-7 | 30.0% | 10.8–60.3% | 1 / 2 |
| Obo | 7-3 | 70.0% | 39.7–89.2% | 4 / 3 |
| **diversified pool** | **10-10** | **50.0%** | **29.9–70.1%** | **5 / 5** |

The measured generalization gap is 7.5 percentage points. It is matchup
specific rather than a uniform seat effect: the diversified aggregate has no
seat gap, while Claude exposes a 27.5-point drop from the fixed-pool rate.
All 20 matches completed with zero champion faults, unfinished games, or
illegal actions. Mean runtime was 16.29s and p95 was 32.05s.

## Exclusive public-information loss diagnosis

The deterministic classifier assigns every diversified loss once, using only
public board/choice telemetry: policy calibration 8/10, matchup robustness
1/10, pool coverage 1/10, package provenance 0/10, and unclassifiable 0/10.
The result supports a policy/matchup explanation for the local gap. It cannot
causally attribute Kaggle's hidden-opponent score movement; missing historical
artifact fingerprints remain a provenance uncertainty rather than fabricated
evidence.

## Independent next screens

1. `cross-lineage-matchup-value-calibration`: change only leaf evaluation for
   public board-energy or attack-readiness disadvantage. This is new evidence
   from 8/10 diversified losses, distinct from the rejected SOT-2175 generic
   seat-tempo weights.
2. `opponent-family-balanced-root-selection`: change only the public
   opponent-family prior used for root action selection. The Claude 30% result
   motivates matchup-specific calibration without retrying prior root cap or
   prior-temperature sweeps.
3. `diversified-pool-screen-gate`: change only the promotion evaluation gate
   by adding this frozen pool as a non-regression unit. This is evaluation
   coverage, not another median/trimmed-mean, `n_worlds`, fallback, deck, or
   behavior proposal.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent /workspaces/ptcg-agent-claude \
  --label claude --seeds 5 --base-seed 2231101 --public-telemetry-only \
  --json artifacts/sot-2231/diversified/claude.json
.venv/bin/python eval/battle_vs.py --opponent /workspaces/ptcg-agent-obo \
  --label obo --seeds 5 --base-seed 2231101 --public-telemetry-only \
  --json artifacts/sot-2231/diversified/obo.json
.venv/bin/python scripts/analyze_generalization_gap.py \
  eval/manifests/sot-2231-generalization-gap.json \
  --output artifacts/sot-2231-summary.json
```
