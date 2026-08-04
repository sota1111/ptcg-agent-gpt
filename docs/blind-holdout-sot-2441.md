# SOT-2441 tactical terminal artifact blind audit

## Frozen terminal and isolation

SOT-2440 rejected the public tactical-controller candidate because the `obo` matchup and mean runtime regressed at the paired screen, so this audit evaluates the retained champion. Before holdout results were opened, commit `71a8632` froze five seeds unused by SOT-2439/2440 (`2441101..2441105`), both seats, five opponent revisions/decks, and source/screen/confirm artifact exclusions. The full SOT-2440 merge identity was corrected from a mistyped long hash to the already-frozen short commit `dbbe452` before summary generation. Candidate behavior remains disabled in normal and Kaggle execution.

## Blind result

The 50 real-engine matches finished 32-18 (64%). Fixed-pool performance was 18-12 (60%) and diversified performance was 14-6 (70%). The worst matchup was matsu at 4-6. First-seat and second-seat rates were 84% and 44%. There were no faults, illegal actions, or unfinished games; maximum whole-match runtime was 50.00 seconds against the 600-second gate. All operational audit gates passed.

## Exact parent handoff

Two deterministic builds were byte-identical. The exact `submission.tar.gz` has archive SHA-256 `e528f57e16068c6f3947063d74c6fe552c561207f7cd2a0bb2e2e42d27a1adda` and canonical content SHA-256 `186744e97227881a84b3ca931fab8e24c3bbf9a7052d496e13569f1f9a7ac698`. Top-level `main.py`, offline import, and isolated exec-style verification passed.

`artifacts/sot-2441/handoff.json` is the machine-readable fingerprint gate for parent SOT-2434. It binds the SOT-2440 screen-failure decision, champion identity, blind matchup/seat/reliability/runtime evidence, archive/source identities, and exact artifact path. This child did not execute a Kaggle submission; only the parent may decide or perform submission.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> --label <label> --seeds 5 --base-seed 2441101 --json artifacts/sot-2441/holdout/<label>.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2441.py eval/manifests/sot-2441-blind-holdout.json --output artifacts/sot-2441/summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz --output artifacts/sot-2441/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
```
