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

import os
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
# D-2982/D-401: a STATIC import, deliberately. This module is a declared writer_of_record, and the ownership
# audit could not SEE the lazy `importlib.import_module("lib.write_guard")` - so the invariant that exists to
# prevent BUG-478 read as unenforced for this writer while it was in fact guarded. The old ImportError
# fallback also wrote WITHOUT a receipt (tempfile + os.replace), i.e. the one path that most needed the guard
# was the one path that bypassed it; failing to import the guard is now a loud import error (C16).
from lib.write_guard import OWNED_ANY, write_document  # noqa: E402
CFG_PATH = REPO / "config/gov_sync.yaml"
IDX_S = "<!-- GOV-INDEX:START (D-2981 - DERIVED by scripts/gov_sync.py; do NOT hand-edit inside) -->"
IDX_E = "<!-- GOV-INDEX:END -->"
HIS = ("<!-- GOV-HISTORY:START (D-2981/D-2986) - below this line a face makes NO LIVE CLAIM: the INDEX "
       "sections are declared HAND INDEXES (row-joined on every run of the rail, never the authority) and the "
       "rest is DATED HISTORY (append-only). The DERIVED block above is the ONE authority for the current "
       "state. -->")
CENSUS_DEC = re.compile(r"\b\d+ decisions \(census stamp [0-9a-f]+, \d{4}-\d{2}-\d{2}\)")
CENSUS_BUG = re.compile(r"\b\d+ bugs \(\d+ open / \d+ closed;")
# The STAMP-LESS form (a face that restates the decision count without the census stamp - the shape
# MASTER-TASK-REGISTER.md used before D-2981). It must be owned too, or a history line keeps a stale
# count that the faces rail still reads.
CENSUS_DEC_BARE = re.compile(r"\b\d+ decisions(?= [^a-z])")
# D-2985/BUG-757: ANY hash depth. The old reader required EXACTLY two hashes, so a bug written as
# `### BUG-426 (HIGH, OPEN ...)` was invisible to the census - the SAME visibility defect the buglog
# records for BUG-426/BUG-427 ("HEADER_RE was ^##\s+(BUG-\d+) - EXACTLY two hashes ... so the rail never
# saw them"). The lesson was recorded and never propagated to this reader; MEASURED 2026-10-13: 18 open
# ids were invisible to the severity census for exactly this reason.
BUG_HEAD = re.compile(r"(?m)^#{1,6}\s*BUG-(\d{3,4})\b([^\n]*)")
# D-2985: a count that a REGISTER owns has ONE home. A task title is what the face PRINTS, so a measured
# count stored there is stale the moment it is written (BUG-588/D-2692) and the face then contradicts the
# census line three lines above it - MEASURED: T-104's title said "108 of 185 open bugs" while the block's
# own census said 125 and the joined truth was 101. Three answers, one question, one screen.
_CNT = r"(?<![-\w])\d[\d,]*"
COUNT_NOUN_RE = re.compile(rf"{_CNT}(?:\s+\w+)?(?:\s+\w+)?\s+(?:bugs?|tasks?|decisions?|rows?)\b", re.IGNORECASE)
CENSUS_SCALAR_RE = re.compile(rf"\b(?:open|closed)\s*[=:]\s*{_CNT}\b|\b{_CNT}\s+(?:open|closed)\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
SEV = re.compile(r"\b(CRITICAL|HIGH|MED|LOW)\b")
STATE = re.compile(r"\b(OPEN|CLOSED|FIXED|RESOLVED|SUPERSEDED|FILED|HELD)\b")
EXIT_OK, EXIT_DRIFT, EXIT_FAIL = 0, 1, 2


def cfg() -> dict:
    doc = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) or {}
    for key in ("registers", "faces", "open_decision_states", "severity_tokens", "task_priorities",
                "task_states", "task_movers", "owner_gate_token", "face_owner_lane_label",
                "state_glyphs", "decision_in_effect_states", "decision_closed_states",
                "decision_void_states"):
        if key not in doc:
            raise SystemExit(f"FAIL-CLOSED (C16): {CFG_PATH.name} declares no {key!r} - the join has no home (D-2981)")
    return doc


