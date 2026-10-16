#!/usr/bin/env python3
"""subagent_recipe.py - THE RUNNER for the DECLARED sub-agent recipe vocabulary.

WHY THIS EXISTS (measured, not asserted). Delegation here is frequent and expensive, and the answer to "may this
loop run with NO human in it?" was living in prose - the shape of a chat message. A recipe is now a DECLARED
triple: what the answer must CONTAIN (a shape the grader can read), WHICH AXIS model it is for (a pointer into
config/model_assignments.yaml#harness_roles, never a model name typed here), and a DONE CHECK: a deterministic
command whose exit code says whether the loop finished.

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


def role_model(role: str) -> str:
    """The model ONE axis resolves to. An unknown role is FATAL: a recipe must not name a model of its own."""
    roles = _yaml(ASSIGNMENTS).get("harness_roles") or {}
    spec = roles.get(role)
    if not isinstance(spec, dict) or not spec.get("model"):
        raise SystemExit(f"FATAL: role {role!r} is not a model-bearing role in "
                         f"config/model_assignments.yaml#harness_roles (declared: {sorted(roles)})")
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
    if spec.get("model_role"):
        model = role_model(str(spec["model_role"]))
    if human_free and not done:
        raise SystemExit(f"REFUSED: recipe {name!r} declares human_free: true with NO done_check. An LLM judging "
                         f"an LLM is not a verifier (R5). Owed: {spec.get('owed') or 'a deterministic decider'}")
    if done:
        check_command(str(done))
    return {"shape": shape or None, "model_role": spec.get("model_role"), "model": model or None,
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
    task = {"id": name, "model": values.get("model") or spec.get("model_role") and role_model(str(spec["model_role"])) or "",
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
    for problem in bad:
        print(f"  FAIL control: {problem}")
    print(f"{'OK' if not bad else 'FAILED'} subagent-recipe controls: {5 - len(bad)}/5 known-answer")
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
