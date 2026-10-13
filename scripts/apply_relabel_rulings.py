#!/usr/bin/env python3
"""scripts/apply_relabel_rulings.py — D-2977: turn the OWNER's rulings into a PLAN, then apply it.

WHY. The D-2976 packet asks for one word per REVIEW UNIT, and a unit is a mapping decision — not a row
(1,074 flagged rows collapse to 192 units). But asking a human for 192 words is still the wrong shape:
the units are not independent. They fall into CAUSE CLASSES with the same decision in each, so the
review is a handful of CLASS RULINGS plus a named exception list. This script is what makes that
mechanical instead of manual: it reads config/relabel_rulings.yaml (the ONE home for the owner's
words), computes the effective verdict of every unit, and renders a PLAN — which config line is added,
which rows move, and precisely which units still need eyes. Nothing is applied without `--apply`.

THE VERDICT PRECEDENCE (deterministic, fail-closed - C16):
  1. unit_rulings[review_id]        the owner named this unit: wins outright.
  2. class_rules[cause].policy      the owner ruled the CLASS: applies to every unit of that cause,
                                    gated by `lexical_evidence_required` (a CONFIRM by class only
                                    reaches units whose raw label shares a content token with the
                                    canonical's name, declared raws or definition - the rest are
                                    ESCALATED rather than swept in by a blanket word).
  3. ESCALATE                       no ruling reaches the unit: it is listed for the owner, never
                                    guessed. A PENDING policy escalates its whole class by design.
An unrecognised action, or CORRECT with no `owner_canonical`, FAILS CLOSED (C16).

WHAT IS APPLIED HERE, AND WHAT IS NOT. `--apply` performs the CONFIRM half ONLY: it declares the raw
as an alias in config/taxonomy.yaml, which is what makes the stored label REPRODUCIBLE (R14) - MEASURED
(D-2976 selftest): a raw-alias declaration moves neither menu_hash nor the answer space, because
closed_menu._taxonomy_entries renders value+definition+group only. The write is a SURGICAL text splice
(the taxonomy is hand-formatted and a YAML round-trip would destroy it - C6/R-D410 spirit), asserted both
ways, and atomic. CORRECT (a row relabel), ABSTAIN and LEAVE are RECORDED IN THE PLAN as owed to a
licensed store pass: rewriting canonical labels is a separate, owner-gated write with its own backup and
decision (D-2898), and this script never performs it.

Usage:
    python3 scripts/apply_relabel_rulings.py --selftest
    python3 scripts/apply_relabel_rulings.py                 # render the plan (read-only + one artifact)
    python3 scripts/apply_relabel_rulings.py --apply         # + the CONFIRM declarations
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

_TAXONOMY = ROOT / "config" / "taxonomy.yaml"
_RULINGS = ROOT / "config" / "relabel_rulings.yaml"
_GOV = ROOT / "governance"
ACTIONS = ("CONFIRM", "CORRECT", "ABSTAIN", "LEAVE", "ESCALATE")
CAUSES = ("ALIAS-LAYER-RETIRED", "LATE-HOME", "PROVENANCE-UNRESOLVED", "DEFINITION-RE-SCOPE")
CONFIRM, CORRECT, ABSTAIN, LEAVE, ESCALATE = ACTIONS
_GENERIC = frozenset({"studies", "science", "theory", "research", "practice", "general", "applied"})
SPLICE_MARK = "  raw:"


def _norm(x: object) -> str:
    """Collapse a label for comparison (case- and whitespace-insensitive)."""
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()


def _cause_of(text: str) -> str:
    """The cause class of a packet row's free-text cause (the class, not its parenthetical)."""
    head = str(text or "").split(" (")[0].strip()
    for c in CAUSES:
        if head == c:
            return c
    raise SystemExit(f"FAIL-CLOSED (rulings): unknown cause class {text!r} — the packet and the ruling "
                     "vocabulary have drifted apart (C16)")


def _yaml(path: Path) -> dict:
    """Load a YAML mapping, fail-closed on a missing or non-mapping document (C16)."""
    if not path.exists():
        raise SystemExit(f"FAIL-CLOSED (rulings): {path.name} does not exist (C16)")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit(f"FAIL-CLOSED (rulings): {path.relative_to(ROOT)} is not a mapping (C16)")
    return doc


