#!/usr/bin/env python3
"""Re-derive the fields that DESCRIBE config/decisions.yaml - in the census, never in the registry.

BUG-402 (owner-approved 2026-09-23) established that total_decisions, the summary block, the content stamp
(decisions_sha256_16) and written_by are REDUNDANT DERIVED DATA: they MUST equal values computed from the
decisions list, which is the single source of truth. D-2655 (2026-09-26) then moved them OUT of
config/decisions.yaml, because that file declares mutability: append_only and its handoff receipt is a PREFIX
rule: the receipted bytes must remain a prefix of the bytes on disk. Every field above changes on every mint,
so NO position inside an append-only file is compatible with that rule - the mint's mid-file insert was the
SYMPTOM (BUG-539), not the disease.

WHERE THEY LIVE NOW. config/decisions_summary.json (the census), declared in config/artifact_ownership.yaml and
registered in config/derivations.yaml. It is a PURE FUNCTION of the registry bytes: it carries no generation
timestamp, so re-running this script on an unchanged registry is a byte-identical no-op (a volatile field in a
compared document makes every comparison a false witness). config/decisions.yaml is now RECORDS ONLY and its
records list extends to end-of-file, so:

    --mint <file|-> [--apply]       APPENDS validated record(s). The append is CHECKED (the new text must have
                                    the old text as a prefix), which is exactly what the append-only receipt
                                    demands; the census is rewritten in the same invocation. D-2660: the record's
                                    OWN FIELDS are joined to reality FIRST - the id is the next free one, its bugs
                                    exist in governance/bug_status.json, its payload NAMES its own bugs, every cited
                                    file EXISTS, and a whole-payload clone of a record on disk is REFUSED.
    --selftest                      run the MINT gate's known-answer controls (BUG-492); a control that has never
                                    been seen to fire is a comment. Wired into just health.
    --strip-derived-head [--apply]  the ONE-SHOT migration that removed the derived head and the summary block
                                    by BYTE SPLICE, so the record bytes were never re-rendered.

BUG-402 design note: a timestamp alone is a DECLARATION, not a control - a human can edit it and no tool can
verify it. The stamp is therefore CONTENT-derived: decisions_sha256_16 is the sha256 (16 hex chars) of the
canonical JSON of the decisions list, so it proves WHAT was written, not just WHEN. A WHEN belongs in an
append-only journal (the handoff receipts, the write journal), which cannot lie about the past because it is
never rewritten. --check fails on a missing or mismatched stamp, which is what lets just health catch drift
loudly instead of silently (D-355).

Modes:
    (default)   re-derive the census and repair ONLY it; a registry that is not records-only is a NAMED refusal
    --check     exit 1 if the registry shape or the census has drifted (no write) - wired into just health
    --mint      see above
    --strip-derived-head    see above (one-shot; already applied 2026-09-26)

IMPORTANT - this is NOT tools/sync_decisions.py. That tool treats DECISION-LOG.md as the source
of truth, which is INVERTED: DECISION-LOG.md has ~154 heading blocks vs 736 decision records here,
so running it would corrupt hand-curated records via its "No heading in DECISION-LOG.md" fallback
and heuristic state/category detection. It is now a hard-fail stub (BUG-402).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.write_guard import OWNED_ANY, write_document  # noqa: E402 - D-401/I1 (C6: crash-safe registry write)
from lib import yaml_guard  # noqa: E402 - D-2648: verify the bytes before writing them

DECISIONS_YAML = ROOT / "config" / "decisions.yaml"
#: The writer name declared in config/artifact_ownership.yaml - DERIVED, never typed twice.
WRITER = Path(__file__).resolve().relative_to(ROOT).as_posix()

# Canonical state keys (lowercased in the summary block), in stable order so the
# summary renders consistently and future diffs are minimal.
STATES: list[str] = [
    "PROPOSED",
    "DRAFT",
    "ACTIVE",
    "STALE",
    "SUPERSEDED",
    "ARCHIVED",
    "REJECTED",
    "DEFERRED",
    "RESOLVED",
    "OPEN",   # in use by 17 record(s) but UNDECLARED until 2026-09-25 (BUG-483)
    "RATIFIED",   # in use by 15 record(s) but UNDECLARED until 2026-09-25 (BUG-483)
    "PLANNED",
    # D-2645 (2026-09-25): the WHOLESALE states of the revocation ontology. A whole-record withdrawal is a
    # STATE (counted here); revoking ONE SCOPE of a live decision is a SUB-FACT on the record, never a state -
    # D2205's roadmap stays ACTIVE while ONE of its migrations is revoked. Declared here because
    # config/decisions_policy.yaml#revocation.whole_record_states names them, and two declarations of one fact
    # is the defect D-2646 forbids: vocabulary_problems() joins the two and fails on a mismatch.
    "REVOKED",
    "ABANDONED",
]

WRITTEN_BY: str = "scripts/recompute_decision_summary.py"
STAMP_KEYS: tuple[str, ...] = ("decisions_sha256_16", "written_by")
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"

#: D-2655: the census LEAVES the append-only registry and lives here (config/*.json is inside may_touch;
#: governance/*.json is NOT - a plan may not be widened so an assistant may write it, BUG-528/BUG-445).
CENSUS_JSON = ROOT / "config" / "decisions_summary.json"
CENSUS_SCHEMA_VERSION: str = "1.0"
#: Every key a reader MUST be able to find: an absent one is an error, never a default (D-2644/BUG-487).
CENSUS_REQUIRED_KEYS: tuple[str, ...] = (
    "schema_version",
    "source_path",
    "source_sha256",
    "written_by",
    "decisions_sha256_16",
    "total_decisions",
    "summary",
)


def normalized_id(record: dict) -> str:
    """Return the record's id with the dash spelling collapsed: `D-331` and `D331` are ONE token (C21)."""
    return str(record.get("id") or "").strip().replace("D-", "D").upper()


