#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Close a completed GitHub milestone and create its successor.

Usage:
  scripts/transition_milestone.sh \
    --close <number-or-exact-title> \
    --new-title <title> \
    --new-description <description> \
    [--repo <owner/repository>] \
    [--due-on <YYYY-MM-DD>] \
    [--allow-open-items] \
    [--dry-run] \
    [--yes]

Required arguments:
  --close             Milestone number or exact title to close.
  --new-title          Title for the new milestone.
  --new-description    Description for the new milestone.

Optional arguments:
  --repo               GitHub repository. Defaults to the current repository.
  --due-on             Due date for the new milestone in YYYY-MM-DD format.
  --allow-open-items   Permit closing a milestone that still has open items.
  --dry-run            Validate and print the planned transition without writing.
  --yes                Skip the interactive confirmation prompt.
  -h, --help           Show this help text.

The new milestone is created before the old one is closed. If the close operation
fails, both milestones remain available and no milestone definition is lost.

Example:
  scripts/transition_milestone.sh \
    --repo anilreddy89/Inforsight \
    --close v0.1.0-data-foundation \
    --new-title v0.2.0-risk-model \
    --new-description "Phase 2 baseline ML and model documentation." \
    --dry-run
EOF
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

repo=""
close_ref=""
new_title=""
new_description=""
due_on=""
allow_open_items=false
dry_run=false
assume_yes=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || fail "--repo requires a value"
      repo="$2"
      shift 2
      ;;
    --close)
      [[ $# -ge 2 ]] || fail "--close requires a value"
      close_ref="$2"
      shift 2
      ;;
    --new-title)
      [[ $# -ge 2 ]] || fail "--new-title requires a value"
      new_title="$2"
      shift 2
      ;;
    --new-description)
      [[ $# -ge 2 ]] || fail "--new-description requires a value"
      new_description="$2"
      shift 2
      ;;
    --due-on)
      [[ $# -ge 2 ]] || fail "--due-on requires a value"
      due_on="$2"
      shift 2
      ;;
    --allow-open-items)
      allow_open_items=true
      shift
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    --yes)
      assume_yes=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -n "$close_ref" ]] || fail "--close is required"
[[ -n "$new_title" ]] || fail "--new-title is required"
[[ -n "$new_description" ]] || fail "--new-description is required"

if [[ -n "$due_on" && ! "$due_on" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  fail "--due-on must use YYYY-MM-DD format"
fi

command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) is not installed"
gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated; run 'gh auth login'"

if [[ -z "$repo" ]]; then
  repo="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
fi

[[ "$repo" == */* ]] || fail "--repo must use owner/repository format"

milestones="$(gh api "repos/$repo/milestones?state=all&per_page=100" \
  --jq '.[] | [.number, .title, .state, .open_issues, .closed_issues] | @tsv')"

old_number=""
old_title=""
old_state=""
old_open_items=""
old_closed_items=""
matching_milestones=0

while IFS=$'\t' read -r number title state open_items closed_items; do
  [[ -n "$number" ]] || continue

  if [[ "$close_ref" == "$number" || "$close_ref" == "$title" ]]; then
    old_number="$number"
    old_title="$title"
    old_state="$state"
    old_open_items="$open_items"
    old_closed_items="$closed_items"
    matching_milestones=$((matching_milestones + 1))
  fi

  if [[ "$new_title" == "$title" ]]; then
    fail "milestone '$new_title' already exists as milestone #$number ($state)"
  fi
done <<< "$milestones"

[[ "$matching_milestones" -gt 0 ]] || fail "milestone '$close_ref' was not found in $repo"
[[ "$matching_milestones" -eq 1 ]] || fail "milestone reference '$close_ref' is ambiguous; use its number"
if [[ "$old_state" != "open" && "$old_state" != "closed" ]]; then
  fail "milestone #$old_number '$old_title' has unsupported state '$old_state'"
fi

if [[ "$old_open_items" -gt 0 && "$allow_open_items" != true ]]; then
  fail "milestone #$old_number has $old_open_items open item(s); close or move them, or pass --allow-open-items"
fi

echo "Repository:       $repo"
if [[ "$old_state" == "closed" ]]; then
  echo "Old milestone:   #$old_number $old_title (already closed)"
else
  echo "Close milestone: #$old_number $old_title ($old_open_items open, $old_closed_items closed)"
fi
echo "Create milestone: $new_title"
echo "Description:      $new_description"
if [[ -n "$due_on" ]]; then
  echo "Due date:         $due_on"
else
  echo "Due date:         none"
fi

if [[ "$dry_run" == true ]]; then
  echo "Dry run complete; no GitHub changes were made."
  exit 0
fi

if [[ "$assume_yes" != true ]]; then
  [[ -t 0 ]] || fail "confirmation requires a terminal; rerun with --yes"
  read -r -p "Create the new milestone and close the old milestone? [y/N] " answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || fail "operation cancelled"
fi

create_args=(
  "repos/$repo/milestones"
  --method POST
  -f "title=$new_title"
  -f "description=$new_description"
)

if [[ -n "$due_on" ]]; then
  create_args+=(-f "due_on=${due_on}T23:59:59Z")
fi

new_result="$(gh api "${create_args[@]}" --jq '[.number, .html_url] | @tsv')"
IFS=$'\t' read -r new_number new_url <<< "$new_result"

if [[ "$old_state" == "open" ]]; then
  if ! gh api "repos/$repo/milestones/$old_number" \
    --method PATCH \
    -f state=closed \
    --silent; then
    echo "The new milestone was created, but the old milestone could not be closed." >&2
    echo "New milestone: $new_url" >&2
    exit 1
  fi
fi

echo "Created milestone #$new_number: $new_url"
if [[ "$old_state" == "open" ]]; then
  echo "Closed milestone #$old_number: $old_title"
else
  echo "Milestone #$old_number was already closed: $old_title"
fi
