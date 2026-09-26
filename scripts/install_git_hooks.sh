#!/usr/bin/env bash
# Install RAIL 3 (recalibration pins) + rail 4 (session-plan) + RAIL 0 (repo integrity) as a PRE-COMMIT hook,
# so a violation is REFUSED instead of reported (BUG-445). Rationale: a post-hoc check cannot un-commit.
# The hook path is resolved from GIT, never assumed: after the BUG-500 fix '.git' is a one-line pointer FILE,
# so 'cat > .git/hooks/pre-commit' would fail or write into the wrong place (audited 2026-09-25).
#
# THIS FILE IS THE HOOK'S ONLY HOME (BUG-526). The installed hook is a DERIVED artifact: `--check` re-derives
# it and byte-compares. Until this was added the strongest gates in the repository lived OUTSIDE version
# control and outside the worktree, where no rail could see them drift - hand-editing the installed hook, or
# leaving behind an older one, silently changed what the repository enforces. Same rule as
# scripts/check_bug_status.py: a derived artifact must equal its own re-derivation.
set -euo pipefail
cd "$(dirname "$0")/.."
git_dir="$(git rev-parse --absolute-git-dir)"
[ -n "$git_dir" ] && [ -d "$git_dir" ] || { echo "FAIL install-git-hooks: git dir does not resolve"; exit 1; }
mkdir -p "$git_dir/hooks"
hook="$git_dir/hooks/pre-commit"

render_hook() {
cat <<'HOOK'
#!/usr/bin/env bash
# RAIL 0 - refuse to commit THROUGH a repository whose git metadata a sync client has renamed (P0-A, BUG-400),
# or whose git dir still sits inside a sync domain (BUG-500). Strict on purpose: exit 2 (owner-owed conflict
# copies) also blocks, because a commit is the one act that makes a conflicted tree permanent.
python3 scripts/check_repo_integrity.py || exit 1
# RAIL 3 - refuse a commit that would make a digest-pinned measurement UNREPRODUCIBLE (BUG-526). The pin rule
# and its digests have ONE home (config/recalibration_pins.yaml via scripts/verify_recalibration_pins.py); this
# is that same home at the WRITE moment. It does NOT overreach: a commit naming no pinned artifact is tolerated
# even while the tree is RED - only the commit that MOVES a pinned artifact is refused.
python3 scripts/verify_recalibration_pins.py --staged || exit 1
# RAIL 4 - refuse a commit whose staged paths are outside the session plan. Never bypass with --no-verify.
exec python3 scripts/check_session_plan.py --staged
HOOK
}

if [ "${1:-}" = "--check" ]; then
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
  render_hook > "$tmp"
  [ -f "$hook" ] || { echo "FAIL git-hooks: $hook is NOT installed - run: bash scripts/install_git_hooks.sh"; exit 1; }
  if cmp -s "$tmp" "$hook"; then echo "ok git-hooks: the installed pre-commit hook equals its re-derivation"; exit 0; fi
  echo "FAIL git-hooks: $hook DIFFERS from scripts/install_git_hooks.sh - the installed enforcement is not the declared one:"
  diff "$tmp" "$hook" | head -20 || true
  echo "   -> re-install: bash scripts/install_git_hooks.sh   (then re-run this check)"
  exit 1
fi

render_hook > "$hook"
chmod +x "$hook"
echo "installed $hook"
python3 scripts/check_session_plan.py --staged
