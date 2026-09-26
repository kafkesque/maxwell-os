#!/usr/bin/env python3
"""reconcile.py - ONE engine that answers "where does a declaration disagree with reality, right now?".

WHY (D-405). The register's second-largest class is "a declaration and the world diverged and nothing
compared them": BUG-462 (a floor with no consumer), BUG-463 (a registry understating its own state), BUG-466
(148 rows against a declared 150), BUG-476 (five declared raters, three ever ran), BUG-450, BUG-454/461,
BUG-459, BUG-468, BUG-455/456, BUG-412. Each was found by a bespoke script someone had to REMEMBER to write.
This engine reads the declarations, re-derives every fact from the DECLARATION and the ARTIFACT
independently, and never from another rail's output - a rail whose evidence is the same source as the artifact
it checks cannot detect drift (BUG-467 class).

Two meta-checks live in the engine itself, because they are what stop this file becoming the 31st thing to
remember:
  reach - every scripts/check_*.py / verify_*.py that declares a contract must be invoked by a recipe.
          BUG-482: three checks built in one week were invoked by nothing - including the rail built to be
          un-silent. A check nothing runs is a comment, and forgetting to wire one is now visible.
  cover - every artifact in config/artifact_ownership.yaml must have a reconciliation entry or a declared
          unreconciled_reason.

Exit: 0 all ok | 1 DRIFT (a declaration is false) | 2 owner-owed only (loud, not fatal - BUG-457 convention).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.measure import (declared_resolver_metrics, emit_metric, floor_check,  # noqa: E402
                          min_records)
from lib import artifact_encoding  # noqa: E402 - the ONE home for reading a declared encoding (D-2644/D-2646)

CONFIG = REPO / "config" / "reconciliation.yaml"
OWNERSHIP = REPO / "config" / "artifact_ownership.yaml"
JUSTFILE = REPO / "justfile"
OUT = REPO / "governance" / "RECONCILIATION.json"
CHECK_SCRIPTS = ("check_", "verify_")


def _yaml(path: Path) -> dict:
    """Load a YAML file. A missing declaration is a defect, not an empty config (fail closed)."""
    import yaml
    if not path.exists():
        raise SystemExit(f"FAIL-CLOSED: declared file {path.relative_to(REPO)} does not exist")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve(dotted: str) -> tuple[bool, object]:
    """Resolve 'path/to/file.yaml#a.b.c' -> (found, value). A missing file or key is (False, None)."""
    rel, _, key = dotted.partition("#")
    p = REPO / rel
    if not p.exists():
        return False, None
    node: object = _yaml(p)
    for part in [k for k in key.split(".") if k]:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False, None
    return True, node


def _rows(path: Path) -> int:
    """Count the artifact's records: CSV rows, JSONL lines, or a JSON list/records key."""
    if not path.exists():
        return -1
    if path.suffix == ".csv":
        with path.open("r", encoding=artifact_encoding.read_encoding(path, REPO), newline="") as fh:
            return max(0, sum(1 for _ in csv.DictReader(fh)))
    if path.suffix == ".jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, list):
        return len(doc)
    for k in ("records", "rows", "items", "entries"):
        if isinstance(doc.get(k), list):
            return len(doc[k])
    return -1


def _columns(path: Path) -> list[str]:
    """Return a CSV artifact's header, or [] when it does not exist."""
    if not path.exists():
        return []
    with path.open("r", encoding=artifact_encoding.read_encoding(path, REPO), newline="") as fh:
        return list(csv.DictReader(fh).fieldnames or [])


def _values(path: Path, column: str) -> list[str]:
    """Return the distinct non-empty values of one CSV column, sorted (for enum_matches)."""
    if not path.exists():
        return []
    with path.open("r", encoding=artifact_encoding.read_encoding(path, REPO), newline="") as fh:
        return sorted({(r.get(column) or "").strip() for r in csv.DictReader(fh)} - {""})


REGISTRY = REPO / "config" / "decisions.yaml"
CITATION_KEYS = ("decided", "decided_by", "decision", "decision_id")


def _registry() -> tuple[set[str], list[dict]]:
    """Parse config/decisions.yaml DIRECTLY - never another rail's output (D-402).

    `D-331` and `D331` are ONE token (C21), so ids are compared normalised.
    """
    import yaml
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    recs = [r for r in (data.get("decisions") or []) if isinstance(r, dict)]
    return {str(r.get("id") or "").strip().replace("D-", "D").upper() for r in recs}, recs


