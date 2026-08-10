# SOT-2594 deterministic final submission handoff

`artifacts/sot-2594/handoff.json` is the only parent-facing contract for the two SOT-2593 finalists.
The builder materializes the primary from pinned commit `e67ded7` plus the pinned-by-fingerprint engine,
and the hedge from `84d33d6`; it builds each archive twice, requires byte identity, and then checks the
canonical fingerprints selected by SOT-2593.

Both archives contain top-level `main.py` and `deck.csv`, import without network/PYTHONPATH in isolated
mode, execute the Kaggle-style entry point, return a real 60-card engine deck, and remain below the size
limit. Missing, corrupt, stale, duplicate-fingerprint, or incomplete-checklist inputs fail closed.

The machine-readable final-selection payload records CV best SOT-2556, public best/gap as null (never
imputed), and independent hedge SOT-2574. Deadline is 2026-08-16 23:59 UTC; drop-dead is 21:29 UTC.
Reserve one daily slot and submit in primary-then-hedge order so both become the latest two slots.

This child did not submit to Kaggle. Its decision is always `hold`; only a resumed SOT-2591 parent run
may honor `submit=auto`, re-read the newest directive, complete the checklist, and invoke the required
control-plane submission helper.

Rebuild with:

```bash
.venv/bin/python scripts/freeze_final_handoff_sot_2594.py
pytest -q tests/test_final_handoff_sot_2594.py
```
