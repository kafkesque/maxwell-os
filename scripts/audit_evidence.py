#!/usr/bin/env python3
"""THE EVIDENCE AUDITOR — the one verdict here that is not a test written AFTER a bug.

WHY THIS EXISTS (BUG-935). On 2026-10-18 the applier's control battery was 63/63 GREEN, and ONE `--dry-run` over
the owner's real signed plan found FOUR bugs in a single command (BUG-930..933). Every one of those controls had
been written after its bug, so the suite could prevent a recurrence and could never find a new one: detection was
O(examples), discovery was O(imagination). What found them was not a test — it was the ACCUMULATED EVIDENCE
disagreeing with what the code had declared.

So this reads the evidence itself — every receipt, every plan, every signature — and re-proves it against the
declarations in config. Its input grows each time the pipeline runs, so unlike the controls it gets STRONGER with
use rather than merely longer. Each check is a CLASS derived from a declaration, never an example:

  VOCABULARY   a receipt's state must be one the applier declares (an undeclared state is a row no reader can place)
  AUTHORITY    a receipt line must name the plan digest and the signature that authorised it, and the signature must
               still be ON FILE (BUG-925: a signature overwritten in place left a whole run proving an authority
               that could not be produced)
  PRESENT      a row that says the corpus holds the work must have the work on disk (--deep: and the same bytes)
  TWIN         a `duplicate_of_admitted` row must name a twin that exists (an erased twin is a silent deletion)
  NOTHING-LEFT a row that says nothing was left must not leave an object NO receipt accounts for (BUG-932's shape:
               the target exists and the accounting says the door never wrote it)
  ONE-WORK     one target must never have been admitted with two DIFFERENT digests — a silent overwrite is the one
               fault that loses an owner's bytes without any message
  SIGNATURE    every signature on file must still resolve: plan present, digest equal, scope recomputed equal

Exit: 0 the evidence agrees with the declarations | 2 FINDINGS (a reading is owed, never a failure) | 1 unreadable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import apply_admission as adm

CLEAN, UNREADABLE, FINDINGS = 0, 1, 2


def state_roles(decl: dict[str, Any]) -> dict[str, list[str]]:
    """The DECLARED meaning of each state — which assert bytes are in the corpus, which are twins, which left nothing.

    Fail-closed by design (D-3034): a role this block omits is FATAL, never a silent "not checked" — an auditor
    that quietly skips a class reads exactly like an auditor that found nothing.
    """
    block = decl.get("state_roles")
    if not isinstance(block, dict) or not block:
        raise adm.ApplierError(
            f"FATAL: {adm.POLICY}#source_library.admission.applier.state_roles is not declared — what a state "
            f"ASSERTS must come from the declaration, never from this auditor (C12)"
        )
    roles: dict[str, list[str]] = {}
    for role in ("admitted", "duplicate", "absent", "requires", "removal"):
        values = block.get(role)
        if values is None:
            raise adm.ApplierError(f"FATAL: state_roles declares no {role!r} — that role would go UNCHECKED")
        if not isinstance(values, list):
            raise adm.ApplierError(f"FATAL: state_roles[{role!r}] is not a list — a role is a set of states")
        #: `removal` MAY BE EMPTY AND THAT IS THE POINT: an empty list is the DECLARED fact that this vocabulary
        #: has no state for an object LEAVING the corpus. A verifier reported exactly that gap as an over-claim in
        #: this auditor ("says no receipt records a removal, never searches for one") — so the absence is now
        #: declared, searched for, and quoted. The day a `disposed` state is added, declaring it here is the whole
        #: change; every other role stays non-empty because an empty one would silently switch a check off.
        if not values and role != "removal":
            raise adm.ApplierError(f"FATAL: state_roles declares an EMPTY {role!r} — that role would go UNCHECKED")
        for value in values:
            if role != "requires":
                adm.declared_state(str(value), decl)  # a role may only name a state the receipt vocabulary carries
        roles[role] = [str(value) for value in values]
    return roles


def is_row(record: dict[str, Any]) -> bool:
    """A ROW is an act ('run' and 'summary' are the envelope) — the envelope asserts nothing about a work."""
    return bool(record.get("plan_row")) and bool(record.get("state"))


def disposed_by_receipt(decl: dict[str, Any]) -> set[str]:
    """Objects a RECEIPTED DISPOSITION removed from the corpus (D-3086, BUG-935).

    `scripts/dispose_s0_artifacts.py` moves wrong-shaped artefacts to a LOCAL pen and writes
    S0_ARTIFACT_DISPOSITION_*.applied.jsonl. An artefact whose verdict is `quarantine_and_reconvert` LEFT the corpus
    BY THAT ACT, so its path is a `removed` object — the disposition receipt is the removal record the admission
    vocabulary was missing (D-3036: a removal must be an act, and the act already wrote its receipt). `quarantine_refused`
    is deliberately NOT here: that verdict KEEPS the artefact in place (it has no container to re-derive from, C23).
    """
    prefix = decl.get("disposition_receipt_prefix")
    if not prefix:
        return set()
    base = adm.resolve_root(str(prefix))
    folder, stem = base.parent, base.name
    out: set[str] = set()
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob(f"{stem}*.applied.jsonl")):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("applied") and rec.get("verdict") == "quarantine_and_reconvert":
                    artefact = str(rec.get("artefact") or "").strip()
                    if artefact:
                        out.add(str(Path(artefact).resolve()))
        except (ValueError, OSError):
            continue
    return out


def audit_receipts(decl: dict[str, Any], roles: dict[str, list[str]], *, deep: bool) -> tuple[list[str], int]:
    """Re-prove every receipt line against the declarations. Returns (findings, rows_read)."""
    findings: list[str] = []
    records = adm.read_receipts(decl)
    rows = [record for record in records if is_row(record)]
    for record in records:
        if is_row(record):
            continue
        #: THE ENVELOPE IS NOT A ROW, AND A RECORD THAT IS NEITHER IS NAMED. A receipt line silently skipped is a
        #: line nothing checked, and it reads exactly like a clean one — the blind spot this auditor exists to close.
        if record.get("counts") or (record.get("plan_sha256") and record.get("accept")):
            continue
        findings.append(f"UNCLASSIFIED {record.get('_receipt')}: a record is neither a row (no plan_row) nor an "
                        f"envelope (no counts, no plan_sha256+accept) — nothing checked it")
    admitted_states = set(roles["admitted"])
    duplicate_states = set(roles["duplicate"])
    absent_states = set(roles["absent"])

    #: WHICH OBJECTS SOME RECEIPT ACCOUNTS FOR AS ADMITTED — the only legitimate reason an object exists while a
    #: later row says it left nothing (two works, one name: BUG-921's per-work key is the real remedy, this only
    #: refuses to call the coincidence a fault). BOTH halves count: an admitted row keeps its CONTAINER in the
    #: corpus on purpose (the copy is the work's home), so counting only the markdown made this auditor accuse 100+
    #: legitimate containers on its first run — an instrument that fires on the happy path is one nobody reads.
    accounted: set[str] = set()
    for row in rows:
        if row["state"] in admitted_states:
            for field in ("md_target", "container_target"):
                value = str(row.get(field) or "")
                if value:
                    accounted.add(value)

    #: OBJECTS A RECEIPT SAYS LEFT THE CORPUS, from the DECLARED `removal` role. It is empty today (nothing in the
    #: vocabulary records a removal), which is why a disappearance below is reported rather than assumed benign.
    removed: set[str] = set()
    for record in rows:
        if record["state"] in set(roles["removal"]):
            for field in ("md_target", "container_target"):
                value = str(record.get(field) or "")
                if value:
                    removed.add(value)
    #: A DISPOSITION IS ITS OWN REMOVAL RECEIPT (D-3086): the shape rule moved 57 artefacts to a LOCAL pen and wrote
    #: S0_ARTIFACT_DISPOSITION_*.applied.jsonl; fold those paths in so an `applied` receipt whose target later LEFT
    #: is read as `disposed`, never as a silent disappearance (BUG-935).
    removed |= disposed_by_receipt(decl)
    declared_states = {str(s) for s in decl["states"]}
    digests_by_target: dict[str, dict[str, str]] = {}

    signatures: dict[str, bool] = {}
    for record in rows:
        rel = str(record.get("plan_row"))
        if str(record["state"]) not in declared_states:
            #: A FINDING, NEVER A CRASH. This auditor's job is to NAME an undeclared state; raising here (the
            #: first version did, via `declared_state`) turned one bad receipt line into rc 1 "cannot read" and
            #: hid every other class behind it — a report that stops at the first fault reports nothing.
            findings.append(f"VOCABULARY {record.get('_receipt')}:{rel}: state {str(record['state'])!r} is NOT in "
                            f"the declared vocabulary — a row no reader can place")
            continue
        state = str(record["state"])
        where = f"{record.get('_receipt')}:{rel}"

        if state not in admitted_states and state not in duplicate_states and state not in absent_states:
            findings.append(f"VOCABULARY {where}: state {state!r} is declared but carries NO ROLE — nothing can "
                            f"check what it asserts")

        missing = [key for key in roles["requires"] if not str(record.get(key) or "").strip()]
        if missing:
            findings.append(f"AUTHORITY  {where}: the line names no {', '.join(missing)} — a receipt that cannot be "
                            f"tied to a signature authorises nothing (D-3036)")
        accept = str(record.get("accept") or "").strip()
        if accept:
            if accept not in signatures:
                signatures[accept] = adm.resolve_root(accept).is_file()
            if not signatures[accept]:
                findings.append(f"AUTHORITY  {where}: names the signature {accept!r}, which is NOT ON FILE — the "
                                f"receipt proves an authority that cannot be produced (BUG-925)")

        if state in admitted_states:
            raw_target = str(record.get("md_target") or "").strip()
            if not raw_target:
                findings.append(f"DISAPPEARED {where}: recorded {state!r} and carries NO md_target — an admission "
                                f"that names no object cannot be checked, proved or found")
            elif raw_target not in removed and not Path(raw_target).is_file():
                #: AN ADMISSION IS EVIDENCE OF A PAST ACT, so an absent object is not by itself a false receipt —
                #: it is an object that LEFT after {ts}, and the question is whether ANY act records the leaving
                #: (D-3036: an act that leaves no trace did not happen). MEASURED 2026-10-18: 57 admitted markdown
                #: files are gone, none exists under any name in the corpus, and NEITHER the receipts NOR
                #: governance/MUTATION_JOURNAL.jsonl (which records only document writes) names their removal —
                #: D-3086 disposed 58 wrong-shaped artefacts and the disposal left no admission trace.
                findings.append(
                    f"DISAPPEARED {where}: recorded {state!r} at {record.get('ts')} and {raw_target} is NOT on disk "
                    f"— the corpus LOST this work and no receipt records its removal (the declared vocabulary holds "
                    f"{len(roles['removal'])} state(s) for a removal: D-3036)")
            elif (deep and raw_target and (recorded := str(record.get("md_sha256") or ""))
                  and adm.sha256_bytes(Path(raw_target)) != recorded):
                findings.append(f"PRESENT    {where}: recorded md_sha256 {recorded[:12]}… but the file hashes "
                                f"{adm.sha256_bytes(Path(raw_target))[:12]}… — the bytes moved under the record")
            recorded = str(record.get("md_sha256") or "")
            if recorded and raw_target:
                digests_by_target.setdefault(raw_target, {})[recorded] = f"{where} at {record.get('ts')}"

        if state in duplicate_states:
            twin = str(record.get("duplicate_of") or "").strip()
            if not twin:
                findings.append(f"TWIN       {where}: recorded {state!r} and named no twin — the verdict has no object")
            elif not Path(twin).is_file():
                findings.append(f"TWIN       {where}: its twin {twin} does NOT exist — a duplicate of nothing is a "
                                f"deletion wearing a verdict")

        if state in absent_states:
            for field in ("md_target", "container_target"):
                object_path = str(record.get(field) or "").strip()
                if object_path and Path(object_path).is_file() and object_path not in accounted:
                    findings.append(
                        f"NOTHING-LEFT {where}: recorded {state!r} and {field} EXISTS at {object_path} with NO "
                        f"receipt accounting for it — the corpus holds an object the door says it never wrote")

    for target, digests in digests_by_target.items():
        if len(digests) > 1:
            named = "; ".join(f"{digest[:12]}… ({where})" for digest, where in sorted(digests.items()))
            #: WHAT IS MEASURED, NOT WHAT IS INFERRED: two different digests recorded against ONE target. That the
            #: later file replaced the earlier one is a consequence of the target being one path, not a separate
            #: observation — the message therefore reports the collision and leaves the conclusion to the reader.
            findings.append(f"ONE-WORK   {target}: two or more DIFFERENT digests were admitted to ONE target — the "
                            f"corpus cannot hold both, so the later admission replaced the earlier object. {named}")
    return findings, len(rows)


def audit_signatures(decl: dict[str, Any]) -> tuple[list[str], int]:
    """Every signature on file must still resolve — plan present, digest equal, scope recomputed equal (D-3072)."""
    base = adm.resolve_root(f"{decl['accept_prefix']}")
    folder, stem = base.parent, base.name
    findings: list[str] = []
    seen = 0
    if not folder.is_dir():
        return findings, seen
    for path in sorted(folder.glob(f"{stem}*{decl['accept_extension']}")):
        seen += 1
        try:
            plan_path = adm.acceptance_plan(path, decl)
            if plan_path is None or not plan_path.is_file():
                findings.append(f"SIGNATURE  {path.name}: names a plan that is NOT on file — the word resolves to "
                                f"nothing (D-3034)")
                continue
            adm.load_acceptance(path, plan_path, adm.sha256_bytes(plan_path), decl)
        except adm.ApplierError as exc:
            findings.append(f"SIGNATURE  {path.name}: {exc}")
    return findings, seen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deep", action="store_true",
                        help="also re-hash every admitted target (reads the corpus: cheap to ask for, never a default)")
    parser.add_argument("--json", action="store_true", help="print the findings as JSON (for a caller, not an owner)")
    args = parser.parse_args(argv)

    try:
        decl = adm.applier_policy(adm.census.policy(adm.POLICY))
        roles = state_roles(decl)
        receipt_findings, rows_read = audit_receipts(decl, roles, deep=args.deep)
        signature_findings, signatures_read = audit_signatures(decl)
    except adm.ApplierError as exc:
        print(f"CANNOT READ {exc}")
        return UNREADABLE

    findings = receipt_findings + signature_findings
    if args.json:
        print(json.dumps({"rows": rows_read, "signatures": signatures_read, "findings": findings}, indent=2))
    else:
        print(f"READ      {rows_read} row(s) and {signatures_read} signature(s) from the accumulated evidence")
        for finding in findings:
            print(f"FINDING   {finding}")
        if findings:
            print(f"\n{len(findings)} finding(s) — the evidence and the declarations DISAGREE. Each line names one "
                  f"object; none of them is a batch failure (rc 2 = a reading is owed, BUG-457)")
        else:
            #: WHAT WAS ACTUALLY CHECKED, stated with the verdict: "CLEAN" that quietly omits the checks it did not
            #: run is the same lie as a banner promising an exit code (BUG-934), one level up.
            checked = (f"{rows_read} receipt row(s), {signatures_read} signature(s)"
                       + (", every admitted target re-hashed" if args.deep else ", targets verified on disk only "
                          "(--deep adds the hashes and reads the corpus)"))
            print(f"CLEAN     everything checked agrees with the declarations in config — checked: {checked}")
    return FINDINGS if findings else CLEAN


if __name__ == "__main__":
    sys.exit(main())
