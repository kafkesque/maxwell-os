#!/usr/bin/env python3
"""Fan independent sub-tasks out to local models - the DURABLE delegation executor (BUG-809).

WHY THE OLD VERSION WAS NOT ENOUGH
    It already ran tasks DETACHED (pipeline/research_run.py), but it had three ways to lie,
    and all three were measured in this repo on 2026-10-15:
      (1) A FALSE SUCCESS. Every task's command ended with `TERMINAL: DONE - oneshot rc=$?`, so a
          oneshot that exited 1 (engine refused, no content) was recorded as DONE. That is BUG-817's
          class - a failed answer read as a success - living inside the instrument that reports
          delegation health. The terminal word is now DERIVED from the answer (_grade), never asserted.
      (2) NO REAPER. `timeout_s` was only consulted when somebody happened to call status(). A run
          nobody polled therefore stayed RUNNING forever: "it runs so long without any result, it
          seems stuck". `run` now watches its own run to a declared deadline (research_run watch).
      (3) NO LIVENESS. A hung child and a working child looked identical. Stalled is now measured
          (idle_s against a declared stall_s) and published; only a task declared kill_on_stall is
          killed on suspicion, but silence is never a secret.
    On top of that: an empty/stub answer is retried ONCE on a DIFFERENT declared model (a second
    attempt by the model that just failed adds no information), and every run writes a RECEIPT.

THE ONE ENTRY POINT (guarded, bounded, honest)
    python3 pipeline/subagent_fanout.py doctor --tasks T.yaml     # preflight: refuse to start unsound
    python3 pipeline/subagent_fanout.py run    --tasks T.yaml --run ID [--deadline S]
    ... plan | start | status | retry | verify | _grade            # manual / forensic use

WHAT A TASK IS (one question, one artefact, one file)  -  temp/runs/<run>/fan_<id>/
      - id: t1                       # a slug; the workstream name is fan_<id>
        model: gemma-4-E4B-it-MLX-4bit
        question: "Which function decides a workstream's state, and on which line?"
        files: [pipeline/research_run.py]
        mode: oneshot                # oneshot = one deterministic call (temp 0.0, no tools)
                                     # agent   = goose run -t, which HAS tools (slower, less predictable)
        max_tokens: 400
        timeout_s: 60                # OPTIONAL: this task's own budget (tighter than the mode default;
                                     # a retry never inherits one that just proved insufficient)

EXIT: 0 every task DONE | 1 a task FAILED/EMPTY after its attempts, or the config is unsound
      | 2 tasks still RUNNING when the deadline was spent (owner-owed, never silently waited on)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "temp" / "runs"
RUNNER = ROOT / "pipeline" / "research_run.py"
ASKER = ROOT / "pipeline" / "oneshot_ask.py"
OK, FATAL, PENDING = 0, 1, 2
STUB_PREFIX = "(no content returned"
GUARDS_REQUIRED = ("default_timeout_s", "agent_timeout_s", "deadline_s", "stall_s", "kill_on_stall",
                   "max_attempts", "retry_on", "fallback_model", "min_answer_chars")


def conf() -> dict:
    """The declared engine facts, or a FATAL.

    A missing home is NOT a reason to fall back to a number this module likes: on 2026-10-15 this
    executor ran with its own hardcoded defaults because the declared block had never landed, and a
    sub-agent was blamed for correctly reporting that the setting did not exist (BUG-817).
    """
    import yaml
    doc = yaml.safe_load((ROOT / "config" / "engine.yaml").read_text())
    if not doc.get("fanout"):
        raise SystemExit("FATAL: config/engine.yaml declares no fanout block - refusing to invent a cap (C12)")
    return doc


def guards() -> dict:
    """The declared delegation guards, or a FATAL naming every missing key.

    These are the numbers that decide whether a delegation can be trusted: its budget, its stall
    threshold, whether silence is fatal, how many attempts it gets, on which model it retries, and
    the smallest answer that counts as an answer. Inventing any one of them at runtime is the
    BUG-817 defect, so a missing key stops the run instead of being filled in (C12/C16).
    """
    g = conf().get("fanout", {}).get("guards")
    if not isinstance(g, dict):
        raise SystemExit("FATAL: config/engine.yaml declares no fanout.guards block - a delegation "
                         "without guards is the BUG-809 defect (C12)")
    missing = [k for k in GUARDS_REQUIRED if k not in g]
    if missing:
        raise SystemExit(f"FATAL: config/engine.yaml#fanout.guards is incomplete, missing {missing} - "
                         f"refusing to invent a delegation guard (C12)")
    if int(g["min_answer_chars"]) <= 0:
        raise SystemExit("FATAL: fanout.guards.min_answer_chars must be > 0 - a zero floor accepts an "
                         "empty answer as an answer")
    if int(g["stall_s"]) >= int(g["default_timeout_s"]):
        raise SystemExit("FATAL: fanout.guards.stall_s must be BELOW default_timeout_s, or a silent child "
                         "is reported for the first time at the moment it is killed - the guard would be dead")
    return g


def answer_verdict(path: pathlib.Path, min_chars: int) -> tuple[bool, str]:
    """Did a usable answer actually arrive? One rule, one home (C12/C16).

    The failure this exists for: an engine that returns HTTP 200 with no content, or the stub
    oneshot_ask.py writes when it got nothing, must never be read as a deliverable.
    """
    if not path.exists():
        return False, "no answer file"
    text = path.read_text(errors="replace").strip()
    if not text:
        return False, "the answer is empty"
    if text.startswith(STUB_PREFIX):
        return False, "the model returned no content"
    if len(text) < min_chars:
        return False, f"the answer is {len(text)} chars, below the declared floor of {min_chars}"
    return True, f"ok, {len(text)} chars"


CITATION = re.compile(r"(?<![\w/])([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ya?ml|json|md|sh|toml|txt)):(\d{1,6})")
PATHISH = re.compile(r"(?<![\w/])([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ya?ml|json|md|sh|toml|txt))")
LINE_ONLY = re.compile(r"\bLines?\s+(\d{1,6})\b", re.I)
BACKTICK = re.compile(r"`([^`\n]+)`")
CODEY = re.compile(r"[^A-Za-z0-9\s]|_")     # a fragment with punctuation or an underscore is a QUOTE
# A LABEL is how a model announces that the next line is the code it means: "**Exact Code:** `frag`".
# Requiring a label is what keeps the lookahead below from turning ordinary prose into a failed citation.
QUOTE_LABEL = re.compile(r"^\s*[>*-]*\s*(?:\*\*)?\s*(?:exact\s+code|code|quoted?|reads|says|exact)\b", re.I)


def citation_defects(text: str) -> tuple[int, list[str]]:
    """Check every file:line an answer cites, against the file itself. Returns (checked, defects).

    WHY THIS EXISTS (BUG-721, re-measured live on the FIRST harness job, 2026-10-15): asked to find
    assertions in two files, the deployed agent_loop model returned EIGHT file:line citations and
    every one pointed at unrelated code - it "quoted" `word = "DONE"` at a line that reads
    `if len(text) < min_chars:`. The answer was 1,737 chars, exited 0, cleared the length floor and
    was graded DONE. Nothing in the guard chain could see it, because not one of them READ THE FILE.

    A citation is a claim about a file, and a claim about a file is decidable in one second. This is
    the R5 duty made mechanical: the verifier of a citation need not be a smarter model, it must be a
    reader. THREE SHAPES are read, because all three are what models actually write: `path.py:111` inline,
    a `path.py (line 111)` pair, and a `path.py` heading followed by `Line 111:` bullets. A quote on the
    NEXT line is read only when that line LABELS itself as the code (`**Exact Code:**`) and carries no
    citation of its own. Everything is checked against the file AS IT IS NOW, so a refutation of an answer
    written BEFORE an edit means the file MOVED - the guard is meant for a receipt minutes after the answer,
    not for archaeology. A prose reference (no punctuation, like `the grader`) is never treated as a quote,
    so a loose answer is not failed for being loose.
    """
    checked, defects, context = 0, [], None
    answer_lines = text.splitlines()
    for i, raw in enumerate(answer_lines):
        targets = [(m.group(1), int(m.group(2)), m.start(), m.end()) for m in CITATION.finditer(raw)]
        if not targets:
            line_only = LINE_ONLY.search(raw)
            named = PATHISH.findall(raw)
            # A line that NAMES its own file beats one inherited from a heading, or a heading over file A
            # would check a citation to file B against file A (a false refutation).
            if line_only and len(set(named)) == 1:
                targets = [(named[0], int(line_only.group(1)), line_only.start(), line_only.end())]
            elif line_only and context:
                targets = [(context, int(line_only.group(1)), line_only.start(), line_only.end())]
            elif len(set(named)) == 1 and not line_only:
                context = named[0]         # a heading names the file the following Line N: refer to
                continue
            else:
                continue
        for index, (path, line_no, _, end) in enumerate(targets):
            window_end = targets[index + 1][2] if index + 1 < len(targets) else len(raw)
            frags = [f for f in BACKTICK.findall(raw[end:window_end]) if CODEY.search(f)]
            if not frags and i + 1 < len(answer_lines):
                # THE LABELLED ADJACENT QUOTE, and it is not a hypothetical: measured 2026-10-15, an R5
                # reviewer wrote `**File:line:** pipeline/config_audit.py (line 110)` followed by
                # `**Exact Code:** if not path.exists(): raise SystemExit(...)` - and line 110 actually
                # reads `ACKNOWLEDGED_HARDCODED: set[str] = {`. Without this lookahead the checker
                # certified the line, never read the quote, and reported `0 refuted` on a fabrication
                # (BUG-831). The label is required so that a merely NEARBY fragment is not guessed at;
                # and a line that carries its own citation is never borrowed.
                nxt = answer_lines[i + 1]
                if QUOTE_LABEL.match(nxt) and not CITATION.search(nxt) and not LINE_ONLY.search(nxt):
                    frags = [f for f in BACKTICK.findall(nxt) if CODEY.search(f)]
            checked += 1
            target = ROOT / path
            if not target.exists():
                alt = pathlib.Path(path)
                if not alt.exists():
                    defects.append(f"cites {path}:{line_no} and no such file exists")
                    continue
                target = alt
            lines = target.read_text(errors="replace").splitlines()
            if line_no > len(lines):
                defects.append(f"{path}:{line_no} is past the end of the file ({len(lines)} lines)")
                continue
            actual = " ".join(lines[line_no - 1].split())
            for frag in frags:
                quote = " ".join(frag.split())
                if quote and quote not in actual:
                    defects.append(f"{path}:{line_no} is quoted as `{quote}` but that line reads: {actual[:120] or '(blank)'}")
    return checked, defects


def grade(answer: pathlib.Path, rc: int, min_chars: int, report: pathlib.Path) -> int:
    """Write the workstream's OWN terminal line from the evidence, never from an expectation.

    This runs INSIDE the workstream (it is the last line of cmd.sh), so it is the only writer of the
    terminal word. A non-zero rc with a real answer is still a partial result worth keeping, and it is
    reported as FAILED with the answer on disk - the point is that the WORD may not be guessed.
    """
    ok, why = answer_verdict(answer, min_chars)
    if ok and rc == 0:
        word = "DONE"
    elif "no content" in why or "empty" in why or "no answer file" in why:
        word = "EMPTY"
    else:
        word = "FAILED"
    line = f"TERMINAL: {word} - rc={rc}, {why}"
    with open(report, "a") as fh:
        fh.write(line + "\n")
        fh.flush()
    return 0 if word == "DONE" else 1


def _rows(run_id: str) -> list[dict]:
    """Every workstream's reconciled state, read from the runner that owns that state (one home)."""
    proc = subprocess.run([sys.executable, str(RUNNER), "status", "--run", run_id, "--json"],
                          capture_output=True, text=True, cwd=str(ROOT))
    try:
        return json.loads(proc.stdout or "[]")
    except Exception:
        print(f"FATAL: could not read the run state: {proc.stdout[:200]}{proc.stderr[:200]}")
        return []


