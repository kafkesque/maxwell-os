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


APPEND_STATES: tuple[str, ...] = ("unchanged", "appended", "truncated", "rewritten")


def prefix_state(cur: bytes, rec: dict) -> tuple[str, str]:
    """Decide the append_only rule from BYTES: unchanged / appended / truncated / rewritten (BUG-540).

    THE RULE'S HOME IS HERE (D-2971). A receipt is a claim about bytes, so the four states a receipted region
    can be in are THIS module's subject. The function was written inside the rail that first needed it, and it
    MOVED when the re-baseline act gave it a second caller: the act must ask the identical question before it
    may move a baseline, and two implementations of one rule drift (D-274a). One home, two callers - the rail
    measures with it, the act refuses with it.

    The receipt carries the OLD file's LENGTH and the OLD file's sha256, so "the receipted bytes are a byte-PREFIX
    of the current bytes" is decided by hashing current[:receipted_length] and comparing THAT digest to the
    receipted one. No copy of the old file is needed: a digest and a length are enough, and this is exactly what
    D-403 means by a claim about bytes.

    WHY THIS REPLACED A BLOB COMPARISON. The first implementation compared the current prefix against a blob in
    the content-addressed store, so it could only ever run for a SEALED artifact. config/decisions.yaml declares
    seal: false ("the registry is append_only and textual, so a prefix check detects a rewrite without a copy") -
    a FALSE PREMISE, because the digest+length pair was never used for the check. MEASURED 2026-09-26: appending
    ONE newline to config/decisions.yaml - a legal append - was reported as "a cell was edited or the file was
    truncated". The rule could not say YES (BUG-492: a rule never seen to succeed is a comment) and its verdict
    MISATTRIBUTED the cause, because it cannot tell tampering from "the old bytes were never retained".
    """
    n = int(rec.get("bytes") or 0)
    want = str(rec.get("sha256") or "")
    if not want or n <= 0:
        return "rewritten", "the receipt carries no (bytes, sha256) pair, so the prefix rule cannot be evaluated"
    if len(cur) < n:
        return "truncated", ("the file is now " + str(len(cur)) + " bytes, SHORTER than the receipted " + str(n)
                             + " - a truncation loses every record after the cut")
    got = sha256_bytes(cur[:n])
    if got != want:
        return "rewritten", ("the first " + str(n) + " bytes hash to " + got[:16] + ", not the receipted "
                             + want[:16] + " - a byte inside the receipted region was edited in place")
    if len(cur) == n:
        return "unchanged", ""
    return "appended", ""


#: The fields a receipt MEASURES. `extra` may not carry one (D-2971): a receipt that can be told what it
#: measured is not a receipt, so a caller-supplied collision is a refusal rather than a silent overwrite (C16).
RECEIPT_MEASURED_KEYS: tuple[str, ...] = ("schema_version", "decided", "artifact", "path", "mutability",
                                          "mutability_source", "origin", "code_sha", "stamp", "present",
                                          "sha256", "bytes")


def receipt(artifact_id: str, spec: dict, path: str, origin: str, extra: dict | None = None) -> dict:
    """Take ONE receipt for one declared path and append it to the journal (crash-safe, C6).

    A path that does not exist is RECORDED as absent: a missing artifact is a fact about the world and it is
    the fact a downstream claim is usually wrong about.

    `extra` (D-2971) carries the SUPERSESSION a re-baseline must publish - what it replaced, the commits that
    moved it and the decision that ordered it - so the journal is the permanent record of the rewrite instead of
    a journal from which the rewrite has been wiped. It may not carry a measured field (see above).
    """
    collisions = sorted(set(extra or {}) & set(RECEIPT_MEASURED_KEYS))
    if collisions:
        raise ValueError("FAIL-CLOSED (handoff): extra carries the receipt's OWN measured field(s) "
                         + str(collisions) + " - a receipt that can be told what it measured is not a receipt "
                         "(C16/D-2971)")
    full = REPO / path
    mutability, mut_source = declared_class(spec, path)
    rec: dict = {"schema_version": SCHEMA_VERSION, "decided": "D-403", "artifact": artifact_id, "path": path,
                 "mutability": mutability, "mutability_source": mut_source, "origin": origin,
                 "code_sha": code_sha(), "stamp": stamp(), "present": full.exists()}
    if full.exists():
        rec["sha256"] = sha256_file(full)
        rec["bytes"] = full.stat().st_size
    rec.update(extra or {})  # D-2971: the supersession a re-baseline publishes (measured keys already refused)
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


