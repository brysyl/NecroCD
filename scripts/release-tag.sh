#!/usr/bin/env bash
# Tag the NecroCD release once PR #1 is merged.
# Default mode only reports what would happen. Nothing is tagged or pushed without --execute.
set -euo pipefail

TAG="v1.0.0-kiroween"
REPO="${NECROCD_GH_REPO:-brysyl/NecroCD}"
PR="${NECROCD_PR_NUMBER:-1}"
REMOTE="origin"
EXECUTE=0
DRY_RUN=0

usage() {
  cat <<USAGE
Usage: scripts/release-tag.sh [--dry-run | --execute] [--repo OWNER/NAME] [--pr NUMBER]

Verifies PR #${PR} of ${REPO} is merged (via the GitHub REST API using 'gh api'),
then creates the annotated tag ${TAG} on the PR's merge commit and pushes it.

Options:
  --dry-run   Run every check and print the actions, change nothing.
  --execute   Create the tag locally and push it to ${REMOTE}. Required to make changes.
  --repo      Override repository (env: NECROCD_GH_REPO). Default: ${REPO}
  --pr        Override PR number (env: NECROCD_PR_NUMBER). Default: ${PR}
  -h, --help  Show this help.

With neither --dry-run nor --execute the script behaves like --dry-run.

Refuses to run when the PR is not merged, the working tree is dirty, or the tag exists
locally or on ${REMOTE}. 'git fetch ${REMOTE}' is run first (read only).
USAGE
}

die() { echo "error: $*" >&2; exit 1; }
say() { echo "[release-tag] $*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --execute) EXECUTE=1 ;;
    --repo) [ $# -ge 2 ] || die "--repo needs a value"; REPO="$2"; shift ;;
    --pr) [ $# -ge 2 ] || die "--pr needs a value"; PR="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown argument: $1" ;;
  esac
  shift
done

[ "$EXECUTE" -eq 1 ] && [ "$DRY_RUN" -eq 1 ] && die "--dry-run and --execute are mutually exclusive"
[[ "$REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || die "invalid repo: $REPO"
[[ "$PR" =~ ^[0-9]+$ ]] || die "invalid PR number: $PR"

command -v git >/dev/null || die "git is required"
command -v gh >/dev/null || die "gh (GitHub CLI) is required"
cd "$(git rev-parse --show-toplevel)"

if [ "$EXECUTE" -eq 1 ]; then say "mode: EXECUTE"; else say "mode: dry run (no changes will be made)"; fi

# Working tree must be clean (untracked files are ignored).
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  die "working tree is dirty; commit or stash changes first"
fi

say "fetching ${REMOTE} (read only)"
git fetch --tags --quiet "$REMOTE"

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  die "tag ${TAG} already exists locally"
fi
if [ -n "$(git ls-remote --tags "$REMOTE" "refs/tags/${TAG}")" ]; then
  die "tag ${TAG} already exists on ${REMOTE}"
fi

# 'gh pr view' uses GraphQL; use the REST endpoint instead.
say "checking PR #${PR} on ${REPO}"
merged="$(gh api "repos/${REPO}/pulls/${PR}" --jq '.merged')" || die "could not query PR #${PR}"
if [ "$merged" != "true" ]; then
  die "PR #${PR} is not merged yet; merge it first, then re-run"
fi
sha="$(gh api "repos/${REPO}/pulls/${PR}" --jq '.merge_commit_sha')"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || die "PR has no valid merge_commit_sha: ${sha}"
git cat-file -e "${sha}^{commit}" 2>/dev/null || die "merge commit ${sha} not found locally after fetch"

say "PR #${PR} merged at ${sha}"
say "would run: git tag -a ${TAG} ${sha} -m 'NecroCD ${TAG}'"
say "would run: git push ${REMOTE} refs/tags/${TAG}"

if [ "$EXECUTE" -ne 1 ]; then
  say "nothing changed. Re-run with --execute to tag and push."
  exit 0
fi

git tag -a "$TAG" "$sha" -m "NecroCD ${TAG}"
git push "$REMOTE" "refs/tags/${TAG}"
say "tagged and pushed ${TAG}"