def canonical_state(record: dict) -> str:
    """Return the record's canonical state, or FAIL CLOSED (BUG-483).

    The previous `or "ACTIVE"` default silently re-labelled 62 of 766 records - 59 carried their state
    under a legacy `status:` key and 3 carried none - so the census block was wrong while the rail
    reported "in sync". A defaulted ruler is not a ruler (D-404); an uncounted record is not a record.
    """
    raw = record.get("state")
    if raw is None or not str(raw).strip():
        legacy = sorted(set(record) & {"status", "decision_state"})
        raise SystemExit(
            f"FAIL-CLOSED (BUG-483): decision {record.get('id')!r} carries no canonical 'state:' key "
            f"(legacy keys present: {legacy or 'none'}) - it would be silently counted as ACTIVE. "
            f"Normalise the record; do not re-introduce a default."
        )
    state = str(raw).strip().upper()
    if state not in STATES:
        raise SystemExit(
            f"FAIL-CLOSED (BUG-483): decision {record.get('id')!r} state {raw!r} is not canonical; "
            f"one of {STATES}"
        )
    return state


POLICY_YAML = ROOT / "config" / "decisions_policy.yaml"


def vocabulary_problems() -> list[str]:
    """Join the canonical STATE vocabulary to the revocation ontology's DECLARED states (D-2646).

    A rule about which whole-record states exist has exactly ONE implementation. If the policy declares a state
    this vocabulary cannot count, a record carrying it would be counted as nothing while the rail printed
    "in sync" - the BUG-483 shape (a defaulted ruler is not a ruler). So the join fails LOUDLY in both
    directions, and an ABSENT rules file is the error rather than a default (D-2644).
    """
    if not POLICY_YAML.exists():
        return [POLICY_YAML.relative_to(ROOT).as_posix() + ": absent - the revocation ontology's RULES file is "
                "missing, so the state vocabulary cannot be joined to anything (D-2645)"]
    policy = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
    revocation = policy.get("revocation") or {}
    if "whole_record_states" not in revocation:
        return [POLICY_YAML.relative_to(ROOT).as_posix() + "#revocation.whole_record_states: not declared - the "
                "set of whole-record states must be declared where a reader can FAIL on it (D-2644)"]
    problems: list[str] = []
    for state in [str(v).strip().upper() for v in (revocation.get("whole_record_states") or [])]:
        if state not in STATES:
            problems.append(
                POLICY_YAML.relative_to(ROOT).as_posix() + " declares whole-record state " + repr(state)
                + " that the canonical vocabulary does not carry - add it to STATES or drop the rule "
                "(two declarations of one fact is the defect, D-2646)"
            )
    return problems


def record_problems(decisions: list) -> list[str]:
    """Well-formedness: duplicate normalised ids, duplicate spellings of the same fact, missing fields."""
    problems: list[str] = []
    seen: dict[str, list[str]] = {}
    for d in decisions:
        seen.setdefault(normalized_id(d), []).append(str(d.get("id")))
        if "status" in d:
            problems.append(
                f"{d.get('id')}: carries a redundant legacy 'status:' key alongside 'state:' - one fact in "
                f"two places with nothing reconciling them (BUG-483/RC-2)"
            )
        # Only the fields the census and the id namespace DEPEND on are required. `title` is NOT one of
        # them: ~558 records legitimately describe themselves with `description:`/`decision:` - asserting a
        # schema I cannot back is the same error this bug is about (a declaration not grounded in reality).
        if not str(d.get("id") or "").strip():
            problems.append("a record carries no id - it cannot be cited, counted, or reconciled")
        if not str(d.get("category") or "").strip():
            problems.append(f"{d.get('id')}: no 'category' - it would be silently filed under GOV")
    for key, spellings in seen.items():
        if len(spellings) > 1:
            problems.append(f"duplicate decision id {key} under {spellings} (C21: one token, one namespace)")
    return problems