# ----------------------------------------------------------------------------------------------------------
# THE RE-BASELINE ACT (D-2971/BUG-376): a receipt whose region was rewritten is re-cut WITH THE REWRITE NAMED.
#
# WHY THE ACT EXISTS. MEASURED 2026-10-12: verify_handoffs refused - "decisions_registry: config/decisions.yaml
# is declared append_only but its receipted bytes are not a prefix of the current bytes (rewritten)". Byte-exact
# bisect: commit d149809 (2026-10-10) edited one `state:` cell at line 573 AND inserted 52 lines (D-2905/D-2907/
# D-2908) at line 15,585; commit 3db009e (2026-10-12) re-serialised the whole registry. The rail was RIGHT and
# had no remedy that was not a quiet re-hash: --backfill re-cuts EVERY declared path (moving baselines nobody
# measured as broken) and remembers nothing. This act is the missing remedy, and its two refusals are what make
# it unusable as a laundry: it cannot run where the measured state is a legal append or an unchanged file, and
# where it does run it must publish the commits that moved the bytes and the decision that ordered them.
# ----------------------------------------------------------------------------------------------------------

DECISIONS_REGISTRY: Path = REPO / "config" / "decisions.yaml"
REBASELINE_ORIGIN: str = "rebaseline"

#: The fields a re-baseline publishes BESIDE the measured ones. Declared once and read twice (the act builds
#: its `extra` from the same shape the control asserts), because a key set typed in two places is the drift this
#: repo keeps re-finding (C12/D-274a).
REBASELINE_META_FIELDS: tuple[str, ...] = ("because", "supersedes_bytes_at", "supersedes_bytes",
                                          "supersedes_sha256", "rewrite_named", "reason")


def rebaseline_extra(old_sha: str, old_bytes: int, because: str, commits: list[str], where: str) -> dict:
    """The supersession a re-baseline publishes, in ONE place: what it replaced, by whom, on whose order.

    A re-baseline that published only a new digest would be a quiet re-hash (D-382/BUG-535): the journal would
    carry the new bytes and lose the fact that the old claim was ever broken. These fields ARE that fact, and
    `supersedes_bytes_at` is empty only when NO store re-derives the superseded bytes - the limit named rather
    than left to read as "the old bytes are gone and nobody said so" (D-403/BUG-488).
    """
    return {
        "because": str(because),
        "supersedes_bytes_at": str(where),
        "supersedes_bytes": int(old_bytes),
        "supersedes_sha256": str(old_sha),
        "rewrite_named": [str(c) for c in commits],
        "reason": "the receipted region was REWRITTEN IN PLACE (" + str(old_bytes) + " B at " + str(old_sha)[:16]
                  + "); re-baselined by " + str(because) + " so the rail re-arms on the new bytes - BUG-376",
    }


