#!/usr/bin/env python3
"""scripts/gov_sync.py - ONE writer + ONE check for the USER-FACING governance faces (D-2981).

WHY THIS EXISTS (measured, 2026-10-13). The agent-facing registers (config/decisions.yaml + its
census, governance/buglog.md + bug_status.json, config/task_register.yaml) and the human-facing
faces (DECISION-LOG.md, MASTER-TASK-REGISTER.md, governance/buglog.md, agent/session_seed.yaml) were
joined in exactly TWO places: the two census restatement lines. So:
  * agent/session_seed.yaml - BOOT-LOADED - sat seven days stale (pipeline_commit v3.0-D2370,
    status dated 2026-10-06) and propagated that drift into every session that read it;
  * MASTER-TASK-REGISTER.md and DECISION-LOG.md headers said 2026-10-07 while the registers had
    moved on, and MTR held 240 lines of prose where a register should be;
  * no machine-readable TASK register existed at all, so "how many tasks are open" had no answer.
A face nobody derives is a face that drifts.

WHAT IT OWNS (and therefore what a hand edit can no longer own):
  1. the GOV-INDEX block in each declared face - machine-rendered, byte-compared on --check;
  2. every census-shaped restatement line in those faces (the BUG-588/D-2692 rule: a restated count
     is stale the moment it is written, so it must be DERIVED) - this retires BUG-756;
  3. the derived scalar fields of agent/session_seed.yaml (session.pipeline_commit, session.status).

MODES (tri-state, BUG-457): 0 in sync | 1 drift (the faces are stale - run --apply) | 2 the
declaration or the registers are unreadable/incomplete (fail closed, C16).
    python3 scripts/gov_sync.py            # --check (the ladder runs this)
    python3 scripts/gov_sync.py --apply    # rewrite the faces from the registers
    python3 scripts/gov_sync.py --selftest # known-answer controls (a stale block MUST be seen to fail)
C6: every write is atomic (tempfile -> fsync -> os.replace) through the repo ONE home when available.
"""
from __future__ import annotations

import argparse
import importlib
import os
import pathlib
import re
import sys
import tempfile

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CFG_PATH = REPO / "config/gov_sync.yaml"
IDX_S = "<!-- GOV-INDEX:START (D-2981 - DERIVED by scripts/gov_sync.py; do NOT hand-edit inside) -->"
IDX_E = "<!-- GOV-INDEX:END -->"
HIS = "<!-- GOV-HISTORY:START (D-2981) - everything below is DATED HISTORY: append-only, NOT a register -->"
CENSUS_DEC = re.compile(r"\b\d+ decisions \(census stamp [0-9a-f]+, \d{4}-\d{2}-\d{2}\)")
CENSUS_BUG = re.compile(r"\b\d+ bugs \(\d+ open / \d+ closed;")
# The STAMP-LESS form (a face that restates the decision count without the census stamp - the shape
# MASTER-TASK-REGISTER.md used before D-2981). It must be owned too, or a history line keeps a stale
# count that the faces rail still reads.
CENSUS_DEC_BARE = re.compile(r"\b\d+ decisions(?= [^a-z])")
BUG_HEAD = re.compile(r"(?m)^## BUG-(\d{3,4})\b([^\n]*)")
SEV = re.compile(r"\b(CRITICAL|HIGH|MED|LOW)\b")
STATE = re.compile(r"\b(OPEN|CLOSED|FIXED|RESOLVED|SUPERSEDED|FILED|HELD)\b")
EXIT_OK, EXIT_DRIFT, EXIT_FAIL = 0, 1, 2