def decisions_digest(decisions: list) -> str:
    """Return the 16-hex-char content digest of the decisions list (BUG-402).

    The digest is taken over the RECORDS ONLY, never over the file, so writing the stamp cannot
    change the value it stamps.
    """
    payload = json.dumps(decisions, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def recompute(data: dict) -> tuple[int, dict, str]:
    """Return (total, summary, decisions_digest) computed from data["decisions"]."""
    decisions = data.get("decisions") or []
    total = len(decisions)

    state_counts: dict[str, int] = {s.lower(): 0 for s in STATES}
    category_counts: dict[str, int] = {}
    for d in decisions:
        state = canonical_state(d).lower()
        state_counts[state] = state_counts.get(state, 0) + 1
        category = d.get("category")
        if not str(category or "").strip():
            raise SystemExit(
                f"FAIL-CLOSED (BUG-483): decision {d.get('id')!r} carries no 'category' - it would be "
                f"silently filed under GOV, so the by_category census would be wrong (D-404)"
            )
        category_counts[category] = category_counts.get(category, 0) + 1

    summary: dict = {
        "total": total,
        **state_counts,
        "by_category": dict(sorted(category_counts.items())),
    }
    return total, summary, decisions_digest(decisions)


def census_document(data: dict, total: int, summary: dict, digest: str, registry_text: str) -> dict:
    """The D-2655 census artifact: a PURE FUNCTION of the registry bytes, so a re-run is a no-op (D-2646).

    WHY A SECOND FILE EXISTS AT ALL. config/decisions.yaml is append_only and its handoff receipt is a PREFIX
    rule: the receipted bytes must be a prefix of the bytes on disk. `total_decisions`, `summary`,
    `decisions_sha256_16` and `last_sync` ALL change on every mint, so NO position inside an append-only file is
    compatible with a prefix rule while a derived value lives there (BUG-539) - the mint's mid-file insert is the
    symptom, not the disease. The census therefore leaves the registry.

    `source_sha256` is the sha256 of the WHOLE registry file, so a reader can prove WHICH bytes this document
    describes (D-382: a pin is bytes-on-disk -> digest, never a remembered string). NO generation timestamp is
    carried: a volatile field in a compared document makes every comparison a false witness. `last_sync` was REMOVED from this document in D-2655 HALF B for
    the same reason: a WHEN belongs in an append-only journal (the handoff receipts, the write journal),
    which cannot lie about the past because it is never rewritten. Post-D-2655 this document is the ONLY
    home of the census: the registry carries no derived field at all.

    `written_by` is the DECLARED writer of record for this artifact (config/artifact_ownership.yaml), which is
    this script - two declarations of one fact are joined here rather than trusted twice.
    """
    return {
        "schema_version": CENSUS_SCHEMA_VERSION,
        "source_path": DECISIONS_YAML.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(registry_text.encode("utf-8")).hexdigest(),
        "written_by": WRITER,
        "decisions_sha256_16": digest,
        "total_decisions": total,
        "summary": summary,
    }


CENSUS_COMPARED_KEYS: tuple[str, ...] = tuple(k for k in CENSUS_REQUIRED_KEYS if k != "source_path")


def census_text(document: dict) -> str:
    """Render the census deterministically: fixed key order, 2-space indent, trailing newline."""
    ordered = {key: document[key] for key in CENSUS_REQUIRED_KEYS}
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def census_problems(document: dict, path: Path = CENSUS_JSON) -> list[str]:
    """Drift between the census ON DISK and the census DERIVED from the registry (D-2655, D-2646).

    ABSENT is the error, never an empty census (BUG-487): a derived artifact nobody can read is a defect that
    must fail loudly, and 'nothing found' has never been 'clean' here. Every broken shape gets a NAMED refusal,
    because 'exit != 0' alone cannot tell a named refusal from a traceback (the BUG-541/BUG-544 class). The key
    SET is checked in BOTH directions: a key this writer does not derive cannot be compared, so it is NAMED
    rather than ignored - an undetected extra key is how a stale count survives every comparison.
    """
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = str(path)   # out-of-tree (a control fixture): DECIDE, never raise (BUG-541)
    if not path.exists():
        return [rel + ": ABSENT - the registry's derived census has no home on disk; re-derive it with "
                + WRITER + " (a missing derived artifact is a defect, never an empty one - BUG-487)"]
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [rel + ": UNREADABLE (" + type(exc).__name__ + "): " + str(exc)]
    try:
        on_disk = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [rel + ": does not parse as JSON at line " + str(exc.lineno) + " column " + str(exc.colno)
                + " (" + exc.msg + ")"]
    if not isinstance(on_disk, dict):
        return [rel + ": is a " + type(on_disk).__name__ + ", not a mapping - the census is a document"]
    missing = [k for k in CENSUS_REQUIRED_KEYS if k not in on_disk]
    if missing:
        return [rel + ": declares no " + ", ".join(repr(k) for k in missing) + " - a census missing a key cannot "
                "be compared field by field, and a defaulted census is not a census (D-2644)"]
    stray = sorted(k for k in on_disk if k not in CENSUS_REQUIRED_KEYS)
    if stray:
        return [rel + ': carries key(s) ' + str(stray) + ' that this writer does not derive - it emits exactly '
                + str(len(CENSUS_REQUIRED_KEYS)) + ' key(s) in a fixed order, so an extra key came from a hand '
                'edit or from an older schema, and a census nobody derives is how a stale count survives every '
                'comparison (D-2646/BUG-540). Re-derive with ' + WRITER]
    problems: list[str] = []
    for key in CENSUS_COMPARED_KEYS:
        if on_disk.get(key) != document.get(key):
            problems.append(rel + "." + key + ": declared " + str(on_disk.get(key)) + ", actual "
                            + str(document.get(key)) + " - re-derive with " + WRITER)
    return problems


def write_census(document: dict) -> None:
    """One crash-safe write of the census, verified against the bytes on disk (C6).

    `backup=False` is deliberate and declared: this artifact is derived_regenerable, so its pre-image is
    regenerable by its own contract (write_document's own words); the write still records the pre-image it
    replaced in the journal, which is what R-D410 requires of derived output - a pre-image is kept for a
    record, not for output that a deterministic re-run recreates byte for byte.
    """
    write_document(CENSUS_JSON, census_text(document), writer=WRITER, owned_keys={OWNED_ANY}, backup=False,
                   journal=True)
    post = census_problems(document)
    if post:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the census does not re-derive after writing: "
                         + "; ".join(post))


REGISTRY_DERIVED_KEYS: tuple[str, ...] = (
    "total_decisions", "summary", "last_sync", "decisions_sha256_16", "written_by",
)


