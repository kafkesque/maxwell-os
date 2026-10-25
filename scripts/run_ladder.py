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
audits" rule (BUG-577); the RECEIPT it writes is declared, gitignored runtime state (see below).

THE RECEIPT (D-2983, BUG-759). A prefix report is a verdict about the lines it RAN and says nothing about the
lines it never reached. MEASURED 2026-10-13, that cost a whole-session blindness: the full ladder stood RED on
SEVEN lines and nobody knew, because a session that mints a decision cannot get past the commit-frontier rail
and a session that never runs the whole set never sees the rest. So the whole set is now a MEASUREMENT that
outlives the run. --collect records {coverage fingerprint, line count, worst rc, every fault, cost, the OPENING
state, HEAD at START and at END, and the worktree's tracked readings at both ends} to the path declared in
config/rail_registry.yaml#ladder_receipt (C12: no path in code), and both readers of that record derive the
whole-set entry point from the ladder's own bytes:
  --banner         prints the recorded verdict FIRST, before any rail can abort the recipe (a declaration
                   printed after the abort is read by nobody) and NEVER aborts on it itself;
  --receipt-check  exits with the same tri-state: 0 the whole ladder was MEASURED GREEN under exactly this
                   coverage | 1 a red is RECORDED under exactly this coverage (a measured fault may not go
                   quiet, C16) | 2 UNKNOWN - never measured here, measured against a DIFFERENT ladder, or older
                   than the declared budget (owner-owed and loud, never fatal: only a full scan clears it). It
                   stands LAST in the recipe, because a whole-set report placed early would hide the very lines
                   it speaks for.
The record is held OUT of version control (gitignored, declared in the registry): it is THIS clone's
observation, so committing it would dress a machine-local measurement as durable evidence.

WHICH BYTES (BUG-1010; D-3152 clause 2 - a receipt NAMES the subject it measured). The record's claim is not
"the ladder is green" in the abstract: it is "the ladder was green over THIS SET OF BYTES", and a commit names
that set only while the worktree EQUALS it. Two readings were missing and both were MEASURED to be missing:
HEAD was read when the record was WRITTEN, i.e. after every rail (so a commit landed mid-scan was recorded as
though its bytes had run, and `--receipt-check` returned rc=0 CLEAN naming a commit the tree had already left),
and nothing recorded whether the tree was clean (so a scan of a MODIFIED tree named a commit whose bytes it never
ran, and a clean run and a dirty run produced BYTE-IDENTICAL records). The record now carries `state`,
`started_at`, `head_at_start`, `head_at_end` and
`worktree:{modified_at_start, modified_at_end, untracked_at_start, minted_during_scan}`, and a record that cannot
be ATTRIBUTED to its bytes is OWNER-OWED (rc=2) naming why - never green and never fatal, because only a clean
tree measured again can clear it. `state: "running"` is written BEFORE the first rail, so a scan that is KILLED
leaves a record that says so instead of leaving a tree indistinguishable from one never scanned (MEASURED
2026-10-25: a detached whole-set scan ran 6+ minutes, reached rail ~180 of 194 and vanished - no traceback, no
crash report, receipt untouched).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CFG = REPO / "config/rail_registry.yaml"
SELF = pathlib.Path(__file__).name
RECIPE = re.compile(r"^([A-Za-z0-9_-]+):")
# BUG-1008 (MEASURED 2026-10-25): ONE line may carry `{{just_executable()}}` - a function the LADDER expands
# BEFORE any shell exists. `--collect` hands every line to /bin/sh RAW, so that line was a SYNTAX ERROR
# ("near unexpected token `}}'", rc=2) and the whole-set receipt recorded it as a FAULT - which turned
# `just health` from OWNER-OWED (2) to FATAL (1) the moment the ladder was first measured end to end.
TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
EXIT_CLEAN, EXIT_FATAL, EXIT_OWED = 0, 1, 2
Fault = tuple[str, int, float]
RECEIPT_SCHEMA = "2"
# git's OWN override variables: they are INHERITED by every child process, and this file now reads the worktree to
# decide WHICH BYTES a verdict is about. MEASURED on this clone 2026-10-25: with an inherited EMPTY GIT_INDEX_FILE,
# `git status --porcelain -uall` answered 3973 lines (every tracked path as deleted) against 0 on the real index -
# so an unscrubbed reading would mark EVERY scan un-attributable and turn a green ladder permanently owner-owed
# from a variable nobody in this file set (BUG-527/BUG-568's class, one level up).
GIT_OVERRIDES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
# How many dirty paths a MESSAGE names before it reports the remainder as a count: the record carries them ALL.
PATHS_NAMED = 3


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


def shell_split(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split a recipe's lines by WHO CAN RUN THEM: (a shell can run it, only the LADDER can).

    MEASURED 2026-10-25 (BUG-1008). The collector hands a declaring line to /bin/sh as WRITTEN, while `just`
    interpolates `{{...}}` first, so ONE declared line has TWO execution semantics. `{{just_executable()}}`
    reached the shell literally and died on "syntax error near unexpected token `}}'" (rc=2), and the first
    end-to-end `--collect` recorded that as a fault of the LADDER - a false verdict about the tree produced by a
    fact about the COLLECTOR (BUG-375/BUG-1001 class, one instrument over).

    The census is therefore the set of lines a SHELL can run: a line only the ladder interpreter can run is
    EXCLUDED from it and COUNTED. A narrowed census that is REPORTED is neither a blind spot nor a fault - and
    the property such a line tests is entailed anyway, because a justfile that does not parse cannot start a
    recipe at all. Re-implementing just's expansion here would be a SECOND home for just's semantics (D-2642),
    so the exclusion is the answer and the count is its receipt.
    """
    return ([ln for ln in lines if not TEMPLATE.search(ln)], [ln for ln in lines if TEMPLATE.search(ln)])


def parse_report(text: str, recipe: str) -> tuple[list[str], list[str]]:
    """The declaring lines of ONE recipe, SPLIT BY WHO CAN RUN THEM - the ONE home of that split.

    PURE, and read by BOTH the census the scan RUNS (`parse`) and the count the scan REPORTS (`uncollectable`),
    so the reported narrowing cannot drift from the executed set (D-2642). The self-exclusion (a ladder that
    collects itself would recurse) is applied FIRST, so a template line that invokes the collector stays dropped
    for the older reason rather than being counted twice.
    """
    return shell_split([line for name, lines in recipes_of(text) for line in lines
                        if name == recipe and SELF not in line])


def parse(text: str, recipe: str) -> list[str]:
    """The SHELL-RUNNABLE declaring lines of ONE recipe, in order, with only the call syntax removed.

    PURE on purpose: the known-answer controls drive it on synthetic ladders, so the rule that decides WHICH
    lines are collected is testable without running the live ladder (and without writing a fixture).
    """
    return parse_report(text, recipe)[0]


def uncollectable(recipe: str) -> list[str]:
    """The lines of a DECLARED recipe that only the LADDER can run - consulted only to REPORT the narrowing.

    Steps through `body`'s rejection first, so a recipe no declaration governs is refused here with the same
    named refusal instead of quietly reporting zero exclusions (an empty answer is not a clean answer, D-405).
    """
    body(recipe)
    return parse_report((REPO / declared()[0]).read_text(encoding="utf-8"), recipe)[1]


def recipes_of(text: str) -> list[tuple[str, list[str]]]:
    """Every recipe of a ladder's TEXT with its declaring lines, in order - the ONE rule for reading a line.

    PURE, and the single home of "which lines does a recipe own": `parse` (ONE recipe, self-calls DROPPED,
    because a ladder that collects itself would recurse) and the whole-set entry point (EVERY recipe, self-calls
    KEPT, because that invocation IS the subject) read the same bytes the same way instead of each carrying its
    own copy of the rule (D-2642).
    """
    out: list[tuple[str, list[str]]] = []
    for raw in text.splitlines():
        m = RECIPE.match(raw)
        if m and not raw.startswith((" ", "\t")):
            out.append((m.group(1), []))
            continue
        if not out or not raw.strip() or raw.strip().startswith("#"):
            continue
        out[-1][1].append(raw.strip().lstrip("@"))
    return out


def duplicate_declaring_lines(lines: list[str]) -> list[tuple[str, int]]:
    """Every declaring line that stands MORE THAN ONCE, with its count - one line, one home, EXACTLY ONCE.

    BUG-584: this census IS the ladder's own size, and every line in it is EXECUTED, so a duplicated line is two
    defects at once - the census over-reports the ladder AND the work is done twice. The registry's own census
    (config/rail_registry.yaml) keys by INVOCATION + FLAGS, so a duplicate collapses into ONE key BY CONSTRUCTION
    and cannot be counted twice THERE; the counted unit is decided HERE, so the refusal lives HERE.
    PURE on purpose: a known-answer control drives it on a synthetic ladder (BUG-582 is the zero case, this is
    the twice case).
    """
    seen: dict[str, int] = {}
    for line in lines:
        seen[line] = seen.get(line, 0) + 1
    return [(line, n) for line, n in seen.items() if n > 1]


def duplicated_refusal(recipe: str, ladder: str, dups: list[tuple[str, int]]) -> str:
    """The refusal a duplicated declaring line earns: it NAMES the ladder, the count and the line itself."""
    return ("FAIL-CLOSED (C16): recipe " + recipe + " in the declared ladder " + ladder + " declares "
            + str(len(dups)) + " line(s) MORE THAN ONCE ("
            + "; ".join("x" + str(n) + " " + line for line, n in dups)
            + ") - one line, one home, EXACTLY ONCE: a duplicated declaring line inflates this collector's own "
            "census AND is executed twice (BUG-584; BUG-582 is the zero case, this is the twice case)")


def body(recipe: str) -> list[str]:
    """The declaring lines of one recipe of the DECLARED ladder, refused unless that declaration
    governs it AND unless every line in it stands exactly ONCE (BUG-584).
    """
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
    dups = duplicate_declaring_lines(lines)
    if dups:
        raise SystemExit(duplicated_refusal(recipe, ladder, dups))
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


# --------------------------------------------------------------------- receipt (D-2983)
def receipt_declaration() -> dict:
    """The receipt's ONE declared home: path, recipe and age budget, read from config/rail_registry.yaml.

    NO KEY IS DEFAULTED IN CODE (D-2644/C12): a home or a budget invented here would be a setting living in
    THIS file instead of in the declaration, so a missing key is REFUSED, never filled in (C16).
    """
    doc = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    block = doc.get("ladder_receipt")
    if not isinstance(block, dict):
        raise SystemExit("FAIL-CLOSED (C16): config/rail_registry.yaml declares no ladder_receipt block - a "
                         "recorded verdict with no declared home is a file nobody accounts for (D-2983/D-405)")
    missing = [key for key in ("path", "recipe", "max_age_hours") if block.get(key) in (None, "")]
    if missing:
        raise SystemExit("FAIL-CLOSED (C16): config/rail_registry.yaml#ladder_receipt declares no "
                         + ", ".join(missing) + " - where the receipt lives, which recipe it is a verdict "
                         "about and how long it stays evidence are DECLARED values, never code defaults "
                         "(D-2644/D-2983)")
    return block


def receipt_path() -> pathlib.Path:
    """Where THIS clone records its last full scan: the declared path, resolved against the repository."""
    return REPO / str(receipt_declaration()["path"])


def ladder_text() -> str:
    """The declared ladder's BYTES - the ruler a whole-set verdict is a verdict about (D-404)."""
    ladder, _recipes = declared()
    path = REPO / ladder
    if not path.is_file():
        raise SystemExit("FAIL-CLOSED (C16): the declared ladder " + ladder + " does not exist on disk - a "
                         "receipt about a ladder nobody can read is a claim about nothing (D-405/D-2680)")
    return path.read_text(encoding="utf-8")


def whole_set_entry(recipe: str, text: str) -> str:
    """The ladder's OWN entry point that collects a recipe in ONE run - DERIVED from the bytes, never restated.

    D-2680 gave the ladder a whole-set mode; nothing then required the ladder to HAVE an entry point that uses
    it, so the name lived in one comment and one argument. Here it is derived: the recipe whose declaring line
    invokes this script with --collect <recipe>. Returns "" when the ladder declares none - the remedy then says
    so, because a remedy naming a recipe the ladder does not declare is prose (D-405), and a whole-set mode
    nothing invokes is a control nothing runs (BUG-492).
    """
    pattern = re.compile(r"--collect\s+" + re.escape(recipe) + r"(?![-\w])")
    return ", ".join(name for name, lines in recipes_of(text) if any(pattern.search(ln) for ln in lines))


def remedy_for(recipe: str, text: str) -> str:
    """The remedy a whole-set verdict owes: the DERIVED entry point, or the absence of one named as a fault."""
    entry = whole_set_entry(recipe, text)
    if entry:
        return "run the whole set in ONE run: `just " + entry + "`"
    return ("the ladder declares NO entry point that collects `" + recipe + "` in one run - that is itself a "
            "fault (a whole-set mode nothing invokes is a control nothing runs, BUG-492)")


def line_set_fingerprint(recipe: str, lines: list[str]) -> str:
    """sha16 over a recipe and its ORDERED declaring lines - the COVERAGE a recorded verdict is about (D-2982).

    The same defect the census paid for, one level down: a debt that ROTATES leaves a count untouched. A verdict
    taken over one ladder and compared to another ladder is that defect in the instrument that measures
    everything, and the fingerprint is derived from the lines the scan ITSELF runs, so there is no second census
    of the ladder (D-2642).
    """
    return hashlib.sha256("\n".join([recipe] + list(lines)).encode("utf-8")).hexdigest()[:16]


def age_hours(measured_at: Any, now: datetime) -> float | None:
    """How old a recorded scan is, or None when its timestamp is absent or unusable (never a silent 0)."""
    try:
        measured = datetime.fromisoformat(str(measured_at))
    except (TypeError, ValueError):
        return None
    if measured.tzinfo is None:
        measured = measured.replace(tzinfo=UTC)
    return (now - measured).total_seconds() / 3600.0


def scan_payload(recipe: str, lines: list[str], worst: int | None, faults: list[Fault], elapsed: float | None, *,
                 ladder: str, opening: dict, head_at_end: str, worktree: dict, now: datetime, state: str) -> dict:
    """What ONE scan measured, as a record: the verdict, its coverage, ITS BYTES, its cost and its moments.

    PURE, so a control can drive it without running a ladder. The record IS the measurement - a receipt that can
    drift from the run it describes would be read as evidence, which is worse than no receipt at all.

    TWO MOMENTS, TWO ROLES (BUG-1010). `started_at` is when the scan BEGAN; `measured_at` is when this record was
    WRITTEN, and it is the one the declared age budget is applied to (INV-1), so the opening is named in a field
    of its own rather than by overloading one timestamp. `head_at_start` comes from `opening` and `head_at_end`
    from the close, and `state` says whether the run FINISHED: a record that cannot say it finished is not a
    verdict, whatever else it carries.
    """
    opened = opening.get("worktree") or {}
    untracked_at_start = [str(p) for p in (opened.get("untracked") or [])]
    untracked_at_end = [str(p) for p in (worktree.get("untracked") or [])]
    return {
        "schema_version": RECEIPT_SCHEMA,
        "rail": SELF,
        "ladder": ladder,
        "recipe": recipe,
        "state": state,
        "line_count": len(lines),
        "line_set_fingerprint": line_set_fingerprint(recipe, lines),
        "worst_rc": worst,
        "faults": [{"line": line, "rc": rc, "seconds": round(seconds, 1)} for line, rc, seconds in faults],
        "elapsed_seconds": None if elapsed is None else round(elapsed, 1),
        "started_at": opening.get("started_at"),
        "measured_at": now.isoformat(timespec="seconds"),
        "head_at_start": str(opening.get("head") or ""),
        "head_at_end": head_at_end,
        "worktree": {
            "modified_at_start": [str(p) for p in (opened.get("modified") or [])],
            "modified_at_end": [str(p) for p in (worktree.get("modified") or [])],
            "untracked_at_start": untracked_at_start,
            # UNTRACKED AT END minus UNTRACKED AT START: these are the scan's own OUTPUTS (a rail mints an
            # evidence file), and they are kept apart from the opening reading on purpose - see attribution().
            "minted_during_scan": [p for p in untracked_at_end if p not in untracked_at_start],
        },
    }


def cleared(environ: dict[str, str] | None = None) -> dict[str, str]:
    """The environment git is run with: this process's, minus git's OWN overrides (GIT_OVERRIDES).

    BUG-527/BUG-568's class, and here it feeds a VERDICT. An inherited index or git dir is somebody else's
    repository: MEASURED on this clone 2026-10-25, an empty inherited GIT_INDEX_FILE made `git status --porcelain
    -uall` answer 3973 lines against 0, and `GIT_DIR` pointed at a decoy made git refuse to answer at all. Both
    readings now decide whether a green record may be believed, so both are taken through THIS worktree only.
    """
    source = dict(os.environ if environ is None else environ)
    for name in GIT_OVERRIDES:
        source.pop(name, None)
    return source


def head_sha(environ: dict[str, str] | None = None) -> str:
    """git's own short answer for HEAD at the moment it is ASKED, or "" when git cannot answer (never a guess).

    An EMPTY answer is not a clean answer: attribution() REFUSES on it, because a verdict that names no bytes is
    a verdict about nothing (D-405/BUG-1018's class).
    """
    done = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO), capture_output=True, text=True,
                          env=cleared(environ))
    return done.stdout.strip() if done.returncode == 0 else ""


