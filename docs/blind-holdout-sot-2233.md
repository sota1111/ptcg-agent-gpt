# SOT-2233 first-cycle champion audit and submission decision

## Frozen provenance and isolation

The SOT-2232 terminal state was frozen at merge commit `ef78bac`. Both
distribution-robust candidates were rejected, so the retained champion remains
behavior commit `fd09f65`, with `main.py` SHA-256 `043fa984...`, `deck.csv`
SHA-256 `e92d5717...`, and canonical `agents/*.py` content SHA-256
`fd8c789f...`. The fixed and diversified opponents, their commits/decks, and
five blind seeds (`2233101..2233105`) were preregistered in
`eval/manifests/sot-2233-blind-holdout.json` before evaluation. Those seeds are
disjoint from SOT-2231 diagnosis and SOT-2232 screen/confirm ranges, and every
seed ran from both seats.

## Real-engine blind holdout

| Pool / opponent | W-L | Win rate | Wilson 95% CI |
| --- | ---: | ---: | ---: |
| fixed pool | 15-15 | 50.0% | 33.2%-66.8% |
| matsu (worst fixed) | 3-7 | 30.0% | 10.8%-60.3% |
| diversified pool | 10-10 | 50.0% | 29.9%-70.1% |
| claude (worst diversified) | 4-6 | 40.0% | 16.8%-68.7% |
| **all opponents** | **25-25** | **50.0%** | **36.6%-63.4%** |

Across all 50 matches, first-seat win rate was 48.0% and second-seat win rate
was 52.0%. There were zero agent faults, unfinished matches, or illegal-action
faults. Whole-match runtime was mean 13.56s, p50 11.98s, p95 30.31s, and max
32.60s, safely below 600 seconds. Raw public-telemetry-only reports live under
`artifacts/sot-2233/holdout/`; `artifacts/sot-2233-summary.json` is the
deterministically regenerated audit.

## Champion and submission decision

No candidate was promoted by SOT-2232, and the blind operational audit found
no reason to invalidate the last common-gate champion. Behavior and hashes
therefore remain unchanged.

The deterministic build produced archive SHA-256 `c3b9f8cc...` and canonical
content fingerprint `c99faf21...`. Rebuilding twice produced byte-identical
archives. The preceding local archive had a different compressed SHA-256
(`c1197478...`) but the same canonical content fingerprint (`c99faf21...`).
Accordingly, this run safely skipped Kaggle submission: content is unchanged,
so there is no improved artifact to resubmit. The machine-readable comparison
is `artifacts/sot-2233/submission-comparison.json`.

## Reproduction

```bash
.venv/bin/python scripts/analyze_blind_holdout_sot_2233.py \
  eval/manifests/sot-2233-blind-holdout.json \
  --output artifacts/sot-2233-summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2233/submission-fingerprint.json
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
.venv/bin/python scripts/verify_submission_exec.py
```
