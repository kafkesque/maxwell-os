#!/usr/bin/env python3
"""The certified lint gate (BUG-1015).

`just audit` used to run ``ruff | tail -5`` under ``@``, so the recipe's exit
status was always *tail's* 0 and real findings accumulated unseen (a control
that cannot be seen to FAIL is not a control, BUG-492; a declaration that never
resolves to a reading is not a guard, D-3034). This gate narrows to the
CORRECTNESS family (F = pyflakes: undefined name, unused import/local,
f-string defect, redefinition) because that is the family whose GROWTH means a
real defect, counts findings against a shrink-only ceiling declared in
config/pipeline_config.yaml, and FAILS when the count GROWS. The
modernisation/style families (UP/I/W/E/B) are reported by --report but never
fail the build until a named decision promotes them (D-3038: what we reject we
register, so the debt is named and counted, not silently re-accumulated).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
CFG_HOME = REPO / "config" / "pipeline_config.yaml"


def _load_cfg() -> dict[str, Any]:
    with CFG_HOME.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def lint_block() -> dict[str, Any]:
    """Return the declared lint_gate block, failing closed when absent (C12)."""
    block = _load_cfg().get("lint_gate")
    if not isinstance(block, dict):
        raise SystemExit("!! lint_gate block missing from config/pipeline_config.yaml - fail-closed (C12)")
    return block


def _required(block: dict[str, Any], key: str) -> Any:
    """Read a required key, failing closed when absent — a silent code default is a
    second home for a value that must have exactly one (C12/D-2644)."""
    if key not in block:
        raise SystemExit(f"!! lint_gate.{key} missing from config/pipeline_config.yaml - fail-closed (C12)")
    return block[key]


def verdict(count: int, ceiling: int, direction: str) -> tuple[bool, str]:
    """Return (pass, message) for a shrink-only ceiling.

    A count ABOVE the ceiling FAILS; equal or below passes. ``direction`` must
    be exactly ``shrink_only`` (fail-closed otherwise): a ceiling that may only
    move DOWN is the anti-drift guarantee (D-2644), so a loosened direction is a
    fault, never a shrug.
    """
    if direction != "shrink_only":
        return False, f"direction {direction!r} is not shrink_only - the gate may not be loosened without a decision (D-2644)"
    if count <= ceiling:
        return True, f"certified lint {count} <= ceiling {ceiling} ({ceiling - count} headroom)"
    return False, f"certified lint {count} EXCEEDS ceiling {ceiling} by {count - ceiling}"


def ruff_count(select: str | None, scope: list[str]) -> tuple[int, str]:
    """Run ruff on the declared scope and return (count, error). A count of -1
    with a non-empty error means the run itself was unreadable (fail-closed).
    ``select`` is None to honour the pyproject select+ignore (used by --report),
    otherwise a CLI ``--select`` narrows the rule family (used by --check)."""
    cmd = [sys.executable, "-m", "ruff", "check"]
    if select is not None:
        cmd += ["--select", select]
    cmd += ["--output-format", "json", *scope]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    try:
        findings = json.loads(proc.stdout)
        if isinstance(findings, list):
            return len(findings), ""
    except json.JSONDecodeError:
        pass
    # ruff emits a human "Found N errors." summary on the non-JSON path; fall back to it.
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        if line.startswith("Found ") and " error" in line:
            try:
                return int(line.split()[1]), ""
            except (IndexError, ValueError):
                break
    tail = (proc.stderr or proc.stdout or "").strip()[:200]
    return -1, f"ruff output unparsable (rc={proc.returncode}): {tail}"


def _reported(total: int) -> None:
    """Print the non-failing style-debt total so it is never invisible again."""
    print(f"lint_gate --report: {total} total ruff finding(s) across E/F/I/W/UP/B (style debt OUTSIDE the certified gate)")


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--selftest":
        return selftest()
    if argv and argv[0] == "--report":
        # None => honour pyproject's own select+ignore (E501/B008 stay ignored), the
        # config-select total. Passing --select here would drop `ignore` and inflate
        # the number with ~16k line-length findings (measured 2026-10-26).
        count, err = ruff_count(None, list(_required(lint_block(), "scope")))
        if err:
            print(err)
            return 1
        _reported(count)
        return 0
    block = lint_block()
    select = ",".join(_required(block, "certified_select"))
    ceiling = int(_required(block, "ceiling"))
    direction = str(_required(block, "direction"))
    scope = list(_required(block, "scope"))
    count, err = ruff_count(select, scope)
    if err:
        print(err)
        return 1
    ok, msg = verdict(count, ceiling, direction)
    print(f"lint_gate: {msg} (select={select} scope={','.join(scope)})")
    return 0 if ok else 1


def selftest() -> int:
    """Known-answer controls: the gate must be SEEN to fail on growth, pass at
    the ceiling, pass when shrunk, and refuse a loosened direction (BUG-492)."""
    cases: list[tuple[str, int, int, str, bool]] = [
        ("a finding ABOVE the ceiling FAILS", 253, 252, "shrink_only", False),
        ("a count AT the ceiling passes", 252, 252, "shrink_only", True),
        ("a count BELOW the ceiling passes (shrink)", 100, 252, "shrink_only", True),
        ("zero at zero passes", 0, 0, "shrink_only", True),
        ("a loosened direction FAILS closed", 0, 0, "grow_only", False),
    ]
    for name, count, ceiling, direction, want in cases:
        got, _msg = verdict(count, ceiling, direction)
        if got != want:
            print(f"FAIL selftest {name}: verdict({count},{ceiling},{direction!r}) = {got}, want {want}")
            return 1
    print(f"ok lint_gate --selftest: {len(cases)} known answers "
          f"(a ceiling that cannot be SEEN to fail is a comment, BUG-492)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