def registry_shape_problems(data: dict) -> list[str]:
    """The POST-D-2655 contract of config/decisions.yaml: RECORDS ONLY, and the records well formed.

    D-2655 HALF B (2026-09-26). The derived fields left this file because it is append_only and its handoff
    receipt is a PREFIX rule, while total_decisions / summary / last_sync change on every mint - no position
    inside an append-only file is compatible with that (BUG-539). The ABSENCE of those keys is therefore not
    "nothing to check": it IS the contract, and a key that comes back is DRIFT, because the next mint would have
    to move bytes inside the receipted region. A rule that can never fire would be a comment (BUG-540), so this
    one was SEEN to refuse: with total_decisions restored to a copy of the registry, --check exits 1 naming it.
    """
    problems: list[str] = []
    back = sorted(k for k in REGISTRY_DERIVED_KEYS if k in data)
    if back:
        problems.append("derived key(s) " + str(back) + ": config/decisions.yaml is append_only with a PREFIX"
                        " receipt, so a derived field inside it makes every mint a mid-file rewrite"
                        " (BUG-539/D-2655) - the census is config/decisions_summary.json"
                        " (run: --strip-derived-head to restore the declared shape)")
    records = data.get("decisions")
    if not isinstance(records, list) or not records:
        problems.append("decisions: not a non-empty list of records - an empty registry is a defect, never an"
                        " empty success (BUG-487)")
        return problems
    problems.extend(record_problems(records))
    problems.extend(vocabulary_problems())
    return problems

def _diff(data: dict, total: int, summary: dict, digest: str) -> list[str]:
    """The PRE-D-2655 head check: LIVE ONLY as the one-shot strip's precondition (D-2655 HALF B).

    Post-strip this file carries no derived field, so there is nothing here to diff. It is kept, and
    kept honest, because --strip-derived-head must refuse to migrate a header that is ALREADY wrong.
    """
    problems: list[str] = []
    if data.get("total_decisions") != total:
        problems.append(
            f"total_decisions: declared {data.get('total_decisions')!r}, actual {total}"
        )
    declared = data.get("summary") or {}
    for key, actual in summary.items():
        if key == "by_category":
            declared_cats = declared.get("by_category") or {}
            all_keys = sorted(set(declared_cats) | set(actual))
            for ck in all_keys:
                if declared_cats.get(ck) != actual.get(ck):
                    problems.append(
                        f"summary.by_category[{ck!r}]: declared "
                        f"{declared_cats.get(ck)!r}, actual {actual.get(ck)!r}"
                    )
        elif declared.get(key) != actual:
            problems.append(
                f"summary.{key}: declared {declared.get(key)!r}, actual {actual!r}"
            )
    # ONE-WAY IS NOT A JOIN (audit F6, MEASURED 2026-09-25): iterating only over the DERIVED keys let a
    # declared key that is no longer canonical survive every run without a word, so a state removed from the
    # vocabulary would keep reporting a count nobody re-derives. Removal may not happen by silence (D-2645).
    for stray in sorted(k for k in declared if k not in summary):
        problems.append(
            f"summary.{stray}: declared but NOT a canonical key - a key the reader no longer derives must be "
            f"removed, not left reporting (D-2645/D-2646)"
        )

    # BUG-402 integrity stamp: a declaration with no writer cannot fail loudly, so it is checked.
    declared_digest = data.get("decisions_sha256_16")
    if declared_digest != digest:
        problems.append(
            f"decisions_sha256_16: declared {declared_digest!r}, actual {digest!r} "
            "(the record set changed or the stamp was hand-edited)"
        )
    if not str(data.get("last_sync") or "").strip():
        problems.append("last_sync: missing or blank (no sanctioned writer ran)")
    if data.get("written_by") != WRITTEN_BY:
        problems.append(
            f"written_by: declared {data.get('written_by')!r}, expected {WRITTEN_BY!r}"
        )
    # BUG-483: the well-formedness of the RECORDS is part of "in sync", so --check reports it.
    problems.extend(record_problems(data.get("decisions") or []))
    # D-2645/D-2646: the RULE side is part of "in sync" too - a policy state the vocabulary cannot count.
    problems.extend(vocabulary_problems())
    return problems


MINT_REQUIRED: tuple[str, ...] = ("id", "state", "category", "title", "decision")

# D-2660 - THE MINT GATE JOINS A RECORD'S OWN FIELDS TO REALITY. BUG-550 was a record that named the wrong
# module and the wrong bug and stayed invisible: every rail read a record's VERDICT, no rail read two of its
# FIELDS together. MEASURED 2026-09-26 on the 790 records already on disk: 559 carry no `title`, 128 name no
# payload key at all, 26 file citations do not resolve and one `files:` value is a comma-joined BLOB - so this
# rule is FORWARD-ONLY, applied at the MOMENT OF MINT. It never rewrites history (the registry is append_only
# and its receipt is a PREFIX rule, BUG-539) and it never counts it. Existence of a cited FILE is checked on
# the machine that mints: a citation is a claim about the tree NOW, and the mint is the moment it is authored.
MINT_BUGS_KEY: str = "bugs"
MINT_PAYLOAD_KEYS: tuple[str, ...] = ("title", "decision", "rationale", "measured", "description", "verification")
MINT_CLONE_PREFIX: int = 200
BUG_REGISTER: Path = ROOT / "governance" / "bug_status.json"


def bug_register_ids() -> set[str]:
    """Return every bug id the register carries, or FAIL CLOSED - a citation checked against nothing is unchecked."""
    if not BUG_REGISTER.exists():
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + BUG_REGISTER.relative_to(ROOT).as_posix()
                         + " is absent - a bug citation checked against nothing is a citation nobody checked (C16)")
    doc = json.loads(BUG_REGISTER.read_text(encoding="utf-8"))
    ids = {str(b.get("id")) for b in (doc.get("open") or []) if isinstance(b, dict)}
    ids |= {str(b) for b in (doc.get("closed") or [])}
    if not ids:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + BUG_REGISTER.relative_to(ROOT).as_posix()
                         + " carries no bug id - an EMPTY register would refuse every honest mint or, worse, "
                         "pass every dishonest one (D-2659: a store named by its CAUSE)")
    return ids