def _id_shaped(value: object) -> bool:
    """True when the value BEGINS with an id-shaped token (D123 / D-123 / D274a)."""
    if value is None or isinstance(value, (dict, list)):
        return False
    text = str(value).strip().strip("'\"")
    if not text:
        return False
    token = text.split()[0]
    if not token.startswith("D"):
        return False
    body = token[1:].lstrip("-").rstrip("abcdefghijklmnopqrstuvwxyz")
    return 3 <= len(body) <= 4 and body.isdigit()


def _citation_token(value: object) -> str:
    """Normalise a citation to its registry token: 'D-274a' / 'D274a' / 'D-274' -> 'D274A' / 'D274'."""
    token = str(value).strip().strip("'\"").split()[0]
    return token.replace("D-", "D").upper()


def _citation_base(value: object) -> str:
    """'D-274a' -> 'D274': a sub-lettered id is a variant of its base decision.

    BUG-498 (2026-09-25): the letter strip used to run AFTER ``.upper()``, where it could never match a
    lowercase letter, so this function's own docstring described a resolution that did not exist
    (declaration <-> mechanism disagreement, BUG-491c class) and a citation of the BASE of a
    sub-lettered decision was reported as "does not exist". Strip-then-normalise makes the sentence
    above true; known-answer controls exercise both directions (cited variant resolves, invented
    variant does not).
    """
    return _citation_token(value).rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _resolves_citation(token: str, known: "set[str]") -> "list[str]":
    """Registry id(s) a citation resolves to: itself, or the sub-lettered variant(s) of the base it names.

    FAIL-CLOSED: an INVENTED variant (D271z) resolves to nothing - the base of a name that does not
    exist cannot be a source for it. One definition of "a citation resolves" for every citation check.
    """
    if token in known:
        return [token]
    return sorted(v for v in known if v != token and _citation_base(v) == token)


def _citation_exemptions() -> set[str]:
    """Declared homonym citations: a key whose NAME is in the citation vocabulary but whose value is not a source.

    D-402/BUG-483: an exemption is a VISIBLE, reasoned act written in config/reconciliation.yaml, never a rename
    that quiets the rail. The list is printed on every run and is shrink-only.
    """
    return {str(x) for x in (((_yaml(CONFIG).get("meta") or {}).get("citation_exemptions")) or [])}


