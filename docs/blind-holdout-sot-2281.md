# SOT-2281 fourth-cycle terminal artifact audit

## Frozen terminal and isolation

SOT-2280 retained `champion`: Wellspring bench pressure passed screen but failed confirm after
the preregistered `matsu` non-regression gate fell from 60% to 30%. The audited terminal maps to
commit `b48e5f5f`, `main.py` SHA-256 `043fa984...`, and `deck.csv` SHA-256 `e92d5717...`.

Before the blind run, `eval/manifests/sot-2281-blind-holdout.json` froze seeds
`2281101..2281105`, both seats, opponent commits/decks, and the fixed/diversified pools. These
seeds are disjoint from SOT-2279 screen seed `2279101` and SOT-2280 confirm seeds
`2280101..2280105`.

## Blind holdout result

| Pool / opponent | W-L | Win rate | Wilson 95% CI |
| --- | ---: | ---: | ---: |
| fixed pool | 21-9 | 70.0% | 52.1%-83.3% |
| diversified pool | 11-9 | 55.0% | 34.2%-74.2% |
| reproduced worst-matchup pair | 12-8 | 60.0% | 38.7%-78.1% |
| Claude (blind worst matchup) | 5-5 | 50.0% | 23.7%-76.3% |
| **all opponents** | **32-18** | **64.0%** | **50.1%-75.9%** |

The 50 real-engine matches covered five seeds × two seats × five frozen opponents. First-seat
win rate was 76%; second-seat win rate was 52%. There were zero semantic faults, illegal-action
faults, or unfinished games. Maximum whole-match runtime was 45.33 seconds, below the frozen
600-second limit. The retained champion therefore passes the operational blind audit.

## Deterministic artifact handoff

Two clean invocations of `scripts/build_submission.sh` produced byte-identical archives. Archive
SHA-256 is `c3b9f8cc...`; canonical content SHA-256 is `c99faf21...`. The archive entry hashes for
`main.py` and `deck.csv` exactly match the frozen terminal identity, and isolated exec-style
loading passed.

`artifacts/sot-2281/handoff.json` is the machine-readable contract for parent SOT-2278. It records
the retained outcome, terminal commit, holdout result, all four artifact identities, and the
verification gates. This issue did not call the approved submission helper and did not submit to
Kaggle; the parent may use the helper after its own final decision.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-opponent-repo> \
  --label <label> --seeds 5 --base-seed 2281101 \
  --json artifacts/sot-2281/holdout/<label>.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2281.py \
  eval/manifests/sot-2281-blind-holdout.json --output artifacts/sot-2281/summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2281/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
```