def next_free_decision_id(decisions: list) -> str:
    """Return D-<max+1>: an id is a POSITION in the namespace, so a mint may only extend it by one."""
    nums: list[int] = []
    for d in decisions:
        body = str(d.get("id") or "").strip()
        if body.startswith("D"):
            body = body[1:].lstrip("-")
            if body.isdigit():
                nums.append(int(body))
    if not nums:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the registry carries no D-NNNN id - the next free id "
                         "cannot be derived from an empty namespace (C16)")
    return "D-" + str(max(nums) + 1)


def payload_text(record: dict) -> str:
    """Return every prose field of one record, joined: the payload a CLONE would have copied verbatim (BUG-550)."""
    return " ".join(str(record.get(k) or "") for k in MINT_PAYLOAD_KEYS).strip()


def _file_list(record: dict) -> list[str]:
    """Return the cited files as a list of strings - anything else is NOT a list and is reported as such."""
    files = record.get("files")
    return [str(f) for f in files] if isinstance(files, list) else []


def _bug_list(record: dict) -> list[str]:
    """Return the cited bugs as a list of strings - anything else is NOT a list and is reported as such."""
    bugs = record.get(MINT_BUGS_KEY)
    return [str(b) for b in bugs] if isinstance(bugs, list) else []


def mint_validate(record: dict, decisions: list) -> list[str]:
    """Every reason a record may NOT be inserted - checked BEFORE a byte is written (D-2648/D-2649)."""
    problems: list[str] = []
    if not isinstance(record, dict):
        return ["the minted record is " + type(record).__name__ + ", not a mapping"]
    missing = [k for k in MINT_REQUIRED if not str(record.get(k) or "").strip()]
    if missing:
        problems.append("missing required key(s) " + str(missing) + " - the census and the id namespace depend on "
                        "them, so an incomplete record would be counted while saying nothing")
        return problems
    canonical_state(record)   # FAIL CLOSED on a non-canonical state (BUG-483) rather than miscount it
    norm = normalized_id(record)
    same = [str(d.get("id")) for d in decisions if normalized_id(d) == norm]
    if same:
        problems.append(record.get("id") + " is already minted as " + ", ".join(same)
                        + " - a registry that can hold one id twice cannot answer what is decided (C21)")
    if "status" in record:
        problems.append("carries a legacy `status:` key alongside `state:` - one fact in two places (BUG-483)")
    # D-2660 CLAUSE 1 - the id is the NEXT FREE id. A namespace is extended, never sampled: a skipped id is a hole
    # that cannot be told apart from a record somebody removed (C21), and BUG-550 was found by reading ids in order.
    expected = next_free_decision_id(decisions)
    if normalized_id(record) != normalized_id({"id": expected}):
        problems.append("id " + str(record.get("id")) + " is not the next FREE id (" + expected + ") - the mint "
                        "APPENDS, so an id that skips one is a hole indistinguishable from a deleted record (D-2660)")
    # CLAUSE 2 - the bugs it names EXIST in the register, and its own payload NAMES at least one of them. A record
    # whose payload names a bug it does not cite IS the BUG-550 signature (D-2659 carried BUG-542's rationale).
    bugs = _bug_list(record)
    if not [b for b in bugs if b.strip()]:
        problems.append("names no `bugs:` list - a decision that fixes nothing cannot be joined to the register "
                        "(D-2660)")
    else:
        known = bug_register_ids()
        unknown = [b for b in bugs if b not in known]
        if unknown:
            problems.append("cites bug(s) that are NOT in the register: " + ", ".join(unknown)
                            + " - register the bug BEFORE the decision that cites it, or the citation names nothing "
                            "(D-2660)")
        payload = payload_text(record)
        if payload and not any(b in payload for b in bugs):
            problems.append("its payload names NONE of its own bugs " + str(bugs) + " - the tell of a CLONED record "
                            "(BUG-550); a decision must say what it fixes")
    # CLAUSE 3 - every cited FILE exists, and `files` is a LIST. A comma-joined blob is one path that exists
    # nowhere: MEASURED on 1 of the 790 records on disk, which is why the rule is forward-only.
    files = _file_list(record)
    if not files:
        problems.append("names no `files:` list - a decision with no artifact cannot be joined to the tree (D-2660)")
    else:
        absent = [f for f in files if not Path(f).expanduser().exists()]
        if absent:
            problems.append("cites file(s) that do NOT exist: " + ", ".join(absent)
                            + " - a citation is a claim about the tree at the MOMENT OF MINT (D-2660)")
    # CLAUSE 4 - a WHOLE-PAYLOAD CLONE of a record already on disk is REFUSED. Same files AND same bugs AND the
    # same payload opening is not a coincidence: it is BUG-550, where a cloned record named the wrong module and
    # the wrong bug while EVERY rail stayed green, because no rail read two fields of one record together.
    mine = (sorted(files), sorted(bugs), payload_text(record)[:MINT_CLONE_PREFIX])
    for other in decisions:
        theirs = (sorted(_file_list(other)), sorted(_bug_list(other)),
                  payload_text(other)[:MINT_CLONE_PREFIX])
        if mine[2] and mine == theirs:
            problems.append("is a WHOLE-PAYLOAD CLONE of " + str(other.get("id")) + " (same files, same bugs, same "
                            "payload opening) - that is the BUG-550 signature, not a coincidence (D-2660)")
            break
    return problems



