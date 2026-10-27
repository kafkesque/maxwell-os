#!/usr/bin/env python3
"""resolve_route.py — THE ROUTE GRAPH: which capability owns this work, and is the graph well-formed? (D-3024/T-156)

WHY (the class, not the instance). MEASURED 2026-10-15 (see `--census`): of 537 python files, 32 are named by no
justfile recipe, no config file and no governance document; of 131 pipeline modules 6 declare a check verb and of
404 scripts 67 do. "Who runs what" lived in prose and in a justfile, so a task could not be RESOLVED to the
capability that owns it and a capability whose entrypoint or check does not exist could not be REFUSED. This
script is the ONE deterministic reader of config/capability_registry.yaml (the declared graph, C12).

WHAT IT SETTLES, without judgement:
  * every declared capability has a KIND from the declared vocabulary, an ENTRYPOINT and a CHECK that RESOLVE
    (a file path that EXISTS, or `just <recipe>` that the ladder file still declares), a RECEIPT that names a home
    that exists (a path, or `<file>#<key>` followed into the declaration that owns that fact), a COST TIER from the
    vocabulary config/delegation_economy.yaml owns, and OWNED paths that exist;
  * every operator LANE names a recipe the ladder still carries, a command that recipe still carries, and a command
    that is in NO governed ladder recipe (if it were, its guard class would belong in config/rail_registry.yaml);
  * every OPEN item (task or bug) either ROUTES to a declared capability by the artifacts it names, or carries a
    DECLARED reason — a mover with no declared disposition is a fault, and an item listed as unrouted that is no
    longer open is a STALE declaration;
  * the routing DEBT is a SHRINK-ONLY ceiling (the D-3023 shape): inherited debt cannot grow unnoticed, and a
    shrink is reported as good news;
  * the CEILING ITSELF is anchored (BUG-1097): the declared number must be the number the recorded history ENDS
    at, every row must chain onto the one before it, a row that RAISES a ceiling must cite a decision id that
    EXISTS in config/decisions.yaml, and `routing_debt.measured` must be a date no later than the last act. Until
    this existed the rail compared in ONE direction only (`debt > ceiling`), so the ceiling could be edited
    upward in silence - and `measured` was read by NO code at all, which made it a declaration with no consumer
    (D-3034). MEASURED 2026-10-28 before the guard: `unrouted_open_bugs: 172 -> 173` by a bare edit, rail rc 0;
  * the report is BYTE-STABLE: it is rendered twice and the two digests must agree.
It does NOT decide policy, and it never assigns: an LLM may write a PROPOSAL into temp/ and `--propose` validates
it against this same schema while writing nothing (D-2898/D-2941).

THE ONE WRITE, and it is the one act D-2644 permits: `--rebaseline --set <tasks|bugs>=<n> [--because D-xxxx]`
re-records a ceiling, APPENDS the row that explains the move, and re-dates `measured`. A LOWERING needs no
citation (D-2644: a ceiling may only be lowered, because a shrink is not a decision); a RAISE is a DECISION and
is refused without `--because` naming an id that exists in config/decisions.yaml. `--check` never writes.

Exit: 0 ok | 1 fault(s) | 2 the registry itself is unreadable/incomplete (fail closed, C16).
--selftest: known-answer controls over SYNTHETIC graphs (no model, no live write, BUG-492).
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import json
import pathlib
import re
import shlex
import sys
from typing import Callable

import yaml
from lib import artifact_encoding  # noqa: E402
from lib import handoff, write_guard, yaml_guard  # noqa: E402

RAIL_REL = "scripts/resolve_route.py"
REPO = pathlib.Path(__file__).resolve().parents[1]
CFG = REPO / "config/capability_registry.yaml"
RAIL = REPO / "config/rail_registry.yaml"
ECON = REPO / "config/delegation_economy.yaml"
DECL = REPO / "config/declaration_consumers.yaml"
FLAGS = REPO / "config/flag_consumer_registry.yaml"
TASKS = REPO / "config/task_register.yaml"
BUGS = REPO / "governance/bug_status.json"
TEMP = REPO / "temp"

REQUIRED_KEYS = ("schema_version", "authority", "kinds", "capabilities", "dispositions", "reasons", "routing_debt")
CAP_FIELDS = ("id", "kind", "entrypoint", "check", "receipt", "cost_tier", "owns")
LANE_FIELDS = ("recipe", "cmd", "produces", "why")
PRODUCES = ("reading", "receipt", "state")
# ARTIFACT is IMPORTED, not restated (D-3212 / D-2642): the census (scripts/bug_status.py) must publish exactly
# the tokens this rail recognises, so the pattern has ONE home - scripts/lib/artifact_tokens.py.
from lib.artifact_tokens import ARTIFACT  # noqa: E402  (after the path constants, matching this file's idiom)
JUST = re.compile(r"\bjust\s+([A-Za-z0-9][A-Za-z0-9_-]*)")   # a recipe name may carry _ and - (justfile)
TIER = re.compile(r"\bT[0-2]\b")
RECIPE = re.compile(r"^([A-Za-z0-9_-]+)(?:\s+[^:\n]+)?:\s*(?:#.*)?$")
PATHISH = re.compile(r"^[\w.-]+(?:/[\w .&()-]+)+$")
DEBT_CLASSES = ("tasks", "bugs")            # the ceiling key is `unrouted_open_<cls>`; the item class is singular
HISTORY_KEY = "ceiling_changed"             # append-only: the anchor the declared number must END at (BUG-1097)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _iso(value: object) -> "str | None":
    """The DATE a declaration names, or None - reading both shapes YAML can give for one fact.

    MEASURED while landing BUG-1097: `measured: '2026-10-28'` arrives as a str, but the identical unquoted
    `measured: 2026-10-28` arrives as a datetime.date. A guard that only accepts the quoted form would refuse a
    perfectly valid registry and would be WRONG in the dangerous direction (it would train the owner to distrust a
    true fault). One reader for "what date does this name", and it accepts both spellings of the same declaration.
    """
    if isinstance(value, str):
        return value.strip() if ISO_DATE.match(value.strip()) else None
    if isinstance(value, datetime.date):          # datetime.datetime subclasses date; strftime normalises both
        return value.strftime("%Y-%m-%d")
    return None


def _executable(rel: str) -> bool:
    """Is this repo-relative file executable? The real bit, read from the real path (BUG-842/T-146)."""
    try:
        return bool((REPO / rel).stat().st_mode & 0o111)
    except OSError:
        return False


def _bare_form_faults(where: str, cmd: str, w: "World") -> list:
    """A command written as a BARE script path must be runnable BY TYPING IT (BUG-842/T-146).

    MEASURED 2026-10-16: the owner ran 'pipeline/hf_fetch_model.py' and got "permission denied". The file
    carries a shebang, which PROMISES it can be run directly, and this repo has 562 tracked .py files that
    make that promise and cannot keep it - so the promise was a matter of habit in both directions. The
    declared rule is the FORM, and it is the form every capability in config/capability_registry.yaml already
    uses: 'python3 <path>' requires the file to EXIST, while a bare '<path> <args>' requires the executable
    bit, because that is how that command is read and run. Enforcing the form is what makes either spelling
    honest instead of tribal.
    """
    tokens = str(cmd).split()
    if not tokens:
        return []
    first = tokens[0]
    if not PATHISH.match(first) or "/" not in first or w.executable(first):
        return []
    return [f"{where}: it is written as a BARE path {first!r} and is run by typing it, but the file is not "
            f"executable - either declare the interpreter form 'python3 {first}' (the form every capability "
            f"in this registry uses, so a mode-by-accident cannot break a declared route) or make the file "
            f"executable (BUG-842/T-146)"]

#: where the ITEM text lives. A task's evidence is part of its claim (T-156's own source list is evidence), and a
#: bug carries only a title, which is why a bug routes rarely and by design (see #dispositions).
TASK_TEXT_FIELDS = ("source", "gate", "evidence", "title", "why", "blocked_by")


def recipe_bodies(text: str) -> dict[str, str]:
    """The ladder's recipes -> their bodies, so a `just <recipe>` route can be RESOLVED and a lane's command
    FOUND. Read from the ladder's own bytes: a route is verified against the file the operator would run."""
    out: dict[str, str] = {}
    name: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = RECIPE.match(line)
        if m and not line.startswith((" ", "\t")):
            if name is not None:
                out[name] = "\n".join(buf)
            name, buf = m.group(1), []
            continue
        if name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf)
    return out


def read_pointer(ref: str, exists: Callable[[str], bool]) -> list[str]:
    """A RECEIPT may be a path or `<file>#<key>`: a pointer is FOLLOWED into the declaration that owns the fact
    (a composed receipt is verified, never asserted, D-3024/C12)."""
    if "#" not in ref:
        parent = str(pathlib.PurePosixPath(ref).parent)
        if exists(ref.rstrip("/")):
            return []
        if parent in ("", ".") or exists(parent):
            return []
        return [f"its receipt home {parent!r} does not exist"]
    path, _, key = ref.partition("#")
    if not exists(path):
        return [f"its receipt points at {path!r}, which does not exist"]
    try:
        text = artifact_encoding.open_artifact(REPO / path, REPO).read()
    except OSError as exc:                                        # pragma: no cover - a readable path was just checked
        return [f"its receipt {ref!r} could not be read: {exc}"]
    if not re.search(rf"^{re.escape(key)}\s*:", text, re.M):
        return [f"its receipt {ref!r} points at key {key!r}, which {path} does not declare"]
    return []


