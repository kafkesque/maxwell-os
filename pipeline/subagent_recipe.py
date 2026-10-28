#!/usr/bin/env python3
"""subagent_recipe.py - THE RUNNER for the DECLARED sub-agent recipe vocabulary.

WHY THIS EXISTS (measured, not asserted). Delegation here is frequent and expensive, and the answer to "may this
loop run with NO human in it?" was living in prose - the shape of a chat message. A recipe is now a DECLARED
triple: what the answer must CONTAIN (a shape the grader can read), WHICH AXIS model it is for (a pointer into
config/model_assignments.yaml#harness_roles, never a model name typed here), and a DONE CHECK: a deterministic
command whose exit code says whether the loop finished.

T-219 (BUG-1090/D-3210) added the FOURTH term, because the model alone was half a declaration: a role that declares
`class:` + `mode:` + `not_a_loop:` is resolved HERE WITH ITS CLASS, and a recipe that names such a role must say
which class it is running it in (`run_class:`) or be REFUSED. MEASURED 2026-10-28: `AGENT_EDIT_LONG_CONTEXT` is
gpt-oss-20b at the 600 s `agent_probe` class because a 26,214-token turn costs 124.83 s of prefill - more than any
loop class pays - so the same role is payable as a one-shot and unpayable as a loop. That difference used to live
only in prose; now it is a refusal that names the class that pays.

THE ONE RULE, ENFORCED HERE AND NOT MERELY WRITTEN DOWN: a loop may run with no human only when its done_check is
a command that RESOLVES. An LLM judging an LLM is not a verifier (R5), so a recipe that declares human_free: true
while its done_check is null is REFUSED, loudly (C16) - and the refusal NAMES what is missing, so the recipe
cannot quietly keep its claim.

The recipes themselves live in config/engine.yaml#fanout.task_recipes (C12: one home, not a second list here).
This runner RENDERS one recipe into a fan-out task file and prints the exact commands to run it; it starts
nothing itself, because a runner that starts a model run must also be the thing that can be told to stop.

Usage:
  python3 pipeline/subagent_recipe.py --list
  python3 pipeline/subagent_recipe.py --plan NAME [--set key=value ...]
  python3 pipeline/subagent_recipe.py --selftest
Exit: 0 ok | 1 FATAL (a recipe that does not RESOLVE, C12/C16) | --selftest 0/1.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENGINE = ROOT / "config/engine.yaml"
ASSIGNMENTS = ROOT / "config/model_assignments.yaml"

def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Read one declared YAML file (the repository's own idiom: a local import, no helper invented)."""
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

PLACEHOLDERS = ("target", "question", "run", "model", "out", "answer", "file")


def recipes() -> dict[str, dict[str, Any]]:
    """Every DECLARED recipe. Malformed is FATAL, never defaulted (C12/C16)."""
    block = (_yaml(ENGINE).get("fanout") or {}).get("task_recipes")
    if not isinstance(block, dict) or not block:
        raise SystemExit("FATAL: config/engine.yaml#fanout.task_recipes is absent or malformed - refusing to "
                         "read a recipe out of a declaration that is not there (C12/C16)")
    return block


def declared_shapes() -> list[str]:
    """The shape vocabulary, from its one home."""
    return sorted(((_yaml(ENGINE).get("fanout") or {}).get("answer_shapes") or {}).keys())


def _harness_roles() -> dict[str, Any]:
    """`harness_roles` from its one home, or FATAL (C12/C16: a role set that cannot be read refuses nothing)."""
    roles = _yaml(ASSIGNMENTS).get("harness_roles")
    if not isinstance(roles, dict) or not roles:
        raise SystemExit("FATAL: config/model_assignments.yaml#harness_roles is absent or malformed - a role "
                         "reader with nothing to read cannot refuse a caller (C12/C16)")
    return roles


def role_class(role: str) -> "str | None":
    """The BUDGET CLASS a role is declared to run as, or None when its declaration makes no such claim (T-219).

    T-219 (BUG-1090/D-3210): `class:`, `mode:` and `not_a_loop:` sat beside the model as annotations NO READER
    resolved, so a role's re-bind was enforced as a MODEL and unenforced as a BUDGET - and any caller could run a
    26,214-token role as an interactive loop that no served model can pay. A declaration whose subject is absent is
    an assertion, not a control (D-3034); this is the reader that gives it a subject.
    """
    spec = _harness_roles().get(role)
    declared = spec.get("class") if isinstance(spec, dict) else None
    return str(declared) if declared else None


