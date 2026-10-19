#!/usr/bin/env bash
# BUG-802 remedy, GUARDED. The engine must survive a reboot - but it must not be started
# TWICE. D2455/D2456 record that a blind start (omlx-cli restart / a bare "omlx start" while a
# managed server is already running) spawns a DUPLICATE managed server; guard_stacks_single_source.py
# exists to catch exactly that. A launchd job that always starts the engine would be that bug,
# wearing a LaunchAgent as a disguise.
#
# So the job runs THIS: if the engine already answers its own /health, the job exits 0 and does
# nothing at all. Only when nothing answers does it bring the engine up - through the app, which
# is the engine's single source on this machine (server.auto_start_on_launch = true).
#
# Exit 0 = the engine is up (or was already). Non-zero = it is not, and the job SHOULD be
# retried by launchd (the plist declares KeepAlive {SuccessfulExit: false} for exactly this).
#
# C12: no path, port or timeout is hardcoded here - everything comes from config/engine.yaml.
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

read_cfg() {
  python3 - "$REPO/config/engine.yaml" "$1" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1]))
node = doc["engine"]
for key in sys.argv[2].split("."):
    node = node[key]
print(node)
PY
}

# BUG-940 fix: when launchd launches this script it lives OUTSIDE the repo (in ~/.omlx/), so the
# repo-relative config read would resolve to $HOME/config/engine.yaml (wrong) and any read of the
# repo's Dropbox path fails under TCC (Operation not permitted, exit 126). The installer renders the
# engine facts into EnvironmentVariables; when present they are authoritative and the repo is never
# read at runtime. The config-file fallback stays for a MANUAL run from inside the repo (the one home
# that owns these facts: config/engine.yaml).
if [ -n "${OMLX_ENGINE_HOST:-}" ] && [ -n "${OMLX_ENGINE_PORT:-}" ] && [ -n "${OMLX_ENGINE_BUNDLE:-}" ]; then
  ENGINE_HOST="$OMLX_ENGINE_HOST"
  ENGINE_PORT="$OMLX_ENGINE_PORT"
  ENGINE_BUNDLE="$OMLX_ENGINE_BUNDLE"
else
  ENGINE_HOST="$(read_cfg host)"
  ENGINE_PORT="$(read_cfg port)"
  ENGINE_BUNDLE="$(read_cfg bundle)"
fi

URL="http://${ENGINE_HOST}:${ENGINE_PORT}/health"
WAIT_S="${MAXWELL_ENGINE_WAIT_S:-120}"
GUI_APP="${ENGINE_BUNDLE%/Contents}"

if curl -s -o /dev/null -m 3 "$URL"; then
  echo "ok: the engine already answers $URL - nothing started (single-source preserved)"
  exit 0
fi

echo "engine is down ($URL silent) - bringing up $GUI_APP"
# BUG-941 restart route: `open -a <name>` is flaky; `open <full path>` reliably spawns the server.
open "$GUI_APP" || { echo "FAIL: could not open $GUI_APP"; exit 1; }
deadline=$(( $(date +%s) + WAIT_S ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if curl -s -o /dev/null -m 3 "$URL"; then
    echo "ok: the engine answers $URL after bringing up $GUI_APP"
    exit 0
  fi
  sleep 3
done
echo "FAIL: $URL did not answer within ${WAIT_S}s"
exit 1