@dataclasses.dataclass(frozen=True)
class Item:
    """One OPEN item of work: a task (it has a mover) or a bug (it does not)."""
    id: str
    cls: str
    mover: str
    text: str


@dataclasses.dataclass(frozen=True)
class World:
    """Every fact the judgement needs, injected - so the controls are over SYNTHETIC graphs, not the live tree."""
    cfg: dict
    recipes: dict[str, str]
    governed: tuple[str, ...]                                # the recipes the RAIL REGISTRY governs
    exists: Callable[[str], bool]
    executable: Callable[[str], bool]                        # is this repo-relative file runnable by path
    tiers: set[str]
    items: list[Item]
    edges: tuple[int, int]                                   # (declaration edges, flag edges)
    #: The ids config/decisions.yaml declares, INJECTED as a zero-argument callable (BUG-1097): a raise of a
    #: ceiling must cite one that EXISTS, and the registry costs ~1.7 s to parse - so it is read ONLY on the path
    #: that needs it (a raised ceiling exists) and never on the ordinary green run. A callable keeps `check()`
    #: pure in the same way `exists`/`executable`/`tiers` already do.
    decisions: "Callable[[], set[str]] | None" = None


def load_cfg() -> dict:
    """Fail closed: an unreadable or incomplete registry is never a silent empty graph (C16)."""
    if not CFG.is_file():
        raise SystemExit("FAIL-CLOSED: config/capability_registry.yaml is absent - a route graph that declares "
                         "nothing cannot refuse anything")
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    for key in REQUIRED_KEYS:
        if key not in cfg:
            raise SystemExit(f"FAIL-CLOSED: config/capability_registry.yaml must declare '{key}'")
    if not cfg.get("capabilities"):
        raise SystemExit("FAIL-CLOSED: the registry declares NO capability - an empty graph is not a graph")
    return cfg


def load_items() -> list[Item]:
    """The open population, from the registers that own it: tasks by `state: open`, bugs from the bug CENSUS
    (governance/bug_status.json, whose parser is declared there - parsing the buglog here would be a second
    parser for one fact, C12)."""
    items: list[Item] = []
    tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8")) or {}
    for t in tasks.get("tasks") or []:
        if str(t.get("state")) != "open":
            continue
        text = " ".join(str(t.get(f) or "") for f in TASK_TEXT_FIELDS)
        items.append(Item(id=str(t["id"]), cls="task", mover=str(t.get("mover") or ""), text=text))
    bugs = json.loads(BUGS.read_text(encoding="utf-8"))
    for b in bugs.get("open") or []:
        # D-3212 (2026-10-28): A TASK IS READ FROM SIX EVIDENCE FIELDS AND A BUG WAS READ FROM TWO OF ITS OWN
        # (id + title), because the census — the ONE parser of the buglog (C12) — published no evidence. So a bug
        # whose TITLE names no artifact read as `no_artifact_named` even when its EVIDENCE named the very file an
        # owning capability holds: 231 open bugs against a declared ceiling of 221, and 63 of them were that
        # artefact. The remedy is NOT to parse the buglog here (a second parser for one fact) - it is for the
        # census to publish the artifacts its own evidence names, which is what `artifacts` now carries.
        # LOUD, never `.get(...)`: an index written by an older census cannot answer this question at all, and a
        # silent empty list would read as REAL debt (the BUG-1083 shape: a rail failing in the direction that
        # inflates a number nobody can then tell from work).
        if "artifacts" not in b:
            raise SystemExit(
                "FAIL-CLOSED (C16/D-3212): governance/bug_status.json carries an open bug with no `artifacts` "
                f"field ({b.get('id')!r}) - the index predates the reader that asks this question.\n"
                "  fix it with: python3 scripts/bug_status.py   (the census is the one parser of the buglog, C12)")
        text = " ".join([str(b.get("id") or ""), str(b.get("title") or "")]
                        + [str(a) for a in (b.get("artifacts") or [])])
        items.append(Item(id=str(b["id"]), cls="bug", mover="", text=text))
    return sorted(items, key=lambda i: (i.cls, i.id))


def world() -> World:
    """The LIVE world: the registry, the ladder's own bytes, the two composed joins and the open population."""
    rail = yaml.safe_load(RAIL.read_text(encoding="utf-8")) or {}
    ladder = REPO / str(rail.get("ladder") or "justfile")
    decl = yaml.safe_load(DECL.read_text(encoding="utf-8")) or {}
    flags = yaml.safe_load(FLAGS.read_text(encoding="utf-8")) or {}
    edges = (sum(len(d.get("consumers") or []) for d in decl.get("declarations") or []),
             sum(len(f.get("consumers") or []) for f in flags.get("flags") or []))
    return World(cfg=load_cfg(), recipes=recipe_bodies(ladder.read_text(encoding="utf-8")),
                 governed=tuple(str(r) for r in (rail.get("recipes") or [])),
                 exists=lambda p: (REPO / p).exists(), executable=_executable,
                 tiers=set(TIER.findall(ECON.read_text(encoding="utf-8"))),
                 items=load_items(), edges=edges, decisions=handoff.decision_ids)


# ------------------------------------------------------------------ the judgements (PURE, one reader each)
def capability_faults(cap: dict, w: World) -> list[str]:
    """ONE capability -> the reasons it cannot be called or cannot be believed (T-156's fail-closed clause)."""
    cid = str(cap.get("id") or "<no id>")
    faults: list[str] = []
    for field in CAP_FIELDS:
        value = cap.get(field)
        if value in (None, "", [], {}):
            faults.append(f"capability {cid}: no {field} - a route with no {field} cannot be called, checked, "
                          f"believed or costed")
    kind = str(cap.get("kind") or "")
    kinds = [str(k) for k in (w.cfg.get("kinds") or {})]
    if kind and kind not in kinds:
        faults.append(f"capability {cid}: kind {kind!r} is not one of the declared kinds {kinds}")
    tier = str(cap.get("cost_tier") or "")
    if tier and tier not in w.tiers:
        faults.append(f"capability {cid}: cost_tier {tier!r} is not in the vocabulary config/"
                      f"delegation_economy.yaml owns (it declares {sorted(w.tiers)}) - a re-badged economy is a "
                      f"fault, not a relabelling")
    for field in ("entrypoint", "check"):
        cmd = str(cap.get(field) or "")
        if not cmd:
            continue
        just = JUST.search(cmd)
        if just:
            if just.group(1) not in w.recipes:
                faults.append(f"capability {cid}: its {field} `just {just.group(1)}` is not a recipe the ladder "
                              f"file declares - a declared route whose entrypoint is ABSENT")
        else:
            #: The MODULE the interpreter is handed is the ROUTE; the tokens after it name inputs and outputs, and
            #: an output that does not exist yet is not a defect (a false fault here would teach the next session to
            #: distrust the rail). So the first path-shaped token is the one that must EXIST.
            module = next((t for t in cmd.split() if PATHISH.match(t) and "/" in t), "")
            if module and not w.exists(module):
                faults.append(f"capability {cid}: its {field} names {module!r}, which DOES NOT EXIST - a declared "
                              f"route whose entrypoint is absent is the one thing this registry exists to refuse "
                              f"(T-156)")
            faults.extend(_bare_form_faults(f"capability {cid}: its {field}", cmd, w))
    if cap.get("owns") and not isinstance(cap["owns"], list):
        faults.append(f"capability {cid}: owns is {type(cap['owns']).__name__}, not a LIST - a bare string would be "
                      f"iterated character by character and report a fault per letter, which reads as a cascade rather "
                      f"than as the one-line schema mistake it is")
    for owned in (cap.get("owns") if isinstance(cap.get("owns"), list) else []):
        token = str(owned).rstrip("/")
        if not w.exists(token):
            faults.append(f"capability {cid}: it claims to OWN {owned!r}, which does not exist - ownership of an "
                          f"absent path is an assertion (D-405/BUG-488)")
    if str(cap.get("receipt") or ""):
        faults.extend([f"capability {cid}: {x}" for x in read_pointer(str(cap["receipt"]), w.exists)])
    return faults


def _without_comments(body: list[str] | str) -> str:
    """The recipe body with its `#` COMMENTS removed, so a MENTION can never be read as a RUN.

    MEASURED 2026-10-25 (BUG-1014): a justfile comment that merely NAMED `pipeline/model_loadability_probe.py` made
    lane_faults report that the lane's command "is ALSO run by the governed ladder recipe 'health'". The comment was
    an explanation of WHY the rail was cheaper than a recollection, and it became a declaration that the lane was a
    ladder rail — the BUG-838 limb-3 shape one register over ("the reader's own vocabulary may not declare a byte").
    A FALSE RED is worse than an UNKNOWN (D-3150), and nothing may go quiet about a real overlap either, so a line
    that cannot be tokenised is kept VERBATIM: the conservative direction for a rail is to still see it.
    """
    kept: list[str] = []
    for line in (body if isinstance(body, list) else str(body).splitlines()):
        try:
            kept.append(" ".join(shlex.split(str(line), comments=True)))
        except ValueError:
            kept.append(str(line))
    return "\n".join(kept)


