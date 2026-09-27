#!/usr/bin/env python3
"""run_ladder.py - D-2680 / BUG-573: the ladder is run for EVERY fault, not until the FIRST one.

WHY. MEASURED 2026-09-27 (BUG-573): `just health` stood RED at one line for a whole session. Repairing that red
let the recipe CONTINUE, and the rail registry immediately reported a fault it had NEVER reported - a stale
dormancy left behind by an earlier decision. The fix did not create the fault, it UNHID it, and the same prefix
hid every line after it. A recipe that stops at the first failing line reports a PREFIX while it is read as a
VERDICT: every repair round then costs a new session to discover the next fault, and "how much is left?" has no
measured answer - which is exactly what makes a repair programme look like it is running in circles.

WHAT THIS IS. Two modes over ONE subject, the ladder itself:
  --banner RECIPE --full RECIPE   says, in the ladder's OWN units, that a prefix is what `just RECIPE` reports,
                                  and names the entry point that reports the whole set. Printed BEFORE any rail
                                  can abort, because a declaration printed after the abort is read by nobody.
  --collect RECIPE                every declaring line of that recipe is RUN, in order, and EVERY fault is
                                  reported with its own return code and elapsed time. The exit code is the WORST
                                  collected code (1 FATAL outranks 2 owner-owed), never the FIRST one.

THE ONE HOME IS THE LADDER. This script never names a rail or a line: it READS the recipe body from the ladder
file declared in config/rail_registry.yaml#ladder, for a recipe that same declaration names in #recipes. Adding a
line to the ladder is therefore collected without editing anything here (C12: no path, pattern or count in code).
A recipe the declaration does not govern is REFUSED, fail closed (C16), and so is a ladder that is absent, empty
or unreadable - a report about a ladder nobody declared is a verdict about nothing (D-405).

FIDELITY. Each line is executed AS WRITTEN, through a POSIX shell, from the repository root, so the line's OWN
guard decides what counts as a fault: `cmd || exit 1` yields 1, `cmd || [ $? -eq 2 ]` yields 0 for an owner-owed
rail. A line that invokes THIS script is SKIPPED and reported: a ladder that collects itself would recurse, and
that is the only line whose behaviour is not the ladder's own.

TRI-STATE (BUG-457): 0 every line green | 1 FATAL (a hard gate red) | 2 owner-owed only (loud, NOT fatal).
--selftest: known-answer controls over SYNTHETIC ladders, executing only lines this file writes itself - no
filesystem fixture at all, so this rail adds no second home of the "a fixture resolves OUTSIDE the tree it
audits" rule (BUG-577) and no writer to declare (config/rail_registry.yaml#writers).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import pathlib
import re
import subprocess
import sys
import time

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CFG = REPO / "config/rail_registry.yaml"
SELF = pathlib.Path(__file__).name
RECIPE = re.compile(r"^([A-Za-z0-9_-]+):")
EXIT_CLEAN, EXIT_FATAL, EXIT_OWED = 0, 1, 2
Fault = tuple[str, int, float]


def declared() -> tuple[str, list[str]]:
    """The ladder file and the recipes the registry governs - READ from their one home, never restated here."""
    if not CFG.is_file():
        raise SystemExit("FAIL-CLOSED (C16): config/rail_registry.yaml is absent - the ladder this script "
                         "collects has no declared home, and a ladder nobody declares is a ladder nobody can "
                         "verify (D-2680)")
    doc = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    ladder, recipes = doc.get("ladder"), doc.get("recipes")
    if not ladder or not recipes:
        raise SystemExit("FAIL-CLOSED (C16): config/rail_registry.yaml must declare 'ladder' and 'recipes' - a "
                         "collector with no declared subject would report a verdict about nothing (D-2680)")
    return str(ladder), [str(r) for r in recipes]


def parse(text: str, recipe: str) -> list[str]:
    """The declaring lines of ONE recipe in a ladder's TEXT, in order, with only the call syntax removed.

    PURE on purpose: the known-answer controls drive it on synthetic ladders, so the rule that decides WHICH
    lines are collected is testable without running the live ladder (and without writing a fixture).
    """
    out: list[str] = []
    name = None
    for raw in text.splitlines():
        m = RECIPE.match(raw)
        if m and not raw.startswith((" ", "\t")):
            name = m.group(1)
            continue
        if name != recipe or not raw.strip() or raw.strip().startswith("#"):
            continue
        line = raw.strip().lstrip("@")
        if SELF in line:
            continue  # a self-invocation (the banner): collecting it would recurse
        out.append(line)
    return out


def body(recipe: str) -> list[str]:
    """The declaring lines of one recipe of the DECLARED ladder, refused unless that declaration governs it."""
    ladder, recipes = declared()
    if recipe not in recipes:
        raise SystemExit("FAIL-CLOSED (C16): " + repr(recipe) + " is not one of the recipes that config/"
                         "rail_registry.yaml#recipes governs (" + ", ".join(recipes) + ") - a ladder no "
                         "declaration governs is a report about nothing (D-2680)")
    path = REPO / ladder
    if not path.is_file():
        raise SystemExit("FAIL-CLOSED (C16): the declared ladder " + ladder + " does not exist on disk - the "
                         "collector would otherwise report an empty ladder as a clean one (D-405)")
    lines = parse(path.read_text(encoding="utf-8"), recipe)
    if not lines:
        raise SystemExit("FAIL-CLOSED (C16): recipe " + recipe + " in the declared ladder " + ladder + " has no "
                         "declaring line - an empty scan is not a clean scan (D-405/D-2680)")
    return lines


def run_lines(lines: list[str], quiet: bool = False) -> tuple[int, list[Fault]]:
    """RUN every line as written; return (worst tri-state code, every fault with its own rc and seconds).

    The line's own text carries its guard, so the collector never decides what a rail MEANT - it reports what the
    ladder DID. Never short-circuits: a fault is recorded and the scan continues, which is the whole rule.
    """
    worst, faults = EXIT_CLEAN, []
    for line in lines:
        t0 = time.monotonic()
        p = subprocess.run(line, shell=True, cwd=str(REPO), capture_output=True, text=True)
        dt = time.monotonic() - t0
        if not quiet:
            sys.stdout.write(p.stdout)
            sys.stderr.write(p.stderr)
        rc = p.returncode
        if rc:
            faults.append((line, rc, dt))
            if rc == EXIT_OWED and worst == EXIT_CLEAN:
                worst = EXIT_OWED
            elif rc != EXIT_OWED:
                worst = EXIT_FATAL
            if not quiet:
                print("  FAULT rc=" + str(rc) + " after " + f"{dt:.1f}" + "s: " + line, flush=True)
        elif not quiet:
            print("  ok   " + f"{dt:6.1f}" + "s " + line, flush=True)
    return worst, faults


def banner(recipe: str, full: str) -> int:
    """Declare the ladder's own shape, in the ladder's own units, before any rail can abort the recipe."""
    lines = body(recipe)
    hard = [ln for ln in lines if "exit 1" in ln]
    print("ladder scan: `just " + recipe + "` reports a PREFIX - it stops at the FIRST non-zero line, and "
          + str(len(lines)) + " declaring line(s) stand in it (" + str(len(hard)) + " declared a HARD gate), so a "
          "red line HIDES every line after it (BUG-573).")
    print("ladder scan: for EVERY fault of this ladder in ONE run use `just " + full + "` (D-2680).")
    return EXIT_CLEAN


def scan(recipe: str) -> int:
    """Collect every fault of one declared recipe and exit with the WORST code, never the first."""
    lines = body(recipe)
    print("=== ladder scan (" + recipe + ", " + str(len(lines)) + " declaring line(s)): every line runs, "
          "nothing is hidden (D-2680) ===", flush=True)
    t0 = time.monotonic()
    worst, faults = run_lines(lines)
    elapsed = time.monotonic() - t0
    if not faults:
        print("ok ladder scan: " + str(len(lines)) + " line(s) RUN, 0 fault(s), " + f"{elapsed:.1f}" + "s")
        return EXIT_CLEAN
    print("FAIL ladder scan: " + str(len(faults)) + " fault(s) in ONE pass (a prefix report would have shown only "
          "the FIRST):")
    for line, rc, dt in faults:
        print("  rc=" + str(rc) + " " + f"{dt:6.1f}" + "s " + line)
    print("FAIL ladder scan: worst rc=" + str(worst) + " over " + str(len(lines)) + " line(s) in "
          + f"{elapsed:.1f}" + "s")
    return worst


# ------------------------------------------------------------------ controls
def selftest() -> int:
    """Known-answer controls over SYNTHETIC ladders: the collector's own rule must be SEEN to fire (BUG-492)."""
    ok = fail = 0

    def check(name: str, got: bool, why: str) -> None:
        nonlocal ok, fail
        if got:
            ok += 1
            print("  ok   selftest/" + name + ": " + why)
        else:
            fail += 1
            print("  FAIL selftest/" + name + ": " + why)

    def ladder(body_lines: list[str], neighbour: bool = False) -> str:
        text = "probe:\n" + "".join("    " + ln + "\n" for ln in body_lines)
        if neighbour:
            text += "other:\n    echo NOT_MY_LINE\n"
        return text

    one = ladder(["echo MARK_ONE", "sh -c 'exit 1'", "echo MARK_LATE", "sh -c 'exit 2'"])
    got = parse(one, "probe")
    check("one_recipe_is_not_the_whole_file", got == ["echo MARK_ONE", "sh -c 'exit 1'", "echo MARK_LATE",
                                                      "sh -c 'exit 2'"],
          "a ladder is a SET of recipes: only the collected recipe's declaring lines are read, in order")
    code, faults = run_lines(got, quiet=True)
    check("late_fault_is_visible", len(faults) == 2 and code == EXIT_FATAL,
          "a RED line does NOT hide the fault after it: 2 fault(s) collected in one pass, worst rc=1 (BUG-573)")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_lines(got)
    shown = buf.getvalue()
    check("a_late_line_still_RAN", "MARK_ONE" in shown and "MARK_LATE" in shown,
          "the line AFTER the fault was still executed and its own output is in the report: the scan is not a "
          "prefix - a collector that stopped at the first red would lose MARK_LATE")
    code2, faults2 = run_lines(["sh -c 'exit 2'"], quiet=True)
    check("owner_owed_only_is_not_fatal", code2 == EXIT_OWED and len(faults2) == 1,
          "the tri-state survives collection: 2 owner-owed outranks nothing and is NOT escalated to 1 (BUG-457)")
    code3, faults3 = run_lines(["sh -c 'exit 2' || [ $? -eq 2 ]", "echo TOLERATED"], quiet=True)
    check("the_line_own_guard_decides", code3 == EXIT_CLEAN and not faults3,
          "a line whose OWN text tolerates owner-owed is not a fault: the ladder's text is the ruler, not intent")
    code4, faults4 = run_lines(["echo BEFORE", "true", "echo AFTER"], quiet=True)
    check("negative_control_a_green_ladder_is_clean", code4 == EXIT_CLEAN and not faults4,
          "a ladder with no fault reports 0 fault(s) - a collector that always faults is a collector nobody reads")
    code5, faults5 = run_lines(["echo BEFORE", "sh -c 'exit 9'", "echo AFTER"], quiet=True)
    check("an_unknown_code_is_FATAL_not_owner_owed", code5 == EXIT_FATAL and len(faults5) == 1,
          "a code that is neither 0 nor 2 is not silently read as owner-owed: it is FATAL (C16)")
    neigh = parse(ladder(["echo MINE"], neighbour=True), "probe")
    check("a_neighbour_recipe_is_not_collected", neigh == ["echo MINE"],
          "the scan starts and ends at the collected recipe: another recipe's lines are not run")
    selfline = parse(ladder(["echo KEEP", "python3 scripts/" + SELF + " --banner probe"]), "probe")
    check("self_invocation_is_skipped", selfline == ["echo KEEP"],
          "a line that invokes the collector itself is dropped (a ladder that collects itself would recurse)")
    try:
        body("__no_such_recipe__")
        refused = False
    except SystemExit as e:
        refused = "rail_registry.yaml#recipes" in str(e)
    check("undeclared_recipe_is_refused", refused,
          "fail closed (C16): a recipe the ladder's OWN declaration does not govern is refused, not collected")
    try:
        body("__no_such_recipe__")
        named = False
    except SystemExit as e:
        named = "declared ladder" in str(e) or "rail_registry.yaml" in str(e)
    check("the_refusal_names_the_declaration", named, "the refusal names the home that decides, never a bare exit")
    ladder_path, recipes = declared()
    live = REPO / ladder_path
    both = live.is_file() and all(parse(live.read_text(encoding="utf-8"), r) for r in recipes)
    check("every_declared_recipe_has_declaring_lines", both,
          "D-405 both directions: each recipe config/rail_registry.yaml#recipes names yields >= 1 line ("
          + ", ".join(recipes) + ")")
    print("ladder controls: " + str(ok) + "/" + str(ok + fail) + " known-answer control(s) fire")
    return EXIT_FATAL if fail else EXIT_CLEAN


def main(argv: list[str]) -> int:
    """Dispatch the three modes; every refusal inside them is a VERDICT (a SystemExit message), not a traceback."""
    ap = argparse.ArgumentParser(description="D-2680: run the declared ladder for EVERY fault, not the first.")
    ap.add_argument("--banner", metavar="RECIPE", help="declare the prefix property of this recipe")
    ap.add_argument("--full", metavar="RECIPE", help="the recipe that reports the whole fault set (named here)")
    ap.add_argument("--collect", metavar="RECIPE", help="run every line of this recipe, reporting every fault")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.banner:
        return banner(a.banner, a.full)
    if a.collect:
        return scan(a.collect)
    ap.error("one of --banner, --collect or --selftest is required")
    return EXIT_FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
