#!/usr/bin/env bash
# T-132 / D-3003 - ACT 1: put the ratified harness context into the environment of the process
# that needs it. A declaration that is not in the environment is a comment.
#
#   ./scripts/bind_harness_env.sh <class>            # bind THIS shell (eval the exports)
#   ./scripts/bind_harness_env.sh <class> --show     # print what would be bound
#   ./scripts/bind_harness_env.sh <class> --print    # print the export lines
#
# <class> is MANDATORY and must be a class declared in config/agent_context.yaml#classes. It was
# once optional, and the no-argument path evaled the exports into whatever shell ran the script -
# which is how the names that exist to CLAMP a narrow local window came to clamp every session of
# every provider instead, the owner's cloud lane included (BUG-871: a profile eval is not a scope).
# A binding FOR nobody is a binding for everybody, so this script now names the class or refuses.
#
# The values live in config/agent_context.yaml; they are never restated here (C12). The reader
# is pipeline/harness_env.py, which also exposes --exec for a launcher that must bind a CHILD.
#
# For a harness that is started outside a shell (the desktop app, a launchd job), wrap its launch:
#   pipeline/harness_env.py --exec /Applications/Goose.app/Contents/Resources/bin/goose run -t "..."
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
READER="$REPO/pipeline/harness_env.py"

SCOPE=""
MODE=""
for arg in "$@"; do
  case "$arg" in
    --show)  MODE="--show" ;;
    --print) MODE="--print" ;;
    -*)      echo "FATAL: unknown flag '$arg' (see the header for the interface)" >&2; exit 1 ;;
    *)       if [ -n "$SCOPE" ]; then
               echo "FATAL: more than one class given ('$SCOPE', '$arg') - one binding, one scope" >&2; exit 1
             fi
             SCOPE="$arg" ;;
  esac
done

if [ -z "$SCOPE" ]; then
  echo "FATAL: this script needs a CLASS - a profile eval is not a scope (BUG-871)." >&2
  echo "       declared classes: $(python3 "$READER" --jobs 2>/dev/null | sed -n 's/^\([a-z_]*\) .*/\1/p' | tr '\n' ' ')" >&2
  echo "       usage: $0 <class> [--show|--print]" >&2
  exit 1
fi

case "$MODE" in
  --show)
    echo "The declared contract (from config/agent_context.yaml), bound FOR '$SCOPE':"
    python3 "$READER" --print --scope "$SCOPE" || exit 1
    echo
    echo "Current state:"
    python3 "$READER" --check || true
    ;;
  --print)
    python3 "$READER" --print --scope "$SCOPE" || exit 1
    ;;
  *)
    if ! BOUND="$(python3 "$READER" --print --scope "$SCOPE")"; then
      echo "FATAL: the reader refused scope '$SCOPE' - nothing was bound (C16: no silent failure)" >&2
      exit 1
    fi
    eval "$BOUND"
    echo "bound FOR '$SCOPE':"
    python3 "$READER" --check || true
    ;;
esac