def lane_faults(lane: dict, w: World) -> list[str]:
    """ONE operator lane -> its two-sided claim: the command is STILL THERE, and it is NOT a ladder rail."""
    rid = str(lane.get("recipe") or "<no recipe>")
    faults: list[str] = []
    for field in LANE_FIELDS:
        if lane.get(field) in (None, "", [], {}):
            faults.append(f"lane {rid}: no {field}")
    if lane.get("produces") and str(lane["produces"]) not in PRODUCES:
        faults.append(f"lane {rid}: produces {lane['produces']!r} is not one of {list(PRODUCES)}")
    body = w.recipes.get(rid)
    if body is None and lane.get("recipe"):
        faults.append(f"lane {rid}: the ladder file declares no such recipe - a lane the operator is told to run "
                      f"and cannot (BUG-482, the caller class)")
    cmd = str(lane.get("cmd") or "")
    if body is not None and cmd and cmd not in body:
        faults.append(f"lane {rid}: the recipe no longer carries {cmd!r} - the declaration outlived its subject")
    if cmd:
        for name in w.governed:
            if name in w.recipes and cmd in _without_comments(w.recipes[name]):
                faults.append(f"lane {rid}: {cmd!r} is ALSO run by the governed ladder recipe {name!r} - its guard "
                              f"class belongs in config/rail_registry.yaml#guards, not in a lane (T-164)")
    faults.extend(_bare_form_faults(f"lane {rid}", cmd, w))
    cap = lane.get("capability")
    if cap and str(cap) not in [str(c.get("id")) for c in w.cfg.get("capabilities") or []]:
        faults.append(f"lane {rid}: it names capability {cap!r}, which the registry does not declare")
    return faults


def owning(caps: list[dict], token: str) -> list[str]:
    """The capabilities that own one artifact token - exact match, or a declared `dir/` prefix."""
    hits = {str(c["id"]) for c in caps for o in (c.get("owns") or [])
            if token == str(o) or (str(o).endswith("/") and token.startswith(str(o)))}
    return sorted(hits)


def outcome(item: Item, caps: list[dict], w: World) -> tuple[str, list[str], dict]:
    """ONE open item -> (category, capabilities, FACTS). The categories are MEASURED, never guessed:
    routed | unowned_artifact | absent_path | no_artifact_named.

    The two FACTS are returned ALONGSIDE the category, not instead of it (R5 review, run t156r5b): an item that
    names BOTH an existing artifact nobody owns and an ABSENT path is categorized by the more actionable fact, and
    reporting only the category would hide the other one.

    THE ABSENT FACT IS NAMED FOR WHAT IT IS, NOT FOR THE WORST THING IT COULD BE. An item may name a path that does
    not exist because it is a stale citation (BUG-488), because it is a PROPOSAL to create that artifact (T-128
    declares config/row_lifecycle.yaml in its own gate), or because the home is OUTSIDE the repo (T-157 cites the
    session's ~/.config/goose/config.yaml). The reader cannot tell which and does not claim to: it reports the fact
    and leaves the judgement, which is why the category is 'absent_path' and not 'stale_citation'.
    """
    tokens = sorted(set(ARTIFACT.findall(item.text)))
    hits = sorted({cid for tok in tokens for cid in owning(caps, tok)})
    paths = [t for t in tokens if "/" in t]
    facts = {"exists_unowned": sorted(t for t in paths if w.exists(t) and not owning(caps, t)),
             "absent": sorted(t for t in paths if not w.exists(t))}
    if hits:
        return "routed", hits, facts
    if facts["exists_unowned"]:
        return "unowned_artifact", [], facts
    if facts["absent"]:
        return "absent_path", [], facts
    return "no_artifact_named", [], facts


def item_faults(w: World) -> tuple[list[str], list[tuple[Item, str, list[str]]], dict]:
    """Every open item is ROUTED or it carries a DECLARED reason. A mover nobody dispositioned is a fault; an
    item declared unrouted that is no longer open is a STALE declaration; a reason nobody declared is a fault."""
    faults: list[str] = []
    caps = list(w.cfg.get("capabilities") or [])
    disp = w.cfg.get("dispositions") or {}
    reasons = [str(k) for k in (w.cfg.get("reasons") or {})]
    rows = [(i, cat, hits) for i, cat, hits, _facts in ((i, *outcome(i, caps, w)) for i in w.items)]
    for i, category, hits in rows:
        over = (w.cfg.get("unrouted") or {}).get(i.id)
        if category == "routed":
            # D-3212 (2026-10-28): an escape declared for an item the graph DOES route is a declaration with no
            # referent (D-3034) - it excuses nothing, and worse, it HIDES the fact that the cure already arrived.
            # MEASURED the day the bug reader stopped seeing only id + title: 10 of 15 per-item declarations went
            # inert in one change and NOTHING said so - the fault at (v) only asks whether the item is still OPEN,
            # never whether it is still UNROUTED. This is the invariant behind BUG-1091/1092/1093 (retired by hand
            # on 2026-10-27) and behind these ten: an instance-paying fix would have to be repeated every time an
            # ownership declaration lands. It is paid once, here, as a refusal.
            if over is not None:
                faults.append(f"(vii) INERT unrouted declaration: {i.id} is ROUTED to {', '.join(hits)} and is "
                              f"also declared unrouted with reason {over!r} - the reason outlived the defect it "
                              f"excused (D-3034). Retire the declaration, or the route - but not both.")
            continue
        table = (disp.get("tasks") if i.cls == "task" else disp.get("bugs")) or {}
        reason = table.get(i.mover) if i.cls == "task" else table.get("default")
        if over is not None:
            if str(over) not in reasons:
                faults.append(f"(v) item {i.id} is declared unrouted with reason {over!r}, which is not declared "
                              f"in this registry's reason vocabulary")
        elif reason is None:
            faults.append(f"(v) item {i.id} ({i.cls}, mover {i.mover!r}) RESOLVES TO NO CAPABILITY and no "
                          f"disposition covers its mover: a mover the register carries and the graph does not "
                          f"disposition is a mover nobody said how to route")
    open_ids = {i.id for i in w.items}
    for stale in sorted(w.cfg.get("unrouted") or {}):
        if stale not in open_ids:
            faults.append(f"(v) STALE unrouted declaration: {stale} is not an open item - the reason outlived the "
                          f"item it explained")
    for mover, reason in sorted((disp.get("tasks") or {}).items()):
        if str(reason) not in reasons:
            faults.append(f"(v) dispositions.tasks[{mover}] names reason {reason!r}, which is not declared")
    for reason in sorted((disp.get("bugs") or {}).values()):
        if str(reason) not in reasons:
            faults.append(f"(v) dispositions.bugs names reason {reason!r}, which is not declared")
    # BUG-913 (2026-10-17): the DEBT must count what the rail's own escape does NOT cover. `unrouted:` declares
    # an item a FINDING rather than a missing route (reason `bug_is_a_finding`), and a declaration that lowers no
    # measurement is a declaration with no referent (D-3034) - the first version of this block honoured the fault
    # at (v) and then counted the item anyway at (vi), so the ONE escape the message offers ("declare the route, or
    # disposition the item") could not move the number it was telling the reader to move. Only the PER-ITEM
    # override is subtracted: subtracting `dispositions.bugs.default` (which covers every bug) would zero the debt
    # and make it meaningless.
    overridden = {str(k) for k in (w.cfg.get("unrouted") or {})}
    debt = {"tasks": sum(1 for i, c, _ in rows if i.cls == "task" and c != "routed" and str(i.id) not in overridden),
            "bugs": sum(1 for i, c, _ in rows if i.cls == "bug" and c != "routed" and str(i.id) not in overridden)}
    return faults, rows, debt


def facts_census(w: World, caps: list[dict]) -> dict:
    """The FACTS behind every unrouted item, summed: an existing artifact NO capability owns is a missing ROUTE; a
    named path that does not exist is a STALE CITATION (BUG-488). Kept SEPARATE from the category counts on
    purpose: a category picks the more actionable fact, and a report that silently dropped the other one would be
    the very defect this registry exists to refuse (R5 review, run t156r5b)."""
    out = {"exists_unowned": [], "absent": []}
    for item in w.items:
        _, hits, facts = outcome(item, caps, w)
        if hits:
            continue
        for key in out:
            if facts[key]:
                out[key].append(item.id)
    return {k: sorted(v) for k, v in out.items()}


