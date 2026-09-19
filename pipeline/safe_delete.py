#!/usr/bin/env python3
"""
safe_delete.py — The ONLY sanctioned deletion path for pipeline output.

§F.4 of FABLE-SOLUTIONS-2026-06-11.

Protocol:
  1. Copies target to backup/deletions/{timestamp}/
  2. Prints what/why/size
  3. Requires interactive confirmation (or --maxwell-confirmed "<reason>")
  4. Then deletes

Raw rm / shutil.rmtree / overwrite-deletes on knowledge pipeline/ or
education/ trees = hygiene violation per Output Deletion Law.

Usage:
  python3 tools/safe_delete.py path/to/file_or_dir
  python3 tools/safe_delete.py path/to/file --reason "cleaning stale temp"
  python3 tools/safe_delete.py path/to/dir --maxwell-confirmed "D398: corrupted D5"
  python3 tools/safe_delete.py --list-pending          # show backup/deletions/
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "backup" / "deletions"

# Protected trees — safe_delete is the only deletion path for these
PROTECTED_TREES = [
    "knowledge pipeline",
    "education",
    "5.generated",
    "6.validated",
    "7.accepted",
]


def get_size_str(path):
    """Human-readable size of a file or directory."""
    path = Path(path)
    if path.is_file():
        size = path.stat().st_size
    elif path.is_dir():
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    else:
        size = 0

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def is_protected(path):
    """Check if path is inside a protected tree."""
    resolved = Path(path).resolve()
    for tree in PROTECTED_TREES:
        tree_path = (ROOT / tree).resolve()
        try:
            resolved.relative_to(tree_path)
            return True
        except ValueError:
            continue
    return False


def backup_then_delete(path, reason, no_confirm=False, maxwell_confirmed=None):
    """Backup then delete the target path."""
    path = Path(path)
    if not path.exists():
        print(f"❌ Path does not exist: {path}")
        sys.exit(1)

    # Check if protected
    is_protected_path = is_protected(path)
    if is_protected_path and not maxwell_confirmed:
        print(f"🔒 PROTECTED: {path} is inside a pipeline output tree.")
        print('   Use --maxwell-confirmed "<reason from DECISION-LOG>" to proceed.')
        sys.exit(1)

    # FREE-SPACE PRE-FLIGHT (BUG-261, 2026-09-17): this function COPIES the target into
    # backup/deletions/ before deleting, so the operation needs ~2x the target size free.
    # On 2026-09-17 a 19 GB model was reclaimed on a volume with 24 GB free; the copy drove
    # the volume to 1.7 GB free (100% used) and had to be killed mid-copy, leaving a partial
    # backup that then had to be removed by hand. Refuse instead of risking a full disk —
    # a full disk corrupts whatever is writing at the time (DB, checkpoints, Parquet).
    # Escape hatch for genuinely large artifacts that need no backup (model weights):
    #   MAXWELL_SAFE_DELETE_LARGE=1
    try:
        import os

        need = (sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                if path.is_dir() else path.stat().st_size)
        free = shutil.disk_usage(str(path.parent)).free
        if need > free * 0.5 and os.environ.get('MAXWELL_SAFE_DELETE_LARGE') != '1':
            print(f"🛑 REFUSING: backing up {get_size_str(path)} needs ~{need / 1e9:.1f} GB free "
                  f"but only {free / 1e9:.1f} GB is available.")
            print('   This function copies before deleting, so the free space must exceed the '
                  'target size.')
            print('   For model weights (not pipeline output) delete directly with rm -rf.')
            print('   To override anyway: MAXWELL_SAFE_DELETE_LARGE=1')
            sys.exit(1)
    except OSError as exc:
        print(f"⚠️  free-space pre-flight skipped: {exc}")

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = BACKUP_DIR / timestamp
    backup_subdir.mkdir(parents=True, exist_ok=True)

    dest = backup_subdir / path.name
    size_str = get_size_str(path)

    print(f"\n{'=' * 60}")
    print(f"SAFE DELETE — {path}")
    print(f"{'=' * 60}")
    print(f"  Size:    {size_str}")
    print(f"  Type:    {'Directory' if path.is_dir() else 'File'}")
    print(f"  Reason:  {reason or 'Not specified'}")
    print(f"  Backup:  {dest}")
    print()

    # Copy to backup
    try:
        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)
        print(f"  ✅ Backup created: {dest}")
    except Exception as e:
        print(f"  ❌ Backup failed: {e}")
        sys.exit(1)

    # Confirmation
    if maxwell_confirmed:
        confirmed = True
        print(f"  ✅ Maxwell-confirmed: {maxwell_confirmed}")
    elif no_confirm:
        confirmed = True
    else:
        response = input(f"  Delete {path}? [y/N] ").strip().lower()
        confirmed = response == "y"

    if not confirmed:
        print("  ⏹️  Cancelled. Backup preserved at:", dest)
        sys.exit(0)

    # Delete
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  ✅ Deleted: {path}")
        print(f"  📦 Backup preserved at: {dest}")
        print("  ℹ️  Log to DECISION-LOG.md if this is a pipeline output deletion.")
    except Exception as e:
        print(f"  ❌ Delete failed: {e}")
        sys.exit(1)


def list_pending():
    """List all deletion backups."""
    if not BACKUP_DIR.exists():
        print("No deletion backups found.")
        return
    backups = sorted(BACKUP_DIR.iterdir())
    if not backups:
        print("No deletion backups found.")
        return
    print(f"\nDeletion backups ({len(backups)}):")
    print("-" * 60)
    for b in backups:
        size = get_size_str(b)
        items = len(list(b.rglob("*"))) if b.is_dir() else 1
        print(f"  {b.name}  |  {size}  |  {items} items")


def main():
    parser = argparse.ArgumentParser(
        description="Safe deletion tool for Maxwell OS pipeline output."
    )
    parser.add_argument("path", nargs="?", help="Path to file or directory to delete")
    parser.add_argument("--reason", help="Why this deletion is happening")
    parser.add_argument(
        "--no-confirm", action="store_true", help="Skip interactive confirmation"
    )
    parser.add_argument(
        "--maxwell-confirmed",
        help="Maxwell-authorized deletion with logged reason. "
        "Must reference a DECISION-LOG entry.",
    )
    parser.add_argument(
        "--list-pending", action="store_true", help="List all deletion backups"
    )

    args = parser.parse_args()

    if args.list_pending:
        list_pending()
        return

    if not args.path:
        parser.print_help()
        sys.exit(1)

    backup_then_delete(
        args.path,
        reason=args.reason,
        no_confirm=args.no_confirm,
        maxwell_confirmed=args.maxwell_confirmed,
    )


if __name__ == "__main__":
    main()
