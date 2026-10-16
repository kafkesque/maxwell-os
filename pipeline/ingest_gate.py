#!/usr/bin/env python3
"""ingest_gate.py — the INGEST-SIDE identity gate (D-2997 / BUG-781).

WHY THIS EXISTS (measured, 2026-10-14). The identity machinery was NOT missing: detect_title_renames.py
(D-2736) and detect_same_work_content.py (D-2737) feed ONE owner ledger (governance/duplicate_adjudication.json,
D-2738) and verify_duplicate_gate.py --gate is a declared fail-closed reader — but it is declared POST-RUN only,
so NOTHING IN THE INGEST PATH READ IT. MEASURED: 59 adjudicable pairs, `adjudicated: 0`, oldest entry 2026-09-30,
while ingest continued. BUG-780 then measured the consequence: 530 of the 1,393 corroborated rows are ONE TEXT
under TWO NAMES (84 pairs), 369 of them served. The guarantee "a duplicate work may not enter the corpus" was a
DECLARATION with no enforcement point.

WHAT THIS IS — the missing enforcement point, and nothing else:
  * it does NOT re-detect (C12/D-2646: detection has ONE home — the two detectors, and their reports);
  * it does NOT merge, mark, rename or delete (D-2898: a work-identity label is an OWNER WORD; R-D410);
  * it READS the corpus identity census + the owner ledger + the detector reports and answers ONE question at
    the door: "may THIS candidate be ingested, given what the corpus already holds and what the owner ruled?"

THE DOOR IS DELTA-SCOPED (the cascade rule). Only files ABSENT from the metadata cache are candidates, so an
already-ingested file is NEVER re-classified here: no existing row, checkpoint, source_id or count can move
because of this gate. A deferred candidate is skipped IN PLACE — never deleted — named loudly, and recorded in
a deferral receipt under the declared runtime path.

TWO POINTS, ONE FUNCTION (declared in config): `pre_s0` (identity + bytes; no text needed) and `pre_s1_5`
(content report; the identity screen is strictly stronger once S0.5's author|title exists). The SAME rc means
two things BY DECLARATION: in `just health` rc 2 is owner-owed and NOT fatal (BUG-457); at the ingest door rc 2
REFUSES, because a run that proceeded would mint the claim the unresolved identity makes false.

TRI-STATE: 0 clean | 1 FATAL (a MACHINE-decidable defect: an unreadable input — a BLIND ingest is the defect
class this gate exists for — an unknown ledger verdict, a detector candidate the ledger never saw, or a
name-defect class with no declared disposition) | 2 OWNER-OWED (a pair with no owner word; a name-defect class
DECLARED owner_owed; or candidates that would be deferred right now). MEASURED 2026-10-16 (T-173, D-3043):
with the marker class ACCEPTED the last owner-owed item was this storage class, so the INGEST reading now
reads rc 0 — the refusal that remains is genuine IDENTITY ambiguity, which is what this tri-state was always
about, and the accepted class is still COUNTED and PRINTED.

THE READER'S LOOKUP IS DECLARED (T-130 option B, owner word 2026-10-16, BUG-799). The door declares 37 corpus
names DEFECTIVE (whitespace) while its own comparison key `_key()` ALREADY collapses that whitespace — so the
door was depending on the exact bytes of a name it calls defective (D-3034: a declaration the reader cannot
RESOLVE). Option B does two things and nothing else: the lookup becomes DECLARED and ORDERED
(`identity.record_lookup`) and the whitespace classes become DECLARED DEBT (printed, counted, never an rc 2
trigger) while the marker class kept a disposition of its own.

ONE WORD PER CLASS (D-3043, owner word 2026-10-16 "T-173 accept"). The marker class is now accepted too, and
acceptance is a WORD ABOUT A CLASS: the word, the row it names and the reason it is not a hazard are declared
ON the class they are about (`identity.accepted_debt.declarations`; `same_as` is a POINTER and must RESOLVE,
D-3034). Three things are FATAL: a class with no disposition, a disposition outside the vocabulary, and an
accepted class with no word OF ITS OWN. An accepted class stays COUNTED and PRINTED — the acceptance changes
the rc a class triggers, never its visibility: a class that goes quiet the moment it is accepted IS the
quiet green this gate exists to prevent.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from pipeline.book_metadata import (  # D2176/D2308/D2449 — identity + noise have ONE home
    compute_source_id,
    sanitize_source_book,
)
from pipeline.io_guard import load_jsonl  # D2332: the declared JSONL reader (never a second reader)
from pipeline.pipeline_paths import BOOKS_DIR, CHECKPOINT_DIR, PROJECT_ROOT
from pipeline.stamp import get_pipeline_commit

CONFIG_REL = "config/ingest_identity_gate.yaml"
METADATA_CACHE_NAME = "book_metadata.jsonl"  # origin: pipeline/stage0_5_extract_metadata.py::METADATA_CACHE
SUPPORTED_EXTENSIONS = (".md", ".epub", ".pdf")  # origin: pipeline/stage0_convert.py::SUPPORTED_EXTENSIONS
# MEASURED 2026-10-14 (this gate's first control run): compute_source_id's filename-fallback branch returns a
# BARE digest — there is no `unknown|` prefix to test for. Trusting the id's SHAPE as evidence of work identity
# admitted a file as its own duplicate; identity honesty is therefore decided by the SOURCE (a cache record
# carrying author AND title), never by the id. Any code that branches on an id prefix is reading a claim nothing
# writes (the BUG-511 class).
RECORD_SCHEMA_VERSION = "1.0"
HASH_CHUNK = 1 << 20

RC_CLEAN, RC_FATAL, RC_OWNER_OWED = 0, 1, 2


class GateInputError(RuntimeError):
    """A gate input that cannot be read. A BLIND ingest must never be admitted (C16)."""


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Load the gate policy. Every path, threshold and reading in this module comes from here (C12).

    Args:
        path: Optional override of the declared policy file (selftest uses a synthetic copy).

    Returns:
        The policy mapping, with the four required blocks validated.

    Raises:
        GateInputError: the policy file is absent or a required block is missing (fail closed).
    """
    cfg_path = Path(path) if path else PROJECT_ROOT / CONFIG_REL
    if not cfg_path.exists():
        raise GateInputError(f"gate policy missing: {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    for block in ("door", "identity", "ledger", "content"):
        if block not in data or not isinstance(data[block], dict):
            raise GateInputError(f"gate policy is missing the '{block}' block: {cfg_path}")
    return data


def policy_path(policy: dict[str, Any], *keys: str) -> Path:
    """Resolve a declared policy path: absolute stays absolute, relative resolves at the project root."""
    value = policy
    for key in keys:
        value = value[key]
    candidate = Path(str(value))
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def corpus_files(books_dir: str | Path | None = None) -> list[Path]:
    """Every ingestable file currently in the corpus root, sorted (deterministic order).

    Raises:
        GateInputError: the corpus root is absent — a gate over no corpus cannot certify anything.
    """
    root = Path(books_dir) if books_dir else BOOKS_DIR
    if not root.is_dir():
        raise GateInputError(f"corpus root missing: {root}")
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)