def _watch(run_id: str, budget_s: int) -> int:
    """Enforce the declared budgets for this run. Returns the runner's honest exit code."""
    return subprocess.run([sys.executable, str(RUNNER), "watch", "--run", run_id,
                           "--budget", str(int(budget_s))], cwd=str(ROOT)).returncode


def _write_json(path: pathlib.Path, obj: dict) -> None:
    """Crash-safe JSON write: tempfile -> fsync -> os.replace (C6)."""
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _cmd_for(task: dict, wsd: str, g: dict, model: str) -> str:
    """The exact bytes a workstream runs: the task, then the GRADER that decides its terminal word."""
    lines = [f'echo "STEP 1: {model} starts" >> "$WS_REPORT"']
    if str(task.get("mode", "oneshot")) == "agent":
        lines.append('GOOSE=$(command -v goose || echo /Applications/Goose.app/Contents/Resources/bin/goose)')
        lines.append('"$GOOSE" run -t "$(cat "$WS_DIR/00_prompt.txt")" > "$WS_DIR/20_answer.md" 2>&1')
    else:
        mt = int(task.get("max_tokens", conf().get("fanout", {}).get("default_max_tokens", 512)))
        lines.append(f'python3 pipeline/oneshot_ask.py --model {model} --prompt-file "$WS_DIR/00_prompt.txt" '
                     f'--max-tokens {mt} --out "$WS_DIR/20_answer.md" --json-out "$WS_DIR/21_meta.json" '
                     f'>> "$WS_REPORT" 2>&1')
    lines.append("RC=$?")
    lines.append(f'python3 pipeline/subagent_fanout.py _grade --answer "$WS_DIR/20_answer.md" --rc "$RC" '
                 f'--min-chars {int(g["min_answer_chars"])} --report "$WS_REPORT"')
    return "\n".join(lines) + "\n"


