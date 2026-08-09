# SOT-2540 terminal blind holdout and parent handoff

SOT-2539 rejected forced root exploration at its paired screen, so this terminal audit evaluates
the retained champion. Commit `83f8a75` froze the holdout before results were opened: five policy/deck
entities absent from every SOT-2538 phase, a later time window, unique match units, seeds
`2540101..2540105`, and both seats. The analyzer verifies zero entity, time, match-unit, and seed
overlap against the source CV manifest and pins all source decisions and opponent provenance.

## Blind result

The real engine completed 50 matches at 40-10 (80%, Wilson 95% CI 67.0%-88.8%). Every frozen
opponent ran for ten games: matsu-dragapult 8-2, take-hydrapple 7-3, ume-festival 10-0,
claude-honchkrow 8-2, and search-emerging 7-3. Both seats were 80%. Faults, illegal actions, and
unfinished games were all zero; mean/p95/max runtime was 27.84/83.93/94.82 seconds, below the
600-second cap.

## Exact artifact handoff

Two deterministic builds produced identical archive SHA-256
`3ed0fc2d3ea8deb4f81238bdfd78441b09efbce34fe722c313aa51506ad86659`. Top-level `main.py` and
`deck.csv`, offline import, and exec-style loading passed. The canonical content fingerprint
`5fda6f5f727c4647882755601807ac48b21995336e94670538923ef64767a24e` matches the previous
submission, and SOT-2539 promoted no candidate. Therefore `artifacts/sot-2540/handoff.json` records
`newArtifact=false` and `artifact=null`; the parent must not treat this child as a new submission.
This child did not submit to Kaggle (`kaggleSubmitted=false`).

## Reproduction

```bash
.venv/bin/python eval/battle_vs.py --opponent <frozen-repo> \
  --opponent-deck <frozen-deck> --seeds 5 --base-seed 2540101 \
  --json artifacts/sot-2540/holdout/<label>.json
bash scripts/build_submission.sh
.venv/bin/python scripts/fingerprint_submission.py submission.tar.gz \
  --output artifacts/sot-2540/submission-fingerprint.json
.venv/bin/python scripts/analyze_blind_holdout_sot_2540.py
```