def task_faults(tasks: list, d: dict) -> list[str]:
    """D-2985: the task register must obey its OWN declared schema (PURE - no I/O, so the oracle is testable).

    Four limbs, each with the failure it prevents:
      (1) a standing RULE is not a task: an `R-` id must be `state: rule` and is never counted as open work
          (MEASURED: R-1 sat at rank #1 of the MUST list in every face, because a rule never closes);
      (2) WHO must act is DECLARED, not inferred: `mover` is REQUIRED and must be one of the declared movers
          (a face that cannot say who must move a task cannot answer the owner's only question);
      (3) an owner GATE is a mover, and the gate text must name the owner's word - and a pipeline-moved task
          may not carry a gate that names the owner (the two fields would disagree);
      (4) a count a register owns has ONE home: a measured count in `title`/`why` is a restatement that goes
          stale (BUG-588/D-2692), and a count in `evidence` must carry its date (D-2660: a citation is a
          claim about the tree at the MOMENT OF MINT).
    """
    states, movers = set(d["task_states"]), set(d["task_movers"])
    token = str(d["owner_gate_token"]).lower()
    out: list[str] = []
    seen: set[str] = set()
    for t in tasks or []:
        tid = str(t.get("id", "")).strip()
        if not tid:
            out.append("a task entry carries no id - a task with no id cannot be closed, diffed or cited")
            continue
        if tid in seen:
            out.append(f"{tid} is declared twice in the same register - one task, one home (D-2642)")
        seen.add(tid)
        st, mv = str(t.get("state", "")), str(t.get("mover", ""))
        gate = str(t.get("gate", "none")).strip().lower()
        if st not in states:
            out.append(f"{tid}: state {st!r} is not one of {sorted(states)} - a task's state is DECLARED "
                       f"(gatehood is mover: owner, not a state of its own)")
        if mv not in movers:
            out.append(f"{tid}: mover {mv!r} is not one of {sorted(movers)} - WHO must act is REQUIRED on "
                       f"every entry (D-2985): without it the face cannot separate what only the OWNER can "
                       f"move from what the pipeline will move")
        if tid.startswith("R-") and st != "rule":
            out.append(f"{tid}: an `R-` id is a STANDING RULE, not a task - state must be 'rule', because a "
                       f"rule that never closes must never be counted as open work")
        if mv == "owner" and gate in ("", "none"):
            out.append(f"{tid}: mover: owner but gate is 'none' - name the owner's word that unblocks it "
                       f"(a task cannot be gated on a person who is never told what to decide)")
        if mv != "owner" and token and token in gate:
            out.append(f"{tid}: the gate names the {token!r} but mover says {mv!r} - the two fields disagree; "
                       f"a task the pipeline cannot advance is mover: owner")
        for field in ("title", "why"):
            m = COUNT_NOUN_RE.search(str(t.get(field, ""))) or CENSUS_SCALAR_RE.search(str(t.get(field, "")))
            if m:
                out.append(f"{tid}.{field} restates a measured count ({m.group(0)!r}) - a count a register "
                           f"owns has ONE home (BUG-588/D-2692): state it in `evidence` with its date, or "
                           f"leave it to the census the faces derive from the block")
        ev = str(t.get("evidence", ""))
        if re.search(r"\d", ev) and not DATE_RE.search(ev):
            out.append(f"{tid}.evidence carries a measurement with no date - a citation is a claim at the "
                       f"MOMENT OF MINT (D-2660): add the date it was measured")
    return out


def _read(rel: str) -> str:
    # D-2982 (C16): STRICT - a face that cannot be decoded must fail loud, not be silently repaired into a
    # byte-identical-looking text this writer would then rewrite from (BUG-521 class).
    return (REPO / rel).read_text(encoding="utf-8")


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
    all_tasks = tasks.get("tasks") or []
    faults = task_faults(all_tasks, d)
    if faults:  # C16: a register that breaks its own declared schema is not readable-as-true
        for f in faults:
            print("  !! " + f)
        raise SystemExit(EXIT_FAIL)
    # D-2985: a RULE is never open work; a task's MOVER decides which lane of the face it belongs to.
    live = [t for t in all_tasks if str(t.get("state")) not in ("done", "superseded", "rule")]
    rules = [t for t in all_tasks if str(t.get("state")) == "rule"]
    pri = {p: sum(1 for t in live if t.get("priority") == p) for p in d["task_priorities"]}
    owner_moved = [t for t in live if t.get("mover") == "owner"]
    pipeline_moved = [t for t in live if t.get("mover") != "owner"]
    open_bugs = bugs.get("open") or []
    open_ids = [str(b.get("id")) for b in open_bugs]
    # ONE population for OPEN-ness (the census) and one for severity (the id's first heading at ANY depth).
    sev, unlab = severity_census(d, set(open_ids))
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
        "sev": sev, "unlabelled": len(unlab), "open_bugs": open_bugs, "headed_ids": len(open_ids),
        "tasks": live, "rules": rules, "all_tasks": all_tasks, "pri": pri,
        "owner_moved": owner_moved, "pipeline_moved": pipeline_moved,
        "tasks_total": len(live),
        "version": str(version_value or "unknown"),
        "open_states": open_states,
    }