def worktree_state(environ: dict[str, str] | None = None) -> dict[str, list[str]]:
    """The worktree as git sees it, with TRACKED changes and UNTRACKED files kept APART because they mean apart.

    `git status --porcelain` answers in two letters: `??` is a path git does not know, everything else is a
    TRACKED path that differs from the commit. attribution() turns on the distinction - a tracked difference means
    the bytes that ran are NOT the commit's, while an untracked path is a candidate input whose reach a status
    line cannot decide. An unanswerable read returns empty lists and is therefore NOT a clean reading; the caller
    asks head_sha() separately, and attribution() refuses when either reading is missing.
    """
    done = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=str(REPO), capture_output=True,
                          text=True, env=cleared(environ))
    if done.returncode != 0:
        return {"modified": [], "untracked": []}
    modified: list[str] = []
    untracked: list[str] = []
    for line in done.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        (untracked if line.startswith("??") else modified).append(path)
    return {"modified": modified, "untracked": untracked}


def snapshot(now: datetime | None = None, environ: dict[str, str] | None = None) -> dict:
    """The state a scan is a measurement OF, read ONCE at its OPENING: the moment, the commit, the worktree."""
    return {"started_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
            "head": head_sha(environ),
            "worktree": worktree_state(environ)}


def attribution(payload: dict) -> str:
    """WHY this record may not be read as a verdict about the bytes it names - "" when it may (BUG-1010).

    The claim is about a SET OF BYTES, and a commit names that set only while the worktree equals it. Three shapes
    break the equality, and each is NAMED rather than averaged into one boolean:
      * HEAD MOVED between the opening and the close - the bytes measured are neither commit's;
      * a TRACKED file differed from HEAD when the scan BEGAN - the scan ran code no commit contains;
      * a TRACKED file differed when it ENDED - something the scan ran rewrote the tree it was measuring;
      * no commit at all was named at one end - a verdict whose subject is missing (D-405).

    THE SHAPE IT DOES NOT GATE, named so it cannot be mistaken for coverage (D-3152 clause 4): a path that was
    UNTRACKED when the scan began. A status line cannot decide whether a rail imported it, and the alternative -
    gating on the record's own outputs - would mark every scan that mints an evidence file un-attributable, so the
    rule would be bypassed (D-3151). Both readings therefore TRAVEL in the record and are reported by
    uncommitted_note(); neither turns the verdict.
    """
    start = str(payload.get("head_at_start") or "")
    end = str(payload.get("head_at_end") or "")
    if not start or not end:
        return ("it names no commit (" + ("start" if not start else "end")
                + " reading empty), and a verdict that cannot name its bytes is a verdict about nothing")
    if start != end:
        return ("HEAD MOVED while the rails ran (" + start + " -> " + end + "), so the bytes measured are neither "
                "commit's - the scan spans a commit and no single byte set")
    worktree = payload.get("worktree") or {}
    for field, when in (("modified_at_start", "when the scan BEGAN"), ("modified_at_end", "when it ENDED")):
        dirty = [str(p) for p in (worktree.get(field) or [])]
        if dirty:
            named = ", ".join(dirty[:PATHS_NAMED])
            if len(dirty) > PATHS_NAMED:
                named += ", +" + str(len(dirty) - PATHS_NAMED) + " more"
            return (str(len(dirty)) + " TRACKED file(s) differed from " + end + " " + when + " (" + named
                    + "), so the scan ran code that commit does not contain")
    return ""


