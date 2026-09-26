#!/usr/bin/env python3
"""handoff.py - content-addressed stage handoffs: a receipt binds a claim to BYTES, never to a path (D-403).

WHY (RC-2/BUG-376). A stage that declares an input path cannot prove which bytes it consumed, so a producer
that rewrites that path later invalidates every downstream claim while nothing fails. A handoff is therefore a
RECEIPT: output digest, size, mutability, code_sha and stamp, taken at run time. verify compares bytes.

Sealing copies an immutable artifact's bytes into a content-addressed blob store, so a rewrite destroys the
claim but NOT the verified image (BUG-376's actual loss).

ONE FACT, ONE HOME (C12): mutability is READ from config/artifact_ownership.yaml when that config declares it.
This module never re-declares it.

CLI: --backfill (receipts + seals) | --seal-revisions (materialise declared SUPERSEDED revisions) | --selftest
Exit: 0 ok | 1 DRIFT | 2 owner-owed (BUG-457 tri-state convention).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "handoffs.yaml"
OWNERSHIP = REPO / "config" / "artifact_ownership.yaml"
SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    """Full sha256 of a file's bytes (no truncation: a receipt IS the whole claim)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """sha256 of bytes in memory: a locator is verified by CONTENT, never by the name it was written under."""
    return hashlib.sha256(data).hexdigest()


def git_bytes(commit: str, path: str) -> bytes | None:
    """The bytes of one path at one commit, from the git object store; None when not retrievable.

    git is itself a content-addressed store, so a revision that was COMMITTED survives an in-place rewrite of
    the working tree. That is why a superseded revision is still verifiable rather than merely quotable: the
    digest is re-derived from bytes the store still holds (BUG-488).
    """
    try:
        r = subprocess.run(["git", "show", commit + ":" + path], cwd=REPO, capture_output=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def code_sha() -> str:
    """Identify the CODE that took the receipt, not just the data (R14): HEAD plus a dirty flag."""
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True,
                              text=True).stdout.strip() or "unknown"
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True,
                               text=True).stdout.strip()
        return head + ("+dirty" if dirty else "")
    except OSError as exc:
        return "no-git (" + exc.__class__.__name__ + ")"


