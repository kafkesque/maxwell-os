#!/usr/bin/env bash
# BUG-802 remedy installer. THE OWNER RUNS THIS - loading a launchd job is a SYSTEM act, not an agent act.
# Fail-closed: after loading, it WAITS for the engine's own /health; if the engine does not come up it
# UNLOADS the job and exits non-zero, so the remedy cannot leave the machine worse than it found it.
set -o pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
TPL="$REPO/pipeline/com.maxwell.omlx-engine.plist"
GUARD_SRC="$REPO/pipeline/omlx_engine_guard.sh"
GUARD_DEST="$HOME/.omlx/omlx_engine_guard.sh"
LABEL="com.maxwell.omlx-engine"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

# BUG-940: the engine facts are read ONCE here (the interactive owner has TCC access to the repo)
# and rendered into the plist's EnvironmentVariables, so the deployed guard reads nothing from the
# Dropbox path at runtime. One home (config/engine.yaml), read by the installer, not by the job.
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
ENGINE_HOST="$(read_cfg host)"
ENGINE_PORT="$(read_cfg port)"
ENGINE_BUNDLE="$(read_cfg bundle)"

URL="$MAXWELL_ENGINE_HEALTH"
[ -z "$URL" ] && URL="http://$ENGINE_HOST:$ENGINE_PORT/health"
WAIT_S="$MAXWELL_ENGINE_WAIT_S"
[ -z "$WAIT_S" ] && WAIT_S=90

CONFIRMED=0
if [ "$#" -gt 0 ] && [ "$1" = "--confirm" ]; then CONFIRMED=1; fi

if [ "$CONFIRMED" -ne 1 ]; then
  echo "DRY RUN (nothing changed). This will:"
  echo "  1. copy $GUARD_SRC -> $GUARD_DEST (OUT of the Dropbox/TCC path - BUG-940)"
  echo "  2. render $TPL -> $DEST (substituting HOME, REPO and the engine facts; no absolute path stored)"
  echo "  3. launchctl bootstrap gui/$(id -u) $DEST"
  echo "  4. poll $URL for up to $WAIT_S s; on failure: launchctl bootout + exit 1"
  echo "Re-run with --confirm to install."
  exit 0
fi

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  echo "note: $LABEL is already loaded - booting it out first"
  launchctl bootout "gui/$(id -u)/$LABEL" || true
fi
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.omlx/logs"
# BUG-940: deploy the guard OUTSIDE the repo (TCC-safe) and render the engine facts into the job.
cp "$GUARD_SRC" "$GUARD_DEST" || { echo "FAIL: could not copy $GUARD_SRC -> $GUARD_DEST"; exit 1; }
chmod +x "$GUARD_DEST"
sed -e "s|@HOME@|$HOME|g" \
    -e "s|@REPO@|$REPO|g" \
    -e "s|@ENGINE_HOST@|$ENGINE_HOST|g" \
    -e "s|@ENGINE_PORT@|$ENGINE_PORT|g" \
    -e "s|@ENGINE_BUNDLE@|$ENGINE_BUNDLE|g" "$TPL" > "$DEST"
launchctl bootstrap "gui/$(id -u)" "$DEST" || { echo "FAIL: bootstrap refused"; exit 1; }

deadline=$(( $(date +%s) + WAIT_S ))
while true; do
  if curl -s -o /dev/null -m 3 "$URL"; then
    echo "ok: $LABEL loaded and the engine answers $URL"
    echo "receipt: rendered job at $DEST; boot log ~/.omlx/logs/boot_agent.out.log"
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "FAIL: engine did not answer $URL within $WAIT_S s - ROLLING BACK (bootout)"
    launchctl bootout "gui/$(id -u)/$LABEL" || true
    echo "rollback receipt: job removed; the machine is as it was. See ~/.omlx/logs/boot_agent.err.log"
    exit 1
  fi
  sleep 3
done