def arrival_problems(total_before: int, decisions_after: list, minted_ids: list[str]) -> list[str]:
    """BUG-587 (D-2690): every minted id must be a TOP-LEVEL record, and the count must move by the mint size.

    WHY. MEASURED 2026-09-27: a hand-rolled append of ONE record to config/decisions.yaml added 32 lines and
    deleted none - and the census did NOT move (819 records, last D-2688). A record's files: items emit at indent
    2, the SAME column a record's own '- id:' marker takes when a writer re-indents the dumped block, so the new
    record parsed as ONE MORE ENTRY of the PREVIOUS record's files: list. The file LOADED, every rail stayed
    GREEN, and the decision was INVISIBLE. The write path validated the record BEFORE the write and re-derived
    the registry SHAPE after it - but nothing ever asked whether the mint ARRIVED. That is the BUG-492 class
    aimed at the registry: a write that cannot be SEEN to fail.

    Checked on the WOULD-BE bytes BEFORE the write, so a record that would be absorbed is REFUSED rather than
    landed invisibly, and again on the bytes ON DISK after it.
    """
    problems: list[str] = []
    expected = total_before + len(minted_ids)
    if len(decisions_after) != expected:
        problems.append("the registry holds " + str(len(decisions_after)) + " record(s) after the write, expected "
                        + str(expected) + " (" + str(total_before) + " before + " + str(len(minted_ids))
                        + " minted) - a mint that moves the count by anything else did NOT arrive (BUG-587)")
    top = top_level_ids(decisions_after)
    for minted in minted_ids:
        norm = normalized_id({"id": minted})
        hits = [t for t in top if t == norm]
        if not hits:
            problems.append(str(minted) + ": the minted id is NOT a TOP-LEVEL record after the write - the record "
                            "was ABSORBED into another record's list (its bytes are in the file, the file parses, "
                            "and the decision is invisible; MEASURED 2026-09-27, BUG-587)")
        elif len(hits) > 1:
            problems.append(str(minted) + ": appears " + str(len(hits)) + " time(s) as a TOP-LEVEL record, expected "
                            "exactly once - a registry that can hold one id twice cannot answer what is decided")
    return problems


def top_level_ids(decisions: list) -> list[str]:
    """The NORMALISED ids of the TOP-LEVEL records: an id nested inside a record's list is not a record (BUG-587)."""
    return [normalized_id(r) for r in decisions if isinstance(r, dict)]


def mint_controls() -> list[tuple[str, bool]]:
    """Known-answer controls for the D-2660 MINT gate (BUG-492: a detector nobody has seen fail is not a detector)."""
    live = (yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}).get("decisions") or []
    good = {
        "id": next_free_decision_id(live),
        "state": "OPEN",
        "category": "GOVERNANCE / RULES",
        "title": "control record - never written",
        "decision": "a control payload naming BUG-549 and scripts/recompute_decision_summary.py",
        "bugs": ["BUG-549"],
        "files": ["scripts/recompute_decision_summary.py"],
    }

    def rec(**kw) -> dict:
        """One mutated copy of the control record: a control must be able to fire on ONE field change."""
        base = dict(good)
        base.update(kw)
        return base

    def fires(record: dict) -> bool:
        """True when the gate REFUSES the record (the only evidence a gate exists)."""
        return bool(mint_validate(dict(record), live))

    last = live[-1] if live else {"id": "D-0"}
    # BUG-587: the ABSORBED shape - the minted record lands as ONE MORE ENTRY of the previous record's files: list.
    absorbed_after = live[:-1] + [dict(live[-1], files=list(_file_list(live[-1])) + [dict(good)])] if live else [dict(good)]
    skipped = "D-" + str(int(next_free_decision_id(live).split("-")[1]) + 1)
    return [
        ("the control record itself PASSES - a gate that refuses everything proves nothing", not fires(good)),
        ("an id that SKIPS the next free one fires", fires(rec(id=skipped))),
        ("an id already minted fires", fires(rec(id=str(last.get("id"))))),
        ("a bug that is NOT in the register fires", fires(rec(bugs=["BUG-9999"], decision="naming BUG-9999"))),
        ("no `bugs:` list fires", fires(rec(bugs=[]))),
        ("a payload naming NONE of its own bugs fires (the BUG-550 tell)",
         fires(rec(bugs=["BUG-549"], decision="a record about nothing in particular"))),
        ("a cited FILE that does not exist fires", fires(rec(files=["scripts/does_not_exist_9f3.py"]))),
        ("a comma-joined `files` BLOB fires", fires(rec(files="scripts/a.py, scripts/b.py"))),
        ("a WHOLE-PAYLOAD CLONE of the last record on disk fires",
         fires(dict(last, id=next_free_decision_id(live)))),
        ("a missing required key fires", fires(rec(title=""))),
        ("a mint that ARRIVES is accepted - the count moves by exactly the mint size and the id is TOP-LEVEL",
         not arrival_problems(len(live), live + [dict(good)], [good["id"]])),
        ("a mint whose id is ABSENT from the top level fires (the BUG-587 ABSORBED shape)",
         bool(arrival_problems(len(live) - 1, absorbed_after, [good["id"]]))),
    # BUG-590 (D-2690): the COUNT is landed EXACTLY here (len(live) - 1 before + 1 minted == len(absorbed_after)),
    # so this control can only PASS or FAIL through the TOP-LEVEL clause it names. MEASURED by the mutation gate:
    # with len(live) the control fired through the COUNT clause instead, and the arrival mutation could not be
    # seen to red it - a control whose NAME and REASON disagree is not a control (D-2676 iv, one level down).
        ("a minted id that lands TWICE as a top-level record fires",
         bool(arrival_problems(len(live) + 1, live + [dict(good), dict(good)], [good["id"]]))),
        ("a mint that does not move the count by its own size fires",
         bool(arrival_problems(len(live), live, [good["id"]]))),
    ]