def uncommitted_note(payload: dict) -> str:
    """What the record saw that git did not know, as a NOTE: reported, never gating (D-3151, see attribution()).

    `minted_during_scan` is the scan's own output and `untracked_at_start` is state the run inherited; both are
    counted here so a reader can see that a green verdict was taken on an impure tree WITHOUT the rule turning
    every artefact-producing scan un-attributable.
    """
    worktree = payload.get("worktree") or {}
    before = len(worktree.get("untracked_at_start") or [])
    minted = len(worktree.get("minted_during_scan") or [])
    parts = ([] if not before else [str(before) + " file(s) untracked at start"]) \
        + ([] if not minted else [str(minted) + " minted during the scan"])
    return ("; " + ", ".join(parts)) if parts else ""


def write_record(payload: dict) -> pathlib.Path:
    """Write the record crash-safely (C6): tempfile -> fsync -> os.replace, or REFUSE loudly (never a silent loss)."""
    path = receipt_path()
    try:
        handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=1, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as err:
        raise SystemExit("FAIL-CLOSED (C16): the ladder's receipt could not be written to " + str(path) + " ("
                         + str(err) + ") - a whole-set verdict nobody records is a verdict reasoned about from "
                         "memory, which is how BUG-759 went unnoticed (D-2983)") from err
    return path


