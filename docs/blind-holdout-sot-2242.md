# SOT-2242 second-cycle champion audit and Kaggle submission

## Frozen provenance and seed isolation

SOT-2241 ended at merge commit `ecc0a20` with no candidate promoted. The final
champion therefore remains behavior commit `fd09f65`: `main.py` SHA-256
`043fa984...`, `deck.csv` SHA-256 `e92d5717...`, and canonical `agents/*.py`
SHA-256 `fd8c789f...`. The manifest freezes the fixed pool (matsu/take/ume),
diversified pool (Claude/obo), opponent commits and decks, and blind seeds
`2242101..2242105` before evaluation. These seeds are disjoint from SOT-2240
diagnosis (`2240101..2240103`) and SOT-2241 screen/confirm
(`2241101..2241102`, `2241201..2241205`), and each was run from both seats.

## Real-engine blind holdout

| Pool / opponent | W-L | Win rate | Wilson 95% CI |
| --- | ---: | ---: | ---: |
| fixed pool | 18-12 | 60.0% | 42.3%-75.4% |
| matsu (worst fixed) | 4-6 | 40.0% | 16.8%-68.7% |
| diversified pool | 8-12 | 40.0% | 21.9%-61.3% |
| Claude (worst diversified) | 3-7 | 30.0% | 10.8%-60.3% |
| worst-matchup pair | 7-13 | 35.0% | 18.1%-56.7% |
| **all opponents** | **26-24** | **52.0%** | **38.5%-65.2%** |

Across 50 matches, first-seat win rate was 60.0% and second-seat win rate was
44.0%. There were zero semantic faults, unfinished games, and illegal-action
faults. Whole-match runtime was mean 12.43s, p50 9.92s, p95 29.36s, and max
37.12s, below the 600-second constraint. The known matsu/Claude weakness
remains visible, but there is no SOT-2241 candidate to promote or revert; the
audited champion behavior and hashes are unchanged.

## Reproducible archive and submission

The deterministic build passed isolated execution from an arbitrary temporary
directory without `PYTHONPATH` or an external repository. Two rebuilds were
byte-identical. Archive SHA-256 is `c3b9f8cc...`; canonical content fingerprint
is `c99faf21...`.

Kaggle accepted the exact archive for `pokemon-tcg-ai-battle` as submission ref
`55154527`. Its message contains source commit `bc90f54` and the full artifact
SHA-256. Kaggle completed evaluation with public score **600.0**.
`artifacts/sot-2242/submission.json` uniquely maps champion, holdout, archive
fingerprints, submission ref/status, and score.

## Reproduction

```bash
.venv/bin/python scripts/analyze_blind_holdout_sot_2242.py \
  eval/manifests/sot-2242-blind-holdout.json \
  --output artifacts/sot-2242-summary.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2242/submission-fingerprint.json
.venv/bin/python scripts/verify_submission_exec.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest -q
```
