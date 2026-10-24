#!/usr/bin/env python3
"""scripts/build_archive_index.py — the writer and checker for archive/index.yaml (D-365).

WHY this exists: the shipped archive/index.yaml declared `authority: D2226`, a decision whose
state in config/decisions.yaml is REJECTED. It was generated 2026-08-10 against an out-of-repo
archive_root, so the in-repo archive/ (16 GB, 36 top-level entries) was unindexed, and no reader
anywhere consumes the file. An index that is hand-built, never regenerated and never checked
drifts silently — that is BUG-342's class (never re-derive a governance count by hand).

This script READS the bytes on disk and WRITES the index. It never moves, edits or deletes an
archive entry: it registers them. Deletion is a separate, owner-gated act.

Usage:
    python3 scripts/build_archive_index.py            # regenerate archive/index.yaml
    python3 scripts/build_archive_index.py --check    # exit 1 if the index does not match the bytes

Exit codes: 0 ok | 1 drift (--check), a declared input missing, or the coverage invariant violated |
2 config error or a SHADOWED rule declaration (a rule the ignore block already excludes can never fire -
fail closed, C16/BUG-537).
Config: config/archive_index.yaml (C12 — every path and rule lives there, none here).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CFG_PATH = _ROOT / "config" / "archive_index.yaml"


def write_atomic(path: Path, text: str) -> None:
    """Write text via tempfile -> fsync -> os.replace so a crash cannot leave a torn index (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_idx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_cfg() -> dict[str, Any]:
    """Load and minimally validate the index contract. Raises on a malformed declaration (C16)."""
    cfg = yaml.safe_load(_CFG_PATH.read_text(encoding='utf-8'))
    if not isinstance(cfg, dict) or "rules" not in cfg or "local_archive" not in cfg:
        raise ValueError(f"{_CFG_PATH}: must be a mapping carrying 'local_archive' and 'rules'")
    for rule in cfg["rules"]:
        for key in ("match", "category", "disposition", "reason"):
            if key not in rule:
                raise ValueError(f"{_CFG_PATH}: rule missing '{key}': {rule}")
        re.compile(rule["match"])  # fail loud on a bad pattern, not silently at match time
    return cfg


def classify(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the FIRST matching rule's disposition claim for a top-level archive entry."""
    for rule in cfg["rules"]:
        if re.search(rule["match"], name):
            return {
                "category": rule["category"],
                "disposition": rule["disposition"],
                "authority": rule.get("authority"),
                "reason": rule["reason"],
            }
    return dict(cfg["default"])


def make_ignore(cfg: dict[str, Any]) -> Callable[[str], bool]:
    """Declared OS-metadata exclusion (BUG-469). The rule list lives in config, never here (C12)."""
    spec = cfg.get("ignore") or {}
    names = set(spec.get("names") or [])
    globs = [re.compile(g) for g in (spec.get("globs") or [])]
    return lambda name: name in names or any(g.search(name) for g in globs)


def ignored_claim(cfg: dict[str, Any]) -> dict[str, Any]:
    """The DECLARED claim for the objects the ignore block excludes (BUG-537). Fail closed (C16).

    The ignore block is the ONE home of this class - the names, the globs, the disposition and the reason
    sit together there (D-2646). An exclusion with no declared disposition is an unrecorded loss wearing
    the clothes of hygiene, so it REFUSES rather than defaulting.
    """
    spec = cfg.get("ignore") or {}
    for key in ("category", "disposition", "authority", "reason"):
        if key not in spec:
            raise ValueError(
                f"{_CFG_PATH}: the ignore block must declare '{key}' - an excluded object is either a "
                f"DECLARED exclusion or it is a silent loss (BUG-537)"
            )
    return {k: spec[k] for k in ("category", "disposition", "authority", "reason")}


def shadowed_rules(cfg: dict[str, Any]) -> list[str]:
    r"""Every `rules:` pattern the ignore block already excludes: a rule that could never fire (BUG-537).

    Measured against the ignore block's LITERAL names (a glob-only shadow cannot be enumerated, so it is
    simply not claimed). This is the control that would have caught `^\.DS_Store$` sitting dead in config
    while the very object it describes left the index unnoticed.
    """
    spec = cfg.get("ignore") or {}
    names = list(spec.get("names") or [])
    out: list[str] = []
    for rule in cfg.get("rules", []):
        pat = re.compile(rule["match"])
        hit = [n for n in names if pat.search(n)]
        if hit:
            out.append(f"rule {rule['match']!r} can never fire: the ignore block already excludes {hit}")
    return out


def coverage_faults(indexed: set[str], excluded: set[str], on_disk: set[str]) -> list[str]:
    """BUG-537's invariant: an on-disk object is INDEXED or DECLARED excluded, never silently absent.

    In the words the buglog demanded: `an on-disk object that was indexed is either still indexed or
    declared gone`. The first arm is the class that let `.DS_Store` leave this index while the file stayed
    on disk; the second arm is drift - an indexed object whose bytes are gone is a fact to regenerate,
    never a quiet shrink.
    """
    faults = [
        f"on disk but in NEITHER the index nor the declared exclusions: {name}"
        for name in sorted(on_disk - indexed - excluded)
    ]
    faults += [
        f"indexed but ABSENT from disk (regenerate the index): {name}"
        for name in sorted(indexed - on_disk)
    ]
    return faults


def selftest() -> int:
    """Known-answer controls (BUG-492/BUG-537/BUG-556). No live-tree write, no NLI, no network.

    Every control below FAILS on the pre-fix code and passes on the fixed code - a control never seen to
    fire is not a control, and this file's whole subject is a record that vanished without a verdict.
    """
    fired = 0
    total = 0

    def check(name: str, ok: bool, detail: str) -> None:
        nonlocal fired, total
        total += 1
        if ok:
            fired += 1
        print(f"  {'ok  ' if ok else 'FAIL'} selftest/{name}: {detail}")

    check(
        "coverage_clean",
        coverage_faults({"a"}, {".DS_Store"}, {"a", ".DS_Store"}) == [],
        "an object inside either list is never a fault",
    )
    faults = coverage_faults({"a"}, set(), {"a", ".DS_Store"})
    check(
        "coverage_silent_delisting",
        len(faults) == 1 and ".DS_Store" in faults[0],
        f"an on-disk object in NEITHER list FIRES ({faults[0] if faults else 'NOT FIRED'})",
    )
    faults = coverage_faults({"a", "gone.txt"}, set(), {"a"})
    check(
        "coverage_absent_bytes",
        len(faults) == 1 and "gone.txt" in faults[0],
        f"an indexed-but-absent object FIRES ({faults[0] if faults else 'NOT FIRED'})",
    )
    synth = {"ignore": {"names": [".DS_Store"]}, "rules": [{"match": r'^\.DS_Store$'}]}
    faults = shadowed_rules(synth)
    check(
        "shadowed_rule_fires",
        len(faults) == 1,
        f"a rule the ignore block shadows FIRES ({faults[0] if faults else 'NOT FIRED'})",
    )
    try:
        live = shadowed_rules(yaml.safe_load(_CFG_PATH.read_text(encoding="utf-8")))
        check(
            "shadowed_rule_live_clean",
            live == [],
            f"the LIVE config carries {len(live)} shadowed rule(s)"
            + (f" - {live[0]}" if live else ""),
        )
    except Exception as exc:  # noqa: BLE001 - an unreadable config is reported, never silently clean (C16)
        check("shadowed_rule_live_clean", False, f"the LIVE config is UNREADABLE: {exc}")
    synth_ignore = {"ignore": {"names": [".DS_Store"], "globs": [r"-(wal|shm|journal)$"]}}
    ignores = make_ignore(synth_ignore)
    check(
        "transient_sidecar_ignored",
        ignores("maxwell_pre_index_20260917.db-shm")
        and ignores("x.db-wal")
        and not ignores("maxwell_pre_index_20260917.db"),
        "a transient SQLite sidecar is excluded and a real .db is NOT (BUG-556)",
    )
    try:
        ignored_claim({"ignore": {"names": [".DS_Store"]}})
        check("claim_fail_closed", False, "an ignore block with NO disposition was ACCEPTED")
    except ValueError as exc:
        check("claim_fail_closed", "must declare" in str(exc), f"an incomplete ignore block REFUSES: {exc}")

    print(f"archive-index controls: {fired}/{total} known-answer control(s) fire")
    return 0 if fired == total else 1


def measure(path: Path, ignore: Callable[[str], bool]) -> dict[str, Any]:
    """Measure one entry: bytes, child counts and the newest NON-IGNORED date (BUG-469).

    A directory's own mtime moves when a browser writes '.DS_Store' into it, so it is NOT the date this
    index records: `modified` is the newest non-ignored descendant. A directory with no measurable
    descendant falls back to its own mtime, which is then a fact about bytes and not about a browse.
    """
    if not path.is_dir():
        return {"kind": "file", "bytes": path.stat().st_size, "files": 1, "dirs": 0} if not ignore(
            path.name) else {"kind": "file", "bytes": 0, "files": 0, "dirs": 0}
    files = dirs = 0
    total = 0
    newest = 0.0
    for sub in path.rglob("*"):
        if ignore(sub.name):
            continue
        try:
            st = sub.stat()
        except OSError:
            continue
        newest = max(newest, st.st_mtime)
        if sub.is_dir():
            dirs += 1
        elif sub.is_file():
            files += 1
            total += st.st_size
    if newest == 0.0:
        newest = path.stat().st_mtime
    return {
        "kind": "dir",
        "bytes": total,
        "files": files,
        "dirs": dirs,
        "modified": dt.datetime.fromtimestamp(newest).strftime("%Y-%m-%d"),
    }


def scan_local(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Scan the in-repo archive and return (entries, disposition histogram, excluded census)."""
    root = _ROOT / cfg["local_archive"]
    if not root.is_dir():
        raise FileNotFoundError(f"declared local_archive is not a directory: {root}")
    self_name = Path(cfg["output"]).name
    ignore = make_ignore(cfg)
    claim = ignored_claim(cfg)
    entries: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    hist: dict[str, int] = {}
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.name == self_name:
            continue  # the index does not index itself
        if ignore(child.name):
            # BUG-469: machine-generated metadata is not archive content - excluded from every COUNT and
            # from the `modified` date. BUG-537: and still REPORTED, because an object that leaves this
            # file without a verdict is a silent de-listing, not hygiene.
            st = child.stat()
            excluded.append(
                {
                    "name": child.name,
                    "kind": "dir" if child.is_dir() else "file",
                    "bytes": 0 if child.is_dir() else st.st_size,
                    "modified": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                }
            )
            continue
        claim = classify(child.name, cfg)
        m = measure(child, ignore)
        entries.append(
            {
                "name": child.name,
                "kind": m["kind"],
                "bytes": m["bytes"],
                "files": m["files"],
                "dirs": m["dirs"],
                "modified": m.get("modified")
                or dt.datetime.fromtimestamp(child.stat().st_mtime).strftime("%Y-%m-%d"),
                **claim,
            }
        )
        hist[claim["disposition"]] = hist.get(claim["disposition"], 0) + 1
    return entries, hist, excluded


def scan_external(cfg: dict[str, Any]) -> dict[str, Any]:
    """Report the out-of-repo archive_root the previous index described. Never operated on."""
    spec = cfg.get("external_archive_root") or {}
    out: dict[str, Any] = dict(spec)
    path = Path(spec.get("path", ""))
    out["present"] = path.is_dir()
    out["entries"] = len(list(path.iterdir())) if out["present"] else 0
    return out


def build_body(cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic body of the index (everything except stamps)."""
    entries, hist, excluded = scan_local(cfg)
    total = sum(e["bytes"] for e in entries)
    return {
        "schema_version": cfg["schema_version"],
        "authority": cfg["decision"],
        "scope": cfg["local_archive"],
        "note": (
            "Regenerated by scripts/build_archive_index.py; every entry is MEASURED from the bytes on "
            "disk, and every object the index DECLINES to count is listed under `excluded` with its bytes - "
            "an on-disk object is either indexed or declared excluded, never silently absent (BUG-537). "
            "Nothing here is hand-written, and this script never moves or deletes an entry."
        ),
        "local_archive": {
            "path": cfg["local_archive"],
            "entries": len(entries),
            "bytes": total,
            "dispositions": dict(sorted(hist.items())),
            "excluded": {
                "entries": len(excluded),
                "bytes": sum(e["bytes"] for e in excluded),
                **ignored_claim(cfg),
                "items": excluded,
            },
            "index": entries,
        },
        "external_archive_root": scan_external(cfg),
        "dispositions_vocabulary": cfg["dispositions"],
    }


def body_hash(body: dict[str, Any]) -> str:
    """Stable hash of the derived body, so --check can see any drift in the inventory."""
    canon = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def render(cfg: dict[str, Any], body: dict[str, Any], stamp: str) -> str:
    """Render the final document: body + body hash + generation stamp."""
    doc = {"generated": stamp, "body_sha256": body_hash(body), **body}
    return (
        "# archive/index.yaml — GENERATED by scripts/build_archive_index.py (D-365). Do not hand-edit.\n"
        "# Authority: " + cfg["decision"] + " | check: just health -> scripts/build_archive_index.py --check\n"
        + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
    )


def main() -> int:
    """Regenerate the index, or verify it against the bytes on disk."""
    ap = argparse.ArgumentParser(description="archive index writer/checker (D-365)")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls (BUG-492)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the index does not match the bytes")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    try:
        cfg = load_cfg()
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR config: {exc}", file=sys.stderr)
        return 2
    shadowed = shadowed_rules(cfg)
    if shadowed:
        print("ERROR declaration conflict (fail closed, C16/BUG-537):", file=sys.stderr)
        for fault in shadowed:
            print(f"  {fault}", file=sys.stderr)
        return 2
    try:
        body = build_body(cfg)
    except FileNotFoundError as exc:
        print(f"ERROR declared input: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR declaration: {exc}", file=sys.stderr)
        return 2

    out = _ROOT / cfg["output"]
    want = body_hash(body)

    if args.check:
        if not out.is_file():
            print(f"RED archive index: {cfg['output']} is missing", file=sys.stderr)
            return 1
        try:
            stored = yaml.safe_load(out.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            print(
                f"RED archive index: {cfg['output']} does not parse ({exc}) - an unreadable index is an "
                f"UNKNOWN, not a clean (C16)",
                file=sys.stderr,
            )
            return 1
        stored_la = stored.get("local_archive") if isinstance(stored, dict) else None
        stored_items = (stored_la or {}).get("index")
        stored_excl = ((stored_la or {}).get("excluded") or {}).get("items")
        if not isinstance(stored_items, list) or not isinstance(stored_excl, list):
            print(
                f"RED archive index: {cfg['output']} carries no readable entry/exclusion census - an "
                f"ABSENT census must not read as a clean one (C16/BUG-537)",
                file=sys.stderr,
            )
            return 1
        la_fresh = body["local_archive"]
        faults = coverage_faults(
            {e.get("name") for e in stored_items},
            {e.get("name") for e in stored_excl},
            {e["name"] for e in la_fresh["index"]} | {e["name"] for e in la_fresh["excluded"]["items"]},
        )
        if faults:
            print(
                f"RED archive index: {cfg['output']} fails the coverage invariant (BUG-537):",
                file=sys.stderr,
            )
            for fault in faults:
                print(f"  {fault}", file=sys.stderr)
            print(
                "  an on-disk object is either INDEXED or DECLARED excluded, never silently absent; "
                "run: python3 scripts/build_archive_index.py",
                file=sys.stderr,
            )
            return 1
        have = stored.get("body_sha256")
        if have != want:
            print(
                f"RED archive index: {cfg['output']} is STALE — stored body_sha256 {str(have)[:12]} "
                f"!= measured {want[:12]}. Run: python3 scripts/build_archive_index.py",
                file=sys.stderr,
            )
            return 1
        la = body["local_archive"]
        print(
            f"  ok   archive index in sync ({la['entries']} entries, "
            f"{la['excluded']['entries']} declared exclusion(s), "
            f"{la['bytes'] / 1e9:.1f} GB, dispositions {la['dispositions']})"
        )
        return 0

    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out, render(cfg, body, stamp))
    la = body["local_archive"]
    if not args.quiet:
        print(
            f"archive index written: {cfg['output']} ({la['entries']} entries, "
            f"{la['excluded']['entries']} declared exclusion(s), {la['bytes'] / 1e9:.1f} GB)"
        )
        for item in la["excluded"]["items"]:
            print(f"  excluded ({la['excluded']['disposition']}): {item['name']} ({item['bytes']} B)")
        for name, n in sorted(la["dispositions"].items()):
            print(f"  {name}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
