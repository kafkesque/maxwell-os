#!/usr/bin/env python3
"""T-132's binding: run a command with the harness context contract actually IN the environment.

D-3000 ratified a context contract (T-132). pipeline/harness_contract.py MEASURES that contract
against the running environment and returned rc 2: all three GOOSE_* names UNBOUND, so the
harness was free to fall back to its own cloud price-tier defaults. A declaration that is not in
the environment is not a contract - it is a comment.

This module is the missing half, and the owner approved it (T-132, 2026-10-15). It reads the
declared names from their one home (config/agent_context.yaml#ratified.knobs.trigger), sets them
for the CHILD process only, and execs. It never restates a declared value (C12): every value it
exports is read at run time.

Usage:
  python3 pipeline/harness_env.py --print                  # the export lines, for a shell profile
  python3 pipeline/harness_env.py --check                  # BOUND / UNBOUND / CONFLICT in this shell
  python3 pipeline/harness_env.py --exec -- <cmd> [args]   # exec cmd with the contract bound
  python3 pipeline/harness_env.py --selftest               # controls; exit 1 on any failure

Exit codes (BUG-457 tri-state): 0 = ok / every name bound; 2 = OWNER-OWED, names unbound so the
harness may ignore the contract; 1 = fatal, because an environment value CONTRADICTS the
declaration - that is drift and hiding it would be worse than failing.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

import yaml

CONFIG = pathlib.Path("config/agent_context.yaml")
TRIGGER = "trigger"
ENV_SHAPED = re.compile(r"^[A-Z][A-Z0-9_]*$")
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2


def declared() -> dict[str, str]:
    """The declared trigger names and their values, read from their one home, in declaration order."""
    doc = yaml.safe_load(CONFIG.read_text())
    trigger = doc["ratified"]["knobs"][TRIGGER]
    return {str(key): resolve(str(val)) for key, val in trigger.items() if ENV_SHAPED.match(str(key))}


def resolve(value: str) -> str:
    """Resolve a "@path#dotted.key" pointer to the value in its one home.

    Why pointers: the contract now binds WHICH provider and WHICH model a harness runs on, and a
    model name written into this file would be a second copy of a fact that config/engine.yaml and
    config/model_assignments.yaml already own (C12). An unresolvable pointer is FATAL - it must never
    degrade into a literal string, or a harness would silently run on a model nobody declared (C16).
    """
    if not value.startswith("@"):
        return value
    ref, _, dotted = value[1:].partition("#")
    path = pathlib.Path(ref)
    if not path.is_absolute():
        path = CONFIG.resolve().parent.parent / path
    try:
        node: object = yaml.safe_load(path.read_text())
        for part in dotted.split("."):
            node = node[int(part)] if isinstance(node, list) else node[part]  # type: ignore[index]
    except Exception as exc:
        raise SystemExit(f"FATAL: the pointer {value} does not resolve ({type(exc).__name__}: {exc})")
    return str(node)


def state(bindings: dict[str, str]) -> list[tuple[str, str, str]]:
    """Classify each declared name against the CURRENT environment: BOUND, UNBOUND or CONFLICT."""
    rows: list[tuple[str, str, str]] = []
    for name, want in bindings.items():
        have = os.environ.get(name)
        if have == want:
            rows.append((name, want, "BOUND"))
        elif have is None:
            rows.append((name, want, "UNBOUND"))
        else:
            rows.append((name, want, "CONFLICT"))
    return rows


def print_lines(bindings: dict[str, str]) -> int:
    """Emit shell export lines - values read from config, never restated in this file (C12)."""
    for name, want in bindings.items():
        print('export %s="%s"' % (name, want))
    return RC_OK


def check() -> int:
    """Report the contract against this environment and return the tri-state reading."""
    worst = RC_OK
    for name, _want, verdict in state(declared()):
        print("%-9s %s" % (verdict, name))
        if verdict == "CONFLICT":
            worst = RC_FATAL
        elif verdict == "UNBOUND" and worst == RC_OK:
            worst = RC_OWNER_OWED
    if worst == RC_OWNER_OWED:
        print("OWNER-OWED: an unbound name is not a default - the harness will use its own, and the")
        print("           contract is DECLARED, not BOUND. Bind it for this shell with:")
        print('           eval "$(python3 pipeline/harness_env.py --print)"')
    return worst


def do_exec(argv: list[str]) -> int:
    """Set the declared names for the child process only, then replace this process with it."""
    if not argv:
        print("FATAL: --exec needs a command after --")
        return RC_FATAL
    for name, _want, verdict in state(declared()):
        if verdict == "CONFLICT":
            print("FATAL: %s contradicts the declaration; refusing to hide drift" % name)
            return RC_FATAL
    env = dict(os.environ)
    env.update(declared())
    os.execvpe(argv[0], argv, env)
    return RC_OK


def selftest() -> int:
    """Controls: the binding must be readable, faithful, and must not restate a declared value."""
    checks: list[tuple[str, bool]] = []
    bindings = declared()
    own = pathlib.Path(__file__).read_text()
    checks.append(("the_one_home_declares_at_least_one_env_shaped_name", len(bindings) >= 1))
    checks.append(("every_declared_name_is_env_shaped", all(ENV_SHAPED.match(name) for name in bindings)))
    probe = next(iter(bindings))
    os.environ[probe] = bindings[probe]
    checks.append(("an_env_holding_the_declared_value_reads_bound",
                   dict((n, v) for n, _, v in state(bindings))[probe] == "BOUND"))
    os.environ[probe] = "SELFTEST-CONTRADICTION"
    checks.append(("an_env_contradicting_the_declaration_reads_conflict",
                   dict((n, v) for n, _, v in state(bindings))[probe] == "CONFLICT"))
    del os.environ[probe]
    checks.append(("an_absent_env_reads_unbound_never_bound",
                   dict((n, v) for n, _, v in state(bindings))[probe] == "UNBOUND"))
    checks.append(("the_module_restates_no_declared_value_C12",
                   not [val for val in bindings.values() if val and val in own]))
    checks.append(("the_contract_is_read_from_its_declared_home",
                   CONFIG.as_posix() in own and TRIGGER in own))
    try:
        resolved = resolve("@config/engine.yaml#harnesses.goose_provider_id")
        checks.append(("a_pointer_resolves_the_value_from_its_one_home", bool(resolved)))
    except SystemExit:
        checks.append(("a_pointer_resolves_the_value_from_its_one_home", False))
    try:
        resolve("@config/engine.yaml#no.such.chain")
        checks.append(("an_unresolvable_pointer_is_FATAL", False))
    except SystemExit:
        checks.append(("an_unresolvable_pointer_is_FATAL", True))

    for name, ok in checks:
        print("%-4s %s" % ("ok" if ok else "FAIL", name))
    print("selftest: %d/%d" % (sum(1 for _, ok in checks if ok), len(checks)))
    return RC_OK if all(ok for _, ok in checks) else RC_FATAL


def main(argv: list[str]) -> int:
    """Dispatch the four readings; an unknown flag is fatal rather than silently ignored (C16)."""
    if "--selftest" in argv:
        return selftest()
    if "--print" in argv:
        return print_lines(declared())
    if "--check" in argv:
        return check()
    if "--exec" in argv:
        rest = argv[argv.index("--exec") + 1:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        return do_exec(rest)
    print(__doc__)
    return RC_FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
