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
    report         : 10_report.md   (append-only, written by the workstream)
    command        : cmd.sh         (written by start; the exact bytes that ran)
    run log        : run.log        (stdout+stderr of the workstream)
    state          : state.json     (PENDING/RUNNING/DONE/FAILED/TIMEOUT + pid, t0, t1, rc)
    heartbeat line : "STEP <n>: ..."   (workstream progress, readable while it runs)
    terminal line  : "TERMINAL: <state> - <one line>"  (workstream declares its own end)

USAGE
    python3 pipeline/research_run.py new      --run ID --brief FILE
    python3 pipeline/research_run.py start    --run ID --ws NAME --cmd "..." [--timeout s]
    python3 pipeline/research_run.py status   [--run ID]
    python3 pipeline/research_run.py collect  --run ID [--timeout s]
    python3 pipeline/research_run.py stop     --run ID --ws NAME
    python3 pipeline/research_run.py --selftest

EXIT: 0 everything terminal and none failed; 2 something is still RUNNING (owner-owed);
      1 a workstream FAILED or a marker is malformed (fatal - C16: never silent).
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
TERMINAL = "TERMINAL:"
HEARTBEAT = "STEP "
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
DEFAULT_TIMEOUT_S = 1800
DEFAULT_STALL_S = 600
ANSWER = "20_answer.md"
PROGRESS_FILES = (REPORT, LOG, ANSWER)
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
        return json.loads(path.read_text())
    except Exception:
        return {}


def append_line(path: pathlib.Path, line: str) -> None:
    """Append one line to an append-only report (fsync'd - a report is evidence)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
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
    for raw in report.read_text(errors="replace").splitlines():
        if raw.startswith(TERMINAL):
            return raw
    return None


def last_heartbeat(report: pathlib.Path) -> str | None:
    """Return the last STEP line, so a long workstream is readable while it runs."""
    if not report.exists():
        return None
    lines = [l for l in report.read_text(errors="replace").splitlines() if l.startswith(HEARTBEAT)]
    return lines[-1] if lines else None


def new_run(run_id: str, brief_path: pathlib.Path | None, brief_text: str | None) -> pathlib.Path:
    """Create a run directory and freeze its brief (the brief is the run's only mandate)."""
    _assert_slug(run_id, "run id")
    root = RUNS / run_id
    root.mkdir(parents=True, exist_ok=True)
    body = brief_path.read_text() if brief_path else (brief_text or "")
    (root / "00_brief.md").write_text(body.rstrip("\n") + "\n")
    return root


def start(run_id: str, ws: str, cmd: str, timeout_s: int, note: str = "",
          stall_s: int = DEFAULT_STALL_S, kill_on_stall: bool = False) -> dict:
    """Launch one workstream DETACHED. Returns its state record.

    Detachment is the whole point: start_new_session=True gives the child its own session,
    so nothing that happens to this harness (a new user message, a cancelled turn, a
    compaction) can cancel it.

    The child receives WS_REPORT / WS_DIR / RUN_DIR in its environment, so a workstream
    writes to its own report without ever guessing a path (and without a shell-quoted
    argument that bash will mangle).
    """
    wsd = ws_dir(run_id, ws)
    wsd.mkdir(parents=True, exist_ok=True)
    (wsd / CMD).write_text(cmd.rstrip("\n") + "\n")
    (wsd / REPORT).touch()
    append_line(wsd / REPORT, f"# workstream {ws} (run {run_id}) note: {note or 'none'}")
    env = dict(os.environ)
    env.update(WS_REPORT=str(wsd / REPORT), WS_DIR=str(wsd), RUN_DIR=str(wsd.parent))
    log = open(wsd / LOG, "ab")
    proc = subprocess.Popen(
        ["bash", str(wsd / CMD)], cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    rec = {"run": run_id, "ws": ws, "state": "RUNNING", "pid": proc.pid, "rc": None,
           "t0": time.time(), "t1": None, "timeout_s": timeout_s, "stall_s": stall_s,
           "kill_on_stall": kill_on_stall, "note": note}
    write_json(wsd / STATE, rec)
    return rec


def progress_bytes(wsd: pathlib.Path) -> int:
    """Total bytes of every file a live workstream grows WHILE it works.

    The report alone is a weak liveness signal: in oneshot mode the answer is
    redirected into it only at the end, so a healthy run looks dead for its whole
    life. Log + answer file are counted for the same reason.
    """
    return sum(p.stat().st_size for p in (wsd / f for f in PROGRESS_FILES) if p.exists())


def idle_s(wsd: pathlib.Path, now: float | None = None) -> float:
    """Seconds since ANY progress file was last touched - the liveness signal.

    This is the number that was missing when a delegation "ran for so long without
    any result": without it, a hung child and a working child read identically
    until the timeout fires (BUG-809).
    """
    now = time.time() if now is None else now
    mt = [p.stat().st_mtime for p in (wsd / f for f in PROGRESS_FILES) if p.exists()]
    return round(now - max(mt), 1) if mt else 0.0


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
    rec["progress_bytes"] = progress_bytes(wsd)
    rec["idle_s"] = idle_s(wsd)
    rec["stall_s"] = int(rec.get("stall_s") or DEFAULT_STALL_S)
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
    rows = status(run_id)
    if any(r["state"] == "FAILED" for r in rows):
        return FATAL
    if any(r["state"] == "RUNNING" for r in rows):
        return OWNER_OWED
    return OK


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
    rows = status(run_id)
    if any(r["state"] == "FAILED" for r in rows):
        return FATAL
    return OK


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

    src = pathlib.Path(__file__).read_text()
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
    sub = ap.add_subparsers(dest="verb")
    p_new = sub.add_parser("new"); p_new.add_argument("--run", required=True)
    p_new.add_argument("--brief"); p_new.add_argument("--brief-text")
    p_start = sub.add_parser("start"); p_start.add_argument("--run", required=True)
    p_start.add_argument("--ws", required=True)
    p_start.add_argument("--cmd", default=""); p_start.add_argument("--cmd-file", default="")
    p_start.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S); p_start.add_argument("--note", default="")
    p_start.add_argument("--stall", type=int, default=DEFAULT_STALL_S)
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
    if args.verb == "new":
        root = new_run(args.run, pathlib.Path(args.brief) if args.brief else None, args.brief_text)
        print(f"run {args.run} created at {root}")
        return OK
    if args.verb == "start":
        cmd = pathlib.Path(args.cmd_file).read_text() if args.cmd_file else args.cmd
        if not cmd.strip():
            print("FATAL: start needs --cmd or --cmd-file")
            return FATAL
        rec = start(args.run, args.ws, cmd, args.timeout, args.note,
                    stall_s=args.stall, kill_on_stall=bool(args.kill_on_stall))
        print(f"started {args.ws} pid={rec['pid']} timeout={args.timeout}s stall={args.stall}s (detached)")
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
