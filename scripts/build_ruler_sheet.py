#!/usr/bin/env python3
"""Build the G4 ruler sheet: a BLIND, stratified, human-answerable labelling sheet.

WHY: every axis measures 0.000 human-BLIND (BUG-267/F-16), so the floors in
config/eval_integrity.yaml cannot be evaluated and no model, relabel or rerun can be APPROVED.
This builds the certified core that fixes that: a bounded sample a human answers ONCE, which then
measures (a) the human share per axis -- the ruler -- and (b) how accurate the stored labels actually are.

Two strata, because they answer two different questions and must never be confused:
  stratum A (proportional)     -> the ONLY stratum the FLOOR may be measured on (population estimate)
  stratum B (forced-minority)  -> per-class precision + the F-14 FORM test. NEVER the floor: it is
                                  deliberately not proportional, so quoting a raw accuracy on it would
                                  repeat the majority-class mistake of BUG-269.

Blindness is a hard requirement: the sheet carries NO stored label, and the answer key goes to a separate
file the reviewer must not open (BUG-268 shipped sheets that leaked the answer under test).

Usage:
  python3 scripts/build_ruler_sheet.py                 # build sheet + menus + key
  python3 scripts/build_ruler_sheet.py --validate       # check a FILLED sheet before scoring
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.pipeline_paths import DB_PATH  # C12: no hardcoded paths

SHEET = REPO / "governance" / "RULER_BLIND_SHEET_20260917.csv"
KEY = REPO / "governance" / "ruler_sheet_key_20260917.json"
MENUS = REPO / "governance" / "RULER_MENUS_20260917.md"
CFG = REPO / "config" / "eval_integrity.yaml"
TAX = REPO / "config" / "taxonomy_v5.yaml"
CT = REPO / "config" / "content_types.yaml"
CHECKPOINT = DB_PATH.parent / "stage2_extract" / "t11" / "checkpoint.jsonl"  # derived, never a hardcoded root

BODY_FIELDS = ("definition", "application", "mechanism", "boundary", "source_text")
READABLE_FIRST = ("#", "item_id", "name", "DEFINITION", "APPLICATION", "MECHANISM", "BOUNDARY",
                  "SOURCE EXCERPT")
ANSWER_COLUMNS = ("CT (1-7)", "DISC (1-62)", "FORM (1-4)")
CONF_COLUMNS = ("conf_ct", "conf_disc", "conf_form")


def load_cfg() -> dict[str, Any]:
    """Load the ruler_sheet block plus the floors from eval_integrity.yaml.

    Returns:
        The configuration mapping.
    """
    import yaml
    data = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    rs = dict(data.get("ruler_sheet") or {})
    rs["min_human_share"] = data.get("min_human_share") or {}
    return rs


def vocab(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the answer menus from config, so nothing is hardcoded.

    Returns:
        Mapping with one ordered menu per axis plus the discipline group map.
    """
    import yaml
    cfg = cfg if cfg is not None else load_cfg()
    tax = yaml.safe_load(TAX.read_text(encoding="utf-8"))
    cts = yaml.safe_load(CT.read_text(encoding="utf-8"))
    disc = sorted(str(x.get("canonical")) for x in tax["disciplines"])
    # AXIS 1 is TWO vocabularies in ONE column, and the menu must offer both or it is unanswerable:
    #   content_types = the 5 ROLES that carry knowledge (principle, process_template, process_instance,
    #                   tool_instruction, growth_edge)
    #   dispositions  = what to do with an object that carries none (noise_drop, quarantine); the
    #                   'classified' pseudo-disposition is implicit and is NOT an answer.
    # Measured 2026-09-17: a menu built from content_types alone made 15 of the 150 sheet rows
    # unanswerable (6 quarantine + 9 noise_drop) and capped --validate at 1-5 while the KB uses 7 values.
    roles = list((cts.get("content_types") or {}).keys())
    disp = [k for k in (cts.get("dispositions") or {}) if k != "classified"]
    return {
        "content_type": roles + disp,
        "discipline": disc + ["emerging"],
        "extraction_type": list((cts.get("extraction_types") or {}).keys()),
        "discipline_group": {str(x.get("canonical")): str(x.get("group")) for x in tax["disciplines"]},
        "note_codes": dict(cfg.get("note_codes") or {}),
        "docs": {
            "content_type": dict(cts.get("content_types") or {}),
            "dispositions": dict(cts.get("dispositions") or {}),
            "extraction_type": dict(cts.get("extraction_types") or {}),
            "discipline": {str(x.get("canonical")): x for x in tax["disciplines"]},
        },
    }


