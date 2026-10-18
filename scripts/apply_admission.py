#!/usr/bin/env python3
"""apply_admission.py — THE ADMIT APPLIER: put ONE library work into the corpus through S0 (T-183/D-3051/D-3068).

WHAT THIS ACT IS, AND WHAT IT IS NOT. The admission PLAN (`scripts/plan_admission.py`, T-181) classifies every
file in the declared library kind roots and proposes, for each candidate, the corpus path its own arrangement
implies. It ADMITS NOTHING. This file is the other half: the ONE writer that turns an ACCEPTED plan row into a
work the pipeline can read, and it DECIDES NOTHING.

    * it applies an ACCEPTED plan — a plan is not accepted because it exists, but because a separate file, signed
      by the owner, names it by DIGEST and says which rows are in scope (`governance/ADMISSION_ACCEPTED_*.yaml`);
    * it refuses a row absent from that signed set, a target that already exists with nothing accounting for it,
      a row whose source bytes changed since the plan was derived, and a row whose name a declared defect pattern
      still matches (an admitted name becomes the CORPUS NAME and the DOOR KEY — the repair rides first, T-176);
    * it writes NOTHING without `--apply` (dry run is the default, and the dry run is the owner's cost estimate);
    * it copies crash-safe (C6: tempfile -> fsync -> os.replace in the TARGET directory, so a crash leaves either
      the old tree or a complete new file — never a half one), and it never deletes anything (R-D410);
    * it receipts every row as it lands, one JSON line per row, appended and fsync'd immediately, so an
      interrupted batch is readable instead of ambiguous (D-3036). A row that S0 could not convert is a NAMED
      failure, never a silence (C16).

HOW THE BATCH IS RESUMED. A target that exists AND whose digest a receipt accounts for is `already_applied` — the
honest reading of a second run, not a refusal. A target that exists with NO receipt accounting for it is REFUSED:
something else put a work there, and this writer may not overwrite an act it cannot explain.

Exit: 0 nothing owed / every selected row already applied | 2 OWNER-OWED (no signed acceptance yet, or rows
waiting) — loud, never fatal (BUG-457) | 1 FATAL (an undeclared or unreadable declaration, a digest mismatch, a
refused row, a failed conversion, an escape from the corpus home).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

import plan_admission  # noqa: E402 — the reader whose rows this writer applies (never a second derivation)
import census_source_names as census  # noqa: E402 — the library reader: roots, name classes, the cache join
from pipeline.book_metadata import sanitize_source_book  # noqa: E402 — the door's OWN key (D-3045)
from pipeline.container_integrity import is_readable, probes_from  # noqa: E402 — BUG-886/D-3071
#: BUG-897/D-3076: the OUTER wall of a conversion is declared, not a constant. A Stage-0 subprocess killed by this
#: ceiling is reported as `S0 could not be run`, which names neither the work nor the reason — so the docling
#: ceiling inside it must stay strictly below it (asserted at import in pipeline/pipeline_paths.py).
from pipeline.pipeline_paths import S0_STAGE_TIMEOUT_S, STAGE0_CHECKPOINT  # noqa: E402
#: BUG-933: the ADMISSION lane appends to this checkpoint by running S0 once per row, so the binding between the
#: checkpoint and the code that wrote it is this writer's business too — read from the one home (`pipeline.stamp`),
#: never restated here.
from pipeline.stamp import read_stage_code_fingerprint, stage_code_fingerprint  # noqa: E402

POLICY = census.POLICY
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2
CHUNK = 1024 * 1024
#: A conversion output smaller than this is not a work (the same floor S0 applies to a native .md).
MIN_WORK_BYTES = 100
SCHEMA_VERSION = "1.0"
GEN_MODEL = "deterministic"  # R14: this act is not a model's — it is a repeated derivation, and it says so
#: THE INDEXES THAT CAN ANSWER "THE CORPUS ALREADY HOLDS THIS NAME" (D-3095), and the only two this writer can
#: read. A `name_held.indexes` entry outside this set is FATAL: an index named in the declaration that no reader
#: builds is a rule with no evidence, which is the strictest form of the failure D-3034 forbids.
HELD_INDEXES = ("corpus_index", "ingest_records")


class ApplierError(SystemExit):
    """Fail-closed: an undeclared, absent or unresolvable input is a fault, never a silent zero (C16/D-795)."""


def applier_rc(exc: SystemExit) -> int:
    """The exit code of a refusal — BUG-884: a message passed to SystemExit lands in `.code` as a STRING, so the
    first handler turned every governed refusal ("the acceptance pins digest X but Y hashes to Z") into
    `ValueError: invalid literal for int()`. Fail-closed held — nothing was written — but the operator got a
    traceback instead of the refusal, which is the one thing a refusal exists to say."""
    return exc.code if isinstance(exc.code, int) else RC_FATAL


def declared_state(state: str, decl: dict[str, Any]) -> str:
    """The vocabulary is a GATE, not a description (BUG-923): a state the declaration does not carry is FATAL.

    MEASURED 2026-10-18: `skipped` was written to 85 receipt lines while `applier.states` did not name it, and
    `deferred` was never written at all — the deferral was mislabelled `failed` — so the closed list described a
    vocabulary the writer had already left. A declaration nothing enforces cannot catch that; this one can.
    """
    states = [str(state_) for state_ in decl["states"]]
    if state not in states:
        raise ApplierError(
            f"FATAL: this writer produced the state {state!r}, which {POLICY}#source_library.admission.applier"
            f".states does not declare ({states}) — a receipt line whose state nobody declared is a state no "
            f"reader can classify (C12)"
        )
    return state


def s0_outcome_tokens(decl: dict[str, Any]) -> dict[str, dict[str, str]]:
    """The tokens S0 prints for an outcome that is NOT a conversion, with the sentence its receipt line carries.

    WHY DECLARED AND NOT SPELLED HERE (C12): the token is the contract between two programs and the meaning is a
    sentence a reader of the receipt must not have to reconstruct. BUG-923 measured the cost of the alternative —
    ONE token was recognised in code (`S0_SKIPPED_IMAGE_HEAVY`) and the other (`deferred_for_identity`) was not,
    so a deferral the door had deliberately made arrived as `failed`, tripped the fail-closed exit and told the
    owner a tranche was broken. A token the applier does not carry is FATAL here, never silently "just a failure".
    """
    block = decl.get("s0_outcome_tokens")
    if not isinstance(block, dict) or not block:
        raise ApplierError(
            f"FATAL: {POLICY}#source_library.admission.applier.s0_outcome_tokens is not declared — the tokens S0 "
            f"prints for a skip and for a deferral must come from the declaration, never from this writer (C12)"
        )
    tokens: dict[str, dict[str, str]] = {}
    for state, spec in block.items():
        if not isinstance(spec, dict) or not str(spec.get("token") or "").strip():
            raise ApplierError(f"FATAL: s0_outcome_tokens[{state!r}] declares no token — a named state with no "
                               f"token is a declaration that resolves to nothing (D-3034)")
        declared_state(str(state), decl)  # a token may only name a state the receipt vocabulary carries
        tokens[str(state)] = {"token": str(spec["token"]).strip(), "meaning": str(spec.get("meaning") or "").strip()}
    return tokens


def same_bytes_policy(decl: dict[str, Any]) -> dict[str, str]:
    """What a SECOND copy of already-admitted bytes is answered with, declared rather than spelled here (D-3092).

    The rule exists because identity by NAME cannot answer it: MEASURED 2026-10-18, 28 of the day's 34 door
    deferrals were rows whose identical bytes a receipt of the SAME RUN had already admitted from another library
    path, so each asked the owner to adjudicate an identity the receipts had already resolved. Bytes are the one
    evidence that needs no judgement — and the receipt already carries them, so this costs no extra read.
    """
    spec = decl.get("same_bytes")
    if not isinstance(spec, dict) or not spec:
        raise ApplierError(
            f"FATAL: {POLICY}#source_library.admission.applier.same_bytes is not declared — what a second copy of "
            f"already-admitted bytes is answered with must come from the declaration, never from this writer (C12)"
        )
    for key in ("state", "evidence", "meaning"):
        if not str(spec.get(key) or "").strip():
            raise ApplierError(f"FATAL: same_bytes declares no {key!r} — that resolves to nothing (D-3034)")
    if str(spec["evidence"]) != "source_sha256":
        raise ApplierError(
            f"FATAL: same_bytes.evidence is {spec['evidence']!r}; the applier can prove a duplicate only from the "
            f"digest a receipt carries (source_sha256) — a name or a size is not a work (D-3092)"
        )
    return {"state": declared_state(str(spec["state"]), decl),
            "meaning": str(spec["meaning"]).strip(),
            "absent_target_means": str(spec.get("absent_target_means") or "").strip()}


def name_held_policy(decl: dict[str, Any]) -> dict[str, Any]:
    """What a row the corpus already holds BY NAME is answered with, declared rather than spelled here (D-3095).

    The rule exists because the alternative was measured: a batch-wide FATAL on "no longer a candidate" aborted
    109 outstanding acts of the owner's 237-row plan over 12 rows — 9 redundant by bytes, 3 owner-only questions.
    A name the corpus holds is not a fault and not an admission: it is the D-3045 question, and the owner's own
    doctrine already says what a question costs (BUG-457/BUG-923: rc 2, loud, never fatal).
    """
    spec = decl.get("name_held")
    if not isinstance(spec, dict) or not spec:
        raise ApplierError(
            f"FATAL: {POLICY}#source_library.admission.applier.name_held is not declared — what a row the corpus "
            f"already holds by NAME is answered with must come from the declaration, never from this writer (C12)"
        )
    for key in ("state", "indexes", "meaning"):
        if not spec.get(key):
            raise ApplierError(f"FATAL: name_held declares no {key!r} — that resolves to nothing (D-3034)")
    indexes = spec["indexes"]
    if not isinstance(indexes, list) or not all(isinstance(item, str) for item in indexes):
        raise ApplierError(f"FATAL: name_held.indexes must be a list of declared index names, got {indexes!r}")
    unknown = [item for item in indexes if item not in HELD_INDEXES]
    if unknown:
        raise ApplierError(
            f"FATAL: name_held.indexes names {unknown}, which this writer has no reader for ({HELD_INDEXES}) — an "
            f"index nobody can build is a declaration with no referent (D-3034)"
        )
    if not indexes:
        raise ApplierError("FATAL: name_held.indexes is EMPTY — a rule with no evidence is a caption (D-3034)")
    return {"state": declared_state(str(spec["state"]), decl),
            "indexes": [str(item) for item in indexes],
            "meaning": str(spec["meaning"]).strip(),
            "bytes_win": str(spec.get("bytes_win") or "").strip(),
            "absent_means": str(spec.get("absent_means") or "").strip()}


def held_names(decl: dict[str, Any], doc: dict[str, Any], corpus: Path) -> dict[str, list[str]]:
    """Every NAME the corpus and the ingest records already hold, by the door's OWN key, with what holds it.

    Both readers are the door's (`plan_admission.corpus_index` over the corpus home, `census_source_names.
    cache_keys` over the S0.5 records) and both are keyed by the door's one comparison key, so this asks the same
    two questions `plan_admission.build()` asks FIRST in its own decision order — it invents no third identity
    (D-3045). The answer is a list of WHAT holds the name, because a deferral whose reason does not RESOLVE is a
    sentence, not a question (D-3034).
    """
    policy = name_held_policy(decl)
    held: dict[str, list[str]] = {}
    if "corpus_index" in policy["indexes"]:
        for key, paths in plan_admission.corpus_index(corpus).items():
            for path in paths:
                try:
                    label = f"the corpus holds {Path(path).relative_to(corpus)}"
                except ValueError:
                    label = f"the corpus holds {path}"
                held.setdefault(key, []).append(label)
    if "ingest_records" in policy["indexes"]:
        for key, record in census.cache_keys(doc).items():
            author, title = record.get("author", ""), record.get("title", "")
            label = f"an ingest record read this work as {author!r} — {title!r} (T-130: the corpus copy was renamed)"
            held.setdefault(key, []).append(label)
    return held


def batch_rc(counts: dict[str, int], decl: dict[str, Any]) -> int:
    """The batch exit code, from the DECLARED mapping (BUG-923): refuse/fail is fatal, a deferral is OWNER-OWED."""
    exits = decl.get("exit_codes")
    if not isinstance(exits, dict) or not exits:
        raise ApplierError(
            f"FATAL: {POLICY}#source_library.admission.applier.exit_codes is not declared — what a batch's exit "
            f"code MEANS must come from the declaration, never from this writer (C12)"
        )
    fatal = [declared_state(str(state), decl) for state in (exits.get("fatal_states") or [])]
    owed = [declared_state(str(state), decl) for state in (exits.get("owner_owed_states") or [])]
    if not fatal and not owed:
        raise ApplierError(f"FATAL: applier.exit_codes declares neither fatal_states nor owner_owed_states — a "
                           f"mapping that decides nothing is a sentence, not a rule (D-3034)")
    for state in fatal:
        if counts.get(state):
            return RC_FATAL
    for state in owed:
        if counts.get(state):
            return RC_OWNER_OWED
    return RC_OK


def asking_line(collisions: dict[str, list[str]]) -> str:
    """What the batch says about name-held rows BEFORE their verdict exists — a question in flight, nothing promised.

    WHY THIS FUNCTION CANNOT LIE ABOUT THE EXIT CODE (BUG-934): it is given no counts and no declaration, so it is
    structurally incapable of naming an exit code. MEASURED 2026-10-18 on the live signed plan: 9 rows were held by
    name, the DIGEST then resolved all 9 as `duplicate_of_admitted` (D-3092 — bytes beat name), the batch exited 0,
    and the run printed "rc 2 says so" AND "no word is owed" about the same nine rows. A claim about the exit code
    that is not derived FROM the exit code is a lie the reader cannot check, so the pre-verdict line now speaks only
    about the question, and `verdict_lines` speaks only about counts it is actually handed.
    """
    return (f"ASKING   {len(collisions)} row(s) the corpus already holds BY NAME with other bytes — the DIGEST "
            f"answers first and it answers per row (D-3092: bytes beat name); whatever it leaves unanswered is the "
            f"owner's word on which work that is (D-3045), and this line is not that verdict")


def verdict_lines(counts: dict[str, int], collisions: int, decl: dict[str, Any]) -> list[str]:
    """The lines that speak about what the OWNER OWES and what was REDUNDANT — derived from the SAME counts as the rc.

    Invariant (BUG-934), and it is one control over every declared state rather than one per bug: the presence of
    the owner-owed claim and `batch_rc(counts, decl) == RC_OWNER_OWED` are the same fact, computed from one dict.
    A report may therefore never disagree with its own exit code.
    """
    lines: list[str] = []
    deferred = int(counts.get("deferred") or 0)
    if deferred:
        lines.append(
            f"OWNER-OWED: {deferred} row(s) need YOUR word on identity (D-3045) — either the door DEFERRED the "
            f"work, or the corpus already holds that NAME with other bytes (D-3095) — this is not a failed batch; "
            f"the declared exit code says so (applier.exit_codes)"
        )
    same_state = str(same_bytes_policy(decl)["state"])
    redundant = int(counts.get(same_state) or 0)
    if redundant:
        lines.append(
            f"REDUNDANT: {redundant} row(s) carry bytes a receipt already admitted under another corpus path "
            f"(D-3092) — the work is in the corpus, nothing was copied, and no word is owed; each line names the "
            f"path it duplicates"
        )
    if collisions and not deferred:
        lines.append(
            f"ANSWERED: all {collisions} name-held row(s) resolved on the digest alone — a name is a question, the "
            f"bytes are the answer, and this batch owes the owner nothing (D-3092/D-3095)"
        )
    return lines


# ---------------------------------------------------------------------------------------------------------------------
# THE DECLARATION — every path, prefix and vocabulary this writer obeys comes from its ONE home (C12)
# ---------------------------------------------------------------------------------------------------------------------
def applier_policy(doc: dict[str, Any]) -> dict[str, Any]:
    """The declared applier contract: where a signature lives, where a receipt lands, and what a signature carries."""
    decl = ((doc["source_library"].get("admission") or {}).get("applier"))
    if not isinstance(decl, dict) or not decl:
        raise ApplierError(
            f"FATAL: {POLICY}#source_library.admission.applier is not declared — the acceptance home, the receipt "
            f"home and the signature's required keys must come from the declaration, never from this writer (C12)"
        )
    for key in ("authority", "command", "accept_prefix", "accept_extension", "receipt_prefix",
                "receipt_extension", "accept_modes", "accept_required", "states", "quarantine_prefix",
                "accept_by_placeholder", "accept_by_identity", "s0_outcome_tokens", "exit_codes", "same_bytes",
                "name_held"):
        if key not in decl:
            raise ApplierError(
                f"FATAL: {POLICY}#source_library.admission.applier does not declare {key!r} (C12: an absent "
                f"value is FATAL and never defaulted)"
            )
    #: THE READABILITY PROBE MAP LIVES ONE LEVEL UP, beside the decision vocabulary, because BOTH readers share it:
    #: the plan refuses an unopenable container before an owner signs it and this writer asks again before it
    #: copies (BUG-886/D-3071). A second copy of the map inside this block would be a second home for one fact
    #: (C12), so the declaration is HANDED DOWN here and `probes_from` still refuses an absent or unknown one.
    return dict(decl, container_integrity=(doc["source_library"]["admission"] or {}).get("container_integrity"))


def resolve_root(value: str) -> Path:
    """A declared path, relative to the repository root when it is not absolute (one rule for every declaration)."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else _PROJECT_ROOT / path


def newest(prefix: str, extension: str) -> Path | None:
    """The newest declared artifact by its own stamp — the plan and the signature are both dated files."""
    base = resolve_root(prefix)
    folder, stem = base.parent, base.name
    if not folder.is_dir():
        return None
    found = sorted(folder.glob(f"{stem}*{extension}"))
    return found[-1] if found else None


def sha256_bytes(path: Path) -> str:
    """The digest of a file's BYTES — the only identity a plan row and a receipt can be compared by."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def pipeline_commit() -> str:
    """R14: every persistent object names the code that produced it. A missing git is NAMED, not defaulted."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_PROJECT_ROOT), capture_output=True, text=True,
                             timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARN: git is unavailable ({type(exc).__name__}: {exc}) — the receipt will stamp 'unavailable'")
        return "unavailable"
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else "unavailable"


# ---------------------------------------------------------------------------------------------------------------------
# THE PLAN AND THE SIGNATURE
# ---------------------------------------------------------------------------------------------------------------------
def load_plan(path: Path) -> dict[str, Any]:
    """Read the accepted-candidate plan; a document that is not a plan is FATAL, never an empty worklist."""
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — any failure means this writer cannot know the plan
        raise ApplierError(f"FATAL: the plan {path} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(plan, dict) or not isinstance(plan.get("rows"), list):
        raise ApplierError(f"FATAL: {path} carries no 'rows' list — it is not an admission plan")
    if not plan["rows"]:
        raise ApplierError(f"FATAL: {path} carries ZERO candidate rows — an empty plan is not an accepted batch")
    return plan


#: THE FIELDS A SIGNATURE ACTUALLY AUTHORISES (D-3072). A row is an ACT: WHICH file (rel), WHOSE bytes
#: (source_sha256), WHERE the corpus copy lands (target) and what kind it is. Those four are what the applier reads
#: and all it reads, so those four ARE the word. Everything else in a plan — counts, examples, a probe list, a
#: timestamp, a class that moved from 179 to 180 — is a DERIVATION the owner never signed.
SCOPE_FIELDS = ("rel", "source_sha256", "target", "kind")


def scope_digest(rows: list[dict[str, Any]]) -> str:
    """The digest of the ACTS a signature puts in scope, in PLAN ORDER (order is part of the act: `--limit` reads it).

    MEASURED 2026-10-17, twice: the owner's word was pinned to the plan FILE's sha256, so ANY re-derivation of the
    plan voided it — a bug fix in the reader, a probe added, a timestamp, one refusal class moving by one row. The
    word was voided twice in one sitting and each time the file had to be re-printed, which resets the name to the
    template placeholder, which the applier then refused (BUG-888). That is a loop built into the artifact, not a
    mistake by its owner: the thing being signed (a DOCUMENT) is not the thing being authorised (a SET OF ACTS).
    Pinning the acts is also the stricter reading: a re-derived plan that changed a target or a source digest
    changes the scope and is still refused (D-3034 — only a RESOLUTION grants).
    """
    body = [{field: str(row.get(field, "")) for field in SCOPE_FIELDS} for row in rows]
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def scope_diff(authorised: list[str], live: list[dict[str, Any]]) -> list[str]:
    """What moved between the acts an owner authorised and the acts this plan holds, named in rows.

    A refusal that says only "the digest changed" is a fact its owner can do nothing with (D-3034: a message that
    does not RESOLVE is a sentence). The manifest of `rel` labels the signature carries is what makes this listable.
    """
    authorised_set = {str(rel) for rel in authorised}
    live_set = {str(row.get("rel")) for row in live}
    gone = sorted(authorised_set - live_set)
    new = sorted(live_set - authorised_set)
    lines: list[str] = []
    if gone:
        lines.append(f"{len(gone)} authorised row(s) the plan no longer holds {gone[:3]}")
    if new:
        lines.append(f"{len(new)} row(s) the plan now holds that were never authorised {new[:3]}")
    if not lines:
        lines.append("the SAME rows, with at least one act changed underneath them (target, source digest or kind)")
    return lines


def verify_scope(acc: dict[str, Any], plan_path: Path, plan_digest: str,
                 signed: list[dict[str, Any]], live: list[dict[str, Any]],
                 decl: dict[str, Any]) -> str:
    """Does this signature still authorise THIS plan? Returns how it was proved, and refuses when it does not.

    Two proofs, in order of strength: the plan's own BYTES (the file has not moved a byte since it was signed), or
    its SCOPE (a re-derived plan whose every authorised act is identical). Anything else is FATAL and NAMES the
    rows that differ. A signature that pins neither is refused: silence about what was authorised is not consent.
    """
    pinned = str(acc.get("scope_sha256", "")).strip().lower()
    if not pinned:
        raise ApplierError(
            f"FATAL: the signature carries no `scope_sha256` — a signature that names no ACTS cannot be checked "
            f"against them. Re-sign: `{decl['command']} --sign --as <your name>` (D-3072)"
        )
    live_scope = scope_digest(live)
    if pinned != live_scope:
        raise ApplierError(
            f"FATAL: this signature authorises a DIFFERENT set of acts than {plan_path.name} holds: "
            + "; ".join(scope_diff([str(rel) for rel in acc.get("rows") or []], live))
            + f". Re-sign with the LIVE scope: `{decl['command']} --sign --as <your name>` (D-3072)"
        )
    if str(acc.get("plan_sha256", "")).strip().lower() == plan_digest:
        return "digest"
    #: THE PLAN FILE MOVED, THE ACTS DID NOT. MEASURED: a re-derived plan differs in a timestamp, a count, a class
    #: that moved by one row — none of which the owner signed and none of which the applier reads. Refusing here is
    #: what kept the owner in a loop: the word was voided by a DOCUMENT change and had to be re-printed, and
    #: re-printing resets the name to the placeholder the applier then refused (BUG-888/BUG-892).
    return "scope"


def acceptance_plan(path: Path, decl: dict[str, Any]) -> Path | None:
    """THE PLAN A SIGNATURE NAMES — the plan the applier must apply, whatever else is newer on disk (BUG-931).

    MEASURED 2026-10-18, ring 2 of the same loop. `run()` resolved the plan with `newest(plan_prefix)`, and
    `load_acceptance` then required the signature to name THAT file. So every re-derivation — a fresh stamped
    `ADMISSION_PLAN_…T153603ZZ.json` alongside the signed `ADMISSION_PLAN_…20261018.json` — made a still-valid word
    unusable: `admit-apply` refused with "a signature for another plan authorises nothing" while the signed plan sat
    on disk, unchanged, and its ACTS still matched the signature's `scope_sha256` exactly. The owner's remedy was to
    re-derive and re-sign — which produced yet another plan file and re-armed the same trap.

    A word is given to a DOCUMENT; the clock has no say in which document that is. So when no `--plan` is named
    explicitly, the signature chooses the plan. `newest()` remains the default only when there is NO signature at
    all (the "nothing signed yet" reading). An explicit `--plan` still meets the name check in `load_acceptance`
    and is refused when it disagrees — there the owner chose the document, so the disagreement is real.
    """
    import yaml

    try:
        acc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — an unreadable signature names nothing
        raise ApplierError(f"FATAL: the acceptance {path} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(acc, dict) or not str(acc.get("plan") or "").strip():
        return None  # `load_acceptance` owns the refusal for a signature that names no plan
    named = resolve_root(str(acc["plan"]))
    if not named.is_file():
        raise ApplierError(
            f"FATAL: the acceptance {path.name} names {named} and no such plan is on disk — a word given to a "
            f"document that no longer exists authorises nothing (D-3034). Re-derive the plan and sign the live one."
        )
    return named


def load_acceptance(path: Path, plan_path: Path, plan_digest: str, decl: dict[str, Any]) -> dict[str, Any]:
    """Read the owner's signature: the plan it names, the digest it pins, and the rows it puts in scope."""
    import yaml

    try:
        acc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — an unreadable signature signs nothing
        raise ApplierError(f"FATAL: the acceptance {path} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(acc, dict):
        raise ApplierError(f"FATAL: {path} is not a mapping — an acceptance names a plan and its rows")
    missing = [key for key in decl["accept_required"] if key not in acc]
    if missing:
        raise ApplierError(f"FATAL: {path} does not carry {missing} — a signature missing a field signs nothing")
    #: BUG-888 — A FIELD THAT IS PRESENT IS NOT A FIELD THAT RESOLVES (D-3034). MEASURED 2026-10-17: the owner's
    #: first acceptance carried `accepted_by: <your name>` — the TEMPLATE'S OWN PLACEHOLDER — and it was applied,
    #: because only the field's PRESENCE was ever checked. The name is the whole authorisation: an unresolvable
    #: one is a signature nobody signed. The placeholder is DECLARED (`accept_by_placeholder`) so the writer and
    #: the template cannot disagree about what it is, and an empty value is refused on the same branch.
    who = str(acc["accepted_by"]).strip()
    placeholder = str(decl["accept_by_placeholder"]).strip()
    if not who or who.lower() == placeholder.lower():
        raise ApplierError(
            f"FATAL: {path} carries accepted_by={acc['accepted_by']!r} — a placeholder or an empty name is not a "
            f"signature (the acceptance is the owner's word). Give it ONCE, as a command, and every later plan "
            f"re-derivation reuses it: `{decl['command']} --sign --as <your name>` (D-3072)"
        )
    if acc["mode"] not in decl["accept_modes"]:
        raise ApplierError(
            f"FATAL: {path} declares mode {acc['mode']!r}, outside the declared vocabulary "
            f"{decl['accept_modes']} (C12)"
        )
    named = resolve_root(str(acc["plan"]))
    if named.resolve() != plan_path.resolve():
        raise ApplierError(
            f"FATAL: the acceptance names {named.name} but this run applies {plan_path.name} — a signature for "
            f"another plan authorises nothing (D-3034)"
        )
    #: D-3072: THE DIGEST NO LONGER DECIDES ALONE. It is checked in `verify_scope`, AFTER the rows are selected,
    #: because what an owner authorises is a SET OF ACTS and the acts are the rows — not the file that lists them.
    #: Pinning only the file made every re-derivation of the plan void the word (MEASURED twice on 2026-10-17).
    if acc["mode"] == "listed" and not isinstance(acc.get("rows"), list):
        raise ApplierError(f"FATAL: {path} declares mode=listed but carries no rows list")
    return acc


def declared_identity(decl: dict[str, Any]) -> str:
    """The owner's name, from its ONE declared home — empty until the owner has said it once (D-3072).

    MEASURED 2026-10-17, twice in one sitting: the signature lives in a file the tool PRINTS, and printing reset
    `accepted_by` to the template placeholder every time the plan was re-derived, so the applier refused a word
    the owner had already given. The NAME is an IDENTITY, not a per-plan decision: it is declared once, and only
    the SCOPE is re-decided. An absent or placeholder identity stays a REFUSAL (BUG-888 keeps its teeth).
    """
    path = resolve_root(str(decl["accept_by_identity"]))
    if not path.is_file():
        return ""
    import yaml
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — an unreadable identity is not an absent one (C16)
        raise ApplierError(f"FATAL: the declared identity file {path} cannot be read ({type(exc).__name__}: {exc})")
    return str((doc or {}).get("accept_by") or "").strip()


def acceptance_template(plan_path: Path, digest: str, rows: list[dict[str, Any]],
                        placeholder: str = "<your name>", who: str = "") -> str:
    """A ready-to-sign acceptance, with the LIVE digest already in it — so signing cannot fail on a copied hash.

    The template is deliberately `mode: all` with `rows: []` and a comment naming the alternative: a signature that
    silently selected nothing would look like an authorisation while authorising nothing (D-3034).
    """
    import yaml

    try:  # a signature is more portable when it names the plan RELATIVE to the tree it governs
        plan_ref = plan_path.resolve().relative_to(_PROJECT_ROOT).as_posix()
    except ValueError:  # a plan outside the repo keeps its own absolute path
        plan_ref = str(plan_path)
    body = {
        "schema_version": SCHEMA_VERSION,
        "plan": plan_ref,
        "plan_sha256": digest,
        #: D-3072: WHAT THE OWNER ACTUALLY AUTHORISES — the acts, not the document. A re-derived plan whose acts are
        #: identical still matches this; a plan whose acts moved does not, whatever its bytes hash to.
        "scope_sha256": scope_digest(rows),
        "accepted_by": who or placeholder,
        "accepted_on": datetime.now(UTC).strftime("%Y-%m-%d"),
        "mode": "all",
        #: THE MANIFEST: the `rel` of every act in scope, written even under `mode: all`, so a refusal can NAME the
        #: rows that moved instead of printing two digests at an owner (D-3034).
        "rows": [str(row["rel"]) for row in rows],
    }
    return (
        f"# THE SIGNATURE THIS PLAN NEEDS (T-183/D-3068, D-3072).\n"
        f"# It authorises {len(rows)} row(s), listed at the end of this file by their `rel` label.\n"
        f"# `plan_sha256` pins the DOCUMENT; `scope_sha256` pins the ACTS (rel + source digest + target + kind), so a\n"
        f"# re-derived plan with identical acts does NOT void this signature and one whose acts moved is REFUSED.\n"
        f"# `accepted_by` is the owner's IDENTITY: once it is declared (`--sign --as`), this printer carries it and\n"
        f"# never asks again. A placeholder or an empty name is REFUSED (BUG-888).\n"
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True)
    )


def selected_rows(plan: dict[str, Any], acc: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """The rows this signature puts in scope. A row the signature names but the plan does not hold is FATAL."""
    rows = plan["rows"]
    if acc["mode"] == "all":
        return list(rows), []
    wanted = [str(item) for item in acc.get("rows") or []]
    by_rel = {str(row["rel"]): row for row in rows}
    unknown = [rel for rel in wanted if rel not in by_rel]
    if unknown:
        raise ApplierError(
            f"FATAL: the acceptance names {len(unknown)} row(s) the plan does not carry: {unknown[:3]} — an "
            f"approved row that cannot RESOLVE is a wish, not a grant (D-3034)"
        )
    seen: set[str] = set()
    chosen: list[dict[str, Any]] = []
    for rel in wanted:
        if rel not in seen:  # a duplicated line in a signature is one row, not two copies
            chosen.append(by_rel[rel])
            seen.add(rel)
    return chosen, []


def derive() -> dict[str, str]:
    """The CURRENT classification of every file, by the reader's own derivation — never a second opinion."""
    plan = plan_admission.build()
    return {str(row["rel"]): str(row["key"]) for row in plan["rows"]}


def verify_rows(rows: list[dict[str, Any]], derived: dict[str, str],
                held: dict[str, list[str]] | None = None) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    """What the TREE now says about each signed row: (per-row FAULTS, per-row NAME COLLISIONS).

    THE DEFECT THIS REPLACES (BUG-930/D-3095, MEASURED 2026-10-18). This gate asked ONE boolean — "is this row
    still a candidate?" — and answered "no" with a batch-wide FATAL. On the owner's 237-row plan that aborted 109
    outstanding acts over 12 rows, and neither the block nor the count was true:

      * 9 of the 12 carried bytes a receipt had ALREADY admitted from another library path — the work is in the
        corpus and the row is redundant (D-3092). A fault was recorded where the ACT WAS FULFILLED.
      * 3 are the D-3045 format duplicates (a .docx and a .pdf of one work) that ONLY THE OWNER may name. A
        question only a human can answer drove a FATAL — the exact category error BUG-923 fixed one layer down,
        where a deferral drove rc 1 instead of rc 2.

    So the gate now classifies instead of judging, and every class has one owner:

      SATISFIED — the row's own target is on disk: an earlier tranche of THIS signature applied it (BUG-922). Not
                  a fault. `apply_row` still decides, because it holds the receipt index.
      QUESTION  — no index holds the target, but the corpus (or an ingest record) holds this NAME: the D-3045
                  question. Named, deferred, rc 2 — never copied, and never a fatal (BUG-457).
      FAULT     — no target, no name held anywhere: the row did not become a question, it became UNREADABLE (its
                  source is gone, its bytes moved, or the door now refuses the file itself). Named per row, and
                  REFUSED per row — not a verdict on the other 108 rows of the same signature.
      KEY MOVED — the door still reads the row as a candidate under a DIFFERENT key than the one the owner signed:
                  a fault, because the act on the signature and the act the tree would perform are not one act.
    """
    faults: list[tuple[str, str]] = []
    collisions: dict[str, list[str]] = {}
    for row in rows:
        rel = str(row["rel"])
        if rel in derived:
            if derived[rel] != str(row["key"]):
                faults.append((rel, f"the door's key moved ({derived[rel]!r} != {row['key']!r}) — the act on the "
                                    f"signature is no longer the act this tree would perform"))
            continue
        if Path(str(row["target"])).is_file():
            continue  # already applied by an earlier tranche — not a staleness (BUG-922)
        collision = (held or {}).get(str(row["key"])) or []
        if collision:
            collisions[rel] = list(collision)
            continue
        faults.append((rel, f"no index holds this name and the door no longer reads it as a candidate — "
                            f"{_unreadable_reason(row)}"))
    return faults, collisions


def _unreadable_reason(row: dict[str, Any]) -> str:
    """WHY a signed row stopped resolving, in the row's own terms — a fault an owner can act on (D-3034)."""
    source = Path(str(row["path"]))
    if not source.is_file():
        return "the source file is gone (the plan names bytes that no longer exist)"
    size = int(row.get("bytes") or -1)
    if size != source.stat().st_size:
        return f"the source changed since the plan was derived ({size} -> {source.stat().st_size} bytes)"
    return ("the door now refuses the file ITSELF — its folder, its name or its container — so no word about "
            "identity can admit it: re-derive the plan to read the class (T-181)")


# ---------------------------------------------------------------------------------------------------------------------
# THE RECEIPT — an act that leaves no trace did not happen (D-3036)
# ---------------------------------------------------------------------------------------------------------------------
def receipt_path(decl: dict[str, Any], stamp: str | None = None) -> Path:
    """The declared receipt home, one JSONL per run (never a single file this writer keeps appending to)."""
    when = stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return resolve_root(f"{decl['receipt_prefix']}{when}{decl['receipt_extension']}")


def append_receipt(path: Path, record: dict[str, Any]) -> None:
    """Append ONE line and fsync — a crash between two rows leaves the first row proved, not lost."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def read_receipts(decl: dict[str, Any]) -> list[dict[str, Any]]:
    """Every record every receipt carries — ONE reader for the indexes built from them (never a second derivation).

    A receipt this writer cannot read is LOUD (C16): it may not be treated as "no receipt", because that is how a
    rerun becomes a licence to overwrite bytes nobody can account for.
    """
    base = resolve_root(decl["receipt_prefix"])
    folder, stem = base.parent, base.name
    records: list[dict[str, Any]] = []
    if not folder.is_dir():
        return records
    for path in sorted(folder.glob(f"{stem}*{decl['receipt_extension']}")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            # C16: a receipt this writer cannot read is LOUD - it may not be treated as "no receipt".
            raise ApplierError(f"FATAL: receipt {path} cannot be read ({type(exc).__name__}: {exc})") from exc
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                #: BUG-927: A TORN TAIL IS NOT A CORRUPT RECEIPT. MEASURED 2026-10-18: this reader parses the
                #: receipt a RUNNING batch is still appending to (the day's own file grew 276 -> 422 records while
                #: the owner's tranches ran), so the LAST line can be half-written at the instant it is read. The
                #: old rule made that a FATAL "receipt carries a line that is not JSON" — a false fault, of exactly
                #: the shape that sends the owner round the loop again. Only the FINAL line may be skipped, and it
                #: is NAMED on the way past; every earlier line stays FATAL, because an interior gap is corruption
                #: and silence about it is how a rerun becomes a licence to overwrite bytes nobody can account for.
                if index == len(lines) - 1:
                    print(f"NOTE: {path.name} ends mid-line (a batch is still writing it) — that partial line is "
                          f"not a record yet and is not read; every earlier line parsed")
                    continue
                raise ApplierError(f"FATAL: receipt {path} carries a line that is not JSON: {line[:80]!r}") from exc
            record["_receipt"] = path.name
            records.append(record)
    return records


def receipt_index(decl: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every target a previous run accounted for, by target path — the only thing that makes a rerun honest.

    A LATER REFUSAL MAY NOT ERASE AN EARLIER ADMISSION (BUG-932, MEASURED 2026-10-18 on the day's own receipt).
    The index was written LAST-WINS, so this ordinary sequence hid an admitted work from its own record:

        applied  …/Financial/Start-Up-Programme-Finance-Workbook-January-2013.docx  (md_sha256 e7ad6ab1…)
        refused  …/Financial/Start-Up-Programme-Finance-Workbook-January-2013.md    (no digest)

    Both rows write the SAME markdown target (the work is in the library twice: as the .docx that was converted and
    as the .md that is already a work). The refusal was itself a false fault of the old pre-BUG-928 code, but it did
    not merely linger: it OVERWROTE the applied record in the index, so every later run read "the markdown target
    already exists and NO receipt accounts for it" about a file whose admission was accounted for twice over. An
    index that lets a record with NO BYTES outrank a record WITH them is asking the weaker evidence first.

    So the rank is the evidence: `applied`/`already_applied` (a target proved by digest) outrank `failed`/`refused`
    (an attempt that proved nothing), and within a rank the last record wins (a later re-admission is the current
    truth). A target whose ONLY record is a refusal still refuses — the refusal is not ignored, it is only not
    allowed to speak louder than an admission.
    """
    rank = {"applied": 2, "already_applied": 2, "failed": 1, "refused": 1}
    index: dict[str, dict[str, Any]] = {}
    for record in read_receipts(decl):
        state = str(record.get("state") or "")
        if state not in rank:
            continue
        for path in (str(record.get("md_target") or ""), str(record.get("container_target") or "")):
            if not path:
                continue
            prior = index.get(path)
            if prior is None or rank[state] >= rank.get(str(prior.get("state") or ""), 0):
                index[path] = record
    return index


def admitted_bytes(decl: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every byte-sequence a receipt already ADMITTED, by digest (D-3092/BUG-921) — the corpus asked by BYTES.

    WHY A SECOND INDEX (C12 forbids a second home, so this states what the first one cannot answer): `receipt_index`
    is keyed by TARGET PATH, and the question here is not "is this path taken" but "does the corpus already hold
    these bytes under ANY path". MEASURED 2026-10-18: the same work sat in two library folders
    (`business-notes/pdf/...` admitted, `business-pdf/...` then deferred against its twin's own output), so a
    path-keyed lookup could not see it and the door asked the owner which work it was.

    Only APPLIED acts are indexed: a `failed`/`refused`/`deferred` record proves nothing about bytes being held, and
    `skipped` means the bytes are in the corpus but not as a work. An empty digest (a dry run, BUG-882) is never
    indexed — an unproven key would make one row vouch for another.
    """
    admitted: dict[str, dict[str, Any]] = {}
    for record in read_receipts(decl):
        digest = str(record.get("source_sha256") or "")
        if digest and record.get("state") in ("applied", "already_applied"):
            admitted.setdefault(digest, record)
    return admitted


def decided_acts(decl: dict[str, Any], held: dict[str, list[str]] | None = None
                 ) -> dict[tuple[str, str], dict[str, Any]]:
    """The acts a PRIOR receipt already DECIDED, by (rel, target) — BUG-924, and the reason a batch converges.

    MEASURED 2026-10-18 on the day's own receipts: 20 rows were attempted in MORE THAN ONE tranche and one failed
    row was copied, converted and quarantined THREE times (20261018T132104Z -> T132142Z -> T134204Z). Every re-run
    of `--limit N` re-walked the same prefix and re-paid for work already concluded.

    `skipped` and `deferred` are DECIDED FOR A GIVEN ACT: the S0 skip is a property of those bytes, and the door's
    deferral is a property of that NAME colliding with one the corpus holds. Neither is a coin to re-flip, and
    neither can change without the ACT changing (a repaired name re-derives a new target = a new act, and then this
    lookup misses and the row is attempted again). `applied` is deliberately NOT here: `apply_row` re-proves an
    applied target by DIGEST, and skipping that check would trade a repeated read for a blind one.

    A DEFERRAL IS DECIDED ONLY WHILE ITS COLLISION IS STILL THERE (D-3095). A skip is a property of the BYTES, which
    cannot change without the act changing; a deferral is a property of a COLLISION, and a collision can be removed
    by someone else — the owner moves the corpus copy away, or a re-derivation lands the work under that name. Held
    forever, the record would silently refuse to re-attempt a row that is now plainly admittable, and the owner
    would see rc 0 with a work still outside the corpus (BUG-920's shape: a claim honoured after its grounds are
    gone). So `held` — the live name index — decides it, and a reopened act is simply attempted.
    """
    decided: dict[tuple[str, str], dict[str, Any]] = {}
    for record in read_receipts(decl):
        state = record.get("state")
        if state == "skipped":
            decided[(str(record.get("plan_row") or ""), str(record.get("md_target") or ""))] = record
        elif state == "deferred" and (held is None or str(record.get("key") or "") in held):
            decided[(str(record.get("plan_row") or ""), str(record.get("md_target") or ""))] = record
    return decided


def split_decided(rows: list[dict[str, Any]], decided: dict[tuple[str, str], dict[str, Any]]
                  ) -> tuple[list[dict[str, Any]], int]:
    """(the acts still OUTSTANDING, how many a prior receipt already decided) — a tranche is taken from the first.

    The unit is the ACT (rel + target), not the row label: the same label with a different target is a different
    act, and it is attempted. `--limit` therefore counts WORK, not positions, which is what makes `--limit 50`
    five tranches of fifty rather than five looks at the same fifty.
    """
    outstanding: list[dict[str, Any]] = []
    already = 0
    for row in rows:
        if (str(row["rel"]), str(row["target"])) in decided:
            already += 1
        else:
            outstanding.append(row)
    return outstanding, already


# ---------------------------------------------------------------------------------------------------------------------
# THE WRITE — crash-safe copy (C6), then S0 turns the container into the work
# ---------------------------------------------------------------------------------------------------------------------
def copy_atomic(source: Path, target: Path) -> None:
    """tempfile -> fsync -> os.replace IN THE TARGET DIRECTORY, so a crash leaves one whole file or none."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.stem}.", suffix=target.suffix + ".tmp")
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as src:
            shutil.copyfileobj(src, out, CHUNK)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)  # the only deletion here: this writer's OWN half-written temp file
        raise


def quarantine_copy(paths: list[Path], decl: dict[str, Any], run_stamp: str, why: str,
                    *, rel: str = "") -> list[str]:
    """MOVE the files THIS row created out of the corpus, so the corpus holds only works (BUG-887/D-3071).

    WHY A MOVE AND NOT A DELETE: R-D410 forbids this writer to delete (its only unlink is its own half-written
    temp file), and the bytes of a failed conversion are EVIDENCE — they are what a later reader inspects to learn
    why a work would not convert. A move keeps every byte, leaves the source untouched, and is recorded in the
    receipt beside the reason.

    WHY OUTSIDE THE CORPUS, and not a dot-folder inside it: `pipeline/stage0_convert.py::find_books` discovers
    books with `rglob('*<ext>')` and skips no dot-directory, so a quarantine inside the corpus would be re-read
    and would fail again on EVERY later run. MEASURED 2026-10-17 (the owner's first tranche): one unreadable
    container left in the corpus turned `Stage 0 FAILED: 1/941 ... 0.1% > max_failed_ratio=0.0` — a single bad
    byte-source halted the whole conversion stage for everything else. The destination is DECLARED
    (`admission.applier.quarantine_prefix`), never spelled here (C12), and each run writes below its own stamp.
    """
    base = resolve_root(str(decl["quarantine_prefix"])) / run_stamp
    home = base / Path(rel).parent if rel else base
    moved: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        #: BUG-936 — A QUARANTINE THAT DROPS THE FOLDER DESTROYS EVIDENCE. MEASURED 2026-10-18: the destination was
        #: `base / path.name`, so FOUR distinct works called `*GYST_README!.rtf` (four GYST folders) were moved onto
        #: ONE path, each `shutil.move` replacing the previous one, and the survivor is now gone altogether; over
        #: every receipt, 398 destinations and 3 of them are claimed by more than one DIFFERENT source. The safety
        #: net was the thing losing bytes. The row's own `rel` restores the folder dimension, and a name that STILL
        #: collides is disambiguated by the digest of its source path (unique per work) instead of being replaced.
        destination = home / path.name
        if destination.exists():
            tag = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:8]
            destination = destination.with_name(f"{destination.stem}.{tag}{destination.suffix}")
        if destination.exists():
            #: last resort: REFUSE rather than replace. Evidence that is overwritten cannot be recovered by any
            #: later reader, and a quarantine that silently loses a byte-source is worse than a failed row.
            raise ApplierError(
                f"FATAL: quarantine destination {destination} already holds another work's bytes — refusing to "
                f"replace evidence (BUG-936). Nothing was moved for this path; the row is left as it was."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        moved.append(str(destination))
    return moved


def stage0_code_binding() -> tuple[str, str]:
    """(the code fingerprint the S0 checkpoint records, the one this code has) — BUG-933's pre-flight.

    WHY THE APPLIER ASKS THIS AT ALL. This writer runs S0 once per row, so every row appends to ONE checkpoint. When
    that checkpoint was written by different code, S0 refuses to run (BUG-614 is right to), and the refusal arrives
    as a PER-ROW failure: MEASURED 2026-10-18, three rows of the owner's signed plan were copied into the corpus,
    refused by the guard and quarantined while the batch reported `failed` — and every later row of the signature
    would have paid the same cost. A condition about the CODE is not a verdict on a BOOK, so it is asked ONCE,
    before a byte is copied (D-3095's shape, one level up: a global condition is never recorded as a row fault).
    """
    return read_stage_code_fingerprint(STAGE0_CHECKPOINT) or "", stage_code_fingerprint("stage0")


def conversion_argv(container: Path, corpus: Path) -> list[str]:
    """The declared conversion entrypoint, given the row's OWN path below the corpus home (never a bare name)."""
    rel = container.relative_to(corpus)
    return [sys.executable, str(_PROJECT_ROOT / "pipeline" / "stage0_convert.py"), "--book", str(rel)]


def target_paths(row: dict[str, Any], corpus: Path) -> tuple[Path, Path]:
    """(container target, markdown target) for one row, both INSIDE the declared corpus home or FATAL."""
    md_target = Path(str(row["target"]))
    container_target = md_target if str(row["kind"]) == "md" else md_target.with_suffix(f".{row['kind']}")
    root = corpus.resolve()
    for path in (md_target, container_target):
        if not path.resolve().is_relative_to(root):
            raise ApplierError(
                f"FATAL: {path} escapes the declared corpus home {corpus} — a row may not write outside the one "
                f"tree the pipeline reads (D-3034)"
            )
    return container_target, md_target


def apply_row(row: dict[str, Any], corpus: Path, decl: dict[str, Any], index: dict[str, dict[str, Any]],
              *, apply: bool, convert: bool, run_stamp: str = "",
              admitted: dict[str, dict[str, Any]] | None = None,
              held: list[str] | None = None, refusal: str = "") -> dict[str, Any]:
    """Decide and (when `apply`) perform ONE row. Returns the receipt record; never raises for a refusal.

    `held` is what the corpus (or an ingest record) says it already holds under this row's NAME, and `refusal` is
    the per-row verdict `verify_rows` reached when no index held it (D-3095). Both arrive from the caller so this
    function still DECIDES NOTHING about identity: it reads the declaration and records what the declaration says.
    """
    source = Path(str(row["path"]))
    container_target, md_target = target_paths(row, corpus)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plan_row": str(row["rel"]),
        "key": str(row["key"]),
        "source": str(source),
        "container_target": str(container_target),
        "md_target": str(md_target),
        "state": "",
        "reason": "",
    }
    if refusal:
        #: A FAULT THE GATE CAN ALREADY NAME (D-3095): the row is not applied and not asked about, because the tree
        #: says the file itself is unreadable (gone, moved size, or refused by the door for its own properties).
        record.update(state="refused", reason=refusal)
        return record
    if not source.is_file():
        record.update(state="refused", reason="the source file is gone (the plan names bytes that no longer exist)")
        return record
    source_digest = ""
    if int(row.get("bytes") or -1) != source.stat().st_size:
        record.update(state="refused",
                      reason=f"the source changed since the plan was derived ({row.get('bytes')} -> "
                             f"{source.stat().st_size} bytes)")
        return record
    # BUG-882: a DRY RUN PRICES the work. Hashing here read every source in full — 8.0 GiB over 479 rows, and on
    # this Dropbox-backed library an unmaterialised PDF STALLED the reading for minutes (row 309, 2026-10-17).
    # `stat` answers "did it change" in microseconds; the digest is EVIDENCE of the ACT and is taken only when acting.
    # D-3095 ADDED ONE BOUNDED EXCEPTION and it does not spend BUG-882: a row the corpus already holds BY NAME is
    # priced as a QUESTION, and the digest is the only thing that can answer it (bytes beat the name, D-3092). The
    # set is bounded by the WORLD — a row no index holds never appears here — so a pricing run still reads nothing
    # but the handful of files the tree has already narrowed to a collision (12 of 237 rows on 2026-10-18).
    if apply or held:
        source_digest = sha256_bytes(source)
    record["source_sha256"] = source_digest
    #: The rename rides FIRST (T-176): an admitted name is the corpus name AND the door's key.
    patterns = plan_admission.name_patterns(census.policy(POLICY))
    if census.classify(source.name, patterns):
        record.update(state="refused", reason="the name still matches a declared defect pattern (repair first, T-176)")
        return record
    #: A target this writer cannot account for is not overwritten.
    for path, label in ((md_target, "markdown target"), (container_target, "container target")):
        if path.exists():
            prior = index.get(str(path)) or {}
            if prior.get("state") in ("applied", "already_applied") and str(prior.get("md_sha256") or "") == sha256_bytes(path):
                record.update(state="already_applied", reason=f"the {label} is on disk and a receipt accounts for it")
                record["md_sha256"] = prior.get("md_sha256", "")
                return record
            record.update(state="refused",
                          reason=f"the {label} already exists and NO receipt accounts for it: {path}")
            return record
    if path_inside(corpus, source):
        record.update(state="already_applied", reason="the source ALREADY lives inside the corpus home")
        return record
    #: D-3092/BUG-921 — TWO ROWS, ONE WORK. The RECEIPTS are asked before the door is, because a receipt says what
    #: was ADMITTED while the door can only say what the corpus is NAMED. MEASURED 2026-10-18: 28 of 34 deferrals in
    #: one run were the same bytes admitted minutes earlier from another library path, and every one of them asked
    #: the owner to adjudicate an identity the receipts had already resolved. The proof is the digest, which `apply`
    #: takes anyway (BUG-882 forbids hashing in a dry run, so a dry run cannot resolve this and says so).
    if admitted and source_digest:
        twin = admitted.get(source_digest)
        if twin:
            twin_target = Path(str(twin.get("md_target") or ""))
            twin_digest = str(twin.get("md_sha256") or "")
            if twin_target.is_file() and twin_digest and sha256_bytes(twin_target) == twin_digest:
                record.update(state=same_bytes_policy(decl)["state"],
                              reason=f"these exact bytes are already admitted at {twin_target} (receipt "
                                     f"{twin.get('_receipt')}, plan row {twin.get('plan_row')}): the work is in the "
                                     f"corpus and this copy is redundant — nothing was copied or converted")
                record["duplicate_of"] = str(twin_target)
                return record
            #: THE RECORD HAS NO BYTES (BUG-920's mirror): a receipt naming an output that is NOT on disk does not
            #: prove the work is held, so this row is CONVERTED here. Both halves are named on the line — one half
            #: may never silently vouch for the other.
            record["twin_without_bytes"] = str(twin_target)
    if held:
        #: BUG-930/D-3095 — THE CORPUS HOLDS THIS NAME AND NOT THESE BYTES. Reached only after `same_bytes` above
        #: has refused to find the bytes, i.e. the row is a DIFFERENT WORK of a name the corpus already carries (or
        #: one work in two formats). Nothing is copied and nothing is quarantined: copying would land a second
        #: container under a name S0 then refuses to convert, and quarantining it would move a file the owner has
        #: not been asked about. The owner's question is recorded once, named, and it is rc 2 — never rc 1.
        policy = name_held_policy(decl)
        record.update(state=policy["state"],
                      reason=(f"{policy['meaning']} | held by: {'; '.join(held)}"
                              + (f" | a receipt names a twin output that is NOT on disk ({record['twin_without_bytes']}) "
                                 f"— so those bytes prove nothing (BUG-920)"
                                 if record.get("twin_without_bytes") else "")))
        record["held_by"] = list(held)
        return record
    #: BUG-886/D-3071 — A SUFFIX IS A CLAIM, THE BYTES ARE THE FACT. The PLAN now refuses a container no stage can
    #: open, but a plan may be OLDER than the bytes it priced (a download that completed mid-flight, a file
    #: replaced at the same size), and this ACT is where the cost of trusting a suffix is actually paid: MEASURED
    #: 2026-10-17, one 137 MB truncated `.epub` was copied into the corpus and then failed S0. So the act asks
    #: again, and asks BEFORE the copy — the refusal is cheap and the copy is not.
    probes = probes_from(decl, ApplierError)
    probe = probes.get(f".{str(row['kind']).lower()}")
    if probe is None:
        raise ApplierError(
            f"FATAL: the row's kind {row['kind']!r} declares no readability probe "
            f"({sorted(probes)}) — an accepted kind nobody checks is admitted on its suffix alone (C12)"
        )
    if not is_readable(source, probe):
        record.update(state="refused",
                      reason=f"the source is not a readable .{row['kind']} container (declared probe {probe!r}): the "
                             f"stage that would read it cannot OPEN it, so the remedy is a re-download of the work, "
                             f"not an admission — nothing was copied")
        return record
    if not apply:
        record.update(state="would_apply", reason="dry run: nothing was written")
        return record
    try:
        copy_atomic(source, container_target)
    except OSError as exc:
        record.update(state="failed", reason=f"the crash-safe copy failed ({type(exc).__name__}: {exc})")
        return record
    record["container_sha256"] = sha256_bytes(container_target)
    if str(row["kind"]) == "md":
        record.update(state="applied", md_sha256=record["container_sha256"],
                      reason="native markdown: copied, no conversion stage reads it")
        return record
    if not convert:
        record.update(state="failed", reason="--no-convert was given: the container landed but is NOT a work yet")
        return record
    argv = conversion_argv(container_target, corpus)
    try:
        done = subprocess.run(argv, cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=S0_STAGE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        record.update(state="failed", reason=f"S0 could not be run ({type(exc).__name__}: {exc})")
        return record
    #: A failed S0 prints its banner to STDOUT and its traceback to STDERR; `stdout or stderr` threw the
    #: traceback away whenever stdout was non-empty, so a code-drift RuntimeError reached the receipt as the
    #: bare banner and the REAL cause was invisible (C16 — a silent error). Append stderr AFTER stdout so the
    #: tail carries the traceback when there is one, and is unchanged on a clean success (stderr empty).
    captured = (done.stdout or "") + (("\n" + done.stderr) if (done.stderr or "").strip() else "")
    tail = " | ".join(line.strip() for line in captured.strip().splitlines()[-3:])
    #: WHAT S0 CONCLUDED, IN ITS OWN DECLARED WORDS (BUG-923). S0 can say something that is NOT a conversion and
    #: NOT a fault: the scan carries no text layer (owner policy: convert-text-only, no OCR), or the door DEFERRED
    #: the work because its name collides with one the corpus already holds and only the OWNER may decide which
    #: work that is (D-3045). MEASURED 2026-10-18: ONE of those two tokens was recognised in this writer
    #: (`S0_SKIPPED_IMAGE_HEAVY`, 85 rows) and the OTHER was not — 7 rows the door had deferred were written
    #: `failed`, which drove the batch's fail-closed exit and told the owner a tranche was broken when it had done
    #: exactly what the door said. Both tokens now come from `applier.s0_outcome_tokens` (C12), the sentence in the
    #: receipt comes from the same declaration, and an unmapped token stays what it must be: a FAILED conversion.
    tokens = s0_outcome_tokens(decl)
    outcome = next((state for state, spec in tokens.items() if spec["token"] in captured), "")
    if outcome:
        named = next((line.strip() for line in captured.splitlines() if tokens[outcome]["token"] in line), "")
        why = f"S0 {outcome.upper()} — {tokens[outcome]['meaning']}"
        if named and named != tokens[outcome]["token"]:
            why += f" | {named[:300]}"
        moved = quarantine_copy([container_target, md_target], decl,
                                run_stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"), why,
                                rel=str(row["rel"]))
        record.update(state=declared_state(outcome, decl), reason=why)
        record["quarantine"] = moved
        return record
    if done.returncode != 0 or not md_target.is_file() or md_target.stat().st_size < MIN_WORK_BYTES:
        #: BUG-887/D-3071 — THE CORPUS HOLDS WORKS, NOT ATTEMPTS. Leaving the copy behind cost twice: the next plan
        #: read its KEY as `already_in_the_corpus` (so a work that never arrived was silently absorbed and could
        #: never be retried through this door), and every later S0 run re-failed on it under max_failed_ratio 0.0.
        #: The row still FAILS loudly — what changes is only WHERE its bytes rest.
        why = (f"S0 rc={done.returncode}, markdown "
               f"{'absent' if not md_target.is_file() else 'too small'} — {tail[:400]}")
        moved = quarantine_copy([container_target, md_target], decl,
                                run_stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"), why,
                                rel=str(row["rel"]))
        record.update(state="failed", reason=why)
        record["quarantine"] = moved
        record["reason"] += (f" | the copy was MOVED out of the corpus to {moved[0]}" if moved
                             else " | nothing was left in the corpus")
        return record
    record.update(state="applied", md_sha256=sha256_bytes(md_target), reason=f"S0 rc=0 — {tail[:200]}")
    return record


def stamp(record: dict[str, Any], header: dict[str, Any]) -> dict[str, Any]:
    """Carry the RUN's identity onto a row: a receipt line without the plan digest cannot be tied to a signature."""
    record.update(plan=header["plan"], plan_sha256=header["plan_sha256"], accept=header["accept"],
                  pipeline_commit=header["pipeline_commit"])
    return record


def path_inside(root: Path, path: Path) -> bool:
    """True when `path` already resolves inside `root` (a source in the corpus is not an admission)."""
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def shadowed_module_names(source: str) -> list[str]:
    """Local bindings that shadow a module-level callable of the SAME file — the defect class of BUG-881.

    WHY a class and not the instance: `stamp = datetime.now(...)` inside `run()` made the module's own
    `stamp(...)` call a `TypeError: 'str' object is not callable` at the moment the operator ran the ACT.
    No control caught it because the controls called `stamp()` directly — they tested the UNIT, the crash lived
    in the COMPOSITION. A name bound locally over a module-level callable is unreachable from that point on, and
    Python reports it only when that line finally executes. So the check is static, whole-file, and reads the
    file's own bytes: it names every function/class of module scope that some function binds over.
    """
    tree = ast.parse(source)
    module_level = {node.name for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    findings: list[str] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bound: set[str] = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                targets: list[ast.expr] = list(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.For)):
                targets = [node.target]
            else:
                continue
            bound.update(t.id for t in targets if isinstance(t, ast.Name))
        findings += [f"{fn.name}:{name}" for name in sorted((bound & module_level) - {fn.name})]
    return findings


# ---------------------------------------------------------------------------------------------------------------------
# THE RUN
# ---------------------------------------------------------------------------------------------------------------------
def run(plan_path: Path | None, accept_path: Path | None, *, apply: bool, convert: bool, limit: int | None,
        json_out: bool) -> int:
    """One batch: read the plan, read the signature, verify, then apply (or say exactly what would happen)."""
    doc = census.policy(POLICY)
    decl = applier_policy(doc)
    corpus = plan_admission.home_path(doc["source_library"]["arrangement"], "corpus_home")

    #: BUG-931 — THE WORD NAMES THE PLAN, NOT THE CLOCK. No re-derivation may make a valid signature unusable, and
    #: `newest()` must never decide which DOCUMENT an owner signed. So the signature is read FIRST and, when the
    #: operator named no plan, ITS plan is the one applied. An explicit `--plan` still has to agree with the
    #: signature (`load_acceptance` refuses the disagreement: there the owner chose the document, so the
    #: disagreement is real). MEASURED 2026-10-18: the reverse order took `newest()` (a fresh stamped plan) and then
    #: refused a signature whose `scope_sha256` still matched the signed plan exactly — a loop with no fault in it.
    accept_path = accept_path or newest(str(decl["accept_prefix"]), str(decl["accept_extension"]))
    if plan_path is None and accept_path is not None and accept_path.is_file():
        plan_path = acceptance_plan(accept_path, decl)
    if plan_path is None:
        plan_path = newest(str(plan_admission.admission_policy(doc)["plan_prefix"]), ".json")
    if plan_path is None or not plan_path.is_file():
        raise ApplierError(
            f"FATAL: no plan found under {plan_admission.admission_policy(doc)['plan_prefix']}*.json — derive one "
            f"first: {plan_admission.admission_policy(doc)['reading'].split('|')[2].strip()}"
        )
    plan = load_plan(plan_path)
    plan_digest = sha256_bytes(plan_path)

    if accept_path is None or not accept_path.is_file():
        rows = plan["rows"]
        total = sum(int(row.get("bytes") or 0) for row in rows)
        print(f"OWNER-OWED: no signed acceptance under {decl['accept_prefix']}*{decl['accept_extension']}")
        print(f"            {plan_path.name} holds {len(rows)} candidate row(s), {total / 2**20:.1f} MiB to copy")
        print(f"            a signature names the plan's digest ({plan_digest}) and the rows it puts in scope;")
        print(f"            nothing is written until one exists (mode is declared in {POLICY})")
        return RC_OWNER_OWED
    acc = load_acceptance(accept_path, plan_path, plan_digest, decl)
    signed, _ = selected_rows(plan, acc)
    #: THE WORD IS CHECKED AGAINST THE ACTS, before a tranche limit narrows them: `--limit` decides how many of the
    #: SIGNED rows this run takes, never which acts were authorised.
    signed_by = verify_scope(acc, plan_path, plan_digest, signed, signed, decl)
    #: BUG-924: THE TRANCHE COUNTS WORK, NOT POSITIONS. `rows[:limit]` took the first N SIGNED rows, so every later
    #: tranche re-walked the same prefix — MEASURED 2026-10-18 on the day's own receipts: 20 rows were attempted in
    #: more than one tranche and one already-failed row was copied, converted and quarantined THREE times. An act a
    #: receipt has already DECIDED is reported, never re-performed, and does not consume the tranche.
    #: D-3095: the name index is built BEFORE the decision, because a DEFERRAL is decided only while its collision
    #: is still there (see `decided_acts`) — a question whose grounds are gone is not a question any more.
    held = held_names(decl, doc, corpus)
    outstanding, decided_here = split_decided(signed, decided_acts(decl, held))
    rows = outstanding if limit is None else outstanding[:limit]
    if decided_here:
        print(f"DECIDED  {decided_here} act(s) a prior receipt already decided (skipped/deferred) — not re-attempted; "
              f"{len(outstanding)} outstanding, this run attempts {len(rows)}")

    #: BUG-930/D-3095 — THE GATE CLASSIFIES, AND A FAULT IS NOT A VERDICT ON THE WHOLE BATCH. MEASURED 2026-10-18:
    #: this raised here and aborted 109 outstanding acts over 12 rows, of which 9 were redundant by BYTES and 3 were
    #: the owner's own format-duplicate questions. The authorisation is still checked HARD and EARLY (`verify_scope`,
    #: above, which is about the SIGNATURE); this gate is about the WORLD, and the world is decided row by row.
    faults, collisions = verify_rows(rows, derive(), held)
    fault_by_rel: dict[str, str] = {}
    for rel, why in faults:
        fault_by_rel[rel] = why
        print(f"REFUSED  {rel}: {why[:200]}")
    if collisions:
        #: BUG-934 — a QUESTION IN FLIGHT, with no exit code named: see `asking_line`.
        print(asking_line(collisions))
    if fault_by_rel:
        print(f"NOTE: {len(fault_by_rel)} row(s) are REFUSED INDIVIDUALLY — the other {len(rows) - len(fault_by_rel)} "
              f"act(s) of this signature are still performed (a fault in one row is not a verdict on the rest)")

    #: BUG-933 — ASK THE CODE BINDING ONCE, BEFORE ANY COPY. See `stage0_code_binding`.
    code_blocked = ""
    if convert:
        stored_fp, current_fp = stage0_code_binding()
        if stored_fp and stored_fp != current_fp:
            code_blocked = (
                f"S0's checkpoint ({STAGE0_CHECKPOINT.name}) was produced by DIFFERENT code (stored {stored_fp}, "
                f"current {current_fp}), so every conversion of this batch would be refused by the guard and its "
                f"copy would be quarantined (BUG-933). Nothing was copied. Remedy: if the change was a READER fix, "
                f"declare it and re-bind: `python3 pipeline/stage0_convert.py --rebind-code-fingerprint --why "
                f"'<what changed and why it cannot change a conversion>'`")
            if apply:
                raise ApplierError(f"FATAL: {code_blocked}")
            print(f"BLOCKED  {code_blocked}")

    free = shutil.disk_usage(str(corpus)).free
    need = sum(int(row.get("bytes") or 0) for row in rows)
    if apply and free < need:
        raise ApplierError(f"FATAL: {need / 2**30:.2f} GiB to copy but {free / 2**30:.2f} GiB free in {corpus}")

    index = receipt_index(decl)
    admitted = admitted_bytes(decl)
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")  # BUG-881: never `stamp` — that name is the FUNCTION below
    out_path = receipt_path(decl, run_stamp)
    header = {"schema_version": SCHEMA_VERSION, "gen_model": GEN_MODEL, "state": "run",
              "ts": run_stamp, "plan": str(plan_path), "plan_sha256": plan_digest,
              "accept": str(accept_path), "accept_sha256": sha256_bytes(accept_path),
              #: D-3072: HOW the signature was proved this run — its own bytes (`digest`) or a re-derived plan whose
              #: ACTS are identical (`scope`). Recorded because "the plan moved but the acts did not" is a fact a
              #: reader of the receipt must be able to see, not infer.
              "signed_by": signed_by, "scope_sha256": scope_digest(signed), "accepted_by": acc["accepted_by"],
              "mode": acc["mode"], "apply": apply, "convert": convert, "rows": len(rows),
              "bytes": need, "pipeline_commit": pipeline_commit()}
    if apply:
        append_receipt(out_path, header)

    counts: dict[str, int] = {}
    for row in rows:
        #: D-3095: the two verdicts the gate reached travel WITH the row, so `apply_row` neither re-derives the world
        #: nor re-reads an index — it records what the declaration says (D-3068: the applier decides nothing).
        record = stamp(apply_row(row, corpus, decl, index, apply=apply, convert=convert, run_stamp=run_stamp,
                                 admitted=admitted, held=collisions.get(str(row["rel"])),
                                 refusal=fault_by_rel.get(str(row["rel"]), "")),
                       header)
        if apply and record["state"] != "would_apply":
            declared_state(str(record["state"]), decl)  # BUG-923: the closed vocabulary is a GATE, not a caption
        counts[record["state"]] = counts.get(record["state"], 0) + 1
        if apply and record.get("state") in ("applied", "already_applied"):
            #: D-3092: THE INDEX IS THE RUN'S OWN MEMORY. It is built once from the receipts that EXISTED when the
            #: batch started, so without this line two copies of one work inside the SAME tranche would still send
            #: the second through the door, where it defers against the first's fresh output and comes back as an
            #: owner question. A row this run has just ADMITTED is therefore added here, so the later copy is named
            #: as redundant instead of being asked about.
            if record.get("source_sha256"):
                admitted.setdefault(str(record["source_sha256"]), record)
            #: BUG-928: AND THE TARGET INDEX IS THE SAME MEMORY. MEASURED 2026-10-18 (final receipt, 449 rows): two
            #: rows of one work recorded `refused — the markdown target already exists and NO receipt accounts for
            #: it`, because the receipt that DOES account for it was written by THIS run, minutes earlier, after
            #: `receipt_index()` had already been built. A refusal that names a fault where the record exists is a
            #: false fault, so both the target and the container are added here the moment they are accounted for.
            for key in ("md_target", "container_target"):
                if record.get(key):
                    index.setdefault(str(record[key]), record)
        if apply:
            append_receipt(out_path, record)
        if json_out:
            print(json.dumps(record, ensure_ascii=False))
        else:
            mark = {"applied": "ADMIT", "already_applied": "  ok", "duplicate_of_admitted": " DUP ",
                    "would_apply": "would", "refused": " NO ", "failed": "FAIL", "skipped": "SKIP",
                    "deferred": "HOLD"}.get(record["state"], record["state"].upper()[:5])
            detail = (record["reason"] if record["state"] in ("refused", "failed", "skipped", "deferred",
                                                              "duplicate_of_admitted")
                      else record["md_target"])
            print(f"{mark} {record['plan_row'][:96]} -> {detail[:140]}")

    summary = {"state": "summary", "counts": counts, "receipt": str(out_path) if apply else None,
               "rows": len(rows), "bytes": need, "decided_by_prior_receipt": decided_here}
    if apply:
        append_receipt(out_path, summary)
        print(f"\n{counts} | receipt: {out_path}")
    else:
        print(f"\nDRY RUN {counts} | nothing written | --apply to perform | receipt would be {out_path}")
    for line in verdict_lines(counts, len(collisions), decl):
        print(line)
    if not apply:
        print("NOTE: a dry run takes NO digest for a row no index holds (BUG-882: hashing 8.0 GiB over a "
              "cloud-backed library stalls), so such a row whose bytes a receipt already holds reads `would_apply` "
              f"here and resolves as {decl['same_bytes']['state']!r} when it is applied. A row the corpus already "
              "holds BY NAME is digested even here, because the digest is the only thing that can answer it (D-3095)")
    return RC_FATAL if code_blocked else batch_rc(counts, decl)