def record_open(recipe: str, lines: list[str], opening: dict) -> pathlib.Path:
    """Record that a scan has BEGUN, BEFORE the first rail, so a killed scan is a NAMED state (BUG-1010).

    MEASURED 2026-10-25: a detached whole-set scan reached rail ~180 of 194 and vanished - no traceback, no crash
    report, the receipt untouched - leaving a tree indistinguishable from one never scanned. `worst_rc` is None
    and never 0 here, so even a reader that ignored `state` cannot read a half-run as green.
    """
    ladder, _recipes = declared()
    payload = scan_payload(recipe, lines, None, [], None, ladder=ladder, opening=opening, head_at_end="",
                           worktree={}, now=datetime.now(UTC), state="running")
    return write_record(payload)


def record_scan(recipe: str, lines: list[str], worst: int, faults: list[Fault], elapsed: float, *,
                opening: dict, environ: dict[str, str] | None = None) -> pathlib.Path:
    """Record what this run measured. Crash-safe (C6), and written for a RED ladder too: a red is a measurement.

    `opening` is REQUIRED, not defaulted: a record whose opening was invented at the close would name a moment
    and a commit it never read, which is the defect this parameter exists to end (D-3152 clause 2).
    """
    ladder, _recipes = declared()
    payload = scan_payload(recipe, lines, worst, faults, elapsed, ladder=ladder, opening=opening,
                           head_at_end=head_sha(environ), worktree=worktree_state(environ),
                           now=datetime.now(UTC), state="finished")
    return write_record(payload)


def recorded_scan() -> tuple[dict | None, str]:
    """The recorded scan, or (None, why not). An unreadable record is a REPORTED condition, never an abort.

    The banner reads this BEFORE any rail runs, so raising here would hide the whole ladder - the very defect
    (BUG-759) this record exists to end. The fail-closed reading is the LAST line of the recipe instead.
    """
    path = receipt_path()
    shown = str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
    if not path.is_file():
        return None, "no full scan is recorded at " + shown
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return None, "the recorded receipt " + shown + " cannot be read (" + str(err) + ")"
    if not isinstance(payload, dict):
        return None, "the recorded receipt " + shown + " is not an object"
    return payload, ""


