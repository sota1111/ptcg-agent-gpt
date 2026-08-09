# SOT-2556 counter-meta terminal blind holdout

SOT-2555 rejected the default-disabled counter-meta candidate at screen and retained the unchanged
champion. Commit `99298c7` froze this terminal contract before results were opened: five opponent
policy/deck entities and submission lineages absent from SOT-2553/SOT-2555, a later evidence window,
unique match units, seeds `2556101..2556105`, and both seats.

## Blind result

The real engine completed 50 matches at 43-7 (86%, Wilson 95% CI 73.8%-93.0%). Results were
matsu-dragapult 7-3, take-hydrapple 10-0, ume-festival 10-0, claude-honchkrow 10-0, and
search-emerging 6-4. Seat 0 was 22-3 and seat 1 was 21-4. Faults, illegal actions, and unfinished
games were all zero; mean/p95/max runtime was 32.08/89.87/98.61 seconds, below the 600-second cap.

## Exact artifact handoff

Two deterministic builds produced the same archive SHA-256
`3ed0fc2d3ea8deb4f81238bdfd78441b09efbce34fe722c313aa51506ad86659`. The terminal builder excludes
the rejected, opt-in `agents/counter_meta_policy.py` evaluation source and packages the exact retained
champion. Top-level `main.py` and `deck.csv`, offline import, exec-style loading, archive size, and
runtime gates passed. Canonical content SHA-256
`5fda6f5f727c4647882755601807ac48b21995336e94670538923ef64767a24e` matches the previous submission,
so `artifacts/sot-2556/handoff.json` records `newArtifact=false` and `artifact=null`. No Kaggle
submission was made; only parent SOT-2552 may make that decision.

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> \
  --opponent-deck <frozen-deck> --seeds 5 --base-seed 2556101 \
  --json artifacts/sot-2556/holdout/<label>.json
bash scripts/build_terminal_artifact_sot_2556.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2556/submission-fingerprint.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2556.py
```
