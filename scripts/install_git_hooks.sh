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
git rev-parse --absolute-git-dir >/dev/null 2>&1 || { echo "FAIL install-git-hooks: git dir does not resolve"; exit 1; }
# THE HOOK'S PATH IS GIT'S OWN ANSWER (D-2687), never "$git_dir/hooks" - a PATH SHAPE. git decides with
# core.hooksPath (and a linked worktree's hooks live in the COMMON dir), so joining the git dir here can
# install a hook git never runs while --check confirms its bytes. MEASURED 2026-09-27. check_rail_registry.py
# puts the SAME question to git, so the installer and its verifier cannot disagree about WHERE the boundary is.
hook="$(git rev-parse --git-path hooks/pre-commit)"
case "$hook" in /*) ;; *) hook="$PWD/$hook" ;; esac   # git answers relative to the caller; the caller is the repo root
mkdir -p "$(dirname "$hook")"

render_hook() {
cat <<'HOOK'
#!/usr/bin/env bash
# BUG-1000 - the four rails below shell a bare `python3`, so the interpreter they get is decided by PATH ORDER.
# MEASURED 2026-10-25: with PATH=/usr/bin:/bin the FIRST rail died on `No module named 'yaml'` and the commit
# was refused for the WRONG reason. This prelude prepends the directory of the interpreter the repository already
# PINNED (config/pipeline_config.yaml#run.python_bin) and PROVES it can import what the rails need; if it cannot,
# the diagnostic names the key, the value and the remedy. THE FOUR DECLARED LINES STAY BYTE-IDENTICAL on purpose:
# config/rail_registry.yaml#commit_boundary.must_contain names them literally, and rewriting them to "$PY" would
# turn that rail RED - a fix that breaks a checker is not a fix, so this prelude keeps both true at once.
PYDIR="$(sh scripts/resolve_python.sh --dir)" || exit 1
export PATH="$PYDIR:$PATH"
# RAIL 0 - refuse to commit THROUGH a repository whose git metadata a sync client has renamed (P0-A, BUG-400),
# or whose git dir still sits inside a sync domain (BUG-500). Strict on purpose: exit 2 (owner-owed conflict
# copies) also blocks, because a commit is the one act that makes a conflicted tree permanent.
python3 scripts/check_repo_integrity.py || exit 1
# RAIL 3 - refuse a commit that would make a digest-pinned measurement UNREPRODUCIBLE (BUG-526). The pin rule
# and its digests have ONE home (config/recalibration_pins.yaml via scripts/verify_recalibration_pins.py); this
# is that same home at the WRITE moment. It does NOT overreach: a commit naming no pinned artifact is tolerated
# even while the tree is RED - only the commit that MOVES a pinned artifact is refused.
python3 scripts/verify_recalibration_pins.py --staged || exit 1
# RAIL 5 - refuse a commit set that SPLITS a declaration from the only code that reads it (D-2669/BUG-562).
# The required lines of this hook are DECLARED in config/rail_registry.yaml#commit_boundary, so a line someone
# deletes is caught by check_rail_registry.py - this hook lives outside the synced tree (BUG-500), where no diff
# and no backup would show it.
python3 scripts/check_declaration_consumers.py --staged || exit 1
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
