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
  * a declared `guard:` is matched against the ladder's own text: a disagreement is class (ii), fail closed.
It does NOT decide policy and it does NOT read the rails' internals - it reports which invariant has no owner.

Exit: 0 ok | 1 fault(s) | 2 the config itself is unreadable/incomplete (fail closed, C16).
--selftest: known-answer controls over SYNTHETIC ladders (no NLI, no live-tree write, BUG-492).
"""
from __future__ import annotations

import argparse
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


def ladder_invocations(text: str, recipes: list[str]) -> dict[str, str]:
    """Every python invocation in the declared recipes -> its full command line, minus the guard (the KEY).

    The key includes the FLAGS, so a rail's `--selftest` and `--check` are two distinct invocations, and a guard
    declared for one is never silently satisfied by the other.
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
        if not body.startswith(("python3 ", "python ")):
            continue
        cmd = re.sub(r"^python3? ", "", body.split("||")[0].strip())
        s = SCRIPT.search(cmd)
        if s:
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


def audit(ladder: str, discovered: list[str], cfg: dict, exists=lambda p: True,
          read=lambda p: None) -> tuple[list[str], dict]:
    """Return (faults, census) for one ladder text, one set of discovered rails, one declaration."""
    inv = ladder_invocations(ladder, [str(r) for r in cfg.get("recipes") or []])
    invoked = {SCRIPT.search(c).group(1) for c in inv}  # type: ignore[union-attr]
    dormant = cfg.get("dormant") or {}
    writers = cfg.get("writers") or {}
    guards = cfg.get("guards") or {}
    faults: list[str] = []

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

    # COMMIT BOUNDARY (BUG-564): a dormancy claim says WHICH file exercises a rail; it cannot say the file still
    # DOES. This hook lives OUTSIDE the synced tree (BUG-500), so no diff would show a deleted line: its required
    # text is a declaration here, verified against the bytes on disk, fail closed (C16).
    cb = cfg.get("commit_boundary") or {}
    if cb:
        bp = str(cb.get("path") or "")
        btext = read(bp) if bp else None
        mc = [str(x) for x in (cb.get("must_contain") or [])]
        if not bp or btext is None:
            faults.append("(i) commit_boundary declares " + (bp or "<nothing>") + ", which is not a readable file - the "
                          "commit-time rails would have no verifiable exerciser (C16/BUG-564)")
        elif not mc:
            faults.append("(i) commit_boundary " + bp + " declares NO must_contain - a claim with no subject")
        else:
            for want in mc:
                if want not in btext:
                    faults.append("(i) commit_boundary " + bp + " does NOT contain " + repr(want) + ": the rail the "
                                  "registry says runs at COMMIT time would silently not run (BUG-564)")

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
              "guards": {k: guard_of(v) for k, v in inv.items() if SCRIPT.search(k) and
                         SCRIPT.search(k).group(1) in guards}}
    return faults, census


def load_cfg() -> dict:
    """Fail closed: an unreadable or incomplete registry is never a silent empty set (C16)."""
    if not CFG.is_file():
        raise SystemExit("FAIL-CLOSED: config/rail_registry.yaml is absent - a registry that decides nothing "
                         "cannot be a registry")
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    for key in ("ladder", "recipes", "dormant"):
        if key not in cfg:
            raise SystemExit(f"FAIL-CLOSED: config/rail_registry.yaml must declare '{key}'")
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
    base = {"recipes": ["health"], "ladder": "justfile", "dormant": {}}
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
    b2 = {**base, "commit_boundary": {"path": "gitdir:hooks/pre-commit",
                                      "must_contain": ["scripts/check_a.py --staged"]}}
    f, _ = audit(L, ["scripts/check_a.py"], b2, read=lambda p: HB)
    check("boundary_line_present", len(f), 0, "a declared commit-boundary line that IS in the file is silent")

    f, _ = audit(L, ["scripts/check_a.py"], {**base, "commit_boundary": {"path": "gitdir:hooks/pre-commit",
                "must_contain": ["scripts/check_declaration_consumers.py --staged"]}}, read=lambda p: HB)
    check("boundary_line_deleted", len([x for x in f if "commit_boundary" in x]), 1,
          "a commit-boundary line DELETED from the out-of-tree hook is reported, not trusted (i/BUG-564)")

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

    def readx(p: str) -> str | None:
        """The declared exerciser's TEXT: gitdir:<rel> resolves against THIS repo's out-of-tree git dir (BUG-500)."""
        if p.startswith("gitdir:"):
            if not gitdir:
                return None
            q = gitdir / p.split(":", 1)[1]
        else:
            q = REPO / p
        try:
            return q.read_text(encoding="utf-8")
        except OSError:
            return None

    faults, census = audit(text, declared, cfg, exists=exists, read=readx)
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
          "declared writer's remedy is proven by the ladder, and no declared guard disagrees with the ladder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
