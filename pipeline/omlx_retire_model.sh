#!/usr/bin/env bash
# Retire a served model from the pool WITHOUT leaving a name that lies.
#
# WHY THIS IS NOT "rm": parking a model created seven `_unloaded` entries whose targets are ABSENT
# (BUG-808) - names that read as "on disk" and resolve to nothing, which is what made two bench rows
# read NA. So retirement has two steps and both are explicit: unload it from the engine's memory, then
# either PARK it inside the engine's own directory (reversible, no dangling link) or, with the owner's
# separate word, hand the bytes to pipeline/safe_delete.py (R-D410).
#
# Usage:
#   pipeline/omlx_retire_model.sh --model NAME              # dry run: shows exactly what would move
#   pipeline/omlx_retire_model.sh --model NAME --confirm    # unload + park under models_stashed/
#   pipeline/omlx_retire_model.sh --model NAME --purge      # additionally PRINTS the safe_delete command
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
MODEL=""
MODE="dry"
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --confirm) MODE="apply"; shift ;;
    --purge) MODE="purge"; shift ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
[ -n "$MODEL" ] || { echo "usage: pipeline/omlx_retire_model.sh --model NAME [--confirm|--purge]"; exit 2; }

read_cfg() { python3 - "$REPO/config/engine.yaml" "$1" <<'PY'
import sys, yaml
node = yaml.safe_load(open(sys.argv[1]))["engine"]
for k in sys.argv[2].split("."):
    node = node[k]
print(node)
PY
}
MODEL_DIR="$(read_cfg model_dir)"
STASH="$(dirname "$MODEL_DIR")/models_stashed"
ENTRY="$MODEL_DIR/$MODEL"

[ -e "$ENTRY" ] || { echo "FAIL: $ENTRY does not exist"; exit 1; }
TARGET="$(readlink "$ENTRY" 2>/dev/null || echo "(a real directory)")"

if [ "$MODE" = "dry" ]; then
  echo "DRY RUN (nothing changed)."
  echo "  model   : $MODEL"
  echo "  entry   : $ENTRY -> $TARGET"
  echo "  would   : unload it from the engine, then move the ENTRY (not the bytes) to $STASH/$MODEL"
  echo "  never   : leave a symlink pointing at nothing (BUG-808)"
  echo "Re-run with --confirm to retire it."
  [ "$MODE" = "purge" ] && echo "  purge   : would also print the safe_delete command for $TARGET"
  exit 0
fi

KEY=$(python3 -c "import sys;sys.path.insert(0,'$REPO');from pipeline.pipeline_paths import OMLX_API_KEY as k;print(k)" 2>/dev/null || true)
HOST=$(read_cfg host); PORT=$(read_cfg port)
echo "unloading $MODEL from the engine"
curl -sS -m 120 -X POST -H "Authorization: Bearer $KEY" "http://$HOST:$PORT/v1/models/$MODEL/unload" || echo "note: unload returned non-zero (it may not have been resident)"

mkdir -p "$STASH"
if [ -L "$ENTRY" ]; then
  rm "$ENTRY" && echo "removed the engine entry (a symlink; the hub bytes stay where they are)"
else
  mv "$ENTRY" "$STASH/$MODEL" && echo "moved the real directory to $STASH/$MODEL"
fi
echo "parked: $MODEL"
if [ "$MODE" = "purge" ]; then
  echo ""
  echo "The bytes are NOT deleted by this script. If they should go, the owner runs:"
  echo "  python3 pipeline/safe_delete.py '$TARGET' --reason 'retired model NAME - <why>'"
fi
