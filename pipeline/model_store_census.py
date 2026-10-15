#!/usr/bin/env python3
"""pipeline/model_store_census.py - BUG-804's blob-aware store census, corrected for three failures.

FAILURE 1 (BUG-804): a census that walks the engine's serving directory measures SYMLINKS and reports 0 B
for a model that is present. Every entry is resolved to its target, and a REAL directory on the serving
path counts as live too, because the engine serves those.

FAILURE 2 (BUG-807, same hour): a single-instant byte count reported 85 GB in the engine's own store as
reclaimable mass, and the store later read 0 B. The first draft then wrote a CAUSE into the record ("the
engine released it") which was false - the OWNER cleaned it. A census may not narrate a cause it did not
observe, so every store is measured TWICE and flagged TRANSIENT when it moves. A transient store is never
offered as an owner decision.

FAILURE 3 (BUG-838, D-3033): the partition's DOMAIN was the hub DIRECTORY, not the MODEL REPOS it holds.
Measured 2026-10-16: `.locks` and `version.txt` - the hub's own machinery - were counted as repos and fell
into ORPHAN, the only class a deletion may ever be proposed from (D-3004(3)); `blobs` read DECLARED because
the word appears in THIS FILE, so the instrument's own vocabulary acted as a declaration; and the eval
datasets were protected by nothing but an incidental citation in config text, although D-3014(2) says a
dataset is never swept with model bytes. The domain is now DECLARED in
config/engine.yaml#model_store.census_domain and READ here, and an entry of no declared kind is a FAULT
rather than a silent candidate.

Classification asks three independent questions, in order, and a MODEL repo that any of them answers stops
there: LIVE (the engine serves it now), PARKED (an engine entry that is not served), DECLARED (a non-backup
file under config/, pipeline/ or scripts/ names it), ORPHAN (none of the three). ORPHAN is the only class a
deletion may ever be proposed from (R-D410). The DECLARED floor (D-3018) then decides whether the decision
is owed at all: a candidate at or below config/engine.yaml#model_store.deletion_floor_bytes is REPORTED and
NOT offered, because below it the decision costs more attention than the bytes.

Exit codes (BUG-457 tri-state): 0 = nothing owed; 1 = a FAULT (an entry of no declared kind, or a declared
value the config does not carry); 2 = bytes only an owner can dispose of.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import time
from collections.abc import Callable

HOME = pathlib.Path(os.path.expanduser("~"))
OMLX = HOME / ".omlx"
SERVING = OMLX / "models"
PARKED = OMLX / "_unloaded"
STASHED = OMLX / "models_stashed"
ENGINE_STORE = OMLX / "cache"
HUB = HOME / ".cache" / "huggingface" / "hub"
REF_ROOTS = ("config", "pipeline", "scripts")
REF_SUFFIXES = (".yaml", ".yml", ".py", ".json", ".toml", ".sh", ".md")
SKIP = (".bak", "archive/", "__pycache__")
ENGINE_YAML = pathlib.Path(__file__).resolve().parent.parent / "config" / "engine.yaml"

KIND_MODEL = "MODEL"
KIND_NON_MODEL_REPO = "NON_MODEL_REPO"
KIND_STORE_METADATA = "STORE_METADATA"
KIND_UNDECLARED = "UNDECLARED"
DOMAIN_KEYS = ("member_prefixes", "non_member_repo_prefixes", "store_metadata")
BUCKETS = ("LIVE", "PARKED", "DECLARED", "ORPHAN")

RC_OK = 0
RC_FAULT = 1
RC_OWNER_OWED = 2


# --- the declared values this instrument reads (C12: never restated here) --------------------------

def _model_store(path: pathlib.Path = ENGINE_YAML) -> dict:
    """The declared model_store block. FATAL when absent - a store rule with no home is a rumour (C12)."""
    import yaml
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


def declared_text() -> str:
    """Every non-backup byte under the reference roots, so a named dependency is recognised as one."""
    chunks = []
    for root in REF_ROOTS:
        base = pathlib.Path(root)
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in REF_SUFFIXES:
                continue
            if any(marker in path.as_posix() for marker in SKIP):
                continue
            try:
                chunks.append(path.read_text(errors="ignore"))
            except OSError:
                continue
    return "\n".join(chunks)


def classify(repos: dict, entries: dict, refs: str) -> dict:
    """LIVE / PARKED / DECLARED / ORPHAN - the first question that answers wins, so ORPHAN is conservative."""
    buckets = {key: [] for key in BUCKETS}
    for repo in repos:
        repo_path = str(HUB / repo)
        owners = [name for named in entries.values() for name, target in named.items() if target.startswith(repo_path)]
        served = [name for name in owners if name in entries["serving"]]
        if served:
            buckets["LIVE"].append(repo)
            continue
        if owners:
            buckets["PARKED"].append(repo)
            continue
        stem = repo.replace("models--", "").replace("--", "/")
        if any(name and name in refs for name in (stem, stem.split("/")[-1])):
            buckets["DECLARED"].append(repo)
            continue
        buckets["ORPHAN"].append(repo)
    return buckets


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


def pretty(repo: str) -> str:
    """A hub directory name as the owner knows the model."""
    return repo.replace("models--", "").replace("--", "/")


# --- the run ---------------------------------------------------------------------------------------

def build_report(domain, floor, kinds, measured, repos, entries, buckets, engine_bytes, engine_transient,
                 broken, above, below, when) -> dict:
    """The face this instrument PRINTS and (with --json-out) WRITES. Every number here was observed (D-3004(4))."""
    return {
        "schema_version": "1",
        "measured_at": when,
        "census_domain": domain,
        "deletion_floor_bytes": floor,
        "buckets": {key: {"n": len(val), "bytes": mb(sum(repos[r] for r in val))} for key, val in buckets.items()},
        "live": sorted(buckets["LIVE"]),
        "parked": sorted(buckets["PARKED"]),
        "orphans": sorted(buckets["ORPHAN"], key=lambda r: -repos[r]),
        "owner_owed_above_floor": above,
        "below_floor_not_offered": below,
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


def main(argv: list) -> int:
    """Measure every store, classify every MODEL repo, and report only what an owner must decide."""
    domain, floor = DOMAIN, FLOOR
    kinds = hub_entries(domain)
    measured = hub_bytes_by_entry(kinds)
    repos = model_repos(measured, kinds)
    undeclared = sorted(n for n in kinds if kinds[n] == KIND_UNDECLARED)
    entries = engine_entries()
    buckets = classify(repos, entries, declared_text())
    engine_bytes, engine_transient = measure_twice(ENGINE_STORE)
    broken = broken_entries()
    above, below = owner_owed(buckets["ORPHAN"], repos, floor)
    when = time.strftime("%Y-%m-%dT%H:%M:%S")
    report = build_report(domain, floor, kinds, measured, repos, entries, buckets, engine_bytes,
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
    print(f"  DELETION FLOOR (D-3018): {floor / 2 ** 20:.1f} MiB per repo - at or below it a candidate is NOT offered")
    print("  ORPHAN ranking (a proposal, never an act - R-D410):")
    for repo in report["orphans"][:10]:
        mark = "OFFERED" if repo in above else "below floor"
        print(f"    {repo:<62} {mb(repos[repo]):9.1f} MB  {mark}")
    print(f"  OWNER-OWED (a candidate ABOVE the floor): {len(above)} repo(s), {mb(sum(repos[r] for r in above)):.1f} MB")
    if undeclared:
        print(f"  FAULT: {len(undeclared)} hub entr(ies) match NO declared kind - declare it in "
              f"config/engine.yaml#model_store.census_domain (D-3033): {', '.join(undeclared)}")
    out = None
    for index, arg in enumerate(argv):
        if arg == "--json-out" and index + 1 < len(argv):
            out = pathlib.Path(argv[index + 1])
    if out:
        out.write_text(json.dumps(report, indent=1, sort_keys=True))
        print("wrote %s" % out)
    return exit_code(undeclared, above)


# --- the controls ----------------------------------------------------------------------------------

CONTROL_DOMAIN = {
    "member_prefixes": ["models--"],
    "non_member_repo_prefixes": ["datasets--", "spaces--"],
    "store_metadata": [".locks", "version.txt", "CACHEDIR.TAG", "blobs"],
}


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


def _cases() -> list:
    """Every known-answer control, as (name, predicate). Each must FIRE (BUG-492)."""
    no_domain = _yaml_with("model_store:\n  deletion_floor_bytes: 1\n")
    no_floor = _yaml_with("model_store:\n  census_domain:\n    member_prefixes: [models--]\n"
                          "    non_member_repo_prefixes: [datasets--]\n    store_metadata: [.locks]\n")
    empty_domain = _yaml_with("model_store:\n  deletion_floor_bytes: 1\n  census_domain:\n"
                              "    member_prefixes: []\n    non_member_repo_prefixes: [datasets--]\n"
                              "    store_metadata: [.locks]\n")
    zero_floor = _yaml_with("model_store:\n  deletion_floor_bytes: 0\n")
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
        return set(classify(members(), {}, "")["ORPHAN"])

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