def receipt_verdict(payload: Any, fingerprint: str, line_count: int, *, recipe: str, now: datetime,
                    max_age_hours: float, absent: str = "", remedy: str = "") -> tuple[int, str]:
    """PURE: what a recorded full scan is evidence FOR, at THIS moment, about THIS ladder (D-2983/BUG-759).

    Three answers, in the tri-state the ladder already speaks (BUG-457):
      0 the whole ladder was MEASURED GREEN under exactly this coverage;
      1 a red is RECORDED under exactly this coverage - a measured fault may not go quiet (C16);
      2 UNKNOWN - never measured here, measured against a DIFFERENT ladder, or older than the declared budget.
        Owner-owed and loud, never fatal: only a full scan can clear it, and "unknown" is not "clean".
    """
    tail = ("; " + remedy) if remedy else ""
    if not isinstance(payload, dict):
        return EXIT_OWED, ("the WHOLE-SET fault set of `just " + recipe + "` is UNKNOWN: "
                           + (absent or "no full scan is recorded on this machine")
                           + " - a prefix report is not a verdict (BUG-573)" + tail)
    # WHICH BYTES, before WHICH LADDER (BUG-1010): a record that cannot say it FINISHED is not a verdict about
    # anything, and both shapes are NAMED - a scan still running or killed, and a record written by a collector
    # younger than this rule, which had no field in which to say it.
    state = str(payload.get("state") or "")
    if state == "running":
        return EXIT_OWED, ("the WHOLE-SET fault set of `just " + recipe + "` is UNKNOWN: a scan BEGAN at "
                           + str(payload.get("started_at") or "an unrecorded moment") + " and never recorded a "
                           "finish, so it was killed or is still running - a half-run is not a verdict (BUG-1010)"
                           + tail)
    if state != "finished":
        return EXIT_OWED, ("the WHOLE-SET fault set of `just " + recipe + "` is UNKNOWN: the recorded scan cannot "
                           "say it FINISHED (schema " + str(payload.get("schema_version") or "?")
                           + " carries no state) - a record that cannot say it finished is not a verdict "
                           "(BUG-1010)" + tail)
    recorded = str(payload.get("line_set_fingerprint") or "")
    if recorded != fingerprint:
        return EXIT_OWED, ("the WHOLE-SET fault set of `just " + recipe + "` is UNKNOWN: the ladder CHANGED "
                           "since the recorded scan (" + str(payload.get("line_count")) + " -> " + str(line_count)
                           + " declaring line(s), " + (recorded or "<none>") + " -> " + fingerprint + ") - a "
                           "verdict is a claim about the ladder at the MOMENT OF MEASUREMENT (D-2660)" + tail)
    age = age_hours(payload.get("measured_at"), now)
    if age is None:
        return EXIT_OWED, ("the WHOLE-SET fault set of `just " + recipe + "` is UNKNOWN: the recorded scan "
                           "carries no usable measured_at, and a record with no moment cannot be aged" + tail)
    if age > max_age_hours:
        return EXIT_OWED, ("the WHOLE-SET fault set of `just " + recipe + "` is UNKNOWN: the last full scan is "
                           + f"{age:.1f}" + "h old, beyond the declared " + f"{max_age_hours:.0f}" + "h budget"
                           + tail)
    if payload.get("faults"):
        recorded_faults = payload.get("faults") or []
        named = "; ".join(str(one.get("line")) for one in recorded_faults if isinstance(one, dict))
        return EXIT_FATAL, ("a red is RECORDED for `just " + recipe + "` under exactly this coverage: "
                            + str(len(recorded_faults)) + " fault(s) measured " + f"{age:.1f}" + "h ago ("
                            + named + ") - a measured fault may not go quiet (C16)" + tail)
    # A RECORDED RED OUTRANKS UNATTRIBUTABILITY, and the order is the point: an unattributable scan that measured
    # a fault still MEASURED it, so reporting provenance first would soften a red into "unknown" - C16 inverted.
    why = attribution(payload)
    if why:
        return EXIT_OWED, ("the whole ladder `just " + recipe + "` recorded no fault, but the record may not be "
                           "read as a verdict about a commit: " + why + " - re-measure on a clean tree"
                           + tail)
    return EXIT_CLEAN, ("the whole ladder `just " + recipe + "` was MEASURED GREEN under exactly this "
                        + str(line_count) + " declaring line(s) " + f"{age:.1f}" + "h ago (fingerprint "
                        + fingerprint + ", head " + str(payload.get("head_at_end") or "?")
                        + uncommitted_note(payload) + ")")


def receipt_lines(*, strict: bool) -> tuple[int, list[str]]:
    """The recorded whole-set verdict, as (tri-state rc, the lines to print).

    strict=False is the BANNER reading: it stands BEFORE every rail, so it may not abort - an unresolvable
    record is REPORTED as UNKNOWN instead, because an abort there would hide the ladder it exists to declare
    (that is BUG-759's mechanism). strict=True is the recipe's LAST line, where a broken DECLARATION is a defect
    (1 FATAL) while an absent, changed or stale RECORD stays owner-owed (2): only a full scan can clear that.
    """
    try:
        block = receipt_declaration()
        recipe = str(block["recipe"])
        lines = body(recipe)
        text = ladder_text()
        budget = block["max_age_hours"]
        if isinstance(budget, bool) or not isinstance(budget, (int, float)):
            raise SystemExit("FAIL-CLOSED (C16): config/rail_registry.yaml#ladder_receipt.max_age_hours is not a "
                             "number (" + repr(budget) + ") - an age budget that cannot be read is not a budget "
                             "(D-2983)")
        max_age = float(budget)
        payload, absent = recorded_scan()
        remedy = remedy_for(recipe, text)
    except SystemExit as err:
        if strict:
            raise
        return EXIT_OWED, ["ladder receipt: UNKNOWN - " + str(err)]
    rc, message = receipt_verdict(payload, line_set_fingerprint(recipe, lines), len(lines), recipe=recipe,
                                  now=datetime.now(UTC), max_age_hours=max_age, absent=absent,
                                  remedy=remedy)
    return rc, ["ladder receipt: " + message]


def narrowing(recipe: str) -> str:
    """The ONE sentence that reports how the shell census narrows a recipe - empty when nothing is excluded.

    BUG-1008: an exclusion that is not reported is a blind spot; this sentence is its receipt. It is emitted by
    BOTH modes (the banner and the scan) so the count a reader sees before the run is the count the run honoured.
    """
    excluded = uncollectable(recipe)
    if not excluded:
        return ""
    return (" | " + str(len(excluded)) + " line(s) carry just-TEMPLATE syntax, so the LADDER runs them and the "
            "shell census excludes them BY DECLARATION (BUG-1008)")


