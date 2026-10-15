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

URL="http://$(read_cfg host):$(read_cfg port)/health"
WAIT_S="${MAXWELL_ENGINE_WAIT_S:-120}"
GUI_APP="$(read_cfg bundle)"
GUI_APP="${GUI_APP%/Contents}"

if curl -s -o /dev/null -m 3 "$URL"; then
  echo "ok: the engine already answers $URL - nothing started (single-source preserved)"
  exit 0
fi

echo "engine is down ($URL silent) - bringing up $GUI_APP"
open -a "$GUI_APP" || { echo "FAIL: could not open $GUI_APP"; exit 1; }
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