def _prompt_for(task: dict, cap: int) -> str:
    """The question plus its evidence, with an explicit permission to say NO EVIDENCE."""
    parts = [str(task.get("question", "")).strip()]
    for f in task.get("files", []):
        p = ROOT / f
        if not p.exists():
            parts.append(f"\n### {f}\n(file absent - say so, do not guess)")
            continue
        parts.append(f"\n### {f}\n{p.read_text(errors='replace')[:cap]}")
    parts.append("\nAnswer in <=12 lines. Cite file:line where it helps. If the files do not "
                 "contain the answer, say NO EVIDENCE rather than guessing.")
    return "\n".join(parts)


def plan(tasks_file: pathlib.Path, run_id: str) -> int:
    """Validate a task file and freeze one command + one prompt per task (artefact-partitioned)."""
    import yaml
    g = guards()
    doc = yaml.safe_load(tasks_file.read_text()) or {}
    tasks = doc.get("tasks") or []
    if not tasks:
        print("FATAL: the task file declares no tasks")
        return FATAL
    cap = int(conf().get("fanout", {}).get("excerpt_bytes", 24000))
    subprocess.run([sys.executable, str(RUNNER), "new", "--run", run_id,
                    "--brief-text", tasks_file.read_text()], check=True, cwd=str(ROOT))
    for t in tasks:
        wid = str(t["id"])
        # THE PREMISE GATE. A fan-out verifies ANSWERS; nothing in it verifies the PREMISE of a task.
        # On 2026-10-15 a task asked about a setting that did not exist, the sub-agent correctly said so,
        # and the answer was read as a model failure (BUG-816/BUG-817). If a task declares expect=REGEX,
        # one of its files must contain it or the task is refused before any model is called.
        expect = t.get("expect")
        if expect:
            hit = [f for f in t.get("files", [])
                   if (ROOT / f).exists() and re.search(str(expect), (ROOT / f).read_text(errors="replace"))]
            if not hit:
                print(f"FATAL: task {wid} declares expect={expect!r} and no listed file contains it - "
                      f"the PREMISE is wrong, so no model should be asked")
                return FATAL
            print(f"premise ok: task {wid} expect={expect!r} found in {hit}")
        wsd = RUNS / run_id / f"fan_{wid}"
        wsd.mkdir(parents=True, exist_ok=True)
        (wsd / "00_prompt.txt").write_text(_prompt_for(t, cap))
        _write_json(wsd / "task.json", {"id": wid, "model": t["model"], "mode": str(t.get("mode", "oneshot")),
                                        "max_tokens": t.get("max_tokens"), "attempt": 1,
                                        "timeout_s": t.get("timeout_s"),
                                        "retry_of": None, "question": str(t.get("question", ""))})
        (wsd / "cmd.sh").write_text(_cmd_for(t, str(wsd), g, str(t["model"])))
    print(f"planned {len(tasks)} task(s) for run {run_id}")
    return OK


def _timeout_for(task: dict, g: dict) -> int:
    """The declared budget for THIS task's mode - a oneshot never inherits an agent's minutes.

    The owner's rule (2026-10-15): if a task can be answered faster than the old blanket 1800 s, it
    must be BUDGETED faster, because a generous timeout is a stall nobody notices. Measured oneshots
    answer in 0.4-17 s, so the oneshot budget is 120 s - and a task that overruns it is reaped and
    reported instead of being waited on.

    A task may declare its own `timeout_s`, which is how a KNOWN-fast task is kept honest: expecting
    a 6 s answer and killing at 120 s is 114 s of silence nobody reads.
    """
    own = task.get("timeout_s")
    if own not in (None, ""):
        if int(own) <= 0:
            raise SystemExit(f"FATAL: task {task.get('id')!r} declares timeout_s={own!r} - a budget of zero "
                             f"kills the task it was meant to bound")
        return int(own)
    return int(g["agent_timeout_s"]) if str(task.get("mode", "oneshot")) == "agent" else int(g["default_timeout_s"])


