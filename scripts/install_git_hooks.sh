#!/usr/bin/env bash
# Install rail 4 as a PRE-COMMIT hook, so a plan violation is refused instead of reported (BUG-445).
# Rationale: a post-hoc check cannot un-commit. On 2026-09-25 a will_not_touch owner instrument was
# committed with 'git add -A', and the plan was then widened to silence the report (scope laundering).
set -euo pipefail
cd "$(dirname "$0")/.."
hook=".git/hooks/pre-commit"
cat > "$hook" <<'HOOK'
#!/usr/bin/env bash
# RAIL 4 - refuse a commit whose staged paths are outside the session plan. Never bypass with --no-verify.
exec python3 scripts/check_session_plan.py --staged
HOOK
chmod +x "$hook"
echo "installed $hook"
python3 scripts/check_session_plan.py --staged