# ---------------------------------------------------------------------------------------------------------------------
# CONTROLS — known answers only (BUG-492: a control nothing runs is a comment)
# ---------------------------------------------------------------------------------------------------------------------
def selftest() -> int:
    """Known-answer controls over a FIXTURE tree: no library file and no receipt of the owner's is touched."""
    checks: list[tuple[str, bool]] = []

    def expect(label: str, condition: bool, detail: str = "") -> None:
        checks.append((label, bool(condition)))
        if not condition:
            print(f"FAIL {label} {detail}")

    def _refuses(call) -> bool:
        """Did this governed act REFUSE? A refusal is the evidence; a return value is not (C16)."""
        try:
            call()
        except ApplierError:
            return True
        return False

    import yaml

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        corpus = tmp_root / "corpus"
        library = tmp_root / "library"
        (corpus / "DOMAIN 1 Test").mkdir(parents=True)
        (library / "epub" / "DOMAIN 1 Test").mkdir(parents=True)
        source = library / "epub" / "DOMAIN 1 Test" / "A Work.epub"
        #: BUG-886: a fixture container must be OPENABLE — the ACT now asks the bytes before it copies, so a fake
        #: `.epub` would make every control below read as a corruption refusal instead of whatever it tests.
        import zipfile
        with zipfile.ZipFile(source, "w") as book:
            book.writestr("mimetype", "application/epub+zip")
            book.writestr("META-INF/container.xml", "<container/>")
        md_source = library / "epub" / "DOMAIN 1 Test" / "A Note.md"
        md_source.write_text("# a note\n" + "text " * 200, encoding="utf-8")

        rows = [
            {"path": str(source), "rel": "books/epub/DOMAIN 1 Test/A Work.epub", "root": "books", "kind": "epub",
             "key": "a work", "bytes": source.stat().st_size,
             "target": str(corpus / "DOMAIN 1 Test" / "A Work.md")},
            {"path": str(md_source), "rel": "books/epub/DOMAIN 1 Test/A Note.md", "root": "books", "kind": "md",
             "key": "a note", "bytes": md_source.stat().st_size,
             "target": str(corpus / "DOMAIN 1 Test" / "A Note.md")},
        ]
        plan_file = tmp_root / "ADMISSION_PLAN_TEST.json"
        plan_file.write_text(json.dumps({"rows": rows}), encoding="utf-8")
        digest = sha256_bytes(plan_file)
        decl = {"accept_modes": ["all", "listed"],
                "accept_required": ["schema_version", "plan", "plan_sha256", "scope_sha256", "accepted_by",
                                    "accepted_on", "mode"],
                "accept_by_identity": str(tmp_root / "owner_identity.yaml"),
                "accept_extension": ".yaml", "receipt_prefix": str(tmp_root / "receipts" / "ADMISSION_APPLIED_"),
                "receipt_extension": ".jsonl", "command": "python3 scripts/apply_admission.py",
                "authority": "D-3068", "accept_prefix": str(tmp_root / "ADMISSION_ACCEPTED_"),
                #: BUG-923: the fixture declares the state vocabulary, the S0 outcome tokens and the exit-code
                #: mapping the way the gate does — they are REQUIRED by the writer, so a fixture that omitted them
                #: would test a writer nobody runs.
                "states": ["run", "would_apply", "applied", "already_applied", "duplicate_of_admitted", "refused",
                           "failed", "skipped", "deferred", "summary"],
                "same_bytes": {"state": "duplicate_of_admitted", "evidence": "source_sha256",
                               "meaning": "these exact bytes are already admitted under another corpus path",
                               "absent_target_means": "the receipt names an output that is NOT on disk: convert it "
                                                       "again rather than write it off (BUG-920)"},
                "name_held": {"state": "deferred", "indexes": ["corpus_index", "ingest_records"],
                              "meaning": "the corpus already holds this NAME with other bytes: the owner's word",
                              "bytes_win": "a row whose bytes are admitted is a duplicate, whatever its name",
                              "absent_means": "no index holds it: unreadable, which is a per-row refusal"},
                "s0_outcome_tokens": {
                    "skipped": {"token": "S0_SKIPPED_IMAGE_HEAVY", "meaning": "no text layer (owner policy)"},
                    "deferred": {"token": "deferred_for_identity", "meaning": "the door deferred it: owner word owed"},
                },
                "exit_codes": {"fatal_states": ["refused", "failed"], "owner_owed_states": ["deferred"]},
                "accept_by_placeholder": "<your name>",
                #: BUG-886/D-3071: the declared probes and the declared quarantine. Both are REQUIRED by the
                #: writer (an absent one is FATAL), so the fixture declares them the way the gate does.
                "container_integrity": {"probes": {".epub": "zip", ".pdf": "pdf", ".md": "none"}},
                "quarantine_prefix": str(tmp_root / "quarantine")}

        accept_file = tmp_root / "ADMISSION_ACCEPTED_TEST.yaml"
        base_accept = {"schema_version": "1.0", "plan": str(plan_file), "plan_sha256": digest,
                       "scope_sha256": scope_digest(rows), "accepted_by": "selftest", "accepted_on": "2026-10-17",
                       "mode": "all", "rows": [row["rel"] for row in rows]}
        accept_file.write_text(yaml.safe_dump(base_accept), encoding="utf-8")

        # 1. D-3072: THE WORD PINS THE ACTS. MEASURED 2026-10-17, twice in one sitting: a signature pinned to the
        #    plan FILE was voided by ANY re-derivation (a probe added, a class count that moved, a timestamp), and
        #    re-printing the signature reset `accepted_by` to the placeholder the applier then refused. Two-sided by
        #    construction: a plan whose ACTS moved must still be REFUSED (naming the row), and a plan re-derived
        #    with identical acts must PASS, or "fixed" becomes "authorised anything".
        moved = dict(base_accept, scope_sha256="0" * 64)
        moved_file = tmp_root / "MOVED.yaml"
        moved_file.write_text(yaml.safe_dump(moved), encoding="utf-8")
        refused, told = False, ""
        try:
            verify_scope(load_acceptance(moved_file, plan_file, digest, decl), plan_file, digest, rows, rows, decl)
        except ApplierError as exc:
            refused, told = True, str(exc)
        expect("a_signature_whose_ACTOR_SCOPE_moved_is_FATAL_and_NAMES_the_change",
               refused and "authorises a DIFFERENT set of acts" in told, told)

        rederived = tmp_root / "ADMISSION_PLAN_REDERIVED.json"
        rederived.write_text(json.dumps({"rows": rows, "generated": "2026-10-17T15:00:00Z",
                                         "counts": {"admit_candidate": 2}}), encoding="utf-8")
        expect("a_re_derived_plan_with_the_SAME_acts_STILL_MATCHES_the_word",
               verify_scope(base_accept, rederived, sha256_bytes(rederived), rows, rows, decl) == "scope")
        expect("a_plan_whose_BYTES_are_the_signed_ones_is_proved_by_its_DIGEST",
               verify_scope(base_accept, plan_file, digest, rows, rows, decl) == "digest")

        shrunk = [rows[0]]
        refused, told = False, ""
        try:
            verify_scope(base_accept, plan_file, digest, rows, shrunk, decl)
        except ApplierError as exc:
            refused, told = True, str(exc)
        expect("a_plan_that_LOST_an_authorised_row_is_FATAL_and_names_it",
               refused and "authorised row(s) the plan no longer holds" in told, told)
        expect("a_signature_that_pins_NO_scope_is_REFUSED",
               _refuses(lambda: verify_scope(dict(base_accept, scope_sha256=""), plan_file, digest, rows, rows, decl)))

        # 1b. BUG-888: a signature that carries the TEMPLATE'S OWN PLACEHOLDER resolved to nothing and was applied
        #     (MEASURED 2026-10-17: the owner's first acceptance held `accepted_by: <your name>`). The name is the
        #     whole authorisation, so an unresolvable one is refused - and a real name still passes (two-sided: a
        #     check that refused every signature would refuse the owner's own act).
        unsigned = dict(base_accept, accepted_by="  <your name>  ")
        unsigned_file = tmp_root / "UNSIGNED.yaml"
        unsigned_file.write_text(yaml.safe_dump(unsigned), encoding="utf-8")
        refused = False
        try:
            load_acceptance(unsigned_file, plan_file, digest, decl)
        except ApplierError:
            refused = True
        expect("a_signature_carrying_the_TEMPLATE_PLACEHOLDER_is_REFUSED", refused)
        expect("a_signature_with_a_REAL_name_still_passes",
               load_acceptance(accept_file, plan_file, digest, decl)["accepted_by"] == "selftest")

        # 2. a row the signature names but the plan does not hold is FATAL
        listed = dict(base_accept, mode="listed", rows=["books/epub/DOMAIN 1 Test/GHOST.epub"])
        listed_file = tmp_root / "LISTED.yaml"
        listed_file.write_text(yaml.safe_dump(listed), encoding="utf-8")
        acc = load_acceptance(listed_file, plan_file, digest, decl)
        refused = False
        try:
            selected_rows({"rows": rows}, acc)
        except ApplierError:
            refused = True
        expect("a_row_absent_from_a_LISTED_acceptance_is_FATAL", refused)

        # 3. dry run writes nothing
        before = sorted(str(p) for p in tmp_root.rglob("*"))
        index = receipt_index(decl)
        dry = apply_row(rows[0], corpus, decl, index, apply=False, convert=False)
        after = sorted(str(p) for p in tmp_root.rglob("*"))
        expect("a_dry_run_writes_no_file_and_no_receipt", before == after and dry["state"] == "would_apply",
               dry["state"])

        # 3b. BUG-882: the DRY RUN prices the work — it does not READ it. A source rewritten to the SAME size with
        #     different bytes stays invisible to the dry run (empty digest) and is caught by the ACT, which takes
        #     the digest because the digest is EVIDENCE of the act. This is the control that a hash cannot creep
        #     back in front of `apply`: on this Dropbox-backed library it read 8.0 GiB and STALLED a pricing run.
        twin = library / "epub" / "DOMAIN 1 Test" / "A Twin.md"
        twin.write_text("AAAA" * 100, encoding="utf-8")
        twin_row = dict(rows[0], path=str(twin), rel="books/epub/DOMAIN 1 Test/A Twin.md", key="a twin", kind="md",
                        bytes=twin.stat().st_size, target=str(corpus / "DOMAIN 1 Test" / "A Twin.md"))
        twin.write_text("BBBB" * 100, encoding="utf-8")  # same size, different bytes
        index = receipt_index(decl)
        priced = apply_row(twin_row, corpus, decl, index, apply=False, convert=False)
        expect("a_dry_run_does_NOT_read_the_source_bytes",
               priced["state"] == "would_apply" and priced["source_sha256"] == "",
               (priced["state"], priced["source_sha256"]))
        index = receipt_index(decl)
        acted = apply_row(twin_row, corpus, decl, index, apply=True, convert=False)
        expect("the_ACT_takes_the_source_digest", acted["state"] == "applied"
               and acted["source_sha256"] == sha256_bytes(twin), (acted["state"], acted["source_sha256"][:12]))

        # 4. a defective name is refused even when the plan carries it — through the WRITER, not a lookup
        bad_source = library / "epub" / "DOMAIN 1 Test" / "A Work (z-lib.org).epub"
        bad_source.write_bytes(b"EPUB-BYTES" * 100)
        bad_row = dict(rows[0], path=str(bad_source), rel="books/epub/DOMAIN 1 Test/A Work (z-lib.org).epub",
                       key="a work (z-lib.org)", bytes=bad_source.stat().st_size,
                       target=str(corpus / "DOMAIN 1 Test" / "A Work (z-lib.org).md"))
        patterns = plan_admission.name_patterns(census.policy(POLICY))
        expect("the_declared_pattern_set_matches_a_marker_name", bool(census.classify(bad_source.name, patterns)))
        expect("a_clean_name_is_not_refused_by_the_pattern_set", not census.classify("A Work.epub", patterns))
        index = receipt_index(decl)
        defective = apply_row(bad_row, corpus, decl, index, apply=True, convert=False)
        expect("a_defective_name_is_REFUSED_even_if_the_plan_carries_it",
               defective["state"] == "refused" and "repair first" in defective["reason"], defective["state"])

        # 5. apply copies the bytes and KEEPS the source
        index = receipt_index(decl)
        done = apply_row(rows[1], corpus, decl, index, apply=True, convert=False)  # native markdown: no S0
        md_target = corpus / "DOMAIN 1 Test" / "A Note.md"
        expect("an_applied_row_copies_the_bytes_and_KEEPS_the_source",
               done["state"] == "applied" and md_target.read_bytes() == md_source.read_bytes()
               and md_source.is_file(), done["state"])

        # 6. the receipt accounts for it, so a rerun is already_applied, not a refusal
        tmp_receipt = receipt_path(decl, "TEST")
        append_receipt(tmp_receipt, done)
        index = receipt_index(decl)
        again = apply_row(rows[1], corpus, decl, index, apply=False, convert=False)
        expect("a_target_a_receipt_accounts_for_is_already_applied", again["state"] == "already_applied",
               again["state"])

        # 7. an unexplained target is REFUSED and its bytes survive
        unexplained = corpus / "DOMAIN 1 Test" / "A Work.md"
        unexplained.write_text("SOMEONE ELSE WROTE THIS", encoding="utf-8")
        index = receipt_index(decl)
        blocked = apply_row(rows[0], corpus, decl, index, apply=True, convert=False)
        expect("an_existing_target_with_no_receipt_is_REFUSED_and_its_bytes_survive",
               blocked["state"] == "refused" and unexplained.read_text(encoding="utf-8") == "SOMEONE ELSE WROTE THIS",
               blocked["state"])

        # 8. a source whose bytes changed is refused
        changed = dict(rows[1], bytes=1)
        index = receipt_index(decl)
        stale = apply_row(changed, corpus, decl, index, apply=False, convert=False)
        expect("a_source_whose_bytes_changed_is_REFUSED", stale["state"] == "refused", stale["state"])

        # 9. an escape from the corpus home is FATAL
        escaped = False
        try:
            target_paths(dict(rows[0], target=str(tmp_root / "elsewhere" / "x.md")), corpus)
        except ApplierError:
            escaped = True
        expect("a_target_outside_the_declared_corpus_home_is_FATAL", escaped)

        # 10. the conversion command names S0 and the row's OWN path below the corpus home
        argv = conversion_argv(corpus / "DOMAIN 1 Test" / "A Work.epub", corpus)
        expect("the_conversion_command_names_S0_and_the_row_own_path",
               argv[-1] == str(Path("DOMAIN 1 Test") / "A Work.epub") and argv[1].endswith("stage0_convert.py"),
               argv)

        # 11. the receipt carries what a later reader needs — including the RUN's identity, via stamp()
        stamped = stamp(done, {"plan": str(plan_file), "plan_sha256": digest, "accept": str(accept_file),
                               "pipeline_commit": "selftest"})
        expect("the_receipt_carries_source_target_key_and_digests",
               all(key in stamped for key in ("source", "container_target", "md_target", "key", "md_sha256",
                                              "pipeline_commit", "plan_sha256", "schema_version", "gen_model")),
               sorted(stamped))

        # 12. the writer owns no prefix of its own: both come from the declaration it was handed
        expect("the_accept_and_receipt_prefixes_come_from_the_declaration",
               str(resolve_root(decl["receipt_prefix"])).startswith(str(tmp_root))
               and str(resolve_root(decl["accept_prefix"])).startswith(str(tmp_root)))

        # 13. the printed template is a VALID signature for THIS plan, pinned to the live digest
        rendered = yaml.safe_load(acceptance_template(plan_file, digest, rows))
        expect("the_acceptance_template_parses_and_pins_the_live_digest",
               rendered["plan_sha256"] == digest and rendered["mode"] == "all"
               and rendered["plan"] == str(plan_file)
               and rendered["scope_sha256"] == scope_digest(rows)
               and rendered["rows"] == [row["rel"] for row in rows], rendered)

        # 14. BUG-881: no local binding shadows a module-level callable of THIS file (the class, not the instance).
        #     The instance was `stamp = <str>` inside run(), which made the module's own stamp() uncallable — and
        #     control 11 below WOULD NOT SEE IT, because it called stamp() directly: the unit, not the composition.
        planted = ("def stamp(r, h):\n    return r\n\n\ndef run():\n    stamp = 'a string'\n"
                   "    return stamp({}, {})\n")
        expect("the_shadow_detector_FINDS_a_planted_shadow",
               shadowed_module_names(planted) == ["run:stamp"], shadowed_module_names(planted))
        expect("a_clean_module_reports_no_shadow", shadowed_module_names("def f():\n    return 1\n") == [])
        own = Path(__file__).read_text(encoding="utf-8")
        expect("THIS_file_binds_no_local_that_shadows_a_module_callable",
               shadowed_module_names(own) == [], shadowed_module_names(own))

        # 16. BUG-886/D-3071: a container whose BYTES do not open is REFUSED BEFORE A BYTE IS COPIED. The plan may be
        #     OLDER than the bytes it priced, and this ACT is where trusting a suffix is actually paid for (MEASURED
        #     2026-10-17: 137 MB copied into the corpus, then S0 failed). TWO-SIDED by construction: control 3 above
        #     drives the SAME row through the SAME probe on a VALID epub and must still read `would_apply`, so a
        #     probe that refused every container would turn that control red.
        truncated = library / "epub" / "DOMAIN 1 Test" / "A Truncated Download.epub"
        truncated.write_bytes(b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 512)
        broken_row = dict(rows[0], path=str(truncated), rel="books/epub/DOMAIN 1 Test/A Truncated Download.epub",
                          key="a truncated download", bytes=truncated.stat().st_size,
                          target=str(corpus / "DOMAIN 1 Test" / "A Truncated Download.md"))
        index = receipt_index(decl)
        corrupt = apply_row(broken_row, corpus, decl, index, apply=True, convert=True)
        expect("a_source_whose_bytes_do_not_OPEN_is_REFUSED_before_a_byte_is_copied",
               corrupt["state"] == "refused" and "cannot OPEN" in corrupt["reason"]
               and not (corpus / "DOMAIN 1 Test" / "A Truncated Download.epub").exists(),
               corrupt["state"])

        # 17. BUG-887/D-3071: a row whose S0 run produces NO work leaves NOTHING in the corpus — the copy is MOVED to
        #     the declared quarantine, never deleted (R-D410) and never left where the next plan would read its key
        #     as `already_in_the_corpus`. MEASURED: the owner's first tranche left a 137 MB container that then made
        #     `Stage 0 FAILED: 1/941 ... > max_failed_ratio=0.0` true for every later run.
        doomed = dict(rows[0], rel="books/epub/DOMAIN 1 Test/A Work.epub", key="a doomed work",
                      target=str(corpus / "DOMAIN 1 Test" / "A Doomed Work.md"))
        index = receipt_index(decl)
        failed = apply_row(doomed, corpus, decl, index, apply=True, convert=True, run_stamp="TESTSTAMP")
        quarantine = tmp_root / "quarantine" / "TESTSTAMP"
        expect("a_row_whose_S0_run_produced_no_work_leaves_NO_container_in_the_corpus",
               failed["state"] == "failed"
               and not Path(failed["container_target"]).exists()
               #: BUG-936: asserted as a PROPERTY, never as a path SHAPE — the first version required the flat
               #: `quarantine/<stamp>/<name>` and went red the moment the folder dimension was restored, which is
               #: a control measuring the bug instead of the rule. What must hold: the corpus holds no attempt, and
               #: the bytes still exist somewhere under the run's own quarantine home.
               and any(Path(p).is_file() for p in failed.get("quarantine") or [])
               and all(str(quarantine) in p for p in failed.get("quarantine") or []),
               (failed["state"], failed.get("quarantine")))

        # 18. D-3072/BUG-892: THE OWNER'S WORD IS ONE COMMAND, AND IT IS GIVEN ONCE. MEASURED 2026-10-17: the name
        #     lived inside a file the tool PRINTS, so every re-derivation reset it to the placeholder and the applier
        #     refused a word already given — the owner ran the same command twice and got the same refusal. Four
        #     sides: a placeholder is refused, a real name is written ONCE and reused, the identity cannot be
        #     silently swapped, and the file the command writes is accepted by the applier that reads it.
        import contextlib
        import io

        def quiet_sign(who: str) -> int:
            with contextlib.redirect_stdout(io.StringIO()):
                return sign(plan_file, decl, who, "all", None)

        identity = resolve_root(str(decl["accept_by_identity"]))
        signed_file = resolve_root(
            f"{decl['accept_prefix']}{datetime.now(UTC).strftime('%Y%m%d')}{decl['accept_extension']}")
        expect("a_signed_word_refuses_a_PLACEHOLDER_or_an_empty_name",
               _refuses(lambda: sign(plan_file, decl, "<your name>", "all", None))
               and _refuses(lambda: sign(plan_file, decl, "   ", "all", None)))
        expect("ONE_command_writes_the_IDENTITY_and_pins_the_LIVE_ACTS",
               quiet_sign("A Human") == RC_OK
               and identity.is_file() and declared_identity(decl) == "A Human"
               and signed_file.is_file()
               and yaml.safe_load(signed_file.read_text(encoding="utf-8"))["scope_sha256"] == scope_digest(rows))
        expect("the_word_that_command_writes_is_ACCEPTED_by_the_applier_that_reads_it",
               verify_scope(load_acceptance(signed_file, plan_file, digest, decl), plan_file, digest, rows, rows,
                            decl) == "digest")
        expect("a_DIFFERENT_name_CANNOT_silently_replace_the_declared_identity",
               _refuses(lambda: sign(plan_file, decl, "Somebody Else", "all", None))
               and declared_identity(decl) == "A Human")
        expect("re_signing_the_SAME_name_is_IDEMPOTENT_and_never_a_second_identity",
               quiet_sign("A Human") == RC_OK and declared_identity(decl) == "A Human")

        # 20. BUG-923 (2026-10-18): THE VOCABULARY IS A GATE AND A DEFERRAL IS NOT A FAILURE. MEASURED: a tranche
        #     that applied 182 works, skipped 85 and DEFERRED 7 exited 1, so `just` printed "Recipe `admit-apply`
        #     failed" at an owner whose batch had done exactly what the door said. Three sides are asserted: the
        #     declared mapping decides the code, a deferral is OWNER-OWED (never fatal, never silent), and a state
        #     outside `states` is refused — the closed list was a caption for as long as nothing enforced it.
        expect("a_batch_that_only_DEFERRED_is_OWNER_OWED_and_never_a_failure",
               batch_rc({"applied": 182, "skipped": 85, "deferred": 7}, decl) == RC_OWNER_OWED
               and batch_rc({"skipped": 85}, decl) == RC_OK
               and batch_rc({"applied": 10}, decl) == RC_OK
               and batch_rc({"deferred": 1, "failed": 1}, decl) == RC_FATAL
               and batch_rc({"refused": 1}, decl) == RC_FATAL,
               batch_rc({"applied": 182, "skipped": 85, "deferred": 7}, decl))
        expect("an_UNDECLARED_state_is_REFUSED_by_the_vocabulary",
               declared_state("deferred", decl) == "deferred"
               and _refuses(lambda: declared_state("nonsense", decl)))
        #: THE TOKEN IS A CONTRACT BETWEEN TWO PROGRAMS, so the control reads the PRODUCER's own bytes: a renamed
        #: token must break a control, not silently turn every skip back into a failure (BUG-492).
        producer = (_PROJECT_ROOT / "pipeline" / "stage0_convert.py").read_text(encoding="utf-8")
        expect("every_declared_S0_outcome_token_EXISTS_in_the_producer_that_prints_it",
               all(spec["token"] in producer for spec in s0_outcome_tokens(decl).values()))

        # 21. BUG-924 (2026-10-18): A TRANCHE COUNTS WORK, NOT POSITIONS. MEASURED on the day's own receipts: 20 rows
        #     were attempted in more than one tranche and one failed row was copied, converted and quarantined THREE
        #     times, because `--limit N` always took the FIRST N signed rows. An act a prior receipt DECIDED is
        #     reported and never re-performed; an act whose target CHANGED is a different act and is attempted.
        decided_probe = {("books/epub/DOMAIN 1 Test/A Work.epub", rows[0]["target"]): {"state": "deferred"}}
        outstanding, already_decided = split_decided(rows, decided_probe)
        expect("a_DECIDED_act_is_not_re_attempted_and_does_not_consume_the_tranche",
               already_decided == 1 and outstanding == rows[1:]
               and split_decided(rows, {})[0] == rows)
        expect("the_SAME_label_with_a_DIFFERENT_target_is_a_DIFFERENT_act",
               len(split_decided(rows, {("books/epub/DOMAIN 1 Test/A Work.epub", "elsewhere.md"): {}})[0]) == 2)

        # 23. D-3092/BUG-921 (2026-10-18): TWO ROWS, ONE WORK — AND THE PROOF IS THE DIGEST, NOT THE NAME. MEASURED
        #     on the day's own receipt: of 37 rows recorded `failed`, 34 were door deferrals and 28 of those carried
        #     bytes a receipt of the SAME RUN had already admitted from another library path (the work held twice:
        #     `business-notes/pdf/...` admitted, `business-pdf/...` then deferred against its twin's own output), so
        #     the owner was asked to adjudicate an identity the receipts had already resolved. Four sides are
        #     asserted: the duplicate is NAMED and NOT copied, it owes no word and is not a failure, and the rule
        #     CANNOT be declared on a name or a size. The fifth side is the mirror (BUG-920): a receipt naming an
        #     output that is NOT on disk proves nothing, so the row is converted rather than written off.
        twin_a = library / "epub" / "DOMAIN 1 Test" / "Twin.epub"
        twin_b = library / "epub" / "DOMAIN 1 Test" / "Twin Copy.epub"
        twin_a.write_bytes(source.read_bytes())
        twin_b.write_bytes(source.read_bytes())  # the same work under two paths: identical bytes, different names
        twin_md = corpus / "DOMAIN 1 Test" / "Twin.md"
        twin_md.write_text("# the admitted twin\n" + "text " * 60, encoding="utf-8")
        receipts_dir = tmp_root / "receipts"
        receipts_dir.mkdir(parents=True, exist_ok=True)
        (receipts_dir / "ADMISSION_APPLIED_TEST.jsonl").write_text(json.dumps(
            {"state": "applied", "plan_row": "books/epub/DOMAIN 1 Test/Twin.epub", "key": "twin",
             "source": str(twin_a), "source_sha256": sha256_bytes(twin_a), "md_target": str(twin_md),
             "md_sha256": sha256_bytes(twin_md)}) + "\n", encoding="utf-8")
        #: BUG-927: A TORN TAIL IS NOT A CORRUPT RECEIPT — AN INTERIOR GAP IS. This reader parses the receipt a
        #: RUNNING batch is still appending to (the day's file grew 276 -> 422 records while tranches ran), so the
        #: LAST line can be half-written at the instant of reading; the old rule made that a FATAL "line that is not
        #: JSON", i.e. a false fault of exactly the shape that sends the owner round the loop again. Two-sided: the
        #: tail is skipped LOUDLY and the records before it still read, while an interior bad line stays FATAL.
        tail_file = receipts_dir / "ADMISSION_APPLIED_TORN.jsonl"
        readable = json.dumps({"state": "skipped", "plan_row": "torn", "md_target": str(twin_md)})
        tail_file.write_text(readable + "\n" + '{"state": "applied", "plan_ro', encoding="utf-8")
        read_after_tail = [] if _refuses(lambda: read_receipts(decl)) else read_receipts(decl)
        expect("a_TORN_TAIL_line_is_skipped_and_the_records_before_it_still_read",
               any(rec.get("plan_row") == "torn" for rec in read_after_tail), f"{len(read_after_tail)} record(s)")
        tail_file.write_text(readable + "\n" + "oops\n" + readable + "\n", encoding="utf-8")
        expect("an_INTERIOR_gap_in_a_receipt_stays_FATAL", _refuses(lambda: read_receipts(decl)))
        tail_file.unlink()
        copy_row = {"path": str(twin_b), "rel": "books/epub/DOMAIN 1 Test/Twin Copy.epub", "root": "books",
                    "kind": "epub", "key": "twin copy", "bytes": twin_b.stat().st_size,
                    "target": str(corpus / "DOMAIN 1 Test" / "Twin Copy.md")}
        admitted_idx = admitted_bytes(decl)
        dup = apply_row(copy_row, corpus, decl, receipt_index(decl), apply=True, convert=False,
                        admitted=admitted_idx)
        expect("bytes_a_receipt_already_ADMITTED_are_NAMED_as_a_duplicate_and_NEVER_copied",
               dup["state"] == "duplicate_of_admitted"
               and dup.get("duplicate_of") == str(twin_md)
               and not (corpus / "DOMAIN 1 Test" / "Twin Copy.epub").exists()
               and batch_rc({"duplicate_of_admitted": 1}, decl) == RC_OK, dup.get("reason", ""))
        twin_md.unlink()  # BUG-920's mirror: the receipt names an output that is NOT on disk
        mirror = apply_row(copy_row, corpus, decl, receipt_index(decl), apply=True, convert=False,
                           admitted=admitted_bytes(decl))
        expect("a_receipt_with_NO_BYTES_behind_it_is_CONVERTED_never_written_off_as_a_duplicate",
               mirror["state"] != "duplicate_of_admitted"
               and mirror.get("twin_without_bytes") == str(twin_md), mirror.get("reason", ""))
        expect("a_same_bytes_rule_declared_on_a_NAME_or_a_SIZE_is_REFUSED",
               _refuses(lambda: same_bytes_policy(dict(decl, same_bytes=dict(decl["same_bytes"], evidence="key"))))
               and _refuses(lambda: same_bytes_policy({k: v for k, v in decl.items() if k != "same_bytes"})))
        #: THE BANKED INDEX MUST LIVE FOR THE WHOLE BATCH, not only for the receipts that existed when it started:
        #: two copies of one work inside the SAME tranche would otherwise defer against the first's fresh output.
        #: No control executes run() (it reads the live POLICY and the real corpus), so this reads the file's own
        #: bytes and requires the refresh to sit after the count it follows — the same idiom as control 19.
        batch_text = own[own.index("def run("):]
        batch_text = batch_text[:batch_text.index("\ndef ")] if "\ndef " in batch_text else batch_text
        expect("the_run_KEeps_its_bytes_index_current_after_every_admitted_row",
               'counts[record["state"]]' in batch_text
               and batch_text.index('counts[record["state"]]') < batch_text.index("admitted.setdefault(")
               and "admitted = admitted_bytes(decl)" in batch_text,
               "run() does not refresh the byte index after an admission")
        #: BUG-928: THE TARGET INDEX IS THE SAME MEMORY, and it was stale in the same way. MEASURED 2026-10-18 on the
        #: FINAL receipt: two rows of one work recorded `refused — the markdown target already exists and NO receipt
        #: accounts for it`, because the accounting receipt was written by that same run after `receipt_index()` had
        #: been built. A refusal naming a fault where the record exists is a false fault, so both are refreshed.
        expect("the_run_ALSO_keeps_its_TARGET_index_current_after_every_admitted_row",
               "index.setdefault(" in batch_text
               and batch_text.index('counts[record["state"]]') < batch_text.index("index.setdefault(")
               and '("md_target", "container_target")' in batch_text,
               "run() does not refresh the target index after an admission")

        # 24. BUG-930/D-3095 (2026-10-18): A ROW THE CORPUS HOLDS BY NAME IS A QUESTION, NOT A FAULT. MEASURED on the
        #     owner's own 237-row plan: the gate asked one boolean and aborted 109 outstanding acts over 12 rows — 9
        #     redundant by BYTES, 3 the owner's format-duplicate questions. Six sides are asserted: the gate
        #     CLASSIFIES instead of faulting, a collision owes a word and copies NOTHING, BYTES BEAT THE NAME, a dry
        #     run still answers it (the digest is the only answer), a fault is per-row and named, and a deferral is
        #     REOPENED once its collision is gone (a decision whose grounds vanished may not hold forever).
        held_source = library / "epub" / "DOMAIN 1 Test" / "A Held Name.epub"
        held_source.write_bytes(b"NOT-THE-ADMITTED-BYTES" * 10)
        held_row = {"path": str(held_source), "rel": "books/epub/DOMAIN 1 Test/A Held Name.epub", "root": "books",
                    "kind": "epub", "key": "a held name", "bytes": held_source.stat().st_size,
                    "target": str(corpus / "DOMAIN 1 Test" / "A Held Name.md")}
        collision = ["the corpus holds DOMAIN 1 Test/A Held Name.md"]
        gate_faults, gate_holds = verify_rows([held_row], {}, {"a held name": collision})
        expect("a_signed_row_the_corpus_holds_BY_NAME_is_a_QUESTION_and_NOT_a_batch_FATAL",
               gate_faults == [] and gate_holds.get(held_row["rel"]) == collision, (gate_faults, gate_holds))
        asked = apply_row(held_row, corpus, decl, receipt_index(decl), apply=True, convert=True, held=collision)
        expect("a_held_name_owes_the_owner_A_WORD_and_copies_converts_and_quarantines_NOTHING",
               asked["state"] == "deferred" and "the corpus holds" in asked["reason"]
               and not (corpus / "DOMAIN 1 Test" / "A Held Name.epub").exists()
               and not (corpus / "DOMAIN 1 Test" / "A Held Name.md").exists()
               and batch_rc({"deferred": 1}, decl) == RC_OWNER_OWED, asked.get("reason", ""))
        admitted_md = corpus / "DOMAIN 1 Test" / "A Held Twin.md"
        admitted_md.write_text("# the twin work\n" + "text " * 40, encoding="utf-8")
        twin_src = library / "epub" / "DOMAIN 1 Test" / "A Held Twin.epub"
        twin_src.write_bytes(b"ADMITTED-BYTES" * 20)
        (receipts_dir / "ADMISSION_APPLIED_HELD.jsonl").write_text(json.dumps(
            {"state": "applied", "plan_row": "books/epub/DOMAIN 1 Test/A Held Twin.epub", "key": "a held twin",
             "source": str(twin_src), "source_sha256": sha256_bytes(twin_src), "md_target": str(admitted_md),
             "md_sha256": sha256_bytes(admitted_md)}) + "\n", encoding="utf-8")
        held_dup_row = {"path": str(twin_src), "rel": "books/epub/DOMAIN 1 Test/Held Twin Copy.epub", "root": "books",
                        "kind": "epub", "key": "a held name", "bytes": twin_src.stat().st_size,
                        "target": str(corpus / "DOMAIN 1 Test" / "Held Twin Copy.md")}
        both = apply_row(held_dup_row, corpus, decl, receipt_index(decl), apply=True, convert=False,
                         admitted=admitted_bytes(decl), held=collision)
        expect("BYTES_win_over_the_NAME_a_held_row_whose_bytes_are_ADMITTED_is_a_DUPLICATE",
               both["state"] == "duplicate_of_admitted"
               and batch_rc({"duplicate_of_admitted": 1}, decl) == RC_OK, both.get("state", ""))
        dry_held = apply_row(held_row, corpus, decl, receipt_index(decl), apply=False, convert=False, held=collision)
        expect("a_dry_run_STILL_answers_a_held_row_because_the_digest_is_the_only_ANSWER",
               dry_held["state"] == "deferred" and dry_held.get("source_sha256") == sha256_bytes(held_source),
               (dry_held["state"], str(dry_held.get("source_sha256"))[:12]))
        lonely_faults, lonely_holds = verify_rows([held_row], {}, {})
        expect("a_row_NO_index_holds_and_the_door_no_longer_reads_is_REFUSED_BY_NAME",
               len(lonely_faults) == 1 and lonely_faults[0][0] == held_row["rel"] and lonely_holds == {},
               lonely_faults)
        refused_only = apply_row(held_row, corpus, decl, receipt_index(decl), apply=True, convert=True,
                                 refusal="no index holds this name and the door no longer reads it")
        expect("a_gate_fault_reaches_the_receipt_as_a_REFUSAL_with_NOTHING_copied",
               refused_only["state"] == "refused"
               and not (corpus / "DOMAIN 1 Test" / "A Held Name.epub").exists(), refused_only["state"])
        dec_file = receipts_dir / "ADMISSION_APPLIED_DECIDE.jsonl"
        dec_file.write_text(json.dumps({"state": "deferred", "plan_row": held_row["rel"], "key": "a held name",
                                        "md_target": held_row["target"]}) + "\n", encoding="utf-8")
        expect("a_DEFERRAL_is_DECIDED_while_its_COLLISION_holds_and_REOPENED_when_it_is_GONE",
               len(split_decided([held_row], decided_acts(decl, {"a held name": collision}))[0]) == 0
               and len(split_decided([held_row], decided_acts(decl, {}))[0]) == 1)
        dec_file.unlink()
        expect("the_name_held_rule_is_DECLARED_and_a_rule_whose_INDEX_no_reader_builds_is_REFUSED",
               name_held_policy(decl)["state"] == "deferred"
               and _refuses(lambda: name_held_policy({k: v for k, v in decl.items() if k != "name_held"}))
               and _refuses(lambda: name_held_policy(dict(decl, name_held=dict(decl["name_held"],
                                                                             indexes=["some_other_index"]))))
               and _refuses(lambda: name_held_policy(dict(decl, name_held=dict(decl["name_held"],
                                                                              state="nonsense")))))

        # 25. BUG-931 (2026-10-18): THE WORD NAMES THE PLAN, NOT THE CLOCK. MEASURED: `run()` resolved the plan with
        #     `newest()`, so a re-derivation left a newer stamped plan beside the SIGNED one and every `admit-apply`
        #     refused a signature whose scope still matched the signed plan exactly — the owner's only remedy was to
        #     re-derive and re-sign, which produced another newer plan and re-armed the same trap. Three sides: the
        #     signature's plan wins over a newer one, a signature NAMING NO PLAN resolves to nothing (its own refusal
        #     lives in load_acceptance), and a signature naming a plan that no longer exists is FATAL and says so.
        plans_dir = tmp_root / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        older_plan = plans_dir / "ADMISSION_PLAN_20260101.json"
        newer_plan = plans_dir / "ADMISSION_PLAN_20260101T235959ZZ.json"
        older_plan.write_text(json.dumps({"rows": rows}), encoding="utf-8")
        newer_plan.write_text(json.dumps({"rows": rows}), encoding="utf-8")
        naming_older = dict(base_accept, plan=str(older_plan))
        naming_older_file = tmp_root / "NAMES_OLDER.yaml"
        naming_older_file.write_text(yaml.safe_dump(naming_older), encoding="utf-8")
        expect("the_signature_s_PLAN_wins_over_a_NEWER_plan_on_disk",
               acceptance_plan(naming_older_file, decl) == older_plan
               and newest(str(plans_dir / "ADMISSION_PLAN_"), ".json") == newer_plan,
               (acceptance_plan(naming_older_file, decl), newest(str(plans_dir / "ADMISSION_PLAN_"), ".json")))
        names_nothing = tmp_root / "NAMES_NOTHING.yaml"
        names_nothing.write_text(yaml.safe_dump({"accepted_by": "selftest"}), encoding="utf-8")
        expect("a_signature_that_names_NO_PLAN_resolves_to_nothing_here_and_is_refused_there",
               acceptance_plan(names_nothing, decl) is None)
        ghost_file = tmp_root / "NAMES_GHOST.yaml"
        ghost_file.write_text(yaml.safe_dump(dict(base_accept, plan=str(tmp_root / "GONE.json"))),
                              encoding="utf-8")
        expect("a_signature_naming_a_plan_that_is_GONE_is_FATAL_and_names_it",
               _refuses(lambda: acceptance_plan(ghost_file, decl)))

        # 26. BUG-932 (2026-10-18): A LATER REFUSAL MAY NOT ERASE AN EARLIER ADMISSION. MEASURED on the day's own
        #     receipt: `applied …-January-2013.docx` (md_sha256 e7ad6ab1…) followed by `refused …-January-2013.md`
        #     (no digest) for the SAME markdown target — the library holds that work twice, as a container that was
        #     converted and as a .md that is already a work — and the last-wins index kept only the refusal, so every
        #     later run reported "the markdown target already exists and NO receipt accounts for it" about a work
        #     whose admission was recorded twice over. The rank is the EVIDENCE; the second side keeps the refusal
        #     honest: a target whose ONLY record is a refusal still refuses.
        rank_dir = tmp_root / "ranked"
        rank_dir.mkdir(parents=True, exist_ok=True)
        target_md = corpus / "DOMAIN 1 Test" / "Ranked Work.md"
        target_md.write_text("# a ranked work\n" + "text " * 40, encoding="utf-8")
        rank_decl = {"receipt_prefix": str(rank_dir / "ADMISSION_APPLIED_"), "receipt_extension": ".jsonl"}
        rank_receipt = receipt_path(rank_decl, "RANK")
        append_receipt(rank_receipt, {"state": "applied", "plan_row": "books/epub/DOMAIN 1 Test/Ranked Work.epub",
                                      "source_sha256": "a" * 64, "md_target": str(target_md),
                                      "md_sha256": sha256_bytes(target_md)})
        append_receipt(rank_receipt, {"state": "refused", "plan_row": "books/epub/DOMAIN 1 Test/Ranked Work.md",
                                      "md_target": str(target_md), "md_sha256": None})
        unaccounted_md = corpus / "DOMAIN 1 Test" / "Unexplained Again.md"
        unaccounted_md.write_text("# nobody admitted this\n" + "text " * 40, encoding="utf-8")
        append_receipt(rank_receipt, {"state": "refused", "plan_row": "books/epub/DOMAIN 1 Test/Unexplained Again.md",
                                      "md_target": str(unaccounted_md), "md_sha256": None})
        ranked = receipt_index(rank_decl)
        expect("an_EARLIER_ADMISSION_outranks_a_LATER_REFUSAL_for_the_same_target",
               str(ranked.get(str(target_md), {}).get("state")) == "applied",
               ranked.get(str(target_md), {}).get("state"))
        ranked_row = {"path": str(md_source), "rel": "books/epub/DOMAIN 1 Test/Ranked Work.md", "root": "books",
                      "kind": "md", "key": "ranked work", "bytes": md_source.stat().st_size,
                      "target": str(target_md)}
        reread = apply_row(ranked_row, corpus, decl, ranked, apply=True, convert=False)
        expect("a_target_an_earlier_ADMISSION_accounts_for_is_ALREADY_APPLIED_not_a_false_fault",
               reread["state"] == "already_applied", reread.get("reason", "")[:120])
        expect("a_target_whose_ONLY_record_is_a_REFUSAL_still_REFUSES",
               str(ranked.get(str(unaccounted_md), {}).get("state")) == "refused"
               and apply_row(dict(ranked_row, target=str(unaccounted_md)), corpus, decl, ranked, apply=False,
                             convert=False)["state"] == "refused")

        # 22. BUG-925 (2026-10-18): A SIGNATURE IS AN APPEND-ONLY ACT. MEASURED: the second `--sign` of the day
        #     REPLACED the first file, and the running batch's receipt — which names its authority by path AND
        #     digest — then pointed at bytes that no longer existed (receipt pinned 94c3c308…, disk hashed
        #     941f3a6c…). The same words must stay ONE signature with a stable digest; different words must land in
        #     a NEW file and must never overwrite the one a receipt already names.
        day_words = signed_file.read_text(encoding="utf-8")
        other_path = signature_path(decl, day_words.replace("accepted_on", "accepted_on ") + "# a different word\n")
        expect("a_second_word_is_APPENDED_and_an_IDENTICAL_word_is_NOT_written_twice",
               signature_path(decl, day_words) == signed_file
               and other_path != signed_file and not other_path.exists()
               and signed_file.read_text(encoding="utf-8") == day_words)

        # 19. D-3072/BUG-881: THE RECEIPT'S WORD-PROOF KEYS ARE BOUND BEFORE THE HEADER THAT CARRIES THEM. The header
        #     is built inside run(), which no control executes (it reads the live POLICY and the real corpus), and the
        #     composition is exactly where BUG-881 lived: the controls had tested the UNIT, never the composition, so
        #     a shadowed name only failed on the operator's command. This reads the file's own text and requires the
        #     definition to precede the use - cheap, and it fails on the day the header is refactored above its proof.
        run_text = own[own.index("def run("):]
        run_text = run_text[:run_text.index("\ndef ")] if "\ndef " in run_text else run_text
        expect("the_receipts_word_proof_keys_are_BOUND_before_the_header_that_carries_them",
               all(token in run_text for token in ('"signed_by": signed_by', '"scope_sha256": scope_digest(signed)',
                                                  '"accepted_by": acc["accepted_by"]'))
               and run_text.index("signed_by = verify_scope(") < run_text.index('"signed_by": signed_by'),
               "the header references a value run() has not bound yet")

        # 15. BUG-884: a REFUSAL prints its message and exits RC_FATAL — never a traceback. A message string handed
        #     to SystemExit lands in `.code`, so `int(exc.code)` turned the digest-mismatch refusal into a
        #     ValueError. Both branches are asserted: a message string AND a declared integer code.
        expect("a_refusal_exits_RC_FATAL_when_its_code_is_a_message",
               applier_rc(ApplierError("FATAL: the acceptance pins a different digest")) == RC_FATAL)
        expect("a_refusal_keeps_a_declared_INTEGER_code", applier_rc(ApplierError(RC_OWNER_OWED)) == RC_OWNER_OWED)

        # 27. BUG-934 — THE REPORT MAY NOT DISAGREE WITH ITS OWN EXIT CODE. MEASURED 2026-10-18 on the live signed
        #     plan: 9 rows were held BY NAME, the digest then resolved all 9 as `duplicate_of_admitted` (D-3092),
        #     the batch exited 0 — and the run printed "rc 2 says so" AND "no word is owed" about the same nine
        #     rows. Nothing caught it because every control asserted a COUNT, and the lie was a RELATION between a
        #     printed claim and the exit code. The fix is structural (the pre-verdict line is handed no counts and
        #     cannot name an rc; the verdict lines are handed the SAME dict `batch_rc` reads), so the control is ONE
        #     INVARIANT OVER EVERY DECLARED STATE rather than one example per bug — the shape that spans a class.
        real_decl = applier_policy(census.policy(POLICY))
        for state_ in real_decl["states"]:
            only = {str(state_): 1}
            claim = "OWNER-OWED" in " ".join(verdict_lines(only, 0, real_decl))
            expect(f"the_owner_owed_claim_agrees_with_the_exit_code_for_{state_}",
                   claim == (batch_rc(only, real_decl) == RC_OWNER_OWED),
                   f"claim={claim} rc={batch_rc(only, real_decl)}")
        pre = asking_line({"a rel": ["held by: an ingest record"]})
        expect("a_pre_verdict_question_never_names_an_exit_code",
               all(token not in pre for token in ("rc ", "OWNER-OWED", "no word is owed")), pre)
        dup = {same_bytes_policy(real_decl)["state"]: 9}
        expect("a_name_held_row_the_digest_ANSWERED_owes_the_owner_nothing",
               "ANSWERED" in " ".join(verdict_lines(dup, 9, real_decl))
               and "OWNER-OWED" not in " ".join(verdict_lines(dup, 9, real_decl)))

        # 28. BUG-936 — THE QUARANTINE MUST NOT DESTROY EVIDENCE. MEASURED 2026-10-18 on the owner's own receipts:
        #     the destination was `base / path.name`, so FOUR distinct works called `*GYST_README!.rtf` (four GYST
        #     folders) were moved onto ONE path — each `shutil.move` replacing the last — and the survivor is gone
        #     altogether; across every receipt, 398 destinations and 3 are claimed by MORE THAN ONE different source.
        #     The fix restores the row's folder (`rel`) and disambiguates a residual collision by the digest of the
        #     source path instead of replacing. Both halves are asserted: distinct works KEEP BOTH, and the same work
        #     quarantined twice does not overwrite its own earlier evidence.
        q_decl = dict(decl, quarantine_prefix=str(tmp_root / "quarantine"))
        first = tmp_root / "one" / "GYST by A" / "README.rtf"
        second = tmp_root / "two" / "GYST by B" / "README.rtf"
        for path_ in (first, second):
            path_.parent.mkdir(parents=True, exist_ok=True)
            path_.write_text(f"bytes of {path_.parent.parent.name}", encoding="utf-8")
        moved = (quarantine_copy([first], q_decl, "T936", "why", rel="books/a/GYST by A/README.rtf")
                 + quarantine_copy([second], q_decl, "T936", "why", rel="books/b/GYST by B/README.rtf"))
        expect("two_works_of_one_NAME_keep_BOTH_bytes_in_quarantine",
               len(moved) == 2 and len(set(moved)) == 2 and all(Path(p).is_file() for p in moved), str(moved))
        expect("a_quarantined_work_keeps_its_FOLDER_dimension",
               all("GYST by" in Path(p).parent.name for p in moved), str(moved))
        again = tmp_root / "three" / "GYST by A" / "README.rtf"
        again.parent.mkdir(parents=True, exist_ok=True)
        again.write_text("a different work, same folder and name", encoding="utf-8")
        moved_again = quarantine_copy([again], q_decl, "T936", "why", rel="books/a/GYST by A/README.rtf")
        expect("a_second_work_on_the_SAME_rel_path_does_not_REPLACE_the_first",
               len(moved_again) == 1 and moved_again[0] not in moved and Path(moved_again[0]).is_file()
               and Path(moved[0]).is_file(), f"{moved_again} vs {moved}")

    passed = sum(1 for _label, ok in checks if ok)
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
    print(f"\n{passed}/{len(checks)} controls")
    return RC_OK if passed == len(checks) else RC_FATAL