def cfg() -> dict:
    doc = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) or {}
    for key in ("registers", "faces", "open_decision_states", "severity_tokens", "task_priorities"):
        if key not in doc:
            raise SystemExit(f"FAIL-CLOSED (C16): {CFG_PATH.name} declares no {key!r} - the join has no home (D-2981)")
    return doc


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def derive(d: dict) -> dict:
    """Every number a face is allowed to print, READ FROM THE REGISTERS (never typed)."""
    reg = d["registers"]
    dec = yaml.safe_load(_read(reg["decisions"]["census"])) or {}
    bugs = yaml.safe_load(_read(reg["bugs"]["census"])) or {}
    tasks = yaml.safe_load(_read(reg["tasks"]["register"])) or {}
    man = yaml.safe_load(_read(reg["manifest"]["path"])) or {}
    version_value = man
    for part in str(reg["manifest"]["key"]).split("."):
        version_value = (version_value or {}).get(part) if isinstance(version_value, dict) else None
    states, by_cat = {}, {}
    summ = dec.get("summary", {}) or {}
    for k, v in summ.items():
        if isinstance(v, int):
            states[k] = v
    open_states = d["open_decision_states"]
    need_action = sum(states.get(s, 0) for s in open_states)
    tl = [t for t in (tasks.get("tasks") or []) if str(t.get("state")) not in ("done", "superseded")]
    pri = {p: sum(1 for t in tl if t.get("priority") == p) for p in d["task_priorities"]}
    gate = sum(1 for t in tl if t.get("state") == "gate")
    open_bugs = bugs.get("open") or []
    sev, unlab, headed_ids = severity_census(d)
    stamp8 = str(dec.get("decisions_sha256_16", ""))[:16]
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from lib import yaml_guard  # D-2648: the ONE home for "today" (a date constant can only go stale)
        today = yaml_guard.today()
    except ImportError:  # C16: named fallback, never a silent guess
        import datetime
        today = datetime.date.today().isoformat()
        print("  note: yaml_guard unavailable - using the system date for the face stamp")
    if os.environ.get("GOV_SYNC_DATE"):
        today = os.environ["GOV_SYNC_DATE"]
    return {
        "decisions_total": dec.get("total_decisions", 0), "states": states, "need_action": need_action,
        "stamp": stamp8, "date": today,
        "bugs_total": bugs.get("total_ids", 0), "bugs_open": bugs.get("open_n", 0), "bugs_closed": bugs.get("closed_n", 0),
        "sev": sev, "unlabelled": len(unlab), "open_bugs": open_bugs, "headed_ids": headed_ids,
        "tasks": tl, "pri": pri, "gate": gate, "tasks_total": len(tl),
        "version": str(version_value or "unknown"),
        "open_states": open_states,
    }


def register_truth(d: dict, x: dict) -> str:
    """The ONE restatement line - shaped for the faces rail's own regex (BUG-588/D-2692)."""
    return (f"{x['decisions_total']} decisions (census stamp {x['stamp']}, {x['date']}) · "
            f"{x['bugs_total']} bugs ({x['bugs_open']} open / {x['bugs_closed']} closed; "
            f"highest OPEN = {str(x['open_bugs'][-1]['id']) if x['open_bugs'] else 'none'}) · "
            f"{x['tasks_total']} open tasks (MUST {x['pri'].get('MUST', 0)} / SHOULD {x['pri'].get('SHOULD', 0)} / "
            f"WORTH {x['pri'].get('WORTH', 0)}; gate {x['gate']})")


def render_block(d: dict, x: dict, decs: list | None = None) -> str:
    lim = int(d.get("face_list_limit", 12))
    out = [IDX_S,
           "> **LIVE INDEX (D-2981 - DERIVED; do NOT hand-edit inside these sentinels).**",
           f"> Register truth (BUG-588/D-2692 - the census is the ONE home; nothing below restates a count): {register_truth(d, x)}.",
           ">",
           f"> Decisions NEEDING ACTION: **{x['need_action']}** of {x['decisions_total']} — " +
           " · ".join(f"{s} {x['states'].get(s, 0)}" for s in x["open_states"]) +
           f" | in effect (active) {x['states'].get('active', 0)} | closed: resolved {x['states'].get('resolved', 0)}, "
           f"superseded {x['states'].get('superseded', 0)}, archived {x['states'].get('archived', 0)}, rejected {x['states'].get('rejected', 0)}",
           ">",
           f"> Open BUGS by severity (heading population, first heading per id): CRITICAL {x['sev'].get('CRITICAL', 0)} · HIGH {x['sev'].get('HIGH', 0)} · "
           f"MED {x['sev'].get('MED', 0)} · LOW {x['sev'].get('LOW', 0)} · UNLABELLED {x['unlabelled']} (BUG-757) of {x['bugs_open']} open.",
           ">",
           "> **MUST tasks (strategic-consequential order — source: config/task_register.yaml):**",
           ">",
           "> | id | pri | state | task | evidence |",
           "> |---|---|---|---|---|"]
    order = {p: i for i, p in enumerate(d["task_priorities"])}
    for t in sorted(x["tasks"], key=lambda t: (order.get(t.get("priority"), 9), str(t.get("id"))))[:lim]:
        ev = str(t.get("evidence", ""))[:90].replace("|", "/")
        out.append(f"> | {t.get('id')} | {t.get('priority')} | {t.get('state')} | {str(t.get('title',''))[:110]} | {ev} |")
    out += [">",
            "> **Open decisions needing action (newest first; the states are DECLARED in config/gov_sync.yaml):**",
            ">",
            "> | id | state | category | title |",
            "> |---|---|---|---|"]
    decs = _open_decisions(d, x) if decs is None else decs
    for e in decs[:lim]:
        out.append(f"> | {e['id']} | {e['state']} | {str(e.get('category',''))[:26]} | {str(e.get('title',''))[:100]} |")
    out += [">",
            f"> **Open bugs, most severe first:** " +
            " · ".join(f"{b['id']}" for b in _severe(x)[:lim]) + ".",
            IDX_E]
    return "\n".join(out)