def role_model(role: str, cls: "str | None" = None) -> str:
    """The model ONE axis resolves to. An unknown role is FATAL: a recipe must not name a model of its own.

    AND SO IS A CLASS THE ROLE'S OWN DECLARATION FORBIDS. A role that declares `class: agent_probe` (with `mode:
    oneshot`) is payable ONLY there; asking it for another class - or for no class at all - is REFUSED, and the
    refusal names the class that pays the bill and quotes the measured reason. A role that declares no class is
    never refused: a guard that fires on every honest caller is noise, and noise is how a rail gets switched off
    (BUG-492). Known answers are the live pair in `--selftest` (T-219's gate).
    """
    roles = _harness_roles()
    spec = roles.get(role)
    if not isinstance(spec, dict) or not spec.get("model"):
        raise SystemExit(f"FATAL: role {role!r} is not a model-bearing role in "
                         f"config/model_assignments.yaml#harness_roles (declared: {sorted(roles)})")
    declared = role_class(role)
    if declared and cls != declared:
        asked = repr(cls) if cls else "no class at all"
        raise SystemExit(f"REFUSED: role {role!r} runs as class {declared!r} (mode {spec.get('mode')!r}) and was "
                         f"asked for {asked}. {spec.get('not_a_loop') or ''} A role's class is not decoration - it "
                         f"is the budget that PAYS the role's prefill bill, so the model and the class are two "
                         f"halves of ONE declaration (T-219/D-3210/BUG-1090). Run it as {declared!r}, or re-bind "
                         f"the role by decision.")
    return str(spec["model"])


def check_command(command: str) -> list[str]:
    """Refuse a done_check that cannot RESOLVE: 'python3 <path> ...' whose <path> must EXIST (D-3034)."""
    parts = command.split()
    script = next((p for p in parts if p.endswith(".py")), "")
    if not script:
        raise SystemExit(f"FATAL: done_check {command!r} names no .py entrypoint - a done check must be a command "
                         "this repository can run (C16)")
    path = ROOT / script
    if not path.exists():
        raise SystemExit(f"FATAL: done_check {command!r} names {script}, which does NOT exist - the decider of a "
                         "loop cannot be a promise (D-3034/C16)")
    return parts


