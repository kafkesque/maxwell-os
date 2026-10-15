#!/usr/bin/env bash
# BUG-802 remedy installer. THE OWNER RUNS THIS - loading a launchd job is a SYSTEM act, not an agent act.
# Fail-closed: after loading, it WAITS for the engine's own /health; if the engine does not come up it
# UNLOADS the job and exits non-zero, so the remedy cannot leave the machine worse than it found it.
set -o pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
TPL="$REPO/pipeline/com.maxwell.omlx-engine.plist"
LABEL="com.maxwell.omlx-engine"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
URL="$MAXWELL_ENGINE_HEALTH"
[ -z "$URL" ] && URL="http://127.0.0.1:11435/health"
WAIT_S="$MAXWELL_ENGINE_WAIT_S"
[ -z "$WAIT_S" ] && WAIT_S=90

CONFIRMED=0
if [ "$#" -gt 0 ] && [ "$1" = "--confirm" ]; then CONFIRMED=1; fi

if [ "$CONFIRMED" -ne 1 ]; then
  echo "DRY RUN (nothing changed). This will:"
  echo "  1. render $TPL -> $DEST   (substituting HOME and REPO; the repo stores no absolute path)"
  echo "  2. launchctl bootstrap gui/$(id -u) $DEST"
  echo "  3. poll $URL for up to $WAIT_S s; on failure: launchctl bootout + exit 1"
  echo "Re-run with --confirm to install."
  exit 0
fi

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  echo "note: $LABEL is already loaded - booting it out first"
  launchctl bootout "gui/$(id -u)/$LABEL" || true
fi
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.omlx/logs"
sed -e "s|@HOME@|$HOME|g" -e "s|@REPO@|$REPO|g" "$TPL" > "$DEST"
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