def _open_decisions(d: dict, x: dict) -> list:
    reg = d["registers"]["decisions"]["registry"]
    doc = yaml.safe_load(_read(reg)) or {}
    out = []
    for e in doc.get("decisions") or []:
        if str(e.get("state", "")).lower() in d["open_decision_states"]:
            out.append({"id": e.get("id"), "state": e.get("state"), "category": e.get("category"), "title": e.get("title")})
    return sorted(out, key=lambda e: str(e["id"]), reverse=True)


def _severe(x: dict) -> list:
    rank = {"CRITICAL": 0, "HIGH": 1, "MED": 2, "LOW": 3}
    def key(b):
        m = SEV.search(str(b.get("title", "")).upper())
        return (rank.get(m.group(1), 9) if m else 9, str(b.get("id")))
    return sorted(x["open_bugs"], key=key)


def render_seed_status(d: dict, x: dict) -> str:
    top = [t for t in x["tasks"] if t.get("priority") == "MUST"][:3]
    nxt = "; ".join(f"({i+1}) {str(t.get('title'))[:90]}" for i, t in enumerate(top))
    return (f"{x['date']} D-2981: the user-facing faces are DERIVED (scripts/gov_sync.py) and "
            f"joined to the registers. Register: {x['decisions_total']} decisions ({x['need_action']} needing action) / "
            f"{x['bugs_total']} bugs ({x['bugs_open']} open) / {x['tasks_total']} open tasks. "
            f"NEXT: {nxt}.")


def _extract_block(text: str) -> str | None:
    """The CURRENT block bytes, or None when the face carries no block (the honest comparison:
    compare the bytes IN THE FILE to the bytes the renderer produces - not two rewrites of them)."""
    if IDX_S not in text or IDX_E not in text:
        return None
    s = text.index(IDX_S)
    return text[s:text.index(IDX_E, s) + len(IDX_E)]


def _replace_block(text: str, block: str) -> tuple:
    """Replace the sentinel block (or insert it where the face's live-index heading is)."""
    if IDX_S in text:
        s = text.index(IDX_S)
        e = text.index(IDX_E, s) + len(IDX_E)
        return text[:s] + block + text[e:], "replaced"
    return text, "absent"


def _recut_census(text: str, truth: str, d: dict, x: dict) -> tuple:
    """Own EVERY restatement line in the face (BUG-588/D-2692; closes BUG-756)."""
    dec_sub = f"{x['decisions_total']} decisions (census stamp {x['stamp']}, {x['date']})"
    n0 = len(CENSUS_DEC_BARE.findall(text))
    bug_sub = f"{x['bugs_total']} bugs ({x['bugs_open']} open / {x['bugs_closed']} closed;"
    n1 = len(CENSUS_DEC.findall(text))
    n2 = len(CENSUS_BUG.findall(text))
    text = CENSUS_DEC.sub(dec_sub, text)
    text = CENSUS_DEC_BARE.sub(f"{x['decisions_total']} decisions", text)
    text = CENSUS_BUG.sub(bug_sub, text)
    return text, n0 + n1 + n2


def severity_census(d: dict) -> tuple:
    """ONE population for both the severity distribution and the gap (BUG-757).

    POPULATION, stated so the number is reproducible: the FIRST heading for each bug id (a later
    heading is an UPDATE of the same bug), whose state token is OPEN (a CLOSED heading needs no
    severity - it is not in the open set), carrying a CRITICAL/HIGH/MED/LOW token or not. The
    register-truth line keeps the CENSUS (governance/bug_status.json) open count separately: two
    populations, both named, neither hidden.
    """
    log = _read(d["registers"]["bugs"]["log"])
    seen, sev, unlab = set(), {s: 0 for s in d["severity_tokens"]}, []
    for m in BUG_HEAD.finditer(log):
        bid, head = "BUG-" + m.group(1), m.group(2).upper()
        if bid in seen:
            continue
        seen.add(bid)
        if "UPDATE" in head:
            continue
        st = STATE.search(head)
        if st and st.group(1) != "OPEN":
            continue
        s2 = SEV.search(head)
        if s2 and s2.group(1) in sev:
            sev[s2.group(1)] += 1
        else:
            unlab.append(bid)
    return sev, unlab, len(seen)