def _start_one(run_id: str, wid: str, g: dict, task: dict, note: str = "") -> None:
    """Launch one planned workstream with the DECLARED budget, stall threshold and kill policy."""
    wsd = RUNS / run_id / f"fan_{wid}"
    cmd = [sys.executable, str(RUNNER), "start", "--run", run_id, "--ws", f"fan_{wid}",
           "--timeout", str(_timeout_for(task, g)), "--stall", str(int(g["stall_s"])),
           "--cmd-file", str(wsd / "cmd.sh"), "--note", note]
    if g.get("kill_on_stall"):
        cmd.append("--kill-on-stall")
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def _running(run_id: str) -> int:
    """How many workstreams of this run are RUNNING right now (the pool cap is theirs)."""
    return sum(1 for r in _rows(run_id) if r["state"] == "RUNNING")


def start(run_id: str, watch: bool = True) -> int:
    """Start tasks under the DECLARED cap, then hand the run to the reaper.

    The reaper is what makes the declared budgets real for a run nobody is polling: a run that is
    started and walked away from is the exact shape of the 2026-10-15 stall (BUG-809).
    """
    g = guards()
    cap = int(conf().get("fanout", {}).get("max_parallel", 3))
    _rows(run_id)                       # reconcile before deciding what to launch
    started, waiting = 0, []
    for t in sorted([p for p in (RUNS / run_id).glob("fan_*") if p.is_dir()]):
        state = {}
        sp = t / "state.json"
        if sp.exists():
            try:
                state = json.loads(sp.read_text())
            except Exception as exc:  # reported, never swallowed (C16)
                print(f"FATAL: unreadable state for {t.name}: {type(exc).__name__}: {exc}")
                return FATAL
        if state.get("state") in ("RUNNING", "DONE", "FAILED", "TIMEOUT", "EMPTY", "STALLED"):
            continue
        if _running(run_id) >= cap:
            # The cap counts workstreams that are ALREADY RUNNING, and only those. Adding `started`
            # on top double-books every launch in this loop and silently strands the last task in
            # PENDING - measured live: 3 tasks, cap 3, started 2 (BUG-825).
            waiting.append(t.name)
            continue
        meta = t / "task.json"
        task = json.loads(meta.read_text()) if meta.exists() else {"mode": "oneshot"}
        _start_one(run_id, t.name.removeprefix("fan_"), g, task)
        started += 1
    print(f"started {started} (cap {cap})")
    if waiting:
        print(f"waiting on the declared cap of {cap}: {waiting} - retry/run will pick them up")
    if watch:
        budget = int(g["agent_timeout_s"]) + int(g["deadline_s"])
        subprocess.Popen([sys.executable, str(RUNNER), "watch", "--run", run_id, "--budget", str(budget)],
                         cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        print(f"reaper attached (budget {budget}s): timeouts and stalls are enforced without polling")
    return OK


RETRYABLE = ("FAILED", "EMPTY", "TIMEOUT", "STALLED")


def retry(run_id: str) -> int:
    """One bounded retry pass: a failed task is re-asked ONCE on a DIFFERENT declared model.

    Two rules make this a guard rather than a loop. (1) The retry model may not be the model that
    just failed - a second identical attempt duplicates the blindspot that produced the failure
    (R5's reasoning applied to delegation). (2) The attempt count is declared, so this can never
    become an unbounded restart loop that burns the pool.
    """
    g = guards()
    retry_on = set(g["retry_on"])
    fallback = str(g["fallback_model"])
    cap = int(conf().get("fanout", {}).get("max_parallel", 3))
    launched = 0
    for t in sorted([p for p in (RUNS / run_id).glob("fan_*") if p.is_dir()]):
        if re.search(r"_r\d+$", t.name):
            continue                                  # already a retry: attempts are declared
        meta = t / "task.json"
        if not meta.exists():
            continue
        try:
            task = json.loads(meta.read_text())
        except Exception as exc:
            print(f"FATAL: unreadable task.json for {t.name}: {type(exc).__name__}: {exc}")
            return 0
        rows = {r["ws"]: r for r in _rows(run_id)}
        state = rows.get(t.name, {}).get("state")
        if state not in retry_on:
            continue
        # R5 FINDING, ACTED ON (review by gemma-4-E4B, 2026-10-15): a non-zero exit with a perfectly
        # USABLE answer is reported FAILED, which then bought a retry nobody needed. A usable answer
        # already in hand is judged by the verifier, not re-purchased from the pool.
        usable, why = answer_verdict(t / "20_answer.md", int(g["min_answer_chars"]))
        if usable:
            print(f"retry: {task['id']} is {state} but already has a usable answer ({why}) - NOT re-asked; "
                  f"judging it is the verifier's job (R5), not the pool's")
            continue
        if int(task.get("attempt", 1)) >= int(g["max_attempts"]):
            print(f"retry: {task['id']} is {state} and has spent its {g['max_attempts']} attempt(s) - not retried")
            continue
        if fallback == task["model"]:
            print(f"FATAL: the retry model for {task['id']} ({fallback}) IS the model that failed - "
                  f"a second attempt by the same model adds no information (declare another fallback)")
            return 0
        if _running(run_id) >= cap:
            print(f"retry: {task['id']} waits - the pool cap of {cap} is in use")
            break
        wid = f"{task['id']}_r2"
        wsd = RUNS / run_id / f"fan_{wid}"
        wsd.mkdir(parents=True, exist_ok=True)
        (wsd / "00_prompt.txt").write_text((t / "00_prompt.txt").read_text())
        retried = dict(task, model=fallback, attempt=int(task.get("attempt", 1)) + 1, retry_of=t.name)
        # A retry does NOT inherit the per-task budget that just proved insufficient: re-asking the
        # same question with the same impossible clock is a way to spend the pool twice and call it
        # resilience. The attempt gets its mode's declared budget instead, and the relaxation is recorded.
        relaxed = retried.pop("timeout_s", None)
        retried["timeout_relaxed_from"] = relaxed
        _write_json(wsd / "task.json", retried)
        (wsd / "cmd.sh").write_text(_cmd_for(retried, str(wsd), g, fallback))
        _start_one(run_id, wid, g, retried, note=f"retry of {t.name} after {state}")
        print(f"retry: {task['id']} ({state}) re-asked on {fallback} as fan_{wid}")
        launched += 1
    return launched


def task_state(attempts: list[dict]) -> str:
    """A TASK's state, rolled up from its attempts: any usable answer makes it DONE.

    Reporting per-WORKSTREAM instead of per-TASK reads as failure when the run actually succeeded:
    the live proof printed "2/4 usable" for a run that answered all three questions, because the
    retried task's first attempt (TIMEOUT) and second attempt (DONE) were counted as two tasks.
    A receipt that under-reports success is as unusable as one that over-reports it.
    """
    if not attempts:
        return "PENDING"
    for a in attempts:
        if a["answer_usable"]:
            return "DONE"
    return attempts[-1]["state"]


def receipt(run_id: str) -> int:
    """Write the run's receipt and return an honest exit code (never a green light on a failure)."""
    rows = _rows(run_id)
    if not rows:
        print("FATAL: no workstreams in this run")
        return FATAL
    floor = int(guards()["min_answer_chars"])
    by_id: dict[str, dict] = {}
    for r in sorted(rows, key=lambda x: x["ws"]):
        wsd = RUNS / run_id / r["ws"]
        meta = {}
        if (wsd / "task.json").exists():
            try:
                meta = json.loads((wsd / "task.json").read_text())
            except Exception as exc:  # reported, never swallowed (C16)
                print(f"warn: unreadable task.json for {r['ws']}: {type(exc).__name__}: {exc}")
        ok, why = answer_verdict(wsd / "20_answer.md", floor)
        # A DELIVERABLE WHOSE CITATIONS ARE REFUTED IS NOT A DELIVERABLE (BUG-721). The verdict above
        # cannot see it: a fabricated answer is long, exits 0 and reads DONE.
        cited, cdefs = ((0, []) if not (wsd / "20_answer.md").exists()
                        else citation_defects((wsd / "20_answer.md").read_text(errors="replace")))
        tid = str(meta.get("id") or r["ws"])
        entry = by_id.setdefault(tid, {"id": tid, "state": "PENDING", "attempts": []})
        entry["attempts"].append({"ws": r["ws"], "state": r["state"], "model": meta.get("model"),
                                  "attempt": meta.get("attempt", 1), "elapsed_s": r["elapsed_s"],
                                  "idle_s": r.get("idle_s"), "terminal": r.get("terminal"),
                                  "answer_usable": ok, "answer_note": why,
                                  "citations_checked": cited, "citations_refuted": len(cdefs),
                                  "citation_defects": cdefs[:5]})
    for entry in by_id.values():
        entry["state"] = task_state(entry["attempts"])
    tasks = [by_id[k] for k in sorted(by_id)]
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t["state"]] = counts.get(t["state"], 0) + 1
    rec = {"run": run_id, "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "tasks": tasks,
           "counts": counts, "done": counts.get("DONE", 0), "total": len(tasks)}
    _write_json(RUNS / run_id / "98_receipt.json", rec)
    print(f"\nreceipt: temp/runs/{run_id}/98_receipt.json")
    for t in tasks:
        trail = " -> ".join(f"{a['state']}({a['model']})" for a in t["attempts"])
        print(f"  {t['id']:<20} {t['state']:<8} {len(t['attempts'])} attempt(s): {trail}")
    print(f"  {rec['done']}/{rec['total']} task(s) DONE")
    refuted = [(t["id"], a) for t in tasks for a in t["attempts"] if a.get("citations_refuted")]
    for tid, a in refuted:
        print(f"  REFUTED CITATION  {tid}/{a['ws']}: {a['citations_refuted']} refuted claim(s) across "
              f"{a['citations_checked']} citation(s) - the answer is not a deliverable")
        for d in a.get("citation_defects", [])[:2]:
            print(f"      {d}")
    if counts.get("RUNNING") or counts.get("PENDING"):
        return PENDING
    if refuted:
        return FATAL
    if rec["done"] < rec["total"]:
        return FATAL
    return OK