def banner(recipe: str, full: str) -> int:
    """Declare the ladder's own shape, in the ladder's own units, before any rail can abort the recipe.

    `full` is the recipe that measures the WHOLE set, so it is not decoration: without it the banner can only say
    "a red line hides the rest" and cannot say what to run instead. MEASURED 2026-10-25: `--banner health` with no
    `--full` raised `TypeError: can only concatenate str (not "NoneType") to str` AFTER printing the first line, so
    a hand-run of a declared mode produced a traceback - a crash reports nothing about the tree and reads as a
    broken rail (C16/D-3150). It now REFUSES with the exact argument that fixes it.
    """
    if not full:
        raise SystemExit("FAIL-CLOSED (ladder): --banner <recipe> also needs --full <whole-set recipe> - the banner"
                         " names the run that measures EVERY fault, and a banner that cannot name it is decoration."
                         " Try: python3 scripts/run_ladder.py --banner health --full health-full")
    lines = body(recipe)
    hard = [ln for ln in lines if "exit 1" in ln]
    print("ladder scan: `just " + recipe + "` reports a PREFIX - it stops at the FIRST non-zero line, and "
          + str(len(lines)) + " declaring line(s) stand in it (" + str(len(hard)) + " declared a HARD gate), so a "
          "red line HIDES every line after it (BUG-573)." + narrowing(recipe))
    print("ladder scan: for EVERY fault of this ladder in ONE run use `just " + full + "` (D-2680).")
    # D-2983: the record is printed HERE, before any rail can abort - and it may never abort the recipe itself.
    _recorded_rc, messages = receipt_lines(strict=False)
    for message in messages:
        print(message)
    return EXIT_CLEAN


