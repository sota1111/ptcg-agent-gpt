# SOT-2279 refreshed meta deck candidates

## Why this is a bounded retry

This is a new deck-axis attempt after SOT-2058, not a reuse of its retained lists. The
opponent inventory now freezes the three fixed policies (matsu, take, ume) and the
diversified Claude/obo policies from SOT-2256. That audit reproduced the weakest
matchups against matsu (30%) and Claude (20%), while the public score sequence fell
from 600 to 529.4 and then 480.0. These changed observations justify three new,
single-card composition hypotheses.

The champion is frozen at behavior commit `fd09f65`, with `main.py` SHA-256
`043fa984...` and `deck.csv` SHA-256 `e92d5717...`. Exact opponent commits and deck
fingerprints, the card database fingerprint, candidate fingerprints, and all decision
rules are recorded in the manifest and generated artifacts. Generation fails closed
if any frozen champion or opponent input drifts.

## Explainable legal candidates

Each candidate removes one Basic Water Energy and adds exactly one card; all are
loadable, 60 cards, legal under `sv-current-2026-07`, and composition-distinct.

| Candidate | Added card | Intended role | Composition fingerprint |
| --- | --- | --- | --- |
| `kyogre-consistency` | third Kyogre | improve availability of the existing attacker | `672d322d...` |
| `suicune-energy-scaling` | Suicune | exploit the champion's dense Water Energy plan | `98db6446...` |
| `wellspring-bench-pressure` | Wellspring Mask Ogerpon ex | add explicit bench pressure for matsu/Claude | `5df8e67b...` |

## Preregistered screen and confirm rule

Before the screen, the manifest fixed fresh seed `2279101`, both-seat reversal, all
five opponents, and identical conditions for champion and candidates. A candidate
passes only when it gains at least one total win, does not lose combined matsu/Claude
wins, and does not increase faults or unfinished matches. At most two candidates
advance, ordered by worst-matchup delta, total delta, then stable candidate ID.

The independent confirm reserved for SOT-2280 uses fresh seeds `2280101..2280105`,
both seats, and the same frozen pool. Promotion requires overall improvement, no
matsu/Claude or fixed-pool regression, and no fault/unfinished increase. This Issue
does not modify the runtime champion and performs no Kaggle submission.

## Screen result

The real engine ran 10 matches per deck (one seed × both seats × five opponents), 40
matches total. All decks had zero faults and zero unfinished matches.

| Deck | W-L | Overall | matsu + Claude wins | Delta vs champion | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| champion | 4-6 | 40% | 1 | — | baseline |
| `kyogre-consistency` | 5-5 | 50% | 1 | +1 overall / +0 worst | confirm |
| `suicune-energy-scaling` | 3-7 | 30% | 1 | -1 overall / +0 worst | reject |
| `wellspring-bench-pressure` | 7-3 | 70% | 2 | +3 overall / +1 worst | confirm |

The next Issue should confirm `wellspring-bench-pressure` and `kyogre-consistency`.
`suicune-energy-scaling` is a quantitatively rejected, non-promotion candidate.

## Reproduction

```bash
.venv/bin/python scripts/refresh_meta_deck_candidates_sot_2279.py --screen
.venv/bin/pytest -q tests/test_meta_deck_candidates.py
.venv/bin/python scripts/verify_submission_exec.py
```
