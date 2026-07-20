#!/bin/bash
# backup_guardian.sh — Maxwell OS · Pre-flight Backup Guardian
# ============================================================
# rsync `final fbs/` → `5.backup/` with timestamp.
# Run before ANY write operation to protect against data loss.
#
# Usage:
#   ./tools/backup_guardian.sh                    # backup, timestamped
#   ./tools/backup_guardian.sh --quiet            # silent unless error
#   ./tools/backup_guardian.sh --dry-run          # preview only
#
# B-laws:
#   B199: script lives in tools/, ROOT = parent dir
#   B174: no hardcoded tokens (no tokens needed for file ops)
#
# Standing constraint:
#   ALWAYS rsync fbs/ → 5.backup/ after any batch write

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SOURCE="$ROOT/knowledge pipeline/output/5.generated"
TARGET="$ROOT/knowledge pipeline/output/5.backup"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
QUIET=false
DRY_RUN=false

# Parse args
for arg in "$@"; do
    case "$arg" in
        --quiet)   QUIET=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
done

# Validate source exists
if [ ! -d "$SOURCE" ]; then
    echo "❌ backup_guardian: Source not found: $SOURCE"
    exit 1
fi

# Ensure target exists
if [ ! -d "$TARGET" ]; then
    echo "  backup_guardian: Creating target: $TARGET"
    $DRY_RUN || mkdir -p "$TARGET"
fi

# Count what we're backing up
FB_COUNT=$(find "$SOURCE" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
SUB_COUNT=0
if [ -d "$SOURCE/substrate" ]; then
    SUB_COUNT=$(find "$SOURCE"/substrate -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
fi
TOTAL_COUNT=$((FB_COUNT + SUB_COUNT))

$QUIET || echo "  🔒 backup_guardian: Pre-flight backup — $TOTAL_COUNT files"
$QUIET || echo "    Source: $SOURCE"
$QUIET || echo "    Target: $TARGET"
$QUIET || echo "    Timestamp: $TIMESTAMP"

if $DRY_RUN; then
    echo "    [DRY-RUN] rsync -a --delete \"$SOURCE/\" \"$TARGET/\""
    echo "    [DRY-RUN] Would backup $TOTAL_COUNT files"
    exit 0
fi

# Execute rsync
# --delete removes files from target that were deleted from source
# -a preserves permissions, timestamps, etc.
rsync -a --delete "$SOURCE/" "$TARGET/" 2>&1
RSYNC_EXIT=$?

if [ $RSYNC_EXIT -eq 0 ]; then
    $QUIET || echo "    ✅ backup_guardian: $TOTAL_COUNT files synced (ts=$TIMESTAMP)"
else
    echo "    ❌ backup_guardian: rsync failed (exit=$RSYNC_EXIT)"
    exit $RSYNC_EXIT
fi

# Write timestamp marker
echo "$TIMESTAMP" > "$TARGET/.last_backup"
