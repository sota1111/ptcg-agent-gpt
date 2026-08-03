# SOT-2347 terminal public-value-model artifact audit

## Frozen terminal and isolation

SOT-2346 rejected `public-value-linear-blend-v1` because confirm tied the champion aggregate
11/18 while regressing the matsu matchup and second seat. Candidate behavior was disabled, so this
audit evaluates the retained champion. Before opening results, the manifest froze five unused seeds
(`2347101..2347105`), both seats, five opponent commits/decks, and explicit exclusions for every
SOT-2346 screen/confirm artifact and seed.

## Blind result

The 50 real-engine matches finished 31-19 (62%). Fixed-pool performance was 19-11 (63.3%) and the
diversified pool was 12-8 (60%). The worst matchup was take at 4-6. First-seat and second-seat rates
were 72% and 52%. There were no faults, illegal actions, or unfinished games; maximum whole-match
runtime was 40.55 seconds against the preregistered 600-second gate. All operational gates passed.

## Exact artifact handoff

Two builds were byte-identical. The exact `submission.tar.gz` has archive SHA-256
`94461a7306daf411f32b6009c4a59d3c574da9646f7e5872d0101e57ef9c9017` and canonical content
SHA-256 `2bc66b4c3d6e51fd11251aedca21fb1ff587101b87cd6675567854ba8c6d6acd`.
Its `main.py` and `deck.csv` hashes match the frozen terminal, and isolated exec-style import passed.

`artifacts/sot-2347/handoff.json` is the sole machine-readable parent contract. It binds the retained
champion decision, manifest/summary fingerprints, blind gates, archive/source/deck identities, and
submission eligibility. This child did not execute a Kaggle submission.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> --label <label> \
  --seeds 5 --base-seed 2347101 --json artifacts/sot-2347/holdout/<label>.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2347.py \
  eval/manifests/sot-2347-blind-holdout.json --output artifacts/sot-2347/summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2347/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
```