def ceiling_faults(ceilings: dict, known: "Callable[[], set[str]] | None") -> list[str]:
    """Does the DECLARED ceiling match the history that explains it? PURE: every fact arrives injected.

    BUG-1097 (MEASURED 2026-10-28). `check()` compared in ONE direction - `debt > ceiling` - so it could see debt
    GROW but never see the CEILING MOVE, and `routing_debt.measured` was read by NO code at all (D-3034: a
    declaration with no consumer). The register even held the receipt of the last raise, in prose:
    "RE-MEASURED 222 -> 225 on 2026-10-17 by D-3080" - a value merely MENTIONED in a comment declares no bytes,
    so that raise left the ceiling 49 items above its own reading and nothing said a word. This reads the same
    fact in the OTHER direction, and it is why the ceiling is now a number with a history instead of a number.

    Three named faults, each one thing a reader can be wrong about:
      (viii) UNANCHORED - the declared number is not the number the record ENDS at: the ceiling moved without a
             recorded act. This is the limb that fires on a bare edit (the red loop's limb i).
      (ix)   UNSIGNED RAISE - a row that raises a ceiling cites no decision, or one that does not EXIST in
             config/decisions.yaml; or a row whose `frm` does not chain onto the row before it, because a gap is a
             move nobody recorded (D-2644: a raise is a DECISION, not an edit).
      (x)    STALE MEASUREMENT - `measured` is not an ISO date, or it predates the last recorded act: a ceiling
             priced on an older reading is a belief wearing a receipt's clothes (D-3109/D-3036).
    """
    faults: list[str] = []
    measured = _iso(ceilings.get("measured"))
    if measured is None:
        faults.append(f"(x) STALE MEASUREMENT: routing_debt.measured is {ceilings.get('measured')!r}, not a date "
                      f"- a ceiling is priced on a READING, and a reading nobody can date cannot be re-taken "
                      f"(D-3109)")
    rows = ceilings.get(HISTORY_KEY)
    if not isinstance(rows, list) or not rows:
        faults.append(f"(viii) CEILING UNANCHORED: routing_debt.{HISTORY_KEY} records no act, so the declared "
                      f"ceilings can be edited in either direction in silence - which is the defect BUG-1097 "
                      f"names. Seed one row per class at the declared reading; move it only through --rebaseline")
        return faults
    valid = {f"unrouted_open_{c}" for c in DEBT_CLASSES}
    for row in rows:
        # The rows are NAMED here when they cannot be read (one fault per defect, and a defect a reader can act
        # on); the per-class arithmetic below reads only rows that resolve (ceiling_record, one home).
        if not isinstance(row, dict):
            faults.append(f"(ix) UNSIGNED RAISE: a routing_debt.{HISTORY_KEY} row is not a mapping ({row!r}) - a "
                          f"record that cannot be read cannot justify a number")
            continue
        target = str(row.get("target") or "")
        if target not in valid:
            faults.append(f"(ix) UNSIGNED RAISE: a routing_debt.{HISTORY_KEY} row moves {target!r}, which is not a "
                          f"declared ceiling (expected one of {', '.join(sorted(valid))})")
            continue
        try:
            int(row["frm"]), int(row["to"])
        except (KeyError, TypeError, ValueError):
            faults.append(f"(ix) UNSIGNED RAISE: the {target} row {row!r} carries no readable frm/to - a move "
                          f"whose direction cannot be read cannot be judged a raise or a shrink")
    for cls in DEBT_CLASSES:
        key = f"unrouted_open_{cls}"
        declared, recorded, chain = ceiling_record(ceilings, cls)
        if not chain:
            faults.append(f"(viii) CEILING UNANCHORED: {key} has NO recorded act in routing_debt.{HISTORY_KEY} - "
                          f"the number below it is an assertion with no origin story (D-3034)")
            continue
        if declared is None:
            faults.append(f"(viii) CEILING UNANCHORED: {key} declares no integer ceiling - a ceiling with no "
                          f"number is a comment, and a comment cannot fail")
            continue
        prev: "int | None" = None
        for row in chain:
            if prev is not None and row["frm"] != prev:
                faults.append(f"(ix) UNSIGNED RAISE: the {key} history does not chain - a row starts at "
                              f"{row['frm']} while the record had ended at {prev}. A gap is a move nobody "
                              f"recorded, and a record with holes justifies nothing (D-2644)")
            prev = row["to"]
        if recorded is not None and declared != recorded:
            direction = "RAISED" if declared > recorded else "LOWERED"
            faults.append(f"(viii) CEILING UNANCHORED: {key} is declared {declared} but the record ends at "
                          f"{recorded} - the ceiling was {direction} WITHOUT a recorded act. A ceiling "
                          f"moves through `--rebaseline --set {cls}=<n>`, never by an edit: a raise is a DECISION "
                          f"that cites an existing id (D-2644/D-3023), and an edit nobody signed is the hole "
                          f"BUG-1097 names")
        raises = [r for r in chain if r["to"] > r["frm"]]
        if raises and known is None:
            faults.append(f"(ix) UNSIGNED RAISE: {key} holds {len(raises)} raise(s) and the decision registry was "
                          f"not injected, so their citations cannot be verified - fail closed (C16)")
        elif raises:
            ids = known()
            for row in raises:
                decision = str(row.get("decision") or "").strip()
                if not decision:
                    faults.append(f"(ix) UNSIGNED RAISE: {key} {row['frm']} -> {row['to']} cites NO decision - a "
                                  f"raise is a DECISION and must name the record that justifies it (D-2644)")
                elif decision not in ids:
                    faults.append(f"(ix) UNSIGNED RAISE: {key} {row['frm']} -> {row['to']} cites {decision}, which "
                                  f"is not an id in config/decisions.yaml ({len(ids)} known) - mint the decision "
                                  f"FIRST, then raise the ceiling (D-2660/D-2982)")
        last = _iso(chain[-1].get("date"))
        if measured is not None and last is not None and measured < last:
            faults.append(f"(x) STALE MEASUREMENT: routing_debt.measured is {measured} but the last "
                          f"recorded act is dated {last} - a ceiling priced on an older reading is a belief, and "
                          f"--rebaseline re-dates it as part of the act (D-3109)")
    return faults


def ceiling_record(ceilings: dict, cls: str) -> tuple["int | None", "int | None", list[dict]]:
    """(declared, recorded, rows) for ONE debt class. The RECORD is the ledger; the number is a cache of it.

    One home for "what does this ceiling's history END at", because three readers need that same fact: the fault
    reader (BUG-1097 limb viii), the transform that moves a ceiling, and the act that decides whether a move is a
    RAISE (needs a decision) or a LOWERING (does not, D-2644). If they each derived it, one of them would
    eventually derive it differently - the two-homes defect (D-2642).

    `recorded` is None when the class has no row at all: an unanchored ceiling is not zero, it is unknown, and the
    caller must fail closed on it rather than treat unknown as a number.
    """
    key = f"unrouted_open_{cls}"
    declared = ceilings.get(key)
    rows: list[dict] = []
    for row in ceilings.get(HISTORY_KEY) or []:
        if not isinstance(row, dict) or str(row.get("target") or "") != key:
            continue
        try:
            rows.append({**row, "frm": int(row["frm"]), "to": int(row["to"])})
        except (KeyError, TypeError, ValueError):
            continue                      # UNREADABLE rows are NAMED by the fault reader, not silently dropped here
    recorded = rows[-1]["to"] if rows else None
    return (declared if isinstance(declared, int) else None), recorded, rows


def apply_ceiling(text: str, cls: str, to: int, *, decision: str, why: str, date: str) -> str:
    """The ONE act that MOVES a routing-debt ceiling (BUG-1097): re-record the number, APPEND the row, re-date.

    PURE text->text on purpose. A write act that can only be exercised on the live registry cannot be proven, so
    the transform is a function a known-answer control drives on a fixture, and `rebaseline` verifies the parsed
    result BEFORE the bytes are committed (C6/D-401: the bytes on disk must be the bytes intended).

    A LOWERING is the permitted direction (D-2644: a shrink is not a decision) and records `decision: null`; a RAISE
    carries the decision id its caller proved EXISTS. The row is YAML flow style so the register stays one line
    per act - a history a reader can diff, oldest first.
    """
    key = f"unrouted_open_{cls}"
    value_re = re.compile(rf"(?m)^(?P<pad>[ \t]*{re.escape(key)}: )(?P<num>-?\d+)[ \t]*$")
    found = value_re.search(text)
    if found is None:
        raise SystemExit(f"FAIL-CLOSED: config/capability_registry.yaml declares no `{key}: <int>` line - the act "
                         f"may only re-record a ceiling that EXISTS (C16) and never invent one")
    declared, recorded, _rows = ceiling_record((yaml.safe_load(text) or {}).get("routing_debt") or {}, cls)
    if recorded is None and declared is None:
        raise SystemExit(f"FAIL-CLOSED: {key} carries neither a declared number nor a readable history row - the "
                         f"act cannot know which number it is moving away from (C16/D-3034)")
    previous = recorded if recorded is not None else int(declared)
    out = value_re.sub(lambda m: m.group("pad") + str(to), text, count=1)
    date_re = re.compile(r"(?m)^(?P<pad>[ \t]*measured: )'?\d{4}-\d{2}-\d{2}'?[ \t]*$")
    if date_re.search(out) is None:
        raise SystemExit("FAIL-CLOSED: config/capability_registry.yaml#routing_debt declares no dated `measured:` "
                         "- an act that cannot re-date the reading cannot honestly record it (BUG-1097)")
    out = date_re.sub(lambda m: m.group("pad") + "'" + date + "'", out, count=1)
    row = (f"- {{date: '{date}', target: {key}, frm: {previous}, to: {to}, decision: {decision}, "
           f"why: {json.dumps(why)}}}")
    rows = out.splitlines(keepends=True)
    header = next((i for i, raw in enumerate(rows)
                   if re.match(rf"^[ \t]*{re.escape(HISTORY_KEY)}:[ \t]*(#.*)?$", raw)), None)
    if header is None:
        raise SystemExit(f"FAIL-CLOSED: config/capability_registry.yaml#routing_debt declares no `{HISTORY_KEY}:` "
                         f"list - the act appends the record it will be judged by, and a record it cannot append "
                         f"to is a raise that would go unrecorded (BUG-1097)")
    head_indent = len(rows[header]) - len(rows[header].lstrip())
    insert_at, indent = header + 1, head_indent + 2
    for index in range(header + 1, len(rows)):
        raw = rows[index]
        if not raw.strip():
            continue
        here = len(raw) - len(raw.lstrip())
        if here <= head_indent:
            break
        indent, insert_at = here, index + 1
    return "".join(rows[:insert_at]) + (" " * indent) + row + "\n" + "".join(rows[insert_at:])


