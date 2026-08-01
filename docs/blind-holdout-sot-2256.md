# SOT-2256 third-cycle champion audit and submission decision

## Frozen terminal provenance

SOT-2255 ended at merge commit `2f0921d` after
`bounded-public-setup-continuation` (candidate commit `5418e86`) failed the
preregistered matsu non-regression gate. The terminal identity is therefore
the retained `champion`, with behavior commit `fd09f65`, `main.py` SHA-256
`043fa984...`, and `deck.csv` SHA-256 `e92d5717...`.

Before evaluation, the manifest froze blind seeds `2256101..2256105`, the
five opponent commits/decks, and both-seat reversal. The seeds do not overlap
SOT-2254 diagnosis (`2254101..2254103`), SOT-2255 screen
(`2255101..2255102`), or its unused confirm reservation
(`2255201..2255205`).

## Real-engine blind holdout

| Pool / opponent | W-L | Win rate | Wilson 95% CI |
| --- | ---: | ---: | ---: |
| fixed pool | 20-10 | 66.7% | 48.8%-80.8% |
| matsu (worst fixed) | 3-7 | 30.0% | 10.8%-60.3% |
| diversified pool | 6-14 | 30.0% | 14.5%-51.9% |
| Claude (worst diversified) | 2-8 | 20.0% | 5.7%-51.0% |
| worst-matchup pair | 5-15 | 25.0% | 11.2%-46.9% |
| **all opponents** | **26-24** | **52.0%** | **38.5%-65.2%** |

Across 50 matches, first-seat win rate was 60.0% and second-seat win rate was
44.0%. There were zero semantic faults, unfinished games, and illegal-action
faults. Whole-match runtime was mean 15.02s, p50 13.91s, p95 32.03s, and max
38.79s, below the 600-second limit. The blind result independently reproduces
the known matsu/Claude weakness; it does not change the already-final SOT-2255
promotion decision.

## Artifact and submission contract

The isolated submission exec check passed. Two deterministic builds were
byte-identical: archive SHA-256 `c3b9f8cc...`, canonical content fingerprint
`c99faf21...`. Archive entries map uniquely to `main.py` SHA-256
`043fa984...` and `deck.csv` SHA-256 `e92d5717...`.

The approved control-plane helper was executed with `--execute`. Its
fingerprint gate detected that this unchanged champion archive had already
been submitted today and safely skipped a duplicate. The matching latest
submission is ref `55154527`, status `COMPLETE`, public score **529.4**. A new
submission becomes eligible only after a genuinely changed artifact receives
a new fingerprint and passes the same holdout, exec, archive, and helper gates.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-opponent-repo> \
  --label <label> --seeds 5 --base-seed 2256101 \
  --json artifacts/sot-2256/holdout/<label>.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2256.py \
  eval/manifests/sot-2256-blind-holdout.json \
  --output artifacts/sot-2256-summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2256/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
```