def register_truth(d: dict, x: dict) -> str:
    """The ONE restatement line - shaped for the faces rail's own regex (BUG-588/D-2692).

    D-2985: the task half of the line now names WHO must move the work. A bare "15 open tasks" was true of
    three different situations at once - a standing rule that never closes, work only the OWNER can advance,
    and work the pipeline will advance - which is what made the top of every face unreadable: the owner saw
    obligations he had already given the agent, and the agent saw a gate it could never pass.
    """
    return (f"{x['decisions_total']} decisions (census stamp {x['stamp']}, {x['date']}) · "
            f"{x['bugs_total']} bugs ({x['bugs_open']} open / {x['bugs_closed']} closed; "
            f"highest OPEN = {str(x['open_bugs'][-1]['id']) if x['open_bugs'] else 'none'}) · "
            f"{x['tasks_total']} open tasks (MUST {x['pri'].get('MUST', 0)} / SHOULD {x['pri'].get('SHOULD', 0)} / "
            f"WORTH {x['pri'].get('WORTH', 0)}; OWNER-moved {len(x['owner_moved'])}, "
            f"pipeline-moved {len(x['pipeline_moved'])}; {len(x['rules'])} standing rule(s) never close)")


def _glyph(d: dict, word: str) -> str:
    """D-2987: the DECLARED sign for a state word, or '' when the map declares none.

    The RENDERER does not fail closed here - the completeness control is the rail
    (scripts/check_governance_faces.py#glyph_faults), so one missing key is reported as a fault against the
    DECLARATION instead of crashing every face this writer owns.
    """
    return str((d.get("state_glyphs") or {}).get(str(word), ""))


def _cell(d: dict, word: str, text) -> str:
    """The sign AND the text ('🔴 open 32'), through ONE helper.

    One helper, so every surface renders a state the same way, and so the sign can never be hand-typed into a
    face: it is a RENDERING of the state the register owns, never a second home (D-2987, D-2642).
    """
    g = _glyph(d, word)
    return f"{g} {text}".strip()


def _sev_of(bug: dict) -> str:
    """A bug's declared severity word, read from its OWN heading (the register's slot, D-2985)."""
    m = SEV.search(str(bug.get("title", "")).upper())
    return m.group(1) if m else ""


def _dec_bucket(d: dict, label: str, states: list, x: dict) -> str:
    """One DECLARED decision bucket, as the face renders it.

    D-2987/C28: a state the register counts as ZERO is SUPPRESSED and an empty bucket prints nothing - the
    face is a VIEW (face_list_limit's rule: the full set stays in the registers). The axis is not weakened by
    this: it stays DECLARED in config/gov_sync.yaml and check_governance_faces.partition_faults still fails
    closed if a counted state has no bucket. MEASURED before suppression: three always-zero void states were
    printed into the block that a boot-loaded face carries into EVERY session.
    """
    live = [(s, x["states"].get(s, 0)) for s in states if x["states"].get(s, 0)]
    if not live:
        return ""
    return f" | {label}: " + " · ".join(f"{_cell(d, s, s)} {n}" for s, n in live)


def _hidden_rows(d: dict, shown: int, total: int) -> list:
    """The rows a face did NOT print must be named (BUG-842/T-142).

    MEASURED 2026-10-16, by the owner reading his own face and asking why the lane never moved: the PIPELINE
    LANE announced 35 and printed 12 with nothing saying so, and because it sorts by (priority, id) the rows
    it prints are the MUST tasks - exactly the rows that outlive a session. A face IS a view
    (config/gov_sync.yaml#face_list_limit), but a view that does not SAY it is one reports 35 and shows 12
    with no lie anyone can catch. The note's text is DECLARED in config, never typed here (C12).
    """
    if total <= shown:
        return []
    note = str(d["face_list_truncation_note"])
    for token, value in (("{shown}", shown), ("{total}", total), ("{limit}", shown)):
        note = note.replace(token, str(value))
    return [">", "> _" + note + "_"]


