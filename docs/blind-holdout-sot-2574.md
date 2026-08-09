# SOT-2574 terminal population blind holdout

SOT-2573 rejected the default-disabled population-prior candidate at independent confirm and retained
the champion. Commit `69baaf9` froze this terminal contract before results were opened. The holdout uses
only SOT-2571's two blind population members, fresh match units and seeds `2574101..2574105`, a later
time window, and both seats. Policy entity, deck entity, evidence, submission lineage, time, match, and
seed overlap against the train/screen/confirm population is zero.

## Blind result

The real engine completed 20 matches at 16-4 (80%, Wilson 95% CI 58.4%-91.9%). The champion went 8-2
against both `obo-diversified` and `meta-proxy`; seat 0 was 9-1 and seat 1 was 7-3. Faults, illegal
actions, and unfinished games were all zero. Mean/p95/max runtime was 24.04/37.65/41.06 seconds, below
the 600-second cap.

## Exact artifact handoff

Two deterministic builds produced archive SHA-256
`568b8cdb9377e926006e133ed1b7f68b3c8889700bc842e47077c55b53a9d0b1`. The builder excludes rejected
candidate-only source/model files and packages the retained champion. Top-level `main.py` and `deck.csv`,
offline import, exec loading, size, and runtime gates passed. Canonical content SHA-256
`07bd558f36408ac422f8340198fc939086878ba4779bf2bd4131f17bf223dc5e` differs from the previous submitted
fingerprint, so `artifacts/sot-2574/handoff.json` records `newArtifact=true` with the exact archive.
No Kaggle submission was made; only parent SOT-2570 may make that decision.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> \
  --opponent-deck <frozen-deck> --seeds 5 --base-seed 2574101 \
  --json artifacts/sot-2574/holdout/<id>.json
bash scripts/build_terminal_artifact_sot_2574.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2574/submission-fingerprint.json
.venv/bin/python scripts/analyze_terminal_population_sot_2574.py
```
