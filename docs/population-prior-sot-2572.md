# SOT-2572 archetype-conditioned population prior

This candidate distils a deterministic, integer-linear policy/value prior from
the SOT-2571 `train` population only. It is an architecture candidate for the
independent SOT-2573 screen/confirm run, not a promoted champion.

Runtime input is limited to revealed opponent card IDs, public board/prize
counts and the engine-provided legal options. Opponent identity, hidden zones,
policy/deck identity, split, seed and lineage have no runtime interface and are
listed in the artifact denylist. Archetype evidence comes only from currently
revealed card IDs; no match-level identity is inferred.

Enable only in the evaluation harness with both
`PTCG_TELEMETRY_PROTOCOL=1` and `PTCG_POPULATION_PRIOR_CANDIDATE=1`. With
either flag absent, `PlannerConfig.population_prior` is false and the champion
code path and behavior fingerprint are unchanged. Missing, corrupt or
incompatible artifacts fail closed to neutral logits; MCTS continues to choose
only engine-listed legal actions.

Rebuild or resume deterministically:

```bash
python scripts/train_population_prior_sot_2572.py --seed 2572
```

The config, train population snapshot, checkpoint, final artifact and training
receipt are SHA-256 linked. The artifact is JSON, dependency-free, well below
the 32 KiB contract and loads on CPU/offline execution. SOT-2573 owns paired
screen followed by independent confirm and decides promotion or revert.

No Kaggle submission was performed.