def scan(recipe: str) -> int:
    """Collect every fault of one declared recipe and exit with the WORST code, never the first."""
    lines = body(recipe)
    print("=== ladder scan (" + recipe + ", " + str(len(lines)) + " declaring line(s)): every line runs, "
          "nothing is hidden (D-2680) ===" + narrowing(recipe), flush=True)
    # BUG-1010: the opening is read and RECORDED before the first rail, so the verdict can name the bytes it ran
    # and a killed scan leaves a record that says so. Recorded, not merely remembered: a detached scan that dies
    # leaves this row and nothing else.
    opening = snapshot()
    record_open(recipe, lines, opening)
    print("ladder scan: opened at head " + (str(opening.get("head")) or "?") + " with "
          + str(len((opening.get("worktree") or {}).get("modified") or [])) + " tracked change(s) and "
          + str(len((opening.get("worktree") or {}).get("untracked") or [])) + " untracked file(s); the receipt "
          "records BOTH ends (BUG-1010)", flush=True)
    t0 = time.monotonic()
    worst, faults = run_lines(lines)
    elapsed = time.monotonic() - t0
    recorded = record_scan(recipe, lines, worst, faults, elapsed, opening=opening)
    print("ladder receipt: RECORDED " + str(len(lines)) + " declaring line(s), worst rc=" + str(worst) + " -> "
          + str(recorded.relative_to(REPO)) + " (coverage " + line_set_fingerprint(recipe, lines) + ")")
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
    # BUG-1008 - the known instance is the LIVE line that produced the false red, not an invented one.
    tmpl = "{{just_executable()}} --list >/dev/null || { echo \"died\"; exit 1; }"
    kept, dropped = shell_split(["echo KEEP", tmpl])
    check("a_just_TEMPLATE_line_is_NOT_handed_to_the_shell", kept == ["echo KEEP"] and dropped == [tmpl],
          "BUG-1008: /bin/sh read `{{just_executable()}}` as `syntax error near unexpected token '}}'` (rc=2) "
          "and the whole-set receipt recorded a FAULT that turned `just health` from OWNER-OWED to FATAL")
    check("the_excluded_line_is_COUNTED_not_silently_dropped", len(parse_report(ladder([tmpl]), "probe")[1]) == 1,
          "a narrowed census that is REPORTED is not a blind spot: the exclusion count is the receipt of the "
          "narrowing (both directions of the BUG-1008 rule)")
    check("a_plain_line_is_untouched_by_that_rule", shell_split(["python3 x.py || exit 1"])[0] == ["python3 x.py || exit 1"],
          "the exclusion narrows ONLY template lines - a rule that drops every line would report a clean scan of "
          "nothing (negative control, BUG-492)")
    check("the_live_ladder_reports_its_own_TEMPLATE_exclusion",
          all(TEMPLATE.search(ln) for ln in uncollectable("health")) and len(uncollectable("health")) >= 1,
          "MEASURED on the LIVE ladder: every line the census excludes really carries just-template syntax, so "
          "the exclusion is a fact about the interpreter and not a filter that hides work")
    try:
        banner("health", "")
        banner_refused = False
    except SystemExit:
        banner_refused = True
    check("a_banner_with_no_WHOLE_SET_recipe_REFUSES_instead_of_crashing", banner_refused,
          "MEASURED 2026-10-25: `--banner health` with no --full raised TypeError AFTER printing its first line, "
          "so a declared mode produced a traceback - a crash reports nothing about the tree (C16/D-3150)")
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
    dup_text = ladder(["echo MARK", "python3 scripts/lib/fixture.py --selftest || exit 1",
                       "python3 scripts/lib/fixture.py --selftest || exit 1"])
    dup_lines = parse(dup_text, "probe")
    dups = duplicate_declaring_lines(dup_lines)
    refused = duplicated_refusal("probe", "justfile", dups)
    check("a_duplicated_declaring_line_is_refused",
          len(dups) == 1 and dups[0][1] == 2 and dup_lines.count(dups[0][0]) == 2 and "justfile" in refused
          and "x2" in refused and dups[0][0] in refused,
          "BUG-584: a declaring line standing TWICE is refused, and the refusal NAMES the ladder, the count and "
          "the line - the census IS the count of these lines, so one line stands ONCE")
    check("negative_control_a_unique_ladder_is_refused_by_nothing",
          not duplicate_declaring_lines(parse(ladder(["echo A", "echo B"]), "probe")),
          "a ladder whose declaring lines are UNIQUE earns no refusal - a rule that refuses everything is not a "
          "rule (BUG-492; BUG-582 is the zero case)")
    ladder_path, recipes = declared()
    live = REPO / ladder_path
    both = live.is_file() and all(parse(live.read_text(encoding="utf-8"), r) for r in recipes)
    check("every_declared_recipe_has_declaring_lines", both,
          "D-405 both directions: each recipe config/rail_registry.yaml#recipes names yields >= 1 line ("
          + ", ".join(recipes) + ")")
    live_census = {r: duplicate_declaring_lines(parse(live.read_text(encoding="utf-8"), r)) for r in recipes}
    check("the_live_ladder_declares_each_line_once", not any(live_census.values()),
          "the LIVE ladder is clean in every declared recipe - the control that would have caught BUG-584 at the "
          "boundary (MEASURED 2026-09-27 before this landing: recipe health carried 98 line(s) where 97 are "
          "DISTINCT)")
    # ---- the RECEIPT (D-2983/BUG-759): one rule, five answers, every input synthetic (no live tree)
    moment = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
    coverage = line_set_fingerprint("probe", got)
    clean_tree = {"modified_at_start": [], "modified_at_end": [], "untracked_at_start": [], "minted_during_scan": []}
    fresh = {"state": "finished", "line_count": len(got), "line_set_fingerprint": coverage, "worst_rc": EXIT_CLEAN,
             "faults": [], "measured_at": (moment - timedelta(hours=1)).isoformat(timespec="seconds"),
             "head_at_start": "abc1234", "head_at_end": "abc1234", "worktree": dict(clean_tree)}
    rc, message = receipt_verdict(fresh, coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_recorded_green_scan_is_green", rc == EXIT_CLEAN and "MEASURED GREEN" in message,
          "D-2983: a whole-set verdict recorded over EXACTLY this coverage, inside its age budget, is the one "
          "state in which 'the ladder is green' is a measurement rather than a hope")
    red = dict(fresh, worst_rc=EXIT_FATAL, faults=[{"line": "sh -c 'exit 1'", "rc": 1, "seconds": 0.1}])
    rc, message = receipt_verdict(red, coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_recorded_ladder_red_is_not_silently_green", rc == EXIT_FATAL and "1 fault" in message,
          "D-2983/BUG-759: a red the whole-set scan MEASURED may not go quiet - once a fault is recorded the "
          "fast ladder is red until it is fixed AND re-measured (C16)")
    rc, message = receipt_verdict(None, coverage, len(got), recipe="probe", now=moment, max_age_hours=72,
                                  absent="no receipt at .ladder_receipt.json")
    check("a_never_measured_ladder_is_UNKNOWN", rc == EXIT_OWED and "UNKNOWN" in message and "no receipt" in message,
          "D-2983: 'never measured on this machine' is a REPORTED state (loud, owner-owed, rc=2) - BUG-759 was a "
          "whole-set fault set that read as clean because nobody had asked")
    rc, message = receipt_verdict(fresh, "0000000000000000", len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_changed_ladder_invalidates_its_receipt", rc == EXIT_OWED and "UNKNOWN" in message
          and "0000000000000000" in message,
          "D-2983: a record measured over a DIFFERENT line set is evidence for a ladder that no longer exists "
          "(D-2660) - a coverage that changed is not a coverage that was met")
    old = dict(fresh, measured_at=(moment - timedelta(hours=80)).isoformat(timespec="seconds"))
    rc, message = receipt_verdict(old, coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_stale_record_is_UNKNOWN_by_age", rc == EXIT_OWED and "80.0h" in message,
          "D-2983: the age budget is DECLARED (config/rail_registry.yaml#ladder_receipt), so a green record "
          "cannot be relied on forever by silence")
    same = line_set_fingerprint("probe", ["echo A"]) == line_set_fingerprint("probe", ["echo A"])
    differs = line_set_fingerprint("probe", ["echo A"]) != line_set_fingerprint("probe", ["echo B"])
    elsewhere = line_set_fingerprint("probe", ["echo A"]) != line_set_fingerprint("other", ["echo A"])
    check("the_fingerprint_follows_the_line_set", same and differs and elsewhere,
          "D-2983: the coverage is the recipe AND its ordered declaring lines - an added line, a reordering or "
          "another recipe is a different coverage, and only a matching coverage makes a record comparable")
    with_entry = ladder(["echo A"], neighbour=True) + "fuller:\n    python3 scripts/" + SELF + " --collect probe\n"
    check("the_whole_set_entry_point_is_DERIVED_from_the_ladder", whole_set_entry("probe", with_entry) == "fuller",
          "D-2983: the entry point a remedy names is READ from the ladder's own bytes, so renaming that recipe "
          "cannot leave the remedy naming a recipe that is gone (D-405)")
    near = ladder(["echo A"]) + "deeper:\n    python3 scripts/" + SELF + " --collect probe-deep\n"
    check("a_longer_recipe_name_is_not_the_entry_for_a_shorter_one",
          whole_set_entry("probe", near) == "" and "NO entry point" in remedy_for("probe", near),
          "D-2983/BUG-492: '--collect probe-deep' is NOT an entry point for 'probe' - a prefix match would "
          "produce a remedy the ladder does not declare, and a whole-set mode nothing invokes is a control "
          "nothing runs")
    payload = scan_payload("probe", got, EXIT_FATAL, [("sh -c 'exit 1'", 1, 0.25)], 1.5, ladder="justfile",
                           opening={"started_at": (moment - timedelta(minutes=9)).isoformat(timespec="seconds"),
                                    "head": "abc1234", "worktree": {"modified": [], "untracked": []}},
                           head_at_end="abc1234", worktree={"modified": [], "untracked": []}, now=moment,
                           state="finished")
    check("the_record_equals_the_measurement_it_took",
          payload["line_count"] == len(got) and payload["line_set_fingerprint"] == coverage
          and payload["worst_rc"] == EXIT_FATAL and len(payload["faults"]) == 1
          and payload["faults"][0]["rc"] == 1 and str(payload["measured_at"]).startswith("2026-10-13"),
          "D-2983: the record IS the measurement - a receipt that can drift from the run it describes would be "
          "read as evidence, which is worse than no receipt at all")
    # ---- WHICH BYTES (BUG-1010/D-3152 clause 2): an attribution rule with BOTH ends driven
    def record(**overrides: Any) -> dict:
        """A finished record over `got` with the opening/close readings a control wants to drive."""
        opening = {"started_at": (moment - timedelta(minutes=9)).isoformat(timespec="seconds"), "head": "abc1234",
                   "worktree": {"modified": [], "untracked": []}}
        worktree = {"modified": [], "untracked": []}
        opening = overrides.pop("opening", opening)
        worktree = overrides.pop("worktree", worktree)
        built = scan_payload("probe", got, EXIT_CLEAN, [], 540.0, ladder="justfile", opening=opening,
                             head_at_end="abc1234", worktree=worktree, now=moment, state="finished")
        built.update(overrides)
        return built

    rc, message = receipt_verdict(record(), coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_clean_scan_names_the_bytes_it_ran", rc == EXIT_CLEAN and "abc1234" in message,
          "BUG-1010: a record read on a clean tree at an unmoved HEAD is a verdict about that commit - the one "
          "state in which the commit sha is a NAME for the bytes that ran")
    rc, message = receipt_verdict(record(head_at_end="def5678"), coverage, len(got), recipe="probe", now=moment,
                                  max_age_hours=72)
    check("a_scan_whose_HEAD_MOVED_is_not_a_verdict_about_either_commit",
          rc == EXIT_OWED and "abc1234" in message and "def5678" in message,
          "BUG-1010 (b): a commit landed MID-SCAN, so the bytes measured belong to no commit - both shas are "
          "named, because the reader has to see WHICH two agreed no verdict covers")
    rc, message = receipt_verdict(record(opening={"started_at": "2026-10-13T11:51:00+00:00", "head": "abc1234",
                                                 "worktree": {"modified": ["scripts/run_ladder.py"],
                                                              "untracked": []}}),
                                  coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_scan_that_BEGAN_on_a_MODIFIED_tracked_file_is_OWNER_OWED",
          rc == EXIT_OWED and "run_ladder.py" in message and "does not contain" in message,
          "BUG-1010's OBSERVED case: a green receipt naming e239b52 for a run whose run_ladder.py was NOT "
          "e239b52 - the scan ran code no commit contains, and the path is NAMED so it can be fixed")
    rc, message = receipt_verdict(record(worktree={"modified": ["scripts/check_x.py"], "untracked": []}),
                                  coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_scan_that_ENDED_on_a_MODIFIED_tracked_file_is_OWNER_OWED",
          rc == EXIT_OWED and "check_x.py" in message,
          "the same defect at the close: something the scan RAN rewrote the tree it was measuring, so the later "
          "rails did not see the bytes the earlier ones did")
    rc, message = receipt_verdict(record(head_at_end=""), coverage, len(got), recipe="probe", now=moment,
                                  max_age_hours=72)
    check("a_record_that_names_NO_commit_is_OWNER_OWED_never_green",
          rc == EXIT_OWED and "names no commit" in message,
          "D-405/BUG-1018's class: git refusing to answer is not a clean answer - a verdict whose subject is "
          "absent may not be reported as a verdict (fail-closed)")
    rc, message = receipt_verdict(record(state="running", worst_rc=None, head_at_end=""),
                                  coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("an_UNFINISHED_scan_is_OWNER_OWED_and_never_green",
          rc == EXIT_OWED and "BEGAN" in message and "half-run" in message,
          "BUG-1010 (a): a scan that was KILLED leaves `state: running` - MEASURED 2026-10-25 a detached scan "
          "vanished at rail 180/194 and left the tree indistinguishable from one never scanned")
    unschema = record()
    unschema.pop("state")
    rc, message = receipt_verdict(unschema, coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("a_record_that_cannot_say_it_FINISHED_is_UNKNOWN_not_green",
          rc == EXIT_OWED and "FINISHED" in message,
          "the schema-1 shape is NAMED rather than assumed: a record written by a collector younger than this "
          "rule had no field in which to say it finished, so no old green survives the change by silence")
    minted = record(worktree={"modified": [], "untracked": ["governance/evidence/NEW.json"]})
    rc, message = receipt_verdict(minted, coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("an_artefact_the_scan_MINTED_does_not_make_it_un_attributable",
          rc == EXIT_CLEAN and "1 minted during the scan" in message,
          "D-3151: gating on the record's OWN OUTPUTS would mark every scan that mints an evidence file "
          "un-attributable, and a rule that costs that much is a rule that gets bypassed - so it is REPORTED")
    inherited = record(opening={"started_at": "2026-10-13T11:51:00+00:00", "head": "abc1234",
                                "worktree": {"modified": [], "untracked": ["notes.py"]}},
                       worktree={"modified": [], "untracked": ["notes.py", "art.json"]})
    rc, message = receipt_verdict(inherited, coverage, len(got), recipe="probe", now=moment, max_age_hours=72)
    check("what_was_UNTRACKED_BEFORE_and_what_APPEARED_are_counted_APART",
          rc == EXIT_CLEAN and "1 file(s) untracked at start" in message and "1 minted" in message,
          "the one distinction the record has to keep: an inherited uncommitted file is state the run did not "
          "create, an appearing one is the run's own output - counting them as one number would make the note "
          "unreadable and its absence in the verdict unfalsifiable")
    check("git_OWN_overrides_are_CLEARED_before_the_worktree_is_read",
          all(name not in cleared({"GIT_DIR": "d", "GIT_WORK_TREE": "w", "GIT_INDEX_FILE": "i", "PATH": "/bin"})
              for name in GIT_OVERRIDES)
          and cleared({"PATH": "/bin"})["PATH"] == "/bin",
          "BUG-527/BUG-568's class: GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE are inherited by every child, and this "
          "reading now decides a verdict - everything else is kept, so the scrub is a filter and not a wipe")
    live = worktree_state()
    armed = worktree_state({"GIT_INDEX_FILE": os.path.join(tempfile.gettempdir(), ".no_such_index_for_a_control"),
                            "PATH": os.environ.get("PATH", "")})
    check("an_INHERITED_index_cannot_change_what_the_worktree_reads",
          not head_sha() or (armed == live),
          "MEASURED on this clone: an inherited empty GIT_INDEX_FILE made the same command answer 3973 lines "
          "against 0, which would have marked EVERY scan un-attributable - the reading is taken through THIS "
          "repository or not at all (the live leg is vacuous only where git cannot answer, which head_sha() names)")
    print("ladder controls: " + str(ok) + "/" + str(ok + fail) + " known-answer control(s) fire")
    return EXIT_FATAL if fail else EXIT_CLEAN


def main(argv: list[str]) -> int:
    """Dispatch the three modes; every refusal inside them is a VERDICT (a SystemExit message), not a traceback."""
    ap = argparse.ArgumentParser(description="D-2680: run the declared ladder for EVERY fault, not the first.")
    ap.add_argument("--banner", metavar="RECIPE", help="declare the prefix property of this recipe")
    ap.add_argument("--full", metavar="RECIPE", help="the recipe that reports the whole fault set (named here)")
    ap.add_argument("--collect", metavar="RECIPE", help="run every line of this recipe, reporting every fault")
    ap.add_argument("--receipt-check", action="store_true",
                    help="report the RECORDED whole-set verdict as a tri-state exit code (D-2983/BUG-759)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.banner:
        return banner(a.banner, a.full)
    if a.collect:
        return scan(a.collect)
    if a.receipt_check:
        recorded_rc, messages = receipt_lines(strict=True)
        for message in messages:
            print(message)
        return recorded_rc
    ap.error("one of --banner, --collect, --receipt-check or --selftest is required")
    return EXIT_FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
