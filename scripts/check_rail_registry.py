#!/usr/bin/env python3
"""check_rail_registry.py - the RAIL REGISTRY: the ONE home of the fact "this rail is a rail" (D-2665).

WHY (the class, not the instance). The rail set had no registry, so the three mechanical defect classes that kept
recurring could only be found by inspiration:
  (i)   a rail NOTHING RUNS - a control that never fires (BUG-492);
  (ii)  a rail whose PRINTED verdict and EXIT CODE disagree - a green line over a red code;
  (iii) a rail whose REMEDY or INPUT is uncontrolled - a rail that rewrites what it checks (BUG-537) or whose
        input the ladder mutates while checking it (BUG-556).
This rail settles, without judgement, what a machine can settle:
  * every `scripts/check_*.py` / `scripts/verify_*.py` is INVOKED by a declared ladder recipe, or declared DORMANT
    with the thing that exercises it - and that path must EXIST (a dormancy whose subject is absent is not a
    declaration, D-405/BUG-488);
  * every rail the registry DECLARES a writer must have its own `--selftest` run BY THE LADDER (class iii: a rail
    that replaces bytes makes a CLAIM, and an unproven claim is where BUG-537 and BUG-556 came from);
  * a declared `guard:` is matched against the ladder's own text: a disagreement is class (ii), fail closed;
  * the registry's OWN SCHEMA is CLOSED: every top-level key must be listed in this file's `schema.keys`, and a key
    shaped like a COMMAND LINE is refused outright (T-164/BUG-837: eight guard declarations lived at column 0 as
    top-level keys, so the rail reported "no declared guard disagrees with the ladder" about 35 of 43 declarations);
  * the COMMIT BOUNDARY is the file GIT RUNS (git rev-parse --git-path: core.hooksPath and the COMMON git dir
    decide it, not this registry) and it must be EXECUTABLE, because git silently skips a hook it may not
    execute (D-2687, the BUG-564 remainder).
It does NOT decide policy and it does NOT read the rails' internals - it reports which invariant has no owner.

Exit: 0 ok | 1 fault(s) | 2 the config itself is unreadable/incomplete (fail closed, C16).
--selftest: known-answer controls over SYNTHETIC ladders (no NLI, no live-tree write, BUG-492).
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import re
import subprocess
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CFG = REPO / "config/rail_registry.yaml"
RAIL_GLOBS = ("check_*.py", "verify_*.py")
RECIPE = re.compile(r"^([A-Za-z0-9_-]+):")
SCRIPT = re.compile(r"((?:scripts|pipeline)/[\w./-]+\.py)")
GUARDS = {"fatal": "exit 1", "tri_state": "[ $? -eq 2 ]"}
INTERPRETERS = ("python3 ", "python ", "bash ", "sh ")


def ladder_invocations(text: str, recipes: list[str]) -> dict[str, str]:
    """Every DECLARING line in the declared recipes -> its command, minus its interpreter and its guard (the KEY).

    The key includes the FLAGS, so a rail's `--selftest` and `--check` are two distinct invocations, and a guard
    declared for one is never silently satisfied by the other.

    T-164/BUG-837: this used to admit ONLY lines beginning `python3`/`python`. A declaration names an invocation,
    and a FATAL rail written `bash scripts/x.sh --check || exit 1` (justfile:136, BUG-526) could therefore not be
    declared at all - the reader would answer a true declaration with "(ii) an invocation the ladder does not
    contain", a FALSE fault, which reads as "this class cannot be pinned" rather than "this class is unpinned".
    Every line is now a candidate except a bare echo (output is not an invocation) and a comment.
    """
    out: dict[str, str] = {}
    name = None
    for line in text.splitlines():
        m = RECIPE.match(line)
        if m and not line.startswith((" ", "\t")):
            name = m.group(1)
            continue
        if name not in recipes or not line.strip() or line.strip().startswith("#"):
            continue
        body = line.strip().lstrip("@")
        if body.startswith("echo "):
            continue
        cmd = body.split("||")[0].strip()
        for prefix in INTERPRETERS:
            if cmd.startswith(prefix):
                cmd = cmd[len(prefix):]
                break
        if cmd:
            out[cmd] = body
    return out


def guard_of(body: str) -> str:
    """The guard class AS THE LADDER WRITES IT - read from the text, never inferred from intent."""
    if "--report-only" in body:
        return "report_only"
    if "exit 1" in body:
        return "fatal"
    if "[ $? -eq 2 ]" in body:
        return "tri_state"
    return "unguarded"


ROUTE = "git-path:"


@dataclasses.dataclass(frozen=True)
class Boundary:
    """The commit boundary AS GIT SEES IT, never as a declaration spells it (D-2687, the BUG-564 remainder).

    Git decides WHICH file to run (core.hooksPath, and the COMMON git dir - a linked worktree's --git-dir is
    not where hooks live), and git decides WHETHER to run it (a hook it may not execute is SKIPPED, silently).
    So a declaration that names a path shape is a claim about a file git may never open: `resolved` is GIT'S
    OWN answer, and `text` / `executable` are the bytes and the MODE at THAT answer.
    """
    declared: str
    resolved: str | None
    text: str | None
    executable: bool


def boundary_faults(cb: dict, b: "Boundary | None") -> list[str]:
    """PURE (ONE reader): is the DECLARED commit boundary the file git actually runs, and may it run?

    The executability requirement is a PROPERTY of the boundary, not a configurable flag - a key here could
    only turn the check OFF, and the subject being declared is git's own behaviour (the D-2686 precedent:
    nothing in config may re-point the audited subject).
    """
    if not cb:
        return []
    faults: list[str] = []
    declared = str(cb.get("path") or "")
    if b is None:
        return ["(i) commit_boundary declares " + (declared or "<nothing>") + " and the ROUTE WAS NEVER RESOLVED: the question 'which file will git run' was never put to git, so every verdict below is a belief about a path rather than a check of the boundary (D-405/BUG-564)"]
    if not declared.startswith(ROUTE):
        faults.append("(i) commit_boundary names " + repr(declared) + ", a PATH SHAPE - not git's own "
                      "answer. MEASURED 2026-09-27: with core.hooksPath set, a DIFFERENT file received the commit "
                      "and " + repr(declared) + " did not exist, so a declaration verified at a path shape can be "
                      "GREEN while the boundary is disarmed. Declare " + ROUTE + "<rel> instead")
    if not b.resolved:
        return faults + ["(i) commit_boundary " + declared + ": git could not resolve the route (git rev-parse --git-path) - a boundary whose path git will not answer for has no verifier (C16)"]
    if b.text is None:
        return faults + ["(i) commit_boundary " + declared + " resolves to " + b.resolved + ", which is NOT A "
                         "READABLE FILE - the commit-time rails have no exerciser at the path git will run (BUG-564)"]
    if not b.executable:
        faults.append("(i) commit_boundary " + b.resolved + " is NOT EXECUTABLE, so git runs NOTHING there: "
                      "MEASURED 2026-09-27, a mode-644 pre-commit is SKIPPED, the commit LANDS (rc=0) and the only "
                      "sign is a `hint:` git documents how to suppress. The strictest gate in the system, "
                      "byte-perfect and inert - class (i) WITH a green verdict (BUG-564)")
    mc = [str(x) for x in (cb.get("must_contain") or [])]
    if not mc:
        faults.append("(i) commit_boundary " + b.resolved + " declares NO must_contain - a claim with no subject")
    for want in mc:
        if want not in b.text:
            faults.append("(i) commit_boundary " + b.resolved + " does NOT contain " + repr(want) + ": the rail the "
                          "registry says runs at COMMIT time would silently not run (BUG-564)")
    return faults


CMD_SHAPED = "/"  # a top-level KEY containing this is a command line, never a section (T-164/BUG-837)


def schema_faults(cfg: dict) -> list[str]:
    """(iv) THE REGISTRY'S OWN SCHEMA IS CLOSED (T-164/BUG-837): a top-level key the file does not declare is a
    declaration the reader never reads, and silence about it is how eight of them lived at column 0 unnoticed.

    The legal SET is read from this file's own schema.keys (C12: no key list in code). Nothing here is optional
    policy: an unknown key means this rail is describing a DIFFERENT file than the one on disk, so the only other
    honest answer would be a refusal to report at all. 'schema' must list itself, which is not a nicety - the
    closure is the thing that must cover its own description, and self-membership is what turns the next stray key
    into a fault instead of a shrug.
    """
    spec = cfg.get("schema")
    if not isinstance(spec, dict) or not spec.get("keys"):
        return ["(iv) the registry declares no schema.keys: the file's own shape is undeclared, so an unknown "
                "top-level key cannot be told from a deliberately new section - the BUG-837 blindness, declared "
                "instead of accidental"]
    keys = [str(k) for k in spec["keys"]]
    faults: list[str] = []
    if "schema" not in keys:
        faults.append("(iv) schema.keys does not list 'schema' ITSELF: a closure that does not cover its own "
                      "description is not a closure (T-164/BUG-837)")
    for key in cfg:
        if CMD_SHAPED in str(key):
            faults.append(f"(iv) top-level key {key!r} is a COMMAND LINE, not a section - the BUG-837 shape "
                          f"(measured 2026-10-15: eight of these were read by nothing and two of them were claims "
                          f"the ladder cannot support). Declare it under guards: if its class must be pinned")
        elif str(key) not in keys:
            faults.append(f"(iv) top-level key {key!r} is not declared in schema.keys - an UNKNOWN SECTION is a "
                          f"declaration this rail never reads, which is exactly the BUG-837 blindness (add it to "
                          f"schema.keys if it is deliberate)")
    return faults


def audit(ladder: str, discovered: list[str], cfg: dict, exists=lambda p: True,
          boundary: "Boundary | None" = None) -> tuple[list[str], dict]:
    """Return (faults, census) for one ladder text, one set of discovered rails, one declaration."""
    inv = ladder_invocations(ladder, [str(r) for r in cfg.get("recipes") or []])
    invoked = {m.group(1) for c in inv if (m := SCRIPT.search(c))}  # a lane may name no .py at all (T-164)
    dormant = cfg.get("dormant") or {}
    writers = cfg.get("writers") or {}
    guards = cfg.get("guards") or {}
    faults: list[str] = schema_faults(cfg)   # (iv): first, because every fault below is about a DIFFERENT FILE if this fails

    # (i) a rail nothing runs - and a dormancy claim whose subject is absent
    for script in sorted(set(discovered) | set(dormant)):
        if script in invoked:
            continue
        d = dormant.get(script)
        if not d:
            faults.append(f"(i) a rail NOTHING RUNS: {script} is invoked by no declared ladder recipe and is "
                          f"declared dormant nowhere - a control that cannot fire (BUG-492)")
            continue
        if script not in discovered:
            faults.append(f"(i) the registry declares dormancy for {script}, which is NOT a rail script on "
                          f"disk - a declaration whose subject is gone (C19)")
        ex = [str(p) for p in (d.get("exercised_by") or [])]
        if not ex:
            faults.append(f"(i) {script} declares dormancy with NOTHING that exercises it")
        for p in ex:
            if not exists(p):
                faults.append(f"(i) {script} is declared dormant, exercised by {p}, which DOES NOT EXIST - an "
                              f"assertion, not a declaration (D-405/BUG-488)")
        if not str(d.get("reason") or "").strip():
            faults.append(f"(i) {script} declares dormancy with no reason")
    for script in dormant:
        if script in invoked:
            faults.append(f"(i) STALE dormancy: {script} is declared dormant and IS invoked by the ladder")

    # COMMIT BOUNDARY (BUG-564/D-2687): a dormancy claim says WHICH file exercises a rail; it cannot say the file
    # still DOES, nor that it is the file GIT RUNS. This hook lives OUTSIDE the synced tree (BUG-500), so no diff
    # would show a deleted line - and no diff would show a deleted EXEC BIT either. Both are settled by ONE pure
    # predicate against git's own answers, fail closed (C16).
    faults.extend(boundary_faults(cfg.get("commit_boundary") or {}, boundary))

    # (ii) a declared guard that disagrees with the ladder's own text
    for key, want in guards.items():
        want = str(want)
        if want not in GUARDS:
            faults.append(f"(ii) guards[{key}] declares {want!r}, which is not one of {sorted(GUARDS)}")
            continue
        body = inv.get(key)
        if body is None:
            faults.append(f"(ii) guards[{key}] declares {want!r} for an invocation the ladder does not contain")
            continue
        got = guard_of(body)
        if got != want:
            faults.append(f"(ii) guards[{key}] declares {want!r} but the ladder runs it {got!r} "
                          f"({GUARDS.get(want)} vs {body.split('||')[-1].strip()!r}) - a printed verdict and an "
                          f"exit code that disagree is a rail the owner learns to ignore (BUG-462)")

    # (iii) a declared WRITER with no known-answer control run BY THE LADDER
    for script, spec in writers.items():
        if script not in invoked:
            faults.append(f"(iii) writers[{script}] writes {spec.get('writes')} but the ladder never runs it")
            continue
        if not str(spec.get("why") or "").strip():
            faults.append(f"(iii) writers[{script}] does not say WHY it writes")
        if f"{script} --selftest" not in inv:
            faults.append(f"(iii) writers[{script}] replaces bytes ({spec.get('writes')}) and the ladder NEVER "
                          f"runs `{script} --selftest`: its remedy is an unproven claim - the BUG-537/BUG-556 class")

    census = {"invocations": len(inv), "rails_invoked": sorted(invoked), "discovered": len(discovered),
              "dormant": sorted(dormant), "writers": sorted(writers),
              "schema_keys": len((cfg.get("schema") or {}).get("keys") or []),
              "guards": {k: guard_of(v) for k, v in inv.items() if k in guards}}
    return faults, census


def load_cfg() -> dict:
    """Fail closed: an unreadable or incomplete registry is never a silent empty set (C16).

    The REQUIRED set is READ from the file's own schema.required (T-164/C12) rather than restated in code, and
    dormant/writers/guards are now among them because the rail's closing sentence asserts something about each: an
    omitted section would make that sentence VACUOUSLY true instead of checked.
    """
    if not CFG.is_file():
        raise SystemExit("FAIL-CLOSED: config/rail_registry.yaml is absent - a registry that decides nothing "
                         "cannot be a registry")
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    spec = cfg.get("schema")
    if not isinstance(spec, dict) or not spec.get("keys") or not spec.get("required"):
        raise SystemExit("FAIL-CLOSED: config/rail_registry.yaml must declare a schema block with keys: and "
                         "required: - a registry with no declared shape can lose a section without saying so "
                         "(T-164/BUG-837)")
    if "schema" not in [str(k) for k in spec["keys"]]:
        raise SystemExit("FAIL-CLOSED: schema.keys must list 'schema' itself (the closure must cover its own "
                         "description)")
    for key in [str(k) for k in spec["required"]]:
        if key not in cfg:
            raise SystemExit(f"FAIL-CLOSED: config/rail_registry.yaml must declare '{key}' (schema.required)")
    return cfg


def discover() -> list[str]:
    out: set[str] = set()
    for g in RAIL_GLOBS:
        for p in sorted((REPO / "scripts").glob(g)):
            out.add(str(p.relative_to(REPO)))
    return sorted(out)


# ------------------------------------------------------------------ controls
def selftest() -> int:
    """Known-answer controls over SYNTHETIC ladders: a registry that never reports a fault is not a registry."""
    schema = {"keys": ["schema", "schema_version", "authority", "ladder", "recipes", "ladder_receipt",
                       "dormant", "writers", "guards", "commit_boundary"],
              "required": ["ladder", "recipes", "dormant", "writers", "guards", "commit_boundary"]}
    base = {"schema": schema, "recipes": ["health"], "ladder": "justfile", "dormant": {}, "writers": {}, "guards": {}}
    ok = fail = 0

    def check(name: str, got: int, want: int, why: str) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
            print(f"  ok   selftest/{name}: {why}")
        else:
            fail += 1
            print(f"  FAIL selftest/{name}: {why} (got {got} fault(s), want {want})")

    L = "health:\n    python3 scripts/check_a.py --check || exit 1\n"
    f, _ = audit(L, ["scripts/check_a.py"], base)
    check("clean_ladder", len(f), 0, "an invoked, declared-clean rail is silent")

    f, _ = audit(L, ["scripts/check_a.py", "scripts/check_orphan.py"], base)
    check("nothing_runs_it", len([x for x in f if "(i)" in x]), 1, "a rail no recipe invokes is reported (i)")

    f, _ = audit(L, [], {**base, "dormant": {"scripts/check_b.py": {"exercised_by": ["nope/absent.yaml"],
                                                                   "reason": "fixture"}}}, exists=lambda p: False)
    check("dormant_exerciser_absent", len([x for x in f if "DOES NOT EXIST" in x]), 1,
          "a dormancy whose exerciser is absent (i)")

    f, _ = audit(L, [], {**base, "dormant": {"scripts/check_a.py": {"exercised_by": ["justfile"],
                                                                   "reason": "fixture"}}})
    check("stale_dormancy", len([x for x in f if "STALE" in x]), 1, "a dormancy that IS invoked is stale (i)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "guards": {"scripts/check_a.py": "tri_state"}})
    check("guard_ladder_disagree", len([x for x in f if "(ii)" in x]), 1, "declared guard != ladder guard (ii)")

    W = ("health:\n    python3 scripts/check_w.py --check || exit 1\n")
    f, _ = audit(W, ["scripts/check_w.py"], {**base, "writers": {"scripts/check_w.py": {"writes": ["x/y.yaml"],
                                                                                      "why": "fixture"}}})
    check("writer_without_selftest", len([x for x in f if "(iii)" in x]), 1, "a declared writer with no ladder --selftest (iii)")

    WS = ("health:\n    python3 scripts/check_w.py --selftest || exit 1\n    python3 scripts/check_w.py --check || exit 1\n")
    f, _ = audit(WS, ["scripts/check_w.py"], {**base, "writers": {"scripts/check_w.py": {"writes": ["x/y.yaml"],
                                                                                        "why": "fixture"}}})
    check("writer_with_selftest", len(f), 0, "a declared writer whose --selftest the ladder runs is clean")

    HB = "#/bin/bash" + chr(10) + "python3 scripts/check_a.py --staged" + chr(10)
    REL = "hooks/pre-commit"
    RES = "/system/temp/rail-registry-fixture/" + REL
    CB = {"path": ROUTE + REL, "must_contain": ["scripts/check_a.py --staged"]}

    def bnd(declared: str = ROUTE + REL, resolved: 'str | None' = RES,
            text: 'str | None' = HB, executable: bool = True) -> Boundary:
        """The boundary FACTS a caller injects: git's answer, and the bytes and mode AT that answer."""
        return Boundary(declared=declared, resolved=resolved, text=text, executable=executable)

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary": CB}, boundary=bnd())
    check("boundary_route_holds_the_declared_line", len(f), 0,
          "git's own answer, executable, holding the declared line is silent (route + mode)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary":
                  {**CB, "must_contain": ["scripts/check_declaration_consumers.py --staged"]}}, boundary=bnd())
    check("boundary_line_deleted", len([x for x in f if "commit_boundary" in x]), 1,
          "a commit-boundary line DELETED from the out-of-tree hook is reported, not trusted (i/BUG-564)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary":
                  {"path": "gitdir:" + REL, "must_contain": CB["must_contain"]}},
                 boundary=bnd(declared="gitdir:" + REL))
    check("boundary_declared_as_a_path_shape", len([x for x in f if "PATH SHAPE" in x]), 1,
          "a boundary declared as a PATH SHAPE is refused: git may run a different file (measured) (BUG-564)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary": CB}, boundary=None)
    check("boundary_route_never_resolved", len([x for x in f if "ROUTE WAS NEVER RESOLVED" in x]), 1,
          "a boundary whose route was never put to git is a belief, not a verification (D-405)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary": CB}, boundary=bnd(resolved=None))
    check("boundary_route_git_cannot_answer", len([x for x in f if "could not resolve" in x]), 1,
          "a route git will not answer for has no verifier (C16)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary": CB}, boundary=bnd(text=None))
    check("boundary_hook_is_absent", len([x for x in f if "NOT A READABLE FILE" in x]), 1,
          "git's answer names no readable file: the commit-time rails have no exerciser")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary": CB}, boundary=bnd(executable=False))
    check("boundary_hook_is_not_executable", len([x for x in f if "NOT EXECUTABLE" in x]), 1,
          "a byte-perfect hook git may not execute runs NOTHING (measured): the gate is inert, not armed")

    # T-164/BUG-837: the registry's OWN schema is closed, and a lane the ladder writes as `bash` is NAMEABLE.
    f, _ = audit(L, ["scripts/check_a.py"], {**base, "orphan_section": {}})
    check("unknown_top_level_section", len([x for x in f if "(iv)" in x]), 1,
          "a top-level key schema.keys does not list is REPORTED - it is a section this rail never reads (BUG-837)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "pipeline/oneshot_ask.py": "tri_state"})
    check("command_line_as_key", len([x for x in f if "(iv)" in x]), 1,
          "the BUG-837 shape itself: a key shaped like a COMMAND LINE is refused ONCE, and refused as a command "
          "line - not as a merely unknown section (which would invite someone to add it to schema.keys)")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "schema": {"keys": ["recipes", "ladder"], "required": ["ladder"]}})
    check("schema_must_list_itself", len([x for x in f if "ITSELF" in x]), 1,
          "schema.keys must cover its own description: a closure that exempts itself is not a closure (BUG-837)")

    BL = "health:" + chr(10) + "    bash scripts/install_x.sh --check || exit 1" + chr(10)
    f, _ = audit(BL, [], {**base, "guards": {"scripts/install_x.sh --check": "fatal"}})
    check("bash_lane_is_nameable", len(f), 0,
          "a rail the ladder writes as bash is a declaration this registry can MAKE (until T-164 it could not)")

    f, _ = audit(BL, [], {**base, "guards": {"scripts/install_x.sh --check": "tri_state"}})
    check("bash_lane_guard_disagrees", len([x for x in f if "(ii)" in x]), 1,
          "a guard declared for a bash lane is still matched against the ladder's own text (class ii)")

    print(f"rail-registry controls: {ok}/{ok + fail} known-answer control(s) fire")
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the RAIL REGISTRY: which invariant has no owner")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over synthetic ladders")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cfg = load_cfg()
    text = (REPO / str(cfg["ladder"])).read_text(encoding="utf-8")
    rails = discover()
    declared = sorted(set(rails) | set(cfg.get("dormant") or {}) | set(cfg.get("writers") or {}))
    gd = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=REPO, capture_output=True, text=True)
    gitdir = pathlib.Path(gd.stdout.strip()).resolve() if gd.returncode == 0 and gd.stdout.strip() else None

    def exists(p: str) -> bool:
        """A declared exerciser must EXIST (C16). `gitdir:<rel>` resolves against THIS repo's git dir: the
        git dir lives outside the synced tree (BUG-500), so a hardcoded `.git/hooks` path would be a lie."""
        if p.startswith("gitdir:"):
            return bool(gitdir) and (gitdir / p.split(":", 1)[1]).exists()
        return (REPO / p).exists()

    def git_answer(rel: str) -> str | None:
        """GIT'S OWN ANSWER to "which file will you run for <rel>?" - the ONE home of the route (D-2687).

        --git-path honours core.hooksPath and the COMMON git dir; --git-dir does not, which is why the
        registry may not answer this question on git's behalf. A relative answer is git's answer RELATIVE TO
        THE CALLER's cwd, so it is resolved here against REPO (the directory the call is made from).
        """
        r = subprocess.run(["git", "rev-parse", "--git-path", rel], cwd=REPO, capture_output=True, text=True)
        ans = r.stdout.strip() if r.returncode == 0 else ""
        if not ans:
            return None
        p = pathlib.Path(ans)
        return str(p if p.is_absolute() else (REPO / p).resolve())

    cb = cfg.get("commit_boundary") or {}
    route = str(cb.get("path") or "")
    boundary = None
    if cb:
        res = git_answer(route.split(":", 1)[1] if route.startswith(ROUTE) else route.split(":", 1)[-1])
        try:
            btext = pathlib.Path(res).read_text(encoding="utf-8") if res else None
        except (OSError, UnicodeDecodeError):
            btext = None
        boundary = Boundary(declared=route, resolved=res, text=btext, executable=bool(res) and os.access(res, os.X_OK))

    faults, census = audit(text, declared, cfg, exists=exists, boundary=boundary)
    print(f"rail registry: {census['invocations']} ladder invocation(s), {len(census['rails_invoked'])} rail(s) "
          f"invoked, {census['discovered']} rail script(s) on disk, {len(census['dormant'])} declared dormant, "
          f"{len(census['writers'])} declared writer(s)")
    for name, g in sorted(census["guards"].items()):
        print(f"  guard {g:11s} {name}")
    if faults:
        print(f"\nFAIL rail registry: {len(faults)} fault(s) - every rail needs an owner for its invariant:")
        for x in faults:
            print("  - " + x)
        return 1
    print("  ok   no rail is unowned: every rail is invoked or declared dormant with an existing exerciser, every "
          "declared writer's remedy is proven by the ladder, no declared guard disagrees with the ladder, the "
          "REGISTRY'S OWN SCHEMA is closed (" + str(census["schema_keys"]) + " declared key(s), no stray "
          "top-level declaration), and the COMMIT BOUNDARY is the file git runs (" + str(boundary.resolved) +
          "), executable, holding every line")
    return 0


if __name__ == "__main__":
    sys.exit(main())
