# SOT-2401 belief terminal artifact blind audit

## Frozen terminal and isolation

SOT-2400 rejected the public-history belief candidate at the reanchored paired screen because the take matchup regressed, so this audit evaluates the retained champion. Before results were opened, commit `c93c4ef` froze five seeds unused by SOT-2399/2400 (`2401101..2401105`), both seats, five opponent revisions/decks, and exclusions for the reanchoring and belief screen artifacts. The belief module remains evidence only and is disabled in normal and Kaggle execution.

## Blind result

The 50 real-engine matches finished 28-22 (56%). Fixed-pool performance was 13-17 (43.3%) and diversified performance was 15-5 (75%). The worst matchup was matsu at 3-7. First-seat and second-seat rates were 72% and 40%. There were no faults, illegal actions, or unfinished games; maximum whole-match runtime was 39.11 seconds against the 600-second gate. All operational audit gates passed.

## Exact parent handoff

Two deterministic builds were byte-identical. The exact `submission.tar.gz` has archive SHA-256 `621a3d113002400d1b4257d9f17e51cdb6ff4797d1aeadbbb5d9f82738bdd221` and canonical content SHA-256 `32c3affee78cdc95eab31bc1620f24fa04fa37911efa4fc8edd408b771fb443f`. Top-level `main.py`, offline import, and isolated exec-style verification passed.

`artifacts/sot-2401/handoff.json` is the machine-readable fingerprint gate for parent SOT-2398. It binds the champion identity, blind matchup/seat/reliability/runtime evidence, archive/source identities, and exact artifact path. This child did not execute a Kaggle submission; only the parent may decide or perform submission.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> --label <label> --seeds 5 --base-seed 2401101 --json artifacts/sot-2401/holdout/<label>.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2401.py eval/manifests/sot-2401-blind-holdout.json --output artifacts/sot-2401/summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz --output artifacts/sot-2401/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
```
