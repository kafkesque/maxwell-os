#!/usr/bin/env python3
"""pipeline/model_store_census.py - BUG-804's blob-aware store census, corrected for four failures.

FAILURE 1 (BUG-804): a census that walks the engine's serving directory measures SYMLINKS and reports 0 B
for a model that is present. Every entry is resolved to its target, and a REAL directory on the serving
path counts as live too, because the engine serves those.

FAILURE 2 (BUG-807, same hour): a single-instant byte count reported 85 GB in the engine's own store as
reclaimable mass, and the store later read 0 B. The first draft then wrote a CAUSE into the record ("the
engine released it") which was false - the OWNER cleaned it. A census may not narrate a cause it did not
observe, so every store is measured TWICE and flagged TRANSIENT when it moves. A transient store is never
offered as an owner decision.

FAILURE 3 (BUG-838, D-3033): the partition's DOMAIN was the hub DIRECTORY, not the MODEL REPOS it holds.
Measured 2026-10-16: .locks and version.txt - the hub's own machinery - were counted as repos and fell
into ORPHAN, the only class a deletion may ever be proposed from (D-3004(3)); blobs read DECLARED because
the word appears in THIS FILE, so the instrument's own vocabulary acted as a declaration; and the eval
datasets were protected by nothing but an incidental citation in config text, although D-3014(2) says a
dataset is never swept with model bytes. The domain is now DECLARED in
config/engine.yaml#model_store.census_domain and READ here, and an entry of no declared kind is a FAULT
rather than a silent candidate.

FAILURE 4 (BUG-840, T-142/D-3034): DECLARED was a MENTION INDEX. classify() asked whether a repo's stem
appeared ANYWHERE in the joined text of config/, pipeline/ and scripts/, so a GOVERNANCE WRITE moved 267.9 MB
out of ORPHAN with no byte moving on disk: the evidence line this very landing had just added to
config/task_register.yaml named a repo stem, and its own prose then "declared" the bytes. MEASURED 2026-10-16
(temp/t142_probe.py, read-only): the homes that declared the 20-repo DECLARED bucket were dominated by
config/decisions.yaml and config/task_register.yaml - two registers whose strings are SENTENCES. A decision
that mentions a model is a RECORD of a decision, not an owner of bytes. So DECLARED now requires a
RESOLUTION, and there are exactly three forms (D-3018: "the byte-owner test is RESOLUTION, not MENTION"):
an ENGINE ENTRY whose realpath lies inside the repo dir; a VALUE that IS the reference (the full org/name or
the bare name, quoted exactly - a sentence is never equal to a model id); or a PATH that EXISTS and lies
inside the repo dir. A string that merely CONTAINS the reference is recorded as a MENTION: reported, never
ownership. WHAT may declare is itself DECLARED in config/engine.yaml#model_store.resolution_domain, including
THIS file by name - the reader's own vocabulary may not declare a byte (BUG-838 limb 3, generalised).

A second copy of a model is never called redundant by NAME either. When the engine holds the same entry name
twice, the census compares the two FILE INVENTORIES and offers nothing unless they are EQUAL. MEASURED
2026-10-16: Phi-4-mini-instruct-8bit is on disk twice - the hub copy (27 files, 9872601143 B of blobs) and the
copy the engine serves from models_stashed (14 files, 4097978555 B) - and they are NOT the same bytes. The
parked hub copy is therefore the only pristine copy of that fetch, it is NOT redundant, and nothing is offered.

Classification asks four questions, in order, and a MODEL repo that any of them answers stops there: LIVE (the
engine serves it now), PARKED (an engine entry that is not served), DECLARED (a declared home RESOLVES into
it), ORPHAN (none of the three). ORPHAN is the only class a deletion may ever be proposed from (R-D410). The
DECLARED floor (D-3018) then decides whether the decision is owed at all: a candidate at or below
config/engine.yaml#model_store.deletion_floor_bytes is REPORTED and NOT offered, because below it the decision
costs more attention than the bytes.

Exit codes (BUG-457 tri-state): 0 = nothing owed; 1 = a FAULT (an entry of no declared kind, or a declared
value the config does not carry); 2 = bytes only an owner can dispose of.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import sys
import tempfile
import time
from collections.abc import Callable

import yaml

HOME = pathlib.Path(os.path.expanduser("~"))
OMLX = HOME / ".omlx"
SERVING = OMLX / "models"
PARKED = OMLX / "_unloaded"
STASHED = OMLX / "models_stashed"
ENGINE_STORE = OMLX / "cache"
HUB = HOME / ".cache" / "huggingface" / "hub"
ENGINE_YAML = pathlib.Path(__file__).resolve().parent.parent / "config" / "engine.yaml"
ROOT = ENGINE_YAML.parent.parent
SELF = pathlib.Path(__file__).resolve()

KIND_MODEL = "MODEL"
KIND_NON_MODEL_REPO = "NON_MODEL_REPO"
KIND_STORE_METADATA = "STORE_METADATA"
KIND_UNDECLARED = "UNDECLARED"
DOMAIN_KEYS = ("member_prefixes", "non_member_repo_prefixes", "store_metadata")
BUCKETS = ("LIVE", "PARKED", "DECLARED", "ORPHAN")
VERDICT_SHADOW = "SHADOW"

#: The vocabulary of RESOLUTION (T-142). A resolution is evidence that SOMEONE ELSE resolves these bytes; a
#: mention is evidence that someone WROTE the name down. Only the first may confer ownership.
MODE_ENTRY = "engine_entry"
MODE_VALUE = "value"
MODE_PATH = "path"
MODE_CODE = "code"
MODE_MENTION = "mention"
REFERENCE_HOMES_KEY = ("value_homes", "code_homes", "file_suffixes")
FETCHABLE = "FETCHABLE-BY-ID"
LOCAL_ONLY = "LOCAL-ONLY"

RC_OK = 0
RC_FAULT = 1
RC_OWNER_OWED = 2

#: A path-ish run of characters, used to walk LEFT from a directory name to the start of the token that
#: contains it. Bounded on purpose: a run that cannot be cut out of the string is not a path (C16).
PATH_LEFT = re.compile(r"[A-Za-z0-9_~.:/@+-]*$")
PATH_RIGHT = re.compile(r"^[A-Za-z0-9_./@+-]*")


# --- the declared values this instrument reads (C12: never restated here) --------------------------

def _model_store(path: pathlib.Path = ENGINE_YAML) -> dict:
    """The declared model_store block. FATAL when absent - a store rule with no home is a rumour (C12)."""
    if not path.exists():
        raise SystemExit("FATAL: " + str(path) + " is absent - it is the one home for the store rules (C12)")
    row = (yaml.safe_load(path.read_text()) or {}).get("model_store")
    if not isinstance(row, dict) or not row:
        raise SystemExit("FATAL: config/engine.yaml declares no model_store block - refusing to invent one (C12)")
    return row


def census_domain(path: pathlib.Path = ENGINE_YAML) -> dict:
    """WHAT the partition is a partition OF, DECLARED (D-3033/C12) - model repos, non-model repos, machinery.

    A partition whose DOMAIN is unstated silently partitions whatever the directory happens to hold, which is
    how the hub's own .locks and version.txt became ORPHAN 'repos' and how the eval datasets ended up
    protected by a citation (BUG-838). Every list is READ and an absent or empty one is FATAL, because a rule
    with no subject set is green by vacancy (BUG-487).
    """
    row = _model_store(path)
    dom = row.get("census_domain")
    if not isinstance(dom, dict) or not dom:
        raise SystemExit("FATAL: config/engine.yaml#model_store.census_domain is absent - the census would "
                         "partition the hub DIRECTORY instead of the model repos it holds (D-3033)")
    out = {}
    for key in DOMAIN_KEYS:
        val = dom.get(key)
        if not isinstance(val, list) or not val or not all(isinstance(x, str) and x for x in val):
            raise SystemExit("FATAL: config/engine.yaml#model_store.census_domain." + key + " is absent or "
                             "empty - a domain with no declared member is green by vacancy (BUG-487/D-3033)")
        out[key] = list(val)
    return out


def resolution_domain(path: pathlib.Path = ENGINE_YAML) -> dict:
    """WHAT may DECLARE a repo, DECLARED (T-142/D-3034/C12).

    The DECLARED class decides which bytes an owner is told are accounted for, so the rule that confers it is
    read from config rather than remembered: which homes are searched, which suffixes, which file is EXCLUDED
    (the reader's own, BUG-838 limb 3), what marks a fetched-and-therefore-re-fetchable cache entry, and how
    many rows the face prints. FATAL when absent or empty: an instrument that falls back to a mention index is
    the defect this function exists to prevent (BUG-840).
    """
    row = _model_store(path)
    dom = row.get("resolution_domain")
    if not isinstance(dom, dict) or not dom:
        raise SystemExit("FATAL: config/engine.yaml#model_store.resolution_domain is absent - DECLARED would "
                         "fall back to a MENTION index, which reclassified 267.9 MB with no byte moving "
                         "(BUG-840/T-142)")
    out = {}
    for key in REFERENCE_HOMES_KEY:
        val = dom.get(key)
        if not isinstance(val, list) or not val or not all(isinstance(x, str) and x for x in val):
            raise SystemExit("FATAL: config/engine.yaml#model_store.resolution_domain." + key + " is absent or "
                             "empty - a resolution rule with no declared " + key + " is green by vacancy "
                             "(BUG-487)")
        out[key] = list(val)
    exclude = dom.get("exclude")
    if not isinstance(exclude, list) or not exclude or not all(isinstance(x, str) and x for x in exclude):
        raise SystemExit("FATAL: config/engine.yaml#model_store.resolution_domain.exclude is absent or empty - "
                         "a resolution reader whose OWN vocabulary is not excluded declares its own names "
                         "(BUG-838 limb 3)")
    out["exclude"] = list(exclude)
    marker = dom.get("re_acquirable_marker")
    if not isinstance(marker, str) or not marker:
        raise SystemExit("FATAL: config/engine.yaml#model_store.resolution_domain.re_acquirable_marker is "
                         "absent - the audit could not say whether deleted bytes can come back (C12)")
    out["re_acquirable_marker"] = marker
    rows = dom.get("report_rows")
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        raise SystemExit("FATAL: config/engine.yaml#model_store.resolution_domain.report_rows is not a positive "
                         "int - a face that cannot bound its own table is unreadable (C12)")
    out["report_rows"] = rows
    return out


def deletion_floor(path: pathlib.Path = ENGINE_YAML) -> int:
    """The floor below which a candidate is not worth a decision (D-3018). READ, never restated (C12)."""
    row = _model_store(path)
    if "deletion_floor_bytes" not in row:
        raise SystemExit("FATAL: config/engine.yaml#model_store declares no deletion_floor_bytes - refusing "
                         "to invent a floor (C12)")
    floor = int(row["deletion_floor_bytes"])
    if floor <= 0:
        raise SystemExit("FATAL: config/engine.yaml#model_store.deletion_floor_bytes is not positive - a floor "
                         "of 0 would offer every candidate, which is the state the floor exists to end (C12)")
    return floor


def _census_move_ratio(path: pathlib.Path = ENGINE_YAML) -> float:
    """The declared tolerance for 'the census moved' (D-3021). It lived in code until BUG-830 - the second
    copy of a declared value that turned preflight red on 2026-10-15.
    """
    row = _model_store(path)
    if "census_move_ratio" not in row:
        raise SystemExit("FATAL: config/engine.yaml#model_store declares no census_move_ratio - refusing to "
                         "invent a tolerance (C12)")
    return float(row["census_move_ratio"])


MOVE = _census_move_ratio()
FLOOR = deletion_floor()
DOMAIN = census_domain()
RESOLUTION = resolution_domain()
REPORT_ROWS = RESOLUTION["report_rows"]


# --- measurement -----------------------------------------------------------------------------------

def dir_bytes(path: pathlib.Path) -> int:
    """Sum the sizes of real files under path without following symlinks, so a mirror is not counted twice."""
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            p = pathlib.Path(root) / name
            if p.is_symlink():
                continue
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def measure_twice(path: pathlib.Path, gap: float = 1.5,
                  reader: Callable[[pathlib.Path], int] = dir_bytes) -> tuple:
    """Return (bytes, transient). TRANSIENT means the store moved between two readings in one run.

    The reader is injectable so the property can be PROVED by a control rather than asserted: a remedy whose
    control nothing runs is a comment (BUG-492), and BUG-807 was exactly a reading with no covariate.
    """
    first = reader(path)
    time.sleep(gap)
    second = reader(path)
    moved = first != second and abs(first - second) > MOVE * max(first, second, 1)
    return max(first, second), moved


def mb(n: int) -> float:
    """Bytes as megabytes, one decimal place."""
    return round(n / 1e6, 1)


def engine_entries() -> dict:
    """Resolve every entry of the three engine directories to the store it really lives in."""
    out = {}
    for label, directory in (("serving", SERVING), ("parked", PARKED), ("stashed", STASHED)):
        out[label] = {}
        if not directory.is_dir():
            continue
        for entry in sorted(directory.iterdir()):
            try:
                out[label][entry.name] = os.path.realpath(entry)
            except OSError:
                out[label][entry.name] = "UNRESOLVED"
    return out


def pretty(repo: str) -> str:
    """A hub directory name as the owner knows the model."""
    return repo.replace("models--", "").replace("--", "/")


def reference_forms(repo: str) -> tuple:
    """The two forms a DECLARED home may write for this repo: the full id and the bare model name."""
    full = pretty(repo)
    return full, full.split("/")[-1]


def _under(child: str, parent: pathlib.Path) -> bool:
    """True when child lies inside parent on the REAL path, so a symlink cannot claim to live elsewhere."""
    try:
        c, p = os.path.realpath(str(child)), os.path.realpath(str(parent))
    except OSError:
        return False
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def file_inventory(path: pathlib.Path) -> frozenset:
    """Every file under path as (name, size), FOLLOWING symlinks so a hub snapshot and a repacked directory
    can be compared at all. This is the proof that a second copy is redundant - never the name (T-142).
    """
    out = set()
    for root, _dirs, files in os.walk(path, followlinks=True):
        for name in files:
            p = pathlib.Path(root) / name
            try:
                out.add((name, p.stat().st_size))
            except OSError:
                continue
    return frozenset(out)


# --- the declared domain decides membership, BEFORE any name is looked for ------------------------

def entry_kind(name: str, domain: dict) -> str:
    """The KIND a hub entry has, decided ONLY by the declared rule (D-3033/C12).

    KIND precedes mention. .locks is the hub's machinery whether or not some file spells the word, and blobs
    is the blob store even though THIS FILE spells it. A name that matches no declared kind - or more than
    one, which is an ambiguity rather than a coin flip - is UNDECLARED: a fault, never a silent candidate.
    """
    kinds = set()
    if name in domain["store_metadata"]:
        kinds.add(KIND_STORE_METADATA)
    for prefix in domain["member_prefixes"]:
        if name.startswith(prefix):
            kinds.add(KIND_MODEL)
    for prefix in domain["non_member_repo_prefixes"]:
        if name.startswith(prefix):
            kinds.add(KIND_NON_MODEL_REPO)
    return kinds.pop() if len(kinds) == 1 else KIND_UNDECLARED


def hub_entries(domain: dict) -> dict:
    """Every entry of the hub root with its declared kind - nothing is skipped in silence (D-3004(4))."""
    out = {}
    if not HUB.is_dir():
        return out
    for entry in sorted(HUB.iterdir()):
        out[entry.name] = entry_kind(entry.name, domain)
    return out


def entry_bytes(entry: pathlib.Path) -> int:
    """One hub entry's bytes, measured on blobs/ when it has one because snapshots are symlinks into it."""
    blobs = entry / "blobs"
    return dir_bytes(blobs if blobs.is_dir() else entry)


def hub_bytes_by_entry(kinds: dict) -> dict:
    """Bytes for EVERY hub entry - the hub total, which is the number a deletion is proved to have moved."""
    return {name: entry_bytes(HUB / name) for name in kinds}


def model_repos(measured: dict, kinds: dict) -> dict:
    """The MODEL repos only. This is the partition's domain: a non-model repo never reaches a bucket."""
    return {name: measured[name] for name in measured if kinds[name] == KIND_MODEL}


# --- RESOLUTION: what may declare a repo, indexed ONCE (T-142/D-3034) -------------------------------

def _reference_files(homes: list, suffixes: list, exclude: list) -> list:
    """Every candidate file in the declared homes, minus the declared exclusions (the reader's own file)."""
    out = []
    for home in homes:
        base = pathlib.Path(home)
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            rel = path.relative_to(ROOT).as_posix() if str(path).startswith(str(ROOT)) else path.as_posix()
            if any(rel == x or rel.startswith(x.rstrip("/") + "/") for x in exclude):
                continue
            out.append(path)
    return out


def _leaves(node, path: list, out: list) -> None:
    """Every STRING leaf of a PARSED document with its key path. A comment is not a value, and this reader
    never sees one: that is half of what makes a value a declaration and a comment a remark (T-142).
    """
    if isinstance(node, dict):
        for key, val in node.items():
            _leaves(val, path + [str(key)], out)
    elif isinstance(node, list):
        for index, val in enumerate(node):
            _leaves(val, path + ["[" + str(index) + "]"], out)
    elif isinstance(node, str):
        out.append((".".join(path), node))


def _docstrings(tree) -> set:
    """The docstring texts of a module, so a sentence in prose is not read as a code constant (T-142)."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            text = ast.get_docstring(node, clean=False)
            if text is not None:
                found.add(text)
    return found


def resolution_index(dom: dict = None) -> dict:
    """Index every declared home ONCE: parsed VALUES by key path, and CODE constants by line.

    Two things are deliberately NOT read. A comment, because a parsed document has none. A docstring, because
    prose explaining a model is not a consumer of it. A file the declared domain excludes is skipped here, and
    the exclusion is DECLARED rather than remembered, so the reader can never declare its own vocabulary.
    """
    dom = RESOLUTION if dom is None else dom
    values, code, unreadable = [], [], []
    for path in _reference_files(dom["value_homes"], dom["file_suffixes"], dom["exclude"]):
        try:
            doc = yaml.safe_load(path.read_text(errors="ignore"))
        except yaml.YAMLError as exc:
            unreadable.append((path.as_posix(), "YAML: " + str(exc).splitlines()[0]))
            continue
        leaves = []
        _leaves(doc, [], leaves)
        rel = path.relative_to(ROOT).as_posix() if str(path).startswith(str(ROOT)) else path.as_posix()
        values.extend((rel, key_path, value) for key_path, value in leaves)
    for path in _reference_files(dom["code_homes"], dom["file_suffixes"], dom["exclude"]):
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except SyntaxError as exc:
            unreadable.append((path.as_posix(), "Python: " + str(exc).splitlines()[0]))
            continue
        skip = _docstrings(tree)
        rel = path.relative_to(ROOT).as_posix() if str(path).startswith(str(ROOT)) else path.as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value not in skip:
                code.append((rel, node.lineno, node.value))
    return {"values": values, "code": code, "unreadable": unreadable}


def _norm(value: str) -> str:
    """A value stripped of the quoting a declared home wraps it in, so 'x' and x compare equal."""
    return str(value).strip().strip("'").strip('"').strip()


def names_reference(value: str, full: str, bare: str) -> bool:
    """True when the value IS the reference - the whole value, not a piece of a sentence (T-142).

    The full id and the bare name are both accepted, because this system writes both (MEASURED: stage5.nli_model
    carries the org, stage4's arm keys carry the bare name). A value that carries an ORG must carry THIS one:
    otherwise other-org/clef-4bit would declare mlx-community's bytes.
    """
    text = _norm(value)
    if not text:
        return False
    if text == full:
        return True
    if "/" in text:
        return False
    return text == bare


def mentions_reference(value: str, full: str, bare: str) -> bool:
    """True when the value CONTAINS a reference. This is the old DECLARED test, demoted to EVIDENCE."""
    text = _norm(value)
    return bool(text) and (full in text or (len(bare) > 3 and bare in text))


def resolving_paths(text: str, repo: str, exists: Callable = None) -> list:
    """Every path in the string that EXISTS and lies inside this repo dir - the strongest local claim (T-142).

    A path is cut out of the string by walking left and right along path characters from the hub directory
    name. A path that does not resolve is NOT a claim: a citation whose subject is absent is an assertion
    (D-405), and the negative direction is a control.
    """
    exists = os.path.exists if exists is None else exists
    found = []
    start = 0
    while True:
        index = text.find(repo, start)
        if index < 0:
            break
        left = PATH_LEFT.search(text[:index])
        right = PATH_RIGHT.match(text[index + len(repo):])
        candidate = text[(left.start() if left else index):index + len(repo) + (right.end() if right else 0)]
        start = index + len(repo)
        if not candidate.startswith(("~", "/", ".")):
            continue
        expanded = os.path.expanduser(candidate)
        if ".." in expanded:
            continue
        if exists(expanded) and _under(expanded, HUB / repo):
            found.append(candidate)
    return found


def resolve(repo: str, index: dict, exists: Callable = None) -> dict:
    """Does a DECLARED thing RESOLVE INTO these bytes? Returns resolution evidence and mention evidence.

    This is the whole of T-142. The old test asked whether a name was WRITTEN DOWN anywhere; this one asks
    who would BREAK if the bytes went away.
    """
    full, bare = reference_forms(repo)
    out = {"resolution": [], "mentions": []}
    for home, key_path, value in index.get("values", []):
        if names_reference(value, full, bare):
            out["resolution"].append(MODE_VALUE + ":" + home + "#" + key_path)
            continue
        for path in resolving_paths(value, repo, exists):
            out["resolution"].append(MODE_PATH + ":" + home + "#" + key_path + " -> " + path)
        if mentions_reference(value, full, bare):
            out["mentions"].append(home + "#" + key_path)
    for home, line, value in index.get("code", []):
        if names_reference(value, full, bare):
            out["resolution"].append(MODE_CODE + ":" + home + ":" + str(line))
            continue
        for path in resolving_paths(value, repo, exists):
            out["resolution"].append(MODE_PATH + ":" + home + ":" + str(line) + " -> " + path)
        if mentions_reference(value, full, bare):
            out["mentions"].append(home + ":" + str(line))
    out["resolution"] = sorted(set(out["resolution"]))[:REPORT_ROWS]
    mentions = sorted(set(out["mentions"]))
    out["mentions"] = mentions[:REPORT_ROWS]
    out["n_mentions"] = len(mentions)
    return out


def engine_owners(repo: str, entries: dict) -> list:
    """The engine entries whose target really lies inside this repo dir (a namesake elsewhere is not one)."""
    return sorted(name for named in entries.values() for name, target in named.items()
                  if _under(target, HUB / repo))


def serving_owners(repo: str, entries: dict) -> list:
    """The owners that are SERVED: the serving store holds the NAME and its TARGET lies inside these bytes.

    Deciding LIVE by the name alone is BUG-841: MEASURED 2026-10-16, the hub holds 5.77 GB of
    Phi-4-mini-instruct-8bit and the engine serves that name from ~/.omlx/models_stashed, so a name test called
    the cache copy LIVE while the bytes it measures are the parked one. LIVE is a claim about THESE bytes, and
    a claim needs its own subject: the serving entry must resolve into them.
    """
    out = []
    for name in engine_owners(repo, entries):
        target = entries.get("serving", {}).get(name)
        if target and _under(target, HUB / repo):
            out.append(name)
    return out


def same_name_copy(repo: str, entries: dict, inventory: Callable = None) -> dict:
    """A copy of this model, under the SAME entry name, that the engine serves from somewhere else.

    A name collision is not redundancy. same_weights is the proof and the only thing that may promote this to
    an offer: MEASURED 2026-10-16, Phi-4-mini-instruct-8bit is on disk twice with DIFFERENT inventories
    (27 files / 9872601143 B beside 14 files / 4097978555 B), so the hub copy is the only pristine copy of
    that fetch and NO offer is made for it. Without this limb the census would have proposed deleting a
    unique fetch because a name was repeated (T-142).
    """
    inventory = file_inventory if inventory is None else inventory
    bare = reference_forms(repo)[1]
    for name, served_from in entries.get("serving", {}).items():
        if name != bare:
            continue
        for store in ("parked", "stashed"):
            held = entries.get(store, {}).get(name)
            if not held or not _under(held, HUB / repo):
                continue
            try:
                same = inventory(pathlib.Path(held)) == inventory(pathlib.Path(served_from))
            except OSError:
                same = False
            return {"entry": name, "served_from": served_from, "second_copy_at": held, "same_weights": same,
                    "redundant": same}
    return {}


def re_acquirability(repo: str, dom: dict = None) -> str:
    """Can these bytes come back if they go? A cache entry that carries the declared marker was FETCHED by
    repo id, so it can be fetched again; anything else is local-only and a deletion would be final (T-142).
    """
    dom = RESOLUTION if dom is None else dom
    return FETCHABLE if (HUB / repo / dom["re_acquirable_marker"]).exists() else LOCAL_ONLY


def classify(repos: dict, entries: dict, index: dict, exists: Callable = None,
             inventory: Callable = None) -> tuple:
    """LIVE / PARKED / DECLARED / ORPHAN plus the per-repo audit - and only a RESOLUTION may confer the third.

    The first question that answers wins, so ORPHAN stays conservative: an engine entry outranks any string,
    and a declaration that does not resolve leaves the repo a candidate rather than hiding it.
    """
    buckets = {key: [] for key in BUCKETS}
    audit = {}
    for repo in repos:
        owners = engine_owners(repo, entries)
        resolutions = sorted(MODE_ENTRY + ":" + name for name in owners)
        served = serving_owners(repo, entries)
        copy_notes = same_name_copy(repo, entries, inventory)
        hits = resolve(repo, index, exists)
        audit[repo] = {
            "bytes": mb(repos[repo]),
            "engine_entries": owners,
            "resolution": resolutions + hits["resolution"],
            "mentions": hits["mentions"],
            "n_mentions": hits["n_mentions"],
            "re_acquirable": re_acquirability(repo),
        }
        if copy_notes:
            audit[repo]["same_name_served_elsewhere"] = copy_notes
        if served:
            verdict = "LIVE"
        elif resolutions:
            verdict = VERDICT_SHADOW if copy_notes.get("redundant") else "PARKED"
        elif hits["resolution"]:
            verdict = "DECLARED"
        else:
            verdict = "ORPHAN"
        audit[repo]["verdict"] = verdict
        buckets[verdict if verdict in BUCKETS else "PARKED"].append(repo)
    return buckets, audit


def owner_owed(candidates: list, repos: dict, floor: int) -> tuple:
    """Split the ORPHAN class by the DECLARED floor (D-3018): only a candidate ABOVE it is a decision owed.

    The floor exists so no mention-based sweep may reach a model a live code DEFAULT resolves into, and so the
    owner is never asked to spend attention on bytes that cost less than the question.
    """
    above = sorted([r for r in candidates if repos.get(r, 0) > floor], key=lambda r: -repos.get(r, 0))
    below = sorted([r for r in candidates if repos.get(r, 0) <= floor], key=lambda r: -repos.get(r, 0))
    return above, below


def exit_code(undeclared: list, above: list) -> int:
    """The tri-state contract (BUG-457): a FAULT outranks an owner-owed set, and neither is silent."""
    if undeclared:
        return RC_FAULT
    if above:
        return RC_OWNER_OWED
    return RC_OK


def broken_entries() -> list:
    """Engine entries whose target is ABSENT: a name that reads as 'on disk' and is not (BUG-808)."""
    out = []
    for directory in (SERVING, PARKED, STASHED):
        if not directory.is_dir():
            continue
        for entry in sorted(directory.iterdir()):
            if not entry.exists():
                out.append(entry.name)
    return out


# --- the run ---------------------------------------------------------------------------------------

def build_report(domain, floor, kinds, measured, repos, entries, buckets, audit, engine_bytes,
                 engine_transient, broken, above, below, when) -> dict:
    """The face this instrument PRINTS and (with --json-out) WRITES. Every number here was observed (D-3004(4))."""
    return {
        "schema_version": "1",
        "measured_at": when,
        "census_domain": domain,
        "resolution_domain": RESOLUTION,
        "deletion_floor_bytes": floor,
        "buckets": {key: {"n": len(val), "bytes": mb(sum(repos[r] for r in val))} for key, val in buckets.items()},
        "live": sorted(buckets["LIVE"]),
        "parked": sorted(buckets["PARKED"]),
        "orphans": sorted(buckets["ORPHAN"], key=lambda r: -repos[r]),
        "declared": sorted(buckets["DECLARED"], key=lambda r: -repos[r]),
        "owner_owed_above_floor": above,
        "below_floor_not_offered": below,
        "byte_owner_audit": dict(sorted(audit.items(), key=lambda kv: -kv[1]["bytes"])),
        "not_a_candidate_non_model_repo": {n: mb(measured[n]) for n in sorted(kinds)
                                           if kinds[n] == KIND_NON_MODEL_REPO},
        "not_a_candidate_store_metadata": {n: mb(measured[n]) for n in sorted(kinds)
                                           if kinds[n] == KIND_STORE_METADATA},
        "undeclared_entries": sorted(n for n in kinds if kinds[n] == KIND_UNDECLARED),
        "broken_entries": broken,
        "engine_store": {
            "bytes": mb(engine_bytes),
            "transient": engine_transient,
            "note": "not on the serving path; measured twice because a single reading reported 85 GB that the "
                    "owner then cleaned (BUG-807)",
        },
        "hub_bytes": mb(sum(measured.values())),
        "model_repo_bytes": mb(sum(repos.values())),
        "engine_entries": entries,
        "hub_repos": {key: mb(val) for key, val in sorted(repos.items(), key=lambda kv: -kv[1])},
    }


def print_audit(audit: dict, repos: dict) -> None:
    """The audit T-142 asks for: per repo, what DECLARES it, its bytes, and whether it can come back."""
    rows = [r for r in sorted(repos, key=lambda r: -repos[r]) if audit[r]["verdict"] in ("DECLARED", "ORPHAN")]
    resolved = sum(1 for r in rows if audit[r]["resolution"])
    by_value = sum(1 for r in rows if any(e.startswith(MODE_VALUE) for e in audit[r]["resolution"]))
    by_path = sum(1 for r in rows if any(e.startswith(MODE_PATH) for e in audit[r]["resolution"]))
    by_code = sum(1 for r in rows if any(e.startswith(MODE_CODE) for e in audit[r]["resolution"]))
    print("  BYTE-OWNER AUDIT (T-142/D-3034) - what DECLARES each non-live repo, and can the bytes come back:")
    print(f"    resolved by a declared home: {resolved} repo(s); mention-only: {len(rows) - resolved} repo(s)")
    print(f"    the resolution was by value in {by_value}, by path in {by_path}, by code constant in {by_code} "
          f"(a repo may be resolved more than once, so these do not sum to {resolved})")
    for repo in rows[:REPORT_ROWS]:
        row = audit[repo]
        why = row["resolution"][0] if row["resolution"] else (
            "NO RESOLUTION - " + str(row["n_mentions"]) + " mention(s), e.g. "
            + (row["mentions"][0] if row["mentions"] else "none"))
        print(f"    {pretty(repo):<56} {mb(repos[repo]):8.1f} MB {row['verdict']:<9} "
              f"{row['re_acquirable']:<16} {why[:110]}")
    if len(rows) > REPORT_ROWS:
        print(f"    ... and {len(rows) - REPORT_ROWS} more row(s) in the face (report_rows = {REPORT_ROWS})")
    for repo in sorted(audit):
        note = audit[repo].get("same_name_served_elsewhere")
        if note and not note["redundant"]:
            print(f"    SAME NAME, DIFFERENT BYTES - {pretty(repo)}: the engine serves {note['entry']!r} from "
                  f"{str(note['served_from']).replace(str(HOME), '~')} while "
                  f"{str(note['second_copy_at']).replace(str(HOME), '~')} holds a SECOND fetch; the inventories "
                  f"differ, so NOTHING is offered (T-142)")


def main(argv: list) -> int:
    """Measure every store, classify every MODEL repo, and report only what an owner must decide."""
    domain, floor = DOMAIN, FLOOR
    kinds = hub_entries(domain)
    measured = hub_bytes_by_entry(kinds)
    repos = model_repos(measured, kinds)
    undeclared = sorted(n for n in kinds if kinds[n] == KIND_UNDECLARED)
    entries = engine_entries()
    index = resolution_index()
    buckets, audit = classify(repos, entries, index)
    engine_bytes, engine_transient = measure_twice(ENGINE_STORE)
    broken = broken_entries()
    above, below = owner_owed(buckets["ORPHAN"], repos, floor)
    shadow_offers = sorted([r for r in repos if audit[r]["verdict"] == VERDICT_SHADOW and repos[r] > floor],
                           key=lambda r: -repos[r])
    when = time.strftime("%Y-%m-%dT%H:%M:%S")
    report = build_report(domain, floor, kinds, measured, repos, entries, buckets, audit, engine_bytes,
                          engine_transient, broken, above, below, when)

    print("STORE CENSUS (BUG-804 remedy, MEASURED, two readings per store)")
    print(f"  engine store (~/.omlx/cache): {mb(engine_bytes):8.1f} MB  transient={engine_transient}")
    print("  hub total:                   %8.1f MB" % mb(sum(measured.values())))
    print(f"  of which model repos:        {mb(sum(repos.values())):8.1f} MB  ({len(repos)} repo(s) - the partition's domain, D-3033)")
    for bucket in BUCKETS:
        counts = report["buckets"][bucket]
        print("  %-8s %2d repo(s)  %9.1f MB" % (bucket, counts["n"], counts["bytes"]))
    print("  LIVE:   %s" % ", ".join(pretty(r) for r in report["live"]))
    print("  PARKED: %s" % ", ".join(pretty(r) for r in report["parked"]))
    non_model = report["not_a_candidate_non_model_repo"]
    machinery = report["not_a_candidate_store_metadata"]
    print(f"  NOT A CANDIDATE - non-model repos (a dataset is never swept with model bytes, D-3014(2)): {len(non_model)}")
    for name in sorted(non_model):
        print(f"    {name:<62} {non_model[name]:9.1f} MB")
    print(f"  NOT A CANDIDATE - store machinery (not a repo at all, never counted, never swept): {len(machinery)}")
    for name in sorted(machinery):
        print(f"    {name:<62} {machinery[name]:9.1f} MB")
    print("  BROKEN entries (an engine name whose target is ABSENT - BUG-808): %s" % (", ".join(broken) or "none"))
    print_audit(audit, repos)
    print(f"  DELETION FLOOR (D-3018): {floor / 2 ** 20:.1f} MiB per repo - at or below it a candidate is NOT offered")
    print("  ORPHAN ranking (a proposal, never an act - R-D410):")
    for repo in report["orphans"][:REPORT_ROWS]:
        mark = "OFFERED" if repo in above else "below floor"
        print(f"    {repo:<62} {mb(repos[repo]):9.1f} MB  {mark}")
    owed = sorted(set(above) | set(shadow_offers), key=lambda r: -repos[r])
    print(f"  OWNER-OWED (a candidate ABOVE the floor, or a PROVED redundant copy): {len(owed)} repo(s), "
          f"{mb(sum(repos[r] for r in owed)):.1f} MB")
    if undeclared:
        print(f"  FAULT: {len(undeclared)} hub entr(ies) match NO declared kind - declare it in "
              f"config/engine.yaml#model_store.census_domain (D-3033): {', '.join(undeclared)}")
    out = None
    for position, arg in enumerate(argv):
        if arg == "--json-out" and position + 1 < len(argv):
            out = pathlib.Path(argv[position + 1])
    if out:
        out.write_text(json.dumps(report, indent=1, sort_keys=True))
        print("wrote %s" % out)
    return exit_code(undeclared, owed)


# --- the controls ----------------------------------------------------------------------------------

CONTROL_DOMAIN = {
    "member_prefixes": ["models--"],
    "non_member_repo_prefixes": ["datasets--", "spaces--"],
    "store_metadata": [".locks", "version.txt", "CACHEDIR.TAG", "blobs"],
}

CONTROL_MODEL = "models--mlx-community--clef-4bit"
CONTROL_LAYA = "models--convaiinnovations--laya"
CONTROL_SNAPSHOT = "~/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/7b928d"


def _yaml_with(text: str) -> pathlib.Path:
    """A synthetic engine.yaml holding exactly this text, for the fail-closed controls."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    handle.write(text)
    handle.close()
    return pathlib.Path(handle.name)


def _raises(fn) -> bool:
    """True when fn refuses. A fail-closed rule that cannot be SEEN to refuse is not a control (C16)."""
    try:
        fn()
    except SystemExit:
        return True
    return False


def _one_value(value: str, key_path: str = "k", home: str = "config/example.yaml") -> dict:
    """An index holding exactly one declared VALUE - so a control tests the rule, not the machine's config."""
    return {"values": [(home, key_path, value)], "code": []}


def _cases() -> list:
    """Every known-answer control, as (name, predicate). Each must FIRE (BUG-492)."""
    no_domain = _yaml_with("model_store:\n  deletion_floor_bytes: 1\n")
    no_floor = _yaml_with("model_store:\n  census_domain:\n    member_prefixes: [models--]\n"
                          "    non_member_repo_prefixes: [datasets--]\n    store_metadata: [.locks]\n")
    empty_domain = _yaml_with("model_store:\n  deletion_floor_bytes: 1\n  census_domain:\n"
                              "    member_prefixes: []\n    non_member_repo_prefixes: [datasets--]\n"
                              "    store_metadata: [.locks]\n")
    zero_floor = _yaml_with("model_store:\n  deletion_floor_bytes: 0\n")
    no_resolution = _yaml_with("model_store:\n  deletion_floor_bytes: 1\n  census_domain:\n"
                               "    member_prefixes: [models--]\n    non_member_repo_prefixes: [datasets--]\n"
                               "    store_metadata: [.locks]\n")
    empty_exclude = _yaml_with("model_store:\n  deletion_floor_bytes: 1\n  resolution_domain:\n"
                               "    value_homes: [config]\n    code_homes: [pipeline]\n"
                               "    file_suffixes: [.yaml]\n    exclude: []\n"
                               "    re_acquirable_marker: refs\n    report_rows: 12\n")
    readings = {"n": 0}

    def reader_moves(_path):
        readings["n"] += 1
        return 100 if readings["n"] == 1 else 200

    def reader_still(_path):
        return 100

    source = pathlib.Path(__file__).read_text()
    kinds = {".locks": KIND_STORE_METADATA, "version.txt": KIND_STORE_METADATA, "blobs": KIND_STORE_METADATA,
             "datasets--TIGER-Lab--MMLU-Pro": KIND_NON_MODEL_REPO, "models--a--b": KIND_MODEL}

    def members() -> dict:
        """The partition's domain when the hub holds one model repo beside a dataset and the hub's machinery."""
        return model_repos({k: 1 for k in kinds}, kinds)

    def orphans() -> set:
        """The candidate class those members produce - the only class a deletion may be proposed from."""
        return set(classify(members(), {}, {"values": [], "code": []})[0]["ORPHAN"])

    real_index = resolution_index()
    hub_snapshot = str(HUB / CONTROL_MODEL / "snapshots" / "abc")
    same_bytes = lambda _path: frozenset({("model.safetensors", 100)})
    different_bytes = lambda path: (frozenset({("model.safetensors", 100)}) if "snapshots" in str(path)
                                    else frozenset({("model.safetensors", 200)}))

    def two_names() -> dict:
        """The engine holding ONE entry name twice: served from a real dir, parked inside the hub repo."""
        return {"serving": {"clef-4bit": "/served/clef-4bit"}, "parked": {"clef-4bit": hub_snapshot}, "stashed": {}}

    def shadow(inventory) -> dict:
        """The audit row for a hub repo whose entry name is also served from somewhere else."""
        return classify({CONTROL_MODEL: 1}, two_names(), {"values": [], "code": []}, inventory=inventory)[1][CONTROL_MODEL]

    return [
        ("a_dataset_and_the_store_machinery_can_never_be_ORPHAN",
         lambda: members() == {"models--a--b": 1} and orphans() == {"models--a--b"}),
        ("store_machinery_is_never_counted_as_a_repo",
         lambda: all(entry_kind(n, CONTROL_DOMAIN) == KIND_STORE_METADATA for n in (".locks", "version.txt"))),
        ("the_hub_blob_root_is_not_a_model_even_though_THIS_FILE_spells_it",
         lambda: "blobs" in source and entry_kind("blobs", CONTROL_DOMAIN) == KIND_STORE_METADATA),
        ("an_entry_of_no_declared_kind_is_a_FAULT_not_a_silent_ORPHAN",
         lambda: entry_kind("something-new", CONTROL_DOMAIN) == KIND_UNDECLARED
         and exit_code(["something-new"], []) == RC_FAULT),
        ("an_AMBIGUOUS_entry_is_a_FAULT_rather_than_a_coin_flip",
         lambda: entry_kind("models--x", {**CONTROL_DOMAIN, "store_metadata": ["models--x"]}) == KIND_UNDECLARED),
        ("a_candidate_at_or_below_the_floor_is_REPORTED_but_NOT_owed",
         lambda: owner_owed(["r"], {"r": FLOOR}, FLOOR) == ([], ["r"])
         and owner_owed(["r"], {"r": FLOOR - 1}, FLOOR) == ([], ["r"])),
        ("a_candidate_above_the_floor_IS_owed_so_the_rule_can_fire",
         lambda: owner_owed(["r"], {"r": FLOOR + 1}, FLOOR) == (["r"], []) and exit_code([], ["r"]) == RC_OWNER_OWED),
        ("an_ORDINARY_run_owes_nothing",
         lambda: exit_code([], []) == RC_OK),
        ("an_absent_census_domain_is_FATAL",
         lambda: _raises(lambda: census_domain(no_domain))),
        ("an_EMPTY_census_domain_is_FATAL_green_by_vacancy",
         lambda: _raises(lambda: census_domain(empty_domain))),
        ("an_absent_deletion_floor_is_FATAL",
         lambda: _raises(lambda: deletion_floor(no_floor))),
        ("a_non_positive_deletion_floor_is_FATAL",
         lambda: _raises(lambda: deletion_floor(zero_floor))),
        ("a_MOVING_store_reads_TRANSIENT_and_a_still_one_does_not",
         lambda: measure_twice(pathlib.Path("."), gap=0, reader=reader_moves)[1] is True
         and measure_twice(pathlib.Path("."), gap=0, reader=reader_still)[1] is False),
        ("an_absent_resolution_domain_is_FATAL",
         lambda: _raises(lambda: resolution_domain(no_resolution))),
        ("an_EMPTY_exclude_list_is_FATAL_because_the_reader_would_declare_itself",
         lambda: _raises(lambda: resolution_domain(empty_exclude))),
        ("a_SENTENCE_that_mentions_a_model_does_NOT_declare_it",
         lambda: resolve(CONTROL_MODEL, _one_value(
             "clef-4bit was adopted as the emerging-classifier arm and 8.8 GB of its bytes stayed on disk"))
         == {"resolution": [], "mentions": ["config/example.yaml#k"], "n_mentions": 1}),
        ("a_value_that_IS_the_reference_DOES_declare_it_full_id_and_bare_name",
         lambda: resolve(CONTROL_MODEL, _one_value("mlx-community/clef-4bit"))["resolution"]
         == ["value:config/example.yaml#k"]
         and resolve(CONTROL_MODEL, _one_value("clef-4bit"))["resolution"] == ["value:config/example.yaml#k"]),
        ("a_bare_name_belonging_to_ANOTHER_org_does_not_declare_THESE_bytes_but_is_still_a_mention",
         lambda: resolve(CONTROL_MODEL, _one_value("other-org/clef-4bit"))["resolution"] == []
         and resolve(CONTROL_MODEL, _one_value("other-org/clef-4bit"))["mentions"] == ["config/example.yaml#k"]),
        ("a_PATH_that_RESOLVES_inside_the_repo_declares_it_and_one_that_does_NOT_does_not",
         lambda: resolve(CONTROL_LAYA, _one_value(CONTROL_SNAPSHOT, "provenance.snapshot_path"),
                         exists=lambda p: str(p).endswith("snapshots/7b928d"))["resolution"]
         == ["path:config/example.yaml#provenance.snapshot_path -> " + CONTROL_SNAPSHOT]
         and resolve(CONTROL_LAYA, _one_value(CONTROL_SNAPSHOT),
                     exists=lambda p: False)["resolution"] == []),
        ("the_INSTRUMENT_own_vocabulary_cannot_declare_a_repo",
         lambda: SELF.relative_to(ROOT).as_posix() in RESOLUTION["exclude"]
         and all("model_store_census.py" not in home for home, _key, _val in real_index["values"])
         and all("model_store_census.py" not in home for home, _line, _val in real_index["code"])),
        ("a_declared_home_that_is_ABSENT_contributes_no_reference_in_silence",
         lambda: resolution_index({"value_homes": ["no/such/home"], "code_homes": ["no/such/home"],
                                   "file_suffixes": [".yaml"], "exclude": ["pipeline/model_store_census.py"],
                                   "re_acquirable_marker": "refs", "report_rows": 12})
         == {"values": [], "code": [], "unreadable": []}),
        ("a_same_name_copy_IS_redundant_when_the_inventories_are_EQUAL",
         lambda: shadow(same_bytes)["verdict"] == VERDICT_SHADOW
         and shadow(same_bytes)["same_name_served_elsewhere"]["redundant"] is True),
        ("a_same_name_copy_with_DIFFERENT_bytes_is_PARKED_and_NOT_offered",
         lambda: shadow(different_bytes)["verdict"] == "PARKED"
         and shadow(different_bytes)["same_name_served_elsewhere"]["redundant"] is False),
        ("an_engine_entry_in_ANOTHER_repo_does_not_claim_this_one",
         lambda: engine_owners(CONTROL_MODEL, {"serving": {"x": str(HUB / "models--mlx-community--clef-4bitX")},
                                               "parked": {}, "stashed": {}}) == []),
    ]


def selftest() -> int:
    """Run every known-answer control and print the count. No store is touched and no config is written."""
    failures = 0
    cases = _cases()
    for name, predicate in cases:
        try:
            ok = bool(predicate())
        except Exception as exc:  # noqa: BLE001 - a control that raises IS a failed control, and it is named
            ok, name = False, name + " (raised " + type(exc).__name__ + ": " + str(exc) + ")"
        print(("  ok   " if ok else "  FAIL ") + name)
        failures += 0 if ok else 1
    print(f"model-store-census: {len(cases) - failures}/{len(cases)} known-answer control(s) fire")
    return RC_FAULT if failures else RC_OK


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main(sys.argv[1:]))