def severity_gap(d: dict) -> list:
    """Open bug headings with NO severity token (BUG-757) - the SHRINK-ONLY ceiling's population."""
    return severity_census(d)[1]


def _write(path: pathlib.Path, text: str) -> str:
    try:
        wg = importlib.import_module("lib.write_guard")
        # D-401/I1: EVERY governed write declares its writer and what it owns. OWNED_ANY is the
        # declared marker for "this writer owns the whole artifact" (the faces are DERIVED in full).
        wg.write_document(path, text, writer="scripts/gov_sync.py", owned_keys={getattr(wg, "OWNED_ANY", "*")})
        return "write_guard"
    except ImportError:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, path)
        print("  note: write_guard unavailable - atomic write without a receipt (scripts/lib on sys.path?)")
        return "atomic"


def check(d: dict, x: dict) -> int:
    faults = []
    for face in d["faces"]:
        p = REPO / face["path"]
        text = p.read_text(encoding="utf-8", errors="replace")
        if face.get("index_block"):
            if IDX_S not in text or IDX_E not in text:
                faults.append(f"{face['path']}: no GOV-INDEX block (run --apply); a face with no derived block cannot be checked")
            else:
                cur = _extract_block(text)
                want = render_block(d, x)
                if cur != want:
                    faults.append(f"{face['path']}: the GOV-INDEX block is STALE (the bytes in the file differ "
                                  f"from the bytes the registers derive - run --apply)")
            if face.get("history_boundary") and HIS not in text:
                faults.append(f"{face['path']}: no GOV-HISTORY-START marker - history is not declared")
        if face.get("derived_fields"):
            for f in face["derived_fields"]:
                val = _field(text, f["key"])
                want = x["version"] if f["from"] == "manifest" else render_seed_status(d, x)
                if val != want:
                    faults.append(f"{face['path']}: {f['key']} is STALE (derived value differs)")
    bad = severity_gap(d)
    ceil = int(d.get("severity_grandfathered", 0))
    if len(bad) > ceil:
        faults.append(f"buglog: {len(bad)} open-ish heading(s) carry no severity token, over the shrink-only ceiling {ceil} "
                      f"(BUG-757). New: {bad[ceil:][:6]}")
    for f in faults:
        print("  !! " + f)
    if faults:
        print(f"FAIL gov-sync: {len(faults)} join fault(s) - the faces do not equal their re-derivation (D-2981)")
        return EXIT_DRIFT
    print(f"ok gov-sync: {len(d['faces'])} face(s) equal their re-derivation from the registers "
          f"({x['decisions_total']} decisions / {x['bugs_total']} bugs / {x['tasks_total']} open tasks)")
    return EXIT_OK


def _field(text: str, dotted: str) -> str:
    """Read a scalar from an indented YAML face (session_seed), never a guess: None when absent."""
    key = dotted.split(".")[-1]
    m = re.search(rf"(?m)^[ \t]*{re.escape(key)}:[ \t]*(.+)$", text)
    return m.group(1).strip().strip("'") if m else None


def apply(d: dict, x: dict) -> int:
    block = render_block(d, x)
    for face in d["faces"]:
        p = REPO / face["path"]
        before = p.read_text(encoding="utf-8", errors="replace")
        text = before
        if face.get("index_block"):
            text, how = _replace_block(text, block)
            if how == "absent":
                text = _insert_block(text, face["path"], block)
        if face.get("history_boundary") and HIS not in text:
            text = text.replace(IDX_E, IDX_E + "\n\n" + HIS, 1)
        text, n = _recut_census(text, register_truth(d, x), d, x)
        if face.get("derived_fields"):
            for f in face["derived_fields"]:
                val = x["version"] if f["from"] == "manifest" else render_seed_status(d, x)
                key = f["key"].split(".")[-1]
                text = re.sub(rf"(?m)^([ \t]*){re.escape(key)}:.*$", lambda m: f"{m.group(1)}{key}: '{val}'", text, count=1)
        if text != before:
            route = _write(p, text)
            print(f"  wrote {face['path']} ({route}; census lines re-cut: {n})")
        else:
            print(f"  unchanged {face['path']}")
    return check(d, x)