def rebaseline(spec: str | None, because: str | None) -> int:
    """THE ONE ACT that may move a ceiling, and the only writer of config/capability_registry.yaml#routing_debt.

    Direction decides the requirement, and that is the whole of D-2644: LOWERING pays debt down and needs nothing
    (a shrink is not a decision); RAISING rides a DECISION, so `--because` is required and the id must EXIST in
    config/decisions.yaml - mint it first, then raise (D-2660/D-2982). Everything about the act is verified before
    a byte is committed, and the write itself is crash-safe, backed up and journaled (C6/D-401).
    """
    if not spec or "=" not in spec:
        print("FAIL rebaseline: --rebaseline needs --set <tasks|bugs>=<n> - e.g. "
              "--rebaseline --set bugs=172")
        return 2
    raw_cls, _, raw_to = spec.partition("=")
    cls = raw_cls.strip().lower()
    if cls not in DEBT_CLASSES:
        print(f"FAIL rebaseline: {raw_cls!r} is not a declared debt class (expected one of "
              f"{', '.join(DEBT_CLASSES)})")
        return 2
    try:
        to = int(raw_to.strip())
    except ValueError:
        print(f"FAIL rebaseline: {raw_to!r} is not an integer - a ceiling is a count, not a phrase")
        return 2
    key = f"unrouted_open_{cls}"
    text = CFG.read_text(encoding="utf-8")
    block = (yaml.safe_load(text) or {}).get("routing_debt") or {}
    declared, recorded, _rows = ceiling_record(block, cls)
    if declared is None and recorded is None:
        print(f"FAIL rebaseline: {key} carries neither a declared number nor a readable history row - the act "
              f"cannot know which number it moves away from (C16)")
        return 2
    current = recorded if recorded is not None else declared
    if declared is not None and recorded is not None and declared != recorded:
        # A hand-edited number is a CACHE that disagrees with the ledger. The act moves from the LEDGER, because
        # the alternative is that an owner who made the forbidden edit can only repair it with another forbidden
        # edit - a guard with no legal way back is a guard that will be worked around.
        print(f"note: {key} is DECLARED {declared} but its record ends at {recorded} - the record is the ledger, "
              f"so this act moves from {current}, and recording it is the only way back")
    to = int(raw_to.strip())
    if to == current:
        print(f"FAIL rebaseline: {key} is already {to} - nothing to record, and an empty act is noise in a "
              f"history that is meant to be read")
        return 2
    if to > current:
        if not because:
            print(f"FAIL rebaseline: raising {key} {current} -> {to} needs --because <D-id> - a raise is a "
                  f"DECISION, not an edit (D-2644/D-3023); mint the decision first, then cite it")
            return 2
        known = handoff.decision_ids()
        if because not in known:
            print(f"FAIL rebaseline: --because {because} is not an id in config/decisions.yaml ({len(known)} "
                  f"known) - a raise may not cite a record that does not exist (D-2660)")
            return 2
        why = f"RAISED {current} -> {to} under {because}"
    else:
        why = f"LOWERED {current} -> {to} to the measured reading" + (f", cited {because}" if because else "")
    date = yaml_guard.today()
    updated = apply_ceiling(text, cls, to, decision=because or "null", why=why, date=date)
    verdict = yaml.safe_load(updated) or {}
    block = verdict.get("routing_debt") or {}
    rows = [r for r in (block.get(HISTORY_KEY) or []) if isinstance(r, dict) and r.get("target") == key]
    faults = []
    if block.get(key) != to:
        faults.append(f"{key} reads {block.get(key)!r} after the transform, not {to}")
    if not rows or int(rows[-1].get("to", -1)) != to:
        faults.append("the appended record does not END at the new value")
    if block.get("measured") != date:
        faults.append(f"measured reads {block.get('measured')!r}, not {date}")
    if faults:
        print("FAIL rebaseline: the transform did not produce the act it described, nothing was written "
              f"(C6/D-401): {'; '.join(faults)}")
        return 2
    report = write_guard.write_document(CFG, updated, writer=RAIL_REL, owned_keys={write_guard.OWNED_ANY},
                                        backup=True)
    print(f"ok rebaseline: {key} {current} -> {to} RECORDED, measured re-dated {date}, history row appended "
          f"(pre {report.pre_sha16} -> post {report.post_sha16}). A raise cites the decision that justifies it, "
          f"so the next move is judged against this one.")
    return 0


def check(w: World) -> tuple[list[str], dict]:
    """Return (faults, census) for one world. PURE: every fact arrives injected (the controls prove the logic)."""
    caps = list(w.cfg.get("capabilities") or [])
    faults: list[str] = []
    seen: set[str] = set()
    for cap in sorted(caps, key=lambda c: str(c.get("id"))):
        cid = str(cap.get("id") or "")
        if cid in seen:
            faults.append(f"capability {cid}: declared TWICE - a second declaration of one route is a second copy "
                          f"of a fact (C12)")
        seen.add(cid)
        faults.extend(capability_faults(cap, w))
    lanes = list(w.cfg.get("lanes") or [])
    for lane in sorted(lanes, key=lambda l: str(l.get("recipe"))):
        faults.extend(lane_faults(lane, w))
    ifaults, rows, debt = item_faults(w)
    faults.extend(ifaults)
    ceilings = w.cfg.get("routing_debt") or {}
    for cls in DEBT_CLASSES:
        ceiling = ceilings.get(f"unrouted_open_{cls}")
        if isinstance(ceiling, int) and debt[cls] > ceiling:
            # BUG-855 (MEASURED 2026-10-16): `Item.cls` is the SINGULAR class token while `cls` here is the PLURAL
            # ceiling key, so this comprehension matched NO row and the sentence ended at "Now unrouted: " - the ONE
            # fault whose whole purpose is to name the items named none of them. `debt` above already compares with
            # the singular, which is why the count and the ceiling were right while the LIST was empty.
            grown = [i.id for i, c, _ in rows if i.cls == cls[:-1] and c != "routed"]
            faults.append(f"(vi) ROUTING DEBT GREW: {debt[cls]} open {cls} resolve to no declared capability, "
                          f"against a declared ceiling of {ceiling} (SHRINK-ONLY, the D-3023 shape). Declare the "
                          f"route, or disposition the item - never raise the ceiling. Now unrouted: "
                          f"{', '.join(sorted(grown)[:12])}" + (" ..." if len(grown) > 12 else ""))
    # BUG-1097: the OTHER direction. The comparison above asks whether the DEBT outgrew its allowance; this asks
    # whether the ALLOWANCE itself moved without a signed act. Without it a ceiling is a promise, not an invariant.
    faults.extend(ceiling_faults(ceilings, w.decisions))
    census = {"capabilities": len(caps), "facts": facts_census(w, caps),
              "by_kind": {k: sum(1 for c in caps if str(c.get("kind")) == k)
                          for k in sorted({str(c.get("kind")) for c in caps})},
              "by_tier": {t: sum(1 for c in caps if str(c.get("cost_tier")) == t)
                          for t in sorted({str(c.get("cost_tier")) for c in caps})},
              "lanes": len(lanes), "edges": w.edges, "debt": debt,
              "ceiling": {c: ceilings.get(f"unrouted_open_{c}") for c in DEBT_CLASSES},
              #: BUG-1097: the number is half the fact; the ANCHOR is what makes it an invariant. Both are carried
              #: into the report so a reader can see the ceiling is DATED and RECORDED without opening the YAML.
              "ceiling_measured": ceilings.get("measured"),
              "ceiling_acts": len([r for r in (ceilings.get(HISTORY_KEY) or []) if isinstance(r, dict)]),
              "items": len(w.items), "rows": rows, "tiers": sorted(w.tiers)}
    return faults, census