def checkpoint_ids() -> set[str] | None:
    """Return the fb_ids present in the S2 checkpoint (used to find the F-14 untraceable pocket).

    Returns:
        Set of fb_ids, or None when the checkpoint is unavailable. None and an empty set are
        NOT the same thing: returning an empty set silently reported "0 untraceable rows" and
        quietly dropped a quota (measured 2026-09-17), which is exactly the silent-error class C16 forbids.
    """
    if not CHECKPOINT.exists():
        print("WARNING: S2 checkpoint not found at %s" % CHECKPOINT)
        print("         the F-14 untraceable quota is SKIPPED (unknown, NOT zero)")
        return None
    known: set[str] = set()
    with CHECKPOINT.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    known.add(str(json.loads(line).get("fb_id")))
                except ValueError:
                    continue
    return known


def body_len(row: dict[str, Any]) -> int:
    """Count the characters of judgeable body text for a row.

    Args:
        row: KB row.

    Returns:
        Character count over definition, application, mechanism, boundary and source text.
    """
    return len(" ".join(str(row.get(k) or "") for k in BODY_FIELDS))


def excerpt(text: Any, n: int) -> str:
    """Return a whitespace-collapsed single-line excerpt.

    Args:
        text: source text.
        n: maximum length in characters.

    Returns:
        The excerpt.
    """
    flat = re.sub(r"\s+", " ", str(text or "")).strip()
    return flat[:n]