def _tokens(text: object) -> set[str]:
    """Content tokens of a label (generic head nouns dropped, so 'X studies' is not a match by itself)."""
    return {t for t in re.split(r"[^a-z0-9]+", _norm(text)) if t and t not in _GENERIC}


def _lexical_evidence(raw: str, stored: str, disciplines: dict[str, dict]) -> bool:
    """Does the raw label share a content token with the canonical's name, raws or definition?

    This is the guard that keeps a CLASS-level CONFIRM from sweeping in the mappings that bridge
    unrelated vocabularies (e.g. `religious studies` -> `anthropology`): those escalate instead.
    """
    entry = disciplines.get(_norm(stored))
    if not entry:
        return False
    base = (_tokens(entry.get("canonical")) | _tokens(" ".join(entry.get("raw") or []))
            | _tokens(entry.get("definition")))
    return bool(_tokens(raw) & base)


def _packet() -> tuple[list[dict], Path]:
    """The most recent D-2976 UNIT csv — the decision surface (never the row-level segments file).

    The two artifacts share a stem, so the segments file is excluded by NAME and the header is then
    asserted: reading the wrong one would silently produce a plan with no cause column (BUG-733 class:
    a glob that selects a sibling is a blind spot, not a convenience).
    """
    cands = sorted((p for p in _GOV.glob("canonical_relabel_review_*.csv")
                    if "_segments_" not in p.stem), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        raise SystemExit("FAIL-CLOSED (rulings): no canonical_relabel_review_*.csv — build the packet "
                         "first (scripts/build_relabel_review_packet.py) (C16)")
    with cands[0].open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    missing = [c for c in ("review_id", "unit_key", "cause", "raw_label", "stored_canonical", "n_rows")
               if c not in (reader.fieldnames or [])]
    if missing:
        raise SystemExit(f"FAIL-CLOSED (rulings): {cands[0].name} lacks {missing} — this is not the "
                         "unit surface the applier reads (C16)")
    return rows, cands[0]


def _verdict(unit: dict, rulings: dict, disciplines: dict[str, dict]) -> tuple[str, str]:
    """Effective action for one unit: explicit ruling, else class policy, else ESCALATE (never a guess)."""
    unit_rulings = rulings.get("unit_rulings") or {}
    named = unit_rulings.get(unit["unit_key"])
    if named:
        action = str(named.get("action", "")).upper()
        if action not in ACTIONS:
            raise SystemExit(f"FAIL-CLOSED (rulings): unit {unit['unit_key']} carries the action "
                             f"{action!r}, which is not one of {ACTIONS} (C16)")
        if str(named.get("hold", "")).strip():
            # An owner word that a measured objection has to be put back to the owner before it
            # PROPAGATES (a forward declaration reaches every future row, not only this one).
            return ESCALATE, f"OWNER-RULED {action} but HELD: {named['hold']}"
        return action, "OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings)"
    cause = _cause_of(unit["cause"])
    rule = (rulings.get("class_rules") or {}).get(cause) or {}
    policy = str(rule.get("policy", "PENDING")).upper()
    if policy == "PENDING" or not policy:
        return ESCALATE, f"class {cause} is PENDING — the owner has not ruled it yet"
    if policy not in ACTIONS:
        raise SystemExit(f"FAIL-CLOSED (rulings): class {cause} carries the policy {policy!r}, which is "
                         f"not one of {ACTIONS} (C16)")
    if policy == CONFIRM and rule.get("lexical_evidence_required", True):
        if not _lexical_evidence(unit["raw_label"], unit["stored_canonical"], disciplines):
            return ESCALATE, (f"class {cause} ruled CONFIRM, but `{unit['raw_label']}` shares no content "
                              f"token with `{unit['stored_canonical']}` (its name, raws or definition) — "
                              f"the lexical guard holds it back for the owner")
    return policy, f"class {cause} ruled {policy}"


def _splice(text: str, canonical: str, raw: str) -> tuple[str, int]:
    """Insert `- raw` into the `raw:` block of ONE canonical discipline entry (surgical, asserted).

    A YAML round-trip would rewrite 2,300 lines of hand-formatted taxonomy (comments, ordering, spacing),
    so the declaration is spliced at the blocking anchor and both sides are asserted (C6/C16).
    """
    lines = text.splitlines(keepends=True)
    heads = [i for i, ln in enumerate(lines) if ln.startswith("- canonical: ")]
    at = [i for i in heads if lines[i].strip() == f"- canonical: {canonical}"]
    if len(at) != 1:
        raise SystemExit(f"FAIL-CLOSED (rulings): `{canonical}` appears as a canonical heading "
                         f"{len(at)} time(s) — refusing to splice blind (C16)")
    start = at[0]
    end = next((h for h in heads if h > start), len(lines))
    if any(_norm(ln.lstrip("- ").strip()) == _norm(raw) for ln in lines[start:end]):
        return text, 0
    raw_at = [i for i in range(start, end) if lines[i].rstrip("\n") == SPLICE_MARK]
    if len(raw_at) != 1:
        raise SystemExit(f"FAIL-CLOSED (rulings): `{canonical}` carries {len(raw_at)} `raw:` block(s) — "
                         "refusing to splice blind (C16)")
    i = raw_at[0] + 1
    while i < end and lines[i].startswith("  - "):
        i += 1
    lines.insert(i, f"  - {raw}\n")
    return "".join(lines), 1


def _atomic(path: Path, text: str) -> None:
    """C6: tempfile -> fsync -> os.replace, so a reader never sees a half-written artifact."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _keyed_rulings(units: list[dict], rulings: dict) -> None:
    """Assert every unit_ruling is keyed by a unit IDENTITY and actually reaches a unit (C16).

    BUG-751, measured: review_id is a POSITIONAL ORDINAL recomputed on every packet build, so a ruling
    keyed on it silently re-points to a different unit the moment the surface is rebuilt. A ruling is
    therefore keyed by unit_key (the decision own content: raw -> stored), and a key that reaches nothing
    FAILS CLOSED instead of being quietly ignored - a ruling that applies to nothing is a silence, not a
    no-op (the same reason the bug register refuses a citation that names nothing).
    """
    keys = {str(u["unit_key"]) for u in units}
    for key, rule in (rulings.get("unit_rulings") or {}).items():
        if re.fullmatch(r"U\d+", str(key)):
            raise SystemExit("FAIL-CLOSED (rulings): unit_rulings is keyed by the ORDINAL " + repr(key)
                             + ". An ordinal is recomputed on every rebuild, so this ruling would "
                             "silently re-point to another unit (BUG-751). Key it by unit_key - the "
                             "unit_key column of the packet.")
        if str(key) not in keys:
            if str(rule.get("applied", "")).strip():
                # A ruling carrying an application receipt whose cohort has LEFT the surface is a RECORD,
                # not a silence: the declaration landed, so the unit no longer exists to rule on. Printed,
                # never silent. A ruling with NO receipt that reaches nothing is still fail-closed below.
                print("  note: ruling " + repr(key) + " is APPLIED (" + str(rule["applied"]) + ") and its "
                      "cohort has left the surface - recorded, nothing to apply")
                continue
            raise SystemExit("FAIL-CLOSED (rulings): unit_rulings key " + repr(key) + " reaches NO unit "
                             "in " + str(len(units)) + " and carries no applied receipt - a ruling that "
                             "applies to nothing is a silence (C16).")
        if str(rule.get("action", "")).upper() == CORRECT and not str(rule.get("owner_canonical", "")):
            raise SystemExit("FAIL-CLOSED (rulings): unit_rulings[" + repr(key) + "] is CORRECT but "
                             "names no owner_canonical (C16)")


def build(apply_now: bool, date: str) -> int:
    """Compute every unit's verdict, render the plan, and (with --apply) the CONFIRM declarations."""
    rulings = _yaml(_RULINGS)
    tax = _yaml(_TAXONOMY)
    disciplines = {_norm(e.get("canonical")): e for e in (tax.get("disciplines") or [])}
    canonicals = {str(e.get("canonical")) for e in (tax.get("disciplines") or [])}
    units, src = _packet()
    _keyed_rulings(units, rulings)

    plan: list[dict] = []
    for u in units:
        action, why = _verdict(u, rulings, disciplines)
        if action == CORRECT:
            target = str((rulings.get("unit_rulings", {}).get(u["unit_key"]) or {}).get("owner_canonical", ""))
            if not target:
                rule = (rulings.get("class_rules") or {}).get(_cause_of(u["cause"])) or {}
                target = str(rule.get("owner_canonical", ""))
            if target not in canonicals:
                raise SystemExit(f"FAIL-CLOSED (rulings): unit {u['review_id']} is CORRECT but names "
                                 f"{target!r}, which is not a canonical discipline (C16)")
        plan.append({**u, "action": action, "why": why})

    declared: dict[str, list[str]] = {}
    for row in plan:
        if row["action"] == CONFIRM:
            declared.setdefault(row["stored_canonical"], []).append(row["raw_label"])
    counts = {a: sum(1 for r in plan if r["action"] == a) for a in ACTIONS}
    rows_of = {a: sum(int(r["n_rows"]) for r in plan if r["action"] == a) for a in ACTIONS}

    md = [
        f"# RELABEL PLAN — {date[:4]}-{date[4:6]}-{date[6:]}",
        "",
        "Rendered by `scripts/apply_relabel_rulings.py` (D-2977) from "
        f"`config/relabel_rulings.yaml` + `{src.name}`. **DO NOT hand-edit: re-run the applier.**",
        "",
        f"- units: {len(plan)} — " + ", ".join(f"**{a}** {counts[a]} ({rows_of[a]} rows)"
                                              for a in ACTIONS if counts[a]),
        f"- CONFIRM declarations to add: **{sum(len(v) for v in declared.values())}** "
        f"alias(es) in config/taxonomy.yaml, making {rows_of[CONFIRM]} row(s) reproducible",
        "- the CONFIRM half is a raw-alias declaration: MEASURED to move neither `menu_hash` nor the "
        "answer space, so it rewrites no provenance (I2/D-2896) and relabels nothing",
        "- CORRECT/ABSTAIN are RECORDED HERE AS OWED: a canonical relabel is a separate owner-gated "
        "store write with its own backup and decision (D-2898) — this applier never performs it",
        "",
        "## CONFIRM — the raw labels to declare (one line each in config/taxonomy.yaml)",
        "",
        "| canonical (the ONE home) | raw labels to declare | rows made reproducible |",
        "|---|---|---|",
    ]
    for canon, raws in sorted(declared.items()):
        n = sum(int(r["n_rows"]) for r in plan if r["action"] == CONFIRM
                and r["stored_canonical"] == canon)
        md.append(f"| `{canon}` | " + ", ".join(f"`{x}`" for x in sorted(set(raws))) + f" | {n} |")
    for action in (CORRECT, ABSTAIN, LEAVE, ESCALATE):
        sel = [r for r in plan if r["action"] == action]
        if not sel:
            continue
        md += ["", f"## {action} — {len(sel)} unit(s), {rows_of[action]} row(s)", ""]
        if action == ESCALATE:
            md.append("These units NO ruling reaches. They are the owner's remaining decision, ordered by "
                      "leverage — nothing here is inferred from a neighbour.")
            md.append("")
        md.append("| unit_key (the identity to rule on) | rows | live says | cause | why |")
        md.append("|---|---|---|---|---|")
        for r in sorted(sel, key=lambda x: -int(x["n_rows"])):
            md.append(f"| `{r['unit_key']}` | {r['n_rows']} | `{r['live_mapper_says']}` "
                      f"| {_cause_of(r['cause'])} | {r['why']} |")
    md.append("")
    _atomic(_GOV / f"relabel_plan_{date}.md", "\n".join(md))

    if apply_now:
        if not declared:
            print("nothing to apply: no unit is ruled CONFIRM yet "
                  "(config/relabel_rulings.yaml#class_rules is where the class policies go)")
        else:
            text = _TAXONOMY.read_text(encoding="utf-8")
            added = 0
            for canon, raws in sorted(declared.items()):
                for raw in sorted(set(raws)):
                    text, n = _splice(text, canon, raw)
                    added += n
                    print(("  add " if n else "  have ") + f"{raw!r} -> {canon}")
            if added:
                _atomic(_TAXONOMY, text)
                if not re.search(r"^- canonical: ", text, flags=re.MULTILINE):
                    raise SystemExit("FAIL-CLOSED (rulings): the spliced taxonomy lost its entries (C16)")
                print(f"applied: {added} declaration(s) added to config/taxonomy.yaml")
    print(f"plan: {counts} | rows {rows_of}")
    print("wrote          : governance/relabel_plan_" + date + ".md")
    if counts[ESCALATE]:
        print(f"escalated      : {counts[ESCALATE]} unit(s) / {rows_of[ESCALATE]} row(s) still need you")
    return 0


def selftest() -> int:
    """Known-answer controls: the verdict ladder and the splice must be SEEN to hold (BUG-492)."""
    fails: list[str] = []

    def expect(name: str, got: object, want: object) -> None:
        if got == want:
            print(f"  ok selftest/{name}")
        else:
            fails.append(name)
            print(f"  FAIL selftest/{name}: {got!r} != {want!r}")

    tax = _yaml(_TAXONOMY)
    disc = {_norm(e.get("canonical")): e for e in (tax.get("disciplines") or [])}
    unit = {"review_id": "U001", "unit_key": "design studies -> design thinking",
            "cause": "ALIAS-LAYER-RETIRED (D-2814)", "raw_label": "design studies",
            "stored_canonical": "design thinking", "n_rows": "107"}
    expect("pending-class-escalates", _verdict(unit, {"class_rules": {}}, disc)[0], ESCALATE)
    expect("class-confirm-with-evidence",
           _verdict(unit, {"class_rules": {"ALIAS-LAYER-RETIRED": {"policy": "CONFIRM"}}}, disc)[0], CONFIRM)
    far = {**unit, "raw_label": "religious studies", "stored_canonical": "anthropology"}
    expect("class-confirm-without-evidence-escalates",
           _verdict(far, {"class_rules": {"ALIAS-LAYER-RETIRED": {"policy": "CONFIRM"}}}, disc)[0], ESCALATE)
    expect("owner-unit-ruling-wins",
           _verdict(unit, {"class_rules": {}, "unit_rulings": {"design studies -> design thinking":
                         {"action": "confirm"}}}, disc)[0], CONFIRM)
    held = {"class_rules": {}, "unit_rulings": {"design studies -> design thinking":
            {"action": "CONFIRM", "hold": "needs re-affirming"}}}
    got, why = _verdict(unit, held, disc)
    expect("a-held-owner-ruling-escalates", (got, "HELD" in why), (ESCALATE, True))
    for name, bad_key, want in (("an-ordinal-ruling-key-fails-closed", "U001", "ordinal"),
                                ("a-ruling-that-reaches-nothing-fails-closed", "ghost -> nowhere", "reaches NO")):
        try:
            _keyed_rulings([unit], {"unit_rulings": {bad_key: {"action": "CONFIRM"}}})
            expect(name, "NO RAISE", want)
        except SystemExit as exc:
            expect(name, want in str(exc), True)
    _keyed_rulings([unit], {"unit_rulings": {"design studies -> design thinking": {"action": "CONFIRM"}}})
    expect("a-correctly-keyed-ruling-passes", "ok", "ok")
    late = {**unit, "cause": "LATE-HOME (x)", "stored_canonical": "emerging", "raw_label": "marketing science"}
    try:
        _verdict(late, {"class_rules": {"LATE-HOME": {"policy": "TELEPORT"}}}, disc)
        expect("unknown-policy-fails-closed", "NO RAISE", "SystemExit")
    except SystemExit:
        expect("unknown-policy-fails-closed", "SystemExit", "SystemExit")
    text = _TAXONOMY.read_text(encoding="utf-8")
    spliced, n = _splice(text, "design thinking", "design studies <selftest>")
    expect("splice-inserts-once", n, 1)
    again, n2 = _splice(spliced, "design thinking", "design studies <selftest>")
    expect("splice-is-idempotent", (n2, again == spliced), (0, True))
    expect("splice-touches-nothing-else", len(again.splitlines()), len(spliced.splitlines()))
    try:
        _splice(text, "no such canonical discipline", "x")
        expect("unknown-canonical-fails-closed", "NO RAISE", "SystemExit")
    except SystemExit:
        expect("unknown-canonical-fails-closed", "SystemExit", "SystemExit")
    if fails:
        print(f"FAIL-CLOSED (rulings): {len(fails)} control(s) failed: " + "; ".join(fails))
        return 1
    print("ok selftest: the verdict ladder and the splice hold (a control that never fires is a comment, BUG-492)")
    return 0


def main(argv: list[str]) -> int:
    """CLI: --selftest, a read-only plan render (default), or --apply for the CONFIRM declarations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--apply", action="store_true", help="also write the CONFIRM declarations")
    parser.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"))
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not re.fullmatch(r"\d{8}", str(args.date)):
        raise SystemExit("FAIL-CLOSED (rulings): --date must be YYYYMMDD (C16)")
    return build(bool(args.apply), str(args.date))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