def write_atomic_text(path: Path, text: str) -> None:
    """tempfile -> fsync -> os.replace in the TARGET directory (C6): a crash leaves the old file or the new one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)  # this writer's OWN half-written temp file, never the owner's bytes
        raise


def signature_path(decl: dict[str, Any], text: str) -> Path:
    """WHERE a word lands: the day's own name when it is free, a STAMPED name when one is already on file.

    BUG-925 MEASURED 2026-10-18: `--sign` wrote `<accept_prefix><date><ext>` UNCONDITIONALLY, so the owner's second
    signature of the day REPLACED the first — and every receipt names its authority by PATH AND DIGEST
    (`accept` + `accept_sha256`). From that moment the running batch's receipt pointed at a document that no longer
    existed: the receipt pins 94c3c308…, the file on disk hashed 941f3a6c… (MEASURED). A signature is an
    APPEND-ONLY act (D-3036: an act that leaves no trace did not happen), so it is never overwritten; and an
    IDENTICAL word is not written twice — re-signing the same acts is one word, and a stable digest is what keeps
    every receipt resolvable (D-3034: a declaration must RESOLVE).
    """
    prefix = str(decl["accept_prefix"])
    extension = str(decl["accept_extension"])
    day = resolve_root(f"{prefix}{datetime.now(UTC).strftime('%Y%m%d')}{extension}")
    if not day.exists():
        return day
    try:
        same = day.read_text(encoding="utf-8").strip() == text.strip()
    except OSError:
        same = False
    if same:  # the same acts, the same day, the same words: ONE signature, and its digest never moves
        return day
    moment = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")  # never `stamp`: that name is the module's own record fn
    candidate = resolve_root(f"{prefix}{moment}{extension}")
    ordinal = 2
    while candidate.exists():
        candidate = resolve_root(f"{prefix}{moment}-{ordinal}{extension}")
        ordinal += 1
    return candidate


def sign(plan_path: Path | None, decl: dict[str, Any], who: str, mode: str, rows_path: Path | None) -> int:
    """WRITE THE OWNER'S WORD — the one act that used to be a hand-edited YAML, and the reason for BUG-892.

    MEASURED 2026-10-17: `just admit-apply --limit 10` failed twice on `accepted_by: <your name>` because the file
    carrying the word is a file this tool PRINTS, and printing reset the name to the placeholder every time the
    plan was re-derived. The owner was told to retype their name into a generated artifact — a step that is not a
    control (it prevented no authorisation and cost two runs), it is a chore with a failure mode. So the name is
    declared ONCE here and the SCOPE is what a plan change re-decides.

    An identity SWAP is refused rather than overwritten: a signature carrying a different name is a different
    signer, and a file that silently changes who signed it is worse than no file (D-3034).
    """
    import yaml

    plan_path = plan_path or newest(str(plan_admission.admission_policy(census.policy(POLICY))["plan_prefix"]), ".json")
    if plan_path is None or not plan_path.is_file():
        raise ApplierError("FATAL: --sign needs a plan to authorise; derive one first (plan_admission.py --plan)")
    plan = load_plan(plan_path)
    digest = sha256_bytes(plan_path)
    placeholder = str(decl["accept_by_placeholder"]).strip()
    name = who.strip()
    if not name or name.lower() == placeholder.lower() or "<" in name or ">" in name:
        raise ApplierError(
            f"FATAL: --as {who!r} is not a name — a placeholder, an empty value or a template token is a signature "
            f"nobody signed (BUG-888). Write the name this act will be asked about."
        )
    if mode not in decl["accept_modes"]:
        raise ApplierError(f"FATAL: --mode {mode!r} is outside the declared vocabulary {decl['accept_modes']} (C12)")
    wanted: list[str] = []
    if mode == "listed":
        if rows_path is None or not rows_path.is_file():
            raise ApplierError("FATAL: --mode listed needs --rows FILE with one `rel` label per line")
        wanted = [line.strip() for line in rows_path.read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.strip().startswith("#")]
        if not wanted:
            raise ApplierError(f"FATAL: {rows_path} names no row — a signature that silently selects nothing looks "
                              f"like an authorisation while authorising nothing (D-3034)")
    selected, _ = selected_rows(plan, {"mode": mode, "rows": wanted})

    identity_path = resolve_root(str(decl["accept_by_identity"]))
    declared = declared_identity(decl)
    if declared and declared.lower() != name.lower():
        raise ApplierError(
            f"FATAL: {identity_path} already declares the owner as {declared!r} and this act would sign as "
            f"{name!r} — an identity change is a NEW DECISION, never an overwrite (D-3034). Correct the file "
            f"deliberately, with the reason, or sign as {declared!r}."
        )
    if not declared:
        write_atomic_text(identity_path, yaml.safe_dump({
            "schema_version": SCHEMA_VERSION,
            "authority": "D-3072",
            "accept_by": name,
            "declared_on": datetime.now(UTC).strftime("%Y-%m-%d"),
            "why": "the owner's IDENTITY: declared ONCE, so a re-derived plan never asks for it again. It is not a "
                   "decision about any plan - the SCOPE (scope_sha256) is what a plan change re-decides.",
        }, sort_keys=False, allow_unicode=True))

    try:  # a signature is more portable when it names the plan RELATIVE to the tree it governs
        plan_ref = plan_path.resolve().relative_to(_PROJECT_ROOT).as_posix()
    except ValueError:
        plan_ref = str(plan_path)
    acceptance = {
        "schema_version": SCHEMA_VERSION,
        "plan": plan_ref,
        "plan_sha256": digest,
        "scope_sha256": scope_digest(selected),
        "accepted_by": name,
        "accepted_on": datetime.now(UTC).strftime("%Y-%m-%d"),
        "mode": mode,
        "rows": [str(row["rel"]) for row in selected],
    }
    text = yaml.safe_dump(acceptance, sort_keys=False, allow_unicode=True)
    target = signature_path(decl, text)
    write_atomic_text(target, text)
    print(f"SIGNED  {target}")
    print(f"        by        {name}")
    print(f"        acts      {len(selected)} row(s), mode {mode}")
    print(f"        plan      {plan_path.name} sha256 {digest}")
    print(f"        scope     {acceptance['scope_sha256']}")
    print(f"        next      {decl['command']} --dry-run   (the price), then --apply")
    print(f"                  the SAME signature authorises the SAME acts: REPEAT --apply until it reports nothing")
    print(f"                  outstanding. Re-derive only when new files have arrived — then a new word is owed.")
    return RC_OK


def main(argv: list[str] | None = None) -> int:
    """Dispatch the readings; an unknown flag is fatal rather than silently ignored (C16)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    if "--sign" in argv:
        #: THE OWNER'S ACT IS A COMMAND, not a hand edit of a generated file (D-3072).
        doc = census.policy(POLICY)
        decl = applier_policy(doc)
        parser = argparse.ArgumentParser(prog="apply_admission.py --sign",
                                         description="Write the owner's word: pin the LIVE plan's ACTS to a name.")
        parser.add_argument("--sign", action="store_true")
        parser.add_argument("--as", dest="who", required=True, help="the owner's name (declared once, then reused)")
        parser.add_argument("--mode", default="all", help="all (every candidate row) or listed (--rows FILE)")
        parser.add_argument("--rows", type=Path, help="for --mode listed: one `rel` label per line")
        parser.add_argument("--plan", type=Path, help="the plan JSON (default: the newest under the declared prefix)")
        args = parser.parse_args(argv)
        try:
            return sign(args.plan, decl, args.who, args.mode, args.rows)
        except ApplierError as exc:
            print(str(exc))
            return applier_rc(exc)
    if "--template" in argv:
        # The signature, pre-pinned to the plan's LIVE digest: the one step a human could get wrong is removed.
        doc = census.policy(POLICY)
        plan_path = newest(str(plan_admission.admission_policy(doc)["plan_prefix"]), ".json")
        if plan_path is None or not plan_path.is_file():
            print(f"FATAL: no plan found under {plan_admission.admission_policy(doc)['plan_prefix']}*.json")
            return RC_FATAL
        plan = load_plan(plan_path)
        decl = applier_policy(doc)
        print(acceptance_template(plan_path, sha256_bytes(plan_path), plan["rows"],
                                  str(decl["accept_by_placeholder"]), declared_identity(decl)), end="")
        return RC_OK
    parser = argparse.ArgumentParser(
        description="The admit applier (T-183): apply an ACCEPTED admission plan, crash-safe, dry run by default.")
    parser.add_argument("--plan", type=Path, help="the plan JSON (default: the newest under the declared prefix)")
    parser.add_argument("--accept", type=Path, help="the signed acceptance YAML (default: the newest)")
    parser.add_argument("--apply", action="store_true", help="write; without it NOTHING is copied or converted")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview from the same door: wins over --apply, writes nothing")
    parser.add_argument("--no-convert", action="store_true", help="copy the container only and leave it UNREAD")
    parser.add_argument("--limit", type=int, help="apply at most N rows (a tranche, counted)")
    parser.add_argument("--json", action="store_true", help="one JSON record per row")
    args = parser.parse_args(argv)
    try:
        return run(args.plan, args.accept, apply=args.apply and not args.dry_run, convert=not args.no_convert,
                   limit=args.limit, json_out=args.json)
    except ApplierError as exc:
        print(str(exc))
        return applier_rc(exc)


if __name__ == "__main__":
    sys.exit(main())