def _insert_block(text: str, rel: str, block: str) -> str:
    """Insert the block after the face's own live-index heading (declared, not guessed)."""
    anchors = {
        "MASTER-TASK-REGISTER.md": r"(?m)^## 🔴 MUST — open[^\n]*$",
        "DECISION-LOG.md": r"(?m)^## 🔴 CURRENT OPEN / PENDING INDEX[^\n]*$",
        "governance/buglog.md": r"(?m)^---$",
    }
    pat = anchors.get(rel)
    if not pat:
        raise SystemExit(f"FAIL-CLOSED: no declared insertion anchor for {rel} (D-2981)")
    m = re.search(pat, text)
    if not m:
        raise SystemExit(f"FAIL-CLOSED: {rel} has no match for its declared anchor - refusing to guess where a block goes")
    return text[:m.end()] + "\n\n" + block + "\n" + text[m.end():]


def selftest() -> int:
    """Known-answer controls: a STALE block must be SEEN to fail (BUG-492)."""
    d = {"registers": {}, "faces": [], "open_decision_states": ["open"], "severity_tokens": ["CRITICAL", "HIGH", "MED", "LOW"],
         "task_priorities": ["MUST", "SHOULD", "WORTH"], "face_list_limit": 12, "severity_grandfathered": 0}
    x = {"decisions_total": 7, "states": {"open": 2, "active": 3, "resolved": 2}, "need_action": 2, "stamp": "deadbeefdeadbeef",
         "date": "2026-01-02", "bugs_total": 5, "bugs_open": 3, "bugs_closed": 2, "sev": {"CRITICAL": 1, "HIGH": 1, "MED": 0, "LOW": 0},
         "unlabelled": 1, "open_bugs": [{"id": "BUG-001", "title": "(LOW - OPEN) x"}, {"id": "BUG-003", "title": "(CRITICAL - OPEN) y"}],
         "tasks": [{"id": "T-1", "priority": "MUST", "state": "open", "title": "t", "evidence": "e"}], "pri": {"MUST": 1, "SHOULD": 0, "WORTH": 0},
         "gate": 0, "tasks_total": 1, "version": "v9.9", "open_states": ["open"]}
    ok = 0
    truth = register_truth(d, x)
    assert re.search(r"\b5 bugs \(3 open / 2 closed;", truth), "register_truth must satisfy the faces rail regex"
    ok += 1
    blk = render_block(d, x, decs=[{"id": "D-1", "state": "open", "category": "X", "title": "t"}])
    assert IDX_S in blk and IDX_E in blk and "deadbeefdeadbeef" in blk, "block must carry the census stamp"
    ok += 1
    face = "## 🔴 MUST — open (x)\n\n" + blk + "\n\ntail line\n"
    out, how = _replace_block(face, blk)
    assert how == "replaced" and out == face, "replacing a block with itself must be a no-op (idempotence)"
    ok += 1
    stale, _ = _replace_block(face, blk.replace("deadbeefdeadbeef", "0000000000000000"))
    assert stale != face, "a STALE block must differ from its re-derivation"
    ok += 1
    recut, n = _recut_census("x 99 decisions (census stamp 0000000000000000, 1999-01-01) · 42 bugs (1 open / 41 closed; y", truth, d, x)
    assert n >= 2 and "deadbeefdeadbeef" in recut and "5 bugs (3 open / 2 closed;" in recut, "census re-cut must own both shapes"
    ok += 1
    bare, n2 = _recut_census("Register truth: 99 decisions · 42 bugs (1 open / 41 closed; y", truth, d, x)
    assert n2 >= 2 and "7 decisions ·" in bare, "the STAMP-LESS restatement must be owned too (the MTR pre-D-2981 shape)"
    ok += 1
    assert _insert_block("## 🔴 MUST — open (x)\nbody\n", "MASTER-TASK-REGISTER.md", blk).count(IDX_S) == 1, "insert anchor"
    ok += 1
    assert _extract_block(face) == blk, "extract must return the block BYTES (the check compares these, not a rewrite)"
    assert _extract_block(face.replace("deadbeefdeadbeef", "0000000000000000")) != blk, "a modified block must compare UNEQUAL"
    ok += 2
    print(f"ok gov-sync --selftest: {ok}/9 known answers (a stale block is DETECTED, not trusted)")
    return EXIT_OK


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    d = cfg()
    x = derive(d)
    if "--apply" in argv:
        return apply(d, x)
    return check(d, x)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
