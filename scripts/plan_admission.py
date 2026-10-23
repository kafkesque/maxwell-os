#!/usr/bin/env python3
"""plan_admission.py — THE ADMISSION PLAN: the works the pipeline has never seen, by the door's own key
(READ-ONLY, T-181/D-3051).

THE HOLE THIS ACT ANSWERS (MEASURED 2026-10-16, D-3050/T-181): the flow between an arrival and a stamped work
has FIVE declared transitions and the middle one — ADMISSION, the step that puts a library file into the corpus
— was declared NOWHERE. `pipeline/stage0_convert.py` reads the CORPUS
(`config/pipeline_config.yaml#books_dir`) recursively, and NOTHING on disk named
the transition that puts a library file into it: the pipeline's OWN INPUT PATH was the one step a human
performed by hand with no counter and no receipt.

WHAT THIS READER IS, and what it is NOT:
  * it is a READER. It opens no library file's CONTENT (metadata is the rename plan's subject, T-176), it
    renames nothing, it moves nothing, it converts nothing, and a bare run writes NO file: the ONE write call
    site sits behind --plan, and a control proves that against this file's own bytes;
  * it answers ONE question per file in the declared library kind roots: does the corpus, or an ingest record,
    already name a work by this file's KEY? The key is the DOOR'S OWN comparison key
    (`pipeline/book_metadata.sanitize_source_book`), because a second key would be a second identity (D-3045).
    A name is EVIDENCE, never identity: a work renamed after its ingest reads under a different key, and a
    defective name (T-176) can read as absent while being present — which is WHY every class below is a row for
    the OWNER and never an act. This reader moves nothing because of a name, ever;
  * it REFUSES with a printed and COUNTED reason: a file that does not sit in the folder its home's own
    DECLARED AXIS orders it by, where that axis IS the kind (a `domain` home keeps the owner's topic folders, so a
    kind-folder test there would invent a class nobody declared); a root whose works have no declared corpus home
    (MEASURED
    2026-10-16: the notes root declares none), a container no stage reads (S0 accepts the containers its own
    conversion transition declares — a `.mobi`/`.azw3`/`.djvu`/`.docx` cannot be admitted at all), a file that
    does not sit in its declared kind folder (where its corpus twin would go is then unknown), and a name the
    rename plan has yet to repair (a defective name admitted into the corpus is a name the S0.5 cache would
    then STAMP, and the corpus-name cascade BUG-800 already costs 2,952 references to undo one).

Exit: 0 nothing owed | 2 ROWS WAITING FOR THE OWNER'S WORD (loud, owner-owed, BUG-457) | 1 FATAL (an undeclared
or unreadable declaration, an absent root, an absent cache or a corpus home that does not resolve — never a
silent zero, D-795). The plan file it writes is a PROPOSAL: the act that admits a work is separate, owner-worded
and plan-first (T-183), exactly as the rename plan is separate from the rename.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

import census_source_names as census  # noqa: E402 — the library reader: roots, name classes, the cache join

from pipeline.book_metadata import (  # noqa: E402 - the door's OWN comparison key (D-3045)
    sanitize_source_book,
)
from pipeline.container_integrity import (  # noqa: E402 - BUG-886/D-3071, BUG-893/D-3073
    defects_from,
    diagnose,
    is_readable,
    probes_from,
)

POLICY = census.POLICY
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2

#: D-3077 — THE CONTAINER SET HAS ONE DECLARATION, AND IT IS CONFIG. It used to be an AST read of a literal set in
#: `pipeline/stage0_convert.py`; the literal is gone, because which container this stage can open is now declared one
#: line per container (`config/pipeline_config.yaml#stage0.containers`, naming the reader that opens it). This reader
#: still does NOT import the pipeline (it pulls the I/O stack, and a ladder line must not pay for it).
#:
#: BUG-907 (MEASURED 2026-10-17): the two homes — the door's `flow.transitions.conversion.accepts` and the stage's
#: `stage0.containers` — were compared ONLY inside this file's selftest, and that comparison put a FIXTURE policy
#: (3 containers) against the LIVE declaration. When D-3077 widened the stage to 10, `just health` went red and the
#: invariant it claimed was still enforced NOWHERE in production. The join is now a DECLARED REFERENCE
#: (`conversion.accepts_from`) that `build()` RESOLVES and refuses on, so a fixture names its own stage0 home and no
#: control depends on a coincidence with the live tree. This reader therefore holds no path of its own (C12/D-3034).
STAGE0_ORIGIN_KEY = "accepts_from"

#: The CLOSED decision vocabulary. Every one of these must be DECLARED in the gate
#: (`source_library.admission.decisions`), a class this reader produces that the declaration does not carry is
#: FATAL, and a declared class that reads zero is PRINTED as zero (green by vacancy is visible, BUG-487).
DECISIONS = (
    "already_in_the_corpus",
    "seen_by_an_ingest_record",
    "admit_candidate",
    "refused_no_declared_corpus_home",
    "refused_container_no_stage_reads_it",
    #: BUG-886/D-3071: an ACCEPTED kind whose own BYTES are not openable. Its own class because its own REMEDY:
    #: a `.mobi` needs an engine (the class above), a truncated `.epub` needs a re-download. MEASURED 2026-10-17:
    #: 3 of 1,289 declared containers cannot be opened, and every one of them read as an ordinary candidate —
    #: the owner signed one, 137 MB were copied, and S0 failed (BUG-887).
    "refused_container_corrupt",
    "refused_name_repair_first",
    "refused_not_in_its_kind_folder",
    #: D-3062: a note's share of the ONE corpus root is its own DOMAIN subtree. A source folder the corpus does
    #: NOT materialise would land at the corpus TOP LEVEL, beside the DOMAIN trees - and the domain vocabulary
    #: HAS ONE MATERIALISATION (census_source_names.axis_vocabulary reads the corpus's own immediate
    #: subdirectories), so an admission would silently WIDEN it. That is a declared refusal, not a guess.
    "refused_domain_not_a_corpus_domain",
    #: BUG-973 (2026-10-23): a file the owner has SETTLED by a receipted disposition (out_of_scope_by_kind,
    #: not_a_work, conversion_refused_permanently). Its own class because its own meaning: it is NOT a refusal
    #: (nothing waits for a pipeline act) and NOT a candidate (nothing waits for the owner's admission word) —
    #: it is DECIDED. Counted once, never re-raised, so a lane whose number can never move becomes a decision
    #: the owner can record and the counter can finish (D-3038 applied to a count).
    "disposed",
)

CONTROL_LABELS = (
    "a_work_the_corpus_holds_by_KEY_is_NOT_an_admission_candidate",
    "a_work_only_an_INGEST_RECORD_names_is_SEEN_and_not_an_admission_candidate",
    "a_work_the_pipeline_has_never_seen_is_an_ADMISSION_CANDIDATE_with_a_DERIVED_target",
    "a_container_no_stage_reads_is_REFUSED_and_COUNTED_never_silently_skipped",
    "a_defective_name_is_REFUSED_as_name_repair_FIRST_and_counted",
    "a_root_that_declares_NO_corpus_home_is_REFUSED_as_UNDECLARED_and_counted",
    "a_root_that_does_not_declare_admits_to_is_FATAL_and_never_defaulted",
    "an_absent_declared_root_is_FATAL_and_never_a_zero",
    "an_absent_declaration_key_is_FATAL_and_never_defaulted",
    "a_corpus_home_that_does_not_resolve_is_FATAL",
    "an_ingest_record_naming_a_work_is_counted_as_SEEN_and_never_swallowed",
    "the_declared_accepted_containers_equal_the_CONVERSION_stage_declared_containers",
    "the_key_is_the_DOOR_own_key_and_not_a_second_one",
    "a_decision_the_declaration_does_not_carry_is_FATAL_and_a_declared_one_reads_zero",
    "a_home_whose_axis_is_NOT_the_kind_is_never_refused_for_its_folder",
    "an_axis_outside_the_declared_vocabulary_is_FATAL_and_never_guessed",
    "a_bare_run_writes_NOTHING_and_the_reader_names_no_path_of_its_own",
    "the_ONE_line_brief_agrees_with_the_full_reading",
    "the_same_work_spelled_NFC_and_NFD_is_ONE_key_and_distinct_names_stay_distinct",
    "a_DOMAIN_axis_root_KEEPS_its_DOMAIN_folder_and_a_folder_the_corpus_does_not_materialise_is_REFUSED",
    #: BUG-886/D-3071 — appended, not inserted: the indices above are how every control addresses this table,
    #: and renumbering them to slot one in would rewrite nineteen controls to add a twentieth (drift for nothing).
    "a_container_the_stage_CANNOT_OPEN_is_REFUSED_as_CORRUPT_and_never_proposed_for_the_owner_word",
    "an_ACCEPTED_kind_with_no_declared_readability_probe_is_FATAL_and_never_admitted_unchecked",
    #: BUG-893/D-3073 — appended for the same reason: an index is how a control addresses this table.
    "EVERY_refused_row_carries_a_handle_that_RESOLVES_and_the_corrupt_ones_name_their_DEFECT_and_REMEDY",
    "a_defect_outside_the_declared_vocabulary_is_FATAL_and_never_printed_as_a_guess",
    #: BUG-895 — the control OF the controls.
    "EVERY_control_label_is_cited_by_INDEX_so_no_name_prints_green_with_nothing_behind_it",
    #: BUG-929 — the plan's DAY NAME is a slot, exactly as the acceptance's was (BUG-925).
    "a_SECOND_derivation_of_the_day_NEVER_replaces_the_plan_a_SIGNATURE_pins_and_a_REPEAT_does_not_rewrite",
    #: BUG-973 — appended for the same reason: an index is how a control addresses this table.
    "a_DISPOSED_row_is_SETTLED_NOT_refused_and_a_disposed_SUFFIX_is_neither_candidate_nor_refusal",
    "a_disposition_REASON_outside_the_declared_vocabulary_is_FATAL_and_never_skipped",
)


class AdmissionError(SystemExit):
    """Fail-closed: an undeclared, absent or unresolvable input is a fault, never a silent zero (C16/D-795)."""


def admission_policy(pol: dict[str, Any]) -> dict[str, Any]:
    """The declared admission policy: what a plan is called, how it is read, and its CLOSED decision vocabulary."""
    decl = pol["source_library"].get("admission")
    if not isinstance(decl, dict) or not decl:
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library.admission is not declared — the plan prefix, the target rule and "
            f"the decision vocabulary must come from the declaration, never from this reader (C12)"
        )
    for key in ("authority", "plan_prefix", "target_rule", "refusal_examples", "worklist_in_full",
                "decisions"):
        if key not in decl:
            raise AdmissionError(
                f"FATAL: {POLICY}#source_library.admission does not declare {key!r} (C12: an absent value is "
                f"FATAL and never defaulted)"
            )
    decisions = decl["decisions"]
    if not isinstance(decisions, dict) or not decisions:
        raise AdmissionError(f"FATAL: {POLICY}#source_library.admission.decisions must be a non-empty mapping")
    return decl


def home_path(homes: dict[str, Any], key: str) -> Path:
    """Resolve a DECLARED home by its key: a root points at a declaration, never at a path of its own (D-3034)."""
    value = homes.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library.arrangement.{key} is not a declared path — a root that points at "
            f"a home the declaration does not carry names nothing (D-3034)"
        )
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    if not path.exists():
        raise AdmissionError(
            f"FATAL: the declared home {key} does not exist: {path} (D-795: an absent home is never a zero)"
        )
    return path


def conversion_block(pol: dict[str, Any]) -> dict[str, Any]:
    """The CONVERSION transition as declared — the one place the door says what it accepts, and where that came from."""
    conv = ((pol["source_library"].get("flow") or {}).get("transitions") or {}).get("conversion")
    if not isinstance(conv, dict):
        raise AdmissionError(f"FATAL: {POLICY}#source_library.flow.transitions.conversion is not declared")
    return conv


def accepted_containers(pol: dict[str, Any]) -> set[str]:
    """The containers the CONVERSION stage accepts, read from the declaration that names its own origin."""
    conv = conversion_block(pol)
    declared = conv.get("accepts")
    if not isinstance(declared, list) or not declared:
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library.flow.transitions.conversion.accepts is not declared — which "
            f"containers can be admitted at all is a declared fact, not an inference (C12)"
        )
    return {_container(str(k)) for k in declared}


def _container(raw: str) -> str:
    """A declared container as one spelling: a leading dot, lowercase (the declaration and the origin must agree)."""
    return f".{raw.lower().lstrip('.')}"


def stage0_containers(pol: dict[str, Any]) -> set[str]:
    """The stage's declared container set, RESOLVED from the reference the gate names (`conversion.accepts_from`).

    D-3034: a value that merely MENTIONS a thing declares nothing; only a RESOLUTION confers the fact. So the door
    points at the declaration of record and this reader follows it — it holds no path, no key and no container of its
    own (C12), and a fixture can point at a fixture without the live tree ever being consulted.
    """
    import yaml  # local: the ladder line does not pay for a YAML parse it does not need

    origin = str(conversion_block(pol).get(STAGE0_ORIGIN_KEY) or "").strip()
    if not origin:
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library.flow.transitions.conversion.{STAGE0_ORIGIN_KEY} is not declared — the "
            f"door's `accepts` list and the conversion stage's own declaration are two homes for ONE fact, and a home "
            f"that only mentions where the other lives (a comment) declares nothing (D-3034, D-3077)"
        )
    path_part, _, key_path = origin.partition("#")
    if not path_part.strip() or not key_path.strip():
        raise AdmissionError(
            f"FATAL: conversion.{STAGE0_ORIGIN_KEY} reads {origin!r}, which is not of the form <path>#<key.path> — "
            f"a reference that cannot be resolved is not a reference (D-3034)"
        )
    path = Path(path_part.strip())
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    if not path.exists():
        raise AdmissionError(f"FATAL: conversion.{STAGE0_ORIGIN_KEY} names {path}, which does not resolve (D-795)")
    node: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in key_path.strip().split("."):
        if not isinstance(node, dict) or key not in node:
            raise AdmissionError(
                f"FATAL: conversion.{STAGE0_ORIGIN_KEY} names {origin}, whose key {key!r} is not declared — an "
                f"unresolvable reference must never read as an empty set (D-795)"
            )
        node = node[key]
    if not isinstance(node, dict) or not node:
        raise AdmissionError(
            f"FATAL: {origin} is not a mapping of container -> reader — which containers this stage can open is a "
            f"DECLARED fact, never an inference from a literal in code (C12, D-3077)"
        )
    return {_container(str(item)) for item in node}


def name_patterns(pol: dict[str, Any]) -> dict[str, re.Pattern[str]]:
    """The declared name-defect patterns, labelled by the declaration's own key names (never a label of our own)."""
    declared = pol["source_library"]
    patterns: dict[str, re.Pattern[str]] = {}
    for key, value in declared.items():
        if key.endswith("_pattern") and isinstance(value, str) and value:
            patterns[key[: -len("_pattern")]] = re.compile(value)
    if not patterns:
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library declares no *_pattern — the name-defect class would read clean on "
            f"a library it never looked at (C12)"
        )
    return patterns


