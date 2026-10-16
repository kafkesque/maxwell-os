#!/usr/bin/env python3
"""delegate_journal.py - the TRACE a delegated run leaves, written BEFORE and AFTER it (T-168 / BUG-844 / D-3036).

WHY THIS EXISTS (measured, not asserted)
    MEASURED 2026-10-16: three delegates were launched for independent read-only work and the harness reported all
    three as cancelled before they finished. ONE of them had ALREADY written its artifact (6,573 B on disk,
    temp/draft_diagnose_skill_20261016.md) and the other two had written nothing - and NOTHING ON DISK DISTINGUISHED
    THE TWO STATES. The delegation ECONOMY was measured (the harness's own cost ledger, config/delegation_economy.yaml)
    while the delegation ACT was not, so a STALL, a KILL and a SUCCESS were ONE observation to every later reader.
    That made the standing rule ("delegate to the right local model, in parallel") UNVERIFIABLE, and a rule that
    cannot be verified decays into a habit (BUG-844).

THE RULE (D-3036, AGENTS.md#working_rules)
    AN ACT THAT LEAVES NO TRACE DID NOT HAPPEN. A delegated run therefore declares, BEFORE it starts, its PURPOSE, its
    MODEL, the exact FILES IT MAY WRITE and its WALL BUDGET; it records its END STATE and its ARTIFACTS afterwards,
    and each artifact is VERIFIED ON DISK rather than claimed. The start row is written BEFORE the call, so a call
    that hangs or is killed cannot lose its own record - the row is ALREADY there and reads OPEN.

WHAT THIS SCRIPT IS NOT
    It is not a scheduler and it does not judge answers. It settles three mechanical things: PRESENCE (a row exists),
    CONTRAST (an open run against an ended one) and BUDGET (elapsed time against the declared wall budget). Whether
    an artifact is GOOD is R5's question (generator != verifier) and whether an answer is RIGHT is the verifier's.
    The MODEL is recorded because it is the JOIN KEY to the harness's own cost ledger: this file restates NO price
    and NO tier, because a second home for a measured fact IS the drift (C12).

THE ONE ENTRY POINT
    python3 scripts/delegate_journal.py start --purpose "..." --model <name> --may-write <repo path|none> \\
        [--may-write ...] --budget-s <seconds>        # BEFORE the call; prints the id and the END command owed
    python3 scripts/delegate_journal.py end --id <id> --state <done|failed|cancelled> [--artifact <path>] [--note ...]
    python3 scripts/delegate_journal.py status [--all] [--json]
    python3 scripts/delegate_journal.py --selftest

EXIT CONTRACT (BUG-457 tri-state)
    start | end: 0 the row is RECORDED | 1 REFUSED - an undeclared word, a claim that does not resolve into this
        repository, a claim another OPEN run already holds, or an artifact the disk contradicts. A refused end writes
        NOTHING, so a run whose artifact is missing STAYS OPEN and is NAMED by status: a false success cannot be
        recorded, and the honest alternative (--state failed) is always available.
    status: 0 nothing is open | 1 a JOURNAL FAULT (a line that is not a row, a duplicate start, an end with no
        start) | 2 an OPEN run past its declared budget - OWNER-OWED, loud and NOT fatal (BUG-457).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# IMPORTED AFTER the sys.path insert DELIBERATELY: this script is invoked as "python3 scripts/delegate_journal.py",
# so the repository root is not yet on the path and the ONE append primitive cannot be imported at the top (the
# append is proved as a SUFFIX and receipted, BUG-560/D-2685 - it is not re-implemented here).
from scripts.lib.write_guard import append_lines  # noqa: E402

WRITER = "scripts/delegate_journal.py"
SURFACE_REL = "config/agent_surface.yaml"
OWNERSHIP_REL = "config/artifact_ownership.yaml"
LOGGING_KEY = "logging"
ARTIFACTS_KEY = "artifacts"
ROW_KIND = "row"
REQUIRED_KEYS: tuple[str, ...] = ("journal", "id_prefix", "row_schema_version", "end_states",
                                  "artifact_required_states", "read_only_token", "max_rows_read", "budget_required",
                                  "verified_artifacts_required")
DIGEST_CHUNK = 1024 * 1024
STAMP_LEN = 16
PURPOSE_WIDTH = 78
ID_HEX = 4
VERDICT_OK = 0
VERDICT_FAULT = 1
VERDICT_OWNER_OWED = 2


def _surface() -> dict[str, Any]:
    """Read the DECLARED logging block fail-closed (C12: this file restates no value of its own).

    An absent block, an absent key, an undeclared end state, or an artifact-required state outside the declared
    end-state vocabulary is FATAL at load: a journal whose own rules are inferred is a journal that can be made to
    accept anything by editing the thing it reads. `read_only_token` must NOT be a path-shaped word, or a caller
    writing a real path would be read as declaring that it writes nothing (the D-3034 shape, inverted).
    """
    cfg = yaml.safe_load((REPO_ROOT / SURFACE_REL).read_text()) or {}
    block = cfg.get(LOGGING_KEY)
    if not isinstance(block, dict):
        raise SystemExit("FATAL (" + WRITER + "): " + SURFACE_REL + " declares no '" + LOGGING_KEY
                         + "' block - a journal with no declared home is a file nobody owns (C12/C16)")
    for key in REQUIRED_KEYS:
        if block.get(key) in (None, "", []):
            raise SystemExit("FATAL (" + WRITER + "): " + SURFACE_REL + "#" + LOGGING_KEY + "." + key
                             + " is ABSENT - a missing declaration is the error, never a default (D-2644)")
    states = [str(s) for s in block["end_states"]]
    extra = [s for s in (str(x) for x in block["artifact_required_states"]) if s not in states]
    if extra:
        raise SystemExit("FATAL (" + WRITER + "): artifact_required_states names " + repr(extra)
                         + " which end_states does not declare - an end state that must carry an artifact and is not "
                           "an end state is a contradiction, not a policy (C16)")
    if "/" in str(block["read_only_token"]):
        raise SystemExit("FATAL (" + WRITER + "): read_only_token " + repr(block["read_only_token"])
                         + " is path-shaped - a token that looks like a claim cannot declare the absence of one")
    return block


LOGGING: dict[str, Any] = _surface()
JOURNAL: Path = (REPO_ROOT / str(LOGGING["journal"])).resolve()


def now_utc() -> datetime:
    """The one clock this reader uses, so two rows written in one sitting are comparable."""
    return datetime.now(UTC)


def shift(when: datetime, seconds: float) -> datetime:
    """A moment `seconds` away from `when`, so a control about TIME is synthetic rather than waited for."""
    return when + timedelta(seconds=seconds)


def stamp(when: datetime) -> str:
    """Render a timestamp as ISO-8601 UTC to the second - a row is read by a human before a machine."""
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_stamp(text: str) -> datetime | None:
    """Parse a row's own stamp; an unreadable stamp is a fault, never silently read as 'now' (C16)."""
    try:
        return datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def rel_of(path: Path, root: Path) -> str:
    """Render a path relative to the tree when it inside it, absolute when it is not (a fact, not a preference)."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def claim_path(raw: str, root: Path) -> tuple[Path | None, str]:
    """Resolve ONE --may-write claim, or return the reason it is not a claim (D-3034: a declaration must resolve).

    A claim that resolves OUTSIDE the tree is refused: a delegate that may write outside the repository cannot be
    held to any receipt this repository keeps, which is the shape BUG-818c measured (a copy landing in a synced
    tree). The read-only token is a separate argument, never an omission: an absent --may-write is refused, so
    "I forgot" can never read as "this run wrote nothing".
    """
    text = str(raw).strip()
    if not text:
        return None, "an empty --may-write is not a claim"
    cand = Path(text)
    full = cand if cand.is_absolute() else (root / cand)
    try:
        resolved = full.resolve()
    except OSError as exc:
        return None, "the claim " + repr(text) + " does not resolve: " + str(exc)
    root_r = root.resolve()
    if resolved != root_r and root_r not in resolved.parents:
        return None, ("the claim " + repr(text) + " resolves to " + str(resolved) + ", OUTSIDE " + str(root_r)
                      + " - work that leaves the repository leaves the receipts behind (BUG-818c)")
    return resolved, ""


def read_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read every row in order; a line that is not a row is a FAULT, never a silent skip (C16).

    Forgiving readers are how a journal acquires a hole nobody can name: a reader that skips its unreadable line
    reports a SHORTER history as if it were the whole one (the BUG-767 defect class). The read bound is declared
    (max_rows_read) and passing it is REPORTED, because a reader that truncates quietly is a reader that lies.
    """
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    faults: list[str] = []
    limit = int(LOGGING["max_rows_read"])
    for n, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            faults.append("line " + str(n) + " is not JSON (" + str(exc) + ") - repair the artifact, never the reader")
            continue
        if not isinstance(obj, dict) or not str(obj.get(ROW_KIND) or ""):
            faults.append("line " + str(n) + " is not a row (no '" + ROW_KIND + "' key)")
            continue
        rows.append(obj)
    if len(rows) > limit:
        faults.append("the journal carries " + str(len(rows)) + " rows, past the declared read bound " + str(limit)
                      + " - the reading below is COMPLETE for the file, and the bound asks for an archive rather "
                        "than a bigger reader")
    return rows, faults


