#!/usr/bin/env python3
"""Durable parallel research runner - the BUG-809 remedy as INFRASTRUCTURE.

WHY THIS EXISTS
    A goose subagent is a CHILD of the session: a new user message cancels every in-flight
    child, and a child that is cancelled mid-flight loses everything it had not yet written
    to disk (BUG-809: 6 of 7 delegated runs were cancelled; one report survived only as chat
    text and died with the compaction). Two failure modes were observed and both are fixed
    here:
      (1) CANCELLATION - a workstream is launched DETACHED (its own session, its own
          process group). No harness event can cancel it. It survives the session.
      (2) WALL-CLOCK WASTE - a deliverable that is already complete but whose process is
          still alive must not be waited on. Every workstream declares a TERMINAL marker in
          its own report; collect returns the moment that line appears, NOT when the process
          exits.

CONTRACT (declared here, restated nowhere - C12)
    runs root      : temp/runs/<run_id>/<ws>/
    class          : every workstream runs AS one (config/agent_context.yaml#classes via workstreams.mode_class);
                     the class - not the caller - decides the stall floor, the wall and the env, and a
                     command carrying a harness launch marker is REFUSED under a class that does not keep
                     its transcript in the workstream (T-154/BUG-828)
    report         : 10_report.md   (append-only, written by the workstream)
    command        : cmd.sh         (written by start; the exact bytes that ran)
    run log        : run.log        (stdout+stderr of the workstream)
    prompt         : 00_prompt.txt  (the workstream's mandate; start REFUSES when absent/empty and no brief exists)
    brief          : 00_brief.md    (the run-level mandate; start materialises it into the prompt when needed)
    state          : state.json     (PENDING/RUNNING/DONE/FAILED/TIMEOUT/STALLED/STOPPED/EMPTY + pid, t0, t1, rc)
    heartbeat line : "STEP <n>: ..."   (workstream progress, readable while it runs)
    liveness       : RECURSIVE over the workstream dir minus the runner's own state.json/.tmp_* - so a
                     harness streaming its transcript under <ws>/agent/** is BUSY, not dead (T-154/BUG-828)
    terminal line  : "TERMINAL: <state> - <one line>"  (workstream declares its own end)

USAGE
    python3 pipeline/research_run.py new      --run ID --brief FILE
    python3 pipeline/research_run.py start    --run ID --ws NAME --cmd "..." [--timeout s] [--class CLASS]
    python3 pipeline/research_run.py status   [--run ID]
    python3 pipeline/research_run.py collect  --run ID [--timeout s]
    python3 pipeline/research_run.py stop     --run ID --ws NAME
    python3 pipeline/research_run.py --check  # recompute every class bound from its declared sources
    python3 pipeline/research_run.py --selftest

EXIT: 0 every workstream DONE; 2 something is still RUNNING (owner-owed);
      1 anything else terminal (FAILED/TIMEOUT/STALLED/STOPPED/EMPTY) or a malformed marker -
        the exit code follows the STATE, never the child's rc (C16: never silent).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "temp" / "runs"
REPORT = "10_report.md"
STATE = "state.json"
CMD = "cmd.sh"
LOG = "run.log"
PROMPT = "00_prompt.txt"   # the workstream's mandate copy; the one name BOTH halves agree on (BUG-833)
BRIEF = "00_brief.md"      # the run-level mandate; start materialises it into PROMPT when PROMPT is absent
TERMINAL = "TERMINAL:"
HEARTBEAT = "STEP "
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


def _guards() -> dict:
    """The DECLARED delegation guards, read from their one home. A missing home STOPS the import.

    These two values were literals here (1800 s and 600 s) until 2026-10-15, when `just preflight`
    turned red on them: config/engine.yaml#fanout.guards ALREADY declares default_timeout_s and
    stall_s, so the literals were a SECOND home for values that had one (C12) - and a workstream that
    quietly inherited 1800 s while the executor budgeted 120 s is the exact silence BUG-809 is about.
    """
    import yaml
    home = ROOT / "config" / "engine.yaml"
    if not home.exists():
        raise SystemExit(f"FATAL: {home} is absent - it is the one home for the delegation budgets (C12)")
    guards = ((yaml.safe_load(home.read_text(encoding='utf-8')) or {}).get("fanout") or {}).get("guards")
    if not isinstance(guards, dict):
        raise SystemExit("FATAL: config/engine.yaml declares no fanout.guards block - a workstream "
                         "without a declared budget is the BUG-809 defect (D-3020)")
    return guards


_GUARDS = _guards()
DEFAULT_TIMEOUT_S = int(_GUARDS["default_timeout_s"])
DEFAULT_STALL_S = int(_GUARDS["stall_s"])
AGENT_CONTEXT = ROOT / "config" / "agent_context.yaml"
TEMP_PREFIX = ".tmp_"          # write_json's own tempfiles: a progress counter must never count its own writes


def _agent_context() -> dict:
    """The class-bound contract, read from its one home (config/agent_context.yaml). FAIL-CLOSED (C12)."""
    import yaml
    if not AGENT_CONTEXT.exists():
        raise SystemExit(f"FATAL: {AGENT_CONTEXT} is absent - it is the one home for the class bounds (C12)")
    doc = yaml.safe_load(AGENT_CONTEXT.read_text(encoding='utf-8')) or {}
    if not doc.get("classes") or not doc.get("workstreams"):
        raise SystemExit("FATAL: config/agent_context.yaml declares no classes/workstreams block - a "
                         "workstream without a declared class is the BUG-828 defect (fail-closed, C16)")
    return doc


_CONTEXT = _agent_context()
CLASSES: dict = _CONTEXT["classes"]
WORKSTREAMS: dict = _CONTEXT["workstreams"]
DEFAULT_CLASS = str(WORKSTREAMS["default_class"])
CLASS_REQUIRED = ("stall_s", "timeout_guard", "max_turns", "transcript_in_ws", "env")


def resolve_class(name: str) -> dict:
    """A workstream class and its declared bound. An unknown or non-workstream class is FATAL.

    T-154/BUG-828: the CLASS is what makes a budget checkable. A workstream that runs as a class the
    contract does not declare has no longest measured turn, no stall floor and no ceiling - which is
    exactly how a healthy pi loop came to read `stalled=True` under a threshold written for scripts.
    """
    spec = CLASSES.get(name)
    if not spec:
        raise SystemExit(f"FATAL: '{name}' is not a declared class (config/agent_context.yaml#classes "
                         f"declares {sorted(CLASSES)}) - refusing to invent a bound (C12)")
    if not spec.get("workstream_class"):
        raise SystemExit(f"FATAL: '{name}' is not a WORKSTREAM class (workstream_class: false) - the pipeline "
                         f"calls the model itself, so no runner may claim it (D-3016)")
    missing = [k for k in CLASS_REQUIRED if k not in spec]
    if missing:
        raise SystemExit(f"FATAL: class '{name}' is missing {missing} - a bound nobody declared cannot be checked")
    if spec["timeout_guard"] not in _GUARDS:
        raise SystemExit(f"FATAL: class '{name}' names timeout_guard '{spec['timeout_guard']}', which "
                         f"config/engine.yaml#fanout.guards does not declare")
    return spec


def class_for_mode(mode: str) -> str:
    """The class a mode runs as, read from the one declared map - never inferred from the command bytes."""
    mapping = WORKSTREAMS.get("mode_class") or {}
    if mode not in mapping:
        raise SystemExit(f"FATAL: mode '{mode}' has no declared class (config/agent_context.yaml"
                         f"#workstreams.mode_class declares {sorted(mapping)})")
    return str(mapping[mode])


def class_env(spec: dict, wsd: pathlib.Path) -> dict:
    """The env the class REQUIRES bound for its child, with {ws}/{run} expanded and dirs created.

    T-154/BUG-828 part 1: a harness streams its transcript into its OWN config directory, which by default
    is outside the workstream where no liveness signal has ever looked. The class declares the binding;
    this is the ONE place it is applied, and the deploy path reads the same line of the same file.
    """
    out: dict[str, str] = {}
    for key, raw in (spec.get("env") or {}).items():
        value = str(raw).replace("{ws}", str(wsd)).replace("{run}", str(wsd.parent))
        if not value.startswith(str(wsd)):
            raise SystemExit(f"FATAL: class env {key}={value} does not resolve INSIDE the workstream {wsd} - "
                             f"a transcript outside the workstream is the BUG-828 defect")
        out[str(key)] = value
        pathlib.Path(value).mkdir(parents=True, exist_ok=True)
    return out


def _refusal(wsd: pathlib.Path, run_id: str, ws: str, reason: str, timeout_s: int, stall_s: int,
             kill_on_stall: bool, note: str) -> dict:
    """FAIL CLOSED: nothing is invoked, no command is written, and the state says why (BUG-833/T-154).

    One shape for every refusal, so a reader cannot tell a mandate-less workstream from a harness asked to
    run as a class that cannot see it - both are EMPTY, both are non-zero, both name their reason.
    """
    append_line(wsd / REPORT, f"{TERMINAL} EMPTY - {reason}")
    rec = {"run": run_id, "ws": ws, "state": "EMPTY", "pid": None, "rc": None,
           "t0": time.time(), "t1": time.time(), "timeout_s": timeout_s, "stall_s": stall_s,
           "kill_on_stall": kill_on_stall, "note": note, "refused": reason}
    write_json(wsd / STATE, rec)
    return rec


TERMINAL_WORDS = ("DONE", "FAILED", "TIMEOUT", "STOPPED", "STALLED", "EMPTY")
POLL_S = 2.0
OK, FATAL, OWNER_OWED = 0, 1, 2


def _assert_slug(value: str, what: str) -> str:
    """A run or workstream name is a SLUG: it may never carry a path separator (C6)."""
    if not SLUG.match(value):
        raise SystemExit(f"FATAL: {what} must match {SLUG.pattern}, got {value!r}")
    return value


def ws_dir(run_id: str, ws: str) -> pathlib.Path:
    """Resolve the workstream directory, creating it if needed."""
    return RUNS / _assert_slug(run_id, "run id") / _assert_slug(ws, "ws name")


def write_json(path: pathlib.Path, obj: dict) -> None:
    """Crash-safe JSON write: tempfile -> fsync -> os.replace (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_json(path: pathlib.Path) -> dict:
    """Read a state file, returning {} when it is absent or unreadable."""
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def append_line(path: pathlib.Path, line: str) -> None:
    """Append one line to an append-only report (fsync'd - a report is evidence)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding='utf-8') as fh:
        fh.write(line.rstrip("\n") + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def pid_alive(pid: int | None) -> bool:
    """True when the pid is a RUNNING process.

    Signal 0 answers for a zombie too, and a detached child whose exit has not been reaped
    is a zombie: without this second look, a workstream that died reads as alive forever and
    the runner never notices it is over.
    """
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    try:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return True
    return bool(state) and not state.upper().startswith("Z")


def signal_group(pid: int, grace_s: float = 5.0) -> None:
    """SIGTERM a whole process group, then SIGKILL what refuses to leave.

    A workstream runs detached, so it may hold child processes (a sleeping bench, a curl).
    Signalling only the parent leaves orphans that keep writing to the report.
    """
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        deadline = time.time() + (grace_s if sig == signal.SIGTERM else 0)
        while time.time() < deadline:
            if not pid_alive(pid):
                return
            time.sleep(0.25)


def terminal_line(report: pathlib.Path) -> str | None:
    """Return the workstream's own TERMINAL line, or None when it has not declared one."""
    if not report.exists():
        return None
    for raw in report.read_text(errors="replace", encoding='utf-8').splitlines():
        if raw.startswith(TERMINAL):
            return raw
    return None


def last_heartbeat(report: pathlib.Path) -> str | None:
    """Return the last STEP line, so a long workstream is readable while it runs."""
    if not report.exists():
        return None
    lines = [l for l in report.read_text(errors="replace", encoding='utf-8').splitlines() if l.startswith(HEARTBEAT)]
    return lines[-1] if lines else None


def new_run(run_id: str, brief_path: pathlib.Path | None, brief_text: str | None) -> pathlib.Path:
    """Create a run directory and freeze its brief (the brief is the run's only mandate)."""
    _assert_slug(run_id, "run id")
    root = RUNS / run_id
    root.mkdir(parents=True, exist_ok=True)
    body = brief_path.read_text(encoding='utf-8') if brief_path else (brief_text or "")
    (root / BRIEF).write_text(body.rstrip("\n") + "\n", encoding='utf-8')
    return root


def _meaningful(path: pathlib.Path) -> bool:
    """True when a file exists and carries more than whitespace (an empty prompt is a no-op call)."""
    return path.exists() and bool(path.read_text(errors="replace", encoding='utf-8').strip())


def materialise_prompt(wsd: pathlib.Path) -> tuple[int, str]:
    """Guarantee the workstream's prompt is non-empty, or say why it cannot run.

    A workstream's command reads $WS_DIR/00_prompt.txt; a missing file silently expands to an
    empty string (BUG-817), so a run that never asked a model still exits 0 (BUG-833). This is
    the single gate that makes that impossible: a prompt the caller wrote wins; otherwise the
    run-level brief (the one mandate new --brief freezes) is copied into the prompt; otherwise
    the workstream is refused. Returns (prompt_bytes, note); 0 bytes means refuse.
    """
    prompt = wsd / PROMPT
    if _meaningful(prompt):
        return prompt.stat().st_size, "prompt present"
    brief = wsd.parent / BRIEF
    if _meaningful(brief):
        prompt.write_text(brief.read_text(encoding='utf-8'), encoding='utf-8')
        return prompt.stat().st_size, f"materialised from run brief ({brief.stat().st_size}B)"
    return 0, "no prompt and no run brief - refused (BUG-833)"


def start(run_id: str, ws: str, cmd: str, timeout_s: int | None = None, note: str = "",
          stall_s: int | None = None, kill_on_stall: bool = False, ws_class: str = "") -> dict:
    """Launch one workstream DETACHED, as a DECLARED CLASS. Returns its state record.

    Detachment is the whole point: start_new_session=True gives the child its own session,
    so nothing that happens to this harness (a new user message, a cancelled turn, a
    compaction) can cancel it.

    The child receives WS_REPORT / WS_DIR / RUN_DIR plus the class's own declared env, so a workstream
    writes to its own report (and a harness streams its transcript INSIDE its own dir) without ever
    guessing a path. The class - not the caller's mood - decides the stall floor, the wall and the env:
    T-154 measured a healthy pi loop reading `stalled=True` because the class was never declared, and
    BUG-828's third part is the same defect on the ceiling (the class inherited a global 32768).

    TWO REFUSALS, both fail-closed (EMPTY, no command, no process, non-zero): a workstream with no
    mandate (BUG-833), and a command carrying a harness launch marker under a class that does not keep
    its transcript in the workstream (T-154 - an unbound transcript is a liveness signal nobody can see).
    """
    spec = resolve_class(ws_class or DEFAULT_CLASS)
    resolved_stall = int(stall_s if stall_s is not None else spec["stall_s"])
    resolved_timeout = int(timeout_s if timeout_s is not None else _GUARDS[spec["timeout_guard"]])
    wsd = ws_dir(run_id, ws)
    wsd.mkdir(parents=True, exist_ok=True)
    markers = [str(m) for m in (WORKSTREAMS.get("harness_cmd_markers") or [])]
    hit = [m for m in markers if m in cmd]
    prompt_bytes, prompt_note = materialise_prompt(wsd)
    (wsd / REPORT).touch()
    append_line(wsd / REPORT, f"# workstream {ws} (run {run_id}) class: {ws_class or DEFAULT_CLASS} "
                             f"note: {note or 'none'}")
    append_line(wsd / REPORT, f"# prompt: {prompt_bytes}B - {prompt_note}")
    if prompt_bytes == 0:
        return _refusal(wsd, run_id, ws, prompt_note, resolved_timeout, resolved_stall,
                        kill_on_stall, note)
    if hit and not spec.get("transcript_in_ws"):
        # FAIL CLOSED: a harness's transcript is the only thing that moves WHILE it works, so a harness
        # run that does not bind it inside the workstream is a run no liveness signal can see (BUG-828).
        return _refusal(wsd, run_id, ws,
                        f"command carries the harness marker {hit} but class '{ws_class or DEFAULT_CLASS}' "
                        f"declares transcript_in_ws: false - run it as a harness class (T-154)",
                        resolved_timeout, resolved_stall, kill_on_stall, note)
    (wsd / CMD).write_text(cmd.rstrip("\n") + "\n", encoding='utf-8')
    bound = class_env(spec, wsd)
    append_line(wsd / REPORT, "# class env: " + (", ".join(f"{k}={v}" for k, v in sorted(bound.items()))
                                                 or "none declared"))
    env = dict(os.environ)
    env.update(WS_REPORT=str(wsd / REPORT), WS_DIR=str(wsd), RUN_DIR=str(wsd.parent))
    env.update(bound)
    log = open(wsd / LOG, "ab")
    proc = subprocess.Popen(
        ["bash", str(wsd / CMD)], cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    rec = {"run": run_id, "ws": ws, "state": "RUNNING", "pid": proc.pid, "rc": None,
           "t0": time.time(), "t1": None, "timeout_s": resolved_timeout, "stall_s": resolved_stall,
           "ws_class": ws_class or DEFAULT_CLASS, "class_env": bound,
           "kill_on_stall": kill_on_stall, "note": note}
    write_json(wsd / STATE, rec)
    return rec


def progress_snapshot(wsd: pathlib.Path) -> tuple[int, int, float | None, str | None]:
    """(bytes, files, newest mtime, newest name) over the WHOLE workstream dir, minus the runner's own state.

    RECURSIVE ON PURPOSE (T-154/BUG-828 part 1). A harness streams its transcript under `<ws>/agent/**`
    while it works and writes its answer only at the end, so a counter that watches three fixed files
    read a healthy pi loop as dead for its whole life. Two exclusions matter as much as the walk:
      * `state.json` is REWRITTEN on every refresh - counting it would pin idle_s at 0.0 and make the
        stall flag UNREACHABLE, a silent failure in the opposite direction (the selftest asserts it);
      * `write_json`'s own `.tmp_*` files are the runner's writes, not the child's progress.
    """
    total = files = 0
    newest: float | None = None
    newest_name: str | None = None
    for path in wsd.rglob("*"):
        if path.name == STATE or path.name.startswith(TEMP_PREFIX) or not path.is_file():
            continue
        try:
            st = path.stat()
        except OSError:
            continue                     # a file that vanished mid-walk is not a reading
        files += 1
        total += st.st_size
        if newest is None or st.st_mtime > newest:
            newest, newest_name = st.st_mtime, str(path.relative_to(wsd))
    return total, files, newest, newest_name


def idle_s(wsd: pathlib.Path, now: float | None = None) -> float:
    """Seconds since the NEWEST counted file changed - the liveness signal (BUG-809/T-154).

    The newest file, never the sum: a sum hides a stall behind a big report written once at boot, and
    the report that once answered this question was measured at 66.6 s idle while pi was mid-loop.
    """
    now = time.time() if now is None else now
    _, _, newest, _ = progress_snapshot(wsd)
    return round(now - newest, 1) if newest else 0.0


def refresh(run_id: str, ws: str) -> dict:
    """Reconcile a state record with the report and the process table."""
    wsd = ws_dir(run_id, ws)
    rec = read_json(wsd / STATE)
    if not rec:
        return {"run": run_id, "ws": ws, "state": "PENDING", "pid": None, "elapsed_s": 0.0}
    rec["report_bytes"] = (wsd / REPORT).stat().st_size if (wsd / REPORT).exists() else 0
    rec["terminal"] = terminal_line(wsd / REPORT)
    rec["heartbeat"] = last_heartbeat(wsd / REPORT)
    rec["elapsed_s"] = round((rec.get("t1") or time.time()) - rec["t0"], 1)
    rec["process_alive"] = pid_alive(rec.get("pid"))
    total, files, _newest, newest_name = progress_snapshot(wsd)
    rec["progress_bytes"] = total
    rec["progress_files"] = files
    rec["progress_newest"] = newest_name
    rec["idle_s"] = idle_s(wsd)
    # The class decides the stall floor when the record does not carry one; an ad-hoc record with no
    # class reads as the declared default class rather than as "unknown" (T-154: one vocabulary).
    rec["ws_class"] = rec.get("ws_class") or DEFAULT_CLASS
    _cls = CLASSES.get(rec["ws_class"]) or {}
    rec["stall_s"] = int(rec.get("stall_s") or _cls.get("stall_s") or DEFAULT_STALL_S)
    if rec["state"] == "RUNNING":
        if rec["terminal"]:
            word = rec["terminal"].split(":", 1)[1].strip().split(" ", 1)[0].upper()
            rec["state"] = word if word in TERMINAL_WORDS else "FAILED"
            rec["t1"] = rec["t1"] or time.time()
        elif not rec["process_alive"]:
            rec["state"] = "FAILED"
            rec["t1"] = rec["t1"] or time.time()
            append_line(wsd / REPORT, f"{TERMINAL} FAILED - the process died without declaring an end (rc unknown)")
        elif rec["elapsed_s"] > rec["timeout_s"]:
            rec["state"] = "TIMEOUT"
            rec["t1"] = rec["t1"] or time.time()
            append_line(wsd / REPORT, f"{TERMINAL} TIMEOUT - exceeded the declared {rec['timeout_s']} s budget")
            signal_group(rec["pid"])
        elif rec["idle_s"] > rec["stall_s"] and rec.get("kill_on_stall"):
            # Only a workstream whose owner declared kill_on_stall is stopped on
            # suspicion. What is NEVER optional is the REPORT: stalled is a fact
            # about the child, not a verdict, so it is published either way.
            rec["state"] = "STALLED"
            rec["t1"] = rec["t1"] or time.time()
            append_line(wsd / REPORT,
                        f"{TERMINAL} STALLED - no progress for {rec['idle_s']}s (declared stall {rec['stall_s']}s)")
            signal_group(rec["pid"])
        else:
            rec["stalled"] = rec["idle_s"] > rec["stall_s"]
        write_json(wsd / STATE, rec)
    return rec


def status(run_id: str | None) -> list[dict]:
    """Return the state of every workstream of a run (or of every run)."""
    if run_id:
        roots = [RUNS / _assert_slug(run_id, "run id")]
    else:
        roots = sorted([p for p in RUNS.glob("*") if p.is_dir() and p.name != "selftest"])
    rows: list[dict] = []
    for root in roots:
        if not root.exists():
            continue
        for wsd in sorted([p for p in root.glob("*") if p.is_dir()]):
            rows.append(refresh(root.name, wsd.name))
    return rows


#: ── THE CLASS BOUND, RECOMPUTED (T-154/BUG-828). Three measured facts, three computed assertions. ──
def _dotted(node: object, dotted: str) -> object:
    """Walk a dotted pointer to its value. A missing step raises - a bound is never guessed (C16)."""
    for part in str(dotted).split("."):
        node = node[part]  # type: ignore[index]
    return node


def _pointer(value: str) -> object:
    """Resolve a pointer: 'a.b.c' in this file, or '@path#a.b.c' in another declared home.

    The same convention pipeline/harness_env.py uses for the harness contract, so a class env and a
    budget source are read the same way. An unresolvable pointer is FATAL, never a literal (C12/C16).
    """
    import yaml
    text = str(value)
    if text.startswith("@"):
        ref, _, dotted = text[1:].partition("#")
        path = pathlib.Path(ref)
        if not path.is_absolute():
            path = ROOT / ref
        if not path.exists():
            raise SystemExit(f"FATAL: the pointer {value} names {path}, which does not exist")
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    else:
        dotted = text
        doc = _CONTEXT
    return _dotted(doc, dotted)


def class_defects(ctx: dict) -> list[tuple[str, str, str]]:
    """Recompute every class bound and return (class, verdict, detail): ok / owner_owed / CONTRADICTION.

    PURE over the context it is handed, so the selftest can feed it a doctored contract and check that
    each defect is CAUGHT (D-400: an instrument that decides is measured on known answers, never on a
    hunch). The three assertions are BUG-828's three measured parts, turned into arithmetic:
      (1) SILENCE - stall_s must exceed the class's longest MEASURED turn by the declared margin. The
          failure it prevents is a healthy 45.58 s turn reading `stalled=True` under a 45 s threshold.
      (2) THE WALL - guards[timeout_guard] must be at least max_turns x per_turn_budget_s. The failure it
          prevents is a wall that is decorative or a ceiling nobody can pay: the bound that actually bit
          was the workstream wall, so the wall is derived from the owner's per-turn knob and the class's
          own declared turn count - and NOTHING else (a prefill term was retracted: a class's working_set
          is the prompt it must be able to PAY FOR, not the prompt it sends).
      (3) THE CEILING - max_tokens_per_turn is DERIVED (per_turn_budget_s x decode_tps) and must be
          BOUND where the class cannot declare it: a harness sends no max_tokens, so the server's own
          per-model fallback IS its ceiling. An engine bound ABOVE the derived ceiling contradicts it;
          an engine bound that is absent is OWNER-OWED (T-132: declared is not bound) - never a pass.
    """
    tb = ctx.get("turn_budget") or {}
    budget_home = str(tb.get("budget_home") or "")
    if not budget_home:
        raise SystemExit("FATAL: config/agent_context.yaml#turn_budget declares no budget_home - the per-turn "
                         "budget has ONE home and a checker that invents it is the defect (C12)")
    budget = float(_dotted(ctx, budget_home))
    margin = float(tb.get("stall_margin", 0))
    decode = _dotted(ctx, str(tb.get("decode_source")))
    routable = ((ctx.get("routing") or {}).get("measured_routable_20261014") or {})
    out: list[tuple[str, str, str]] = []
    for name, spec in (ctx.get("classes") or {}).items():
        if not spec.get("workstream_class"):
            out.append((name, "ok", "not a workstream class - the runner never claims it"))
            continue
        longest = float((spec.get("evidence") or {}).get("longest_turn_measured_s") or 0.0)
        floor = round(longest * margin, 2)
        if longest <= 0:
            out.append((name, "CONTRADICTION", "declares no longest_turn_measured_s - a stall threshold "
                                               "with no measured turn to sit above is BUG-828 itself"))
        elif float(spec.get("stall_s", 0)) <= floor:
            out.append((name, "CONTRADICTION",
                        f"stall_s={spec.get('stall_s')}s is not above the measured-turn floor {floor}s "
                        f"(longest {longest}s x margin {margin})"))
        models = routable.get(name) or []
        if not models:
            out.append((name, "CONTRADICTION", "no measured routable model - a class nobody can run is not bound"))
            continue
        slowest = min(float((decode.get(m) or {}).get("decode_tps", 0) or 0) for m in models)
        if slowest <= 0:
            out.append((name, "CONTRADICTION", f"no measured decode rate for {models} - an unmeasured model "
                                               f"is not routable (refuse, never optimistically assume)"))
            continue
        ceiling_tokens = int(budget * slowest)
        wall = round(float(spec.get("max_turns", 0)) * budget, 1)
        guard = float(_GUARDS[spec["timeout_guard"]])
        detail = (f"wall {wall}s (max_turns {spec.get('max_turns')} x {budget:.0f}s) <= "
                  f"{spec['timeout_guard']}={guard:.0f}s; derived ceiling {ceiling_tokens} tokens "
                  f"({budget:.0f}s x {slowest} tok/s on the slowest routable of {len(models)})")
        if wall > guard:
            out.append((name, "CONTRADICTION",
                        f"the derived wall {wall}s exceeds {spec['timeout_guard']}={guard:.0f}s - the wall "
                        f"would reap the class before its own declared budget is spent"))
            continue
        if spec.get("transcript_in_ws"):
            out.append((name, _binding_verdict(tb, models, ceiling_tokens), detail))
            continue
        declared = int(_pointer(str(tb.get("ceiling_declared_source") or "")))
        if declared > ceiling_tokens:
            out.append((name, "CONTRADICTION",
                        f"a caller declares max_tokens={declared}, ABOVE the derived ceiling "
                        f"{ceiling_tokens} tokens: the class would spend what the budget never bought"))
            continue
        out.append((name, "ok", detail + f"; the caller passes its own max_tokens ({declared})"))
    return out


def _binding_verdict(tb: dict, models: list[str], ceiling_tokens: int) -> str:
    """Is the class's derived ceiling actually BOUND where it can bite? (T-132: declared is not bound.)"""
    pointer = str((tb.get("bindings") or {}).get("harness") or "")
    ref = pointer.split("#")[0].strip()
    if not ref:
        return "CONTRADICTION"
    path = pathlib.Path(ref).expanduser()
    if not path.exists():
        return "owner_owed"
    import json
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return "CONTRADICTION"
    for model in models:
        bound = ((doc.get("models") or {}).get(model) or {}).get("max_tokens")
        if bound is None:
            continue
        if int(bound) > ceiling_tokens:
            return "CONTRADICTION"
        return "ok"
    return "owner_owed"


def class_check() -> int:
    """Print every class bound, recomputed. 0 green / 2 OWNER-OWED (a bound declared but not bound) / 1 a
    contradiction. OWNER-OWED is loud and not fatal, the same tri-state the harness contract uses: the
    engine's per-model fallback is the LIVE SERVER's home, so binding it is the owner's act, not a rail."""
    worst = OK
    for name, verdict, detail in class_defects(_CONTEXT):
        print(f"  [{verdict:<13}] {name:<15} {detail}")
        if verdict == "CONTRADICTION":
            worst = FATAL
        elif verdict == "owner_owed" and worst == OK:
            worst = OWNER_OWED
    if worst == OWNER_OWED:
        print("OWNER-OWED: the harness class ceiling is DECLARED and NOT BOUND - a caller that sends no")
        print("            max_tokens still inherits the server's global 32768. Binding it edits the live")
        print("            server's own home (~/.omlx/model_settings.json), which is the owner's act.")
    return worst


def exit_code_for(rows: list[dict]) -> int:
    """The runner's honest exit code: a run is a SUCCESS only when every workstream is DONE.

    An EMPTY answer is the exact failure BUG-833 measured - a workstream that called no model at
    all and exited 0 - so EMPTY (and TIMEOUT, STALLED, STOPPED, FAILED, PENDING) is non-zero.
    The exit code follows the STATE, never the child process's rc (which can be 0 for nothing).
    """
    if any(r["state"] == "RUNNING" for r in rows):
        return OWNER_OWED
    if all(r["state"] == "DONE" for r in rows):
        return OK
    return FATAL


def collect(run_id: str, timeout_s: int, wait_all: bool = True) -> int:
    """Wait until every workstream is TERMINAL - and not one second past the last marker."""
    deadline = time.time() + timeout_s
    seen: dict[str, str] = {}
    while True:
        rows = status(run_id)
        live = [r for r in rows if r["state"] == "RUNNING"]
        for r in rows:
            # Print on a CHANGE of state, never once per poll: a 4-minute loop must not spam.
            if seen.get(r["ws"]) != r["state"]:
                seen[r["ws"]] = r["state"]
                print(f"  {r['ws']:<14} {r['state']:<8} {r['elapsed_s']:>7.1f}s  report={r.get('report_bytes',0):>7}B  {r.get('heartbeat') or ''}"
                      f"{'  ' + r['terminal'][:60] if r.get('terminal') else ''}")
        if not live or not wait_all:
            break
        if time.time() > deadline:
            print(f"collect: still RUNNING after {timeout_s}s: {[r['ws'] for r in live]} - NOT waiting further")
            break
        time.sleep(POLL_S)
    return exit_code_for(status(run_id))


def watch(run_id: str | None, budget_s: int, poll_s: float = POLL_S) -> int:
    """Reap every declared budget without a human polling - the BUG-809 guard.

    A budget that is only enforced when somebody happens to call status() is not a
    budget: it is a hope. This loop is the thing that makes `timeout_s` and
    `stall_s` REAL for a detached run, and it exits on its own budget so the
    watcher itself can never become the stuck process.

    It reports STALLED loudly and keeps the child alive unless kill_on_stall was
    declared for it: a slow model is not a failure, but an unreported silence is.
    """
    deadline = time.time() + budget_s
    seen: dict[str, str] = {}
    while True:
        rows = status(run_id)
        for r in rows:
            key = f"{r['run']}/{r['ws']}"
            tag = f"{r['state']}{'!' if r.get('stalled') else ''}"
            if seen.get(key) != tag:
                seen[key] = tag
                print(f"  {r['run']}/{r['ws']:<16} {r['state']:<8}"
                      f"{' STALLED' if r.get('stalled') else '':<9}"
                      f" {r['elapsed_s']:>7.1f}s idle={r.get('idle_s', 0):>6.1f}s"
                      f" progress={r.get('progress_bytes', 0):>7}B"
                      f"{'  ' + r['terminal'][:52] if r.get('terminal') else ''}")
        if not any(r["state"] == "RUNNING" for r in rows):
            break
        if time.time() > deadline:
            live = [f"{r['run']}/{r['ws']}" for r in rows if r["state"] == "RUNNING"]
            print(f"watch: budget {budget_s}s spent, still RUNNING: {live} - NOT waiting further")
            return OWNER_OWED
        time.sleep(poll_s)
    return exit_code_for(status(run_id))


def stop(run_id: str, ws: str) -> int:
    """Signal a workstream's whole process group (explicit owner act only)."""
    rec = read_json(ws_dir(run_id, ws) / STATE)
    pid = rec.get("pid")
    if not pid_alive(pid):
        print(f"stop: {ws} is not alive")
        return OK
    try:
        append_line(ws_dir(run_id, ws) / REPORT, f"{TERMINAL} STOPPED - the owner stopped this workstream")
        signal_group(pid)
        print(f"stop: SIGTERM sent to process group of pid {pid}")
        return OK
    except Exception as exc:  # pragma: no cover - reported, never swallowed (C16)
        print(f"FATAL: could not stop {ws}: {type(exc).__name__}: {exc}")
        return FATAL


def selftest() -> int:
    """Prove the two properties that failed in production, or fail loudly."""
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    try:
        _assert_slug("../etc", "run id")
        add("a_run_id_may_not_carry_a_path_separator", False, "accepted ../etc")
    except SystemExit:
        add("a_run_id_may_not_carry_a_path_separator", True)

    rnd = "selftest"
    stale = RUNS / rnd
    if stale.exists():
        shutil.rmtree(stale)          # a stale report makes every control lie
    quick = ws_dir(rnd, "early")
    slow = ws_dir(rnd, "late")
    add("the_selftest_starts_from_an_empty_run", not any(quick.glob("*")) and not any(slow.glob("*")))

    # The runner's own liveness controls still need a non-empty mandate: start's prompt gate must
    # hold for EVERY workstream (T-160), so give the harness run a brief to materialise.
    (RUNS / rnd).mkdir(parents=True, exist_ok=True)
    (RUNS / rnd / BRIEF).write_text("selftest control brief - the runner's own liveness/harness controls\n", encoding='utf-8')

    start(rnd, "early", 'echo boot >> "$WS_REPORT"; echo "TERMINAL: DONE - finished before the process ended" >> "$WS_REPORT"; sleep 90',
          timeout_s=120, note="declares its end, then keeps existing")
    start(rnd, "late", "sleep 1; exit 3", timeout_s=60, note="dies without declaring an end")
    add("start_records_a_state_file_before_launching", bool(read_json(quick / STATE).get("pid")), "no pid recorded")

    t0 = time.time()
    rc_early = collect(rnd, timeout_s=30, wait_all=True)
    dt = time.time() - t0
    add("collect_returns_on_the_TERMINAL_marker_not_on_process_exit", dt < 12.0,
        f"took {dt:.1f}s")
    add("the_process_is_still_alive_when_collect_returns", pid_alive(read_json(quick / STATE).get("pid")),
        "the child had already exited - the early-return property was not exercised")
    add("a_marker_bearing_run_reads_as_terminal", status(rnd)[0]["state"] in ("DONE", "FAILED"))

    rec = read_json(quick / STATE)
    add("the_child_runs_in_its_own_session", os.getpgid(rec["pid"]) != os.getpgid(0),
        f"child pgid {os.getpgid(rec['pid'])} == ours {os.getpgid(0)} - it is cancellable")

    stop(rnd, "early")
    add("a_workstream_can_be_stopped_by_its_group", not pid_alive(rec["pid"]), "still alive after SIGTERM")

    start(rnd, "over", "sleep 20", timeout_s=2, note="exceeds its declared budget")
    time.sleep(3.5)
    over = refresh(rnd, "over")
    add("a_workstream_past_its_budget_reads_TIMEOUT_and_is_signalled", over["state"] == "TIMEOUT", f"state={over['state']}")
    time.sleep(1.0)
    add("a_timeout_actually_signals_the_child", not pid_alive(over.get("pid")), "the child survived its own timeout")
    # A terminal record must STOP COUNTING: an elapsed that keeps growing after the end is a lie about
    # how long the work took, and it was measured live (55.1 s on a task that died at 2.2 s).
    time.sleep(1.5)
    add("a_TIMEOUT_record_stops_growing_its_elapsed_time", refresh(rnd, "over")["elapsed_s"] == over["elapsed_s"],
        f"{over['elapsed_s']} -> {refresh(rnd, 'over')['elapsed_s']}")

    # The liveness controls: a SILENT child must be distinguishable from a working one.
    start(rnd, "quiet", "sleep 60", timeout_s=300, stall_s=2, note="works silently and never reports")
    start(rnd, "loud", 'for i in 1 2 3 4 5 6 7 8; do echo "STEP $i: working" >> "$WS_REPORT"; sleep 1; done; '
                       'echo "TERMINAL: DONE - eight steps" >> "$WS_REPORT"; sleep 60',
          timeout_s=300, stall_s=4, note="reports progress, so it is never called stalled")
    time.sleep(3.5)
    quiet = refresh(rnd, "quiet")
    loud = refresh(rnd, "loud")
    add("a_silent_child_is_reported_STALLED_without_being_killed", bool(quiet.get("stalled")), f"idle={quiet.get('idle_s')}")
    add("a_silent_child_that_was_not_declared_kill_on_stall_is_still_alive", pid_alive(quiet.get("pid")))
    add("a_child_that_reports_progress_is_NOT_stalled", not loud.get("stalled"), f"idle={loud.get('idle_s')}")
    add("a_stalled_child_still_reads_RUNNING_while_it_is_alive", quiet["state"] == "RUNNING", f"state={quiet['state']}")
    start(rnd, "quiet2", "sleep 60", timeout_s=300, stall_s=2, kill_on_stall=True,
          note="silent AND declared kill_on_stall")
    time.sleep(3.5)
    q2 = refresh(rnd, "quiet2")
    add("a_child_stalled_AND_declared_kill_on_stall_reads_STALLED_never_DONE",
        q2["state"] == "STALLED", f"state={q2['state']}")
    time.sleep(0.5)
    add("a_kill_on_stall_child_is_actually_signalled", not pid_alive(q2.get("pid")))
    for name in ("quiet", "loud", "quiet2"):
        stop(rnd, name)

    # T-160: a workstream with NO prompt and NO brief must be REFUSED, not launched (BUG-833).
    rr = "selftest_refusal"
    if (RUNS / rr).exists():
        shutil.rmtree(RUNS / rr)
    refused = start(rr, "nobrief", 'echo "SHOULD NOT RUN" >> "$WS_REPORT"', timeout_s=10)
    add("a_workstream_with_no_prompt_and_no_brief_is_refused_before_anything_runs",
        refused.get("state") == "EMPTY" and refused.get("pid") is None,
        f"state={refused.get('state')} pid={refused.get('pid')}")
    add("a_refused_workstream_writes_no_command", not (RUNS / rr / "nobrief" / CMD).exists(),
        "cmd.sh was materialised for a refused workstream")

    # T-154 (BUG-828): the CLASS is what makes a bound checkable, and the liveness signal must see a
    # harness that streams its transcript INSIDE its workstream.
    start(rnd, "harness", 'for i in 1 2 3 4 5 6; do mkdir -p "$WS_DIR/agent/sessions"; '
                          'echo "{\\"turn\\":$i}" >> "$WS_DIR/agent/sessions/s.jsonl"; sleep 1; done; '
                          'echo "TERMINAL: DONE - transcript-bound harness" >> "$WS_REPORT"; sleep 30',
          timeout_s=300, note="a harness streams a transcript and writes its answer only at the end",
          ws_class="agent_loop")
    time.sleep(3.5)
    hrec = read_json(ws_dir(rnd, "harness") / STATE)
    add("the_class_env_is_bound_INSIDE_the_workstream_T154",
        str(hrec.get("class_env", {}).get("PI_CODING_AGENT_DIR", "")).startswith(str(ws_dir(rnd, "harness"))),
        f"class_env={hrec.get('class_env')}")
    add("the_class_env_directory_exists", (ws_dir(rnd, "harness") / "agent").is_dir(),
        "PI_CODING_AGENT_DIR was declared but not created")
    h = refresh(rnd, "harness")
    add("a_harness_that_streams_a_NESTED_transcript_is_seen_as_progress_T154",
        not h.get("stalled") and "agent/sessions" in (h.get("progress_newest") or ""),
        f"idle={h.get('idle_s')} newest={h.get('progress_newest')} files={h.get('progress_files')}")
    # The counter must not count the runner's OWN writes: refresh() rewrites state.json every poll, so a
    # counter that included it would pin idle_s at 0 and make the stall flag unreachable (BUG-828 reversed).
    idle_a = refresh(rnd, "harness")["idle_s"]
    time.sleep(2.2)
    idle_b = refresh(rnd, "harness")["idle_s"]
    add("a_refresh_may_not_reset_its_own_idle_signal_T154", idle_b > idle_a, f"{idle_a} -> {idle_b}")
    stop(rnd, "harness")

    # A harness launch marker under a class that does not bind its transcript must be REFUSED, and the
    # SAME bytes under the harness class must not be (the control the refusal needs to mean anything).
    marker = str((WORKSTREAMS.get("harness_cmd_markers") or ["?"])[0])
    rq = "selftest_harness_refusal"
    if (RUNS / rq).exists():
        shutil.rmtree(RUNS / rq)
    (RUNS / rq).mkdir(parents=True, exist_ok=True)
    (RUNS / rq / BRIEF).write_text("selftest control brief - the harness-class refusal controls (T-154)\n", encoding='utf-8')
    marked = f'echo "{marker}pi --help" >/dev/null; sleep 30'
    bad_class = start(rq, "unbound", marked, timeout_s=10, note="a harness marker under a one-shot class")
    add("a_harness_marker_under_a_one_shot_class_is_REFUSED_T154",
        bad_class.get("state") == "EMPTY" and bad_class.get("pid") is None,
        f"state={bad_class.get('state')} pid={bad_class.get('pid')}")
    add("a_refused_harness_writes_no_command", not (RUNS / rq / "unbound" / CMD).exists())
    ok_class = start(rq, "bound", marked, timeout_s=30, note="the same bytes under the harness class",
                     ws_class="agent_loop")
    add("the_same_command_under_the_harness_class_is_NOT_refused",
        ok_class.get("state") == "RUNNING", f"state={ok_class.get('state')}")
    stop(rq, "bound")

    # A class must resolve from the declared map, an unknown mode must be FATAL, and a class the pipeline
    # owns may not be claimed by a runner (D-3016).
    add("a_mode_resolves_to_its_declared_class_T154", class_for_mode("harness") == "agent_loop",
        f"harness -> {class_for_mode('harness')}")
    try:
        class_for_mode("SELFTEST-NO-SUCH-MODE")
        add("an_undeclared_mode_is_FATAL_T154", False, "accepted a mode no config declares")
    except SystemExit:
        add("an_undeclared_mode_is_FATAL_T154", True)
    try:
        resolve_class("pipeline_batch")
        add("a_class_the_pipeline_owns_is_not_a_workstream_class_T154", False, "accepted pipeline_batch")
    except SystemExit:
        add("a_class_the_pipeline_owns_is_not_a_workstream_class_T154", True)

    # T-154: the DERIVED bounds, measured on known answers (D-400 - an instrument that decides is checked
    # on fabricated contracts, never on a hunch). Each defect below was measured in production first.
    import copy

    def doctored(**changes) -> list[tuple[str, str, str]]:
        ctx = copy.deepcopy(_CONTEXT)
        for path, value in changes.items():
            node = ctx
            parts = path.split(".")
            for part in parts[:-1]:
                node = node[part]
            node[parts[-1]] = value
        return class_defects(ctx)

    real = class_defects(_CONTEXT)
    add("the_shipped_class_contract_has_no_contradiction_T154",
        not [v for _, v, _ in real if v == "CONTRADICTION"], str([(n, d) for n, v, d in real if v == "CONTRADICTION"]))
    add("the_harness_class_ceiling_reads_OWNER_OWED_while_the_engine_home_is_empty_T154",
        any(v == "owner_owed" for n, v, _ in real if n == "agent_loop"),
        "the harness class ceiling no longer reports unbound - re-measure before trusting it")
    add("a_stall_threshold_below_the_measured_turn_is_CAUGHT_T154",
        any(v == "CONTRADICTION" for n, v, _ in doctored(**{"classes.agent_loop.stall_s": 45}) if n == "agent_loop"),
        "45 s - the exact threshold BUG-828 measured - was accepted")
    add("a_wall_smaller_than_the_class_own_budget_is_CAUGHT_T154",
        any(v == "CONTRADICTION" for _, v, _ in doctored(**{"classes.agent_loop.max_turns": 99})),
        "99 turns x 90 s was accepted against a 600 s wall")
    add("a_class_with_no_measured_turn_is_CAUGHT_T154",
        any(v == "CONTRADICTION" for _, v, _ in doctored(**{"classes.agent_loop.evidence.longest_turn_measured_s": 0})),
        "a stall threshold with no measured turn was accepted")
    # What a ONE-SHOT caller passes (engine.yaml#fanout.excerpt_bytes = 24000) is far above the derived
    # ceiling, so re-pointing the declared-ceiling source at it must be CAUGHT - the control proves the
    # ceiling assertion can fail, not only pass.
    add("a_declared_ceiling_above_the_derived_ceiling_is_CAUGHT_T154",
        any(v == "CONTRADICTION" for n, v, _ in class_defects(
            {**_CONTEXT, "turn_budget": {**(_CONTEXT["turn_budget"]),
                                         "ceiling_declared_source": "@config/engine.yaml#fanout.excerpt_bytes"}})
            if n == "agent_probe"),
        "a caller declaring 24000 max_tokens against a 3150-token ceiling was accepted")
    # ... and the same assertion for the class that sends NO ceiling: what the ENGINE falls back to IS the
    # ceiling, so a bound above it contradicts the budget and an absent bound is OWNER-OWED (never a pass).
    model = (_CONTEXT["routing"]["measured_routable_20261014"]["agent_loop"] or [""])[0]
    bound_file = ws_dir(rnd, "early") / "engine_bound_control.json"
    bound_file.write_text(json.dumps({"models": {model: {"max_tokens": 10 ** 9}}}), encoding='utf-8')
    unbound_file = ws_dir(rnd, "early") / "engine_unbound_control.json"
    unbound_file.write_text(json.dumps({"models": {}}), encoding='utf-8')

    def with_binding(path: pathlib.Path) -> list[tuple[str, str, str]]:
        return class_defects({**_CONTEXT, "turn_budget": {
            **(_CONTEXT["turn_budget"]),
            "bindings": {**(_CONTEXT["turn_budget"]["bindings"]), "harness": f"{path}#models.<model>.max_tokens"}}})

    add("an_engine_bound_ABOVE_the_derived_ceiling_is_CAUGHT_T154",
        any(v == "CONTRADICTION" for n, v, _ in with_binding(bound_file) if n == "agent_loop"),
        "the engine fallback was allowed to exceed the class ceiling")
    add("an_absent_engine_bound_reads_OWNER_OWED_never_OK_T154",
        all(v != "ok" for n, v, _ in with_binding(unbound_file) if n == "agent_loop"),
        "an unbound ceiling was reported as a pass")

    src = pathlib.Path(__file__).read_text(encoding='utf-8')
    # assembled at run time: the control may not contain the literals it forbids
    forbidden = [t for t in ("114" + "35", "sk-" + "maxwell", "bge" + "-m3", "deberta" + "-v3",
                             "gemma" + "-4", "phi" + "-4") if t in src.lower()]
    add("the_module_restates_no_engine_or_model_constant", not forbidden,
        "leaked: " + ", ".join(forbidden))

    bad = 0
    for name, ok, detail in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}{'  ' + detail if detail and not ok else ''}")
        bad += 0 if ok else 1
    print(f"selftest: {len(checks) - bad}/{len(checks)}")
    return FATAL if bad else OK


def main(argv: list[str]) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="recompute every class bound (T-154/BUG-828): 0 green, 2 OWNER-OWED, 1 contradiction")
    sub = ap.add_subparsers(dest="verb")
    p_new = sub.add_parser("new"); p_new.add_argument("--run", required=True)
    p_new.add_argument("--brief"); p_new.add_argument("--brief-text")
    p_start = sub.add_parser("start"); p_start.add_argument("--run", required=True)
    p_start.add_argument("--ws", required=True)
    p_start.add_argument("--cmd", default=""); p_start.add_argument("--cmd-file", default="")
    p_start.add_argument("--timeout", type=int, default=None); p_start.add_argument("--note", default="")
    p_start.add_argument("--stall", type=int, default=None)
    p_start.add_argument("--class", dest="ws_class", default="",
                         help="a workstream class (config/agent_context.yaml#classes); default from "
                              "config/agent_context.yaml#workstreams.default_class")
    p_start.add_argument("--kill-on-stall", action="store_true")
    p_st = sub.add_parser("status"); p_st.add_argument("--run"); p_st.add_argument("--json", action="store_true")
    p_w = sub.add_parser("watch"); p_w.add_argument("--run")
    p_w.add_argument("--budget", type=int, default=DEFAULT_TIMEOUT_S)
    p_c = sub.add_parser("collect"); p_c.add_argument("--run", required=True)
    p_c.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    p_stop = sub.add_parser("stop"); p_stop.add_argument("--run", required=True); p_stop.add_argument("--ws", required=True)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.check:
        return class_check()
    if args.verb == "new":
        root = new_run(args.run, pathlib.Path(args.brief) if args.brief else None, args.brief_text)
        print(f"run {args.run} created at {root}")
        return OK
    if args.verb == "start":
        cmd = pathlib.Path(args.cmd_file).read_text(encoding='utf-8') if args.cmd_file else args.cmd
        if not cmd.strip():
            print("FATAL: start needs --cmd or --cmd-file")
            return FATAL
        rec = start(args.run, args.ws, cmd, args.timeout, args.note,
                    stall_s=args.stall, kill_on_stall=bool(args.kill_on_stall), ws_class=args.ws_class)
        if rec["state"] == "EMPTY":
            print(f"REFUSED {args.ws}: {rec['refused']}")
            return FATAL
        print(f"started {args.ws} pid={rec['pid']} class={rec.get('ws_class')} "
              f"timeout={rec['timeout_s']}s stall={rec['stall_s']}s (detached)")
        return OK
    if args.verb == "status":
        if args.json:
            print(json.dumps(status(args.run), indent=1))
            return OK
        for r in status(args.run):
            print(f"{r['run']:<18} {r['ws']:<14} {r['state']:<8} {r['elapsed_s']:>7.1f}s report={r.get('report_bytes',0)}B alive={r.get('process_alive')}")
        return OK
    if args.verb == "watch":
        return watch(args.run, args.budget)
    if args.verb == "collect":
        return collect(args.run, args.timeout)
    if args.verb == "stop":
        return stop(args.run, args.ws)
    ap.print_help()
    return FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
