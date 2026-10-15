#!/usr/bin/env bash
# F6 / BUG-792 - ACT 3: turn the engine's tiered KV cache ON, with an SSD directory that is
# DISTINCT from the one the owner cleaned.
#
# WHY THE GUARD RAILS:
#   * cache.enabled is false in the live settings. The documented SSD example path is
#     ~/.omlx/cache - the very directory the owner emptied on 2026-10-15 (BUG-807). Reusing it
#     would put a second generation of cache bytes back into a path the owner has just proven
#     they will clear by hand. So the SSD tier gets its OWN declared directory.
#   * The engine is a GUI app. Its settings are re-read through the local admin API
#     (POST /admin/api/reload - the path scripts/omlx_reload.py uses, D2637), NOT by a blind
#     restart: D2455/D2456 record that a restart spawns a duplicate managed server.
#   * Fail-closed: the file is copied first and restored if the engine stops answering, so the
#     machine cannot be left worse than it was found. Same shape as
#     pipeline/install_omlx_engine_agent.sh.
#
# Usage: pipeline/omlx_cache_enable.sh            # dry run, prints the exact change
#        pipeline/omlx_cache_enable.sh --confirm  # apply, then prove the engine still answers
#        pipeline/omlx_cache_enable.sh --rollback # restore the pre-change settings
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
BACKUP="$HOME/.omlx/settings.json.bak-cache_enable"
CONFIRMED=0
MODE="dry"
[ "${1:-}" = "--confirm" ] && { CONFIRMED=1; MODE="apply"; }
[ "${1:-}" = "--rollback" ] && MODE="rollback"

read_cfg() { python3 - "$REPO/config/engine.yaml" "$1" <<'PY'
import sys, yaml
node = yaml.safe_load(open(sys.argv[1]))["engine"]
for k in sys.argv[2].split("."):
    node = node[k]
print(node)
PY
}
SETTINGS="$HOME/.omlx/settings.json"
[ -f "$SETTINGS" ] || SETTINGS="$(read_cfg settings)"
URL="http://$(read_cfg host):$(read_cfg port)/health"
RELOAD="$REPO/scripts/omlx_reload.py"

if [ "$MODE" = "rollback" ]; then
  [ -f "$BACKUP" ] || { echo "FAIL: no backup at $BACKUP - nothing to roll back to"; exit 1; }
  cp "$BACKUP" "$SETTINGS" && echo "rolled back: $BACKUP -> $SETTINGS"
  [ -f "$RELOAD" ] && python3 "$RELOAD" --json >/dev/null 2>&1
  curl -s -o /dev/null -m 5 "$URL" && { echo "ok: the engine answers after the rollback"; exit 0; }
  echo "FAIL: the engine does not answer after the rollback"; exit 1
fi

echo "settings: $SETTINGS"
python3 - "$SETTINGS" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print("before:", json.dumps(d.get("cache", {})))
PY

if [ "$CONFIRMED" -ne 1 ]; then
  echo "DRY RUN (nothing changed). This will:"
  echo "  1. back up the settings to $BACKUP"
  echo "  2. set cache.enabled=true, cache.hot_cache_only=false, cache.ssd_cache_dir=$HOME/.omlx/ssd_cache"
  echo "  3. re-read them through the admin API ($RELOAD), never by restarting (D2455/D2456)"
  echo "  4. prove the engine still answers $URL; if not, RESTORE the backup and reload again"
  echo "  5. print /v1/models/status so the pool is re-measured, not assumed"
  echo "Re-run with --confirm to apply."
  exit 0
fi

cp "$SETTINGS" "$BACKUP"
python3 - "$SETTINGS" "$HOME/.omlx/ssd_cache" <<'PY'
import json, sys
path, ssd = sys.argv[1], sys.argv[2]
raw = open(path).read()
d = json.loads(raw)
cache = d.setdefault("cache", {})
cache["enabled"] = True
cache["hot_cache_only"] = False
cache["ssd_cache_dir"] = ssd
tmp = path + ".tmp"
open(tmp, "w").write(json.dumps(d, indent=2))
import os; os.replace(tmp, path)
print("after:", json.dumps(cache))
PY
mkdir -p "$HOME/.omlx/ssd_cache"

echo "re-reading settings through the admin API"
if [ -f "$RELOAD" ]; then
  python3 "$RELOAD" --json >/dev/null 2>&1 || echo "note: reload returned non-zero; the health probe below decides"
fi

deadline=$(( $(date +%s) + 60 ))
while true; do
  if curl -s -o /dev/null -m 5 "$URL"; then
    echo "ok: the engine answers $URL with the cache enabled"
    echo "receipt: backup at $BACKUP; SSD tier at $HOME/.omlx/ssd_cache"
    [ -f "$RELOAD" ] && python3 "$RELOAD" --json 2>/dev/null | head -20
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "FAIL: the engine stopped answering after the change - RESTORING $BACKUP"
    cp "$BACKUP" "$SETTINGS"
    [ -f "$RELOAD" ] && python3 "$RELOAD" --json >/dev/null 2>&1
    sleep 5
    curl -s -o /dev/null -m 5 "$URL" && echo "rollback receipt: settings restored and the engine answers" && exit 1
    echo "FAIL WORSE: the engine is silent even after the rollback - see ~/.omlx/logs/server.log"
    exit 1
  fi
  sleep 3
done