def route_lines(census: dict, w: World) -> list[str]:
    """The deterministic body of the report: every list sorted, no timestamp (a clock in a report is a report that
    cannot be compared with itself, BUG-597's lesson)."""
    caps = sorted((c for c in w.cfg.get("capabilities") or []), key=lambda c: str(c.get("id")))
    lines = [f"route graph (D-3024/T-156): {census['capabilities']} capability(ies) "
             f"{json.dumps(census['by_kind'], sort_keys=True)} tiers {json.dumps(census['by_tier'], sort_keys=True)}"
             f" | {census['lanes']} operator lane(s) | composed edges: {census['edges'][0]} declaration "
             f"consumer(s), {census['edges'][1]} flag consumer(s) | tier vocabulary {census['tiers']}"]
    for c in caps:
        lines.append(f"  {str(c['id']):18s} {str(c.get('kind')):12s} {str(c.get('cost_tier')):3s} "
                     f"{str(c.get('entrypoint'))}")
    for lane in sorted((l for l in w.cfg.get("lanes") or []), key=lambda l: str(l.get("recipe"))):
        lines.append(f"  lane {str(lane.get('recipe')):16s} {str(lane.get('produces')):8s} {str(lane.get('cmd'))}")
    for cls in ("task", "bug"):
        rows = [(i, c) for i, c, _ in census["rows"] if i.cls == cls]
        by = {k: 0 for k in ("routed", "unowned_artifact", "absent_path", "no_artifact_named")}
        for _, cat in rows:
            by[cat] = by.get(cat, 0) + 1
        lines.append(f"item census ({cls}s): {len(rows)} open | " +
                     " | ".join(f"{k} {v}" for k, v in sorted(by.items())))
        for cat in ("unowned_artifact", "absent_path"):
            ids = sorted(i.id for i, c in rows if c == cat)
            if ids:
                lines.append(f"  {cat}: {', '.join(ids)}")
    lines.append(f"debt facts: {len(census['facts']['exists_unowned'])} item(s) name an artifact that EXISTS "
                 f"and NO capability owns (a missing ROUTE); {len(census['facts']['absent'])} item(s) name a path that "
                 f"does not exist in the repo (a proposal, an out-of-repo home, or a stale citation - the reader "
                 f"reports the FACT and does not claim which)")
    lines.append(f"routing debt: tasks {census['debt']['tasks']}/{census['ceiling']['tasks']} "
                 f"bugs {census['debt']['bugs']}/{census['ceiling']['bugs']} (measured/ceiling, SHRINK-ONLY; a bug "
                 f"is read by id + title + the artifacts its OWN evidence names, D-3212 - before that correction "
                 f"the reader saw only id + title and 69 open bugs read as unrouted debt)")
    lines.append(f"ceiling anchor: measured {census.get('ceiling_measured')}, {census.get('ceiling_acts')} "
                 f"recorded act(s) in routing_debt.{HISTORY_KEY} - the declared number must be the number the "
                 f"record ENDS at, and a raise must cite a decision that exists (BUG-1097: the ceiling used to "
                 f"move in silence and `measured` was read by no code at all)")
    per = {}
    for _, _, hits in census["rows"]:
        for h in hits:
            per[h] = per.get(h, 0) + 1
    for cid in sorted(per):
        lines.append(f"  routes to {cid}: {per[cid]} open item(s)")
    return lines


def render(census: dict, w: World) -> str:
    """ONE home of the report text: what `--check` digests and what `--report` prints are the SAME bytes."""
    body = "\n".join(route_lines(census, w))
    return body + "\nDIGEST " + hashlib.sha256(body.encode()).hexdigest()[:16] + "\n"


def census_report() -> str:
    """T-156's own instrument (D-2642: the number is quoted WITH it): how many python files exist and how many are
    named by a declared home, and how many declare a check verb. No clock in it, so two runs are comparable."""
    arg = re.compile(r"add_argument\(\s*[\"']--(?:selftest|check)[\"']")
    files = sorted(pathlib.Path(REPO, "pipeline").rglob("*.py")) + \
        sorted(pathlib.Path(REPO, "scripts").glob("*.py")) + sorted(pathlib.Path(REPO).glob("*.py"))
    files = [p for p in files if "__pycache__" not in str(p)]
    corpus = [pathlib.Path(REPO, "justfile").read_text(encoding="utf-8")]
    for pat in ("config/*.yaml", "config/*.json", "governance/**/*.md"):
        for p in sorted(REPO.glob(pat)):
            corpus.append(artifact_encoding.open_artifact(p, REPO).read())
    for extra in ("CLAUDE.md", "AGENTS.md", "DECISION-LOG.md", "MASTER-TASK-REGISTER.md"):
        if (REPO / extra).is_file():
            corpus.append(artifact_encoding.open_artifact(REPO / extra, REPO).read())
    blob = "\n".join(corpus)
    unnamed = [str(p.relative_to(REPO)) for p in files if p.name not in blob]
    verbs = sum(1 for p in files if arg.search(artifact_encoding.open_artifact(p, REPO).read()))
    lines = [f"census: {len(files)} python file(s) | {len(unnamed)} named by NO declared home | "
             f"{verbs} declare a check verb",
             "join: a file counts as NAMED when its BASENAME appears in the corpus - COARSE by declaration: "
             "a mention in prose counts, so the unnamed count is a LOWER bound",
             f"declared homes: justfile + config/*.yaml|json + governance/**/*.md + the four faces "
             f"({len(corpus)} file(s), {len(blob)} bytes)",
             f"fingerprint {hashlib.sha256(blob.encode()).hexdigest()[:16]}"]
    for p in unnamed:
        lines.append(f"  unnamed {p}")
    return "\n".join(lines)


# ------------------------------------------------------------------ controls
def ceiling_fixture(tasks: int = 1, bugs: int = 0, date: str = "2026-01-01",
                    history: "list[dict] | None" = None) -> dict:
    """A well-formed routing_debt block for fixtures: DATED, and ANCHORED by one row per class (BUG-1097).

    Every control below turns ONE declared fact false, so every OTHER fact has to be true or the fault it counts
    is a fault it merely happened to trip on. Here the numbers and the history agree BY CONSTRUCTION, which is
    exactly the property the guard reads in the live registry.
    """
    rows = history if history is not None else [
        {"date": date, "target": f"unrouted_open_{cls}", "frm": n, "to": n, "decision": None, "why": "fixture"}
        for cls, n in (("tasks", tasks), ("bugs", bugs))]
    return {"measured": date, "unrouted_open_tasks": tasks, "unrouted_open_bugs": bugs, HISTORY_KEY: rows}


def synthetic(**over) -> World:
    """A small well-formed graph, so every control below turns ONE declared fact false and proves the fault fires."""
    cfg = {"schema_version": "1", "authority": "fixture", "kinds": {"script": "x", "recipe": "y"},
           "capabilities": [{"id": "cap_a", "kind": "script", "entrypoint": "python3 scripts/check_a.py",
                             "check": "python3 scripts/check_a.py --selftest", "receipt": "temp/receipt.json",
                             "cost_tier": "T0", "owns": ["scripts/check_a.py"]}],
           "lanes": [{"recipe": "lane_a", "cmd": "scripts/check_a.py --selftest", "produces": "reading",
                      "why": "fixture"}],
           "dispositions": {"tasks": {"pipeline": "r_no_route"}, "bugs": {"default": "r_bug"}},
           "reasons": {"r_no_route": "fixture", "r_bug": "fixture"},
           "routing_debt": ceiling_fixture(tasks=1, bugs=0)}
    cfg.update(over.pop("cfg", {}))
    w = World(cfg=cfg, recipes={"lane_a": "    python3 scripts/check_a.py --selftest"}, governed=("health",),
              exists=lambda p: p in {"scripts/check_a.py", "temp", "temp/receipt.json"},
              executable=lambda p: p == "scripts/check_a.py", tiers={"T0", "T1", "T2"},
              items=[Item("T-X", "task", "pipeline", "no artifact here")], edges=(0, 0),
              decisions=lambda: {"D-0001"})
    return dataclasses.replace(w, **over) if over else w


