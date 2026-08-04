# SOT-2439 public tactical controller preregistration

## External source audit

The public Kaggle notebook [Improved Probabilistic agent](https://www.kaggle.com/code/aristophanivan/improved-probabilistic-agent)
declares Apache-2.0, has public score 967.7, uses no attached dataset/model or accelerator, and depends
only on Python's standard library plus the competition `cg.api`. Its downloaded V1 notebook is pinned
in the manifest by SHA-256; it is evidence, not a vendored dependency.

The portable score sources are the *concepts* of reachable attack planning, KO/prize target value,
energy readiness, legal gust/switch/retreat sequencing, and archetype response inferred from revealed
board cards. The source deck list, source card IDs, card-specific weights and exceptions, mutable memory
not reconstructible from the current observation, and its particular search/candidate budget are
non-portable assets. SOT-2440 must re-express the concepts for the Abomasnow champion; it must not copy
those assets.

Kaggle's foundational rules permit public competition code shared on Kaggle under an OSI-approved
commercially usable license. This audit still applies the narrower rule above and retains the source URL,
version hash, declared license, dependency boundary, and classification for traceability.

## Public-only tactical boundary

`eval/manifests/sot-2439-public-tactical-contract.json` is the source of truth. Policy inputs may use
the acting player's own observation, revealed public board/discard/stadium data, counts of hidden zones,
legal actions, attack metadata, and derived public KO/prize/readiness/archetype attributes. The exact
allow-list is machine checked.

Hidden opponent hand/deck/prize identities, hidden order, opponent or pool identity, evaluation/match
seed, seat used as a matchup proxy, and hidden-world fingerprints are forbidden. Seat is allowed only
as the public turn-rule fact `acting_seat`; it must never select opponent-specific behavior.

## Frozen screen → confirm protocol

The manifest inherits the exact SOT-2399 reanchored six-opponent pool and pins that source manifest,
current champion `main.py`/`deck.csv`, the candidate scope, and equal search/runtime budget. Screen uses
fresh seed family `2439101` with two seeds per opponent and both seats. Confirm reserves independent
seed family `2439201` with five seeds per opponent and both seats.

Screen authorizes confirm only if aggregate win rate strictly improves and every opponent, seat 1,
faults, unfinished games, and runtime are non-regressing. Any failure skips confirm and reverts candidate
behavior while preserving the manifest, results, and documentation. Promotion additionally requires an
exec-compatible terminal artifact. SOT-2439, SOT-2440, and SOT-2441 must not submit to Kaggle; only the
parent issue may make the fingerprint-gated submission decision.

Run the fail-closed contract check with:

```bash
.venv/bin/python scripts/validate_tactical_contract.py \
  eval/manifests/sot-2439-public-tactical-contract.json
```
