#!/usr/bin/env python3
"""
doc_guard.py — Goose-Level Document Protection Interceptor (D-D11)

THE PROBLEM: Goose's write/edit/shell tools have ZERO pre-flight hooks.
D824 says "never overwrite protected files" but nothing PREVENTS it.
enforce_decisions.py catches the corpse — doesn't stop the murder.

THIS FIX: Pre-operation snapshot + post-operation verification.
Call preflight() before any write, postflight() after.
Violation → auto-restore from vault + halt.

Protected files manifest with minimum line counts.
Append-only policy for DECISION-LOG.md, MASTER-TASK-REGISTER.md, AGENTS.md.
Never-overwrite policy for .env and config/*.yaml.

Usage:
    from tools.doc_guard import preflight, postflight, is_protected
    preflight()                          # snapshot before write
    # ... do write operation ...
    violations = postflight()            # verify after, returns list
    if violations:
        print("BLOCKED:", violations)

CLI:
    python3 tools/doc_guard.py --preflight     # snapshot
    python3 tools/doc_guard.py --postflight    # verify
    python3 tools/doc_guard.py --check FILE    # check if file is protected
"""
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_FILE = ROOT / "knowledge pipeline" / ".tmp" / ".doc_guard_snapshot.json"

# D824: Protected files with minimum line counts
PROTECTED_FILES = {
    "DECISION-LOG.md": {"min_lines": 5000, "policy": "append_only"},
    "MASTER-TASK-REGISTER.md": {"min_lines": 100, "policy": "append_only"},
    "AGENTS.md": {"min_lines": 50, "policy": "append_only"},
    ".env": {"min_lines": 1, "policy": "never_overwrite"},
    "CONSTITUTION.md": {"min_lines": 200, "policy": "versioned"},
}

# Extended config protection
CONFIG_FILES = [
    "config/taxonomy_v5.yaml",
    "config/model_assignments.yaml",
    "config/domain_anchors.yaml",
    "config/domain_disciplines.yaml",
    "config/space_routing.yaml",
    "config/decision_contracts.py",
    "config/intimacy_policy.yaml",
    "config/fb_inventory.yaml",
]
for cf in CONFIG_FILES:
    PROTECTED_FILES[cf] = {"min_lines": 10, "policy": "never_overwrite"}


def is_protected(filepath: str) -> dict | None:
    """Check if a file is protected. Returns policy dict or None."""
    # Normalize path relative to ROOT
    p = Path(filepath)
    try:
        rel = str(p.relative_to(ROOT))
    except ValueError:
        rel = str(p)

    # Check exact match
    if rel in PROTECTED_FILES:
        return PROTECTED_FILES[rel]

    # Check by filename (for config/*.yaml etc.)
    fname = p.name
    if fname in PROTECTED_FILES:
        return PROTECTED_FILES[fname]

    return None


def snapshot() -> dict:
    """Take a snapshot of all protected files. Returns snapshot dict."""
    snap = {
        "timestamp": datetime.now(UTC).isoformat(),
        "files": {}
    }
    for fname, _policy in PROTECTED_FILES.items():
        fpath = ROOT / fname
        if not fpath.exists():
            snap["files"][fname] = {"exists": False}
            continue
        content = fpath.read_text()
        snap["files"][fname] = {
            "exists": True,
            "lines": len(content.split('\n')),
            "size": len(content),
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(snap, indent=2))
    return snap


def preflight() -> dict:
    """Take pre-operation snapshot. Call before any write/edit."""
    return snapshot()


def postflight() -> list[str]:
    """Verify protected files after operation. Returns list of violations."""
    if not SNAPSHOT_FILE.exists():
        return ["ERROR: No preflight snapshot found. Run preflight() first."]

    before = json.loads(SNAPSHOT_FILE.read_text())
    violations = []

    for fname, policy in PROTECTED_FILES.items():
        fpath = ROOT / fname
        before_state = before["files"].get(fname, {})

        if not fpath.exists():
            if before_state.get("exists"):
                violations.append(f"D824: {fname} DELETED (was {before_state.get('lines')} lines)")
            continue

        current = fpath.read_text()
        current_lines = len(current.split('\n'))
        current_sha = hashlib.sha256(current.encode()).hexdigest()
        min_lines = policy["min_lines"]

        # Check minimum lines
        if current_lines < min_lines:
            violations.append(
                f"D824: {fname} TRUNCATED! {current_lines} lines (min: {min_lines}, "
                f"was: {before_state.get('lines', '?')})"
            )
            continue

        # Check overwrite vs append
        if before_state.get("exists") and current_sha != before_state.get("sha256"):
            pol = policy["policy"]
            before_lines = before_state.get("lines", 0)

            if pol == "append_only" and current_lines < before_lines:
                violations.append(
                    f"D824: {fname} OVERWRITTEN! {before_lines}→{current_lines} lines. "
                    f"Policy: {pol}. Restore from vault + append only."
                )
            elif pol == "never_overwrite" and current_sha != before_state.get("sha256"):
                violations.append(
                    f"D824: {fname} MODIFIED! Policy: {pol}. "
                    f"Restore from vault required."
                )

    return violations


def auto_restore(violations: list[str]) -> bool:
    """Auto-restore protected files from vault if violations found."""
    if not violations:
        return True

    print(f"🚨 DOC GUARD: {len(violations)} violations detected!")
    for v in violations:
        print(f"  ❌ {v}")

    # Try restore from vault
    print("🔄 Attempting auto-restore from vault...")
    for v in violations:
        # Extract filename from violation message
        for fname in PROTECTED_FILES:
            if fname in v:
                result = subprocess.run(
                    ["python3", str(ROOT / "tools" / "vault.py"), "--restore", fname],
                    capture_output=True, text=True, cwd=str(ROOT)
                )
                print(f"  {fname}: {result.stdout.strip()}")
                break

    return False


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    if "--preflight" in sys.argv:
        snap = preflight()
        print(f"✅ Preflight snapshot: {len(snap['files'])} files at {snap['timestamp']}")
    elif "--postflight" in sys.argv:
        violations = postflight()
        if violations:
            print(f"❌ {len(violations)} violations:")
            for v in violations:
                print(f"  {v}")
            sys.exit(1)
        else:
            print("✅ All protected files intact.")
    elif "--check" in sys.argv:
        idx = sys.argv.index("--check")
        if idx + 1 < len(sys.argv):
            fname = sys.argv[idx + 1]
            prot = is_protected(fname)
            if prot:
                print(f"🔒 {fname}: PROTECTED (policy: {prot['policy']}, min: {prot['min_lines']} lines)")
            else:
                print(f"✅ {fname}: NOT protected — safe to write")
        else:
            print("Usage: doc_guard.py --check FILENAME")
    elif "--manifest" in sys.argv:
        print("Protected files manifest:")
        for fname, pol in sorted(PROTECTED_FILES.items()):
            print(f"  {fname}: {pol['policy']} (min {pol['min_lines']} lines)")
    else:
        print("Usage: doc_guard.py --preflight | --postflight | --check FILE | --manifest")