def key_of(stem: str) -> str:
    """The door's OWN comparison key. A second key here would be a second identity (D-3045/C12)."""
    return sanitize_source_book(stem).strip().lower()


def corpus_index(corpus: Path) -> dict[str, list[str]]:
    """Every file the corpus home holds, by the door's key of its stem."""
    index: dict[str, list[str]] = {}
    for path in sorted(corpus.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        index.setdefault(key_of(path.stem), []).append(str(path))
    return index


def home_axes(pol: dict[str, Any]) -> dict[str, str]:
    """The AXIS each declared home orders its files by: the folder test only means anything where the axis IS the kind.

    A home whose axis is the domain keeps the owner's own topic folders at depth 1, so a file's folder is not a
    container claim and a kind-folder test there would invent a class nobody declared (the notes root would refuse
    every note the day it declares a corpus home). An axis outside the declared vocabulary is FATAL.
    """
    homes = (pol["source_library"].get("placement") or {}).get("homes")
    if not isinstance(homes, dict) or not homes:
        raise AdmissionError(f"FATAL: {POLICY}#source_library.placement.homes is not declared (C12)")
    axes: dict[str, str] = {}
    for key, entry in homes.items():
        axis = str((entry or {}).get("axis") or "")
        if axis not in ("kind", "domain"):
            raise AdmissionError(
                f"FATAL: the home {key!r} declares the axis {axis!r}, which is outside the declared vocabulary "
                f"(kind, domain) - a file's folder cannot be judged against an axis nobody declared"
            )
        axes[str(key)] = axis
    return axes


def raw_roots(pol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The roots as DECLARED, by id: `census.roots` hands back the validated shape, not the extra keys."""
    return {str(entry.get("id")): entry for entry in pol["source_library"]["roots"]}


def disposed_sets(doc: dict[str, Any]) -> tuple[set[str], set[str]]:
    """The DISPOSED sets, read once from the receipted disposition record (the owner and the applier WRITE it;
    this reader NEVER writes it — C12). Returns (suffixes out of scope, source paths settled).

    BUG-973 (2026-10-23): two shapes. `out_of_scope_by_kind` names a SUFFIX that is permanently out of scope
    (one rule settles the 241 design assets); `not_a_work` / `conversion_refused_permanently` name a SOURCE
    path that is settled. A reason outside the declared vocabulary is FATAL — never a silent skip (D-3038).
    """
    admission = doc["source_library"]["admission"]
    reasons = [str(r) for r in (admission.get("disposition_reasons") or ())]
    if not reasons:
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library.admission.disposition_reasons is EMPTY — the disposed vocabulary "
            f"must be DECLARED, never guessed (BUG-973)"
        )
    prefix = str(admission.get("admission_disposition_prefix") or "").strip()
    if not prefix:
        raise AdmissionError(
            f"FATAL: {POLICY}#source_library.admission.admission_disposition_prefix is not declared (BUG-973)"
        )
    base = _PROJECT_ROOT / prefix
    kinds: set[str] = set()
    sources: set[str] = set()
    for path in sorted(base.parent.glob(f"{base.name}*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AdmissionError(
                    f"FATAL: disposition record {path} carries a non-JSON line: {line[:80]!r}"
                ) from exc
            reason = str(rec.get("reason") or "")
            if reason not in reasons:
                raise AdmissionError(
                    f"FATAL: disposition record {path} carries reason {reason!r}, outside the declared "
                    f"vocabulary {reasons} (BUG-973)"
                )
            if reason == "out_of_scope_by_kind":
                kind = str(rec.get("kind") or "").strip().lstrip(".").lower()
                if kind:
                    kinds.add(kind)
            else:
                source = str(rec.get("source") or "").strip()
                if source:
                    sources.add(source)
    return kinds, sources


def build(pol: dict[str, Any] | None = None) -> dict[str, Any]:
    """The plan: every file classified by the door's key, and every refusal counted with its declared reason."""
    doc = pol or census.policy(POLICY)
    decl = admission_policy(doc)
    declared_decisions = decl["decisions"]
    for name in DECISIONS:
        if name not in declared_decisions:
            raise AdmissionError(
                f"FATAL: this reader produces the class {name!r} and "
                f"{POLICY}#source_library.admission.decisions does not declare it — an undeclared class is a "
                f"silent decision (D-3038/C12)"
            )
    homes = doc["source_library"]["arrangement"]
    roots = census.roots(doc)
    raw = raw_roots(doc)
    accepted = accepted_containers(doc)
    #: D-3077/BUG-907 — THE JOIN IS ENFORCED HERE, IN THE READING THAT RUNS. A door that accepts a container the
    #: stage cannot open prices a copy and a conversion that can only fail (389 rows were refused for exactly this
    #: before D-3077), and a stage that declares a container the door never admits is an engine nothing reaches.
    #: Both directions are named, and neither is defaulted.
    stage_declares = stage0_containers(doc)
    if accepted != stage_declares:
        raise AdmissionError(
            f"FATAL: the door accepts {sorted(accepted)} while the conversion stage declares "
            f"{sorted(stage_declares)} — admitted but no stage reads it {sorted(accepted - stage_declares)}, "
            f"readable but never admitted {sorted(stage_declares - accepted)} "
            f"(config/ingest_identity_gate.yaml#{STAGE0_ORIGIN_KEY} -> the stage's own declaration, D-3077)"
        )
    axes = home_axes(doc)
    patterns = name_patterns(doc)
    #: BUG-886/D-3071: the probe each ACCEPTED kind uses, read from the gate. `accepted` is the conversion
    #: stage's own set, so a kind the stage reads with NO declared probe is FATAL here rather than admitted
    #: unchecked later (C12: an absent declaration is never a zero).
    probes = probes_from(decl, AdmissionError, accepted=accepted)
    #: BUG-893/D-3073: WHAT KIND of unopenable, and what the owner should DO. Read from the same declaration
    #: block as the probes, because a defect name and its remedy are one fact and this reader may not own either.
    defects = defects_from(decl, AdmissionError)
    cache = census.cache_keys(doc)
    corpus_root = home_path(homes, "corpus_home")
    index = corpus_index(corpus_root)
    #: The DOMAIN names the corpus MATERIALISES (census_source_names.axis_vocabulary -> its own immediate
    #: subdirectories). Read, never restated: a second list here would be a second home for the topic vocabulary.
    domains = census.axis_vocabulary(doc, corpus_root)["domain"]
    disp_kinds, disp_sources = disposed_sets(doc)

    counts = {name: 0 for name in DECISIONS}
    examples: dict[str, list[str]] = {name: [] for name in DECISIONS}
    limit = int(decl["refusal_examples"])
    rows: list[dict[str, Any]] = []
    #: BUG-893/D-3073 — THE WORKLIST IS THE DATA, NOT THE ILLUSTRATION. MEASURED 2026-10-17: the plan printed its
    #: refusal examples cut to 120 characters, so the class `refused_container_corrupt` said "5" and handed back
    #: handles like `books/epub/.../How to use graphic desi gn ... ylib.` that resolve to NO file on disk. A count
    #: that cannot be walked to its rows is a declaration with no resolution (D-3034), and the owner's five
    #: corrupt containers became a sentence in a document instead of an act. Every refused row is kept here in
    #: FULL, with its class and — for a container defect — the diagnosed defect and its declared remedy.
    refused: list[dict[str, Any]] = []
    per_root: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    unseen_keys: set[str] = set()

    for root in roots:
        entry = raw.get(root["id"], {})
        if "admits_to" not in entry:
            raise AdmissionError(
                f"FATAL: the declared root {root['id']!r} does not declare 'admits_to' — a root that is silent "
                f"about where its works are admitted is a silence, never a clean answer (D-3038)"
            )
        if root["id"] not in axes:
            raise AdmissionError(
                f"FATAL: the declared root {root['id']!r} has no declared home in placement.homes - a root whose "
                f"axis is undeclared cannot be asked where a file belongs (D-3038)"
            )
        axis = axes[root["id"]]
        admits = entry.get("admits_to")
        target_root = home_path(homes, str(admits)) if admits else None
        stat = {"id": root["id"], "files": 0, "seen": 0, "never_seen": 0, "disposed": 0, "admits_to": admits or None}
        for path in sorted(root["path"].rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            suffix = path.suffix.lower()
            key = key_of(path.stem)
            stat["files"] += 1
            kind_dir = root["path"] / suffix.lstrip(".")
            #: THE TARGET PATH COMES FROM THE ROOT'S OWN DECLARED AXIS AND NOTHING ELSE (D-3062).
            #:   kind   -> below the KIND folder (books/epub/DOMAIN/sub/name)
            #:   domain -> below the ROOT itself, so the DOMAIN folder at depth 1 is CARRIED (notes/DOMAIN/sub/name)
            #: A domain-axis root read with the kind rule proposes every note at the corpus ROOT (its "kind folder"
            #: does not exist), which loses the owner's arrangement AND creates a top-level entry the domain
            #: vocabulary would then claim as a DOMAIN. The axis is declared in placement.homes; this follows it.
            if axis == "kind" and kind_dir.is_dir() and path.is_relative_to(kind_dir):
                rel = path.relative_to(kind_dir)
                rel_label = f"{root['id']}/{suffix.lstrip('.')}/{rel}"
            elif axis == "domain":
                rel = path.relative_to(root["path"])
                rel_label = f"{root['id']}/{rel}"
            else:
                rel = Path(path.name)
                rel_label = f"{root['id']}/{suffix.lstrip('.')}/{rel}"
            if key in index:
                decision = "already_in_the_corpus"
            elif key in cache:
                decision = "seen_by_an_ingest_record"
            else:
                classes = sorted(census.classify(path.name, patterns))
                if not admits:
                    decision = "refused_no_declared_corpus_home"
                elif suffix not in accepted:
                    decision = "refused_container_no_stage_reads_it"
                elif axis == "kind" and not (kind_dir.is_dir() and path.is_relative_to(kind_dir)):
                    decision = "refused_not_in_its_kind_folder"
                elif axis == "domain" and (len(rel.parts) < 2 or rel.parts[0] not in domains):
                    decision = "refused_domain_not_a_corpus_domain"
                elif classes:
                    decision = "refused_name_repair_first"
                #: BUG-886/D-3071 — ASKED LAST, and that is a DECISION with two reasons. (1) REMEDY ORDER: the
                #: branches above say WHERE a work would go or what it would be called; only a file that would
                #: otherwise be SIGNED needs the question "are these bytes openable at all". (2) COST: the probe
                #: opens the file (a zip's trailer, a pdf's head and trailer), and on this cloud-backed library a
                #: cold root pays a fetch per file — so it is asked of the ~477 candidates, never of all 1,289
                #: containers. A corrupt file that ALSO carries a defective name still reads as name-repair-first;
                #: the census counts that debt separately (T-130), so nothing is lost, and after the rename it
                #: reads as corrupt and is refused here.
                elif not is_readable(path, probes[suffix]):
                    decision = "refused_container_corrupt"
                else:
                    decision = "admit_candidate"
                #: BUG-973 (2026-10-23): a DISPOSED row overrides whatever the ladder concluded — it is DECIDED,
                #: never a refusal and never a candidate (a disposed .png would otherwise read
                #: `refused_container_no_stage_reads_it` forever).
                if suffix.lstrip(".") in disp_kinds or str(path) in disp_sources:
                    decision = "disposed"
            counts[decision] += 1
            if decision in ("already_in_the_corpus", "seen_by_an_ingest_record"):
                stat["seen"] += 1
                seen_keys.add(key)
            elif decision == "disposed":
                stat["disposed"] += 1
            else:
                stat["never_seen"] += 1
                unseen_keys.add(key)
            if decision == "admit_candidate":
                rows.append(
                    {
                        "path": str(path),
                        "rel": rel_label,
                        "root": root["id"],
                        "kind": suffix.lstrip("."),
                        "key": key,
                        "bytes": path.stat().st_size,
                        "target": str((target_root / rel).with_suffix(".md")) if target_root else "",
                    }
                )
            elif decision == "disposed":
                pass  # counted under `disposed` above — never a refusal, never a candidate (BUG-973)
            elif decision not in ("already_in_the_corpus", "seen_by_an_ingest_record"):
                #: THE WORKLIST IS THE REFUSALS, and a work the door already KNOWS is not a refusal: the two seen
                #: classes are counted and then left alone (they need no act and would double the list).
                handle = f"{root['id']}/{path.relative_to(root['path'])}"
                if len(examples[decision]) < limit:
                    examples[decision].append(handle)
                entry: dict[str, Any] = {"rel": handle, "decision": decision, "kind": suffix.lstrip(".")}
                if decision == "refused_container_corrupt":
                    defect = diagnose(path, probes[suffix], defects, AdmissionError)
                    entry["defect"] = defect
                    entry["remedy"] = str(defects[defect]["remedy"])
                refused.append(entry)
        per_root.append(stat)

    anomalies = counts["seen_by_an_ingest_record"]
    generated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "act": "T-181 admission plan",
        "authority": str(decl["authority"]),
        "generated": generated,
        "corpus_home": str(home_path(homes, "corpus_home")),
        "accepted_containers": sorted(accepted),
        #: WHAT THE PLAN TESTED, not only what it concluded: a refusal whose probe is not printed is a refusal
        #: the owner cannot argue with (BUG-886/D-3071).
        "readability_probes": probes,
        "target_rule": str(decl["target_rule"]),
        "decisions_declared": {name: str(declared_decisions[name]) for name in DECISIONS},
        "roots": per_root,
        "files": sum(stat["files"] for stat in per_root),
        "seen": sum(stat["seen"] for stat in per_root),
        "never_seen": sum(stat["never_seen"] for stat in per_root),
        "disposed": sum(stat["disposed"] for stat in per_root),
        "seen_keys": len(seen_keys),
        "unseen_keys": len(unseen_keys),
        "counts": counts,
        "examples": examples,
        "refused": refused,
        #: BUG-893/D-3073: how many rows a class may print IN FULL before the document names the class
        #: instead. Declared, because "a list a human can read" is a judgement this reader may not hold.
        "worklist_in_full": int(decl["worklist_in_full"]),
        "rows": rows,
        "rc": RC_OWNER_OWED if (counts["admit_candidate"] or anomalies) else RC_OK,
    }


def render(plan: dict[str, Any], plan_name: str = "") -> str:
    """The plan as the owner reads it: what it proposes, then every refusal with the reason it is declared under."""
    plan_path_name = plan_name or "the machine plan"
    worklist_full = int(plan.get("worklist_in_full", 0))
    lines = [
        f"# ADMISSION PLAN — {plan['generated']}",
        "",
        f"> Authority **{plan['authority']}** (T-181). The corpus home is `{plan['corpus_home']}`. This file is a",
        "> **plan**: it admits nothing, it moves nothing and it converts nothing. The act that admits a work is",
        "> separate, owner-worded and plan-first (T-183).",
        "",
        "## What is measured, and in what unit",
        "",
        f"- files in the declared library kind roots: **{plan['files']}** ({plan['seen_keys']} distinct keys they",
        f"  share with the corpus or an ingest record, {plan['unseen_keys']} distinct keys they do not)",
        f"- already in the corpus by the door's key: **{plan['counts']['already_in_the_corpus']}**",
        f"- seen by an INGEST RECORD whose corpus file now carries a different key: "
        f"**{plan['counts']['seen_by_an_ingest_record']}** (the pipeline read the work; the name moved, T-130)",
        f"- **admission candidates the pipeline has never seen: {plan['counts']['admit_candidate']}**",
        "",
        "## The target rule (declared, never inferred here)",
        "",
        f"{plan['target_rule']}",
        "",
        f"Accepted containers (declared in the conversion transition, origin `pipeline/stage0_convert.py`): "
        f"`{' '.join(plan['accepted_containers'])}`.",
        "",
        f"Readability probes, declared per kind (`container_integrity`, BUG-886): "
        f"`{' '.join(f'{kind}->{token}' for kind, token in plan['readability_probes'].items())}` — a container "
        f"an accepted kind accepts is opened before it is proposed, so a truncated download is a REFUSAL with "
        f"a remedy (re-download) and never a signed row.",
        "",
        "## Every decision, with the reason it is declared under",
        "",
        "| class | files | declared meaning |",
        "|---|---|---|",
    ]
    for name in DECISIONS:
        lines.append(f"| `{name}` | {plan['counts'][name]} | {plan['decisions_declared'][name]} |")
    lines += ["", "## THE WORKLIST — every refusal, with the act it asks for", "",
              f"Every refusal is COUNTED above and every refused row is listed in full in the machine plan "
              f"(`{plan_path_name}`) under `refused[]`. Here each class prints its rows when there are at most "
              f"{worklist_full} of them — the small classes are the ones an owner can act on one by one — and names "
              f"the class's own task when the list is longer, because a hundred-line block in a table is read by "
              f"nobody and the worklist must not become decoration.", ""]
    by_decision: dict[str, list[dict[str, Any]]] = {}
    for entry in plan.get("refused") or []:
        by_decision.setdefault(str(entry["decision"]), []).append(entry)
    for name in DECISIONS:
        if name in ("admit_candidate", "already_in_the_corpus", "seen_by_an_ingest_record", "disposed"):
            continue
        held = by_decision.get(name) or []
        lines.append(f"### `{name}` — {len(held)} row(s)")
        lines.append("")
        if not held:
            lines += ["— (none in this reading)", ""]
            continue
        if len(held) <= worklist_full:
            lines += ["| row (resolves as printed) | kind | defect | remedy |", "|---|---|---|---|"]
            for entry in held:
                lines.append(
                    f"| `{entry['rel']}` | {entry.get('kind', '')} | {entry.get('defect', '—')} | "
                    f"{entry.get('remedy', '—')} |"
                )
        else:
            lines.append(f"All {len(held)} rows are in `{plan_path_name}#refused`; this document names the class "
                         f"and its declared meaning rather than printing a block nobody reads.")
        lines.append("")
    lines += [f"## The admission candidates ({len(plan['rows'])})", "",              "| file (below its root) | key | kind | proposed corpus path | bytes |", "|---|---|---|---|---|"]
    home = plan["corpus_home"].rstrip("/") + "/"
    for row in plan["rows"]:
        shown = row["target"][len(home):] if row["target"].startswith(home) else row["target"]
        lines.append(f"| `{row['rel']}` | `{row['key'][:48]}` | {row['kind']} | `{shown}` | {row['bytes']} |")
    if not plan["rows"]:
        lines.append("| — | — | — | — | — |")
    lines += ["", "## What this plan does NOT do", "",
              "- it does not move, copy, rename or convert a single file, and a bare run writes no file;",
              "- it does not decide a TOPIC: the proposed path inherits the source's own arrangement below its",
              "  declared AXIS folder (kind for books, domain for journals:notes), and the owner may move a row's",
              "  folder (a topic is never decided by an engine, D-2898);",
              "- it does not WIDEN the corpus: a path whose first component is not a name the corpus already",
              "  materialises is refused (arrangement.share_rule, D-3062);",
              "- it does not repair a name: a defective name is refused here and rides the rename plan (T-176),",
              "  because admitting it would materialise a defect the S0.5 cache then STAMPS;",
              "- it does not read a file's content: the identity of a work is evidence by name, and the door's",
              "  metadata cache is the second voice this reading joins.", ""]
    return "\n".join(lines)


def write_plan(plan: dict[str, Any], decl: dict[str, Any], root: Path = _PROJECT_ROOT) -> list[Path]:
    """Write the plan beside its declared prefix: one human file and one machine file (a plan is a READ).

    BUG-929 — THE DAY'S NAME IS A SLOT, AND A SLOT DESTROYS WHAT A SIGNATURE PINS (the mirror of BUG-925). MEASURED
    2026-10-18: `governance/ADMISSION_ACCEPTED_20261018.yaml` pins `ADMISSION_PLAN_20261018.json` by path AND
    digest (`plan_sha256: 9852c484…`), and this function wrote `<prefix><YYYYMMDD>.json` UNCONDITIONALLY — so the
    day's second derivation replaced the bytes the owner's word names. D-3072's scope proof rescues the owner only
    while the ACTS are identical; the moment a derivation moves a row (measured: 12 rows moved once the batch had
    applied them) the pinned digest resolves to nothing and the word is unverifiable — the exact loop, one file
    over. So the day's name is used ONLY when it is free or when the plan repeats itself byte-for-byte in its acts:
    a DIFFERENT plan lands in a stamped file and never replaces the one a signature names. `newest()` already sorts
    the stamped name after the date name (`.` < `T`), so the reader needs no change.
    """
    stamp = plan["generated"][:10].replace("-", "")
    prefix = root / str(decl["plan_prefix"])
    md, js = Path(f"{prefix}{stamp}.md"), Path(f"{prefix}{stamp}.json")
    if js.is_file():
        try:
            same_acts = json.loads(js.read_text(encoding="utf-8")).get("rows") == plan["rows"]
        except json.JSONDecodeError:
            same_acts = False  # an unreadable plan is never "the same plan" — it is replaced by a NAMED new one
        if same_acts:
            return [md, js]  # idempotent: one plan, one stable digest, so every signature keeps resolving
        moment = plan["generated"].replace("-", "").replace(":", "")
        md, js = Path(f"{prefix}{moment}Z.md"), Path(f"{prefix}{moment}Z.json")
        ordinal = 2
        while js.exists():
            md, js = Path(f"{prefix}{moment}Z-{ordinal}.md"), Path(f"{prefix}{moment}Z-{ordinal}.json")
            ordinal += 1
    md.write_text(render(plan, js.name), encoding="utf-8")
    js.write_text(json.dumps(plan, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return [md, js]


def brief(plan: dict[str, Any]) -> str:
    """THE NOTIFY, in ONE line, for the ladder: what waits for the owner's word and nothing else."""
    counts = plan["counts"]
    #: EVERY declared refusal class, DERIVED from the closed vocabulary - never a hand-kept subset. The line this
    #: replaces named four of the classes in prose, so a class added later could read its count only in the plan
    #: file and never on the ladder: a declared class that reads ZERO must still be PRINTED (BUG-487), and one
    #: that is not printed at all is indistinguishable from one that does not exist.
    refusals = [name for name in DECISIONS if name.startswith("refused_")]
    refused = sum(counts[name] for name in refusals)
    detail = ", ".join(f"{name[len('refused_'):].replace('_', ' ')} {counts[name]}" for name in refusals)
    return (
        f"ADMISSION: {plan['files']} file(s) in the declared kind roots, {plan['seen']} the pipeline has seen "
        f"(by key {counts['already_in_the_corpus']}, by an ingest record {counts['seen_by_an_ingest_record']}) "
        f"|| never seen {plan['never_seen']} ({plan['unseen_keys']} key(s)): "
        f"candidates {counts['admit_candidate']}, refused {refused} ({detail}), disposed {counts['disposed']} "
        f"|| plan: just admit-plan"
    )


def selftest() -> int:
    """Known-answer controls over synthetic roots, a synthetic corpus and a synthetic cache (BUG-577/BUG-492)."""
    import tempfile

    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    def expect(label: str, condition: bool, detail: str) -> None:
        if not condition:
            mark(label, detail)

    def write_epub(path: Path) -> None:
        """A MINIMAL container a zip reader can open — the fixture must not be a claim it cannot support."""
        import zipfile
        with zipfile.ZipFile(path, "w") as book:
            book.writestr("mimetype", "application/epub+zip")
            book.writestr("META-INF/container.xml", "<container/>")

    def write_pdf(path: Path) -> None:
        """A minimal PDF: magic at the head, trailer near the end (the two ends `pdf` probes for)."""
        path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\nstartxref\n0\n%%EOF\n")

    with tempfile.TemporaryDirectory(prefix="admission_") as tmp:
        base_dir = Path(tmp)
        corpus = base_dir / "corpus"
        (corpus / "DOMAIN 6 AI + Computing").mkdir(parents=True)
        (corpus / "DOMAIN 6 AI + Computing" / "Seen Book.md").write_text("x", encoding="utf-8")
        books = base_dir / "books"
        for kind in ("epub", "pdf", "md"):
            (books / kind / "DOMAIN 6 AI + Computing").mkdir(parents=True, exist_ok=True)
        write_epub(books / "epub" / "DOMAIN 6 AI + Computing" / "Seen Book.epub")
        (books / "md" / "Renamed Work.md").write_text("x", encoding="utf-8")
        (books / "md" / "never in the corpus.md").write_text("x", encoding="utf-8")
        write_epub(books / "epub" / "DOMAIN 6 AI + Computing" / "Never Seen.epub")
        write_epub(books / "epub" / "DOMAIN 6 AI + Computing" / "A Title (z-lib.org).epub")
        (books / "epub" / "DOMAIN 6 AI + Computing" / "No Stage Reads This.mobi").write_text("x", encoding="utf-8")
        write_epub(books / "epub" / "loose at the root.epub")
        #: BUG-886: a TRUNCATED DOWNLOAD — a valid zip HEADER and no end-of-central-directory record, which is
        #: exactly the shape MEASURED in the owner's library (137,319,019 bytes, `EPUB document` by magic,
        #: `BadZipFile` by structure). A suffix test calls it an admission candidate; the probe must not.
        (books / "epub" / "DOMAIN 6 AI + Computing" / "A Truncated Download.epub").write_bytes(
            b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 512)
        write_pdf(books / "stray out of its kind folder.pdf")
        #: BUG-973: a DISPOSED fixture — one work settled by SUFFIX (a design asset, out of scope by kind) and one
        #: settled by SOURCE path (an epub the owner has said is not a work). Both must read `disposed`, never a
        #: refusal and never a candidate.
        (books / "A Design Asset.png").write_text("x", encoding="utf-8")
        write_epub(books / "epub" / "DOMAIN 6 AI + Computing" / "Settled by owner.epub")
        settled_source = str(books / "epub" / "DOMAIN 6 AI + Computing" / "Settled by owner.epub")
        #: THE NOTE ROOT DECLARES A SHARE of the ONE corpus root (D-3062): its own DOMAIN/<subtopic> path is
        #: CARRIED into the corpus, and a folder the corpus does not materialise as a DOMAIN is REFUSED.
        notes = base_dir / "notes"
        (notes / "DOMAIN 6 AI + Computing" / "design-notes").mkdir(parents=True)
        write_pdf(notes / "DOMAIN 6 AI + Computing" / "design-notes" / "A Note.pdf")
        (notes / "unsorted notes").mkdir(parents=True)
        (notes / "unsorted notes" / "Homeless Note.pdf").write_text("x", encoding="utf-8")
        unhomed = base_dir / "unhomed"
        (unhomed / "pdf").mkdir(parents=True)
        (unhomed / "pdf" / "No Home.pdf").write_text("x", encoding="utf-8")
        cache = base_dir / "book_metadata.jsonl"
        cache.write_text(
            json.dumps({"source_book": "Renamed Work.md", "author": "A Voice", "title": "Renamed Work"}) + "\n",
            encoding="utf-8",
        )
        #: BUG-973: the disposition RECORD the reader joins — one line per settled object, the shape the owner's
        #: `scripts/dispose_admission.py` and the applier write. `.png` settles the design asset by kind; the
        #: source path settles the epub by name (a file the ladder would otherwise admit).
        (base_dir / "ADMISSION_DISPOSITION_20261023-fixture.jsonl").write_text(
            json.dumps({"reason": "out_of_scope_by_kind", "kind": ".png"}) + "\n"
            + json.dumps({"reason": "not_a_work", "source": settled_source}) + "\n",
            encoding="utf-8",
        )
        #: BUG-907 — THE FIXTURE NAMES ITS OWN STAGE0 DECLARATION. This control used to compare the FIXTURE policy
        #: against the LIVE `config/pipeline_config.yaml`, which read green only while the two happened to be equal and
        #: went red the moment D-3077 widened the stage — an invariant that lived in a coincidence. Now the join is
        #: exercised on fixture bytes, and the disagreement branch (a door wider than its stage) is proved to REFUSE.
        import yaml as _yaml

        def write_stage0(name: str, containers: dict[str, str]) -> Path:
            target = base_dir / name
            target.write_text(_yaml.safe_dump({"stage0": {"containers": containers}}), encoding="utf-8")
            return target

        stage0_own = write_stage0("pipeline_config_fixture.yaml",
                                  {".epub": "pandoc_epub", ".pdf": "docling_pdf", ".md": "native_md"})
        stage0_wider = write_stage0("pipeline_config_wider.yaml",
                                    {".epub": "pandoc_epub", ".pdf": "docling_pdf", ".md": "native_md",
                                     ".rtf": "pandoc_rtf"})
        pol = {
            "source_library": {
                "roots": [
                    {"id": "books", "path": str(books), "kinds": ["epub", "pdf", "md"], "admits_to": "corpus_home"},
                    {"id": "notes", "path": str(notes), "kinds": ["pdf", "md"], "admits_to": "corpus_home"},
                    {"id": "unhomed", "path": str(unhomed), "kinds": ["pdf"], "admits_to": None},
                ],
                "metadata_cache": str(cache),
                "marker_pattern": r"(?i)\b(z-lib|1lib)\b",
                "spine_pattern": r"\s--\s|\b[0-9a-f]{16,}\b",
                "truncation_pattern": r"_$|\band\s*$",
                "arrangement": {"corpus_home": str(corpus), "drift_ceiling": 0},
                "placement": {
                    "homes": {
                        "books": {"axis": "kind", "axis_depth": 1},
                        "notes": {"axis": "domain", "axis_depth": 1},
                        "unhomed": {"axis": "domain", "axis_depth": 1},
                    }
                },
                "admission": {
                    "authority": "D-XXXX-fixture",
                    "plan_prefix": "governance/ADMISSION_PLAN_",
                    "target_rule": "fixture rule: the source's own path below its DECLARED AXIS folder, suffix -> .md",
                    "refusal_examples": 3,
                    "worklist_in_full": 3,
                    "decisions": {name: f"fixture meaning of {name}" for name in DECISIONS},
                    "disposition_reasons": ["out_of_scope_by_kind", "not_a_work", "conversion_refused_permanently"],
                    "admission_disposition_prefix": str(base_dir / "ADMISSION_DISPOSITION_"),
                    #: BUG-886/D-3071: the probe each ACCEPTED fixture kind declares. A fixture that skips this
                    #: block is FATAL (probes_from), which is the control that the declaration is required.
                    "container_integrity": {
                        "authority": "D-XXXX-fixture",
                        "probes": {".epub": "zip", ".pdf": "pdf", ".md": "none"},
                        #: BUG-893/D-3073: the fixture declares its OWN defect vocabulary, so a control can prove
                        #: the reader refuses a defect the declaration does not carry - and can drive the
                        #: apple_bookmark shape the owner's library actually holds.
                        "defects": {
                            token: {"meaning": f"fixture meaning of {token}", "remedy": f"fixture remedy for {token}"}
                            for token in ("truncated_zip_no_central_directory", "truncated_pdf_no_trailer",
                                          "null_bytes", "apple_bookmark", "no_magic", "unrecognised")
                        },
                    },
                },
                "flow": {
                    "authority": "D-3050",
                    "transitions": {
                        "conversion": {
                            "command": "python3 pipeline/stage0_convert.py",
                            "accepts": [".epub", ".pdf", ".md"],
                            "accepts_from": f"{stage0_own}#stage0.containers",
                        }
                    },
                    "no_sync": {"fact": "fixture"},
                },
            }
        }
        plan = build(pol)
        counts = plan["counts"]
        rows = {Path(row["path"]).name: row for row in plan["rows"]}
        own_lines = Path(__file__).resolve().read_text(encoding="utf-8").splitlines()
        own = "\n".join(own_lines)

        # (1) a work the corpus holds by KEY is not a candidate; (11) an ingest record alone still reads SEEN
        expect(CONTROL_LABELS[0], counts["already_in_the_corpus"] >= 1 and "Seen Book.epub" not in rows,
               f"a work the corpus holds by key read {counts['already_in_the_corpus']} already-in-corpus")
        expect(CONTROL_LABELS[1], counts["seen_by_an_ingest_record"] >= 1 and counts["admit_candidate"] >= 1,
               f"an ingest record's own work read {counts['seen_by_an_ingest_record']} and the never-seen "
               f"candidates {counts['admit_candidate']} — 'Renamed Work' must be seen, 'Never Seen' a candidate")

        # (2) a never-seen work is a candidate whose target is DERIVED below the corpus home
        row = rows.get("Never Seen.epub", {})
        expect(CONTROL_LABELS[2],
               bool(row) and str(corpus) in str(row.get("target", "")) and str(row["target"]).endswith("Never Seen.md")
               and "DOMAIN 6 AI + Computing" in str(row["target"]),
               f"the candidate row read {row} — expected a target below the corpus home with the source's own "
               f"sub-path and the .md suffix the conversion stage writes")

        # (18) a NOTE keeps its DOMAIN folder and its own subtopic; a folder the corpus does not materialise is REFUSED
        note = rows.get("A Note.pdf", {})
        expect(CONTROL_LABELS[19],
               bool(note) and str(note.get("target", "")).endswith("DOMAIN 6 AI + Computing/design-notes/A Note.md")
               and counts["refused_domain_not_a_corpus_domain"] == 1,
               "the note row read " + str(note) + " and the undeclared-folder refusal read "
               + str(counts["refused_domain_not_a_corpus_domain"]) + " — a note must KEEP its DOMAIN folder and its "
               "own subtopic (the owner's arrangement, never an engine's topic), and a source folder the corpus does "
               "not materialise must be REFUSED rather than widen the domain vocabulary")

        # (3) a container no stage reads is REFUSED and counted; (5) an undeclared corpus home is REFUSED
        expect(CONTROL_LABELS[3], counts["refused_container_no_stage_reads_it"] == 1,
               f"a .mobi read {counts['refused_container_no_stage_reads_it']}, expected 1 (counted, never skipped)")
        #: label 10 was CITED BY NOTHING before BUG-895: every label printed, so a control with no assertion
        #: behind it read green. This asserts the fact its name claims, and the citation control below keeps the
        #: whole table honest.
        expect(CONTROL_LABELS[10],
               counts["seen_by_an_ingest_record"] == 1
               and not any("Renamed Work" in row["rel"] for row in plan["rows"]),
               f"an ingest-record work read {counts['seen_by_an_ingest_record']} and "
               f"{[r['rel'] for r in plan['rows'] if 'Renamed' in r['rel']]}")
        expect(CONTROL_LABELS[5], counts["refused_no_declared_corpus_home"] == 1,
               f"the notes root (admits_to null) read {counts['refused_no_declared_corpus_home']}, expected 1")

        # (4) a defective name is refused as repair-first; the class names come from the DECLARATION's own keys
        expect(CONTROL_LABELS[4], counts["refused_name_repair_first"] == 1
               and plan["examples"]["refused_name_repair_first"],
               f"a marker-named file read {counts['refused_name_repair_first']}, expected 1")

        # (6) a root that does not declare admits_to is FATAL; (12) a class the declaration lacks is FATAL
        absent_key = json.loads(json.dumps(pol))
        absent_key["source_library"]["roots"][0].pop("admits_to")
        try:
            build(absent_key)
            mark(CONTROL_LABELS[6], "a root with no 'admits_to' did not raise (a silence read as an answer)")
        except AdmissionError:
            pass
        short_vocab = json.loads(json.dumps(pol))
        short_vocab["source_library"]["admission"]["decisions"] = {"admit_candidate": "only this one"}
        try:
            build(short_vocab)
            mark(CONTROL_LABELS[13], "a decision the declaration does not carry did not raise")
        except AdmissionError:
            pass
        expect(CONTROL_LABELS[13], counts["refused_not_in_its_kind_folder"] >= 1
               and all(name in plan["decisions_declared"] for name in DECISIONS),
               "the declared vocabulary must carry every class this reader produces, zero rows included")

        # (7) an absent root is FATAL, never a zero; (8) an absent declaration key is FATAL; (9) an absent home
        gone = json.loads(json.dumps(pol))
        gone["source_library"]["roots"][0]["path"] = str(base_dir / "not here")
        try:
            build(gone)
            mark(CONTROL_LABELS[7], "an absent root did not raise (an absent root is never a count of zero)")
        except SystemExit:
            pass
        for key in ("authority", "plan_prefix", "target_rule", "refusal_examples", "worklist_in_full",
                    "decisions"):
            missing = json.loads(json.dumps(pol))
            missing["source_library"]["admission"].pop(key)
            try:
                build(missing)
                mark(CONTROL_LABELS[8], f"an absent admission.{key} did not raise")
            except AdmissionError:
                pass
        no_home = json.loads(json.dumps(pol))
        no_home["source_library"]["arrangement"]["corpus_home"] = str(base_dir / "nowhere")
        try:
            build(no_home)
            mark(CONTROL_LABELS[9], "a corpus home that does not resolve did not raise")
        except AdmissionError:
            pass

        # (10) the declared accepted set RESOLVES to the stage's own declaration, and the join REFUSES a disagreement
        #      (BUG-907, three-sided: it holds, a WIDER door raises, and an absent reference is never read as one)
        expect(CONTROL_LABELS[11], accepted_containers(pol) == stage0_containers(pol),
               f"the declared containers {sorted(accepted_containers(pol))} disagree with the stage declaration it "
               f"names ({sorted(stage0_containers(pol))}) — the stage's declaration of record is the one the gate "
               f"points at (D-3077)")
        import copy

        wider = copy.deepcopy(pol)
        wider["source_library"]["flow"]["transitions"]["conversion"]["accepts_from"] = (
            f"{stage0_wider}#stage0.containers")
        try:
            build(wider)
        except AdmissionError:
            pass
        else:
            mark(CONTROL_LABELS[11],
                 "a door accepting a container the stage does not declare did NOT raise — a row priced for a "
                 "conversion no engine would perform")

        unnamed = copy.deepcopy(pol)
        unnamed["source_library"]["flow"]["transitions"]["conversion"].pop("accepts_from")
        try:
            build(unnamed)
        except AdmissionError:
            pass
        else:
            mark(CONTROL_LABELS[11],
                 "an absent accepts_from did NOT raise — a comment that MENTIONS the origin would then read as one "
                 "(D-3034)")

        # (12) the key is the DOOR's own key: the same function on both sides of the join, and no second one here
        door = sanitize_source_book("Seen Book").strip().lower()
        expect(CONTROL_LABELS[12],
               key_of("Seen Book") == door
               and key_of("Seen Book") == key_of("seen book")
               and key_of("A Title (z-lib.org)") == sanitize_source_book("A Title (z-lib.org)").strip().lower()
               # built from pieces: a control that hardcodes the name it forbids matches its OWN source (BUG-492)
               and ("def saniti" + "ze") not in own,
               f"the reader's key read {key_of('Seen Book')!r} against the door's own {door!r} - it must BE that key")

        # (17) THE DECLARED AXIS (the latent class this reader first got wrong, and CLOSED by D-3062): a home whose
        # axis is NOT the kind keeps the owner's own topic folders, so the SAME file must read as a CANDIDATE there
        # and never as "out of its kind folder" - the kind-folder test means something only where the axis IS the
        # kind. The base fixture now DECLARES that share, so this control isolates the class the other way: it removes
        # the root that declares NO home, leaving one domain-axis home whose works DO have a home.
        domain_home = json.loads(json.dumps(pol))
        domain_home["source_library"]["roots"] = [
            r for r in domain_home["source_library"]["roots"] if r["id"] != "unhomed"
        ]
        with_home = build(domain_home)
        expect(CONTROL_LABELS[14],
               with_home["counts"]["refused_not_in_its_kind_folder"] == 1
               and with_home["counts"]["refused_no_declared_corpus_home"] == 0
               and any(row["rel"].startswith("notes/") for row in with_home["rows"]),
               f"a domain-axis home with a corpus home read {with_home['counts']} - the note must be an "
               f"CANDIDATE, and only the books fixture file (a .pdf under books/epub) may be out of its kind folder")

        # (18) an axis outside the declared vocabulary is FATAL: guessing what a folder means is how a class nobody
        # declared gets invented
        bad_axis = json.loads(json.dumps(pol))
        bad_axis["source_library"]["placement"]["homes"]["books"]["axis"] = "vibes"
        try:
            build(bad_axis)
            mark(CONTROL_LABELS[17], "an axis outside the declared vocabulary did not raise")
        except AdmissionError:
            pass
        no_homes = json.loads(json.dumps(pol))
        no_homes["source_library"]["placement"].pop("homes")
        try:
            build(no_homes)
            mark(CONTROL_LABELS[17], "an absent placement.homes did not raise")
        except AdmissionError:
            pass

        # (19) BUG-886/D-3071: a container of an ACCEPTED kind whose BYTES do not open is REFUSED as CORRUPT and is
        #      never proposed for the owner's word. TWO-SIDED: the truncated fixture file must be refused AND the
        #      valid one in the same folder must still be a candidate, so a probe that simply refused every `.epub`
        #      fails this control too (a refusal that answers everything is not a reading).
        truncated = books / "epub" / "DOMAIN 6 AI + Computing" / "A Truncated Download.epub"
        expect(CONTROL_LABELS[20],
               counts["refused_container_corrupt"] == 1
               and not any("A Truncated Download" in row["rel"] for row in plan["rows"])
               and any("A Truncated Download" in item for item in plan["examples"]["refused_container_corrupt"])
               and is_readable(truncated, "zip") is False
               and is_readable(books / "epub" / "DOMAIN 6 AI + Computing" / "Never Seen.epub", "zip") is True
               and any(row["rel"].endswith("Never Seen.epub") for row in plan["rows"]),
               f"corrupt {counts['refused_container_corrupt']} | rows "
               f"{[r['rel'] for r in plan['rows'] if 'Seen' in r['rel']]}")

        # (20) an ACCEPTED kind with no declared probe is FATAL: silence about how a kind is opened is how a
        #      truncated container gets admitted unchecked, one declaration edit later (D-3034/C12).
        no_probe = json.loads(json.dumps(pol))
        no_probe["source_library"]["admission"]["container_integrity"]["probes"].pop(".md")
        try:
            build(no_probe)
            mark(CONTROL_LABELS[21], "an accepted kind with no declared probe did not raise")
        except AdmissionError:
            pass
        unknown_probe = json.loads(json.dumps(pol))
        unknown_probe["source_library"]["admission"]["container_integrity"]["probes"][".epub"] = "vibes"
        try:
            build(unknown_probe)
            mark(CONTROL_LABELS[21], "an unknown probe token did not raise")
        except AdmissionError:
            pass

        # (21) BUG-893/D-3073: THE WORKLIST RESOLVES. MEASURED 2026-10-17: the plan printed its refusal examples
        #      cut to 120 characters, so a class that counted 5 handed back handles that named no file - the
        #      owner's five corrupt containers could not be walked to an act. TWO-SIDED by construction: every
        #      refused `rel` must resolve to a file on disk (a truncation anywhere in the list fails it) AND the
        #      count must equal the list (a reading whose total disagrees with its rows is two readings), while
        #      the valid siblings in the same folders must still be CANDIDATES - a worklist built by refusing
        #      everything would pass the first half and fail that.
        alias = books / "pdf" / "DOMAIN 6 AI + Computing" / "A Finder Alias.pdf"
        alias.write_bytes(b"book\x00\x00\x00\x00mark" + b"\x00" * 16
                          + b"/Applications/Somewhere/Plug-ins/docs/Keylight_1.2_AE.pdf")
        with_alias = build(pol)
        roots_by_id = {"books": books, "notes": notes, "unhomed": unhomed}
        refused_rows = with_alias["refused"]
        unresolved = [e["rel"] for e in refused_rows
                      if not (roots_by_id[e["rel"].split("/", 1)[0]] / e["rel"].split("/", 1)[1]).is_file()]
        refusal_classes = [name for name in DECISIONS
                           if name not in ("admit_candidate", "already_in_the_corpus", "seen_by_an_ingest_record",
                                          "disposed")]
        corrupt_rows = [e for e in refused_rows if e["decision"] == "refused_container_corrupt"]
        expect(CONTROL_LABELS[22],
               not unresolved
               and len(refused_rows) == sum(with_alias["counts"][name] for name in refusal_classes)
               and len(corrupt_rows) == 2
               and {e.get("defect") for e in corrupt_rows}
               == {"truncated_zip_no_central_directory", "apple_bookmark"}
               and all(e.get("remedy")
                       == pol["source_library"]["admission"]["container_integrity"]["defects"][e["defect"]]["remedy"]
                       for e in corrupt_rows)
               and not any("A Truncated Download" in row["rel"] or "A Finder Alias" in row["rel"]
                           for row in with_alias["rows"])
               and any(row["rel"].endswith("Never Seen.epub") for row in with_alias["rows"]),
               f"unresolved {unresolved[:3]} | refused {len(refused_rows)} vs counted "
               f"{sum(with_alias['counts'][name] for name in refusal_classes)} | "
               f"defects {[e.get('defect') for e in corrupt_rows]}")

        # (22) a defect the declaration does not carry is FATAL: printing a shape nobody named as though it were
        #      diagnosed is how a worklist acquires a row with no remedy (D-3034/D-3038).
        undeclared = json.loads(json.dumps(pol))
        undeclared["source_library"]["admission"]["container_integrity"]["defects"].pop("apple_bookmark")
        try:
            build(undeclared)
            mark(CONTROL_LABELS[23], "an undeclared defect did not raise")
        except AdmissionError:
            pass
        no_defects = json.loads(json.dumps(pol))
        no_defects["source_library"]["admission"]["container_integrity"].pop("defects")
        try:
            build(no_defects)
            mark(CONTROL_LABELS[23], "an absent defect vocabulary did not raise")
        except AdmissionError:
            pass

        # (26) BUG-973: a DISPOSED row is SETTLED, not refused and not a candidate. TWO-SIDED: the .png settled by
        #      SUFFIX (which the ladder would otherwise refuse as `refused_container_no_stage_reads_it` forever, so
        #      that class must still read exactly 1 — the .mobi alone) and the epub settled by SOURCE path (which
        #      the ladder would otherwise admit). Neither may enter a refusal count, the candidate worklist, or the
        #      unseen-key total, so the disposed key is excluded from every lane that waits for an act.
        expect(CONTROL_LABELS[26],
               counts["disposed"] == 2
               and plan["disposed"] == 2
               and counts["refused_container_no_stage_reads_it"] == 1
               and not any("Settled by owner" in row["rel"] for row in plan["rows"])
               and not any("A Design Asset" in e["rel"] for e in plan["refused"]),
               f"disposed {plan['disposed']} (counts {counts['disposed']}), no-stage "
               f"{counts['refused_container_no_stage_reads_it']} (must stay 1 — the .mobi alone), candidates "
               f"{[r['rel'] for r in plan['rows'] if 'Settled' in r['rel']]}, refusals "
               f"{[e['rel'] for e in plan['refused'] if 'Design' in e['rel']]}")

        # (27) BUG-973: a disposition REASON outside the declared vocabulary is FATAL, never a silent skip (D-3038).
        bad_reason = json.loads(json.dumps(pol))
        bad_reason["source_library"]["admission"]["admission_disposition_prefix"] = str(base_dir / "BAD_DISPOSITION_")
        (base_dir / "BAD_DISPOSITION_20261023.jsonl").write_text(
            json.dumps({"reason": "made_up_reason", "kind": ".png"}) + "\n", encoding="utf-8")
        try:
            build(bad_reason)
            mark(CONTROL_LABELS[27], "a disposition reason outside the declared vocabulary did not raise")
        except AdmissionError:
            pass

        # (13) a bare run writes NOTHING: one PRODUCTION write call site, behind --plan (read from this file's own
        #      bytes). The needle matches the line whose assignment target is EXACTLY `paths`, so the selftest's
        #      own fixture calls (`first_paths`, `repeat_paths`, `moved_paths` — which TEST write_plan for BUG-929)
        #      do not count: a fixture is not a production write, and a bare run still writes nothing.
        needle = "paths = write_" + "plan("
        calls = [i for i, line in enumerate(own_lines) if line.strip().startswith(needle)]
        branch = next((i for i, line in enumerate(own_lines) if line.strip().startswith("elif args.plan:")), None)
        leaks = [
            token
            for token in ("~" + "/Library/CloudStorage", "knowledge " + "pipeline/books", "educa" + "tion/")
            if token in own
        ]
        expect(CONTROL_LABELS[16], len(calls) == 1 and branch is not None and calls[0] > branch and not leaks,
               f"a bare run could write ({calls} vs the --plan branch at {branch}) or the reader restates "
               f"{leaks} — it names no path, key or container of its own (C12)")

        # (14) the ONE-line brief carries the same numbers as the full reading
        line = brief(plan)
        expect(CONTROL_LABELS[15],
               "\n" not in line
               and str(counts["admit_candidate"]) in line
               and str(plan["never_seen"]) in line
               and line.startswith("ADMISSION:"),
               f"the brief read {line!r} — one line, carrying the reading's own numbers")

    # (15) BUG-883: ONE text form for ONE work. The same name minted from NFC and from NFD must be the SAME key,
    #      and two genuinely different names must STAY different (two-sided: a normaliser that flattened everything
    #      would satisfy the first half alone). MEASURED 2026-10-17: the corpus held 'Galič' (U+010D) while the
    #      source library held 'c'+U+030C for the identical work, so the reader called an in-corpus work a NEW
    #      candidate and the writer refused the row it had priced — a workspace that disagreed with itself.
    expect(CONTROL_LABELS[18],
           key_of("Galič2017_Article") == key_of("Galic\u030c2017_Article")
           and key_of("Another Work") != key_of("Galič2017_Article"),
           f"NFC {key_of('Galič2017_Article')!r} vs NFD {key_of('Galic\u030c2017_Article')!r}")

    # (23) BUG-895: A LABEL NOBODY CITES PRINTS GREEN. MEASURED 2026-10-17: labels appended mid-table were not
    #      pointed at by the code that names them, so the tail was shifted by one or two - the NFC control reported a
    #      note/domain assertion, the domain-home control reported the bare-run assertion, and label 10 had NO
    #      assertion at all yet printed `ok`, because the printer reads the LABEL TABLE and not the assertions. This
    #      reads this file's own text: every index in the table must be cited, so a label can never again be a name
    #      with nothing behind it. (Duplicates are fine - one label may carry two halves of one rule.)
    cited = {int(match) for match in re.findall(r"CONTROL_LABELS\[(\d+)\]", Path(__file__).read_text("utf-8"))}
    expect(CONTROL_LABELS[24], cited == set(range(len(CONTROL_LABELS))),
           f"label index (or indices) {sorted(set(range(len(CONTROL_LABELS))) - cited)} print ok with no assertion")

    # (24) BUG-929: THE PLAN'S DAY NAME IS A SLOT, EXACTLY AS THE ACCEPTANCE'S WAS (BUG-925). MEASURED 2026-10-18:
    #      `ADMISSION_ACCEPTED_20261018.yaml` pins `ADMISSION_PLAN_20261018.json` by path AND digest, and the
    #      writer named the plan by DATE ONLY and wrote it unconditionally — so the day's second derivation
    #      replaced the bytes the owner's word names. Three sides: a REPEAT (same acts) does not rewrite the file
    #      (one plan keeps one digest), a CHANGED plan lands somewhere else and leaves the pinned bytes intact, and
    #      the changed plan is still readable (a new name is not a silent drop).
    with tempfile.TemporaryDirectory() as plan_tmp:
        plan_root = Path(plan_tmp)
        plan_decl = {"plan_prefix": str(plan_root / "PLAN_")}
        first_plan = json.loads(json.dumps(plan))  # the FIXTURE's real plan: every key the renderer needs
        first_paths = write_plan(first_plan, plan_decl)
        first_bytes = first_paths[1].read_bytes()
        repeat_paths = write_plan(json.loads(json.dumps(first_plan)), plan_decl)
        moved_plan = json.loads(json.dumps(first_plan))
        moved_plan["rows"] = list(moved_plan["rows"]) + [dict(moved_plan["rows"][0], rel="a moved row")]
        moved_paths = write_plan(moved_plan, plan_decl)
        expect(CONTROL_LABELS[25],
               repeat_paths[1] == first_paths[1] and first_paths[1].read_bytes() == first_bytes
               and moved_paths[1] != first_paths[1] and first_paths[1].read_bytes() == first_bytes
               and json.loads(moved_paths[1].read_text("utf-8"))["rows"] == moved_plan["rows"],
               "a second derivation of the day replaced the plan a signature pins")

    failed = {label for label, _ in failures}
    for label in CONTROL_LABELS:
        print(f"  {'FAIL' if label in failed else 'ok  '} {label}")
    for label, detail in failures:
        print(f"CONTROL FAILED [{label}]: {detail}", file=sys.stderr)
    if failures:
        return RC_FATAL
    print(f"selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} controls green")
    return RC_OK


def main(argv: list[str] | None = None) -> int:
    """CLI: (default) the reading | --brief (ONE line) | --plan (writes the plan) | --json | --selftest."""
    parser = argparse.ArgumentParser(description="The admission plan: what the pipeline has never seen (READ-ONLY).")
    parser.add_argument("--brief", action="store_true", help="ONE line for the ladder")
    parser.add_argument("--plan", action="store_true", help="write the plan (one .md and one .json) - a READ + 2 files")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    plan = build()
    if args.json:
        print(json.dumps({k: v for k, v in plan.items() if k != "rows"}, indent=2, sort_keys=False))
    elif args.plan:
        paths = write_plan(plan, admission_policy(census.policy(POLICY)))
        print(f"plan written: {', '.join(str(path) for path in paths)}")
    elif args.brief:
        print(brief(plan))
    else:
        counts = plan["counts"]
        print(f"admission: {plan['files']} file(s) in the declared kind roots | seen {plan['seen']} "
              f"(corpus {counts['already_in_the_corpus']}, ingest record {counts['seen_by_an_ingest_record']}) "
              f"| never seen {plan['never_seen']} in {plan['unseen_keys']} key(s)")
        for name in DECISIONS:
            print(f"  {counts[name]:6d}  {name}")
        home = plan["corpus_home"].rstrip("/") + "/"
        for row in plan["rows"][:12]:
            landed = row["target"][len(home):] if row["target"].startswith(home) else row["target"]
            print(f"  admit  {row['rel'][:64]:64s} -> {landed[:64]}")
        if len(plan["rows"]) > 12:
            print(f"  ... {len(plan['rows']) - 12} more candidates (--plan writes the full table, --json the machine form)")
        print(f"  corpus home: {plan['corpus_home']} | accepted: {' '.join(plan['accepted_containers'])}")
    return int(plan["rc"])


if __name__ == "__main__":
    sys.exit(main())
