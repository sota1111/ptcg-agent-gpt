# SOT-2058 deck-pool evaluation

## Protocol

The three preselected deck candidates were evaluated with the repository's real
`cg` engine against the frozen decks and current policies from matsu, take, and
ume. Each pairing used agent seeds `205800`–`205802`, with one game in each seat
per seed. This produced 18 matches per candidate and 54 matches total.

The final-pool gate requires a legal and loadable 60-card deck, zero invalid
actions, zero unfinished matches, an aggregate win rate of at least 50%, no
duplicate of a retained deck, and at most two additions. The existing baseline
is retained. Candidate roles were predeclared in
`configs/deck-pool-evaluation.json`.

## Results

| candidate | role coverage | W-L | win rate | first | second | avg turns | invalid / errors | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| top-emerging | top, emerging | 9-9 | 50.0% | 66.7% | 33.3% | 19.333 | 0 / 0 | add |
| counter-diversity | counter, diversity | 8-10 | 44.4% | 55.6% | 33.3% | 21.694 | 0 / 0 | remove |
| low-usage-diversity | low-usage top, diversity | 10-8 | 55.6% | 66.7% | 44.4% | 19.528 | 0 / 0 | add |

Per-representative results, raw match records, decision hashes, and legality
details are stored in `artifacts/sot-2058-deck-pool/summary.json`. All three
candidates loaded successfully and passed the repository card legality check.

## Final reorganization

The pool changes from one to three retained decks:

- Keep the existing baseline for baseline/top coverage.
- Add `top-emerging`; it meets the 50% gate and preserves current-top/emerging
  coverage.
- Add `low-usage-diversity`; it has the strongest aggregate result and preserves
  low-usage-top/diversity coverage.
- Reject `counter-diversity`; its 44.4% aggregate win rate misses the preregistered
  gate. Low usage was not used as a removal reason.

This is a bounded two-deck addition, not a bulk replacement. The reviewable pool
CSV is `artifacts/sot-2058-deck-pool/final-deck-pool.csv`; the retained candidate
CSVs are in the adjacent `decks/` directory.

## Reproduction

```bash
.venv/bin/python scripts/evaluate_deck_pool.py
```

Existing complete raw reports are reused so an interrupted run can resume without
repeating finished pairings.
