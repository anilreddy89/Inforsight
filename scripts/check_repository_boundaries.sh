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
  data-contracts/v3/policy-event.schema.json
  data-contracts/v3/observation-record.schema.json
  data-contracts/v3/oracle-sidecar.schema.json
  docs/experiments/phase-02r-09-v3-corpus-manifest.json
  docs/experiments/phase-02r-10-v3.1-pre-remediation-disposition.json
  docs/experiments/phase-02r-10-v3-structural-support-3.2.0.json
  docs/experiments/phase-02r-10-v3-split-manifest-3.2.0.json
  docs/experiments/phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json
  docs/experiments/phase-02r-10-v3-feature-diagnostics-manifest-3.2.0.json
  docs/experiments/phase-02r-10-v3-candidate-selection-manifest-3.2.0.json
  docs/modeling/phase-02r-11-v3-statistical-acceptance-execution-contract.md
  docs/experiments/phase-02r-11-v3-statistical-acceptance-manifest.json
  docs/experiments/phase-02r-11-v3-statistical-acceptance-report.md
  docs/experiments/phase-02r-11-v3-statistical-acceptance-decision.md
  docs/modeling/phase-02r-10-v3-feature-dictionary.json
  datasets/v3/DATA_CARD.md
)

# Missing Repository Artifact Chekc
for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required repository artifact: $file" >&2
    exit 1
  fi
done

if ! grep -q '"final_holdout_status": "not_materialized"' \
  docs/experiments/phase-02r-11-v3-statistical-acceptance-manifest.json; then
  echo "R2-11 final-holdout boundary is missing or invalid" >&2
  exit 1
fi

if ! grep -q '"decision": "redesign"' \
  docs/experiments/phase-02r-11-v3-statistical-acceptance-manifest.json; then
  echo "R2-11 mechanical decision is missing or invalid" >&2
  exit 1
fi

# R2-10 commits only aggregate evidence and portable digests.
while IFS= read -r forbidden; do
  echo "Forbidden R2-10 materialization detected: $forbidden" >&2
  exit 1
done < <(find docs datasets -type f \( \
  -iname '*v3*matrix*' -o -iname '*v3*prediction*' -o \
  -iname '*v3*oracle*sidecar*' -o -iname '*v3*fitted*.pkl' -o \
  -iname '*v3*fitted*.pickle' \) -print)

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
