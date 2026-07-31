#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
archive="$repo/submission.tar.gz"
for required in main.py deck.csv agents cg; do
  [ -e "$repo/$required" ] || { echo "missing required submission path: $required" >&2; exit 1; }
done
tar -C "$repo" --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  --exclude='__pycache__' --exclude='*.pyc' -cf - main.py deck.csv agents cg \
  | gzip -n > "$archive"
gzip -t "$archive"
listing="$(mktemp)"
trap 'rm -f -- "$listing"' EXIT
tar -tzf "$archive" > "$listing"
grep -Fx main.py "$listing" >/dev/null
grep -Fx deck.csv "$listing" >/dev/null
if grep -E '(^|/)(\.env($|\.)|\.git/|tests/|eval/|\.venv/|access_token|kaggle\.json|__pycache__/|.*\.pyc$)' "$listing"; then
  echo "submission contains a forbidden path" >&2
  exit 1
fi
python3 "$repo/scripts/verify_submission_exec.py"
echo "submission archive: $archive"
