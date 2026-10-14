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
class this gate exists for — an unknown ledger verdict, or a detector candidate the ledger never saw) |
2 OWNER-OWED (a pair with no owner word; a corpus name defect, whose fix is a write).
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


def corpus_census(corpus: list[Path], records: list[dict[str, Any]]) -> dict[str, Any]:
    """The corpus's identity census: canonical ids, sanitized stems, byte sizes, and the cache's own keys."""
    by_name: dict[str, dict[str, Any]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    for rec in records:
        name = str(rec.get("source_book") or "").strip()
        if name:
            by_name.setdefault(name, rec)
        raw_path = str(rec.get("source_path") or "").strip()
        if raw_path:
            by_path.setdefault(str(Path(raw_path).resolve()), rec)

    def record_for(path: Path) -> dict[str, Any] | None:
        return by_name.get(path.name.strip()) or by_path.get(str(path.resolve()))

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
    return {"by_name": by_name, "by_path": by_path, "source_ids": ids, "stems": stems, "sizes": sizes,
            "record_for": record_for}


def candidates(corpus: list[Path], census: dict[str, Any]) -> list[Path]:
    """THE DELTA RULE: a file the metadata cache already knows is NOT a candidate and is never re-classified."""
    out: list[Path] = []
    for path in corpus:
        if str(path.resolve()) in census["by_path"]:
            continue
        if path.name.strip() in census["by_name"]:
            continue
        out.append(path)
    return out


def sha256_file(path: Path) -> str:
    """Streaming SHA-256 of a file (bounded memory; no read of the whole file)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(HASH_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def decide_candidate(path: Path, census: dict[str, Any]) -> dict[str, Any]:
    """Decide ONE candidate: admitted, or deferred with the reason and the corpus file it collides with.

    Self-matches are IMPOSSIBLE by construction: the candidate lives in the census too (it is a file in the
    corpus root), so every comparison excludes the candidate's own name. MEASURED 2026-10-14: without that
    exclusion a brand-new file matched ITSELF and was deferred — a control that fires on everything reports
    nothing.
    """
    record = census["record_for"](path)
    sid = honest_identity(record)
    decision: dict[str, Any] = {"path": str(path), "name": path.name,
                                "identity": sid or fallback_identity(path.name),
                                "identity_is_evidence": bool(sid),
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
    census = corpus_census(corpus, records)
    delta = candidates(corpus, census)
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
    rc 2 OWNER  — a pair with no owner word (ledger or collapse sheet), a corpus name defect (the fix is a
                  write), or candidates that would be deferred if this batch were ingested now.
    """
    pol = policy or load_policy()
    corpus = corpus_files(books_dir)
    cache_records()  # fail-closed guard: an absent identity source RAISES here (C16) — a blind door must never read as clean
    ledger = ledger_debt(pol)
    collapse = collapse_debt(pol)
    content = content_debt(pol, corpus)
    patterns = {str(k): re.compile(str(v)) for k, v in pol["identity"]["name_defect_patterns"].items()}
    marker = re.compile(str(pol["identity"]["ingest_site_marker_pattern"]))
    defects = {k: 0 for k in patterns}
    markers = 0
    for path in corpus:
        for label, pattern in patterns.items():
            if pattern.search(path.stem):
                defects[label] += 1
        if marker.search(path.stem):
            markers += 1
    uncovered = uncovered_candidates(content["candidate_keys"], set(ledger["all_pair_keys"]))
    delta = preflight(books_dir=books_dir, policy=pol, write_receipt=False)
    fatal: list[str] = []
    owner: list[str] = []
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
    if sum(defects.values()) or markers:
        owner.append(f"corpus name defects (fix is a write): {defects} markers={markers}")
    if delta["deferrals"]:
        owner.append(f"candidates deferred if this batch ingested NOW: {len(delta['deferrals'])}")
    if delta["override"]:
        owner.append(f"operator override ACTIVE ({delta['override']}): the door published and proceeded")
    rc = RC_FATAL if fatal else (RC_OWNER_OWED if owner else RC_CLEAN)
    return {"rc": rc, "fatal": fatal, "owner_owed": owner, "corpus_files": len(corpus),
            "candidates": delta["candidates"], "ledger": ledger, "collapse": collapse,
            "content": content, "name_defects": defects, "marker_names": markers, "override": delta["override"]}


def gate_read(decisions: list[dict[str, Any]], policy: dict[str, Any] | None = None) -> int:
    """The DOOR's reading of rc: 2 (unresolved identity) REFUSES the run — by declaration, never by accident."""
    pol = policy or load_policy()
    return RC_OWNER_OWED if decisions and str(pol["door"].get("ingest_reading", "")) == "rc2_refuses" else RC_CLEAN
