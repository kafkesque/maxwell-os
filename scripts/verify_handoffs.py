#!/usr/bin/env python3
"""verify_handoffs.py - re-derive every handoff claim from the BYTES, never from the path (D-403).

Checks, each a declaration<->reality join (D-405):
  receipt_present   - every declared path carries a receipt, else the artifact is unprotected (owner-owed)
  path_present      - a receipted path that is now absent is DRIFT (the artifact the claim rests on was deleted)
  digest_current    - immutable / human_authored: bytes must be unchanged, else DRIFT
  prefix_intact     - append_only: the receipted bytes must be a byte-PREFIX of the current bytes, so a cell
                      edit or a truncation is caught without forbidding a legal append
  sealed            - a path declared seal must have a blob matching NOW, else the verified image is gone
  floors            - a journal or blob store BELOW its declared floor is DRIFT, never a 0-of-0 ok
                      (BUG-487 class: a rail that reads an absent registry reports green by vacancy)
  revision          - a digest quoted in prose may name a SUPERSEDED revision, so no live path holds those
                      bytes. A declared revision LOCATOR names a content-addressed store that still does; the
                      rail RE-DERIVES the digest from those bytes and fails closed if they disagree (BUG-488)
  identity          - every path carrying a role is joined to the file that DECLARES the role; a path whose
                      declaring file is gone is an assertion, not a declaration (BUG-488)
  hash_claim        - every 64-hex digest quoted in a declared document must resolve to bytes: a live declared
                      path or a declared revision. A digest resolving to NOTHING is DRIFT (D-403)
  cross_declaration - every digest this repo declares about a path (locks, supersession) must be a live digest
                      or a declared revision. An ORPHAN digest is DRIFT wherever it is declared, not only in
                      the documents this config names
  provenance        - every receipted (path, digest) is joined to a store that RE-DERIVES it: git HEAD, a declared
                      revision locator, or the RETAINED PREFIX of an append_only path (BUG-540). A receipt over
                      bytes no declared store can re-derive certified a FOREIGN body (BUG-559) and is refused;
                      the escapes are DECLARED in config/handoffs.yaml#receipt_provenance and joined to a live
                      receipt in both directions (an escape nobody can join is DRIFT, D-405)

Emits D-404 metric envelopes, so the numbers this rail reports travel with their ruler (I4).
--selftest is the known-answer control for the RESOLUTION meter (D-400/RC-5): a meter that resolves everything
and a meter that resolves nothing are both useless, so the control shows one negative and one positive.
Exit: 0 ok | 1 DRIFT | 2 owner-owed only (BUG-457 convention).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import handoff  # noqa: E402
from lib.measure import contaminant_drift, declared_resolver_metrics, emit_metric, min_records  # noqa: E402

REPO = handoff.REPO
HEX64 = re.compile(chr(92) + "b[0-9a-f]{64}" + chr(92) + "b")
FABRICATED = "0" * 63 + "1"  # no artifact in this repo can hash to this: the meter's known NEGATIVE


def current(path: str) -> tuple[str | None, int]:
    """Return (sha256, bytes) for a repo-relative path, or (None, 0) when the path is absent."""
    full = REPO / path
    if not full.exists():
        return None, 0
    return handoff.sha256_file(full), full.stat().st_size


def locators(cfg: dict) -> dict[str, dict]:
    """Declared revision locators keyed by digest: a SUPERSEDED revision that no live path holds."""
    return {str(loc.get("digest")): loc for loc in (cfg.get("revision_locators") or [])}


def live_digests(cfg: dict) -> set[str]:
    """Every digest currently on disk for a DECLARED handoff path: the live half of the resolution domain."""
    out: set[str] = set()
    for spec in cfg.get("artifacts") or []:
        for p in handoff.paths_of(spec):
            sha = current(p["path"])[0]
            if sha:
                out.add(sha)
    return out


def resolve(digest: str, live: set[str], loc: dict[str, dict]) -> str:
    """Classify a digest against the resolution domain: 'live', 'revision', or 'none' (D-403).

    The domain is what makes a hash claim checkable. It is deliberately NOT limited to the paths this config
    declares: a superseded revision is still bytes, and a store that still holds it is a legitimate referent.
    """
    if digest in live:
        return "live"
    if digest in loc:
        return "revision"
    return "none"


def blob_state(digest: str) -> str:
    """Verify a revision blob BY ITS BYTES: the blob NAME is a claim, so its content must re-derive it."""
    blob = handoff.blob_dir() / (digest + ".bin")
    if not blob.exists():
        return "absent"
    got = handoff.sha256_bytes(blob.read_bytes())
    return "ok" if got == digest else "corrupt (" + got[:16] + ")"


# THE APPEND_ONLY STATE RULE (BUG-540) NOW LIVES IN THE RECEIPT MODULE (D-2971). A receipt is a claim about
# bytes, so the states a receipted region can be in are handoff's subject: the re-baseline act must ask the
# identical question before it may move a baseline, and two implementations of one rule drift (D-274a). This
# rail MEASURES with handoff.prefix_state; that act REFUSES with it - one home, two callers.
# D-2972 moves the FINDING TEXT (the state, WHO moved the region, and the act that repairs it) to the same home as
# well: the controls assert on the sentence this rail prints, so a remedy cannot drift out of the rail while a test
# still believes it (BUG-746).


PROVENANCE_JOINS: tuple[str, ...] = ("head", "prefix", "revision", "declared")


def receipt_provenance(path: str, rec: dict, cur: bytes | None, head: str | None,
                       loc: dict[str, dict], declared: set[tuple[str, str]]) -> tuple[str, str]:
    """Decide whether the RECEIPTED bytes are RE-DERIVABLE, and name the store that re-derives them (BUG-559).

    A receipt is {path, digest, bytes, mutability, code_sha, stamp} about BYTES, and NOTHING in that record says
    those bytes are a revision of this repo or a declared derivation from one - so receipt() and --backfill
    could bless whatever a process found on disk. MEASURED (BUG-558): the workbook path held 92135 bytes
    (574aafef64f0cff7) that exist in NO revision of that path, and this rail reported "unchanged" because the
    receipt had been cut OVER them. The rail was not broken; it verified exactly what it was told. What was
    missing is the JOIN, and that is what this function decides. Returns (join, detail):

      head     - the receipted digest IS the digest of this path at git HEAD (the receipt is over a revision)
      prefix   - the path is append_only and the receipted bytes are its RETAINED PREFIX, so truncating the
                 live file to the receipted LENGTH re-derives them (the BUG-540 rule, already proven seen)
      revision - the digest is a declared revision locator for THIS path (its bytes re-derive from bytes_at)
      declared - named in config/handoffs.yaml#receipt_provenance.unrevisioned_declared, which must carry the
                 reason no store can hold them; the escape is a DECLARATION, never a default
      unrevisioned - none of the above: no declared store can re-derive the receipted bytes (refused)

    A same-length live copy is deliberately NOT a join: the live path is the SAME copy, so "the bytes are on
    disk and the receipt describes them" is exactly the circularity BUG-559 is about. Limit, named rather than
    hidden: a receipt over an EARLIER COMMITTED revision is reported unrevisioned, and the remedy is a revision
    locator - a locator is this repo's declared home for superseded bytes.
    """
    digest = str(rec.get("sha256") or "")
    if not digest:
        return "unrevisioned", "the receipt carries no digest at all"
    if head and digest == head:
        return "head", "the receipted bytes ARE the revision of this path at git HEAD (" + head[:16] + ")"
    ell = loc.get(digest)
    if ell is not None and str(ell.get("path") or "") == path:
        return "revision", ("declared revision locator " + digest[:16] + " re-derived from "
                            + str(ell.get("bytes_at")))
    n = int(rec.get("bytes") or 0)
    if str(rec.get("mutability") or "") == "append_only" and cur is not None and n > 0 and len(cur) > n:
        if handoff.sha256_bytes(cur[:n]) == digest:
            return "prefix", ("the receipted bytes are the RETAINED PREFIX of the live file (" + str(n) + " of "
                              + str(len(cur)) + " bytes), re-derived by truncation to the receipted length")
    if (path, digest) in declared:
        return "declared", "named in config/handoffs.yaml#receipt_provenance.unrevisioned_declared"
    return "unrevisioned", ("no declared store re-derives it: not the bytes of this path at git HEAD, not a "
                            "declared revision locator, not the retained prefix of an append_only path, and not "
                            "named in config/handoffs.yaml#receipt_provenance.unrevisioned_declared")


def check(record: bool = False) -> int:
    """Evaluate every declared artifact, print one line per finding, and return the tri-state exit code.

    BUG-660: `record` gates the metric emission. A health rail is a PROBE - it measures and reports, never
    writes. Publishing the three handoff metrics into the append-only governance/METRICS.jsonl is a RESOLVE
    act, so it is refused unless --record is given.
    """
    cfg = handoff.config()
    receipts = handoff.latest()
    loc = locators(cfg)
    drift: list[str] = []
    owed: list[str] = []
    checked = 0
    sealed = 0

    for spec in cfg.get("artifacts") or []:
        aid = str(spec.get("id"))
        for p in handoff.paths_of(spec):
            path = p["path"]
            rec = receipts.get((aid, path))
            checked += 1
            if rec is None:
                owed.append(aid + ": no receipt for " + path + " - unprotected (run handoff.py --backfill)")
                continue
            cur_sha, cur_bytes = current(path)
            if not rec.get("present"):
                print("  ok  " + aid + ": receipt records the path as ABSENT (a fact, not a failure)")
                continue
            if cur_sha is None:
                drift.append(aid + ": receipted " + path + " is ABSENT now - the artifact the claim rests "
                             "on was deleted")
                continue
            mut = str(rec.get("mutability") or "undeclared")
            if cur_sha == rec.get("sha256"):
                print("  ok  " + aid + ": " + path + " unchanged (" + cur_sha[:16] + ")")
            elif mut == "append_only":
                state, why = handoff.prefix_state((REPO / path).read_bytes(), rec)
                if state in ("unchanged", "appended"):
                    print("  ok  " + aid + ": " + path + " " + state.upper() + " (prefix intact, "
                          + str(rec.get("bytes")) + " -> " + str(cur_bytes) + " bytes)")
                else:
                    # D-2972: the finding TEXT (state, attribution, remedy) has ONE home in the receipt module, so
                    # the controls can assert on the very sentence this rail prints (BUG-746: the claim is the unit).
                    drift.append(handoff.unrepaired_region_finding(aid, path, state, why))
            elif mut == "derived_regenerable":
                print("  ok  " + aid + ": " + path + " REGENERATED by declaration (derived_regenerable)")
            else:
                drift.append(aid + ": " + path + " is declared " + mut + " and its bytes CHANGED ("
                             + str(rec.get("sha256"))[:16] + " -> " + cur_sha[:16] + ") - the claim no "
                             "longer describes the artifact it was taken over")
            if p["seal"]:
                if (handoff.blob_dir() / (cur_sha + ".bin")).exists():
                    sealed += 1
                    print("  ok  " + aid + ": sealed blob " + cur_sha[:16] + ".bin present")
                else:
                    drift.append(aid + ": " + path + " is declared seal: true but no blob " + cur_sha[:16]
                                 + " exists - the verified image does not survive a rewrite (BUG-376)")
            elif mut == "immutable" and not str(spec.get("no_seal_reason") or "").strip():
                owed.append(aid + ": " + path + " is immutable with seal: false and no declared "
                            "no_seal_reason - an unsealed immutable claim dies with its path")

    # RECEIPT PROVENANCE (BUG-559): join every receipted (path, digest) to a store that RE-DERIVES it, and
    # refuse a receipt over bytes no declared store can re-derive. The per-artifact loop above answers "do these
    # bytes still match the receipt"; this answers the question that loop cannot ask - "is the receipted body a
    # REVISION of anything at all". A receipt whose bytes resolve to no store certified a FOREIGN body.
    rp = cfg.get("receipt_provenance") or {}
    declared = {(str(e.get("path")), str(e.get("digest") or ""))
                for e in (rp.get("unrevisioned_declared") or [])}
    ceiling = int(rp.get("max_unrevisioned") or 0)
    joins: dict[str, int] = {}
    joined = 0
    seen_pairs: set[tuple[str, str]] = set()
    seen_escapes: set[tuple[str, str]] = set()
    for spec in cfg.get("artifacts") or []:
        aid = str(spec.get("id"))
        for p in handoff.paths_of(spec):
            path = p["path"]
            rec = receipts.get((aid, path))
            if rec is None or not rec.get("present"):
                continue
            seen_pairs.add((path, str(rec.get("sha256") or "")))
            cur_sha, _ = current(path)
            hb = handoff.git_bytes("HEAD", path)
            head = handoff.sha256_bytes(hb) if hb is not None else None
            cur = (REPO / path).read_bytes() if cur_sha else None
            join, detail = receipt_provenance(path, rec, cur, head, loc, declared)
            joins[join] = joins.get(join, 0) + 1
            if join == "declared":
                seen_escapes.add((path, str(rec.get("sha256") or "")))
            if join == "unrevisioned":
                owed.append("provenance: " + aid + " receipted " + path + " at "
                            + str(rec.get("sha256"))[:16] + " - UNREVISIONED (BUG-559): " + detail
                            + ". Remedy: land those bytes as a revision and declare a revision_locator, re-cut the"
                              " receipt over the committed revision, or - with a decision, and only when NO store"
                              " can hold the bytes - name it in config/handoffs.yaml#receipt_provenance")
            else:
                joined += 1
                print("  ok  provenance: " + aid + " -> " + join + " (" + detail + ")")
    # THE ESCAPE IS JOINED TO REALITY IN BOTH DIRECTIONS (D-405): a declaration no live receipt matches is an
    # assertion someone wrote once and nobody re-read. Measured both ways: frozen bytes make an escape stale.
    stale = sorted(declared - seen_escapes)
    if stale:
        drift.append("provenance: " + str([p for p, _ in stale]) + " is declared as unrevisioned in "
                     "config/handoffs.yaml#receipt_provenance but NO live receipt carries that (path, digest) - an"
                     " escape nobody can join is not a declaration (D-405)")
    if len(declared) > ceiling:
        drift.append("provenance: " + str(len(declared)) + " declared escape(s) exceed the SHRINK-ONLY census "
                     "max_unrevisioned " + str(ceiling) + " - adding an escape weakens the rule for every path, "
                     "so it takes a decision (config/handoffs.yaml) and two coordinated edits, not one")
    if record:
        emit_metric("handoff_receipts_revisioned", float(joined),
                    population="every receipted declared handoff path whose receipted digest is re-derivable",
                    denominator=joined + joins.get("unrevisioned", 0), ruler="config/handoffs.yaml",
                    note=str(joins.get("head", 0)) + " at git HEAD, " + str(joins.get("prefix", 0))
                         + " retained prefix, " + str(joins.get("revision", 0)) + " declared revision, "
                         + str(joins.get("declared", 0)) + " declared unrevisioned, "
                         + str(joins.get("unrevisioned", 0)) + " UNREVISIONED (BUG-559)")
    print("  ok  provenance: " + str(joined) + "/" + str(joined + joins.get("unrevisioned", 0))
          + " receipt(s) re-derivable (" + ", ".join(k + "=" + str(joins[k]) for k in PROVENANCE_JOINS if k in joins)
          + ("; unrevisioned=" + str(joins["unrevisioned"]) if joins.get("unrevisioned") else "")
          + "); " + str(len(declared)) + " declared escape(s) of census " + str(ceiling))

    # FLOORS (BUG-487 class): a rail that reads a journal or a blob store which does not exist must FAIL
    # CLOSED, because 0 of 0 reads as "ok" and an empty registry passes every check ever written. The numbers
    # now come from the ONE home for floors, config/evidence_floors.yaml (C12/C21) - a floor re-declared per
    # rail is the drift this file exists to prevent.
    floors = cfg.get("floors") or {}
    recs_all = handoff.read_receipts()
    cont_drift, cont_notes, n_rec, n_fixture = contaminant_drift(str(cfg.get("journal")), recs_all)
    drift.extend(cont_drift)
    min_rec = min_records(str(cfg.get("journal")))
    min_blobs = min_records(str(cfg.get("blob_dir")))
    blobs = sorted(handoff.blob_dir().glob("*.bin")) if handoff.blob_dir().exists() else []
    if min_rec < 1 or min_blobs < 1:
        drift.append("floors: " + str(cfg.get("journal")) + " / " + str(cfg.get("blob_dir")) + " has NO declared "
                     "floor in config/evidence_floors.yaml - a store with no floor cannot distinguish 'nothing "
                     "was missed' from 'nothing was read' (BUG-487). A stale `floors:` block in this rail's own "
                     "config is not a home: " + str(bool(floors)))
    else:
        if n_rec < min_rec:
            drift.append("floors: " + str(n_rec) + " receipt(s) in " + str(cfg.get("journal")) + " is below the "
                         "declared floor " + str(min_rec) + " - an absent or truncated journal is not a clean rail")
        if len(blobs) < min_blobs:
            drift.append("floors: " + str(len(blobs)) + " sealed blob(s) in " + str(cfg.get("blob_dir"))
                         + " is below the declared floor " + str(min_blobs) + " - the verified images are gone")
        print("  ok  floors: " + str(n_rec) + " receipt(s) >= " + str(min_rec) + ", " + str(len(blobs))
              + " blob(s) >= " + str(min_blobs) + " (declared in config/evidence_floors.yaml; "
              + str(n_fixture) + " control fixture record(s) EXCLUDED from the count: "
              + ("; ".join(cont_notes) if cont_notes else "none") + " - BUG-491)")

    # REVISION LOCATORS: a superseded revision is still bytes, and the rail re-derives it rather than trusting
    # the locator. This is the check that was missing when a superseded digest read as "resolves to nothing".
    for digest, ell in loc.items():
        kind, _, ref = str(ell.get("bytes_at") or "").partition(":")
        state = blob_state(digest)
        if state != "ok":
            owed.append("revision: " + digest[:16] + " (" + str(ell.get("state")) + ") has no verified blob ("
                        + state + ") - run: python3 scripts/lib/handoff.py --seal-revisions")
            continue
        sealed += 1
        if kind == "git":
            data = handoff.git_bytes(ref, str(ell.get("path")))
            if data is None:
                drift.append("revision: " + digest[:16] + " declares bytes_at git:" + ref + " but no bytes are "
                             "retrievable there - the locator points at nothing (D-403)")
                continue
            got = handoff.sha256_bytes(data)
            if got != digest:
                drift.append("revision: git:" + ref + " holds bytes hashing to " + got[:16] + ", declared "
                             + digest[:16] + " - the locator does not describe those bytes")
                continue
        live_sha = current(str(ell.get("path")))[0]
        print("  ok  revision: " + digest[:16] + " re-derived from " + str(ell.get("bytes_at")) + " (" + kind
              + "), state " + str(ell.get("state")) + ", live path now "
              + (live_sha[:16] if live_sha else "ABSENT"))
        if live_sha == digest:
            owed.append("revision: " + digest[:16] + " is declared " + str(ell.get("state")) + " but the live "
                        "path holds those bytes again - the declaration and the bytes disagree about which "
                        "revision is current")

    # IDENTITY: a role declared elsewhere is verifiable; a role asserted here is not. Join the two.
    for entry in cfg.get("identity_map") or []:
        path = str(entry.get("path"))
        decl = [str(d) for d in (entry.get("declared_by") or [])]
        if not (REPO / path).exists():
            owed.append("identity: " + path + " (" + str(entry.get("role")) + ") is absent from the worktree")
            continue
        missing = [d for d in decl if not (REPO / d).exists()]
        if missing:
            drift.append("identity: the role of " + path + " is declared by " + str(missing) + ", which does "
                         "not exist - a role with no declaring file is an assertion")
        else:
            print("  ok  identity: " + str(entry.get("role")) + " <- " + path + " ("
                  + str(len(decl)) + " declaring file(s) present)")

    quoted_total = 0
    unresolved_total = 0
    for claim in cfg.get("hash_claims") or []:
        doc = REPO / str(claim.get("document"))
        about = str(claim.get("about"))
        spec = next((s for s in (cfg.get("artifacts") or []) if str(s.get("id")) == about), None)
        if not doc.exists() or spec is None:
            owed.append("hash_claim: " + str(claim.get("document")) + " or target " + about + " unresolved")
            continue
        live = {current(str(p["path"]))[0] for p in handoff.paths_of(spec)}
        quoted = sorted(set(HEX64.findall(doc.read_text(encoding="utf-8"))))
        quoted_total += len(quoted)
        unresolved = [q for q in quoted if resolve(q, live, loc) == "none"]
        unresolved_total += len(unresolved)
        kinds = [q[:16] + ":" + resolve(q, live, loc) for q in quoted]
        print("  ok  hash_claim: " + doc.name + " quotes " + str(len(quoted)) + " digest(s) about " + about
              + " -> " + str(kinds))
        if unresolved:
            drift.append("hash_claim: " + doc.name + " quotes " + str(len(unresolved)) + " digest(s) that "
                         "resolve to NO bytes anywhere in the declared stores ("
                         + str([u[:16] for u in unresolved]) + ") - a hash claim must point at bytes, not at "
                         "a path (D-403)")

    # CROSS-DECLARATION: every digest this repo declares about a path is joined to bytes HERE, once, so an
    # orphan digest cannot survive by living in a config nobody re-derives.
    declared_total = 0
    live_all = live_digests(cfg)
    orphans: list[str] = []
    for cd in cfg.get("cross_declarations") or []:
        src = REPO / str(cd.get("file"))
        if not src.exists():
            drift.append("cross_declaration: " + str(cd.get("file")) + " is declared as a source of digests "
                         "but is absent - a declaration nobody can read is not a declaration")
            continue
        pairs: list[tuple[str, str]] = []
        structure = str(cd.get("structure"))
        if structure == "locks":
            data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
            for lock in data.get("instruments") or []:
                if lock.get("sha256"):
                    pairs.append((str(lock.get("path") or ""), str(lock.get("sha256"))))
                for sup in lock.get("superseded") or []:
                    if sup.get("sha256"):
                        pairs.append((str(lock.get("path") or ""), str(sup.get("sha256"))))
        elif structure == "named_digests":
            data = json.loads(src.read_text(encoding="utf-8"))
            for field in cd.get("fields") or []:
                if data.get(field):
                    pairs.append(("", str(data[field])))
        else:
            drift.append("cross_declaration: " + str(cd.get("file")) + " declares structure " + repr(structure)
                         + ", which no reader implements - a structure nobody reads is a blindspot")
            continue
        for path, digest in pairs:
            declared_total += 1
            live_here = current(path)[0] if path else None
            if live_here == digest or digest in live_all or resolve(digest, live_all, loc) == "revision":
                continue
            orphans.append(str(cd.get("file")) + ((" for " + path) if path else "") + " -> " + digest[:16])
    if orphans:
        drift.append("cross_declaration: " + str(len(orphans)) + " declared digest(s) resolve to NO bytes in "
                     "any declared store (orphan digest = the D-403 defect, wherever it is declared): "
                     + str(orphans))
    else:
        print("  ok  cross_declaration: " + str(declared_total) + " declared digest(s) across "
              + str(len(cfg.get("cross_declarations") or [])) + " source(s) all resolve to bytes")

    denom = quoted_total + declared_total
    # BUG-489: PUBLISH the resolution domain with the coverage. A finding may not name an artifact defective
    # without naming what was searched, so the domain is emitted in the envelope AND printed beside the rows.
    dom_text = declared_resolver_metrics().get("handoff_digests_resolved") or {}
    dom = {"identifier": dom_text.get("identifier"),
           "stores": [str(s.get("name")) for s in (dom_text.get("stores") or [])],
           "searched": denom, "resolved": denom - unresolved_total - len(orphans)}
    print("  domain handoff_hash_claims: " + str(dom["identifier"]) + " resolved against " + str(len(dom["stores"]))
          + " store(s) " + str(dom["stores"]) + " -> " + str(dom["resolved"]) + "/" + str(denom))
    if record:
        emit_metric("handoff_digests_resolved", float(dom["resolved"]),
                    population="every digest quoted by a declared hash claim and every digest declared about a "
                               "path in the cross-declaration sources",
                    denominator=denom, ruler="config/handoffs.yaml",
                    note=str(len(loc)) + " declared revision(s), " + str(unresolved_total) + " quoted digest(s) "
                         "unresolved, " + str(len(orphans)) + " orphan declared digest(s)",
                    domain=dom)
    dom_paths = declared_resolver_metrics().get("handoff_paths_unchanged") or {}
    domp = {"identifier": dom_paths.get("identifier"),
            "stores": [str(s.get("name")) for s in (dom_paths.get("stores") or [])],
            "searched": checked, "resolved": checked - len(owed)}
    print("  domain handoff_paths: " + str(domp["identifier"]) + " resolved against " + str(len(domp["stores"]))
          + " store(s) " + str(domp["stores"]) + " -> " + str(domp["resolved"]) + "/" + str(domp["searched"]))
    if record:
        emit_metric("handoff_paths_unchanged", float(domp["resolved"]),
                    population="declared handoff paths in config/handoffs.yaml", denominator=checked,
                    ruler="config/handoffs.yaml",
                    note=str(len(drift)) + " drift, " + str(len(owed)) + " owner-owed, " + str(sealed)
                         + " sealed blob(s)",
                    domain=domp)

    if drift:
        print(chr(10) + "FAIL verify_handoffs: a handoff claim no longer describes the bytes (D-403):")
        for d in drift:
            print("  !!", d)
        return 1
    if owed:
        print(chr(10) + "owner-owed (loud, not fatal - BUG-457):")
        for o in owed:
            print("  ->", o)
        return 2
    print(chr(10) + "ok verify_handoffs: " + str(checked) + " declared path(s), " + str(denom)
          + " digest(s) and " + str(len(loc)) + " revision(s) all agree with their bytes")
    return 0


def selftest() -> int:
    """Known-answer control for the RESOLUTION meter (D-400/RC-5): show it can say NO and can say YES.

    A resolution domain that accepts anything and one that accepts nothing are the same failure with different
    signs, so the control exercises both: a fabricated digest must resolve to 'none', and every declared
    revision must re-derive its declared digest from the store it names.
    """
    cfg = handoff.config()
    loc = locators(cfg)
    live = live_digests(cfg)
    ok = True
    if resolve(FABRICATED, live, loc) != "none":
        print("FAIL verify_handoffs selftest: a fabricated digest RESOLVED - the meter always says yes")
        ok = False
    if not loc:
        print("FAIL verify_handoffs selftest: no declared revision locator, so the positive half of the control "
              "(bytes recovered from a store that still holds them) is untested - the meter is unvalidated")
        ok = False
    for digest, ell in loc.items():
        kind, _, ref = str(ell.get("bytes_at") or "").partition(":")
        if kind != "git":
            print("FAIL verify_handoffs selftest: bytes_at store " + repr(kind) + " has no reader - the locator "
                  "is unverifiable by construction")
            ok = False
            continue
        data = handoff.git_bytes(ref, str(ell.get("path")))
        if data is None or handoff.sha256_bytes(data) != digest:
            print("FAIL verify_handoffs selftest: revision " + digest[:16] + " does not re-derive from "
                  + str(ell.get("bytes_at")))
            ok = False
    # BUG-540 CONTROL: the append_only rule must be SEEN to say YES to a legal append and NO to an
    # equal-length rewrite. MEASURED before this control existed: a one-byte append to config/decisions.yaml (a
    # legal append) was reported as tampering, so the rule could never pass - and it could not distinguish
    # tampering from "the old bytes were never retained" (BUG-492: a control never seen to fail is a comment,
    # and a rule never seen to pass is not a rule either).
    old = b"- id: D-1\n  state: PROPOSED\n"
    receipted = {"bytes": len(old), "sha256": handoff.sha256_bytes(old)}
    for label, cur, want in (
        ("an UNCHANGED file says yes", old, "unchanged"),
        ("a legal APPEND says yes", old + b"- id: D-2\n", "appended"),
        ("an EQUAL-LENGTH rewrite says no", old.replace(b"PROPOSED", b"RESOLVED"), "rewritten"),
        ("a TRUNCATION says no", old[:-6], "truncated"),
        ("a fabricated digest says no", old, "rewritten") if receipted["sha256"] == " " else
        ("a digest for OTHER bytes says no", old, "rewritten"),
    ):
        got, _why = handoff.prefix_state(cur, receipted if label.startswith(("an UNCHANGED", "a legal APPEND", "an EQUAL-LENGTH", "a TRUNCATION")) else
                                 {"bytes": len(old), "sha256": "0" * 64})
        if got != want:
            print("FAIL verify_handoffs selftest: " + label + " - the meter said " + repr(got)
                  + " instead of " + repr(want))
            ok = False
    # BUG-559 CONTROL, both directions. The PROVENANCE join must be SEEN to refuse a receipt over bytes no
    # declared store can re-derive, and SEEN to accept each of the four joins a legitimate receipt can have - a
    # rule never seen to fail is a comment, and a rule never seen to PASS is not a rule either (BUG-492).
    # Synthetic only: a control that calibrates a ruler must not write into it (BUG-491).
    body, older = b"alpha\nbeta\n", b"alpha\n"
    hid, oid = handoff.sha256_bytes(body), handoff.sha256_bytes(older)
    fake_loc = {"deadbeef" * 8: {"path": "p.csv", "bytes_at": "git:abc1234"}}
    decl = {("p.csv", FABRICATED)}
    for label, rec, cur, head, want in (
        ("a receipt over the bytes AT HEAD is accepted",
         {"sha256": hid, "bytes": len(body)}, body, hid, "head"),
        ("a receipt over a RETAINED PREFIX is accepted",
         {"sha256": oid, "bytes": len(older), "mutability": "append_only"}, body, hid, "prefix"),
        ("a receipt over a DECLARED REVISION is accepted",
         {"sha256": "deadbeef" * 8, "bytes": 9}, None, hid, "revision"),
        ("a NAMED unrevisioned receipt is accepted (the declared escape)",
         {"sha256": FABRICATED, "bytes": 9}, None, hid, "declared"),
        ("a receipt over a SAME-LENGTH live copy is REFUSED (the BUG-559 shape)",
         {"sha256": oid, "bytes": len(body), "mutability": "append_only"}, body, None, "unrevisioned"),
        ("a receipt over a FOREIGN body is REFUSED",
         {"sha256": "ab" * 32, "bytes": 9}, None, hid, "unrevisioned"),
        ("a receipt with NO digest is REFUSED", {"sha256": "", "bytes": 9}, None, hid, "unrevisioned"),
    ):
        got, _d = receipt_provenance("p.csv", rec, cur, head, fake_loc, decl)
        if got != want:
            print("FAIL verify_handoffs selftest: " + label + " - the join said " + repr(got) + " instead of "
                  + repr(want))
            ok = False
    # THE ESCAPE MUST BE JOINED IN BOTH DIRECTIONS (D-405): the live config's escapes are checked against the
    # live receipts here, so this control refuses the moment an escape stops describing a real receipt.
    rp = (cfg.get("receipt_provenance") or {})
    live_pairs = set()
    receipts = handoff.latest()
    for spec in cfg.get("artifacts") or []:
        for p in handoff.paths_of(spec):
            r = receipts.get((str(spec.get("id")), p["path"]))
            if r is not None:
                live_pairs.add((p["path"], str(r.get("sha256") or "")))
    declared_live = {(str(e.get("path")), str(e.get("digest") or ""))
                     for e in (rp.get("unrevisioned_declared") or [])}
    for pair in sorted(declared_live):
        if pair not in live_pairs:
            print("FAIL verify_handoffs selftest: the declared unrevisioned escape " + pair[0]
                  + " (" + pair[1][:16] + ") matches NO live receipt - either the receipt was re-cut and the "
                    "escape is stale, or the escape was written for bytes nobody receipted")
            ok = False
    if not declared_live:
        print("FAIL verify_handoffs selftest: no declared unrevisioned escape exists, so the positive half of the "
              "provenance control (an escape that IS joined to a live receipt) is untested - the rule is "
              "unvalidated in the direction that lets it pass")
        ok = False
    if ok:
        print("ok verify_handoffs selftest: a fabricated digest resolves to nothing (" + str(len(live))
              + " live digest(s), " + str(len(loc)) + " revision(s)), each declared revision re-derives its "
              "digest from the store it names, the provenance join accepts all FOUR joins (head/prefix/revision/"
              "declared) and refuses a same-length live copy, a foreign body and a digestless receipt, and every "
              "declared unrevisioned escape is joined to a live receipt (the meter can say no AND can say yes)")
    return 0 if ok else 1


def main() -> int:
    """CLI: --selftest (the meter's known-answer control) or the full rail, which has no weakening options."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true", help="read-only (default): report without publishing (BUG-660)")
    ap.add_argument("--record", action="store_true", help="publish the three handoff metrics (BUG-660)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return check(record=a.record)


if __name__ == "__main__":
    sys.exit(main())
