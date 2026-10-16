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
  * the report is BYTE-STABLE: it is rendered twice and the two digests must agree.
It does NOT decide policy, and it never assigns: an LLM may write a PROPOSAL into temp/ and `--propose` validates
it against this same schema while writing nothing (D-2898/D-2941).

Exit: 0 ok | 1 fault(s) | 2 the registry itself is unreadable/incomplete (fail closed, C16).
--selftest: known-answer controls over SYNTHETIC graphs (no model, no live write, BUG-492).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
import sys
from typing import Callable

import yaml

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
ARTIFACT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ya?ml|json|md|sh|jsonl|txt)")
JUST = re.compile(r"\bjust\s+([A-Za-z0-9][A-Za-z0-9_-]*)")   # a recipe name may carry _ and - (justfile)
TIER = re.compile(r"\bT[0-2]\b")
RECIPE = re.compile(r"^([A-Za-z0-9_-]+):")
PATHISH = re.compile(r"^[\w.-]+(?:/[\w .&()-]+)+$")


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
        text = (REPO / path).read_text(encoding="utf-8", errors="replace")
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
        items.append(Item(id=str(b["id"]), cls="bug", mover="", text=f"{b.get('id', '')} {b.get('title', '')}"))
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
                 items=load_items(), edges=edges)


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
            if name in w.recipes and cmd in w.recipes[name]:
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
        if category == "routed":
            continue
        table = (disp.get("tasks") if i.cls == "task" else disp.get("bugs")) or {}
        reason = table.get(i.mover) if i.cls == "task" else table.get("default")
        over = (w.cfg.get("unrouted") or {}).get(i.id)
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
    debt = {"tasks": sum(1 for i, c, _ in rows if i.cls == "task" and c != "routed"),
            "bugs": sum(1 for i, c, _ in rows if i.cls == "bug" and c != "routed")}
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
    for cls in ("tasks", "bugs"):
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
    census = {"capabilities": len(caps), "facts": facts_census(w, caps),
              "by_kind": {k: sum(1 for c in caps if str(c.get("kind")) == k)
                          for k in sorted({str(c.get("kind")) for c in caps})},
              "by_tier": {t: sum(1 for c in caps if str(c.get("cost_tier")) == t)
                          for t in sorted({str(c.get("cost_tier")) for c in caps})},
              "lanes": len(lanes), "edges": w.edges, "debt": debt,
              "ceiling": {c: ceilings.get(f"unrouted_open_{c}") for c in ("tasks", "bugs")},
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
                 f"bugs {census['debt']['bugs']}/{census['ceiling']['bugs']} (measured/ceiling, SHRINK-ONLY)")
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
            corpus.append(p.read_text(encoding="utf-8", errors="replace"))
    for extra in ("CLAUDE.md", "AGENTS.md", "DECISION-LOG.md", "MASTER-TASK-REGISTER.md"):
        if (REPO / extra).is_file():
            corpus.append((REPO / extra).read_text(encoding="utf-8", errors="replace"))
    blob = "\n".join(corpus)
    unnamed = [str(p.relative_to(REPO)) for p in files if p.name not in blob]
    verbs = sum(1 for p in files if arg.search(p.read_text(encoding="utf-8", errors="replace")))
    lines = [f"census: {len(files)} python file(s) | {len(unnamed)} named by NO declared home | "
             f"{verbs} declare a check verb",
             f"join: a file counts as NAMED when its BASENAME appears in the corpus - COARSE by declaration: "
             f"a mention in prose counts, so the unnamed count is a LOWER bound",
             f"declared homes: justfile + config/*.yaml|json + governance/**/*.md + the four faces "
             f"({len(corpus)} file(s), {len(blob)} bytes)",
             f"fingerprint {hashlib.sha256(blob.encode()).hexdigest()[:16]}"]
    for p in unnamed:
        lines.append(f"  unnamed {p}")
    return "\n".join(lines)


# ------------------------------------------------------------------ controls
def synthetic(**over) -> World:
    """A small well-formed graph, so every control below turns ONE declared fact false and proves the fault fires."""
    cfg = {"schema_version": "1", "authority": "fixture", "kinds": {"script": "x", "recipe": "y"},
           "capabilities": [{"id": "cap_a", "kind": "script", "entrypoint": "python3 scripts/check_a.py",
                             "check": "python3 scripts/check_a.py --selftest", "receipt": "temp/receipt.json",
                             "cost_tier": "T0", "owns": ["scripts/check_a.py"]}],
           "lanes": [{"recipe": "lane_a", "cmd": "scripts/check_a.py --selftest", "produces": "reading",
                      "why": "fixture"}],
           "dispositions": {"tasks": {"pipeline": "r_no_route"}, "bugs": {"default": "r_bug"}},
           "reasons": {"r_no_route": "fixture", "r_bug": "fixture"}, "routing_debt": {"measured": "fixture",
                                                                                     "unrouted_open_tasks": 1,
                                                                                     "unrouted_open_bugs": 0}}
    cfg.update(over.pop("cfg", {}))
    w = World(cfg=cfg, recipes={"lane_a": "    python3 scripts/check_a.py --selftest"}, governed=("health",),
              exists=lambda p: p in {"scripts/check_a.py", "temp", "temp/receipt.json"},
              executable=lambda p: p == "scripts/check_a.py", tiers={"T0", "T1", "T2"},
              items=[Item("T-X", "task", "pipeline", "no artifact here")], edges=(0, 0))
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

    w = synthetic(items=[Item("T-X", "task", "pipeline", "x"), Item("T-Y", "task", "pipeline", "y")])
    f, _ = check_world(w)
    control("debt_grew", len([x for x in f if "DEBT GREW" in x]), 1,
          "routing debt above the declared shrink-only ceiling is refused (D-3023 shape)")

    # BUG-855: the assertion is on the IDS, never on the fault's existence - a fault that names nothing passed the
    # control above, which is why nothing caught this. A world of two unrouted BUGS against a ceiling of one.
    wb = synthetic(items=[Item("B-1", "bug", "", "x"), Item("B-2", "bug", "", "y")],
                   cfg={"routing_debt": {"measured": "fixture", "unrouted_open_tasks": 1, "unrouted_open_bugs": 1}})
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
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over synthetic graphs")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
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