def fold(rows: Sequence[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Fold rows into runs; a duplicate start and an end with no start are FAULTS (an act has ONE beginning).

    PURE over its input, so the controls that drive it are synthetic and this repository's own journal can never
    make one pass (BUG-492).
    """
    runs: dict[str, dict[str, Any]] = {}
    faults: list[str] = []
    for row in rows:
        kind = str(row.get(ROW_KIND))
        run = str(row.get("run") or "")
        if not run:
            faults.append("a " + kind + " row names no run id")
            continue
        if kind == "start":
            if run in runs:
                faults.append("run " + run + " carries TWO start rows - an act has one beginning")
                continue
            runs[run] = {"start": row}
        elif kind == "end":
            if run not in runs:
                faults.append("run " + run + " carries an end row and NO start row - the trace begins before the act")
                continue
            if runs[run].get("end"):
                faults.append("run " + run + " is ended TWICE")
                continue
            runs[run]["end"] = row
        else:
            faults.append("run " + run + " carries an undeclared row kind " + repr(kind))
    return runs, faults


def open_runs(runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """The runs that have a beginning and no end - the only rows a budget can speak about."""
    return [runs[k] for k in runs if not runs[k].get("end")]


def claims_of(run: dict[str, Any]) -> list[str]:
    """The claims a run declared, as written - a reader compares what the writer was TOLD it may touch."""
    return [str(x) for x in (run["start"].get("may_write") or [])]


def elapsed_s(run: dict[str, Any], when: datetime) -> float | None:
    """Seconds from a run's own start stamp to `when`; None when the stamp is unreadable (a fault, never a zero)."""
    began = parse_stamp(str(run["start"].get("started_utc") or ""))
    if began is None:
        return None
    return round((when - began).total_seconds(), 1)


def overdue_runs(runs: Sequence[dict[str, Any]], when: datetime) -> list[dict[str, Any]]:
    """PURE: the open runs past their DECLARED wall budget - the reading that is owner-owed, never a shrug."""
    out: list[dict[str, Any]] = []
    for run in runs:
        budget = run["start"].get("budget_s")
        spent = elapsed_s(run, when)
        if budget in (None, "") or spent is None:
            continue
        if float(spent) > float(budget):
            out.append(run)
    return out


def claim_faults(new: Sequence[Path], runs: dict[str, dict[str, Any]], root: Path) -> list[str]:
    """PURE: the C21/C23 refusal - two runs that may write ONE file may not be open at the same time.

    Two delegates writing one file is not parallelism, it is interleaving, and the loser is whichever wrote first
    (C23). A DIRECTORY claim contains a file claim, so the comparison is not equality alone: containment counts,
    which is what makes partitioning by directory honest rather than a way around the rule.
    """
    faults: list[str] = []
    for path in new:
        for run in open_runs(runs):
            for held in claims_of(run):
                held_path, _why = claim_path(held, root)
                if held_path is None:
                    continue
                if path == held_path:
                    faults.append("run " + str(run["start"].get("run")) + " already HOLDS " + rel_of(path, root)
                                  + " - a file two runs may write is written by neither of them reliably (C21/C23)")
                elif path in held_path.parents or held_path in path.parents:
                    faults.append("run " + str(run["start"].get("run")) + " holds " + rel_of(held_path, root)
                                  + ", which CONTAINS " + rel_of(path, root) + " - partition the work, or end the "
                                    "run that holds it")
    return faults


def start_faults(run_id: str, purpose: str, model: str, claims: Sequence[Path], read_only: bool, budget_s: Any,
                 runs: dict[str, dict[str, Any]], declared: str, rule: dict[str, Any], root: Path) -> list[str]:
    """PURE: what must hold for a delegated run to have a RECORDED BEGINNING (T-168: one control per limb).

    `declared` is the mutability the artifact register states for the journal - empty when the journal is not
    declared at all, which is D-401 drift rather than a policy choice.
    """
    faults: list[str] = []
    if run_id in runs:
        faults.append("the run id " + run_id + " already exists - a trace is never reused")
    if not str(purpose).strip():
        faults.append("no --purpose: a row that cannot say WHAT the run is for cannot be read by the next agent")
    if not str(model).strip():
        faults.append("no --model: the model is the JOIN KEY to the harness cost ledger, so a row without it joins "
                      "nothing (and this journal restates no price of its own, C12)")
    if bool(rule["budget_required"]) and budget_s in (None, ""):
        faults.append("no --budget-s: a run with no declared budget can never be OVERDUE, so it can never be "
                      "reported - the budget is what turns silence into a reading")
    if isinstance(budget_s, int) and budget_s <= 0:
        faults.append("--budget-s must be a positive number of seconds")
    if read_only and claims:
        faults.append("--may-write names paths AND the read-only token: the two claims contradict each other")
    if not read_only and not claims:
        faults.append("no --may-write: name every file this run may write, or the read-only token "
                      + repr(rule["read_only_token"]) + " - an OMISSION is not a claim (D-3034)")
    if not declared:
        faults.append("the journal " + rel_of(JOURNAL, REPO_ROOT) + " is NOT declared in " + OWNERSHIP_REL
                      + " - add it under 'artifacts:' with 'mutability: append_only' and this writer as "
                        "'writer_of_record' (D-401: a governed artifact with no declared home is a file nobody owns)")
    faults.extend(claim_faults(claims, runs, root))
    return faults


def end_faults(run_id: str, state: str, proofs: Sequence[dict[str, Any]], runs: dict[str, dict[str, Any]],
               rule: dict[str, Any]) -> list[str]:
    """PURE: what must hold for a run to have a RECORDED END - and the two limbs that refuse a false success.

    A 'done' whose artifact is ABSENT is refused rather than recorded, and the refusal leaves the row OPEN: the
    false success has no home in the file, and `status` names the run until the caller either leaves the artifact
    or records the honest word (failed). An artifact-required state with no artifact named is the same refusal one
    step earlier (verified_artifacts_required, AGENTS.md#working_rules).
    """
    faults: list[str] = []
    run = runs.get(run_id)
    if run is None:
        faults.append("no start row for " + repr(run_id) + " - a trace begins BEFORE the act; an end with no "
                      "beginning cannot be read by anybody (append the start row, or do not claim the run)")
    elif run.get("end"):
        faults.append("run " + run_id + " is already ended - a trace has ONE end, and a second one would rewrite "
                      "the first (the artifact is append-only)")
    states = [str(s) for s in rule["end_states"]]
    if state not in states:
        faults.append("state " + repr(state) + " is not one of " + repr(states)
                      + " - the vocabulary is DECLARED, never inferred (C12)")
    required = [str(s) for s in rule["artifact_required_states"]]
    if bool(rule["verified_artifacts_required"]) and state in required and not proofs:
        faults.append("state " + repr(state) + " requires at least one --artifact: an act that leaves no trace did "
                      "not happen (D-3036), and a run that wrote nothing records the word that says so")
    if bool(rule["verified_artifacts_required"]):
        absent = [str(p.get("path")) for p in proofs if not p.get("present")]
        if absent:
            faults.append("the disk CONTRADICTS the claim: " + ", ".join(absent) + " absent - a claimed artifact "
                          "that is not there is a NAMED fault (BUG-844); record --state failed, or leave the file. "
                          "Nothing was written, so the run STAYS OPEN and status will name it")
    return faults


def hash16(path: Path) -> str:
    """The repository's 16-hex content stamp: what proves the artifact read now is the artifact left behind."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(DIGEST_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()[:STAMP_LEN]


def artifact_proof(raw: str, root: Path) -> dict[str, Any]:
    """Verify ONE artifact ON DISK: present or absent, its bytes and its content stamp. A claim is never recorded."""
    cand = Path(str(raw))
    full = cand if cand.is_absolute() else (root / cand)
    proof: dict[str, Any] = {"path": rel_of(full, root), "present": False}
    try:
        if full.is_file():
            proof["bytes"] = full.stat().st_size
            proof["sha256_16"] = hash16(full)
            proof["present"] = True
    except OSError as exc:
        proof["error"] = str(exc)
    return proof


def declared_append_only(rel: str, ownership: dict[str, Any]) -> str:
    """Return the declared mutability of `rel` when it is declared append_only, else '' (the D-401 preflight)."""
    table = ownership.get(ARTIFACTS_KEY)
    if not isinstance(table, dict):
        return ""
    entry = table.get(rel)
    if not isinstance(entry, dict):
        return ""
    mutability = str(entry.get("mutability") or "")
    return mutability if mutability == "append_only" else ""


def ensure_ledger(path: Path) -> None:
    """Create an EMPTY ledger when the journal does not exist yet, so the FIRST run of a fresh tree is traceable.

    MEASURED 2026-10-16, by this route's own FIRST live `start`: the append primitive proves a SUFFIX, so it reads a
    pre-image first - and on a virgin tree there is no pre-image, so the first delegated run crashed with
    FileNotFoundError and its trace was LOST. An empty ledger is not a lie: it is ZERO ROWS, which is exactly the
    truth about a tree where no run has been declared yet, and the reader STATES that truth ("0 row(s)") rather than
    reporting an absence as an error. The creation is a bare create (an empty file has no content to lose) and the
    append that follows is STILL proved as a suffix over the file that now exists (BUG-560/D-2685).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


def append_row(path: Path, row: dict[str, Any], writer: str, receipt: bool = True) -> None:
    """Append ONE row through the repository's append primitive (suffix-only proof + a mutation receipt, C6/D-2685).

    `receipt=False` is used by the controls only: a selftest that appended receipts to the live mutation journal
    would make every ladder run look like a mutation of this repository.
    """
    line = json.dumps(row, sort_keys=True, ensure_ascii=False)
    if "\n" in line or "\r" in line:
        raise SystemExit("FATAL (" + writer + "): the row would carry a line terminator - the ledger's own convention "
                         "is not the writer's to change (C16)")
    ensure_ledger(path)
    append_lines(path, [line], writer=writer, backup=False, journal=receipt)


def make_id(prefix: str, when: datetime) -> str:
    """A run id that is a WORD: the stamp makes it sortable, the suffix makes two runs in one second distinct."""
    return str(prefix) + when.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:ID_HEX]


def start_main(argv: Sequence[str]) -> int:
    """Record the BEGINNING of a delegated run - BEFORE the call, so a hung call cannot lose its own row."""
    ap = argparse.ArgumentParser(prog=WRITER + " start", description="record a delegated run BEFORE it starts")
    ap.add_argument("--purpose", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--may-write", action="append", default=None)
    ap.add_argument("--budget-s", type=int, default=None)
    ap.add_argument("--id", default="")
    args = ap.parse_args(list(argv))

    token = str(LOGGING["read_only_token"])
    raw_claims = [str(x) for x in (args.may_write or [])]
    read_only = bool(raw_claims) and all(c.strip() == token for c in raw_claims)
    if read_only:
        raw_claims = []
    claims: list[Path] = []
    faults: list[str] = []
    for raw in raw_claims:
        path, why = claim_path(raw, REPO_ROOT)
        if path is None:
            faults.append(why)
        else:
            claims.append(path)

    rows, read_faults = read_rows(JOURNAL)
    runs, fold_faults = fold(rows)
    when = now_utc()
    run_id = str(args.id).strip() or make_id(str(LOGGING["id_prefix"]), when)
    ownership = yaml.safe_load((REPO_ROOT / OWNERSHIP_REL).read_text()) or {}
    declared = declared_append_only(rel_of(JOURNAL, REPO_ROOT), ownership)
    faults.extend(start_faults(run_id, args.purpose, args.model, claims, read_only, args.budget_s, runs, declared,
                               LOGGING, REPO_ROOT))
    if faults:
        return refuse("start", faults)

    row = {"schema_version": str(LOGGING["row_schema_version"]), ROW_KIND: "start", "run": run_id,
           "started_utc": stamp(when), "purpose": str(args.purpose), "model": str(args.model),
           "may_write": [rel_of(p, REPO_ROOT) for p in claims], "read_only": read_only, "budget_s": args.budget_s}
    append_row(JOURNAL, row, WRITER)
    print("RECORDED " + run_id + " OPEN - the row is written BEFORE the call, so a call that hangs is VISIBLE.")
    print("  budget  " + str(args.budget_s) + "s | model " + str(args.model))
    print("  claims  " + (", ".join(row["may_write"]) if row["may_write"] else "NONE (read-only)"))
    print("  END the run with:")
    print("    python3 " + WRITER + " end --id " + run_id + " --state done --artifact <the file it leaves>")
    if read_faults or fold_faults:
        print("  note: the journal already carried " + str(len(read_faults) + len(fold_faults))
              + " fault(s) - 'status' names them")
    return VERDICT_OK


def end_main(argv: Sequence[str]) -> int:
    """Record the END of a run: the state word, the wall time MEASURED from the journal's own rows, and artifacts."""
    ap = argparse.ArgumentParser(prog=WRITER + " end", description="record a delegated run's end and its artifacts")
    ap.add_argument("--id", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--artifact", action="append", default=None)
    ap.add_argument("--note", default="")
    args = ap.parse_args(list(argv))

    rows, _read_faults = read_rows(JOURNAL)
    runs, _fold_faults = fold(rows)
    proofs = [artifact_proof(a, REPO_ROOT) for a in (args.artifact or [])]
    faults = end_faults(str(args.id), str(args.state), proofs, runs, LOGGING)
    if faults:
        return refuse("end", faults)

    when = now_utc()
    run = runs[str(args.id)]
    row = {"schema_version": str(LOGGING["row_schema_version"]), ROW_KIND: "end", "run": str(args.id),
           "ended_utc": stamp(when), "state": str(args.state), "wall_s": elapsed_s(run, when), "artifacts": proofs,
           "note": str(args.note)}
    append_row(JOURNAL, row, WRITER)
    print("RECORDED " + str(args.id) + " ended " + str(args.state) + " (wall " + str(row["wall_s"]) + "s)")
    print("  the wall time is MEASURED from the journal's own two rows, so the caller cannot restate it")
    for proof in proofs:
        if proof.get("present"):
            print("  artifact " + str(proof["path"]) + " present " + str(proof.get("bytes")) + " B sha256_16 "
                  + str(proof.get("sha256_16")))
        else:
            print("  artifact " + str(proof["path"]) + " ABSENT")
    return VERDICT_OK


def status_verdict(faults: Sequence[str], overdue: Sequence[dict[str, Any]]) -> int:
    """PURE: the tri-state reading - a fault is 1, a budget spent is 2, a clean sheet is 0 (BUG-457)."""
    if faults:
        return VERDICT_FAULT
    if overdue:
        return VERDICT_OWNER_OWED
    return VERDICT_OK


def status_main(argv: Sequence[str]) -> int:
    """The READER: which runs are OPEN, which are PAST BUDGET, which rows are faults. It writes nothing at all."""
    ap = argparse.ArgumentParser(prog=WRITER + " status", description="name the open, overdue and faulty runs")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(list(argv))

    rows, faults = read_rows(JOURNAL)
    runs, fold_faults = fold(rows)
    faults = list(faults) + list(fold_faults)
    when = now_utc()
    opened = open_runs(runs)
    overdue = overdue_runs(opened, when)

    if args.json:
        print(json.dumps({"journal": rel_of(JOURNAL, REPO_ROOT), "rows": len(rows), "runs": len(runs),
                          "open": len(opened), "overdue": [str(r["start"].get("run")) for r in overdue],
                          "faults": faults}, indent=1, sort_keys=True))
        return status_verdict(faults, overdue)

    print("DELEGATE JOURNAL - " + rel_of(JOURNAL, REPO_ROOT))
    print("  " + str(len(rows)) + " row(s), " + str(len(runs)) + " run(s), " + str(len(opened)) + " open, "
          + str(len(overdue)) + " past budget")
    for run in opened:
        late = run in overdue
        print(("  OVERDUE " if late else "  OPEN    ") + str(run["start"].get("run"))
              + "  elapsed " + str(elapsed_s(run, when)) + "s / budget " + str(run["start"].get("budget_s"))
              + "s  model " + str(run["start"].get("model")))
        print("            purpose: " + str(run["start"].get("purpose"))[:PURPOSE_WIDTH])
        claims = claims_of(run)
        print("            claims : " + (", ".join(claims) if claims else "NONE (read-only)"))
    if args.all:
        for run_id, run in runs.items():
            if run.get("end"):
                print("  ENDED   " + str(run_id) + "  " + str(run["end"].get("state")) + "  wall "
                      + str(run["end"].get("wall_s")) + "s  artifact(s) "
                      + str(len(run["end"].get("artifacts") or [])))
    if faults:
        print("  !! " + str(len(faults)) + " JOURNAL FAULT(S):")
        for fault in faults:
            print("     - " + fault)
    if overdue:
        print("  !! " + str(len(overdue)) + " OPEN run(s) past their declared budget - OWNER-OWED, loud and not "
              "fatal: the run either ends, or the budget was wrong, and both are WORDS (BUG-457).")
    if not faults and not overdue:
        print("  ok   no run is open past its budget and the journal reads as a journal (T-168/D-3036).")
    return status_verdict(faults, overdue)


def refuse(verb: str, faults: Sequence[str]) -> int:
    """Refuse an act, naming EVERY limb, and write NOTHING (C16: no silent error and no partial write)."""
    print("REFUSED (" + WRITER + " " + verb + ") - nothing was written:")
    for fault in faults:
        print("  !! " + fault)
    return VERDICT_FAULT


def scratch_lines(path: Path, lines: Sequence[str]) -> Path:
    """Create a scratch ledger for the controls - hermetic, so this repository's own bytes can never pass one."""
    path.write_text("".join(line + "\n" for line in lines))
    return path


def selftest() -> int:
    """Known-answer controls: every limb of the licence and of the reader must be SEEN to fire (BUG-492)."""
    import shutil
    import tempfile

    passed = 0
    failed: list[str] = []
    rule = dict(LOGGING)
    #: RESOLVED, so a fixture claim and a claim resolved by the licence are the SAME path even where the
    #: system temp dir is a symlink (/var -> /private/var on macOS): a control that fails for that reason
    #: would be testing the filesystem rather than the refusal.
    root = Path(tempfile.mkdtemp(prefix="delegate_journal_selftest_")).resolve()
    scratch = root / "temp"
    scratch.mkdir(parents=True, exist_ok=True)

    def control(name: str, got: int, want: int, why: str) -> None:
        nonlocal passed
        if got == want:
            passed += 1
        else:
            failed.append(name + ": got " + str(got) + ", want " + str(want) + " (" + why + ")")

    def n_start(*args: Any) -> int:
        return len(start_faults(*args))

    def n_end(*args: Any) -> int:
        return len(end_faults(*args))

    def only(run_id: str, claims: list[str] | None = None) -> dict[str, dict[str, Any]]:
        return {run_id: {"start": {"run": run_id, "may_write": claims or [], "budget_s": 60}}}

    def ended(run_id: str) -> dict[str, dict[str, Any]]:
        return {run_id: {"start": {"run": run_id, "may_write": [], "budget_s": 60},
                         "end": {"run": run_id, "state": "done"}}}

    claim = root / "scripts" / "held.py"
    claim.parent.mkdir(parents=True, exist_ok=True)
    held = only("DJ-held", ["scripts/held.py"])
    held_dir = only("DJ-dir", ["scripts"])

    # ── the beginning ────────────────────────────────────────────────────────────────────────────────────────
    control("start_purpose_required", n_start("DJ-a", "", "m", [], True, 60, {}, "append_only", rule, root), 1,
            "a row that cannot say what the run is for cannot be read")
    control("start_model_required", n_start("DJ-a", "p", "", [], True, 60, {}, "append_only", rule, root), 1,
            "the model is the join key to the cost ledger")
    control("start_budget_required", n_start("DJ-a", "p", "m", [], True, None, {}, "append_only", rule, root), 1,
            "a run with no budget can never be OVERDUE")
    control("start_budget_positive", n_start("DJ-a", "p", "m", [], True, 0, {}, "append_only", rule, root), 1,
            "zero seconds is not a budget")
    control("start_claim_or_token", n_start("DJ-a", "p", "m", [], False, 60, {}, "append_only", rule, root), 1,
            "an OMISSION is not a claim (D-3034)")
    control("start_contradiction", n_start("DJ-a", "p", "m", [claim], True, 60, {}, "append_only", rule, root), 1,
            "claims AND the read-only token contradict each other")
    control("start_id_reused", n_start("DJ-used", "p", "m", [], True, 60, ended("DJ-used"), "append_only", rule,
                                       root), 1, "a trace is never reused")
    control("start_undeclared_home", n_start("DJ-a", "p", "m", [], True, 60, {}, "", rule, root), 1,
            "a journal no declaration owns is D-401 drift")
    control("start_outside_tree", 1 if claim_path("../../etc/passwd", root)[0] is None else 0, 1,
            "a claim that resolves outside the tree leaves its receipts behind (BUG-818c)")
    control("start_claim_held", n_start("DJ-b", "p", "m", [claim], False, 60, held, "append_only", rule, root), 1,
            "one file two runs may write is written by neither reliably (C21/C23)")
    control("start_claim_in_held_dir", n_start("DJ-b", "p", "m", [claim], False, 60, held_dir, "append_only", rule,
                                               root), 1, "containment counts, not equality alone")
    control("start_refusal_stands_while_open", n_start("DJ-b", "p", "m", [claim], False, 60,
                                                       {**ended("DJ-old"), **held}, "append_only", rule, root), 1,
            "another run ending does not release a claim this run still holds")
    control("start_accepted", n_start("DJ-b", "p", "m", [claim], False, 60, ended("DJ-old"), "append_only", rule,
                                      root), 0, "a clean declaration is ACCEPTED")

    # ── the end ──────────────────────────────────────────────────────────────────────────────────────────────
    absent = {"path": "temp/nothing.md", "present": False}
    present = {"path": "temp/thing.md", "present": True, "bytes": 12, "sha256_16": "0" * STAMP_LEN}
    control("end_needs_a_start", n_end("DJ-x", "done", [present], {}, rule), 1, "the trace begins before the act")
    control("end_once", n_end("DJ-old", "done", [present], ended("DJ-old"), rule), 1,
            "a second end would rewrite the first")
    control("end_state_declared", n_end("DJ-open", "finished", [present], only("DJ-open"), rule), 1,
            "the vocabulary is DECLARED, never inferred")
    control("end_artifact_required", n_end("DJ-open", "done", [], only("DJ-open"), rule), 1,
            "an act that leaves no trace did not happen (D-3036)")
    control("end_absent_refused", n_end("DJ-open", "done", [absent], only("DJ-open"), rule), 1,
            "a claimed artifact that is not there is a NAMED fault (BUG-844)")
    control("end_failed_without_artifact", n_end("DJ-open", "failed", [], only("DJ-open"), rule), 0,
            "the honest word is always available")
    control("end_accepted", n_end("DJ-open", "done", [present], only("DJ-open"), rule), 0,
            "a verified artifact is accepted")

    # ── the reader ───────────────────────────────────────────────────────────────────────────────────────────
    began = {"schema_version": "1", ROW_KIND: "start", "run": "DJ-t", "started_utc": stamp(shift(now_utc(), -90)),
             "purpose": "p", "model": "m", "may_write": [], "budget_s": 60}
    inside = {"schema_version": "1", ROW_KIND: "start", "run": "DJ-u", "started_utc": stamp(shift(now_utc(), -10)),
              "purpose": "p", "model": "m", "may_write": [], "budget_s": 60}
    folded, fold_ok = fold([began, inside])
    control("fold_two_starts", len(folded), 2, "two runs, two beginnings")
    control("fold_clean", len(fold_ok), 0, "a clean journal folds with no fault")
    control("overdue_is_measured", len(overdue_runs(open_runs(folded), now_utc())), 1,
            "90s past a 60s budget is OVERDUE; 10s is not")
    control("verdict_fault_wins", status_verdict(["a fault"], overdue_runs(open_runs(folded), now_utc())),
            VERDICT_FAULT, "a fault outranks a budget: a broken reader is not a slow run")
    control("verdict_owner_owed", status_verdict([], overdue_runs(open_runs(folded), now_utc())),
            VERDICT_OWNER_OWED, "an overdue run is 2, loud and not fatal (BUG-457)")
    control("verdict_green", status_verdict([], []), VERDICT_OK, "an empty journal is green")
    control("duplicate_start_is_a_fault", len(fold([began, dict(began)])[1]), 1, "an act has ONE beginning")
    control("orphan_end_is_a_fault", len(fold([{**began, ROW_KIND: "end", "run": "DJ-ghost"}])[1]), 1,
            "an end with no start is a fault, never a run")
    control("unknown_kind_is_a_fault", len(fold([{**began, ROW_KIND: "pause"}])[1]), 1,
            "an undeclared row kind is refused")
    control("unreadable_line_is_a_fault", len(read_rows(scratch_lines(scratch / "broken.jsonl",
                                                                     ["not json at all"]))[1]), 1,
            "a reader that skips its unreadable line reports a shorter history as the whole one (C16)")
    control("missing_journal_is_empty", len(read_rows(scratch / "absent.jsonl")[0]), 0,
            "an absent ledger is zero rows, not an error")

    # ── the append ───────────────────────────────────────────────────────────────────────────────────────────
    ledger = scratch_lines(scratch / "ledger.jsonl", [])
    first = json.dumps(began, sort_keys=True)
    second = json.dumps({**began, ROW_KIND: "end", "run": "DJ-t", "state": "done"}, sort_keys=True)
    append_row(ledger, began, "selftest", receipt=False)
    append_row(ledger, {**began, ROW_KIND: "end", "run": "DJ-t", "state": "done"}, "selftest", receipt=False)
    reread, again = read_rows(ledger)
    control("append_then_read", len(reread) + len(again), 2, "the primitive appends two readable rows")
    control("append_is_a_suffix", len(ledger.read_bytes()), len(first) + 1 + len(second) + 1,
            "an append only ever ADDS bytes (BUG-560/D-2685)")
    virgin = scratch / "virgin.jsonl"
    if virgin.exists():
        virgin.unlink()
    append_row(virgin, began, "selftest", receipt=False)
    virgin_rows, virgin_faults = read_rows(virgin)
    control("virgin_ledger_is_created", 1 if len(virgin_rows) == 1 and not virgin_faults else 0, 1,
            "MEASURED 2026-10-16: the FIRST live start of a fresh tree crashed (FileNotFoundError), because the "
            "append proves a SUFFIX and there was no pre-image - the trace of a delegated run was lost by the writer "
            "that exists to prevent exactly that")
    missing_parent = scratch / "deep" / "ledger.jsonl"
    append_row(missing_parent, began, "selftest", receipt=False)
    control("ledger_parent_is_created", 1 if missing_parent.exists() else 0, 1,
            "a declared home whose directory does not exist is created by the writer, never left to the caller")
    proof = artifact_proof("governance/buglog.md", REPO_ROOT)
    control("artifact_present_verified", 1 if proof.get("present") and proof.get("sha256_16") else 0, 1,
            "a real artifact is verified ON DISK with its content stamp")
    control("artifact_absent_named", 1 if artifact_proof("temp/definitely-absent.md", REPO_ROOT)["present"] is False
            else 0, 1, "an absent artifact reads absent, never as an error and never as present")

    shutil.rmtree(root, ignore_errors=True)
    if failed:
        print("FAILED " + str(len(failed)) + " control(s) of " + str(passed + len(failed)) + ":")
        for line in failed:
            print("  !! " + line)
        return VERDICT_FAULT
    print("OK " + str(passed) + "/" + str(passed) + " known-answer controls (T-168/BUG-844/D-3036)")
    return VERDICT_OK


def main(argv: Sequence[str]) -> int:
    """Dispatch the verbs; an unknown verb is refused, never guessed."""
    if argv and argv[0] == "--selftest":
        return selftest()
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return VERDICT_OK
    verb, rest = argv[0], list(argv[1:])
    if verb == "start":
        return start_main(rest)
    if verb == "end":
        return end_main(rest)
    if verb == "status":
        return status_main(rest)
    print("FAIL-CLOSED (" + WRITER + "): unknown verb " + repr(verb) + " - use start|end|status|--selftest")
    return VERDICT_FAULT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
