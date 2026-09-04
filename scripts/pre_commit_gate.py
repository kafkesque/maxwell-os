#!/usr/bin/env python3
"""scripts/pre_commit_gate.py — C11 + C12 pre-commit gate (D2552/GOV-CI).

Runs the two cheap, DB-free integrity checks that matter for every commit:
  - check_import_dependencies (C11: every import ∈ requirements ∪ stdlib ∪ local)
  - check_hardcoded_paths    (C12: no /Users/ /home/ C:\\Users absolute paths)

Exit 0 = pass, 1 = fail. Wired via .pre-commit-config.yaml local hook.
Reuses pipeline/integrity_check.py (single source of truth — no duplicated logic).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.integrity_check import (  # noqa: E402
    check_hardcoded_paths,
    check_import_dependencies,
)


def main() -> int:
    failures: list[str] = []
    for name, fn in (
        ("C11 import⊂requirements", check_import_dependencies),
        ("C12 no hardcoded paths", check_hardcoded_paths),
    ):
        ok, msg = fn()
        first_line = msg.splitlines()[0] if msg else ""
        print(f"{'✅' if ok else '❌'} {name}: {first_line}")
        if not ok:
            failures.append(f"{name}:\n{msg}")
    if failures:
        print("\n" + "\n\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