def _walk_keys(node: object):
    """Yield (key, value) for every mapping entry at any depth, so a nested citation is not a blind spot."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k), v
            yield from _walk_keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_keys(v)


def _citations() -> list[tuple[str, str, object]]:
    """Every decision-family value under config/**, EXCEPT the registry itself.

    D-402/BUG-483: this is the EVIDENCE side of the citation check, re-derived from the config files directly.
    Two holes were closed on 2026-09-25: a LIST value was skipped entirely - a silent pass - and a declared
    homonym is skipped only when it is written down in config/reconciliation.yaml#meta.citation_exemptions.
    """
    import yaml
    exempt = _citation_exemptions()
    out: list[tuple[str, str, object]] = []
    for path in sorted((REPO / "config").glob("*.yaml")):
        if path.resolve() == REGISTRY.resolve():
            continue
        rel = path.relative_to(REPO).as_posix()
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for key, val in _walk_keys(doc):
            if key not in CITATION_KEYS or f"{rel}:{key}" in exempt:
                continue
            if isinstance(val, list):
                out.extend((rel, key, v) for v in val if not isinstance(v, (dict, list)))
            else:
                out.append((rel, key, val))
    return out


def check_entry(entry: dict) -> tuple[str, str]:
    """Evaluate one declared entry. Returns (state, evidence): state in ok / drift / owner_owed."""
    kind = entry.get("check")
    about = REPO / str(entry.get("about", ""))
    state = "owner_owed" if entry.get("optional") else "drift"
    found, value = resolve(str(entry.get("declares", "")))

    if kind in ("path_resolves", "consumer_exists"):
        targets = value if isinstance(value, list) else [value]
        # A declared key may resolve to a DOCUMENT (an ownership registry), not a path. Then there is no
        # path-shaped target, so the check falls back to the artifact the entry is ABOUT - and a mapping must
        # never reach the filesystem: `REPO / str(dict)` raised OSError "File name too long", an error leak (C16)
        # that made a declaration defect read as a crash.
        targets = [str(x) for x in targets if isinstance(x, (str, pathlib.Path))]
        if not targets:
            targets = [str(entry.get("about") or "")]
        missing = []
        for t in targets:
            rel = str(t).split("#")[0].strip()
            if not rel or not (REPO / rel).exists():
                missing.append(rel)
        if not found:
            return state, f"declaration {entry['declares']} does not resolve (a declared key must exist)"
        if missing:
            return state, f"declared target(s) do not resolve: {missing}"
        return "ok", f"{len(targets)} declared target(s) resolve"

    if kind == "declared_keys_match_columns":
        declared = sorted(value) if isinstance(value, dict) else []
        suffix = str(entry.get("column_suffix", ""))
        actual = sorted(c for c in _columns(about) if c.endswith(suffix))
        if declared == actual:
            return "ok", f"{len(declared)} declared rater(s) == {len(actual)} column(s) ending {suffix!r}"
        only_d = [k for k in declared if k not in actual]
        only_a = [k for k in actual if k not in declared]
        return state, (f"declared-but-absent {only_d}; present-but-undeclared {only_a} "
                       f"(BUG-476 class: a declaration naming a rater that never rated)")

    if kind == "count_matches":
        actual = _rows(about)
        if actual < 0:
            return state, f"artifact {entry['about']} has no countable records"
        # BUG-501 (2026-09-25): THREE different states shared ONE owner_owed sentence, so a rail pointing at
        # a key nobody ever wrote read as "the rule is not ruled yet". It is not: a declaration that DOES
        # NOT RESOLVE is a BROKEN RAIL - the declaration moved or was renamed and nobody repointed this
        # entry - and no rule can be owed AT a key that does not exist. This is exactly how BUG-466's own
        # ruling stayed invisible: the entry named the PRE-ruling home
        # (config/agreement_floor.yaml#panels.depth_axis_panel.rows_declared), which was never written,
        # while the ruling sat in config/cohort_declaration.yaml and a consumer was already checking it.
        # `optional: true` may downgrade a MISMATCH to a pending ruling; it may never launder a pointer
        # that resolves to nothing.
        if not found:
            return "drift", (f"declaration {entry['declares']} does not resolve - a broken rail is never a "
                             f"pending ruling (found {actual} row(s) at {entry['about']})")
        if not isinstance(value, int) or isinstance(value, bool):
            return "drift", (f"declared count at {entry['declares']} is {type(value).__name__}, not an "
                             f"integer (found {actual} row(s) at {entry['about']})")
        if actual != value:
            return state, f"declared {value} vs found {actual}"
        return "ok", f"declared count == found count ({actual})"

    if kind == "key_present":
        cols = _columns(about)
        col = str(entry.get("column", ""))
        if col in cols:
            return "ok", f"column {col!r} present"
        return state, f"column {col!r} absent from {entry['about']} ({len(cols)} column(s))"

    if kind == "enum_matches":
        actual = _values(about, str(entry.get("column", "")))
        declared = sorted(value) if isinstance(value, list) else []
        if actual == declared:
            return "ok", f"{len(actual)} value(s) match the closed menu"
        return state, f"declared {declared} vs found {actual}"

    if kind == "digest_current":
        if not about.exists():
            return state, f"artifact {entry['about']} does not exist"
        actual = hashlib.sha256(about.read_bytes()).hexdigest()[:16]
        if str(value)[:16] == actual:
            return "ok", f"digest current ({actual})"
        return state, f"declared {str(value)[:16]} vs current {actual} (BUG-468 class)"

    if kind == "decision_exists":
        known, _ = _registry()
        ids = value if isinstance(value, list) else [value]
        bad = [str(i) for i in ids if not _resolves_citation(_citation_token(i), known)]
        if bad:
            return state, (f"cited decision(s) {bad} do not exist in config/decisions.yaml - a provenance "
                           f"stamp naming an undefined decision is a claim, not a source (R14/BUG-483)")
        return "ok", f"{len(ids)} cited decision(s) resolve in the registry"

    if kind == "decision_registry_wellformed":
        known, recs = _registry()
        seen: dict[str, int] = {}
        for r in recs:
            key = str(r.get("id") or "").strip().replace("D-", "D").upper()
            seen[key] = seen.get(key, 0) + 1
        dups = sorted(k for k, v in seen.items() if v > 1)
        legacy = [str(r.get("id")) for r in recs if "status" in r]
        nostate = [str(r.get("id")) for r in recs if not str(r.get("state") or "").strip()]
        missing, unval = [], []
        for rel, key, val in _citations():
            if val is None or not str(val).strip():
                unval.append(f"{rel}:{key}=<blank>")
            elif _id_shaped(val):
                if not _resolves_citation(_citation_token(val), set(seen)):
                    missing.append(f"{rel}:{key}={val}")
            else:
                unval.append(f"{rel}:{key}={str(val)[:30]!r}")
        if dups or nostate or legacy or missing:
            return "drift", (f"registry: {len(dups)} duplicate id(s) {dups}; {len(nostate)} record(s) with no "
                             f"canonical state; {len(legacy)} legacy 'status:' key(s); citations that do not "
                             f"resolve: {missing} (BUG-483)")
        if unval:
            return "owner_owed", (f"{len(unval)} citation value(s) are NOT id-shaped, so no rail can validate "
                                  f"them - name the deciding decision or drop the key: {unval[:6]}")
        ex = sorted(_citation_exemptions())
        if ex:
            return "owner_owed", (f"{len(ex)} declared homonym citation(s) are EXEMPT from id validation - an "
                                  f"exemption is a visible act, not a silent pass: {ex}")
        return "ok", (f"{len(seen)} decision id(s) unique under one namespace; {len(recs)} record(s) carry a "
                      f"canonical state; every citation resolves")

    return "drift", (f"undeclared check kind {kind!r} - a probe this engine cannot evaluate is not a check "
                     f"(it would be a silent pass)")


def _invoked_scripts(text: str) -> set[str]:
    """Every <name>.py token in a command declaration - what this file actually runs."""
    return {m.group(1) for m in re.finditer(r"([A-Za-z0-9_]+\.py)", text)}


def _base(name: str) -> str:
    """The BASENAME of a script reference: a declared edge names a path, the closure holds basenames."""
    return Path(name).name


def _reach_closure(meta: dict) -> tuple[set[str], list[dict]]:
    """Run the reachability closure to a fixed point, then report ONE row per declared edge.

    BUG-486: the edge reader was compared as a PATH ('scripts/drift_monitor.py') against a set that holds
    BASENAMES ('drift_monitor.py'), so the declared edge could NEVER fire. Two check scripts were reported
    uninvoked for a whole session because of a declaration that no reality could join - inside the engine
    built to catch exactly that. Edges are therefore normalised AND counted: an edge that fires zero times
    is a finding, never a silent pass (RC-2 applied to the mechanism itself).
    """
    roots_text = ""
    for rel in (meta.get("roots") or []):
        p = REPO / str(rel)
        if p.exists():
            roots_text += p.read_text(encoding="utf-8")
    reached: set[str] = _invoked_scripts(roots_text)
    decls = list(meta.get("declared_commands") or [])
    while True:
        before = set(reached)
        for decl in decls:
            reader = _base(str(decl.get("reader") or ""))
            if reader and reader not in reached:
                continue
            p = REPO / str(decl.get("file") or "")
            if not p.exists():
                continue
            reached |= _invoked_scripts(p.read_text(encoding="utf-8"))
        if reached == before:
            break
    edges: list[dict] = []
    for decl in decls:
        reader = _base(str(decl.get("reader") or ""))
        rel_file = str(decl.get("file") or "")
        p = REPO / rel_file
        fired, state = 0, "ok"
        if reader and reader not in reached:
            state = "reader_unreached"
        elif not p.exists():
            state = "file_absent"
        else:
            fired = len(_invoked_scripts(p.read_text(encoding="utf-8")))
            if fired == 0:
                state = "fired_nothing"
        edges.append({"file": rel_file, "reader": reader, "fired": fired, "state": state})
    return reached, edges


def reach() -> tuple[list[str], set[str], list[dict]]:
    """Every check script that declares a contract must be REACHABLE from something that runs.

    Reachability is DERIVED as a closure over declared invocation edges (D-402/BUG-482): roots are files
    something actually runs; declared_commands are files that DECLARE invocations, honoured only when the
    declared reader is itself reached. Returns (unwired, reached, edges). The edges list is the
    declaration<->reality join this engine exists to make (D-405), reported on every run.
    """
    meta = (_yaml(CONFIG).get("meta") or {}).get("reach") or {}
    exempt = set(meta.get("exempt") or [])
    reached, edges = _reach_closure(meta)
    unwired = []
    for p in sorted((REPO / "scripts").glob("*.py")):
        if not p.name.startswith(CHECK_SCRIPTS) or p.name in exempt:
            continue
        if p.name not in reached:
            unwired.append(f"scripts/{p.name}")
    return unwired, reached, edges


def cover() -> list[str]:
    """Meta-check: every owned artifact has a reconciliation entry or a declared reason."""
    entries = _yaml(CONFIG).get("entries") or []
    have = {str(e.get("about", "")) for e in entries}
    bad = []
    for name, spec in (_yaml(OWNERSHIP).get("artifacts") or {}).items():
        if name in have or (spec or {}).get("unreconciled_reason"):
            continue
        bad.append(f"{name}: no reconciliation entry and no unreconciled_reason")
    return bad


def resources() -> tuple[list[str], list[str], list[str]]:
    """Join the DECLARED resolution domains (BUG-489) and the DECLARED store floors (BUG-487) to reality.

    A resolution domain is the PREMISE of every finding a rail prints: if the domain is unstated or narrow, a
    join miss is indistinguishable from a fact about the artifact (BUG-488). So the premise is checked like any
    other declaration - the rail exists, every declared store names a READER (BUG-486 class), every declared
    metric is published WITH its domain, and a resolver that publishes no metric says why. Floors are checked in
    the same join because they answer the same question: was anything actually read?
    Returns (drift, owed, rows).
    """
    drift: list[str] = []
    owed: list[str] = []
    rows: list[str] = []
    reg = _yaml(REPO / "config" / "resolution_domains.yaml")
    latest: dict[str, dict] = {}
    journal = REPO / "governance" / "METRICS.jsonl"
    if journal.exists():
        for i, line in enumerate(journal.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                rec = json.loads(line)
                latest[str(rec.get("name"))] = rec
    for res in reg.get("resolvers") or []:
        rid = str(res.get("id"))
        rail = REPO / str(res.get("rail") or "")
        if not rail.exists():
            drift.append("domain " + rid + ": rail " + str(res.get("rail")) + " does not exist - a declared "
                         "resolution domain that nothing implements is a comment")
            continue
        blind = [str(s.get("name")) + " (reader " + str(s.get("reader")) + ")"
                 for s in (res.get("stores") or [])
                 if not str(s.get("reader") or "").split("::")[0] or
                 not (REPO / str(s.get("reader")).split("::")[0]).exists()]
        if blind:
            drift.append("domain " + rid + ": store(s) nothing can read " + str(blind) + " - a store with no "
                         "reader is the BUG-486 class")
        names = [str(m) for m in (res.get("metrics") or [])]
        if not names and not str(res.get("no_metric_reason") or "").strip():
            drift.append("domain " + rid + ": declares no metric and no no_metric_reason - emptiness needs a "
                         "stated reason, not a blank")
        for mname in names:
            rec = latest.get(mname)
            if rec is None:
                owed.append("domain " + rid + ": metric " + mname + " declared but NEVER published by "
                            + str(res.get("rail")))
            elif not rec.get("domain"):
                owed.append("domain " + rid + ": metric " + mname + " published WITHOUT a resolution domain "
                            "(BUG-489) - re-run " + str(res.get("rail")))
        rows.append("domain " + rid + ": " + str(len(names)) + " metric(s), " + str(len(res.get("stores") or []))
                    + " store(s), rail " + ("present" if rail.exists() else "ABSENT"))
    fl = _yaml(REPO / "config" / "evidence_floors.yaml")
    for entry in (fl.get("journals") or []) + (fl.get("stores") or []):
        store = str(entry.get("store"))
        # ONE definition of what counts (BUG-491): the same function the store's own rail calls, so this rail
        # can never print a floor row its enforcer disagrees with (it printed 20 >= 6 while verify_handoffs
        # printed 6 >= 6: the count excluded control fixtures in one home and not in the other).
        f_drift, f_owed, f_rows = floor_check(store)
        drift.extend(f_drift)
        owed.extend(f_owed)
        rows.extend(f_rows)
    return drift, owed, rows


def main() -> int:
    """Evaluate every entry + the two meta-checks, write RECONCILIATION.json, and state the tri-state."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cfg = _yaml(CONFIG)
    results: list[dict] = []
    drift, owed = [], []

    for e in cfg.get("entries") or []:
        state, evidence = check_entry(e)
        results.append({"id": e.get("id"), "state": state, "evidence": evidence, "check": e.get("check"),
                        "about": e.get("about"), "declares": e.get("declares")})
        if state == "drift":
            drift.append(f"{e.get('id')}: {evidence}")

    for bad in cover():
        drift.append(f"cover: {bad}")
        results.append({"id": "cover", "state": "drift", "evidence": bad})

    r_drift, r_owed, r_rows = resources()
    for row in r_rows:
        print("  ok  " + row)
    for d in r_drift:
        drift.append(d)
        results.append({"id": "domain", "state": "drift", "evidence": d})
    for o in r_owed:
        owed.append(o)
        results.append({"id": "domain", "state": "owner_owed", "evidence": o})

    unwired, reached, edges = reach()
    meta = (cfg.get("meta") or {}).get("reach") or {}
    debt_max = int(meta.get("debt_max", 0))
    require_edge_fires = bool(meta.get("require_edge_fires", True))
    dead = [e for e in edges if e["state"] != "ok"]
    state = "drift" if (dead and require_edge_fires) else ("owner_owed" if (unwired or dead) else "ok")
    results.append({"id": "reach", "state": state,
                    "evidence": f"{len(unwired)} uninvoked of {len(reached)} reachable check script(s), "
                                f"{len(edges)} declared edge(s) ({len(dead)} dead), debt_max {debt_max}",
                    "unwired": unwired, "edges": edges})
    if len(unwired) > debt_max:
        drift.append(f"reach: {len(unwired)} uninvoked check script(s) exceeds the declared debt_max "
                     f"{debt_max} - the list is SHRINK-ONLY (BUG-482)")
    elif unwired:
        owed.append(f"reach: {len(unwired)} check script(s) invoked by nothing (debt_max {debt_max}): "
                    + ", ".join(unwired))
    for e in dead:
        msg = (f"reach edge {e['file']} (reader {e['reader']}) is {e['state']}: a declared invocation edge "
               f"that fires nothing joins no declaration to any reality (BUG-486)")
        (drift if require_edge_fires else owed).append(msg)

    # BUG-489: this engine is itself a resolver, so it PUBLISHES its own resolution domain with its coverage.
    dm = declared_resolver_metrics().get("reconcile_objects_agreeing") or {}
    dom = {"identifier": dm.get("identifier"),
           "stores": [str(s.get("name")) for s in (dm.get("stores") or [])],
           "searched": len(results),
           "resolved": len([r for r in results if r.get("state") == "ok"])}
    print("  domain reconcile_entries: " + str(dom["identifier"]) + " resolved against " + str(len(dom["stores"]))
          + " store(s) " + str(dom["stores"]) + " -> " + str(dom["resolved"]) + "/" + str(len(results)))
    emit_metric("reconcile_objects_agreeing", float(dom["resolved"]),
                population="every declared object in config/reconciliation.yaml#entries plus the cover, domain "
                           "and floors meta-checks",
                denominator=len(results), ruler="config/reconciliation.yaml",
                note=str(len(drift)) + " drift, " + str(len(owed)) + " owner-owed", domain=dom)

    # I1 (D-401): the engine's OWN artifact is written through the guard, so governance/MUTATION_JOURNAL.jsonl
    # carries its first receipt. This artifact is DERIVED_REGENERABLE, so the declaration is the whole-file
    # regeneration (OWNED_ANY) - a derived document has no cells to arbitrate, and write_document REFUSES any
    # other ownership set rather than letting "the guard ran" read as "every cell was protected".
    from lib.write_guard import OWNED_ANY, write_document  # noqa: E402 (cycle-safe: write_guard is leaf-ward)
    rep = write_document(OUT, json.dumps({"schema_version": "1.0", "decided": "D-405",
                                          "declaration": "config/reconciliation.yaml", "results": results,
                                          "drift_n": len(drift), "owner_owed_n": len(owed)}, indent=2) + "\n",
                         writer="scripts/reconcile.py", owned_keys={OWNED_ANY})
    print("  ok  reconcile artifact: written through write_guard (OWNED_ANY, derived_regenerable, "
          + rep.pre_sha16 + " -> " + rep.post_sha16 + ") - I1/D-401")

    for r in results:
        print(f"  {r['state']:>10}  {r['id']}: {r['evidence']}")
    if drift:
        print("\nFAIL reconcile: a declaration disagrees with reality (D-405):")
        for d in drift:
            print("  !!", d)
        return 1
    if owed:
        print("\nowner-owed (loud, not fatal - BUG-457):")
        for o in owed:
            print("  ->", o)
        return 2
    print(f"\nok reconcile: {len(results)} declared object(s) agree with reality")
    return 0


if __name__ == "__main__":
    sys.exit(main())
