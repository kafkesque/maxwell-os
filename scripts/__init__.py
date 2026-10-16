"""This directory is a PACKAGE, and that is a claim about BYTES rather than a convenience (BUG-875).

WHY THIS FILE EXISTS
    MEASURED 2026-10-16: with no __init__.py here, `scripts` was a NAMESPACE package, and an unrelated
    distribution (skillopt-0.1.0) had installed a top-level REGULAR package also called `scripts`. PEP 420
    consults a namespace portion ONLY when no regular package of that name exists anywhere on sys.path, so
    `from scripts.lib.write_guard import append_lines` inside this repository resolved to
    /Users/barn/miniforge3/lib/python3.13/site-packages/scripts/__init__.py - ANOTHER PROJECT'S BYTES - and
    inserting the repository at sys.path[0] could not change that.
    The consequence was not theoretical: `python3 scripts/delegate_journal.py --selftest`, a rail declared
    FATAL in config/rail_registry.yaml, exited 1 with ModuleNotFoundError: No module named 'scripts.lib' on
    the interpreter an agent session uses, while the SAME declared command exited 0 under another python3.
    ONE COMMAND, TWO VERDICTS - and the thing that could not run is the T-168 journal, the ONE record a
    delegated act leaves behind (D-3036/BUG-844). 16 import sites under scripts/ and tests/ were dead or
    resolving elsewhere for the same reason.

WHAT THIS FILE CHANGES
    Nothing at run time. It is the DECLARATION that makes the name this repository's own: a regular package
    at sys.path[0] wins on every interpreter, so `from scripts.x import y` keeps reading this tree.
    The rule is then ENFORCED, not remembered: scripts/check_repo_integrity.py (RAIL 0) fails closed on any
    first-party top-level name that resolves outside the repository, NAMING the distribution that captured
    it, and config/repo_integrity.yaml#import_resolution declares the rule and the exclusions.

    Deliberately empty of code: an __init__.py carrying side effects would run for every consumer of this
    package, and this file exists to make a name RESOLVE, not to do work (C12 - a declaration, not a
    behaviour). The two root-level modules that ARE importable by name (maxwell_mcp_server, mcp_doc_guard)
    are regular modules and are covered by the same rule.
"""