def main() -> int:
    """Build the sheet, the menus and the answer key, or validate a filled sheet."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="check a FILLED sheet")
    args = ap.parse_args()

    cfg = load_cfg()
    menus = vocab(cfg)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("select * from fbs")]
    conn.close()

    if args.validate:
        return validate(cfg, menus)

    min_body = int(cfg.get("min_body_chars", 200))
    usable = [r for r in rows if body_len(r) >= min_body]
    dropped = len(rows) - len(usable)
    known = checkpoint_ids()
    untr = [r for r in usable if r["fb_id"] not in known] if known is not None else []

    rng = random.Random(int(cfg.get("seed", 0)))
    by_ct: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in usable:
        by_ct[str(r.get("content_type") or "?")].append(r)
    for bucket in by_ct.values():
        rng.shuffle(bucket)

    sa = cfg.get("stratum_a") or {}
    sb = cfg.get("stratum_b") or {}
    n_a, n_b = int(sa.get("n", 100)), int(sb.get("n", 50))
    quota = {ct: int(round(n_a * len(b) / len(usable))) for ct, b in by_ct.items()}
    biggest = max(quota, key=lambda k: len(by_ct[k]))
    quota[biggest] += n_a - sum(quota.values())

    picked: list[dict[str, Any]] = []
    for ct in sorted(quota):
        picked.extend([dict(r, _stratum="A") for r in by_ct[ct][: max(0, quota[ct])]])
    taken = {r["fb_id"] for r in picked}

    majority = max(by_ct, key=lambda k: len(by_ct[k]))
    each = int(sb.get("minority_content_type_each", 6))
    for ct in sorted(by_ct):
        if ct == majority:
            continue
        add = [dict(r, _stratum="B") for r in by_ct[ct] if r["fb_id"] not in taken][:each]
        picked.extend(add)
        taken.update(r["fb_id"] for r in add)

    rare_max = int(sb.get("rare_discipline_max_rows", 20))
    counts = collections.Counter(str(r.get("discipline") or "") for r in usable)
    rare = {d for d, c in counts.items() if 0 < c <= rare_max}
    pool = [dict(r, _stratum="B") for r in usable
            if str(r.get("discipline") or "") in rare and r["fb_id"] not in taken]
    rng.shuffle(pool)
    for r in pool[: int(sb.get("rare_discipline_rows", 8))]:
        taken.add(r["fb_id"])
        picked.append(r)

    if untr:
        pool = [dict(r, _stratum="B") for r in untr if r["fb_id"] not in taken]
        rng.shuffle(pool)
        for r in pool[: int(sb.get("untraceable_pocket_rows", 6))]:
            taken.add(r["fb_id"])
            picked.append(r)

    rng.shuffle(picked)
    picked = picked[: n_a + n_b]

    cap = int(cfg.get("source_excerpt_chars", 400))
    key: list[dict[str, Any]] = []
    with SHEET.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(list(READABLE_FIRST) + ["len"] + list(ANSWER_COLUMNS) + list(CONF_COLUMNS)
                   + ["note_codes", "reviewer", "date"])
        for i, r in enumerate(picked, 1):
            item = "R%03d" % i
            w.writerow([i, item, r.get("name"),
                        excerpt(r.get("definition"), cap), excerpt(r.get("application"), cap),
                        excerpt(r.get("mechanism"), cap), excerpt(r.get("boundary"), cap),
                        excerpt(r.get("source_text"), cap), body_len(r)]
                       + [""] * (len(ANSWER_COLUMNS) + len(CONF_COLUMNS) + 3))
            key.append({
                "item_id": item, "stratum": r.get("_stratum"), "fb_id": r["fb_id"],
                "name": r.get("name"), "body_chars": body_len(r),
                "untraceable_pocket": known is not None and r["fb_id"] not in known,
                "stored": {k: r.get(k) for k in ("content_type", "extraction_type", "depth",
                                                 "discipline", "domains", "status",
                                                 "content_type_source", "discipline_source")},
            })
    KEY.write_text(json.dumps(key, indent=1), encoding="utf-8")

    MENUS.write_text(render_menus(menus, rows, {r["fb_id"] for r in picked}, known), encoding="utf-8")

    print("usable %d rows (dropped %d thin) | untraceable pocket in KB: %s"
          % (len(usable), dropped, len(untr) if known is not None else "n/a (checkpoint missing)"))
    for s in ("A", "B"):
        sub = [r for r in picked if r.get("_stratum") == s]
        print("  stratum %s: n=%d" % (s, len(sub)))
        print("     content_type: %s" % dict(collections.Counter(r["content_type"] for r in sub)))
        print("     top disciplines: %s"
              % collections.Counter(str(r.get("discipline")) for r in sub).most_common(5))
    print("sheet -> %s" % SHEET.relative_to(REPO))
    print("key   -> %s  (DO NOT open while labelling: it holds the stored labels)" % KEY.relative_to(REPO))
    print("menus -> %s" % MENUS.relative_to(REPO))
    return 0


AIDS: dict[str, dict[str, dict[str, str]]] = {
    "content_type": {
        "principle": {
            "ask": "Is there ONE transferable instruction or truth here that would still hold in a different field?",
            "not_this": "a described procedure with named steps is process_template; one concrete finished case is process_instance",
            "trap": "D2587 boundary: a SINGLE transferable prescriptive sentence that acts as a filter across 3+ domains is a PRINCIPLE, not a process_template. Length is not the test; transferability is.",
        },
        "process_template": {
            "ask": "Is this a reusable SHAPE with slots I could fill for a different case (numbered steps, a checklist, a matrix)?",
            "not_this": "a single step is not a template, and a one-off narrative is not a template",
            "trap": "if the steps only make sense inside one specific tool, consider tool_instruction",
        },
        "process_instance": {
            "ask": "Is this one CONCRETE execution, with a real actor, a real case and a real outcome?",
            "not_this": "a generalisable recipe is process_template",
            "trap": "an instance can be valuable and still be an instance: do not promote it because it reads well",
        },
        "tool_instruction": {
            "ask": "Is this about how to OPERATE a specific tool, feature or interface?",
            "not_this": "a field-independent heuristic is principle",
            "trap": "tool instructions date fast; judge what it IS, not how long it lasts",
        },
        "growth_edge": {
            "ask": "Is this an open question, a frontier or an unresolved tension rather than a settled claim?",
            "not_this": "a hypothesis stated as fact is principle -- note the mismatch with note code 4",
            "trap": "the config criterion for growth_edge is that the object names what is NOT yet known",
        },
        "noise_drop": {
            "ask": "Is this descriptive or historical summary with no prescriptive filter, no template, no named method-execution and no transferable value?",
            "not_this": "if it carries SOME value but no clean role, use quarantine instead",
            "trap": "this is a DISPOSITION, not a role: answering it means the object should be DROPPED",
        },
        "quarantine": {
            "ask": "Does it carry some value but no clean role (has it steps? a method? an applicable mechanism? a transferable principle?)",
            "not_this": "if you can name the role, answer the role",
            "trap": "quarantine is a HOLD for later identification, not a judgement that the object is worthless",
        },
    },
    "extraction_type": {
        "causal_mechanism": {
            "ask": "Does the text actually show X causes Y BECAUSE Z, with the chain visible?",
            "not_this": "two things co-varying is NOT a mechanism",
            "trap": "THE known S2 bias: when the mechanism/boundary fields are in the prompt, models over-claim causal_mechanism (human agreement measured at 8%). Rule: if you cannot point at the chain in the text, it is empirical_pattern.",
        },
        "descriptive_model": {
            "ask": "Is this a structure, taxonomy or set of categories describing WHAT exists?",
            "not_this": "a rule telling you what to do is normative_heuristic",
            "trap": "test the categories: are they complete and mutually exclusive? If the text is vague about that, say so with note code 2",
        },
        "normative_heuristic": {
            "ask": "Does it tell you what to DO, without claiming to explain why it works?",
            "not_this": "an explanation of a cause is causal_mechanism, even when practical",
            "trap": "the test is practical efficacy, NOT truth: many useful heuristics are unproven",
        },
        "empirical_pattern": {
            "ask": "Is this a correlation or a recurring observation WITHOUT a shown causal chain?",
            "not_this": "if the chain is shown, it is causal_mechanism",
            "trap": "this is the correct answer far more often than intuition suggests; do not upgrade it because the claim sounds causal",
        },
    },
}

DISCIPLINE_INTRO: list[str] = [
    "**What a discipline IS:** the academic field that OWNS the object -- the field a researcher would publish",
    "it in. It is the library shelf, so it is single-valued: exactly ONE field, from the 61 canonical names plus",
    "the fail-closed catch-all 'emerging'.",
    "",
    "It is NOT a topic (that is the domains axis), NOT a role (that is content_type) and NOT a shape of claim",
    "(that is FORM).",
    "",
    "**The same word can appear in two taxonomies and still be two different objects.** 'research methodology'",
    "is a DISCIPLINE; 'research & methodology' is a DOMAIN. Same name, different namespace -- a declared homonym",
    "(D-271a, 2026-09-17). Never write a domain name into the discipline cell: the validator rejects it.",
    "",
    "**How to choose:** (1) find the group; (2) pick the field whose definition matches what the object CLAIMS;",
    "(3) if two fit, read the NOT list -- the near-neighbour is usually the trap.",
    "",
    "**'emerging' is not an answer.** It is the fail-closed catch-all: use it only when genuinely no field fits,",
    "and add note code 5.",
]


def pick_example(rows: list[dict[str, Any]], field: str, value: str, exclude: set[str],
                 traceable: set[str] | None) -> tuple[str, str] | None:
    """Pick a real KB object as a worked example, never one from the blind sheet.

    Args:
        rows: KB rows.
        field: column to match (content_type or extraction_type).
        value: value to match.
        exclude: fb_ids in the blind sheet; using one would leak an answer.
        traceable: fb_ids backed by a source record; preferred when available.

    Returns:
        (name, definition excerpt), or None when no safe example exists.
    """
    pool = [r for r in rows if str(r.get(field) or "") == value and r["fb_id"] not in exclude
            and body_len(r) >= 400]
    if traceable:
        preferred = [r for r in pool if r["fb_id"] in traceable]
        pool = preferred or pool
    if not pool:
        return None
    pool.sort(key=lambda r: str(r["fb_id"]))
    return str(pool[0].get("name")), excerpt(pool[0].get("definition"), 240)


def render_menus(menus: dict[str, Any], rows: list[dict[str, Any]], sheet_ids: set[str],
                 traceable: set[str] | None) -> str:
    """Render the answer menus with sourced definitions, tests, traps and real examples.

    Args:
        menus: vocab() output, including the docs block.
        rows: KB rows (the example source).
        sheet_ids: fb_ids in the blind sheet, excluded from examples.
        traceable: fb_ids with a source record; preferred for examples.

    Returns:
        The markdown document.
    """
    docs = menus.get("docs") or {}
    out = ["# RULER MENUS - G4 blind labelling sheet (2026-09-17)", "",
           "Generated by scripts/build_ruler_sheet.py from config/content_types.yaml and",
           "config/taxonomy_v5.yaml. DO NOT hand-edit: regenerate it.",
           "Every definition below is quoted from config; the ASK / NOT THIS / TRAP lines are reading aids;",
           "every EXAMPLE is a real object from the KB that is NOT in your sheet.",
           "",
           "CAVEAT ON THE EXAMPLES: each one illustrates the category AS THE KB CURRENTLY LABELS IT.",
           "Those stored labels are themselves under audit (F-14: 4054 rows carry a pre-repair FORM",
           "distribution), so treat an example as an illustration of the category, never as a verified",
           "answer. Your own reading of the object is the evidence.", "",
           "## 0. HOW TO ANSWER", "",
           "Write the NUMBER only, in all three answer cells of every row you answer.",
           "The three axes are orthogonal -- answer them one at a time, in this order:", "",
           "1. content_type -- what is this object FOR in the pipeline? (role, not topic)",
           "2. discipline -- which single field OWNS it? (the shelf)",
           "3. extraction_type (FORM) -- what shape of CLAIM does it make?", "",
           "Then: three confidences (0.0-1.0), up to two numbered note codes, your name, the date.", "",
           "## 1. A WORKED EXAMPLE (one real row, end to end)", ""]

    ex_ct = pick_example(rows, "content_type", "principle", sheet_ids, traceable)
    if ex_ct:
        out += ["Take an object named: **%s**" % ex_ct[0], "",
                "> %s" % ex_ct[1], "",
                "Walk it in order:",
                "- **content_type:** is there ONE transferable instruction or truth that survives a change of",
                "  field? Yes -> 1 (principle). Had it been a reusable shape with slots, it would be 2.",
                "- **discipline:** which field would publish this? Read the definitions below, then the NOT",
                "  lists. Write that field's number.",
                "- **FORM:** does the text show WHY it works (a chain) or only WHAT is true / WHAT to do?",
                "  Only WHAT -> 3 (a rule) or 2 (a description). A shown chain -> 1.",
                "- If you cannot point at the chain in the text, the answer is 4 (empirical_pattern), not 1.", ""]

    out += ["## AXIS 1 - content_type: 5 ROLES + 2 DISPOSITIONS (write 1-7)", "",
            "This axis asks what the object IS for the pipeline -- its functional role. It is not about topic.",
            "Items 1-5 are ROLES (the object carries knowledge). Items 6-7 are DISPOSITIONS (it carries none, or",
            "no clean one): answering 6 or 7 says the object should be dropped or held, not published.", ""]
    for n, lab in enumerate(menus["content_type"], 1):
        is_disp = lab in (docs.get("dispositions") or {})
        doc = (docs.get("dispositions") or {}).get(lab) if is_disp else (docs.get("content_type") or {}).get(lab)
        if isinstance(doc, dict):
            desc = doc.get("description")
        else:
            desc = doc if isinstance(doc, str) else None
        aid = (AIDS["content_type"] or {}).get(lab) or {}
        out.append("### %d. %s%s" % (n, lab, "   [DISPOSITION, not a role]" if is_disp else ""))
        out.append("")
        if desc:
            out.append("- **definition (config):** %s" % re.sub(r"\s+", " ", str(desc)))
        if aid.get("ask"):
            out.append("- **ASK:** %s" % aid["ask"])
        if aid.get("not_this"):
            out.append("- **NOT THIS:** %s" % aid["not_this"])
        if aid.get("trap"):
            out.append("- **TRAP:** %s" % aid["trap"])
        ex = pick_example(rows, "content_type", lab, sheet_ids, traceable)
        if ex:
            out.append("- **EXAMPLE (in the KB, not in this sheet):** %s -- %s" % (ex[0], ex[1]))
        out.append("")

    out += ["## AXIS 2 - discipline (SINGULAR: exactly one, write 1-62)", ""] + DISCIPLINE_INTRO + [""]
    for n, lab in enumerate(menus["discipline"], 1):
        entry = (docs.get("discipline") or {}).get(lab) or {}
        grp = menus["discipline_group"].get(lab)
        out.append("### %d. %s%s" % (n, lab, ("   _(" + grp + ")_") if grp else ""))
        out.append("")
        if entry.get("definition"):
            out.append("- **definition (config):** %s" % re.sub(r"\s+", " ", str(entry["definition"])))
        raw = entry.get("raw") or []
        if raw:
            out.append("- **also written as:** %s" % ", ".join(sorted({str(x) for x in raw})[:10]))
        exc = entry.get("exclude") or []
        if exc:
            out.append("- **NOT (near neighbours):** %s" % ", ".join(sorted({str(x) for x in exc})))
        out.append("")

    out += ["## AXIS 3 - extraction_type (epistemic FORM, write 1-4)", "",
            "This axis asks what shape of CLAIM the object makes -- independent of its role and its field.",
            "A principle can be causal, descriptive, normative or correlational; so can a process_template.",
            "FORM is orthogonal to content_type on purpose.", ""]
    for n, lab in enumerate(menus["extraction_type"], 1):
        entry = (docs.get("extraction_type") or {}).get(lab) or {}
        aid = (AIDS["extraction_type"] or {}).get(lab) or {}
        out.append("### %d. %s" % (n, lab))
        out.append("")
        if entry.get("description"):
            out.append("- **definition (config):** %s" % re.sub(r"\s+", " ", str(entry["description"])))
        if entry.get("verification_standard"):
            out.append("- **the test (config):** %s" % entry["verification_standard"])
        if aid.get("ask"):
            out.append("- **ASK:** %s" % aid["ask"])
        if aid.get("not_this"):
            out.append("- **NOT THIS:** %s" % aid["not_this"])
        if aid.get("trap"):
            out.append("- **TRAP:** %s" % aid["trap"])
        ex = pick_example(rows, "extraction_type", lab, sheet_ids, traceable)
        if ex:
            out.append("- **EXAMPLE (in the KB, not in this sheet):** %s -- %s" % (ex[0], ex[1]))
        out.append("")

    out += ["## NOTE CODES (write up to two numbers, comma-separated)", ""]
    for code, text in sorted((menus.get("note_codes") or {}).items(), key=lambda kv: int(kv[0])):
        out.append("%s. %s" % (code, text))
    out += ["", "## CONFIDENCE (0.0-1.0, one per axis)", "",
            "Your probability that the answer is right. Be honest, not optimistic: these feed a selective-risk",
            "curve and a conformal threshold, which only work if a low number means what it says.",
            "0.9+ = the definition fits cleanly. 0.6-0.8 = it fits but a neighbour nearly fits too. Below 0.5 =",
            "you are guessing: say so and use a note code.", ""]
    return "\n".join(out)


def validate(cfg: dict[str, Any], menus: dict[str, Any]) -> int:
    """Validate a FILLED sheet: completeness, menu ranges and namespace cleanliness.

    Args:
        cfg: the ruler_sheet configuration.
        menus: the answer menus.

    Returns:
        0 when the sheet is complete and valid, 1 otherwise.
    """
    import yaml
    from pipeline.schemas import validate_discipline_domain
    if not SHEET.exists():
        print("FAIL-CLOSED: no sheet at %s" % SHEET)
        return 1
    with SHEET.open(encoding="utf-8") as fh:
        sheet = list(csv.DictReader(fh))
    tax = yaml.safe_load(TAX.read_text(encoding="utf-8"))
    domains = {re.sub(r"[^a-z0-9]", "", str(x.get("canonical")).lower()) for x in tax["domains"]}
    limits = {"CT (1-7)": len(menus["content_type"]), "DISC (1-62)": len(menus["discipline"]),
              "FORM (1-4)": len(menus["extraction_type"])}
    problems: list[str] = []
    filled = 0
    for r in sheet:
        got = {c: str(r.get(c) or "").strip() for c in ANSWER_COLUMNS}
        if not any(got.values()):
            continue
        filled += 1
        for col, val in got.items():
            if not val.isdigit() or not 1 <= int(val) <= limits[col]:
                problems.append("%s: %s=%r out of range 1-%d" % (r["item_id"], col, val, limits[col]))
        if got["DISC (1-62)"].isdigit() and 1 <= int(got["DISC (1-62)"]) <= limits["DISC (1-62)"]:
            chosen = menus["discipline"][int(got["DISC (1-62)"]) - 1]
            if re.sub(r"[^a-z0-9]", "", chosen.lower()) in domains:
                problems.append("%s: discipline resolves to a DOMAIN label (%s)" % (r["item_id"], chosen))
            flags = validate_discipline_domain(chosen, None)
            if flags:
                problems.append("%s: %s" % (r["item_id"], flags[0]))
    print("sheet rows %d | answered %d | problems %d" % (len(sheet), filled, len(problems)))
    for p in problems[:20]:
        print("  FAIL " + p)
    if filled < len(sheet):
        print("INCOMPLETE: %d row(s) unanswered; the scorer refuses an incomplete sheet"
              % (len(sheet) - filled))
        return 1
    if problems:
        return 1
    print("OK: sheet complete and namespace-clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())

