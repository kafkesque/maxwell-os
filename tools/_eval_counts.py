#!/usr/bin/env python3
"""Print the item count for every suite (sanity check before a long run)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mes", ROOT / "tools" / "model_eval_suite.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)  # type: ignore[union-attr]

total = 0
for name in mod.SUITES:
    try:
        n = len(mod.SUITES[name]())
    except Exception as exc:
        print(name.ljust(14), "ERR", type(exc).__name__, str(exc)[:80])
        continue
    total += n
    print(name.ljust(14), n)
print("TOTAL per model", total)
