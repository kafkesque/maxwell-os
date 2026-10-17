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
import ast
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

POLICY = census.POLICY
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2

#: The conversion stage's OWN accepted-container set lives in `pipeline/stage0_convert.py::SUPPORTED_EXTENSIONS`.
#: This reader does NOT import that module (it pulls the pipeline's I/O stack, and a ladder line must not pay for
#: it): the set is DECLARED in the gate's conversion transition and a control below reads the origin and refuses
#: a disagreement between the two homes.
STAGE0 = _PROJECT_ROOT / "pipeline" / "stage0_convert.py"

#: The CLOSED decision vocabulary. Every one of these must be DECLARED in the gate
#: (`source_library.admission.decisions`), a class this reader produces that the declaration does not carry is
#: FATAL, and a declared class that reads zero is PRINTED as zero (green by vacancy is visible, BUG-487).
DECISIONS = (
    "already_in_the_corpus",
    "seen_by_an_ingest_record",
    "admit_candidate",
    "refused_no_declared_corpus_home",
    "refused_container_no_stage_reads_it",
    "refused_name_repair_first",
    "refused_not_in_its_kind_folder",
    #: D-3062: a note's share of the ONE corpus root is its own DOMAIN subtree. A source folder the corpus does
    #: NOT materialise would land at the corpus TOP LEVEL, beside the DOMAIN trees - and the domain vocabulary
    #: HAS ONE MATERIALISATION (census_source_names.axis_vocabulary reads the corpus's own immediate
    #: subdirectories), so an admission would silently WIDEN it. That is a declared refusal, not a guess.
    "refused_domain_not_a_corpus_domain",
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
    "the_declared_accepted_containers_equal_the_CONVERSION_stage_own_constant",
    "the_key_is_the_DOOR_own_key_and_not_a_second_one",
    "a_decision_the_declaration_does_not_carry_is_FATAL_and_a_declared_one_reads_zero",
    "a_home_whose_axis_is_NOT_the_kind_is_never_refused_for_its_folder",
    "an_axis_outside_the_declared_vocabulary_is_FATAL_and_never_guessed",
    "a_bare_run_writes_NOTHING_and_the_reader_names_no_path_of_its_own",
    "the_ONE_line_brief_agrees_with_the_full_reading",
    "a_DOMAIN_axis_root_KEEPS_its_DOMAIN_folder_and_a_folder_the_corpus_does_not_materialise_is_REFUSED",
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
    for key in ("authority", "plan_prefix", "target_rule", "refusal_examples", "decisions"):
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


def accepted_containers(pol: dict[str, Any]) -> set[str]:
    """The containers the CONVERSION stage accepts, read from the declaration that names its own origin."""
    conv = ((pol["source_library"].get("flow") or {}).get("transitions") or {}).get("conversion")
    if not isinstance(conv, dict):
        raise AdmissionError(f"FATAL: {POLICY}#source_library.flow.transitions.conversion is not declared")
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


def stage0_containers(path: Path = STAGE0) -> set[str]:
    """The conversion stage's OWN constant, READ (never imported: the pipeline I/O stack is not worth a ladder)."""
    source = path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(target, "id", "") == "SUPPORTED_EXTENSIONS" for target in node.targets):
            continue
        if isinstance(node.value, (ast.Set, ast.Tuple, ast.List)):
            return {_container(str(item.value)) for item in node.value.elts}
    raise AdmissionError(f"FATAL: {path} no longer declares SUPPORTED_EXTENSIONS (the origin of the set)")


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
    axes = home_axes(doc)
    patterns = name_patterns(doc)
    cache = census.cache_keys(doc)
    corpus_root = home_path(homes, "corpus_home")
    index = corpus_index(corpus_root)
    #: The DOMAIN names the corpus MATERIALISES (census_source_names.axis_vocabulary -> its own immediate
    #: subdirectories). Read, never restated: a second list here would be a second home for the topic vocabulary.
    domains = census.axis_vocabulary(doc, corpus_root)["domain"]

    counts = {name: 0 for name in DECISIONS}
    examples: dict[str, list[str]] = {name: [] for name in DECISIONS}
    limit = int(decl["refusal_examples"])
    rows: list[dict[str, Any]] = []
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
        stat = {"id": root["id"], "files": 0, "seen": 0, "never_seen": 0, "admits_to": admits or None}
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
                else:
                    decision = "admit_candidate"
                unseen_keys.add(key)
            counts[decision] += 1
            if decision in ("already_in_the_corpus", "seen_by_an_ingest_record"):
                stat["seen"] += 1
                seen_keys.add(key)
            else:
                stat["never_seen"] += 1
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
            elif len(examples[decision]) < limit:
                examples[decision].append(f"{root['id']}/{path.relative_to(root['path'])}"[:120])
        per_root.append(stat)

    anomalies = counts["seen_by_an_ingest_record"]
    generated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "act": "T-181 admission plan",
        "authority": str(decl["authority"]),
        "generated": generated,
        "corpus_home": str(home_path(homes, "corpus_home")),
        "accepted_containers": sorted(accepted),
        "target_rule": str(decl["target_rule"]),
        "decisions_declared": {name: str(declared_decisions[name]) for name in DECISIONS},
        "roots": per_root,
        "files": sum(stat["files"] for stat in per_root),
        "seen": sum(stat["seen"] for stat in per_root),
        "never_seen": sum(stat["never_seen"] for stat in per_root),
        "seen_keys": len(seen_keys),
        "unseen_keys": len(unseen_keys),
        "counts": counts,
        "examples": examples,
        "rows": rows,
        "rc": RC_OWNER_OWED if (counts["admit_candidate"] or anomalies) else RC_OK,
    }