def decision_ids() -> set[str]:
    """The decision ids config/decisions.yaml declares - read from the ONE home, never re-declared (C12).

    A `--because` licence that cannot be checked is not a licence: if the registry is unreadable the act refuses
    rather than accepting an attribution it cannot verify (C16).
    """
    if not DECISIONS_REGISTRY.exists():
        raise SystemExit("FAIL-CLOSED (handoff): " + str(DECISIONS_REGISTRY.relative_to(REPO)) + " is absent - "
                         "the re-baseline licence (--because) names a decision record, and a licence that cannot "
                         "be checked is not one")
    doc = yaml.safe_load(DECISIONS_REGISTRY.read_text(encoding="utf-8")) or {}
    rows = doc.get("decisions") or []
    if not rows:
        raise SystemExit("FAIL-CLOSED (handoff): " + str(DECISIONS_REGISTRY.relative_to(REPO)) + " declares no "
                         "record, so no --because could ever be checked (C16)")
    return {str(r.get("id")) for r in rows if isinstance(r, dict)}


def superseded_bytes_at(digest: str, path: str, n: int) -> str:
    """The commit that RE-DERIVES a superseded digest for this path, as 'git:<sha>'; '' when none does.

    WHY THIS EXISTS. A re-baseline that published only a digest would move the claim onto bytes nobody can
    recover: the journal would say "de3acd30 was replaced" while de3acd30 became unverifiable prose. So the act
    asks git - the store that OUTLIVES an in-place rewrite - whether the superseded bytes are still a revision
    of this path (or a RETAINED PREFIX of one), and records WHERE they re-derive when they do (D-403: a claim
    about bytes points at bytes; BUG-488: a superseded revision is still verifiable rather than quotable).
    MEASURED for the decisions_registry receipt of 979,096 B: commit 98471a36 holds exactly those bytes.
    """
    if not digest or n <= 0:
        return ""
    try:
        proc = subprocess.run(["git", "log", "--format=%H", "--", path], cwd=REPO, capture_output=True, text=True)
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    for sha in proc.stdout.split():
        data = git_bytes(sha, path)
        if data is None or len(data) < n:
            continue
        if sha256_bytes(data) == digest or sha256_bytes(data[:n]) == digest:
            return "git:" + sha
    return ""


def rebaseline_problems(rec: dict | None, cur: bytes, head: bytes | None, because: str, commits: list[str],
                        decisions: set[str]) -> list[str]:
    """Every reason this re-baseline may NOT proceed; [] means the act is licensed (fail-closed, C16).

    THE ONE STATE THAT LICENSES IT. A re-baseline moves the bytes the receipt is taken over, so it may run ONLY
    where the receipt has ALREADY been measured `rewritten` - the state the rail reports as a BUG-376 fault.
    A legal append is what a prefix receipt is FOR, so re-baselining one would move a baseline nobody measured
    as broken (D-2642: a rail is repaired, never re-recorded quiet); a truncation LOSES records, so it is
    restored, never re-baselined. Both refusals are the act's licence to exist: it cannot be reached where no
    defect was measured, and where it is reached it must name the rewrite and its owner.
    """
    problems: list[str] = []
    if rec is None:
        problems.append("there is no prior receipt for this path: a re-baseline SUPERSEDES a receipt, so it "
                        "cannot invent one - run --backfill for a first receipt (origin=backfill is honest "
                        "labelling) and re-baseline only a MEASURED rewrite")
    else:
        state, why = prefix_state(cur, rec)
        if state in ("unchanged", "appended"):
            problems.append("the receipted bytes are still a " + state.upper() + " of the live file, so nothing "
                            "was rewritten and there is nothing to re-baseline (" + why + ") - a baseline moved "
                            "where nobody measured a break is a quiet re-record (D-2642)")
        elif state == "truncated":
            problems.append("the live file is SHORTER than the receipted region (" + why + ") - a truncation "
                            "loses records, so it is RESTORED, never re-baselined")
    if not str(because or "").strip():
        problems.append("--because <D-id> is required: an in-place edit of an append_only artifact is a RULE, "
                        "and a rule with no home is a favour (C12/D-2655) - the act must be owned by a decision")
    elif str(because) not in decisions:
        problems.append("--because " + str(because) + " names no record in " + str(DECISIONS_REGISTRY.name)
                        + " - an act attributed to a decision that does not exist is an unattributable act")
    if not commits:
        problems.append("at least one --commit <sha> is required: a rewrite that is INVISIBLE to the receipt is "
                        "the whole defect (BUG-376), so the act publishes the commits that made it")
    if head is None:
        problems.append("this path has no bytes at git HEAD, so the live bytes are not a revision of it - a "
                        "receipt over bytes no declared store holds is the BUG-559 shape")
    elif sha256_bytes(cur) != sha256_bytes(head):
        problems.append("the live bytes are NOT the bytes of this path at git HEAD (uncommitted): COMMIT the "
                        "declared in-place edit first, because a receipt taken over a dirty worktree is "
                        "UNREVISIONED by the rail's own join rule (BUG-559) - so the two steps cannot be fused "
                        "into one invocation")
    return problems