def cache_records(cache_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Read the metadata cache. Absent cache is FATAL, not empty: an identity gate with no identity is blind."""
    path = Path(cache_path) if cache_path else CHECKPOINT_DIR / METADATA_CACHE_NAME
    if not path.exists():
        raise GateInputError(f"metadata cache missing: {path} (a gate with no corpus identity is blind, C16)")
    return list(load_jsonl(path))


def _key(name: str) -> str:
    """The sanitized comparison key for a filename or stem. Sanitizing has ONE home (book_metadata D2449)."""
    return sanitize_source_book(str(name or "")).strip().lower()


LOOKUPS = ("exact_name", "exact_path", "canonical_name")
#: The DECLARED vocabulary of record-resolution methods (config#identity.record_lookup). A token outside it is
#: FATAL: a lookup this module cannot perform must never read as "the record is absent".
DISPOSITIONS = ("accepted_debt", "owner_owed")
#: The DECLARED vocabulary of a defect class's disposition (config#identity.defect_disposition). An undeclared
#: class or a token outside this tuple is FATAL - acceptance may never be acquired by omission (C16).
ACCEPTED_DEBT, OWNER_OWED = DISPOSITIONS

EXACT_METHODS = ("exact_name", "exact_path")
#: The lookups that name THE FILE ITSELF: a record found by one of these IS this corpus file. A record found by
#: any OTHER declared lookup is the same WORK reached through a variant name — a THIRD state the pre-B door
#: could not reach (its exact-bytes lookup could never find such a file), and now a recorded deferral rather
#: than an admission (T-130 option B / BUG-848: without it, the deferred rename of T-172 would re-ingest work
#: the store already holds).

NOT_FOUND = "none"
REASON_ALREADY_INGESTED = "already_ingested_by_canonical_name"
#: The deferral reason of the THIRD state (see decide_candidate): the work is already in the store under a
#: variant name. It is a code-level token like the other three reasons (same_work_identity, same_sanitized_stem,
#: byte_identical); declaring the reason VOCABULARY in config is a hardening this act does not perform and
#: records instead as a known limit (BUG-848).
#: The resolution the door reports when NO declared lookup answers. It is a NAME, never a blank: a receipt that
#: cannot say HOW a record was found cannot show that acceptance was safe (D-795: absent is never 0).


def lookup_order(policy: dict[str, Any] | None = None) -> list[str]:
    """The DECLARED, ORDERED record-resolution rule: the first lookup that answers WINS (T-130 option B).

    MEASURED BUG-799: the door declares 37 corpus names DEFECTIVE and resolved their records by EXACT BYTES,
    so accepting those names would have depended on the very bytes it calls defective: the door called a name
    defective and then asked that name to identify itself (D-3034). The rule lives in
    config/ingest_identity_gate.yaml, not here — and it governs the DECISION, never candidacy
    (identity.candidate_lookup, BUG-848).

    Raises:
        GateInputError: the declared order is empty, or names a lookup this module cannot perform (C12/C16).
    """
    pol = policy or load_policy()
    order = [str(token) for token in pol["identity"]["record_lookup"]]
    unknown = [token for token in order if token not in LOOKUPS]
    if not order or unknown:
        raise GateInputError(f"identity.record_lookup is undeclared or names an unknown lookup: {order} "
                             f"(declared vocabulary: {list(LOOKUPS)})")
    return order


#: The one counted class whose pattern lives at its OWN key (`identity.ingest_site_marker_pattern`) because its
#: remedy was a WRITE, not a rename. It is a COUNTED CLASS like any other, so `standing()` counts it once, in one
#: place, beside the pattern classes (T-173/D-3043) — a class counted in two homes is a class that drifts.
MARKER_CLASS = "ingest_site_marker"


def _resolve_declaration(raw: dict[str, Any], name: str, seen: tuple[str, ...] = ()) -> dict[str, Any] | None:
    """Follow an accepted-debt declaration's `same_as` pointer to the entry that carries the WORD.

    Returns None when NOTHING carries a word: no entry for the class, a pointer to an entry that does not exist,
    or a pointer CYCLE. A pointer must RESOLVE (D-3034) — "same_as" a class that was never declared is not an
    acceptance, and two classes pointing at each other accept nothing.
    """
    decl = raw.get(name)
    if not isinstance(decl, dict):
        return None
    target = str(decl.get("same_as") or "").strip()
    if not target:
        return decl
    if target in (name, *seen):
        return None
    return _resolve_declaration(raw, target, (name, *seen))


def undeclared_defect_dispositions(policy: dict[str, Any] | None = None) -> list[str]:
    """Every FAULT in the declared dispositions, as strings (empty = every counted class has a lawful one).

    Acceptance (T-130 option B, T-173/D-3043) is the riskiest thing this gate can read: a class that silently
    acquired the `accepted_debt` treatment would turn a NEW defect into a quiet green. THREE faults are reported
    here and treated as FATAL by `standing()` — an accepted class with no word OF ITS OWN, a `same_as` pointer
    that does not resolve, and a stale acceptance for a class that is not accepted at all. Acceptance must be a
    WORD about a CLASS: never a default, never a mood, never another class's word.
    """
    pol = policy or load_policy()
    declared = set(pol["identity"]["name_defect_patterns"]) | {MARKER_CLASS}
    dispositions = pol["identity"]["defect_disposition"]
    raw = (pol["identity"].get("accepted_debt") or {}).get("declarations") or {}
    faults: list[str] = []
    for name in sorted(declared):
        token = dispositions.get(name)
        if token is None:
            faults.append(f"{name}: no disposition declared")
        elif token not in DISPOSITIONS:
            faults.append(f"{name}: disposition {token!r} is outside {list(DISPOSITIONS)}")
        elif token == ACCEPTED_DEBT:
            decl = _resolve_declaration(raw, name)
            if decl is None or not str(decl.get("owner_word") or "").strip():
                faults.append(f"{name}: declared accepted_debt with NO owner word of its own - there is no "
                              f"declaration carrying a word for THIS class under "
                              f"identity.accepted_debt.declarations (a `same_as` pointer that does not resolve "
                              f"is not a word, D-3034): acceptance must be a WORD about THIS class, never a "
                              f"default")
    for name in sorted(raw):
        if dispositions.get(name) != ACCEPTED_DEBT:
            faults.append(f"{name}: an accepted-debt declaration for a class that is NOT declared "
                          f"accepted_debt (its disposition is {dispositions.get(name)!r}) - a stale acceptance "
                          f"resolves to nothing (D-3034)")
    return faults


def candidate_lookup(policy: dict[str, Any] | None = None) -> list[str]:
    """The DECLARED delta rule: which lookups may decide that a corpus file is NOT a candidate (BUG-848).

    CANDIDACY IS VISIBILITY, NOT IDENTITY. `pipeline/stage0_convert.py` converts the corpus MINUS the deferrals
    this gate names, so a file the delta rule absorbs is never decided, never recorded and never skipped — it is
    CONVERTED (the duplicate-work outcome the whole gate exists to prevent). MEASURED 2026-10-16: routing this
    rule through the canonical lookup made a noise-suffixed duplicate vanish, and a PRE-EXISTING control caught
    it. The canonical fallback therefore belongs to the DECISION, where a variant name becomes a recorded
    deferral grounded in identity instead of an invisible candidate.

    Raises:
        GateInputError: the candidate lookups are empty, unknown, or not a SUBSET of the declared record lookup
            — the only way back into the trap is to add `canonical_name` here, so that edit is a FAULT.
    """
    pol = policy or load_policy()
    declared = [str(token) for token in pol["identity"]["candidate_lookup"]]
    unknown = [token for token in declared if token not in LOOKUPS]
    outside = [token for token in declared if token not in lookup_order(pol)]
    if not declared or unknown or outside:
        raise GateInputError(f"identity.candidate_lookup is undeclared, unknown or outside record_lookup: "
                             f"{declared} (declared vocabulary: {list(LOOKUPS)}; record_lookup governs identity "
                             f"resolution and MUST contain the candidate lookups)")
    return declared


def honest_identity(record: dict[str, Any] | None) -> str:
    """The canonical source_id a cache record can HONESTLY support, or "" when it cannot.

    A record carrying author AND title is the only source of work identity this gate trusts (D2176/D2308).
    Everything else is a filename fallback: it is still computed (so the receipt shows what the file claims)
    but it is NEVER matched against the corpus, because a fallback key collapses names, not works.
    """
    if not record:
        return ""
    author = str(record.get("author") or "").strip()
    title = str(record.get("title") or "").strip()
    return compute_source_id(author, title) if author and title else ""


def fallback_identity(name: str) -> str:
    """The declared filename-fallback id (shown in the receipt; NOT usable as identity evidence)."""
    return compute_source_id("", "", fallback_key=_key(name))


def corpus_census(corpus: list[Path], records: list[dict[str, Any]],
                  policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """The corpus's identity census: canonical ids, sanitized stems, byte sizes, and the cache's own keys.

    THE LOOKUP IS DECLARED AND ORDERED (T-130 option B / BUG-799). Three indexes are built — exact name, exact
    path, and the CANONICAL key — and `resolve()` walks `identity.record_lookup` in order, returning WHICH
    lookup answered, so a receipt carries the EVIDENCE of how an identity was found rather than the assumption.
    The canonical index is what lets the door accept a whitespace-defective name SAFELY: `_key()` collapses
    exactly that defect, so the door can find the identity of a name it also calls defective (D-3034).
    """
    pol = policy or load_policy()
    order = lookup_order(pol)
    by_name: dict[str, dict[str, Any]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    by_key: dict[str, dict[str, Any]] = {}
    for rec in records:
        name = str(rec.get("source_book") or "").strip()
        if name:
            by_name.setdefault(name, rec)
            by_key.setdefault(_key(name), rec)
        raw_path = str(rec.get("source_path") or "").strip()
        if raw_path:
            by_path.setdefault(str(Path(raw_path).resolve()), rec)

    def resolve(path: Path, methods: list[str] | None = None) -> tuple[dict[str, Any] | None, str]:
        """Resolve ONE corpus file to its cache record: the FIRST lookup in `methods` that answers wins.

        `methods` defaults to the declared `identity.record_lookup`. The DELTA rule passes its own declared
        subset (`identity.candidate_lookup`, exact lookups only): candidacy is visibility, not identity
        (BUG-848), so the two readers share ONE implementation but deliberately NOT one rule.
        """
        for method in methods or order:
            if method == "exact_name":
                rec = by_name.get(path.name.strip())
            elif method == "exact_path":
                rec = by_path.get(str(path.resolve()))
            else:  # canonical_name — the declared fallback (T-130 option B, BUG-799)
                rec = by_key.get(_key(path.name))
            if rec is not None:
                return rec, method
        return None, NOT_FOUND

    def record_for(path: Path) -> dict[str, Any] | None:
        """Compatibility reader: the record alone. A caller that needs the METHOD (evidence) uses `resolve`."""
        return resolve(path)[0]

    ids: dict[str, list[str]] = {}
    stems: dict[str, list[str]] = {}
    sizes: dict[int, list[str]] = {}
    for path in corpus:
        rec = record_for(path)
        sid = honest_identity(rec)
        if sid:
            ids.setdefault(sid, []).append(path.name)
        stems.setdefault(_key(path.stem), []).append(path.name)
        try:
            sizes.setdefault(path.stat().st_size, []).append(str(path))
        except OSError:
            continue
    return {"by_name": by_name, "by_path": by_path, "by_key": by_key, "source_ids": ids, "stems": stems,
            "sizes": sizes, "record_for": record_for, "resolve": resolve, "lookup_order": order}


def candidates(corpus: list[Path], census: dict[str, Any],
               policy: dict[str, Any] | None = None) -> list[Path]:
    """THE DELTA RULE: a file the cache cannot name by EXACT bytes is a candidate, and is DECIDED (BUG-848).

    CANDIDACY IS VISIBILITY. It is tempting to route this rule through the same canonical lookup the decision
    uses, and it is WRONG: `stage0_convert.py` converts the corpus MINUS the deferrals this gate names, so a
    file the delta rule absorbs is never decided, never recorded in the receipt and never skipped — it is
    CONVERTED, i.e. ingested as a second work under a second name (the outcome BUG-780 measured 530 rows of).
    MEASURED 2026-10-16: that routing made a noise-suffixed duplicate vanish, and a PRE-EXISTING control caught
    it. The canonical fallback therefore belongs to the DECISION, where a variant name becomes a RECORDED
    deferral grounded in identity — a loud skip — rather than a silent exclusion from the gate.
    """
    pol = policy or load_policy()
    methods = candidate_lookup(pol)  # an undeclared or non-subset rule fails HERE rather than guessing (C12)
    resolve = census["resolve"]
    return [path for path in corpus if resolve(path, methods)[0] is None]


def sha256_file(path: Path) -> str:
    """Streaming SHA-256 of a file (bounded memory; no read of the whole file)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(HASH_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def decide_candidate(path: Path, census: dict[str, Any]) -> dict[str, Any]:
    """Decide ONE candidate: admitted, or deferred with the reason and the record/corpus file it collides with.

    THREE DEFERRAL STATES, checked in this order (T-130 option B):
      1. an IDENTITY twin — another corpus file shares this file's honest work identity (author|title);
      2. a STEM twin — another corpus file shares its sanitized stem (the fallback when a record carries no
         author|title, so no identity can be honestly claimed);
      3. CANONICALLY ALREADY INGESTED — the cache names this work only through a variant name, so admitting it
         would ingest a work the store already holds (BUG-848).
    A byte twin closes the list.

    Self-matches are IMPOSSIBLE by construction: the candidate lives in the census too (it is a file in the
    corpus root), so every comparison excludes the candidate's own name. MEASURED 2026-10-14: without that
    exclusion a brand-new file matched ITSELF and was deferred — a control that fires on everything reports
    nothing.
    """
    record, resolution = census["resolve"](path)
    sid = honest_identity(record)
    decision: dict[str, Any] = {"path": str(path), "name": path.name,
                                "identity": sid or fallback_identity(path.name),
                                "identity_is_evidence": bool(sid),
                                "record_resolution": resolution,
                                "canonical_name": f"{sanitize_source_book(path.stem).strip()}.md",
                                "admitted": True, "defer_reason": "", "matched": ""}
    if sid:
        others = [name for name in census["source_ids"].get(sid, []) if name != path.name]
        if others:
            decision.update(admitted=False, defer_reason="same_work_identity", matched=others[0])
            return decision
    stem_key = _key(path.stem)
    stem_others = [name for name in census["stems"].get(stem_key, []) if name != path.name]
    if stem_key and stem_others:
        decision.update(admitted=False, defer_reason="same_sanitized_stem", matched=stem_others[0])
        return decision
    if record is not None and resolution not in EXACT_METHODS:
        # State 3 (T-130 option B / BUG-848): the record was found ONLY by a non-exact lookup, so this work is
        # ALREADY IN THE STORE — the corpus holds it under a variant name, or this file IS the record's file
        # renamed (its recorded source_path no longer exists: the state T-172's rename creates). Admitting it
        # would ingest work the store already holds (BUG-780's shape, one file at a time). The fail-closed and
        # LOUD answer is a recorded deferral naming the record it matched, which a human can adjudicate.
        decision.update(admitted=False, defer_reason=REASON_ALREADY_INGESTED,
                        matched=str(record.get("source_book") or ""))
        return decision
    try:
        size = path.stat().st_size
    except OSError:
        return decision
    for other in census["sizes"].get(size, []):
        if other == str(path):
            continue
        if sha256_file(path) == sha256_file(Path(other)):
            decision.update(admitted=False, defer_reason="byte_identical", matched=Path(other).name)
            return decision
    return decision


def preflight(books_dir: str | Path | None = None, cache_path: str | Path | None = None,
              run_id: str = "", policy: dict[str, Any] | None = None, write_receipt: bool = True,
              allow_missing_cache: bool = False) -> dict[str, Any]:
    """P1/P1.5 — may each CANDIDATE be ingested? Returns the decision record and writes the deferral receipt.

    Args:
        books_dir: Corpus root override (selftest, alternate batches).
        cache_path: Metadata-cache override (selftest).
        run_id: Batch id stamped into the receipt (defaults to a UTC timestamp).
        policy: Policy mapping override (selftest); defaults to the declared file.
        write_receipt: False keeps the gate pure (selftest).
        allow_missing_cache: True ONLY at the pre-S0 point, where the cache legitimately does not exist yet
            (S0.5 writes it) and no claim is minted. The degradation is RECEIPTED, never silent (C16).

    Returns:
        {run_id, books_dir, candidates, deferrals, admitted, action, receipt, override, identity_available,
         rc_owner_owed}.
    """
    pol = policy or load_policy()
    corpus = corpus_files(books_dir)
    identity_available = True
    try:
        records = cache_records(cache_path)
    except GateInputError:
        if not allow_missing_cache:
            raise
        records, identity_available = [], False
    census = corpus_census(corpus, records, pol)
    delta = candidates(corpus, census, pol)
    decisions = [decide_candidate(path, census) for path in delta]
    deferrals = [d for d in decisions if not d["admitted"]]
    run = run_id or datetime.now(UTC).strftime("preflight-%Y%m%dT%H%M%SZ")
    receipt_path = policy_path(pol, "door", "deferral_dir") / f"{run}.json"
    receipt: str | None = None
    if write_receipt:
        payload = {"schema_version": RECORD_SCHEMA_VERSION, "kind": "ingest_deferral_receipt",
                   "run_id": run, "created_at": datetime.now(UTC).isoformat(),
                   "pipeline_commit": get_pipeline_commit(), "books_dir": str(Path(books_dir) if books_dir else BOOKS_DIR),
                   "candidate_count": len(delta), "deferred_count": len(deferrals),
                   "identity_available": identity_available,
                   "action": str(pol["door"]["action"]), "override": _override(pol), "deferrals": deferrals}
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        receipt = str(receipt_path)
    return {"run_id": run, "books_dir": str(Path(books_dir) if books_dir else BOOKS_DIR),
            "candidates": len(delta), "decisions": decisions, "deferrals": deferrals,
            "admitted": len(decisions) - len(deferrals), "action": str(pol["door"]["action"]),
            "receipt": receipt, "override": _override(pol), "identity_available": identity_available,
            "rc_owner_owed": RC_OWNER_OWED if deferrals else RC_CLEAN}


def _override(policy: dict[str, Any]) -> str:
    """The declared operator escape hatch (empty unless the named env var says `warn`)."""
    import os

    env_name = str(policy["door"].get("override_env", "")) or "MAXWELL_INGEST_GATE"
    return "" if os.environ.get(env_name, "").strip().lower() != "warn" else "warn"


def ledger_debt(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """The owner-word debt in the ONE ledger (D-2738): open pairs, closed pairs, and any UNDECLARED verdict."""
    pol = policy or load_policy()
    path = policy_path(pol, "ledger", "file")
    if not path.exists():
        raise GateInputError(f"owner ledger missing: {path} (an unruled corpus is not a clean ingest)")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    pairs = list(ledger.get("pairs") or [])
    openv = {str(v) for v in pol["ledger"]["verdicts_open"]}
    closedv = {str(v) for v in pol["ledger"]["verdicts_closed"]}
    undeclared = sorted(str(p.get("pair_id")) for p in pairs if str(p.get("verdict")) not in openv | closedv)
    opened = [p for p in pairs if str(p.get("verdict")) in openv]
    return {"file": str(path.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in path.parents else str(path),
            "candidate_count": ledger.get("candidate_count"), "pairs": len(pairs), "open": len(opened),
            "closed": len(pairs) - len(opened), "undeclared_verdicts": undeclared,
            "open_pair_ids": [str(p.get("pair_id")) for p in opened],
            "all_pair_ids": [str(p.get("pair_id")) for p in pairs],
            "open_pair_keys": [pair_key(p.get("a_id"), p.get("b_id")) for p in opened],
            "all_pair_keys": [pair_key(p.get("a_id"), p.get("b_id")) for p in pairs]}


def pair_key(a_id: Any, b_id: Any) -> str:
    """The ONE pair key both surfaces carry. MEASURED 2026-10-14: the detector report has NO `pair_id` — the
    ledger has one — so coverage compared two id NAMESPACES and reported all 29 content candidates as
    uncovered (a false FATAL). The unordered {a_id,b_id} pair is the only key present on both."""
    return "|".join(sorted((str(a_id), str(b_id))))


def uncovered_candidates(candidate_keys: list[str], ledger_keys: set[str]) -> list[str]:
    """Content-detector pairs the owner ledger does not carry: the ledger is STALE (machine half unrun).

    A pair the detector found and the ledger never saw is a blind spot in the door, not an owner question:
    the remedy is mechanical (re-run gate_duplicate_candidates.py), so it is FATAL (C16) and not owner-owed.
    """
    return [key for key in candidate_keys if key not in ledger_keys]


def declared_pointer(pol: dict[str, Any], key: str) -> str:
    """Resolve a '<file>#<dotted.path>' pointer DECLARED in this policy (C12). Never sniffed by name (BUG-782)."""
    pointer = str(pol["ledger"].get(key, "")).strip()
    if "#" not in pointer:
        raise GateInputError(
            f"{CONFIG_REL}#ledger.{key} must be a '<file>#<dotted.path>' pointer, got {pointer!r}")
    rel, dotted = pointer.split("#", 1)
    node: Any = yaml.safe_load((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
    for step in dotted.split("."):
        if not isinstance(node, dict) or step not in node:
            raise GateInputError(f"{pointer} does not resolve: missing {step!r}")
        node = node[step]
    value = str(node).strip()
    if not value:
        raise GateInputError(f"{pointer} resolves to an empty value")
    return value


def declared_sheet_column(pol: dict[str, Any]) -> str:
    """The review sheet's ruling COLUMN, resolved from its DECLARED home (C12). Never sniffed by name.

    BUG-782, MEASURED: this reader used to take the FIRST column whose name contains "ruling". On the rendered
    sheet that column is `proposed_ruling` — a PROPOSAL — so a name-sniff would count machine proposals as owner
    words and release the lane. The column is declared once, with the owner-word contract, and read from there.
    """
    return declared_pointer(pol, "collapse_word_column_from")


def collapse_debt(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """T-129's sheet read in the LEDGER's vocabulary: ONE owner act, two sheets (mapping declared in policy)."""
    pol = policy or load_policy()
    path = policy_path(pol, "ledger", "collapse_sheet")
    words = {str(k).upper(): str(v).upper() for k, v in pol["ledger"]["collapse_words"].items()}
    empty = {"file": str(path.name), "rows": 0, "ruled": 0, "outstanding": 0, "missing": True, "ruled_rows": 0,
             "unprovenanced": 0}
    if not path.exists():
        return empty
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {**empty, "missing": False}
    column = declared_sheet_column(pol)
    if column not in rows[0]:
        raise GateInputError(
            f"collapse sheet has no DECLARED ruling column {column!r}: {path} (looked up by declaration, "
            f"never sniffed by name — BUG-782)")
    # BUG-786, MEASURED 2026-10-14: THE WORD MUST BE PROVENANCED. `--apply` is the only writer of the derived
    # column and it ALWAYS records where the word came from ('row' for a per-row override, 'signature:<tier>@<date>'
    # for a signature expansion). MEASURED: the sheet on disk carried a word in ALL 84 rows with
    # `ruling_source = none` — typed by hand into the DERIVED column — and this reader counted them as RULED
    # (84 ruled / 0 owed). A reader that cannot tell a hand-typed cell from a signature releases the lane without an
    # owner act, which is the BUG-782 defect one column over. So 'none' (or a blank) is OWED, and the reading NAMES
    # the provenance column it required.
    source_column = declared_pointer(pol, "collapse_word_source_column")
    if source_column not in rows[0]:
        raise GateInputError(
            f"collapse sheet has no DECLARED provenance column {source_column!r}: {path} (BUG-786: a word without "
            f"provenance is not an owner act)")
    none_token = str(pol["ledger"].get("collapse_word_source_none", "")).strip().lower()
    ruled = 0
    unprovenanced = 0
    for row in rows:
        word = str(row.get(column) or "").strip().upper()
        if not word or words.get(word, "PENDING") == "PENDING":
            continue
        source = str(row.get(source_column) or "").strip().lower()
        if source in ("", none_token):
            unprovenanced += 1
            continue
        ruled += 1
    return {"file": path.name, "rows": len(rows), "ruled": ruled, "outstanding": len(rows) - ruled,
            "missing": False, "ruled_rows": ruled, "unprovenanced": unprovenanced,
            "provenance_column": source_column, "provenance_none": none_token}


def content_debt(policy: dict[str, Any] | None = None, corpus: list[Path] | None = None) -> dict[str, Any]:
    """P2 — the content detector's report, its AGE against the corpus, and any candidate the ledger never saw."""
    pol = policy or load_policy()
    path = policy_path(pol, "content", "report")
    if not path.exists():
        raise GateInputError(f"content detector report missing: {path} (the door has no content screen)")
    report = json.loads(path.read_text(encoding="utf-8"))
    cands = list(report.get("candidates") or [])
    newest = max((p.stat().st_mtime for p in (corpus if corpus is not None else corpus_files())), default=0.0)
    stale = path.stat().st_mtime < newest
    return {"file": path.name, "candidates": len(cands), "stale": stale,
            "candidate_keys": [pair_key(c.get("a_id"), c.get("b_id")) for c in cands if c.get("a_id") and c.get("b_id")]}


def standing(policy: dict[str, Any] | None = None, books_dir: str | Path | None = None) -> dict[str, Any]:
    """The `--check` census: every debt this gate is the door for, with the tri-state rc it earns.

    rc 1 FATAL  — an unreadable input, an UNDECLARED ledger verdict, a content candidate the ledger never saw
                  (the ledger is stale: the machine half of the gate did not run), or a stale content report.
    rc 2 OWNER  — a pair with no owner word (ledger or collapse sheet), a corpus name defect whose class is
                  declared OWNER-OWED, or candidates that would be deferred if this batch were ingested now.
                  A class declared `accepted_debt` is PRINTED and COUNTED but is never an rc 2 trigger — and
                  only a named OWNER WORD, declared ON that class, may accept it (T-130 option B, T-173/
                  D-3043); anything else is a quiet green and is FATAL. MEASURED 2026-10-16: accepting the
                  marker class removed the last owner-owed item and the ingest reading now reads rc 0.
    """
    pol = policy or load_policy()
    corpus = corpus_files(books_dir)
    cache_records()  # fail-closed guard: an absent identity source RAISES here (C16) — a blind door must never read as clean
    ledger = ledger_debt(pol)
    collapse = collapse_debt(pol)
    content = content_debt(pol, corpus)
    patterns = {str(k): re.compile(str(v)) for k, v in pol["identity"]["name_defect_patterns"].items()}
    dispositions = {str(k): str(v) for k, v in pol["identity"]["defect_disposition"].items()}
    accepted_raw = (pol["identity"].get("accepted_debt") or {}).get("declarations") or {}
    marker = re.compile(str(pol["identity"]["ingest_site_marker_pattern"]))
    defects = {k: 0 for k in patterns}
    markers = 0
    for path in corpus:
        for label, pattern in patterns.items():
            if pattern.search(path.stem):
                defects[label] += 1
        if marker.search(path.stem):
            markers += 1
    disposition_faults = undeclared_defect_dispositions(pol)
    # ONE CLASS, ONE COUNT (D-3043/T-173). The marker pattern lives at its own key because its remedy was a
    # WRITE, but it is a COUNTED CLASS like any other — so it is counted HERE, beside the pattern classes, and
    # an accepted class stays COUNTED AND PRINTED: acceptance changes the rc a class TRIGGERS, never its
    # VISIBILITY (a class that goes quiet the moment it is accepted is the quiet green this gate is for).
    counted = dict(defects)
    counted[MARKER_CLASS] = markers
    accepted_debt = {k: v for k, v in counted.items() if dispositions.get(k) == ACCEPTED_DEBT and v}
    owed_defects = {k: v for k, v in defects.items() if v and dispositions.get(k) == OWNER_OWED}
    accepted_words = {k: str((_resolve_declaration(accepted_raw, k) or {}).get("owner_word", ""))
                      for k in sorted(accepted_debt)}
    accepted_rows = {k: str((_resolve_declaration(accepted_raw, k) or {}).get("row", ""))
                     for k in sorted(accepted_debt)}
    accepted_by = sorted({str(_id) for k in accepted_debt
                          for _id in ((_resolve_declaration(accepted_raw, k) or {}).get("declared_by") or [])})
    markers_owed = markers if dispositions.get(MARKER_CLASS) == OWNER_OWED else 0
    uncovered = uncovered_candidates(content["candidate_keys"], set(ledger["all_pair_keys"]))
    delta = preflight(books_dir=books_dir, policy=pol, write_receipt=False)
    fatal: list[str] = []
    owner: list[str] = []
    if disposition_faults:
        fatal.append("name-defect disposition fault: " + "; ".join(disposition_faults))
    if ledger["undeclared_verdicts"]:
        fatal.append(f"ledger verdict outside the declared vocabulary: {len(ledger['undeclared_verdicts'])} pair(s)")
    if uncovered:
        fatal.append(f"content candidates the ledger never saw (re-run gate_duplicate_candidates.py): {len(uncovered)}")
    if content["stale"]:
        fatal.append(f"content report older than the newest corpus file: {content['file']} (re-run detect_same_work_content.py)")
    if ledger["open"]:
        owner.append(f"ledger pairs with no owner word: {ledger['open']} of {ledger['pairs']}")
    if collapse["outstanding"]:
        owner.append(f"T-129 collapse rows with no owner word: {collapse['outstanding']} of {collapse['rows']}")
    if collapse.get("unprovenanced"):
        owner.append(
            f"T-129 collapse rows whose word carries NO PROVENANCE ({collapse['provenance_column']} is blank or "
            f"'{collapse['provenance_none']}'): {collapse['unprovenanced']} of {collapse['rows']} - a value in the "
            f"DERIVED column is not an owner act (BUG-786: `--apply` is the only writer that records where a word "
            f"came from, so a provenance-less word is OWED until it is expanded from a signature)")
    if owed_defects:
        owner.append(f"corpus name defects whose class is declared OWNER-OWED (the fix is a write): {owed_defects}")
    if markers_owed:
        owner.append(
            f"ingest-site markers in corpus stems: {markers_owed} - a DIFFERENT defect class than the "
            f"whitespace debt (its remedy is the sanitizer, which would rename 571 cache names, not 37): T-173")
    if delta["deferrals"]:
        owner.append(f"candidates deferred if this batch ingested NOW: {len(delta['deferrals'])}")
    if delta["override"]:
        owner.append(f"operator override ACTIVE ({delta['override']}): the door published and proceeded")
    rc = RC_FATAL if fatal else (RC_OWNER_OWED if owner else RC_CLEAN)
    return {"rc": rc, "fatal": fatal, "owner_owed": owner, "corpus_files": len(corpus),
            "candidates": delta["candidates"], "ledger": ledger, "collapse": collapse,
            "content": content, "name_defects": defects, "marker_names": markers,
            "accepted_debt": {"classes": accepted_debt, "total": sum(accepted_debt.values()),
                              "words": accepted_words, "rows": accepted_rows, "declared_by": accepted_by},
            "defect_dispositions": dispositions,
            "record_lookup": lookup_order(pol), "override": delta["override"]}


def gate_read(decisions: list[dict[str, Any]], policy: dict[str, Any] | None = None) -> int:
    """The DOOR's reading of rc: 2 (unresolved identity) REFUSES the run — by declaration, never by accident."""
    pol = policy or load_policy()
    return RC_OWNER_OWED if decisions and str(pol["door"].get("ingest_reading", "")) == "rc2_refuses" else RC_CLEAN
