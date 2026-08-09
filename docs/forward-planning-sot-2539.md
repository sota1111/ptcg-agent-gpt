# SOT-2539 search-audited forward-planning evaluation

## Source audit and preregistered axis

The candidate distills exactly one portable concept from the Apache-2.0 public
Search-Audited Alakazam v12 notebook, version 19: visit every legal root arm
once before adaptive UCB/PUCT allocation. The frozen normalized source hash is
`d709a2f2a86644ea3fdf481cdacebd6c495ba360bc73c1b4c07e64304c925804`; the
upstream payload hash is recorded in the manifest. The candidate neither
copies its deck-specific state evaluator nor retries the rejected public value,
pairwise prior, belief determinization, or tactical-controller axes.

`eval/manifests/sot-2539-forward-planning.json` preregistered the allow-list,
forbidden features, source/version/license/hashes, hypothesis, unchanged
search budget, SOT-2538 screen/confirm split, and fail-closed gate before the
screen ran. The implementation reads only legal root branches and their local
visit counts over the champion's existing public-only determinizations. It has
no hidden-zone identity, opponent identity, private/deck-specific feature, or
external weight input. The environment switch requires the evaluation
telemetry protocol; normal and Kaggle execution remain the disabled champion.

## Paired screen result

The real-engine screen used the frozen SOT-2538 screen field (`take` and
`search-alakazam-v12`), one seed per opponent and both semantic seats. The
candidate finished 2/4 versus champion 3/4. It tied `take` 2/2 but regressed
against Search-Audited Alakazam from 1/2 to 0/2, and seat 0 from 2/2 to 1/2;
seat 1 tied at 1/2. Both identities had zero faults and zero unfinished games.

Champion runtime mean/p95/max was 22.010/26.324/26.324 seconds. Candidate
runtime mean/p95/max was 20.524/37.866/37.866 seconds (mean ratio 0.9325).
Because pooled improvement, every-opponent non-regression, and every-seat
non-regression all failed, the independent confirm was not opened. The
candidate remains default disabled, the champion is retained, and no Kaggle
submission was made. Machine-readable evidence is in
`artifacts/sot-2539/screen-decision.json`.

## Reproduce

```bash
.venv/bin/python scripts/evaluate_forward_planning_sot_2539.py \
  --manifest eval/manifests/sot-2539-forward-planning.json \
  --phase screen \
  --raw-dir artifacts/sot-2539/screen \
  --output artifacts/sot-2539/screen-decision.json
```

The runner reuses identity/seed/opponent-matched raw reports, preventing a
retry from launching duplicate engine writers. A `confirm` invocation requires
a passing screen receipt and fails closed for this rejected result.
