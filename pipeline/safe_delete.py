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
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "backup" / "deletions"

# Protected trees — safe_delete is the only deletion path for these.
# BUG-625(c): the data-dir name is read config-first (paths.data_dir) so safe_delete protects whatever
# tree is actually configured; "knowledge pipeline" is kept as a permanent defense-in-depth entry because
# over-protection is the fail-safe direction for a deletion guard (must not depend on config readability).
try:
    import yaml as _yaml
    _DATA_DIR_NAME = ((_yaml.safe_load(open(ROOT / "config" / "pipeline_config.yaml", encoding="utf-8")) or {}).get("paths") or {}).get("data_dir", "knowledge pipeline")
except Exception:
    _DATA_DIR_NAME = "knowledge pipeline"

PROTECTED_TREES = [
    _DATA_DIR_NAME,
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


def _delete_safety_roots():
    """Read the model + storage roots from config/delete_safety.yaml (C12, fail-closed).

    BUG-1102: `scripts/check_delete_target.py` is the ONLY instrument that knows whether model bytes are
    SERVED, REFERENCED, SHARED or IN FLIGHT. This helper names the roots that decide whether a path IS model
    bytes, so the four-axis gate is applied where it is relevant and pipeline output (which the rail does not
    cover) is left to `is_protected()`.

    An unreadable config is a REFUSAL, never a smaller search space (D-2644/BUG-1083): a deleter that cannot
    read its own gate would fail OPEN, which is the exact direction this bug is about.
    """
    cfg_path = ROOT / "config" / "delete_safety.yaml"
    try:
        cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        roots = list(cfg["model_roots"]) + list(cfg["storage_roots"])
    except Exception as exc:  # C16: say it AND refuse, never a silent skip
        raise SystemExit(
            f"FAIL-CLOSED (safe_delete): cannot read {cfg_path} ({exc}) - "
            "the four-axis delete gate cannot be evaluated, so nothing is deleted"
        ) from None
    return [Path(str(r)).expanduser().resolve() for r in roots]


def _is_model_bytes(path):
    """True when the path's REALPATH lies under a declared model/storage root (BUG-1102).

    The test uses the realpath, so a pipeline path that is a SYMLINK into a model root is still caught:
    deleting it would delete the model bytes it resolves to.
    """
    real = Path(path).resolve()
    for root in _delete_safety_roots():
        if real == root or root in real.parents:
            return True
    return False


def delete_rail_gate(path):
    """Run the four-axis rail read-only and refuse unless it says SAFE_TO_DELETE (BUG-1102).

    Returns (safe: bool, detail: str). This function NEVER deletes and NEVER mutates the target.
    The gate is NON-BYPASSABLE: an owner's `--maxwell-confirmed` word records INTENT, but it cannot make a
    SERVED model safe to delete, so the four axes are asked regardless of that word.

    Exit codes are the rail's own (scripts/check_delete_target.py):
      0 SAFE_TO_DELETE | 2 REFUSE | 3 UNDETERMINED (fail-closed) | 4 usage/config error
    """
    if not _is_model_bytes(path):
        return True, "not model bytes (the four axes do not apply; pipeline output keeps is_protected)"
    rail = ROOT / "scripts" / "check_delete_target.py"
    if not rail.exists():
        return False, f"FAIL-CLOSED: the delete rail is missing at {rail}"
    proc = subprocess.run(
        [sys.executable, str(rail), str(path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if proc.returncode == 0:
        return True, "SAFE_TO_DELETE (served/referenced/shared/in-flight all clear)"
    if proc.returncode == 2:
        return False, "REFUSE (the four axes: something still serves, links to, shares or is downloading these bytes)"
    if proc.returncode == 3:
        return False, "UNDETERMINED (fail-closed: the engine is unreachable, so 'still advertised' cannot be ruled out)"
    return False, f"USAGE/CONFIG ERROR rc={proc.returncode} (the delete guard could not run, so nothing is deleted)"


def _tree_stats(path):
    """(file_count, total_bytes) for a file or a directory (recursive, stat only — no read)."""
    path = Path(path)
    if path.is_file():
        return 1, path.stat().st_size
    count = 0
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            count += 1
            total += f.stat().st_size
    return count, total


def _verify_backup(src, dest):
    """Prove the backup holds the same file count and bytes as the source (R5 concern, BUG-1102b).

    Returns (ok: bool, detail: str). A backup that is NOT verified is not a backup: the deletion it
    protects is irreversible, so a short copy must REFUSE the deletion rather than proceed on hope.
    LIMIT (stated, not hidden): this is a cheap stat-level equality, not a content hash — it catches
    truncation, a missing file and a failed copy; it does not catch silent bit-rot inside an equally
    sized file. A hash is deliberately not paid for here because a 15 GB model copy would double the
    pre-flight cost for a failure mode that `shutil.copy2` does not produce.
    """
    src_count, src_bytes = _tree_stats(src)
    dst_count, dst_bytes = _tree_stats(dest)
    if (src_count, src_bytes) != (dst_count, dst_bytes):
        return False, (f"backup MISMATCH: source {src_count} file(s)/{src_bytes} B vs "
                       f"backup {dst_count} file(s)/{dst_bytes} B")
    return True, f"{dst_count} file(s) / {dst_bytes} B verified"


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

    # BUG-1102 GATE (read-only): the four irreversibility axes, asked BEFORE any copy or delete.
    # Placed ahead of the backup so a REFUSED deletion never copies 15 GB of a served model first.
    # Non-bypassable: --maxwell-confirmed records intent, but cannot make a SERVED model safe to delete.
    rail_safe, rail_detail = delete_rail_gate(path)
    if not rail_safe:
        print(f"⛔ REFUSING (four-axis delete gate): {path}")
        print(f"   {rail_detail}")
        print("   Read the full verdict, nothing is deleted:  python3 scripts/check_delete_target.py <path>")
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

    # VERIFY THE BACKUP before anything is deleted (R5 concern 2026-10-28, BUG-1102b): a backup
    # that is not verified is not a backup, and the deletion it protects is irreversible.
    ok, verify_detail = _verify_backup(path, dest)
    if not ok:
        print(f"  ❌ {verify_detail}")
        print("  ⛔ REFUSING to delete: the backup does not match the source. Nothing was deleted.")
        sys.exit(1)
    print(f"  ✅ Backup verified: {verify_detail}")

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


def selftest():
    """Known-answer controls for the BUG-1102 four-axis gate (nothing is deleted, 0 model calls)."""
    import inspect

    failures: list[str] = []

    def check(name, cond, detail=""):
        if cond:
            print(f"  PASS {name}")
        else:
            failures.append(name)
            print(f"  FAIL {name} {detail}")

    # A. the gate config is readable and declares at least one root (a deleter that cannot read its own
    #    gate would fail OPEN - the exact direction BUG-1102 is about).
    roots = _delete_safety_roots()
    check("the delete-safety config declares >= 1 model/storage root", len(roots) >= 1, f"roots={len(roots)}")

    # B. a path under the FIRST declared root reads as MODEL BYTES (so the four axes will be asked).
    probe_under = roots[0] / "__selftest_probe__"
    check("a path under the first declared root reads as model bytes", _is_model_bytes(probe_under) is True)

    # C. a non-model path is NOT gated as model bytes, and the rail is never invoked (0 model calls).
    probe_out = ROOT / "temp" / "__selftest_not_model__"
    check("a non-model path is not gated as model bytes", _is_model_bytes(probe_out) is False)
    safe, detail = delete_rail_gate(probe_out)
    check("a non-model path passes the gate WITHOUT invoking the rail",
          safe is True and "not model bytes" in detail, detail)

    # D. the gate is NON-BYPASSABLE: delete_rail_gate exposes no parameter that could skip the four axes.
    params = list(inspect.signature(delete_rail_gate).parameters)
    check("the gate exposes no bypass parameter (an owner word cannot skip the four axes)",
          params == ["path"], f"params={params}")

    # E. the BACKUP is VERIFIED, and a SHORT backup is refused (R5 finding 2026-10-28, BUG-1102b).
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello", encoding="utf-8")
        (src / "b.txt").write_text("world", encoding="utf-8")
        good = Path(td) / "good"
        shutil.copytree(src, good)
        ok_good, _ = _verify_backup(src, good)
        check("a matching backup verifies", ok_good is True)
        short = Path(td) / "short"
        shutil.copytree(src, short)
        (short / "b.txt").unlink()
        ok_short, detail_short = _verify_backup(src, short)
        check("a short backup is REFUSED (never delete on hope)", ok_short is False, detail_short)

    if failures:
        print(f"FAIL safe_delete selftest: {len(failures)} control(s) failed: {', '.join(failures)}")
        return 1
    print("ok safe_delete selftest: 7/7 controls")
    return 0


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
    parser.add_argument(
        "--selftest", action="store_true", help="Run the BUG-1102 four-axis gate known-answer controls"
    )

    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

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
