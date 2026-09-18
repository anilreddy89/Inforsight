#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -eq 0 ]]; then
  echo "usage: $0 command [args ...]" >&2
  exit 2
fi

before="$(git status --porcelain=v1 --untracked-files=all)"
"$@"
after="$(git status --porcelain=v1 --untracked-files=all)"

if [[ "$before" != "$after" ]]; then
  echo "read-only verification changed the working tree" >&2
  diff -u <(printf '%s\n' "$before") <(printf '%s\n' "$after") || true
  exit 1
fi

echo "Read-only verification passed: working tree unchanged."