def mint_selftest() -> int:
    """Run the mint gate's known-answer controls; return 1 if any control did NOT fire."""
    rows = mint_controls()
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [n for n, ok in rows if not ok]
    if failed:
        print("FAIL (" + WRITER + ") --selftest: " + str(len(failed)) + " of " + str(len(rows))
              + " known-answer control(s) did not fire - a mint gate nobody has seen refuse is a comment (BUG-492)")
        return 1
    print("ok (" + WRITER + ") --selftest: " + str(len(rows)) + "/" + str(len(rows))
          + " known-answer control(s) fire")
    return 0


def mint_main(argv: list[str]) -> int:
    """`--mint <file|-> [--apply]`: insert record(s) that were VALIDATED and RENDERED, never hand-typed.

    WHY (D-2648/D-2649). MEASURED 2026-09-26: two YAML artifacts were left unparseable inside one session by string
    surgery on YAML - one of them this registry, whose line 8667 carried a hand-written `decision:` value with an
    unquoted colon-space. The remedy for the WRITER is not a rule it must remember, it is a path where the failure
    cannot be authored: the record is dumped by the YAML emitter (which quotes what needs quoting), the resulting
    bytes are parsed back in full, and only then are they written through write_guard. A caller can still write a
    bad record BY HAND; it cannot make this path emit one. Preview is the default; --apply writes. The file is read
    as YAML, so the same path accepts JSON (JSON is a subset of YAML).
    """
    args = [a for a in argv[1:] if a not in ("--mint", "--apply")]
    unknown = [a for a in argv[1:] if a.startswith("--") and a not in ("--mint", "--apply")]
    if unknown or len(args) != 1:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): usage: --mint <record.yaml|record.json|-> [--apply]"
                         + (" - unknown flag(s) " + str(unknown) if unknown else "")
                         + " - one record file, refusing rather than guessing")
    raw = sys.stdin.read() if args[0] == "-" else Path(args[0]).read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    records = doc if isinstance(doc, list) else [doc]

    text = DECISIONS_YAML.read_text(encoding="utf-8")
    decisions = (yaml.safe_load(text) or {}).get("decisions") or []
    problems: list[str] = []
    for record in records:
        problems += [str(p) for p in mint_validate(record, decisions)]
    if problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the record was NOT written: " + "; ".join(problems))

    block = yaml.dump(records, default_flow_style=False, sort_keys=False, allow_unicode=True, width=110,
                      indent=2).rstrip(chr(10))
    # D-2655 HALF B: a mint is an APPEND, and it is checked as one rather than asserted. The registry is
    # records-only and extends to EOF, so the new bytes have the old bytes as a PREFIX - which is exactly what the
    # decisions_registry receipt demands. MEASURED BEFORE: the mid-file insert moved bytes inside the receipted
    # region and the rail reported the registry as 'rewritten' (BUG-539); a record appended after a later
    # top-level key is what left config/derivations.yaml unparseable (BUG-505), and records-only removes both
    # failure modes at once (there is no later top-level key).
    new_text = (text if text.endswith(chr(10)) else text + chr(10)) + block + chr(10)
    if not new_text.startswith(text):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the minted text is not an APPEND of the registry on disk, "
                         "so the append-only receipt could not survive it - refusing by construction (D-2655)")
    yaml_guard.assert_yaml(new_text, "config/decisions.yaml", WRITER)
    if "--apply" not in argv:
        print("PREVIEW (nothing written) - " + str(len(records)) + " record(s) would be inserted:")
        print(block)
        print("re-run with --apply to write, then the derived fields are recomputed in the same invocation.")
        return 0

    # ONE write (D-2648): the inserted record and the derived fields it invalidates go to disk TOGETHER.
    # MEASURED 2026-09-26 by this path's own first run: writing the record on its own left 784 records under a
    # 783 header, and the rail that caught it was the NEXT reader, not this writer.
    yaml_guard.assert_yaml(new_text, "config/decisions.yaml", WRITER)
    would_be = yaml.safe_load(new_text) or {}
    post = registry_shape_problems(would_be)
    if post:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the minted registry does not re-derive cleanly: "
                         + "; ".join(map(str, post)))
    write_document(DECISIONS_YAML, new_text, writer=WRITER, owned_keys={OWNED_ANY}, backup=True, journal=True)
    # D-2655: the census is derived from the registry, so a mint that moved the registry MUST carry the census
    # with it in the SAME invocation - otherwise the mint succeeds and leaves the second home describing bytes
    # that no longer exist, and the reader that catches it is the NEXT one (the D-2648 lesson).
    post_text = DECISIONS_YAML.read_text(encoding="utf-8")
    post_data = yaml.safe_load(post_text) or {}
    post_total, post_summary, post_digest = recompute(post_data)
    write_census(census_document(post_data, post_total, post_summary, post_digest, post_text))
    print("merged " + str(len(records)) + " record(s): " + ", ".join(str(r.get("id")) for r in records)
          + " - total=" + str(post_total) + ", stamp " + post_digest
          + ", census " + CENSUS_JSON.relative_to(ROOT).as_posix())
    return 0



STRIP_FLAG: str = "--strip-derived-head"


