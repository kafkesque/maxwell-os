#!/usr/bin/env python3
"""BUG-804's blob-aware store census - corrected for two failures this instrument committed.

FAILURE 1 (BUG-804 itself): a census that walks the engine's serving directory measures SYMLINKS
and reports 0 B for a model that is present. This census resolves every entry to its target, and
it treats a REAL directory in the serving path as live too, because the engine serves those.

FAILURE 2 (BUG-807, same hour): a single-instant byte count reported 85 GB in the engine's own
store as reclaimable mass, and the store later read 0 B. The first draft then wrote a CAUSE into
the record ("the engine released it") which was false - the OWNER cleaned it. A census may not
narrate a cause it did not observe, so every store is now measured TWICE and flagged TRANSIENT
when it moves. A transient store is never offered as an owner decision.

Classification asks three independent questions, in order, and a repo that any of them answers
stops there: LIVE (the engine serves it now), PARKED (an engine entry that is not served),
DECLARED (a non-backup file under config/, pipeline/ or scripts/ names it), ORPHAN (none of the
three - the only category a deletion may ever be proposed from, R-D410).

Exit codes (BUG-457 tri-state): 0 = nothing unowned; 2 = bytes only an owner can dispose of.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

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
MOVE = 0.05


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


def measure_twice(path: pathlib.Path, gap: float = 1.5) -> tuple[int, bool]:
    """Return (bytes, transient). TRANSIENT means the store moved between two readings in one run."""
    first = dir_bytes(path)
    time.sleep(gap)
    second = dir_bytes(path)
    moved = first != second and abs(first - second) > MOVE * max(first, second, 1)
    return max(first, second), moved


def mb(n: int) -> float:
    """Bytes as megabytes, one decimal place."""
    return round(n / 1e6, 1)


def engine_entries() -> dict[str, dict[str, str]]:
    """Resolve every entry of the three engine directories to the store it really lives in."""
    out: dict[str, dict[str, str]] = {}
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


def hub_repos() -> dict[str, int]:
    """Per-repo bytes measured on the repo's blobs directory, because snapshots are symlinks into it."""
    out: dict[str, int] = {}
    if not HUB.is_dir():
        return out
    for repo in sorted(HUB.iterdir()):
        blobs = repo / "blobs"
        out[repo.name] = dir_bytes(blobs if blobs.is_dir() else repo)
    return out


def declared_text() -> str:
    """Every non-backup byte under the reference roots, so a named dependency is recognised as one."""
    chunks: list[str] = []
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


def classify(repos: dict[str, int], entries: dict[str, dict[str, str]], refs: str) -> dict[str, list[str]]:
    """LIVE / PARKED / DECLARED / ORPHAN - the first question that answers wins, so ORPHAN is conservative."""
    buckets: dict[str, list[str]] = {key: [] for key in ("LIVE", "PARKED", "DECLARED", "ORPHAN")}
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


def broken_entries() -> list[str]:
    """Engine entries whose target is ABSENT: a name that reads as 'on disk' and is not (BUG-808)."""
    out: list[str] = []
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


def main(argv: list[str]) -> int:
    """Measure every store, classify every repo, and report only what an owner must decide."""
    entries = engine_entries()
    repos = hub_repos()
    buckets = classify(repos, entries, declared_text())
    engine_bytes, engine_transient = measure_twice(ENGINE_STORE)
    broken = broken_entries()
    report = {
        "measured_at": "2026-10-15",
        "broken_entries": broken,
        "engine_store": {
            "bytes": mb(engine_bytes),
            "transient": engine_transient,
            "note": "not on the serving path; measured twice because a single reading reported 85 GB that the owner then cleaned (BUG-807)",
        },
        "hub_bytes": mb(sum(repos.values())),
        "buckets": {key: {"n": len(val), "bytes": mb(sum(repos[r] for r in val))} for key, val in buckets.items()},
        "live": sorted(buckets["LIVE"]),
        "parked": sorted(buckets["PARKED"]),
        "orphans": sorted(buckets["ORPHAN"], key=lambda r: -repos[r]),
        "engine_entries": entries,
        "hub_repos": {key: mb(val) for key, val in sorted(repos.items(), key=lambda kv: -kv[1])},
    }
    print("STORE CENSUS (BUG-804 remedy, MEASURED, two readings per store)")
    print("  engine store (~/.omlx/cache): %8.1f MB  transient=%s" % (mb(engine_bytes), engine_transient))
    print("  hub total:                   %8.1f MB" % mb(sum(repos.values())))
    for bucket in ("LIVE", "PARKED", "DECLARED", "ORPHAN"):
        counts = report["buckets"][bucket]
        print("  %-8s %2d repo(s)  %9.1f MB" % (bucket, counts["n"], counts["bytes"]))
    print("  LIVE:   %s" % ", ".join(pretty(r) for r in report["live"]))
    print("  PARKED: %s" % ", ".join(pretty(r) for r in report["parked"]))
    print("  BROKEN entries (an engine name whose target is ABSENT - BUG-808): %s" % (", ".join(broken) or "none"))
    print("  ORPHAN ranking (a proposal, never an act - R-D410):")
    for repo in report["orphans"][:10]:
        print("    %-62s %9.1f MB" % (repo, mb(repos[repo])))
    out = None
    for index, arg in enumerate(argv):
        if arg == "--json-out" and index + 1 < len(argv):
            out = pathlib.Path(argv[index + 1])
    if out:
        out.write_text(json.dumps(report, indent=1, sort_keys=True))
        print("wrote %s" % out)
    return 2 if report["buckets"]["ORPHAN"]["n"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
