#!/usr/bin/env bash
set -euo pipefail

required_files=(
  README.md
  LICENSE
  NOTICE
  THIRD_PARTY_NOTICES.md
  docs/clean-room-policy.md
  docs/assumptions.md
  docs/adr/0001-clean-room-and-synthetic-data.md
  docs/adr/0002-separate-risk-from-action-eligibility.md
)

# Missing Repository Artifact Chekc
for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required repository artifact: $file" >&2
    exit 1
  fi
done

# Secret-Bearing Filename Check
while IFS= read -r -d '' file; do
  relative="${file#./}"
  case "$relative" in
    .env.example) ;;
    .env|.env.*|*credentials*.json|*service-account*.json|*.pem|*.p12|*.pfx|*.key)
      echo "Potential secret-bearing filename detected: $relative" >&2
      exit 1
      ;;
  esac
done < <(git ls-files --cached --others --exclude-standard -z)

# Credential/Secret Content Scan
while IFS= read -r -d '' file; do
  case "$file" in
    scripts/check_repository_boundaries.sh|*.pdf|*.docx|*.xlsx|*.png|*.zip) continue ;;
  esac

  if grep -IqE '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[0-9A-Za-z]{30,})' "$file"; then
    echo "Potential credential material detected in: $file" >&2
    exit 1
  fi
done < <(git ls-files --cached --others --exclude-standard -z)

echo "Repository boundary checks passed."
