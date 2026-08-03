# SOT-2378 action-ranking terminal artifact blind audit

## Frozen terminal and isolation

SOT-2377 rejected the pairwise action-ranking candidate at screen, so this audit evaluates the retained champion. Before results were opened, commit `5ffd11e` froze five seeds unused by SOT-2376/2377 (`2378101..2378105`), both seats, five opponent revisions/decks, and exclusions for the source oracle and screen artifacts. The candidate artifact remains evidence only and is not loaded by normal or Kaggle execution.

## Blind result

The 50 real-engine matches finished 25-25 (50%). Fixed-pool performance was 18-12 (60%) and diversified performance was 7-13 (35%). The worst matchup was claude at 3-7. First-seat and second-seat rates were 64% and 36%. There were no faults, illegal actions, or unfinished games; maximum whole-match runtime was 40.81 seconds against the 600-second gate. All operational audit gates passed.

## Exact parent handoff

Two deterministic builds were byte-identical. The exact `submission.tar.gz` has archive SHA-256 `94461a7306daf411f32b6009c4a59d3c574da9646f7e5872d0101e57ef9c9017` and canonical content SHA-256 `2bc66b4c3d6e51fd11251aedca21fb1ff587101b87cd6675567854ba8c6d6acd`. Isolated exec-style verification passed.

`artifacts/sot-2378/handoff.json` is the machine-readable fingerprint gate for parent SOT-2364. It binds the champion identity, blind matchup/seat/reliability/runtime evidence, archive/source identities, and exact artifact path. This child did not execute a Kaggle submission; only the parent may decide or perform submission.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> --label <label> --seeds 5 --base-seed 2378101 --json artifacts/sot-2378/holdout/<label>.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2378.py eval/manifests/sot-2378-blind-holdout.json --output artifacts/sot-2378/summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz --output artifacts/sot-2378/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
```
