#!/usr/bin/env python3
"""T-132 / D-3000 - THE HARNESS CONTEXT CONTRACT'S BINDING.

DECLARED IS NOT BOUND. MEASURED 2026-10-15: the contract declared GOOSE_AUTO_COMPACT_THRESHOLD and
GOOSE_AUTO_COMPACT_TOKEN_LIMIT, and the probe still reported them as "from default" - because a
declaration in YAML is not an environment variable. An unset variable silently falls back to the
vendor default, and the vendor default is a CLOUD price-tier artifact, not a local budget (C1/C22).

This module is the ONE place that turns -config/agent_context.yaml#ratified.knobs.trigger- into
environment, and the ONE reading that says whether the RUNNING process is bound. It reads every value
and restates none (C12), which --selftest proves by reading its own bytes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CONFIG = Path("config/agent_context.yaml")
TRIGGER_KEY = "trigger"
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2


def declared_bindings(config: Path = CONFIG) -> dict[str, str]:
    """Read the contract's trigger block; return env var -> declared value.

    Raises rather than defaulting: a contract that cannot be read is FATAL, never silently empty (C16).
    """
    import yaml

    doc: Any = yaml.safe_load(config.read_text())
    trigger = doc["ratified"]["knobs"][TRIGGER_KEY]
    return {str(k): str(v) for k, v in trigger.items() if ENV_NAME.match(str(k))}


def read_state(bindings: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Classify each declared binding against the RUNNING environment.

    BOUND    - the environment holds exactly the declared value.
    UNBOUND  - the variable is absent, so the harness will silently use its own default (D-795:
               absent is not zero, and it is not "declared" either).
    CONFLICT - the environment holds a DIFFERENT value: a drift, not a default.
    """
    state: dict[str, dict[str, Any]] = {}
    for name, want in bindings.items():
        got = os.environ.get(name)
        if got is None:
            state[name] = {"state": "UNBOUND", "declared": want, "effective": None}
        elif str(got).strip() == want:
            state[name] = {"state": "BOUND", "declared": want, "effective": str(got)}
        else:
            state[name] = {"state": "CONFLICT", "declared": want, "effective": str(got)}
    return state


def emit_env(bindings: dict[str, str]) -> str:
    """Render the bindings as shell export lines (the wrapper's source of truth)."""
    return chr(10).join(f"export {k}={v}" for k, v in sorted(bindings.items()))


def _selftest() -> int:
    """Known-answer controls (BUG-492: a control nothing runs is a comment)."""
    checks: list[tuple[str, bool]] = []
    bind = declared_bindings()
    checks.append(("a_declared_trigger_key_binds_to_an_env_name", len(bind) >= 3))
    checks.append(("every_declared_name_is_env_shaped", all(ENV_NAME.match(k) for k in bind)))

    saved = {k: os.environ.get(k) for k in bind}
    try:
        name = sorted(bind)[0]
        os.environ[name] = bind[name]
        checks.append(("an_env_holding_the_declared_value_reads_bound", read_state(bind)[name]["state"] == "BOUND"))
        os.environ.pop(name, None)
        st = read_state(bind)[name]
        checks.append(("an_absent_env_reads_unbound_and_never_zero", st["state"] == "UNBOUND" and st["effective"] is None))
        os.environ[name] = "999999999" if bind[name].isdigit() else "not-the-declared-value"
        checks.append(("an_env_that_contradicts_the_declaration_reads_conflict", read_state(bind)[name]["state"] == "CONFLICT"))
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    own = Path(__file__).read_text()
    restated = [v for v in bind.values() if len(v) >= 2 and re.search(r"(?<![0-9A-Za-z_.])" + re.escape(v) + r"(?![0-9A-Za-z_.])", own)]
    checks.append(("the_module_restates_no_declared_value", not restated))
    checks.append(("the_contract_is_read_from_its_declared_home", CONFIG.name in own and TRIGGER_KEY in own))
    bad = sum(0 if ok else 1 for _, ok in checks)
    for label, ok in checks:
        print(("  PASS " if ok else "  FAIL ") + label)
    print(f"selftest: {len(checks) - bad}/{len(checks)}")
    return RC_OK if bad == 0 else RC_FATAL


def main() -> int:
    """Entry point: --check (the reading), --emit-env (the binding), --selftest, --json."""
    ap = argparse.ArgumentParser(description="T-132 harness context contract: read, bind, verify.")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--emit-env", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    try:
        bind = declared_bindings()
    except Exception as exc:
        print(f"FAIL harness-contract: cannot read {CONFIG}: {exc}")
        return RC_FATAL
    if args.emit_env:
        print(emit_env(bind))
        return RC_OK
    state = read_state(bind)
    if args.json:
        print(json.dumps(state, indent=1))
    else:
        for name, row in sorted(state.items()):
            print(f"  {row['state']:<8} {name} declared={row['declared']} effective={row['effective']}")
    if any(r["state"] == "CONFLICT" for r in state.values()):
        print("FAIL harness-contract: an environment value CONTRADICTS the declaration (a drift, not a default)")
        return RC_FATAL
    if any(r["state"] == "UNBOUND" for r in state.values()):
        print("OWNER-OWED harness-contract: the harness will use its OWN defaults for the names above (C1/C22: those defaults are a cloud price tier, not a local budget)")
        return RC_OWNER_OWED
    return RC_OK


if __name__ == "__main__":
    sys.exit(main())