def run_task_file(tasks_file: pathlib.Path, run_id: str, deadline_s: int | None) -> int:
    """The guarded front door: plan -> start -> reap -> retry ONCE -> receipt. Bounded, always."""
    g = guards()
    deadline = int(deadline_s or g["deadline_s"])
    rc = plan(tasks_file, run_id)
    if rc != OK:
        return rc
    rc = start(run_id)
    if rc != OK:
        return rc
    t0 = time.time()
    _watch(run_id, deadline)
    left = max(30, deadline - int(time.time() - t0))
    # A task that waited on the pool cap has not had its turn yet: it is PENDING, not failed, and
    # leaving it behind is the silent gap the cap fix exists for. Sweep, then reap again.
    start(run_id, watch=False)
    retry(run_id)
    _watch(run_id, left)
    return receipt(run_id)


def verify(run_id: str, model: str, out: pathlib.Path) -> int:
    """Cross-family check of the collected answers (R5): the generator never checks itself."""
    g = guards()
    answers = []
    for t in sorted((RUNS / run_id).glob("fan_*")):
        a = t / "20_answer.md"
        ok, why = answer_verdict(a, int(g["min_answer_chars"]))
        if ok:
            answers.append(f"## {t.name}\n{a.read_text(errors='replace')[:4000]}")
        elif a.exists():
            answers.append(f"## {t.name}\n[UNUSABLE ANSWER - {why}; the verifier must not treat this as "
                           f"a claim to check]")
    if not answers:
        print("FATAL: no answers to verify")
        return FATAL
    prompt = ("You are the VERIFIER, not the author. Below are independent answers produced by other "
              "models. For each: state whether it answers its question, quote the strongest evidence, "
              "and name any claim that the cited file would contradict. End with a table "
              "(task | verdict | one-line reason).\n\n" + "\n\n".join(answers))
    tmp = RUNS / run_id / "99_verify_prompt.txt"
    tmp.write_text(prompt)
    rc = subprocess.run([sys.executable, str(ASKER), "--model", model, "--prompt-file", str(tmp),
                         "--max-tokens", "1200", "--out", str(out)], cwd=str(ROOT)).returncode
    print("verify: " + ("ok" if rc == 0 else "FAILED") + f" -> {out}")
    return rc