def strip_main(argv: list[str]) -> int:
    """ONE-SHOT (D-2655 HALF B): take the derived fields OUT of the append-only registry, by BYTE SPLICE.

    WHY A SPLICE AND NOT A REWRITE. The records are never re-rendered: the new text is
    `version/ratified + registry[decisions: up to the summary block]`, so the record BYTES are the bytes that were
    already on disk. The proof is the content stamp, which must not move (asserted below, not assumed); a YAML
    re-dump would have produced a NEW document that merely happens to parse - the D-2655 HALF A lesson.

    IT REFUSES UNLESS THE REGISTRY IS ALREADY COHERENT (C16, fail closed): the derived fields must re-derive with
    zero drift AND the census on disk must already describe these exact bytes. Stripping a registry whose header is
    already wrong would delete the disagreement instead of reporting it. A second run refuses as ALREADY STRIPPED.
    """
    if argv[1:] not in ([STRIP_FLAG], [STRIP_FLAG, "--apply"]):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): usage: " + STRIP_FLAG + " [--apply]")
    text = DECISIONS_YAML.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not [k for k in REGISTRY_DERIVED_KEYS if k in data]:
        print("ALREADY STRIPPED - nothing to do: the registry carries no derived key")
        return 0
    total, summary, digest = recompute(data)
    want = census_document(data, total, summary, digest, text)
    on_disk = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))
    bad = [k for k in ("written_by", "source_sha256", "total_decisions", "summary", "decisions_sha256_16")
           if on_disk.get(k) != want[k]]
    problems = _diff(data, total, summary, digest) + (
        ["census " + str(bad) + ": the census on disk does not describe these bytes, so the strip would delete a "
         "disagreement instead of reporting it"] if bad else [])
    if problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): refusing to strip a registry that is not ALREADY coherent: "
                         + "; ".join(problems))
    head_end = text.index(chr(10), text.index(chr(10)) + 1) + 1
    body_at = text.index(chr(10) + "decisions:" + chr(10)) + 1
    cut_at = text.rindex(chr(10) + "summary:")
    new_text = text[:head_end] + text[body_at:cut_at] + chr(10)
    stripped = text[head_end:body_at]
    post = yaml.safe_load(new_text) or {}
    post_total, post_summary, post_digest = recompute(post)
    if post_total != total or post_digest != digest:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the splice MOVED the records (" + str(total) + "->"
                         + str(post_total) + ", stamp " + digest + "->" + post_digest + ") - refusing")
    if registry_shape_problems(post):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the spliced text is not records-only: "
                         + "; ".join(registry_shape_problems(post)))
    print("PRE  " + str(len(text)) + " B sha256 " + hashlib.sha256(text.encode("utf-8")).hexdigest())
    print("DROP " + str(len(stripped)) + " B of derived head: " + stripped.replace(chr(10), " | "))
    print("DROP " + str(len(text) - cut_at) + " B of summary block")
    if "--apply" not in argv:
        print("PREVIEW (nothing written): re-run with --apply")
        return 0
    write_document(DECISIONS_YAML, new_text, writer=WRITER, owned_keys={OWNED_ANY}, backup=True, journal=True)
    disk = DECISIONS_YAML.read_text(encoding="utf-8")
    disk_data = yaml.safe_load(disk) or {}
    d_total, d_summary, d_digest = recompute(disk_data)
    write_census(census_document(disk_data, d_total, d_summary, d_digest, disk))
    print("POST " + str(len(disk)) + " B sha256 " + hashlib.sha256(disk.encode("utf-8")).hexdigest())
    print("     records " + str(d_total) + ", stamp " + d_digest + " (stamp UNMOVED: " + str(d_digest == digest)
          + ") - census re-derived from the bytes ON DISK")
    print("NEXT (same sitting): re-baseline the receipt, then --check")
    return 0


def main(argv: list[str]) -> int:
    """Recompute, --check, --mint a validated record, or --strip-derived-head; keep the census in step.

    D-2655 HALF B: the registry is RECORDS ONLY, so the steady-state repair below touches the CENSUS
    ONLY. A drifted registry is repaired by --mint (an APPEND) or by a person, never by a convenience
    write. The HALF A paragraph that follows is kept for the record of that reasoning.

    SELF-HEALING PER ARTIFACT (and this matters for the receipt). The write branch fixes ONLY what is actually
    wrong: a drift-free registry is NEVER rewritten, so the registry bytes do not move and the
    `decisions_registry` prefix receipt is untouched. Writing the registry whenever the census is merely absent
    would move `last_sync` on a healthy registry and turn that receipt into 'rewritten' - a repair that breaks a
    guarantee is not a repair.
    """
    if "--selftest" in argv:
        return mint_selftest()
    if "--mint" in argv:
        return mint_main(argv)
    if STRIP_FLAG in argv:
        return strip_main(argv)
    check_only = "--check" in argv
    text = DECISIONS_YAML.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    total, summary, digest = recompute(data)
    registry_problems = registry_shape_problems(data)
    census = census_document(data, total, summary, digest, text)
    problems = registry_problems + census_problems(census)

    if not problems:
        print(f"✅ {DECISIONS_YAML.relative_to(ROOT).as_posix()} is records-only (D-2655) — {total} decisions, stamp {digest}.")
        print(f"✅ {CENSUS_JSON.relative_to(ROOT).as_posix()} describes those exact bytes "
              f"({len(CENSUS_REQUIRED_KEYS)} key(s), source_sha256 {census['source_sha256'][:16]}).")
        return 0

    print(f"⚠️  {len(problems)} drift(s) detected:")
    for p in problems:
        print(f"   - {p}")

    if check_only:
        return 1

    # D-2655 HALF B: this branch repairs the CENSUS ONLY. It may never write the registry, because the registry
    # is append_only and the only write that preserves its prefix receipt is an APPEND - and the only sanctioned
    # append is --mint. A repair that breaks a guarantee is not a repair (BUG-539).
    if registry_problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the registry is not in its declared records-only shape, "
                         "and this branch may not rewrite an append_only artifact: " + "; ".join(registry_problems))
    write_census(census)
    print(f"✅ census written: {CENSUS_JSON.relative_to(ROOT).as_posix()} — {total} decisions, "
          f"stamp {digest}, source_sha256 {census['source_sha256'][:16]}")
    print(f"   (registry untouched: records-only and byte-identical, so its prefix receipt still holds)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