def render_block(d: dict, x: dict, decs: list | None = None) -> str:
    lim = int(d.get("face_list_limit", 12))
    order = {p: i for i, p in enumerate(d["task_priorities"])}
    out = [IDX_S,
           "> **LIVE INDEX (D-2981 - DERIVED; do NOT hand-edit inside these sentinels).**",
           f"> Register truth (BUG-588/D-2692 - the census is the ONE home; nothing below restates a count): {register_truth(d, x)}.",
           ">",
           # D-2987 (BUG-765): every DECLARED bucket is printed, so the line accounts for the WHOLE
           # register instead of the part it used to name. The buckets PARTITION the axis
           # (check_governance_faces.partition_faults), so the counts below are exact by construction -
           # MEASURED before this: 981 of 1114, with 133 `ratified` decisions invisible.
           f"> Decisions NEEDING ACTION: **{x['need_action']}** of {x['decisions_total']} — " +
           (" · ".join(f"{_cell(d, s, s)} {x['states'].get(s, 0)}" for s in x["open_states"]
                       if x['states'].get(s, 0)) or "none") +
           "".join(_dec_bucket(d, lbl, d[bucket], x) for lbl, bucket in
                   (("in effect", "decision_in_effect_states"),
                    ("closed", "decision_closed_states"),
                    ("void (never used)", "decision_void_states"))) +
           f" — the DECLARED buckets sum to the whole register ({x['decisions_total']}, D-2987/BUG-765)",
           ">",
           f"> Open BUGS by severity (population = the census's {x['bugs_open']} open ids; severity read from each id's FIRST heading at ANY hash depth): {_cell(d, 'CRITICAL', 'CRITICAL')} {x['sev'].get('CRITICAL', 0)} · "
           f"{_cell(d, 'HIGH', 'HIGH')} {x['sev'].get('HIGH', 0)} · {_cell(d, 'MED', 'MED')} {x['sev'].get('MED', 0)} · "
           f"{_cell(d, 'LOW', 'LOW')} {x['sev'].get('LOW', 0)} · UNLABELLED {x['unlabelled']} (BUG-757) of {x['bugs_open']} open.",
           ">",
           # D-2985: the OWNER LANE leads. The four previous lines said "MUST tasks" and stopped there, so a
           # standing rule, two owner-gated items and one actionable task rendered as one list in priority
           # order - and the owner, reading his own register, saw three things he had already handed over.
           f"> **{d['face_owner_lane_label']} ({len(x['owner_moved'])}) — what ONLY YOU can move; the pipeline cannot "
           f"advance these, each needs YOUR word:**",
           ">",
           "> | id | pri | what YOU decide | the gate |",
           "> |---|---|---|---|"]
    for t in sorted(x["owner_moved"], key=lambda t: (order.get(t.get("priority"), 9), str(t.get("id")))):
        out.append(f"> | {t.get('id')} | {_cell(d, t.get('priority'), t.get('priority'))} | "
                   f"{str(t.get('title',''))[:110]} | {str(t.get('gate',''))[:70]} |")
    out += [">",
            f"> **{d['face_pipeline_lane_label']} ({len(x['pipeline_moved'])}) — {d['face_pipeline_lane_note']}:**",
            ">",
            "> | id | pri | state | task | evidence |",
            "> |---|---|---|---|---|"]
    for t in sorted(x["pipeline_moved"], key=lambda t: (order.get(t.get("priority"), 9), str(t.get("id"))))[:lim]:
        ev = str(t.get("evidence", ""))[:90].replace("|", "/")
        out.append(f"> | {t.get('id')} | {_cell(d, t.get('priority'), t.get('priority'))} | "
                   f"{_cell(d, t.get('state'), t.get('state'))} | {str(t.get('title',''))[:110]} | {ev} |")
    out += _hidden_rows(d, lim, len(x["pipeline_moved"]))
    if x["rules"]:
        out += [">",
                f"> **STANDING RULES — in effect, never close ({len(x['rules'])}):**",
                ">",
                "> | id | rule |",
                "> |---|---|"]
        for t in x["rules"]:
            out.append(f"> | {_cell(d, 'rule', t.get('id'))} | {str(t.get('title',''))[:120]} |")
    out += [">",
            "> **Open decisions needing action (newest first; the states are DECLARED in config/gov_sync.yaml):**",
            ">",
            "> | id | state | category | title |",
            "> |---|---|---|---|"]
    decs = _open_decisions(d, x) if decs is None else decs
    for e in decs[:lim]:
        out.append(f"> | {e['id']} | {e['state']} | {str(e.get('category',''))[:26]} | {str(e.get('title',''))[:100]} |")
    out += _hidden_rows(d, lim, len(decs))
    out += [">",
            f"> **Open bugs, most severe first:** " +
            " · ".join(_cell(d, _sev_of(b), b["id"]) for b in _severe(x)[:lim]) + ".",
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
    """D-2985: the BOOT face leads with the OWNER's obligations.

    session_seed.yaml is loaded at boot, so it is the one derived face that reaches EVERY session. It used
    to render the top three MUST tasks - which was, in fact, a standing rule the pipeline keeps itself, plus
    two items only the owner can move; the actionable work never appeared. The boot line now says what the
    owner must decide and what the agent will do, in that order.
    """
    own = "; ".join(f"{_cell(d, t.get('priority'), t.get('id'))} {str(t.get('title'))[:70]}" for t in
                    sorted(x["owner_moved"], key=lambda t: str(t.get("id")))[:3]) or "nothing"
    nxt = "; ".join(f"{_cell(d, t.get('priority'), t.get('id'))} {str(t.get('title'))[:70]}" for t in
                    sorted(x["pipeline_moved"], key=lambda t: str(t.get("id")))[:3]) or "nothing"
    return (f"{x['date']} D-2981: the user-facing faces are DERIVED (scripts/gov_sync.py) and "
            f"joined to the registers. Register: {x['decisions_total']} decisions ({x['need_action']} needing action) / "
            f"{x['bugs_total']} bugs ({x['bugs_open']} open) / {x['tasks_total']} open tasks "
            f"({len(x['owner_moved'])} OWNER-moved, {len(x['pipeline_moved'])} pipeline). "
            f"YOURS: {own}. AGENT NEXT: {nxt}.")


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
    """Own EVERY restatement line in the face's LIVE region (BUG-588/D-2692; closes BUG-756).

    D-2985 (SCOPE): the region BELOW the history marker is NOT re-cut. It is declared "DATED HISTORY:
    append-only, NOT a register" (D-2981), and MEASURED 2026-10-13 this writer was rewriting counts inside
    those snapshots to TODAY'S value while the line still said "as measured then" - i.e. this writer was
    making historical claims FALSE, the one thing the history declaration forbids (R-D410). A historical
    count is scoped by the moment the line names; the derived block owns the current one.
    """
    head, sep, tail = text.partition(HIS)
    dec_sub = f"{x['decisions_total']} decisions (census stamp {x['stamp']}, {x['date']})"
    n0 = len(CENSUS_DEC_BARE.findall(head))
    bug_sub = f"{x['bugs_total']} bugs ({x['bugs_open']} open / {x['bugs_closed']} closed;"
    n1 = len(CENSUS_DEC.findall(head))
    n2 = len(CENSUS_BUG.findall(head))
    head = CENSUS_DEC.sub(dec_sub, head)
    head = CENSUS_DEC_BARE.sub(f"{x['decisions_total']} decisions", head)
    head = CENSUS_BUG.sub(bug_sub, head)
    return head + sep + tail, n0 + n1 + n2


def severity_census(d: dict, open_ids: set[str]) -> tuple:
    """ONE population for both the severity distribution and the gap (BUG-757, re-measured by D-2985).

    POPULATION, stated so the number is reproducible: the ids the CENSUS calls OPEN (governance/bug_status.json
    - the ONE home for OPEN-ness, D-2642), each carrying the severity token of its FIRST heading at ANY hash
    depth (a later heading is an UPDATE of the same bug). Both halves were wrong before and in opposite
    directions, which is why the line could not be checked: the old reader re-derived OPEN-ness from a heading
    token (so 88 bugs the register calls CLOSED were counted as open) and required EXACTLY two hashes (so 18
    open bugs written with three were invisible - the BUG-426/427 class). MEASURED 2026-10-13: 255 counted
    open-ish vs 185 open, and the parts summed to 255 for a population of 185.
    """
    log = _read(d["registers"]["bugs"]["log"])
    first: dict[str, str] = {}
    for m in BUG_HEAD.finditer(log):
        first.setdefault("BUG-" + m.group(1), m.group(2).upper())
    sev = {s: 0 for s in d["severity_tokens"]}
    unlab = []
    for bid in sorted(open_ids):
        head = first.get(bid)
        s2 = SEV.search(head) if head is not None else None
        if s2 and s2.group(1) in sev:
            sev[s2.group(1)] += 1
        else:
            unlab.append(bid)  # no heading, or a heading with no severity token: the gap, one bucket
    return sev, unlab


def severity_gap(d: dict, open_ids: set[str]) -> list:
    """Open ids with NO severity token (BUG-757) - the SHRINK-ONLY ceiling's population."""
    return severity_census(d, open_ids)[1]


def _write(path: pathlib.Path, text: str) -> str:
    # D-401/I1: EVERY governed write declares its writer and what it owns. OWNED_ANY is the declared marker
    # for "this writer owns the whole artifact" (the faces are DERIVED in full). D-2982: the guard is imported
    # STATICALLY at the top of this module, so the ownership audit can see it, and there is no unguarded
    # fallback left to bypass it.
    write_document(path, text, writer="scripts/gov_sync.py", owned_keys={OWNED_ANY})
    return "write_guard"


def check(d: dict, x: dict) -> int:
    faults = []
    for face in d["faces"]:
        p = REPO / face["path"]
        text = p.read_text(encoding="utf-8")  # D-2982 (C16): STRICT - a laundered byte would be compared as a face
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
    bad = severity_gap(d, {str(b.get("id")) for b in (x["open_bugs"] or [])})
    ceil = int(d.get("severity_grandfathered", 0))
    if len(bad) > ceil:
        faults.append(f"buglog: {len(bad)} of the register's OPEN ids carry no severity token, over the "
                      f"shrink-only ceiling {ceil} (BUG-757). New: {bad[ceil:][:6]}")
    for f in faults:
        print("  !! " + f)
    if faults:
        print(f"FAIL gov-sync: {len(faults)} join fault(s) - the faces do not equal their re-derivation (D-2981)")
        return EXIT_DRIFT
    print(f"ok gov-sync: {len(d['faces'])} face(s) equal their re-derivation from the registers "
          f"({x['decisions_total']} decisions / {x['bugs_total']} bugs / {x['tasks_total']} open tasks)")
    return EXIT_OK


def _yaml_quote(value: str) -> str:
    """One-line YAML scalar, SINGLE-quoted with inner quotes DOUBLED (the YAML rule).

    BUG-791 (MEASURED 2026-10-14): this splice used to interpolate the rendered value straight into a
    single-quoted scalar, so a title carrying an apostrophe ("the model's served window") CLOSED the scalar
    early and left agent/session_seed.yaml - the BOOT-LOADED face - unparseable, taking four ladder rails with
    it (YAML parse, referenced files, vector dimensions, version stamps). A value that reaches a face is quoted
    BY RULE, never by hope: the rule is YAML's own (double the inner quote), so the file stays in the style the
    faces are written in, and a value that is not one line is REFUSED rather than silently folded.
    """
    if "\n" in value or "\r" in value:
        raise SystemExit("FAIL-CLOSED (gov-sync): a rendered face value must be ONE line (BUG-791)")
    return "'" + value.replace("'", "''") + "'"


def _scalar_round_trips(value: str) -> bool:
    """True when a value can be spliced into a face and READ BACK unchanged (BUG-791).

    The control must REPORT, never crash: a rule that fails by raising a traceback prints no verdict line, so a
    mutation of it cannot be SEEN through the control that names it (D-2676 iv - a crash is not a control).
    """
    try:
        return bool(yaml.safe_load("status: " + _yaml_quote(value))["status"] == value)
    except (yaml.YAMLError, KeyError, TypeError):
        return False


def _field(text: str, dotted: str) -> str | None:
    """Read a scalar from an indented YAML face (session_seed), never a guess: None when absent."""
    key = dotted.split(".")[-1]
    m = re.search(rf"(?m)^[ \t]*{re.escape(key)}:[ \t]*(.+)$", text)
    if not m:
        return None
    # BUG-791 (the reader half): a scalar is read BY THE YAML RULE, never by stripping quotes. With the writer
    # now doubling an inner apostrophe ('the model''s window'), strip() would hand back the ESCAPED text and the
    # face would read STALE forever - a false staleness, which is the worst kind: it is loud and wrong.
    try:
        value = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return None if value is None else str(value)


def apply(d: dict, x: dict) -> int:
    block = render_block(d, x)
    for face in d["faces"]:
        p = REPO / face["path"]
        before = p.read_text(encoding="utf-8")  # D-2982 (C16): STRICT - the pre-image of a governed write
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
                # BUG-791: the value is QUOTED BY RULE (an apostrophe in a title used to close the scalar early).
                text = re.sub(rf"(?m)^([ \t]*){re.escape(key)}:.*$",
                              lambda m: f"{m.group(1)}{key}: {_yaml_quote(str(val))}", text, count=1)
        if text != before and str(face.get("path", "")).endswith((".yaml", ".yml")):
            try:                                    # a writer that cannot read back its own output must not write it
                yaml.safe_load(text)
            except yaml.YAMLError as exc:
                raise SystemExit(f"FAIL-CLOSED: {face['path']} would not parse after this write ({exc}) - "
                                 f"refusing to leave a BOOT-LOADED face unloadable (BUG-791)")
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
         "task_priorities": ["MUST", "SHOULD", "WORTH"], "face_list_limit": 12, "severity_grandfathered": 0,
         "task_states": ["open", "rule", "done", "superseded"], "task_movers": ["owner", "pipeline"],
         "owner_gate_token": "owner", "face_owner_lane_label": "OWNER LANE",
         "face_pipeline_lane_label": "PIPELINE LANE",
         "face_pipeline_lane_note": "what the agent will do next (fixture)",
         "face_list_truncation_note": "the face is a VIEW: {shown} of {total} row(s) (fixture)",
         "decision_in_effect_states": ["active", "ratified"],
         "decision_closed_states": ["resolved", "superseded", "archived", "rejected"],
         "decision_void_states": ["stale", "revoked", "abandoned"]}
    x = {"decisions_total": 7, "states": {"open": 2, "active": 3, "resolved": 2}, "need_action": 2, "stamp": "deadbeefdeadbeef",
         "date": "2026-01-02", "bugs_total": 5, "bugs_open": 3, "bugs_closed": 2, "sev": {"CRITICAL": 1, "HIGH": 1, "MED": 0, "LOW": 0},
         "unlabelled": 1, "open_bugs": [{"id": "BUG-001", "title": "(LOW - OPEN) x"}, {"id": "BUG-003", "title": "(CRITICAL - OPEN) y"}],
         "tasks": [{"id": "T-1", "priority": "MUST", "state": "open", "mover": "pipeline", "title": "t", "evidence": "e"}],
         "rules": [{"id": "R-1", "priority": "MUST", "state": "rule", "mover": "pipeline", "title": "the faces are derived"}],
         "all_tasks": [], "pri": {"MUST": 1, "SHOULD": 0, "WORTH": 0},
         "owner_moved": [{"id": "T-2", "priority": "MUST", "state": "open", "mover": "owner", "title": "sign",
                          "gate": "the owner word", "evidence": "e (2026-01-02)"}],
         "pipeline_moved": [{"id": "T-1", "priority": "MUST", "state": "open", "mover": "pipeline", "title": "t",
                             "evidence": "e (2026-01-02)"}],
         "tasks_total": 2, "version": "v9.9", "open_states": ["open"]}
    ok = 0
    truth = register_truth(d, x)
    assert re.search(r"\b5 bugs \(3 open / 2 closed;", truth), "register_truth must satisfy the faces rail regex"
    ok += 1
    blk = render_block(d, x, decs=[{"id": "D-1", "state": "open", "category": "X", "title": "t"}])
    assert IDX_S in blk and IDX_E in blk and "deadbeefdeadbeef" in blk, "block must carry the census stamp"
    ok += 1
    # D-2987: a DECLARED sign must be RENDERED beside its state, on every surface. The map is injected here
    # (ASCII signs) so the known answer is readable and cannot be satisfied by a hard-coded emoji in the
    # renderer - a literal there would pass only by accident of the real map.
    d2 = {**d, "state_glyphs": {"open": "X", "active": "Y", "resolved": "Z", "superseded": "S",
                                "archived": "A", "rejected": "R", "CRITICAL": "C", "HIGH": "H",
                                "MED": "M", "LOW": "L", "rule": "P", "MUST": "!", "SHOULD": "?",
                                "WORTH": "~", "proposed": "p", "draft": "d", "deferred": "f",
                                "planned": "n", "done": "D"}}
    blk2 = render_block(d2, x, decs=[{"id": "D-1", "state": "open", "category": "X", "title": "t"}])
    assert "X open 2" in blk2 and "Y active 3" in blk2, "a DECLARED sign must render beside its state (D-2987)"
    assert "in effect: Y active 3" in blk2, "every DECLARED bucket must be printed (D-2987/BUG-765)"
    assert "! MUST" in blk2, "the OWNER LANE must carry the tier sign, not a bare word (D-2987)"
    assert "P R-1" in blk2, "a STANDING RULE must carry its never-closes sign (D-2987)"
    ok += 1
    seed2 = render_seed_status(d2, x)
    assert "! T-2" in seed2, "the BOOT face must carry the tier sign on every id it names (D-2987)"
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
    # D-2985: the re-cut has a SCOPE - history is never rewritten, not even by the writer that owns the faces.
    scoped, n3 = _recut_census("live 99 decisions (census stamp 27, 1999-01-01)\n" + HIS +
                               "\nSNAPSHOT: 99 decisions (census stamp 27, 1999-01-01)", truth, d, x)
    bare, n2 = _recut_census("Register truth: 99 decisions · 42 bugs (1 open / 41 closed; y", truth, d, x)
    assert n2 >= 2 and "7 decisions ·" in bare, "the STAMP-LESS restatement must be owned too (the MTR pre-D-2981 shape)"
    ok += 1
    assert _insert_block("## 🔴 MUST — open (x)\nbody\n", "MASTER-TASK-REGISTER.md", blk).count(IDX_S) == 1, "insert anchor"
    ok += 1
    assert _extract_block(face) == blk, "extract must return the block BYTES (the check compares these, not a rewrite)"
    assert _extract_block(face.replace("deadbeefdeadbeef", "0000000000000000")) != blk, "a modified block must compare UNEQUAL"
    ok += 2
    # D-2985: the task register's OWN schema, as NAMED known answers in BOTH directions - a rule whose control
    # has never been seen to fail is not a control (BUG-492), and a mutation must RED the control that NAMES
    # the rule rather than only move a counter (D-2676 iv).
    # BUG-791: a rendered value reaches the boot face through a SINGLE-QUOTED scalar.
    # NOTE: render_seed_status reads x['owner_moved'] - injecting the quirk into the wrong argument is how a
    # control stays green while mutated (the BUG-787 shape), and the mutation gate caught exactly that here.
    quirky = render_seed_status(d2, {**x, "owner_moved": [{"id": "T-1", "priority": "MUST", "state": "open",
                                                           "mover": "owner",
                                                           "title": "the model's served window",
                                                           "gate": "the owner word",
                                                           "evidence": "e (2026-01-02)"}],
                                    "pipeline_moved": []})
    base = {"priority": "MUST", "evidence": "e (2026-01-02)", "gate": "none"}
    one_lane = lambda n: [{"id": "T-%d" % i, "priority": "MUST", "state": "open", "mover": "pipeline",
                           "title": "t", "evidence": "e (2026-01-02)"} for i in range(n)]
    rows = [
        ("no key in this fixture is absent from the live config - a second home for a RENAMED fact would"
         " drift here in silence (a key the fixture LACKS is caught by the renderer call below, which raises)",
         set(d) - set(cfg()) == set()),
        ("a conforming task register makes no fault",
         task_faults([{**base, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t"},
                      {**base, "id": "T-2", "state": "open", "mover": "owner", "title": "sign", "gate": "the owner word"},
                      {**base, "id": "R-1", "state": "rule", "mover": "pipeline", "title": "r"}], d) == []),
        ("a standing RULE registered as an open task must fire",
         any("STANDING RULE" in f for f in task_faults([{**base, "id": "R-1", "state": "open", "mover": "pipeline", "title": "r"}], d))),
        ("an entry that does not say WHO must move it must fire",
         any("WHO must act" in f for f in task_faults([{**base, "id": "T-1", "state": "open", "title": "t"}], d))),
        ("mover: owner with gate 'none' must fire",
         any("mover: owner but gate is 'none'" in f for f in task_faults([{**base, "id": "T-1", "state": "open", "mover": "owner", "title": "t"}], d))),
        ("a pipeline-moved task whose gate names the owner must fire",
         any("the two fields disagree" in f for f in task_faults([{**base, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t", "gate": "the owner word"}], d))),
        ("a title that restates a measured count must fire",
         any("ONE home" in f for f in task_faults([{**base, "id": "T-1", "state": "open", "mover": "pipeline", "title": "108 of 185 open bugs"}], d))),
        ("an evidence line carrying a count with no date must fire",
         any("MOMENT OF MINT" in f for f in task_faults([{**base, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t", "evidence": "185 open"}], d))),
        ("the derived block LEADS with the OWNER LANE (before the pipeline lane)",
         render_block(d, x, decs=[]).index("OWNER LANE") < render_block(d, x, decs=[]).index("PIPELINE LANE")),
        ("a lane longer than face_list_limit MUST name the rows it did not print (BUG-842/T-142)",
         "12 of 20" in render_block(d, {**x, "pipeline_moved": one_lane(20)}, decs=[])
         and "20" in render_block(d, {**x, "pipeline_moved": one_lane(20)}, decs=[])),
        ("a lane that FITS carries NO truncation note",
         "row(s) shown" not in render_block(d, {**x, "pipeline_moved": one_lane(3)}, decs=[])),
        ("the pipeline lane declares the ORDER the renderer sorts by, not a strategic order it cannot support",
         d["face_pipeline_lane_note"] in render_block(d, x, decs=[])
         and "strategic" not in render_block(d, x, decs=[]).lower()),
        ("a rendered value with an apostrophe is quoted so the BOOT face stays parseable (BUG-791)",
         _scalar_round_trips(quirky)),
        ("a standing RULE is NOT counted as open work", "standing rule(s) never close" in register_truth(d, x)),
        ("the census re-cut owns the LIVE region and leaves the history region BYTE-IDENTICAL",
         n3 >= 1 and "7 decisions (census stamp deadbeefdeadbeef, 2026-01-02)" in scoped
         and "SNAPSHOT: 99 decisions (census stamp 27, 1999-01-01)" in scoped),
    ]
    for name, okk in rows:
        print(("  ok  " if okk else "  !!  ") + name)
    ok += len(rows)
    failed = [name for name, okk in rows if not okk]
    if failed:
        print("FAIL gov-sync --selftest: " + str(len(failed)) + " known answer(s) did not fire")
        return EXIT_DRIFT
    print(f"ok gov-sync --selftest: {ok} known answers (a stale block is DETECTED, not trusted)")
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