def rebaseline(artifact: str, because: str, commits: list[str], apply: bool = False) -> int:
    """`--rebaseline <artifact>`: re-cut the receipt over the live bytes, NAMING what it supersedes (D-2971).

    THE DECLARED SEQUENCE (three obligations, and the third is automatic): (1) the in-place edit is COMMITTED;
    (2) the receipt is re-cut over the committed bytes, carrying the superseded digest, the commits that moved
    it and the decision that ordered it; (3) the rail RE-ARMS on the new region, so the next in-place edit is a
    fault again - which is the only way a rail that has fired stays worth having. Preview is the default.
    """
    cfg = config()
    spec = next((s for s in (cfg.get("artifacts") or []) if str(s.get("id")) == str(artifact)), None)
    if spec is None:
        raise SystemExit("FAIL-CLOSED (handoff): " + str(artifact) + " is not declared in config/handoffs.yaml"
                         "#artifacts - the act re-cuts a DECLARED receipt, because an undeclared path has no "
                         "mutability rule to preserve")
    paths = paths_of(spec)
    if len(paths) != 1:
        raise SystemExit("FAIL-CLOSED (handoff): " + str(artifact) + " declares " + str(len(paths)) + " path(s); "
                         "the act re-baselines ONE path at a time so the receipt it writes names exactly what it "
                         "moved - re-baselining several paths in one act would hide which region was rewritten")
    path = paths[0]["path"]
    full = REPO / path
    if not full.exists():
        raise SystemExit("FAIL-CLOSED (handoff): " + path + " does not exist - re-baselining an absent artifact "
                         "would append a claim about nothing")
    cur = full.read_bytes()
    rec = latest().get((str(artifact), path))
    problems = rebaseline_problems(rec, cur, git_bytes("HEAD", path), str(because), list(commits), decision_ids())
    if problems:
        raise SystemExit("FAIL-CLOSED (handoff): refusing to re-baseline " + path + ": " + "; ".join(problems))
    old_sha = str((rec or {}).get("sha256") or "")
    old_bytes = int((rec or {}).get("bytes") or 0)
    where = superseded_bytes_at(old_sha, path, old_bytes)
    extra = rebaseline_extra(old_sha, old_bytes, str(because), list(commits), where)
    print("PRE  receipted " + str(old_bytes) + " B sha256 " + old_sha[:16])
    if where:
        print("     the superseded bytes still RE-DERIVE from " + where + " (a revision, not a quotation)")
    else:
        print("     LIMIT NAMED: no revision of " + path + " re-derives those bytes, so the superseded claim is "
              "QUOTED, not re-derivable (D-403) - the act does not pretend otherwise")
    if not apply:
        print("PREVIEW (nothing written): re-run with --apply to append the superseding receipt")
        return 0
    new = receipt(str(artifact), spec, path, REBASELINE_ORIGIN, extra=extra)
    # THE RECEIPT MUST BE SEEN TO ARRIVE (BUG-587 class, one level up): a receipt that landed in the journal but
    # does not read back is a write nobody can verify, so the act re-reads it through the SAME reader the rail uses.
    back = latest().get((str(artifact), path)) or {}
    if (str(back.get("sha256") or "") != str(new.get("sha256") or "")
            or str(back.get("origin") or "") != REBASELINE_ORIGIN
            or str(back.get("supersedes_sha256") or "") != old_sha
            or str(back.get("because") or "") != str(because)):
        raise SystemExit("FAIL-CLOSED (handoff): the superseding receipt did NOT read back as written (sha "
                         + str(back.get("sha256"))[:16] + ", origin " + str(back.get("origin")) + ") - refusing "
                         "to report a re-baseline the journal does not carry")
    print("POST receipt " + str(new.get("bytes")) + " B sha256 " + str(new.get("sha256"))[:16] + " origin="
          + REBASELINE_ORIGIN + " supersedes=" + old_sha[:16] + " because=" + str(because) + " commits="
          + str(commits))
    print("NEXT (read-only): python3 scripts/verify_handoffs.py --check")
    return 0


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