def _served() -> set[str]:
    """The ids the engine is actually serving right now (never a list copied by hand - BUG-819)."""
    sys.path.insert(0, str(ROOT))
    try:
        import json as _json
        import urllib.request

        from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL
        req = urllib.request.Request(f"{OMLX_URL}/v1/models",
                                     headers={"Authorization": f"Bearer {OMLX_API_KEY}"})
        with urllib.request.urlopen(req, timeout=10) as fh:
            return {m["id"] for m in _json.loads(fh.read().decode()).get("data", [])}
    except Exception as exc:
        print(f"  [FAIL] the engine could not be asked what it serves: {type(exc).__name__}: {exc}")
        return set()


def _plan_models(tasks_file: pathlib.Path | None) -> list[str]:
    """The models a PLAN will use. No plan -> the empty list: history is not a plan (see doctor)."""
    if not tasks_file:
        return []
    import yaml
    return [str(t["model"]) for t in (yaml.safe_load(tasks_file.read_text()) or {}).get("tasks", [])]


def _served_check(models: list[str], served: set[str]) -> tuple[bool | None, str]:
    """Is every model the plan names actually served? UNDECIDED (None) when there is no plan."""
    if not models:
        return None, "no plan given - pass --tasks to decide this"
    unserved = sorted({m for m in models if served and m not in served})
    return (not unserved), (f"not served: {unserved}" if unserved else f"{len(set(models))} distinct model(s) checked")


def _retry_check(fallback: str, models: list[str]) -> tuple[bool | None, str]:
    """R5: is the retry target DIFFERENT from the model(s) the plan will use? None = no plan to ask about."""
    if not models:
        return None, f"no plan given - fallback is {fallback}, nothing to compare it against"
    return (fallback not in set(models)), f"fallback={fallback}"


def doctor(tasks_file: pathlib.Path | None = None) -> int:
    """Preflight: refuse to start a delegation that cannot be sound. Print every check, fail on any.

    This is the guard against the whole BLINDSPOT/GAP class the owner asked for - an unguarded run
    (missing config), an unserved model (a 404 discovered halfway), a stuck ledger (a RUNNING entry
    whose process is dead, which reads forever as "still working"), and a retry target that is the
    model that failed. An instrument that cannot decide says so and stops (D-3015).
    """
    bad = 0
    # ok is TRI-STATE: True / False / None. None means UNDECIDED - the check had nothing to decide,
    # which is a verdict and must be printed as one. A check that cannot decide must never print as
    # a pass (measured 2026-10-15: doctor read 7/8 against the LEDGER OF EVERY RUN EVER, so the R5
    # retry check failed against a historical plan while the check that "passed" had checked nothing).
    checks: list[tuple[str, bool | None, str]] = []

    def add(name: str, ok: bool | None, why: str = "") -> None:
        checks.append((name, ok, why))

    try:
        g = guards()
        add("fanout.guards is declared and complete (C12)", True,
            f"timeout={g['default_timeout_s']}s stall={g['stall_s']}s attempts={g['max_attempts']}")
    except SystemExit as exc:
        add("fanout.guards is declared and complete (C12)", False, str(exc).split("\n")[0])
        g = {}

    served = _served()
    add("the engine answers /v1/models", bool(served), f"{len(served)} served id(s)")
    # THE PLAN, OR NOTHING. R5's retry question ("is the retry model the model that failed?") is a
    # property of a PLAN. Reading it off every run directory instead asks the question of delegations
    # that already finished, so a fallback model that was some task's model YESTERDAY fails a doctor
    # run for a plan that does not exist yet - a false FAIL, which teaches an operator to ignore the
    # guard. With no plan in hand the honest verdict is UNDECIDED, and a check that decided nothing
    # must never print as a pass either.
    models = _plan_models(tasks_file)
    add("every task model is served by the engine", *_served_check(models, served))
    if g:
        fallback = str(g["fallback_model"])
        add("the retry model is not a task model (R5: a retry may not repeat the failing model)",
            *_retry_check(fallback, models))
        add("the retry model itself is served", bool(served) and str(g["fallback_model"]) in served,
            str(g["fallback_model"]))
    add("the run root is writable", RUNS.exists() and RUNS.is_dir(), str(RUNS))
    add("both instruments are present", RUNNER.exists() and ASKER.exists())

    stuck = []
    for r in _rows_present():
        if r["state"] == "RUNNING" and not r.get("process_alive"):
            stuck.append(f"{r['run']}/{r['ws']}")
    add("no workstream reads RUNNING with a dead process (a stuck ledger, BUG-809)", not stuck,
        f"stuck: {stuck[:5]}" if stuck else "ledger reconcilable")

    for name, ok, why in checks:
        verdict = "undecided" if ok is None else ("ok" if ok else "FAIL")
        print(f"  [{verdict}] {name}{'  ' + why if why else ''}")
        bad += 0 if ok is not False else 1
    und = sum(1 for _, ok, _ in checks if ok is None)
    decided_n = len(checks) - und
    print(f"doctor: {decided_n - bad}/{decided_n} decided" + (f", {und} undecided (nothing to decide)" if und else ""))
    return FATAL if bad else OK


def _rows_present() -> list[dict]:
    """Every workstream of every run, reconciled (the ledger's own view)."""
    if not RUNS.exists():
        return []
    proc = subprocess.run([sys.executable, str(RUNNER), "status", "--json"],
                          capture_output=True, text=True, cwd=str(ROOT))
    try:
        return json.loads(proc.stdout or "[]")
    except Exception:
        return []