def selftest() -> int:
    """Known-answer controls: a registry that never reports a fault is not a registry (BUG-492)."""
    ok = fail = 0

    def control(name: str, faults: "list[str] | int", want: int, why: str) -> None:
        """One known answer: a COUNT (already filtered by the caller) or the fault list itself."""
        nonlocal ok, fail
        n = faults if isinstance(faults, int) else len(faults)
        if n == want:
            ok += 1
            print(f"  ok   selftest/{name}: {why}")
        else:
            fail += 1
            print(f"  FAIL selftest/{name}: {why} (got {n} fault(s), want {want})")
            if isinstance(faults, list):
                for x in faults:
                    print(f"         -> {x}")

    f, _ = check(*((lambda w: (w,)))([])[:0]) if False else (check.__name__, None)  # noqa: F841 - no-op guard
    f, _c = check_world(synthetic())
    control("clean_graph", f, 0, "a well-formed graph over a resolvable recipe is silent")

    w = synthetic()
    w.cfg["capabilities"][0].pop("check")
    f, _ = check_world(w)
    control("capability_without_check", f, 1, "a capability with no CHECK is refused (T-156's gate)")

    w = synthetic()
    w.cfg["capabilities"][0]["entrypoint"] = "python3 scripts/absent.py"
    f, _ = check_world(w)
    control("entrypoint_absent", f, 1, "a declared route whose ENTRYPOINT is absent is refused")

    w = synthetic()
    w.cfg["capabilities"][0]["entrypoint"] = "just no_such_recipe"
    f, _ = check_world(w)
    control("recipe_absent", f, 1, "a `just <recipe>` route whose recipe is gone is refused")

    # A PARAMETRISED RECIPE IS STILL A RECIPE (BUG-880, MEASURED 2026-10-17): the header pattern required the
    # colon IMMEDIATELY after the name, so `admit-apply *ARGS:` - a real, runnable recipe - was invisible, and a
    # lane pointing at it read "the ladder file declares no such recipe". A route that exists read as absent: the
    # exact defect class (D-3034) the lane check exists to catch, turned against a working declaration.
    bodies = recipe_bodies("admit-apply *ARGS:\n    python3 x.py\n\nplain:\n    y\n")
    control("parametrised_recipe_header",
            [] if bodies.get("admit-apply", "").strip() == "python3 x.py" and bodies.get("plain") == "    y"
            else ["a parametrised header is unreadable"], 0,
            "a recipe with a parameter is parsed, so a lane may point at one")

    w = synthetic()
    w.cfg["capabilities"][0]["entrypoint"] = "scripts/check_a.py --selftest"
    w = dataclasses.replace(w, executable=lambda p: False)
    f, _ = check_world(w)
    control("bare_path_not_executable", f, 2, "the BARE form is refused at BOTH sites (a capability and a lane) - "
            "this is the command the owner typed and got permission denied (BUG-842/T-146)")

    w = synthetic()
    w.cfg["capabilities"][0]["entrypoint"] = "python3 scripts/check_a.py --selftest"
    w.cfg["lanes"][0]["cmd"] = "python3 scripts/check_a.py --selftest"
    w = dataclasses.replace(w, executable=lambda p: False)
    f, _ = check_world(w)
    control("interpreter_form_needs_no_exec_bit", f, 0, "the OTHER direction: 562 tracked .py files carry a "
            "shebang and are not executable, so the declared 'python3 X' form must NOT require the bit")

    lane = {"recipe": "lane_a", "cmd": "scripts/check_a.py --selftest", "produces": "reading", "why": "fixture"}
    w = dataclasses.replace(synthetic(), recipes={
        "lane_a": "    python3 scripts/check_a.py --selftest",
        "health": "    echo ok   # scripts/check_a.py --selftest is run by a lane, never by this recipe"})
    control("a_MENTION_in_a_COMMENT_is_not_a_RUN", lane_faults(lane, w), 0,
            "MEASURED 2026-10-25/BUG-1014: a comment that merely NAMED a lane's command made this rail report that "
            "the lane was a ladder rail - the mention acted as a declaration (BUG-838 limb 3, one register over), "
            "and a FALSE RED is worse than an UNKNOWN (D-3150)")

    w = dataclasses.replace(synthetic(), recipes={
        "lane_a": "    python3 scripts/check_a.py --selftest",
        "health": "    scripts/check_a.py --selftest"})
    control("a_REAL_line_in_a_governed_recipe_IS_a_RUN", lane_faults(lane, w), 1,
            "the other direction, unchanged: stripping comments must NOT hide a genuine ladder rail - a lane whose "
            "command really runs in a governed recipe still has to move to rail_registry#guards (T-164)")

    w = synthetic()
    w.cfg["capabilities"][0]["cost_tier"] = "T9"
    f, _ = check_world(w)
    control("tier_outside_economy", f, 1, "a cost tier the economy does not declare is refused (composed vocabulary)")

    w = synthetic()
    w.cfg["capabilities"][0]["kind"] = "wizard"
    f, _ = check_world(w)
    control("kind_not_declared", f, 1, "a kind outside the declared vocabulary is refused")

    w = synthetic()
    w.cfg["capabilities"][0]["owns"] = "scripts/check_a.py"
    f, _ = check_world(w)
    control("owns_is_not_a_list", f, 1, "a bare string for owns is ONE fault, not a fault per letter")

    w = synthetic()
    w.cfg["capabilities"][0]["owns"] = ["scripts/absent_dir/"]
    f, _ = check_world(w)
    control("owned_path_absent", f, 1, "owning a path that does not exist is an assertion (D-405/BUG-488)")

    w = synthetic()
    w.cfg["lanes"][0]["cmd"] = "scripts/check_a.py --census"
    f, _ = check_world(w)
    control("lane_cmd_left_the_recipe", f, 1, "a lane whose command the recipe no longer carries is refused")

    w = synthetic(recipes={"lane_a": "    python3 scripts/check_a.py --selftest", "health": "    python3 "
                                                                                            "scripts/check_a.py "
                                                                                            "--selftest || exit 1"})
    f, _ = check_world(w)
    control("lane_cmd_is_a_ladder_rail", len([x for x in f if "ALSO run" in x]), 1,
          "a lane command that a GOVERNED recipe also runs belongs in rail_registry#guards (T-164)")

    w = synthetic()
    w.cfg["dispositions"]["tasks"] = {}
    f, _ = check_world(w)
    control("mover_not_dispositioned", len([x for x in f if "mover" in x.lower()]), 1,
          "an open item whose MOVER has no declared disposition is refused")

    w = synthetic()
    w.cfg["unrouted"] = {"T-CLOSED": "r_no_route"}
    f, _ = check_world(w)
    control("stale_unrouted_declaration", len([x for x in f if "STALE" in x]), 1,
          "an unrouted declaration for an item that is not open is refused")

    # D-3212: the OTHER end of the same declaration. (v) above asks whether the item is still OPEN; this asks
    # whether it is still UNROUTED. An escape on a routed item excuses nothing, and the day the bug reader was
    # widened TEN of the fifteen live declarations went inert while the rail stayed silent.
    w = synthetic(items=[Item("T-X", "task", "pipeline", "scripts/check_a.py")])
    w.cfg["unrouted"] = {"T-X": "r_no_route"}
    f, _ = check_world(w)
    control("inert_unrouted_declaration", len([x for x in f if "INERT" in x]), 1,
          "an unrouted declaration on an item the graph DOES route is refused - it excuses nothing and hides the "
          "fact that the cure arrived (D-3034/D-3212)")

    w = synthetic(items=[Item("T-X", "task", "pipeline", "x"), Item("T-Y", "task", "pipeline", "y")])
    f, _ = check_world(w)
    control("debt_grew", len([x for x in f if "DEBT GREW" in x]), 1,
          "routing debt above the declared shrink-only ceiling is refused (D-3023 shape)")

    # BUG-855: the assertion is on the IDS, never on the fault's existence - a fault that names nothing passed the
    # control above, which is why nothing caught this. A world of two unrouted BUGS against a ceiling of one.
    wb = synthetic(items=[Item("B-1", "bug", "", "x"), Item("B-2", "bug", "", "y")],
                   cfg={"routing_debt": ceiling_fixture(tasks=1, bugs=1)})
    fb, _ = check_world(wb)
    control("debt_grew_names_the_bugs_it_is_about",
          len([x for x in fb if "DEBT GREW" in x and "B-1" in x and "B-2" in x]), 1,
          "the routing-debt fault PRINTS the ids it is about, never an empty list (BUG-855)")

    w = synthetic()
    _f, c = check_world(w)
    r1, r2 = render(c, w), render(c, w)
    control("report_is_byte_stable", [] if r1 == r2 else ["digest differs"], 0,
          "the report is byte-stable: two renders of one world agree")

    w = synthetic()
    w.cfg["reasons"] = {}
    f, _ = check_world(w)
    control("reason_not_declared", len([x for x in f if "not declared" in x]), 2,
          "a disposition or an unrouted override naming an undeclared reason is refused")

    # ── BUG-1097: the ceiling itself is a value a reader can be wrong about, in the OTHER direction ──────────
    # The red loop this file's own fault (viii) exists for: the declared number and the record that explains it
    # disagree, i.e. the ceiling MOVED by an edit. MEASURED 2026-10-28 before the guard: 172 -> 173 by a bare
    # edit, rail rc 0. The control drives the same shape on a fixture.
    moved = ceiling_fixture(tasks=1, bugs=1)
    moved["unrouted_open_bugs"] = 2
    control("ceiling_moved_by_an_edit", len([x for x in ceiling_faults(moved, lambda: {"D-0001"})
                                             if "UNANCHORED" in x]), 1,
            "a ceiling that is not the number its own record ENDS at is refused - the raise limb (BUG-1097)")

    unsigned = ceiling_fixture(tasks=1, bugs=1)
    unsigned[HISTORY_KEY] = unsigned[HISTORY_KEY][:1] + [
        {"date": "2026-01-02", "target": "unrouted_open_bugs", "frm": 1, "to": 2, "decision": None,
         "why": "raised for no stated reason"}]
    unsigned["unrouted_open_bugs"] = 2
    control("raise_with_no_decision", len([x for x in ceiling_faults(unsigned, lambda: {"D-0001"})
                                           if "UNSIGNED RAISE" in x]), 1,
            "a RAISE that cites no decision is refused - a raise is a decision, not an edit (D-2644)")

    absent = ceiling_fixture(tasks=1, bugs=1)
    absent[HISTORY_KEY] = absent[HISTORY_KEY][:1] + [
        {"date": "2026-01-02", "target": "unrouted_open_bugs", "frm": 1, "to": 2, "decision": "D-9999",
         "why": "cited a record that does not exist"}]
    absent["unrouted_open_bugs"] = 2
    control("raise_citing_an_absent_decision", len([x for x in ceiling_faults(absent, lambda: {"D-0001"})
                                                    if "UNSIGNED RAISE" in x]), 1,
            "a raise citing an id that is not in config/decisions.yaml is refused (D-2660)")

    signed = ceiling_fixture(tasks=1, bugs=1)
    signed[HISTORY_KEY] = signed[HISTORY_KEY][:1] + [
        {"date": "2026-01-01", "target": "unrouted_open_bugs", "frm": 1, "to": 2, "decision": "D-0001",
         "why": "the OTHER direction: a cited, chained raise, dated the day of the measurement it rests on"}]
    signed["unrouted_open_bugs"] = 2
    control("signed_raise_is_accepted", ceiling_faults(signed, lambda: {"D-0001"}), 0,
            "a raise that cites a decision WHICH EXISTS and chains onto the record is silent - the guard refuses "
            "the act it cannot justify, never the act it can (note the row must ALSO be dated no later than "
            "`measured`: a raise recorded after the reading is the stale shape)")

    stale = ceiling_fixture(tasks=1, bugs=0)
    stale["measured"] = "2025-12-31"
    control("measurement_predating_the_act", len([x for x in ceiling_faults(stale, lambda: set())
                                                 if "STALE MEASUREMENT" in x]), 2,
            "`measured` is READ, once per class: a reading older than the last recorded act is refused, which is "
            "the consumer D-3034 required and nothing had (BUG-1097)")

    unquoted = ceiling_fixture()
    unquoted["measured"] = datetime.date(2026, 1, 1)     # the SAME declaration, spelled without quotes
    control("measurement_as_a_yaml_date", [x for x in ceiling_faults(unquoted, lambda: set())
                                           if "STALE MEASUREMENT" in x], 0,
            "`measured: 2026-10-28` unquoted arrives as a datetime.date and is ACCEPTED - one reader for one fact, "
            "so a valid registry can never be refused for its quoting")

    undated = ceiling_fixture()
    undated["measured"] = "fixture"
    control("measurement_is_not_a_date", len([x for x in ceiling_faults(undated, lambda: set())
                                             if "STALE MEASUREMENT" in x]), 1,
            "a `measured` that is not an ISO date is refused - a reading nobody can date cannot be re-taken")

    # THE WRITE ACT, proved as a transform before any byte is committed: the fixture carries ONE history row (bugs
    # 3 -> 3) and the act must re-record the number, APPEND the row that chains onto it, re-date `measured` and
    # leave the OTHER class untouched - a scope guard, because an act that rewrites a neighbouring number is the
    # defect it was meant to prevent.
    fixture = ("x: 1\n"
               "routing_debt:\n"
               "  measured: '2026-01-01'\n"
               "  unrouted_open_tasks: 2\n"
               "  unrouted_open_bugs: 3\n"
               f"  {HISTORY_KEY}:\n"
               "    - {date: '2026-01-01', target: unrouted_open_bugs, frm: 3, to: 3, decision: null, why: 'o'}\n"
               "tail: 9\n")
    try:
        after = yaml.safe_load(apply_ceiling(fixture, "bugs", 5, decision="D-0001", why="fixture raise",
                                             date="2026-02-02")) or {}
        block = after.get("routing_debt") or {}
        rows = block.get(HISTORY_KEY) or []
        bad = [why for why, ok in (
            ("bugs not re-recorded", block.get("unrouted_open_bugs") == 5),
            ("the appended row does not END at the new value",
             bool(rows) and rows[-1].get("to") == 5 and rows[-1].get("frm") == 3),
            ("the row does not carry its decision", bool(rows) and rows[-1].get("decision") == "D-0001"),
            ("measured was not re-dated", block.get("measured") == "2026-02-02"),
            ("the OTHER class was touched", block.get("unrouted_open_tasks") == 2),
            ("the row was appended outside its block", after.get("tail") == 9),
        ) if not ok]
    except SystemExit as exc:                                   # fail closed is a PASS for the control only if named
        bad = [f"the act refused a well-formed fixture: {exc}"]
    control("rebaseline_writes_the_number_and_the_row", bad, 0,
            "the one act that moves a ceiling re-records the number, APPENDS the chained row that justifies it and "
            "re-dates `measured` - and touches nothing else (C6/D-401)")

    print(f"resolve-route controls: {ok}/{ok + fail} known-answer control(s) fire")
    return 1 if fail else 0