def rebaseline_controls() -> list[tuple[str, bool]]:
    """Known-answer controls for the re-baseline act (BUG-492: a gate nobody has seen refuse is a comment).

    Every control below is synthetic - a control that calibrates a ruler must not write into it (BUG-491) - and
    the act is exercised through its PURE decision function, so the controls cost no journal append and no git
    call. The first row is the positive: an act that only ever refuses could not repair BUG-376 at all.
    """
    old = b"- id: D-1\n  state: PROPOSED\n"
    # A REAL rewrite for the fixture: SAME length, a byte inside the receipted region moved. `old + <record>` is
    # an APPEND, not a rewrite - a fixture that cannot distinguish the two would make the positive control below
    # pass through the wrong door (the reason this file's own control was repaired before it was trusted).
    body = old.replace(b"PROPOSED", b"RESOLVED")
    rec = {"bytes": len(old), "sha256": sha256_bytes(old), "mutability": "append_only"}
    head = body  # "the bytes of this path at git HEAD" ARE the live bytes in a licensed act (D-2971)

    def fires(cur: bytes, h: bytes | None, because: str, commits: list[str], decisions: set[str]) -> bool:
        """True when the act REFUSES to run (the only evidence the act has a gate)."""
        return bool(rebaseline_problems(rec, cur, h, because, commits, decisions))

    def publishes_supersession() -> bool:
        """True when the receipt the act would append NAMES its predecessor and touches no measured field."""
        extra = rebaseline_extra("ab" * 32, 5, "D-2971", ["d149809", "3db009e"], "git:98471a36")
        return (tuple(extra) == REBASELINE_META_FIELDS and extra["supersedes_sha256"] == "ab" * 32
                and extra["supersedes_bytes"] == 5 and extra["rewrite_named"] == ["d149809", "3db009e"]
                and extra["supersedes_bytes_at"] == "git:98471a36"
                and not (set(extra) & set(RECEIPT_MEASURED_KEYS)))

    def measured_field_refused() -> bool:
        """True when receipt() refuses an `extra` carrying a field it MEASURES - and refuses BEFORE the write.

        The refusal is the FIRST statement of receipt(), so nothing reaches the journal; the point of holding
        this control inside the sandbox (BUG-491) is that the claim is then MEASURED rather than argued: an
        append would move the sandbox journal and the byte-identity check below would fail.
        """
        try:
            receipt("selftest", {"id": "selftest", "mutability": "immutable", "paths": []}, "config/handoffs.yaml",
                    "selftest", extra={"sha256": "0" * 64})
        except ValueError:
            return True
        return False

    return [
        ("a MEASURED rewrite, named and owned, over the bytes at git HEAD is ACCEPTED - an act that refuses "
         "everything proves nothing", not fires(body, head, "D-2971", ["d149809"], {"D-2971"})),
        ("a legal APPEND is refused - nothing was rewritten, so there is no break to repair (D-2642)",
         fires(old + b"- id: D-2\n", head, "D-2971", ["d149809"], {"D-2971"})),
        ("an UNCHANGED file is refused", fires(old, head, "D-2971", ["d149809"], {"D-2971"})),
        ("a TRUNCATION is refused - records were lost, so it is restored, never re-baselined",
         fires(old[:-6], head, "D-2971", ["d149809"], {"D-2971"})),
        ("a --because that names no live decision is refused",
         fires(body, head, "D-9999", ["d149809"], {"D-2971"})),
        ("a MISSING --because is refused - an act with no owner is a favour (C12/D-2655)",
         fires(body, head, "", ["d149809"], {"D-2971"})),
        ("a MISSING --commit is refused - the rewrite would stay invisible, which is the whole defect (BUG-376)",
         fires(body, head, "D-2971", [], {"D-2971"})),
        ("bytes with NO revision at git HEAD are refused (the BUG-559 shape)",
         fires(body, None, "D-2971", ["d149809"], {"D-2971"})),
        ("bytes that DIFFER from git HEAD are refused - an uncommitted baseline is unrevisioned",
         fires(body, body + b"uncommitted", "D-2971", ["d149809"], {"D-2971"})),
        ("NO prior receipt is refused - a re-baseline supersedes one; it cannot invent one",
         bool(rebaseline_problems(None, body, head, "D-2971", ["d149809"], {"D-2971"}))),
        ("the supersession the act publishes carries what it REPLACED and touches no MEASURED field (a "
         "re-baseline that does not name its predecessor is the quiet re-hash D-382/BUG-535 forbids)",
         publishes_supersession()),
        ("an `extra` that would overwrite what the receipt MEASURED is refused BEFORE anything is written (C16)",
         measured_field_refused()),
    ]


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
            # D-2971: the re-baseline act's known answers, run INSIDE the sandbox (BUG-491) - one of them
            # (`an extra that overwrites a measured field`) calls receipt() and must be refused before any
            # append, so if the guard ever stopped firing, the journal check below would SEE it grow.
            rebaseline_rows = rebaseline_controls()
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
    failed = [name for name, ok in rebaseline_rows if not ok]
    for name in failed:
        print("FAIL handoff selftest (re-baseline act): " + name + " - the act's gate did NOT fire")
    if failed:
        print("FAIL handoff selftest: " + str(len(failed)) + " of " + str(len(rebaseline_rows))
              + " re-baseline control(s) did not fire - the act that repairs BUG-376 is unvalidated (BUG-492)")
        return 1
    print("ok handoff selftest: a rewrite changes the digest (the meter detects drift); SANDBOXED in a temp dir "
          "(2 receipt(s) + 1 blob), production journal byte-identical (" + str(pre)[:16] + ") - BUG-491; and the "
          "re-baseline act fires on all " + str(len(rebaseline_rows)) + " known answers (a MEASURED rewrite with "
          "an owner and named commits is accepted; an append, an unchanged file, a truncation, an unowned or "
          "uncommitted rewrite and a receiptless path are all refused)")
    return 0


def main() -> int:
    """CLI: --backfill (receipts + seals), --rebaseline (the D-2971 act) or --selftest (the known-answer control)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--seal-revisions", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rebaseline", metavar="ARTIFACT",
                    help="re-cut a receipt whose region was MEASURED rewritten, naming what it supersedes")
    ap.add_argument("--because", default="", help="the decision id that orders the re-baseline (required)")
    ap.add_argument("--commit", action="append", default=[], help="a commit that rewrote the region (repeatable)")
    ap.add_argument("--apply", action="store_true", help="append the superseding receipt (default: preview)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.rebaseline:
        return rebaseline(a.rebaseline, a.because, a.commit, apply=a.apply)
    if a.seal_revisions:
        return seal_revisions()
    if a.backfill:
        return backfill()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
