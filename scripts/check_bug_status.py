#!/usr/bin/env python3
"""check_bug_status.py - the bug register must equal its own re-derivation (a register that can drift silently).

WHY: governance/bug_status.json|md are GENERATED from governance/buglog.md by scripts/bug_status.py.
On 2026-09-25 the register sat 13 ids behind the log with no rail noticing - a stale register is worse than
no register, because `just health` was green while "98 open" was false. This re-derives into a temp dir and
byte-compares. Fail closed.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
GEN = REPO / "scripts" / "bug_status.py"


def main() -> int:
    """Re-derive the register into a temp dir and compare with the tracked files."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="governance/bug_status.json")
    ap.add_argument("--md", default="governance/bug_status.md")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        j, m = pathlib.Path(td) / "bug_status.json", pathlib.Path(td) / "bug_status.md"
        r = subprocess.run([sys.executable, str(GEN), "--json-out", str(j), "--md-out", str(m)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL bug_status: the generator itself failed")
            print(r.stdout[-800:], r.stderr[-800:])
            return 1
        drift = []
        for tracked, fresh in ((REPO / a.json, j), (REPO / a.md, m)):
            if not tracked.exists() or tracked.read_bytes() != fresh.read_bytes():
                drift.append(str(tracked.relative_to(REPO)))
        if drift:
            print(f"FAIL bug_status: stale register {drift} - re-run: python3 scripts/bug_status.py")
            return 1
    print("ok bug_status: register equals its re-derivation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