def stamp() -> str:
    """UTC timestamp, second resolution (a receipt must be orderable across machines)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def config() -> dict:
    """Read config/handoffs.yaml. Fail closed: an unreadable declaration is never a silent empty set (C16)."""
    if not CONFIG.exists():
        raise SystemExit("FAIL-CLOSED: config/handoffs.yaml is absent - a handoff mechanism with no "
                         "declaration decides nothing")
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


#: BUG-491: a CONTROL may not write into the RULER it calibrates. While this is set, every path this module
#: would append to resolves INSIDE the sandbox, so --selftest cannot put fixture receipts into the production
#: journal. Measured before the fix: 14 of the first 20 receipts in governance/HANDOFFS.jsonl were this
#: fixture (2 per health run), which inflated the population its floor is counted over - so the floor could
#: never fail. A guard that cannot fail is not a guard.
SANDBOX: Path | None = None


def journal_path() -> Path:
    """The append-only receipt journal (R-D410: appended, never edited); SANDBOXED during a control run."""
    if SANDBOX is not None:
        return SANDBOX / "HANDOFFS.selftest.jsonl"
    return REPO / str(config().get("journal"))


def blob_dir() -> Path:
    """The content-addressed blob store directory; SANDBOXED during a control run (BUG-491)."""
    if SANDBOX is not None:
        return SANDBOX / "blobs"
    return REPO / str(config().get("blob_dir"))


def ownership_class(path: str) -> str | None:
    """The mutability class for a path, READ from artifact_ownership.yaml when declared there (C12)."""
    if not OWNERSHIP.exists():
        return None
    arts = (yaml.safe_load(OWNERSHIP.read_text(encoding="utf-8")) or {}).get("artifacts") or {}
    spec = arts.get(path) or {}
    return str(spec.get("mutability") or "") or None


def declared_class(spec: dict, path: str) -> tuple[str, str]:
    """Return (mutability, source) for one path: the ownership registry wins over a local copy (one home)."""
    if str(spec.get("ownership_ref") or ""):
        return (ownership_class(path) or "undeclared"), "config/artifact_ownership.yaml"
    return str(spec.get("mutability") or "undeclared"), "config/handoffs.yaml"


def paths_of(spec: dict) -> list[dict]:
    """Every declared path of an artifact, normalised to {path, seal} dicts."""
    out: list[dict] = []
    for p in spec.get("paths") or []:
        if isinstance(p, str):
            out.append({"path": p, "seal": False})
        else:
            out.append({"path": str(p.get("path")), "seal": bool(p.get("seal"))})
    return out


def receipt(artifact_id: str, spec: dict, path: str, origin: str) -> dict:
    """Take ONE receipt for one declared path and append it to the journal (crash-safe, C6).

    A path that does not exist is RECORDED as absent: a missing artifact is a fact about the world and it is
    the fact a downstream claim is usually wrong about.
    """
    full = REPO / path
    mutability, mut_source = declared_class(spec, path)
    rec: dict = {"schema_version": SCHEMA_VERSION, "decided": "D-403", "artifact": artifact_id, "path": path,
                 "mutability": mutability, "mutability_source": mut_source, "origin": origin,
                 "code_sha": code_sha(), "stamp": stamp(), "present": full.exists()}
    if full.exists():
        rec["sha256"] = sha256_file(full)
        rec["bytes"] = full.stat().st_size
    jp = journal_path()
    jp.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(jp.parent), prefix=".handoff_", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(jp.read_text(encoding="utf-8") if jp.exists() else "")
            fh.write(json.dumps(rec, sort_keys=True) + chr(10))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, jp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return rec


def _write_blob(digest: str, data: bytes) -> str:
    """Write bytes into the content-addressed store under the digest they hash to (crash-safe, C6).

    Content-addressed: the blob is NAMED by its digest, so sealing twice is idempotent and cannot collide.
    """
    dest = blob_dir() / (digest + ".bin")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        fd, tmp = tempfile.mkstemp(dir=str(dest.parent), prefix=".blob_", suffix=".bin")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    try:
        return str(dest.relative_to(REPO))
    except ValueError:  # a sandboxed control run writes outside the repo BY DESIGN (BUG-491)
        return str(dest)


def seal(path: str) -> str:
    """Copy an artifact's bytes into the content-addressed blob store; return the blob path, or 'absent'."""
    full = REPO / path
    if not full.exists():
        return "absent"
    return _write_blob(sha256_file(full), full.read_bytes())


def seal_revision(locator: dict) -> str:
    """Materialise ONE declared SUPERSEDED revision from the store its locator names; '' if absent.

    The locator is NOT trusted. The bytes are read from the named store, the digest is RE-DERIVED from them,
    and a disagreement RAISES rather than writing a blob whose name lies - because every later verification
    would then inherit the lie.
    """
    kind, _, ref = str(locator.get("bytes_at") or "").partition(":")
    declared = str(locator.get("digest") or "")
    if kind != "git":
        raise SystemExit("FAIL-CLOSED: bytes_at store " + repr(kind) + " has no reader - a revision locator "
                         "naming a store nothing can read is not a locator")
    data = git_bytes(ref, str(locator.get("path")))
    if data is None:
        return ""
    got = sha256_bytes(data)
    if got != declared:
        raise SystemExit("FAIL-CLOSED: " + ref + ":" + str(locator.get("path")) + " hashes to " + got[:16]
                         + ", declared " + declared[:16] + " - the locator does not describe those bytes")
    return _write_blob(declared, data)


def seal_revisions() -> int:
    """Seal every declared revision locator, so a superseded revision's verified image also survives."""
    locs = config().get("revision_locators") or []
    if not locs:
        print("ok handoff revisions: no revision locator declared (nothing to seal)")
        return 0
    for loc in locs:
        blob = seal_revision(loc)
        print("  revision " + str(loc.get("digest"))[:16] + " (" + str(loc.get("state")) + ") via "
              + str(loc.get("bytes_at")) + ": " + (blob or "ABSENT - the store does not hold those bytes"))
    print("ok handoff revisions: " + str(len(locs)) + " declared revision(s) resolved by re-derived bytes")
    return 0