def resolve(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    """VALIDATE one recipe and return what it resolved to - the whole reason this file exists."""
    shape = spec.get("shape") or ""
    if shape and shape not in declared_shapes():
        raise SystemExit(f"FATAL: recipe {name!r} declares shape {shape!r}, which is not in "
                         f"config/engine.yaml#fanout.answer_shapes ({declared_shapes()})")
    human_free = bool(spec.get("human_free"))
    done = spec.get("done_check") or ""
    model = ""
    run_class = spec.get("run_class")
    if spec.get("model_role"):
        # T-219: the class travels WITH the resolution, so a recipe cannot name a role and leave its budget
        # unstated - the one act that used to be possible and unpayable.
        model = role_model(str(spec["model_role"]), str(run_class) if run_class else None)
    if human_free and not done:
        raise SystemExit(f"REFUSED: recipe {name!r} declares human_free: true with NO done_check. An LLM judging "
                         f"an LLM is not a verifier (R5). Owed: {spec.get('owed') or 'a deterministic decider'}")
    if done:
        check_command(str(done))
    return {"shape": shape or None, "model_role": spec.get("model_role"), "model": model or None,
            "run_class": run_class or None,
            "human_free": human_free, "done_check": done or None, "owed": spec.get("owed") or None}


def render(name: str, spec: dict[str, Any], values: dict[str, str], stamp: str) -> pathlib.Path:
    """Write ONE fan-out task file (the schema pipeline/subagent_fanout.py documents) and return its path."""
    question = str(spec["question"])
    for key in PLACEHOLDERS:
        question = question.replace("{" + key + "}", values.get(key, "{" + key + "}"))
    unresolved = [k for k in PLACEHOLDERS if "{" + k + "}" in question]
    if unresolved:
        raise SystemExit(f"FATAL: recipe {name!r} left {unresolved} unset - pass them with --set key=value "
                         "(a template with a hole is a prompt with a hole)")
    task = {"id": name, "model": values.get("model") or spec.get("model_role")
            and role_model(str(spec["model_role"]), str(spec["run_class"]) if spec.get("run_class") else None) or "",
            "question": question, "mode": spec.get("mode", "oneshot"),
            "max_tokens": int(spec.get("max_tokens", 600)), "files": [values.get("target", "")] if values.get("target") else []}
    if spec.get("shape"):
        task["shape"] = spec["shape"]
    if spec.get("timeout_s"):
        task["timeout_s"] = int(spec["timeout_s"])
    run = f"recipe_{name}_{stamp}"
    directory = ROOT / "temp" / run
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / "tasks.yaml"
    out.write_text(json.dumps([task], indent=2) + "\n", encoding="utf-8")
    print(f"task file {out}\nnext (starts nothing by itself):\n"
          f"  python3 pipeline/subagent_fanout.py doctor --tasks {out}\n"
          f"  python3 pipeline/subagent_fanout.py run --tasks {out} --run {run}")
    return out


def selftest() -> int:
    """Known-answer controls on the RESOLVER (pure: the real config is read, but nothing is planned or run)."""
    bad: list[str] = []
    ok = resolve("review-artifact", dict(recipes()["review-artifact"]))
    if not ok["done_check"]:
        bad.append("the declared review-artifact recipe resolved with no done_check")
    for label, spec, want in (
            ("human_free with no done_check is REFUSED",
             {"question": "q", "human_free": True, "done_check": ""}, "human_free"),
            ("an undeclared shape is REFUSED",
             {"question": "q", "human_free": False, "shape": "not-a-declared-shape"}, "shape"),
            ("an unknown model role is REFUSED",
             {"question": "q", "human_free": False, "model_role": "NO_SUCH_ROLE"}, "role"),
            ("a done_check naming a missing file is REFUSED",
             {"question": "q", "human_free": True, "done_check": "python3 scripts/no_such_script_xyz.py"}, "done_check")):
        try:
            resolve(label, spec)
            bad.append(f"{label}: accepted")
        except SystemExit as exc:
            if want not in str(exc):
                bad.append(f"{label}: refused for the wrong reason: {exc}")
    # ── T-219's GATE: the LIVE pair, plus the inverse that keeps the guard from firing on every honest caller ──
    # (1) the annotated role asked for a LOOP class must be REFUSED - this is the BUG-1090 defect itself: a
    #     26,214-token role run as an interactive loop is unpayable by ANY served model, and until this reader
    #     existed nothing refused it.
    try:
        role_model("AGENT_EDIT_LONG_CONTEXT", "agent_loop")
        bad.append("T-219: the annotated role was ACCEPTED as agent_loop - the class is decoration again")
    except SystemExit as exc:
        if "agent_probe" not in str(exc):
            bad.append(f"T-219: refused for the wrong reason (it must NAME the payable class): {exc}")
    # (2) the SAME role asked for the class it declares must be ALLOWED - a guard that cannot pass a lawful
    #     request is a wall, not a guard.
    try:
        if role_model("AGENT_EDIT_LONG_CONTEXT", "agent_probe") != "gpt-oss-20b-MXFP4-Q8":
            bad.append("T-219: the lawful class resolved to the wrong model")
    except SystemExit as exc:
        bad.append(f"T-219: the role's OWN declared class was refused: {exc}")
    # (3) a role that declares NO class is never refused, whatever it is asked for (the inverse).
    try:
        role_model("AGENT_LOOP_SHORT")
        role_model("AGENT_LOOP_SHORT", "agent_probe")
    except SystemExit as exc:
        bad.append(f"T-219: an unannotated role was refused - a guard that fires on every honest caller is noise: "
                   f"{exc}")
    total = 5 + 3
    for problem in bad:
        print(f"  FAIL control: {problem}")
    print(f"{'OK' if not bad else 'FAILED'} subagent-recipe controls: {total - len(bad)}/{total} known-answer")
    return 1 if bad else 0


def main() -> int:
    """--list | --plan NAME | --selftest. Nothing here starts a model run."""
    parser = argparse.ArgumentParser(description="the declared sub-agent recipe vocabulary")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--plan", default="")
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    declared = recipes()
    if args.list or not args.plan:
        print(f"{len(declared)} declared recipe(s) - config/engine.yaml#fanout.task_recipes")
        for name, spec in declared.items():
            resolved = resolve(name, spec)
            print(f"  {name:22} human_free={str(resolved['human_free']):5} shape={str(resolved['shape']):7} "
                  f"model={str(resolved['model'] or '-'):38} done={resolved['done_check'] or 'OWED: ' + str(resolved['owed'])}")
        return 0
    if args.plan not in declared:
        print(f"FATAL: {args.plan!r} is not declared (declared: {sorted(declared)})", file=sys.stderr)
        return 1
    values = dict(pair.split("=", 1) for pair in args.set if "=" in pair)
    render(args.plan, declared[args.plan], values, time.strftime("%Y%m%d%H%M%S"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
