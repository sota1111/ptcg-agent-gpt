#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
archive="$repo/submission.tar.gz"

# SOT-2573 rejected the opt-in population-prior candidate. Package the exact
# retained champion without candidate-only source or model data.
tar -C "$repo" --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='agents/counter_meta_policy.py' \
  --exclude='agents/population_prior.py' \
  --exclude='agents/population_prior_sot_2572.json' \
  -cf - main.py deck.csv agents cg | gzip -n > "$archive"

gzip -t "$archive"
listing="$(mktemp)"
trap 'rm -f -- "$listing"' EXIT
tar -tzf "$archive" > "$listing"
grep -Fx main.py "$listing" >/dev/null
grep -Fx deck.csv "$listing" >/dev/null
if grep -E '^agents/(counter_meta_policy\.py|population_prior(_sot_2572.json|\.py))$' "$listing" >/dev/null; then
  echo "rejected candidate leaked into terminal artifact" >&2
  exit 1
fi
python3 "$repo/scripts/verify_submission_exec.py"
echo "terminal submission archive: $archive"