def render(plan: dict[str, Any]) -> str:
    """The plan as the owner reads it: what it proposes, then every refusal with the reason it is declared under."""
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
        "## Every decision, with the reason it is declared under",
        "",
        "| class | files | declared meaning |",
        "|---|---|---|",
    ]
    for name in DECISIONS:
        lines.append(f"| `{name}` | {plan['counts'][name]} | {plan['decisions_declared'][name]} |")
    lines += ["", "## Examples of what is refused (bounded; every refusal is COUNTED above)", ""]
    for name in DECISIONS:
        if name not in ("admit_candidate", "already_in_the_corpus", "seen_by_an_ingest_record"):
            shown = plan["examples"].get(name) or ["—"]
            lines.append(f"- `{name}`: " + "; ".join(f"`{item}`" for item in shown))
    lines += ["", f"## The admission candidates ({len(plan['rows'])})", "",
              "| file (below its root) | key | kind | proposed corpus path | bytes |", "|---|---|---|---|---|"]
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
    """Write the plan beside its declared prefix: one human file and one machine file (a plan is a READ)."""
    stamp = plan["generated"][:10].replace("-", "")
    prefix = root / str(decl["plan_prefix"])
    md, js = Path(f"{prefix}{stamp}.md"), Path(f"{prefix}{stamp}.json")
    md.write_text(render(plan), encoding="utf-8")
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
        f"candidates {counts['admit_candidate']}, refused {refused} ({detail}) || plan: just admit-plan"
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

    with tempfile.TemporaryDirectory(prefix="admission_") as tmp:
        base_dir = Path(tmp)
        corpus = base_dir / "corpus"
        (corpus / "DOMAIN 6 AI + Computing").mkdir(parents=True)
        (corpus / "DOMAIN 6 AI + Computing" / "Seen Book.md").write_text("x", encoding="utf-8")
        books = base_dir / "books"
        for kind in ("epub", "pdf", "md"):
            (books / kind / "DOMAIN 6 AI + Computing").mkdir(parents=True, exist_ok=True)
        (books / "epub" / "DOMAIN 6 AI + Computing" / "Seen Book.epub").write_text("x", encoding="utf-8")
        (books / "md" / "Renamed Work.md").write_text("x", encoding="utf-8")
        (books / "md" / "never in the corpus.md").write_text("x", encoding="utf-8")
        (books / "epub" / "DOMAIN 6 AI + Computing" / "Never Seen.epub").write_text("x", encoding="utf-8")
        (books / "epub" / "DOMAIN 6 AI + Computing" / "A Title (z-lib.org).epub").write_text("x", encoding="utf-8")
        (books / "epub" / "DOMAIN 6 AI + Computing" / "No Stage Reads This.mobi").write_text("x", encoding="utf-8")
        (books / "epub" / "loose at the root.epub").write_text("x", encoding="utf-8")
        (books / "stray out of its kind folder.pdf").write_text("x", encoding="utf-8")
        #: THE NOTE ROOT DECLARES A SHARE of the ONE corpus root (D-3062): its own DOMAIN/<subtopic> path is
        #: CARRIED into the corpus, and a folder the corpus does not materialise as a DOMAIN is REFUSED.
        notes = base_dir / "notes"
        (notes / "DOMAIN 6 AI + Computing" / "design-notes").mkdir(parents=True)
        (notes / "DOMAIN 6 AI + Computing" / "design-notes" / "A Note.pdf").write_text("x", encoding="utf-8")
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
                    "decisions": {name: f"fixture meaning of {name}" for name in DECISIONS},
                },
                "flow": {
                    "authority": "D-3050",
                    "transitions": {
                        "conversion": {
                            "command": "python3 pipeline/stage0_convert.py",
                            "accepts": [".epub", ".pdf", ".md"],
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
        expect(CONTROL_LABELS[18],
               bool(note) and str(note.get("target", "")).endswith("DOMAIN 6 AI + Computing/design-notes/A Note.md")
               and counts["refused_domain_not_a_corpus_domain"] == 1,
               "the note row read " + str(note) + " and the undeclared-folder refusal read "
               + str(counts["refused_domain_not_a_corpus_domain"]) + " — a note must KEEP its DOMAIN folder and its "
               "own subtopic (the owner's arrangement, never an engine's topic), and a source folder the corpus does "
               "not materialise must be REFUSED rather than widen the domain vocabulary")

        # (3) a container no stage reads is REFUSED and counted; (5) an undeclared corpus home is REFUSED
        expect(CONTROL_LABELS[3], counts["refused_container_no_stage_reads_it"] == 1,
               f"a .mobi read {counts['refused_container_no_stage_reads_it']}, expected 1 (counted, never skipped)")
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
        for key in ("authority", "plan_prefix", "target_rule", "refusal_examples", "decisions"):
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

        # (10) the declared accepted set is the conversion stage's OWN constant (the origin, read from its bytes)
        expect(CONTROL_LABELS[11], accepted_containers(pol) == stage0_containers(),
               f"the declared containers {sorted(accepted_containers(pol))} disagree with "
               f"{sorted(stage0_containers())} — the origin is pipeline/stage0_convert.py::SUPPORTED_EXTENSIONS")

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
        expect(CONTROL_LABELS[16],
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

        # (13) a bare run writes NOTHING: one write call site, behind --plan (read from this file's own bytes)
        needle = "paths = write_" + "plan("
        calls = [i for i, line in enumerate(own_lines) if needle in line]
        branch = next((i for i, line in enumerate(own_lines) if line.strip().startswith("elif args.plan:")), None)
        leaks = [
            token
            for token in ("~" + "/Library/CloudStorage", "knowledge " + "pipeline/books", "educa" + "tion/")
            if token in own
        ]
        expect(CONTROL_LABELS[14], len(calls) == 1 and branch is not None and calls[0] > branch and not leaks,
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