def check_world(w: World) -> tuple[list[str], dict]:
    """A thin alias so the controls read as judgements about a WORLD (and so `check` stays PURE)."""
    return check(w)


def main() -> int:
    ap = argparse.ArgumentParser(description="the ROUTE GRAPH: which capability owns this work")
    ap.add_argument("--check", action="store_true", help="fail on an incomplete capability, an absent route, an "
                                                         "undeclared mover or routing debt that grew")
    ap.add_argument("--route", metavar="ITEM_ID", help="resolve ONE open item to the capabilities that own it")
    ap.add_argument("--census", action="store_true", help="T-156's own instrument: how many files are named")
    ap.add_argument("--propose", metavar="FILE", help="validate a PROPOSAL from temp/ (never apply it, D-2941)")
    ap.add_argument("--rebaseline", action="store_true",
                    help="THE ONE ACT that moves a routing-debt ceiling (D-2644/BUG-1097): re-record it, re-date "
                         "`measured`, append the history row. Needs --set <tasks|bugs>=<n>; a RAISE also needs "
                         "--because <D-id>, and that id must exist in config/decisions.yaml")
    ap.add_argument("--set", dest="set_to", metavar="CLASS=N",
                    help="the ceiling to re-record, e.g. --set bugs=172 (lowering needs no --because)")
    ap.add_argument("--because", metavar="D-xxxx", help="the decision that justifies a RAISE (D-2644/D-2660)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over synthetic graphs")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.rebaseline:
        return rebaseline(a.set_to, a.because)
    if a.census:
        print(census_report())
        return 0
    if a.propose:
        p = pathlib.Path(a.propose)
        if not p.is_absolute():
            p = REPO / p
        if TEMP.resolve() not in p.resolve().parents:
            print(f"FAIL proposal: {a.propose} is not under temp/ - an LLM may write a PROPOSAL into temp/ and "
                  f"never an assignment into a governed home (D-2898/D-2941)")
            return 1
        if not p.is_file():
            print(f"FAIL proposal: {a.propose} does not exist")
            return 1
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            print(f"FAIL proposal: unreadable YAML: {exc}")
            return 1
        blocks = doc.get("capabilities") or ([doc] if "id" in doc else [])
        w = world()
        faults = [f for b in blocks for f in capability_faults(b, w)]
        for x in faults:
            print("  - " + x)
        print(f"proposal {a.propose}: {len(blocks)} capability block(s), {len(faults)} fault(s). "
              f"VALIDATION ONLY - nothing was written and nothing was assigned: applying it is a governed edit.")
        return 1 if faults else 0
    try:
        w = world()
    except SystemExit as exc:
        print(str(exc))
        return 2
    faults, census = check(w)
    body = render(census, w)
    if a.route:
        rows = {i.id: (c, h) for i, c, h in census["rows"]}
        if a.route not in rows:
            print(f"route: {a.route} is not an open item")
            return 2
        cat, hits = rows[a.route]
        print(f"route {a.route}: {cat}" + (f" -> {', '.join(hits)}" if hits else ""))
        for cid in hits:
            cap = next(c for c in w.cfg["capabilities"] if str(c["id"]) == cid)
            print(f"  {cid}: entrypoint {cap['entrypoint']} | check {cap['check']} | receipt {cap['receipt']} | "
                  f"tier {cap['cost_tier']}")
        return 0
    print(body, end="")
    if a.check:
        twice = render(check(w)[1], w)
        if twice != body:
            faults.append("(vii) the report is NOT byte-stable: two renders of one world differ")
        if faults:
            print(f"\nFAIL route graph: {len(faults)} fault(s):")
            for x in faults:
                print("  - " + x)
            return 1
        print("  ok   the route graph is well-formed: every capability resolves its entrypoint, check, receipt and "
              "tier, every lane still points at a command its recipe carries, every open item is routed or carries a "
              "declared reason, and the routing debt is within its shrink-only ceiling")
        return 0
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