def read_receipts() -> list[dict]:
    """Read the journal. A malformed line is a DEFECT, so it raises rather than being skipped (C16)."""
    jp = journal_path()
    if not jp.exists():
        return []
    out: list[dict] = []
    for i, line in enumerate(jp.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit("FAIL-CLOSED: " + jp.name + " line " + str(i) + " is not JSON: " + str(exc)) from exc
    return out


def latest() -> dict[tuple[str, str], dict]:
    """The most recent receipt per (artifact, path): later receipts supersede earlier ones by design."""
    out: dict[tuple[str, str], dict] = {}
    for rec in read_receipts():
        out[(str(rec.get("artifact")), str(rec.get("path")))] = rec
    return out


def backfill() -> int:
    """Take a receipt for every declared path, and seal every path declared seal: true.

    origin=backfill is honest labelling: these receipts claim what the bytes ARE now, not what a past run
    consumed. They are immediately useful - from now on a rewrite of any declared path is DETECTED.
    """
    n = 0
    for spec in config().get("artifacts") or []:
        aid = str(spec.get("id"))
        for p in paths_of(spec):
            rec = receipt(aid, spec, p["path"], "backfill")
            n += 1
            if p["seal"] and rec.get("present"):
                print("  sealed " + aid + ": " + seal(p["path"]))
            print("  receipt " + aid + ": " + str(rec.get("sha256", "ABSENT"))[:16] + " " + p["path"])
    print("ok handoff backfill: " + str(n) + " receipt(s) appended to " + journal_path().name)
    return 0


def selftest() -> int:
    """Known-answer control for the METER itself (D-400/RC-5), run in a SANDBOX (BUG-491).

    A rail that has never been shown a positive is indistinguishable from a rail that always passes. But a
    control that writes into the JOURNAL it calibrates is worse than no control: the fixtures inflate the
    population the store's floor is measured over, so the floor can never fail (14 of 20 receipts were this
    fixture). So the control now asserts THREE things, and any of them can fail: the digest moves on a
    rewrite; the receipts landed in the SANDBOX (the redirect is proven, not assumed); and the PRODUCTION
    journal is byte-identical afterwards (the ruler was not touched).
    """
    global SANDBOX
    prod = journal_path()
    pre = sha256_file(prod) if prod.exists() else "absent"
    art = {"id": "selftest", "mutability": "immutable", "paths": []}
    first: dict = {}
    second: dict = {}
    measured = -1
    blob = "absent"
    with tempfile.TemporaryDirectory(prefix="handoff_selftest_") as td:
        SANDBOX = Path(td)
        try:
            fixture = SANDBOX / "fixture.bin"
            fixture.write_bytes(b"original")
            first = receipt("selftest", art, str(fixture), "selftest")
            fixture.write_bytes(b"REWRITTEN")
            second = receipt("selftest", art, str(fixture), "selftest")
            blob = seal(str(fixture))
            measured = len(read_receipts())
        finally:
            SANDBOX = None
    post = sha256_file(prod) if prod.exists() else "absent"
    if not (first.get("sha256") and first.get("sha256") != second.get("sha256")):
        print("FAIL handoff selftest: a rewrite did not change the digest - the meter is broken")
        return 1
    if measured != 2 or blob == "absent":
        print("FAIL handoff selftest: the control's receipts did not land in the SANDBOX (" + str(measured)
              + " record(s), blob " + str(blob) + ") - the isolation is assumed, not proven")
        return 1
    if post != pre:
        print("FAIL handoff selftest: the control WROTE INTO THE RULER it calibrates (" + str(prod) + ": "
              + str(pre)[:16] + " -> " + str(post)[:16] + ") - BUG-491")
        return 1
    print("ok handoff selftest: a rewrite changes the digest (the meter detects drift); SANDBOXED in a temp dir "
          "(2 receipt(s) + 1 blob), production journal byte-identical (" + str(pre)[:16] + ") - BUG-491")
    return 0


def main() -> int:
    """CLI: --backfill (receipts + seals) or --selftest (the meter's known-answer control)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--seal-revisions", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.seal_revisions:
        return seal_revisions()
    if a.backfill:
        return backfill()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
