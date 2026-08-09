# SOT-2554 single-prize counter-meta candidate

This evaluation-only candidate couples a 4-4-4 single-prize Abra/Kadabra/Alakazam line with four Mist
Energy and a deterministic policy.  Alakazam supplies a low prize-liability attacker and draw engine;
Mist Energy is attached preferentially to an unprotected developed attacker using only visible board
cards and the engine's current legal options.  The policy inherits the explicit 49-context rule table,
deck-out guard, and legal random fallback.

## Evidence and source audit

SOT-2553's time-pinned metagame CV records Search-Audited Alakazam v12 as the stronger public screen
opponent and preserves source version 19, Apache-2.0 notice, hashes, and offline payload.  Its executable
actually uses a multi-prize Fighting deck; this candidate therefore adopts only the portable concepts
supported by that evidence—single-prize pressure and Mist Energy effect protection.  No upstream code,
weights, or deck list was copied.  The deck and policy here are independently authored against the
repository's existing API and card database.  The source audit remains at
`eval/opponents/search_audited_alakazam_v12/NOTICE.md` and the calibrated evidence contract at
`eval/manifests/sot-2553-replay-lineage-cv.json`.

The policy accepts only the adapted public board, public log, and current legal options.  It has no
opponent/pool identifier input and does not inspect hidden opponent hands, facedown prize identities,
or unrevealed deck identities.

## Activation and reproducibility

The champion remains the default.  Evaluation must opt in with both variables:

```bash
PTCG_TELEMETRY_PROTOCOL=1 \
PTCG_COUNTER_META_CANDIDATE=single-prize-alakazam-mist python3 -c \
  'from agents.counter_meta_policy import candidate_enabled; assert candidate_enabled()'
pytest -q tests/test_counter_meta_candidate_sot_2554.py
bash scripts/build_submission.sh
```

The committed experiment contract forbids screen/confirm and Kaggle submission in this construction
issue.  Later SOT-2555 owns paired evaluation.  Packaging stays offline and retains the 2 vCPU,
12.2 GiB, and sub-600-second decision constraints.