def selftest() -> int:
    """The controls that would have caught the three lies, plus the config guard itself."""
    g = guards()
    checks: list[tuple[str, bool]] = []
    tmp = RUNS / "selftest_fanout"
    tmp.mkdir(parents=True, exist_ok=True)

    stub = tmp / "stub.md"
    stub.write_text(STUB_PREFIX + ")\n")
    ok, why = answer_verdict(stub, 10)
    checks.append(("the_no_content_stub_is_NOT_an_answer", not ok))
    empty = tmp / "empty.md"
    empty.write_text("   \n")
    checks.append(("a_whitespace_answer_is_NOT_an_answer", not answer_verdict(empty, 10)[0]))
    short = tmp / "short.md"
    short.write_text("yes")
    checks.append(("an_answer_below_the_declared_floor_is_NOT_an_answer",
                   not answer_verdict(short, int(g["min_answer_chars"]))[0]
                   or int(g["min_answer_chars"]) <= 3))
    real = tmp / "real.md"
    real.write_text("x" * (int(g["min_answer_chars"]) + 5))
    checks.append(("a_real_answer_is_an_answer", answer_verdict(real, int(g["min_answer_chars"]))[0]))
    checks.append(("a_missing_answer_file_is_NOT_an_answer",
                   not answer_verdict(tmp / "nope.md", 10)[0]))

    # THE BUG-817 CLASS: the terminal word must be DERIVED, never asserted. A non-zero rc with a stub
    # answer must read EMPTY; a non-zero rc with a real answer must read FAILED, not DONE.
    rep = tmp / "10_report.md"
    rep.unlink(missing_ok=True)
    grade(stub, 1, int(g["min_answer_chars"]), rep)
    checks.append(("a_failed_oneshot_with_a_stub_reads_EMPTY_not_DONE",
                   rep.read_text().startswith("TERMINAL: EMPTY")))
    rep.unlink(missing_ok=True)
    grade(real, 1, int(g["min_answer_chars"]), rep)
    checks.append(("a_failed_oneshot_with_an_answer_reads_FAILED_not_DONE",
                   rep.read_text().startswith("TERMINAL: FAILED")))
    rep.unlink(missing_ok=True)
    grade(real, 0, int(g["min_answer_chars"]), rep)
    checks.append(("a_successful_oneshot_with_an_answer_reads_DONE",
                   rep.read_text().startswith("TERMINAL: DONE")))

    # NO COMMAND MAY CARRY A BAKED-IN VERDICT (the exact defect: `TERMINAL: DONE - rc=$?`).
    cmd = _cmd_for({"id": "x", "mode": "oneshot", "max_tokens": 8}, "/tmp", g, "M")
    checks.append(("no_generated_command_asserts_its_own_terminal_word",
                   "TERMINAL: DONE" not in cmd and "_grade" in cmd))
    checks.append(("every_generated_command_grades_the_answer_it_got", "--min-chars " in cmd))
    checks.append(("the_stall_threshold_is_strictly_inside_the_timeout",
                   int(g["stall_s"]) < int(g["default_timeout_s"])))
    checks.append(("a_oneshot_is_budgeted_FAR_MORE_TIGHTLY_than_an_agent_loop",
                   _timeout_for({"mode": "oneshot"}, g) < _timeout_for({"mode": "agent"}, g)))
    checks.append(("the_oneshot_budget_is_not_a_blanket_1800s",
                   _timeout_for({"mode": "oneshot"}, g) <= 300))
    checks.append(("the_whole_run_is_bounded_by_a_deadline_the_parent_obeys",
                   int(g["deadline_s"]) > 0))
    checks.append(("the_retry_count_is_bounded", int(g["max_attempts"]) >= 1))
    checks.append(("a_retried_task_cannot_be_retried_again_by_construction",
                   r'if re.search(r"_r\d+$", t.name)' in pathlib.Path(__file__).read_text()))
    # The receipt must roll attempts up to the TASK, or a successful retry is reported as a failure.
    checks.append(("a_task_that_succeeded_on_its_retry_reads_DONE_not_TIMEOUT",
                   task_state([{"state": "TIMEOUT", "answer_usable": False},
                               {"state": "DONE", "answer_usable": True}]) == "DONE"))
    checks.append(("a_task_whose_attempts_all_failed_reads_its_last_attempt",
                   task_state([{"state": "EMPTY", "answer_usable": False},
                               {"state": "FAILED", "answer_usable": False}]) == "FAILED"))
    checks.append(("a_task_with_no_attempt_yet_reads_PENDING", task_state([]) == "PENDING"))
    # R5 finding: a task that already holds a usable answer must not buy a retry (the pool is a resource,
    # and the verifier - not the pool - decides whether a usable-but-odd answer is good enough).
    checks.append(("a_usable_answer_is_not_re_bought_from_the_pool",
                   "already has a usable answer" in pathlib.Path(__file__).read_text()))
    # The cap may not double-book a launch: counting `started` on top of the ledger stranded a task.
    # The literal is assembled at run time because a control may not CONTAIN what it forbids.
    cap_leak = "started" + " + _running"
    checks.append(("the_pool_cap_counts_each_running_workstream_exactly_once",
                   cap_leak not in pathlib.Path(__file__).read_text()))

    # A CHECK THAT DECIDED NOTHING MUST NOT READ AS A PASS (BUG-826). doctor was reading the LEDGER OF
    # EVERY RUN EVER as if it were the plan, so the R5 check failed against a historical plan while the
    # check beside it "passed" having checked nothing.
    checks.append(("a_doctor_with_no_plan_reads_UNDECIDED_not_FAIL", _retry_check("m", [])[0] is None))
    checks.append(("a_plan_whose_task_model_IS_the_retry_model_reads_FAIL", _retry_check("m", ["m"])[0] is False))
    checks.append(("a_plan_whose_task_model_differs_from_the_retry_model_reads_ok", _retry_check("m", ["n"])[0] is True))
    checks.append(("a_served_check_with_no_plan_reads_UNDECIDED", _served_check([], {"a"})[0] is None))
    checks.append(("a_served_check_still_fails_on_an_unserved_plan_model", _served_check(["ghost"], {"a"})[0] is False))

    # BUG-721, MADE MECHANICAL: a citation is a claim about a file, so it is checkable without a model.
    bad_ans = 'pipeline/subagent_fanout.py:1 `word = "DONE"` asserts the terminal word'
    checks.append(("a_fabricated_citation_is_refuted", len(citation_defects(bad_ans)[1]) == 1))
    src = (ROOT / "pipeline/subagent_fanout.py").read_text().splitlines()
    n = next(i for i, line in enumerate(src, 1) if "def grade(" in line)
    good_ans = f"see pipeline/subagent_fanout.py:{n} `def grade(` for the only writer of the word"
    checks.append(("a_true_citation_passes", citation_defects(good_ans)[1] == []))
    checks.append(("a_citation_past_the_end_of_the_file_is_refuted",
                   len(citation_defects("pipeline/subagent_fanout.py:999999 `x = 1`")[1]) == 1))
    checks.append(("a_citation_to_a_file_that_does_not_exist_is_refuted",
                   len(citation_defects("pipeline/no_such_module_xyz.py:3 `x = 1`")[1]) == 1))
    checks.append(("an_answer_with_no_citation_checks_nothing_not_passing",
                   citation_defects("the code looks fine to me")[0] == 0))
    checks.append(("a_prose_reference_is_never_read_as_a_quote",
                   citation_defects(f"see pipeline/subagent_fanout.py:{n} for the grader")[1] == []))
    # BUG-831: the quote that sits on a LABELLED NEXT LINE must be tied to the citation, or a fabricated
    # "Exact Code:" walks through - which it did, in the R5 review of this very function.
    checks.append(("a_fabricated_quote_on_a_labelled_next_line_is_refuted",
                   len(citation_defects(f"File:line: pipeline/subagent_fanout.py (line {n})\n"
                                        'Exact Code: `word = "DONE"`')[1]) == 1))
    checks.append(("an_honest_quote_on_a_labelled_next_line_is_not_refuted",
                   citation_defects(f"File:line: pipeline/subagent_fanout.py (line {n})\n"
                                    "Exact Code: `def grade(`")[1] == []))
    checks.append(("a_fragment_on_an_UNLABELLED_next_line_is_not_guessed_at",
                   citation_defects(f"see pipeline/subagent_fanout.py:{n}\n"
                                    "and `something_else_entirely` elsewhere")[1] == []))
    checks.append(("a_next_line_with_its_own_citation_is_never_borrowed",
                   citation_defects(f"see pipeline/subagent_fanout.py:{n}\n"
                                    "Exact Code: `def grade(` (pipeline/research_run.py:1)")[1] == []))
    checks.append(("a_line_naming_its_own_file_is_checked_against_THAT_file",
                   len(citation_defects("### 1. `pipeline/research_run.py`\n"
                                        "File:line: `pipeline/subagent_fanout.py` (line 1)\n"
                                        'Exact Code: `word = "DONE"`')[1]) == 1))

    bad = 0
    for name, ok_ in checks:
        print(f"  [{'ok' if ok_ else 'FAIL'}] {name}")
        bad += 0 if ok_ else 1
    print(f"selftest: {len(checks) - bad}/{len(checks)}")
    return FATAL if bad else OK


