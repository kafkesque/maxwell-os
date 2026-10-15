#!/usr/bin/env bash
# T-132 / D-3003 - ACT 1: put the ratified harness context into the environment of the process
# that needs it. A declaration that is not in the environment is a comment.
#
#   ./scripts/bind_harness_env.sh            # bind THIS shell (eval the exports)
#   ./scripts/bind_harness_env.sh --show     # print what would be bound
#   ./scripts/bind_harness_env.sh --print    # print the export lines
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

case "${1:-}" in
  --show)
    echo "The declared contract (from config/agent_context.yaml):"
    python3 "$READER" --print
    echo
    echo "Current state:"
    python3 "$READER" --check || true
    ;;
  --print)
    python3 "$READER" --print
    ;;
  *)
    eval "$(python3 "$READER" --print)"
    echo "bound:"
    python3 "$READER" --check || true
    ;;
esac
