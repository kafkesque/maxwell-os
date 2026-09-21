#!/bin/bash
# backup_guardian.sh — Maxwell OS · DB Backup Guardian (C13)
# ============================================================
# Consistent SQLite backup of the knowledge DB, run before/after ANY batch
# write. Uses sqlite3's online backup API (`.backup`) so the copy is
# transaction-consistent even while the DB is open in WAL mode — unlike
# `shutil.copy2`/`cp`, which can capture a torn mid-write state.
#
# BUG-276: the previous version rsync'd `output/5.generated` (markdown), which
# no longer exists and was NOT the DB — there was effectively no automated DB
# backup. This script now backs up the actual SQLite DB and integrity-checks
# the copy (fail-closed).
#
# Usage:
#   bash pipeline/backup_guardian.sh               # backup, timestamped
#   bash pipeline/backup_guardian.sh --quiet       # silent unless error
#   bash pipeline/backup_guardian.sh --dry-run     # preview only
#   bash pipeline/backup_guardian.sh --tag pre_serving_gate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DB="$ROOT/knowledge pipeline/maxwell.db"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
TAG=""
QUIET=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --quiet)   QUIET=true ;;
        --dry-run) DRY_RUN=true ;;
        --tag=*)   TAG="_${arg#--tag=}" ;;
    esac
done

DEST="${DB}.bak_${TIMESTAMP}${TAG}"

if [ ! -f "$DB" ]; then
    echo "❌ backup_guardian: DB not found: $DB" >&2
    exit 1
fi

if $DRY_RUN; then
    echo "    [DRY-RUN] sqlite3 \"$DB\" \".backup '$DEST'\""
    exit 0
fi

$QUIET || echo "  🔒 backup_guardian: consistent DB backup"
$QUIET || echo "    Source: $DB"
$QUIET || echo "    Dest:   $DEST"

if ! sqlite3 "$DB" ".backup '$DEST'"; then
    echo "    ❌ backup_guardian: sqlite3 .backup failed" >&2
    exit 1
fi

CHECK="$(sqlite3 "$DEST" "PRAGMA integrity_check;" 2>/dev/null || true)"
if [ "$CHECK" != "ok" ]; then
    echo "    ❌ backup_guardian: integrity_check on backup failed: ${CHECK:-<empty>}" >&2
    exit 1
fi

printf '%s' "$TIMESTAMP" > "$(dirname "$DEST")/.last_db_backup"
$QUIET || echo "    ✅ backup_guardian: backup written + integrity ok (ts=$TIMESTAMP)"
