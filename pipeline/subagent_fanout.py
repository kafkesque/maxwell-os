#!/usr/bin/env python3
"""Fan independent sub-tasks out to local models - the parallel-delegation executor.

THE PROBLEM IT SOLVES
    "Delegate in parallel to the most reliable local model" fails in two ways today: an in-session
    subagent is cancelled by the next user message (BUG-809), and the ENGINE POOL is serial
    (8 served / 46.88 GB / 55 GB guard, BUG-803), so more concurrency past a small cap makes the
    whole machine slower and less repeatable. This executor therefore: partitions by ARTEFACT (each
    task reads its own files and writes its OWN answer file), runs every task as a DETACHED
    workstream through pipeline/research_run.py, and caps concurrency at engine.fanout.max_parallel.

WHAT A TASK IS (one question, one artefact, one file)
    tasks:
      - id: t1                       # a slug; the workstream name is fan_<id>
        model: gemma-4-E4B-it-MLX-4bit
        question: "Which function decides a workstream's state, and on which line?"
        files: [pipeline/research_run.py]
        mode: oneshot                # oneshot = one deterministic curl (temp 0.0, no tools)
                                     # agent   = goose run -t, which HAS tools (slower, less predictable)
        max_tokens: 400
    Synthesis is NOT automatic: after every task is TERMINAL, --verify runs ONE extra cross-family
    pass (R5) over the collected answers, so the generator is never its own checker.

USAGE
    python3 pipeline/subagent_fanout.py plan   --tasks TASKS.yaml --run ID
    python3 pipeline/subagent_fanout.py start  --run ID
    python3 pipeline/subagent_fanout.py status --run ID
    python3 pipeline/subagent_fanout.py verify --run ID --model M --out SYNTH.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "temp" / "runs"
RUNNER = ROOT / "pipeline" / "research_run.py"
OK, FATAL, PENDING = 0, 1, 2


def conf() -> dict:
    """Engine + fan-out facts from their one home (C12)."""
    import yaml
    return yaml.safe_load((ROOT / "config" / "engine.yaml").read_text())


def plan(tasks_file: pathlib.Path, run_id: str) -> int:
    """Validate a task file and write one command file per task (artefact-partitioned)."""
    import yaml
    doc = yaml.safe_load(tasks_file.read_text()) or {}
    tasks = doc.get("tasks") or []
    if not tasks:
        print("FATAL: the task file declares no tasks")
        return FATAL
    cap = int(conf().get("fanout", {}).get("excerpt_bytes", 24000))
    subprocess.run([sys.executable, str(RUNNER), "new", "--run", run_id,
                    "--brief-text", tasks_file.read_text()], check=True)
    for t in tasks:
        wid = str(t["id"])
        wsd = RUNS / run_id / f"fan_{wid}"
        wsd.mkdir(parents=True, exist_ok=True)
        prompt = [str(t.get("question", "")).strip()]
        for f in t.get("files", []):
            p = ROOT / f
            if not p.exists():
                prompt.append(f"\n### {f}\n(file absent - say so, do not guess)")
                continue
            text = p.read_text(errors="replace")[:cap]
            prompt.append(f"\n### {f}\n{text}")
        prompt.append("\nAnswer in <=12 lines. Cite file:line where it helps. If the files do not "
                      "contain the answer, say NO EVIDENCE rather than guessing.")
        (wsd / "00_prompt.txt").write_text("\n".join(prompt))
        if str(t.get("mode", "oneshot")) == "agent":
            cmd = (f'GOOSE=$(command -v goose || echo /Applications/Goose.app/Contents/Resources/bin/goose)\n'
                   f'"$GOOSE" run -t "$(cat "$WS_DIR/00_prompt.txt")" > "$WS_DIR/20_answer.md" 2>&1\n'
                   f'echo "TERMINAL: DONE - agent task rc=$?" >> "$WS_REPORT"\n')
        else:
            mt = int(t.get("max_tokens", conf().get("fanout", {}).get("default_max_tokens", 512)))
            cmd = (f'python3 pipeline/oneshot_ask.py --model {t["model"]} --prompt-file "$WS_DIR/00_prompt.txt" '
                   f'--max-tokens {mt} --out "$WS_DIR/20_answer.md" --json-out "$WS_DIR/21_meta.json" '
                   f'>> "$WS_REPORT" 2>&1\n'
                   f'echo "TERMINAL: DONE - oneshot rc=$?" >> "$WS_REPORT"\n')
        (wsd / "cmd.sh").write_text(cmd)
    print(f"planned {len(tasks)} task(s) for run {run_id}")
    return OK


def start(run_id: str) -> int:
    """Start tasks with the DECLARED concurrency cap; the rest wait their turn."""
    cap = int(conf().get("fanout", {}).get("max_parallel", 3))
    tasks = sorted([p for p in (RUNS / run_id).glob("fan_*") if p.is_dir()])
    started, waiting = 0, []
    for t in tasks:
        state = {}
        sp = t / "state.json"
        if sp.exists():
            state = json.loads(sp.read_text())
        if state.get("state") in ("RUNNING", "DONE", "FAILED", "TIMEOUT"):
            continue
        if started >= cap:
            waiting.append(t.name)
            continue
        subprocess.run([sys.executable, str(RUNNER), "start", "--run", run_id, "--ws", t.name,
                        "--timeout", "900", "--cmd-file", str(t / "cmd.sh")], check=True)
        started += 1
    if waiting:
        print(f"started {started}; {len(waiting)} waiting on the declared cap of {cap}: {waiting}")
        print("re-run 'start' after the running ones are terminal (the cap protects the pool)")
    else:
        print(f"started {started} (cap {cap})")
    return OK


def verify(run_id: str, model: str, out: pathlib.Path) -> int:
    """Cross-family check of the collected answers (R5): the generator never checks itself."""
    answers = []
    for t in sorted((RUNS / run_id).glob("fan_*")):
        a = t / "20_answer.md"
        if a.exists():
            answers.append(f"## {t.name}\n{a.read_text(errors='replace')[:4000]}")
    if not answers:
        print("FATAL: no answers to verify")
        return FATAL
    prompt = ("You are the VERIFIER, not the author. Below are independent answers produced by other "
              "models. For each: state whether it answers its question, quote the strongest evidence, "
              "and name any claim that the cited file would contradict. End with a table "
              "(task | verdict | one-line reason).\n\n" + "\n\n".join(answers))
    tmp = RUNS / run_id / "99_verify_prompt.txt"
    tmp.write_text(prompt)
    rc = subprocess.run([sys.executable, str(ROOT / "pipeline" / "oneshot_ask.py"), "--model", model,
                         "--prompt-file", str(tmp), "--max-tokens", "1200", "--out", str(out)],
                        cwd=str(ROOT)).returncode
    print("verify: " + ("ok" if rc == 0 else "FAILED") + f" -> {out}")
    return rc


def main(argv: list[str]) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="verb")
    p = sub.add_parser("plan"); p.add_argument("--tasks", required=True); p.add_argument("--run", required=True)
    for verb in ("start", "status"):
        q = sub.add_parser(verb); q.add_argument("--run", required=True)
    v = sub.add_parser("verify"); v.add_argument("--run", required=True)
    v.add_argument("--model", required=True); v.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.verb == "plan":
        return plan(pathlib.Path(args.tasks), args.run)
    if args.verb == "start":
        return start(args.run)
    if args.verb == "status":
        return subprocess.run([sys.executable, str(RUNNER), "status", "--run", args.run], cwd=str(ROOT)).returncode
    if args.verb == "verify":
        return verify(args.run, args.model, pathlib.Path(args.out))
    ap.print_help()
    return FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