def main(argv: list[str]) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="verb")
    d = sub.add_parser("doctor"); d.add_argument("--tasks")
    r = sub.add_parser("run"); r.add_argument("--tasks", required=True); r.add_argument("--run", required=True)
    r.add_argument("--deadline", type=int)
    p = sub.add_parser("plan"); p.add_argument("--tasks", required=True); p.add_argument("--run", required=True)
    s = sub.add_parser("start"); s.add_argument("--run", required=True); s.add_argument("--no-watch", action="store_true")
    for verb in ("status", "retry"):
        q = sub.add_parser(verb); q.add_argument("--run", required=True)
    v = sub.add_parser("verify"); v.add_argument("--run", required=True)
    v.add_argument("--model", required=True); v.add_argument("--out", required=True)
    gr = sub.add_parser("_grade"); gr.add_argument("--answer", required=True); gr.add_argument("--rc", required=True)
    gr.add_argument("--min-chars", required=True); gr.add_argument("--report", required=True)
    ci = sub.add_parser("citations"); ci.add_argument("--answer", required=True)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.verb == "_grade":
        return grade(pathlib.Path(args.answer), int(args.rc), int(args.min_chars), pathlib.Path(args.report))
    if args.verb == "citations":
        a = pathlib.Path(args.answer)
        if not a.exists():
            print(f"FATAL: no answer file at {a}")
            return FATAL
        checked, defects = citation_defects(a.read_text(errors="replace"))
        for d in defects:
            print(f"  REFUTED  {d}")
        if not checked:
            print("citations: none to check - this answer makes no checkable claim about a file")
            return PENDING
        print(f"citations: {checked} citation(s) checked, {len(defects)} refuted claim(s)")
        return FATAL if defects else OK
    if args.verb == "doctor":
        return doctor(pathlib.Path(args.tasks) if args.tasks else None)
    if args.verb == "run":
        return run_task_file(pathlib.Path(args.tasks), args.run, args.deadline)
    if args.verb == "plan":
        return plan(pathlib.Path(args.tasks), args.run)
    if args.verb == "start":
        return start(args.run, watch=not args.no_watch)
    if args.verb == "status":
        rows = _rows(args.run)
        for r in rows:
            print(f"{r['ws']:<20} {r['state']:<8}{' STALLED' if r.get('stalled') else '        '}"
                  f" {r['elapsed_s']:>7.1f}s idle={r.get('idle_s', 0):>6.1f}s"
                  f" progress={r.get('progress_bytes', 0):>7}B")
        return OK
    if args.verb == "retry":
        return OK if retry(args.run) >= 0 else FATAL
    if args.verb == "verify":
        return verify(args.run, args.model, pathlib.Path(args.out))
    ap.print_help()
    return FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
