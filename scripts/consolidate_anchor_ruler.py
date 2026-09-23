#!/usr/bin/env python3
"""Consolidate the F-11 150-row anchor from the owner's final judgement (R-D410: append-only).

Reads, in priority order, per-axis and per-row:

1. the owner's filled review sheet  -> ``owner_<axis>`` cell = the owner's ruling
2. the ruler blind sheet            -> the human label as written (never modified here)
3. the two round-2 coder artifacts  -> context only, NEVER a source of truth

and emits ONE consolidated anchor row per item with an explicit provenance tier per axis:

* ``human-ruled``       the human label stands as written (owner cell left empty)
* ``owner-adjudicated`` the owner overruled or filled the human cell on 2026-09-23
* ``declared-missing``  nobody has a label (owner may confirm with owner_keep_missing=yes)

Nothing is ever imputed from a model. An unanswered axis stays empty and is *declared*
missing, never back-filled (BUG-363 disposition).

Writes crash-safely (tempfile -> fsync -> os.replace, C6) and refuses to overwrite an
existing export unless ``--force`` is given.

Usage:
    python3 scripts/consolidate_anchor_ruler.py --report
    python3 scripts/consolidate_anchor_ruler.py --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from datetime import date as _date
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "f11_llm_coder.yaml"

AXES: tuple[str, ...] = ("content_type", "discipline", "extraction_type")
MENU_SECTION: dict[str, str] = {
    "content_type": "content_types",
    "discipline": "disciplines",
    "extraction_type": "extraction_types",
}

# Confidence suffixes are appended as " (0.42)" by the review-sheet renderer.
_CONF_SUFFIX = re.compile(r"\s*\((?:0|1)\.\d+\)\s*$")


def norm(value: object) -> str:
    """Return the look-up key of a label: lowercase, alphanumerics only.

    ``"research methodology"``, ``"researchmethodology"`` and ``"Research Methodology"``
    all collapse to ``"researchmethodology"``. Spaces, hyphens, underscores and case are
    therefore never a reason to call a value unknown.
    """
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def strip_conf(raw: str) -> str:
    """Remove a trailing confidence suffix from a rendered label."""
    return _CONF_SUFFIX.sub("", str(raw or "")).strip()


def load_config() -> dict[str, Any]:
    """Load the F-11 coder config (source of truth for paths, menus and aliases)."""
    try:
        import yaml
    except ImportError:  # pragma: no cover - PyYAML is a hard dependency of this repo
        raise SystemExit("PyYAML is required: python3 -m pip install pyyaml")
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def load_menu(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    """Return (look-up maps per axis, ordered menu values per axis) from the closed menu.

    The *value* field of each menu entry is the vocabulary a reviewer must type; the
    capitalised/normalised key is internal only and must never be shown to the owner.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    maps: dict[str, dict[str, str]] = {}
    ordered: dict[str, list[str]] = {}
    for axis, section in MENU_SECTION.items():
        values = [(it["value"] if isinstance(it, dict) else str(it)) for it in data[section]]
        maps[axis] = {norm(v): v for v in values}
        ordered[axis] = values
    return maps, ordered


def build_canon(
    aliases: list[dict[str, str]], menu: dict[str, dict[str, str]]
) -> Callable[[str, object], tuple[str | None, str, str]]:
    """Build a canonicaliser: raw label -> (menu value | None, verbatim raw)."""
    # Aliases are AXIS-TAGGED: a content_type typo must never relabel a discipline cell.
    # An entry without an "axis" key stays global for backwards compatibility.
    alias_map: dict[tuple[str, str], str] = {}
    global_alias: dict[str, str] = {}
    for entry in aliases or []:
        if not (isinstance(entry, dict) and entry.get("as_written") and entry.get("canonical")):
            continue
        key, target = norm(entry["as_written"]), norm(entry["canonical"])
        if entry.get("axis"):
            alias_map[(str(entry["axis"]), key)] = target
        else:
            global_alias[key] = target

    def canon(axis: str, raw: object) -> tuple[str | None, str, str]:
        """Canonicalise and REPORT THE MECHANISM.

        Returning the mechanism is what keeps a declared alias (a typo repair - an act of
        interpretation) distinguishable from pure orthographic normalisation (separator/case
        only, no interpretation). Conflating them made the first F-1 fix label 32 innocent
        "tool instruction" cells as "canonicalised via a declared alias".
        """
        text = strip_conf(str(raw or ""))
        if not text:
            return None, "", "empty"
        key = norm(text)
        table = menu[axis]
        if key in table:
            value = table[key]
            return value, text, ("verbatim" if text == value else "orthographic")
        for target in (alias_map.get((axis, key)), global_alias.get(key)):
            if target is not None and target in table:
                return table[target], text, "alias"
        return None, text, "offmenu"

    return canon


def read_csv_rows(path: Path, *, stats: dict[str, int] | None = None) -> list[dict[str, str]]:
    """Read a CSV into dicts, tolerating a leading '#' marker in the first header cell.

    Whitespace-only data lines (the unmapped tail of the ruler sheet) are skipped and
    counted in ``stats['blank_lines']`` so a silently dropped row can never go unnoticed.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        header = [h.lstrip("#").strip() or f"col{i}" for i, h in enumerate(header)]
        out: list[dict[str, str]] = []
        blank = 0
        for row in reader:
            if not any(c.strip() for c in row):
                blank += 1
                continue
            out.append({header[i]: (row[i] if i < len(row) else "") for i in range(len(header))})
        if stats is not None:
            stats["blank_lines"] = blank
        return out


def read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    """Read a JSONL artifact, unwrapping markdown code fences if present."""
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().strip("`").strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:  # C16: never swallow
            raise SystemExit(f"{path.name}: unparsable JSONL line: {exc}: {line[:120]}")
        iid = str(obj.get("item_id", "")).strip()
        if iid:
            out[iid] = obj
    return out


def safe_write(path: Path, text: str, *, force: bool) -> None:
    """Write atomically (tempfile -> fsync -> os.replace, C6); refuse silent overwrite."""
    if path.exists() and not force:
        raise SystemExit(f"refusing to overwrite existing file (use --force): {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _domains(menu_path: Path) -> frozenset[str]:
    """Normalised set of DOMAIN menu values (the fourth menu, not one of the axes).

    The owner sometimes files a domain where a discipline belongs. That is a deliberate
    vocabulary choice, not a typo and not noise, so it is preserved verbatim and flagged as
    OFF_MENU_DOMAIN rather than being "repaired" into a discipline nobody ruled for.
    """
    items = json.loads(menu_path.read_text(encoding="utf-8")).get("domains", [])
    return frozenset(norm(i["value"] if isinstance(i, dict) else str(i)) for i in items)


def nearest(axis: str, raw: str, table: dict[str, str], cutoff: float = 0.8) -> str | None:
    """Return the closest menu value to an off-menu label, for a human to confirm.

    This is a *proposal*: an off-menu owner value is always kept verbatim, because a
    near-match is not a ruling (R-D410 - never rewrite an owner's judgement).
    """
    import difflib

    hits = difflib.get_close_matches(norm(raw), list(table), n=1, cutoff=cutoff)
    return table[hits[0]] if hits else None


def agreement_class(human: str | None, picks: Iterable[str | None]) -> str:
    """Classify a row's three-way agreement on one axis (no imputation, no blanks)."""
    coder = [p for p in picks]
    if human is None:
        return "HUMAN_ABSTAIN"
    live = [p for p in coder if p is not None]
    if len(live) < len(coder):
        return "CODER_ABSTAIN"
    if all(p == human for p in live):
        return "UNANIMOUS"
    if len(set(live)) == 1:
        return "CONSENSUS_DIVERGENCE"
    if human in live:
        return "MODEL_SPLIT"
    return "THREE_WAY"


def main() -> int:
    """Run the consolidation in report (dry-run) or apply mode."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="dry-run: audit only, write nothing")
    ap.add_argument("--apply", action="store_true", help="write the consolidated anchor")
    ap.add_argument("--force", action="store_true", help="overwrite an existing export")
    ap.add_argument("--date", default=_date.today().strftime("%Y%m%d"),
                    help="output date stamp (YYYYMMDD, the governance convention)")
    args = ap.parse_args()
    if not (args.report or args.apply):
        args.report = True

    cfg = load_config()
    cons = cfg["consolidation"]
    menu, ordered = load_menu(PROJECT_ROOT / cons["menu"])
    canon = build_canon(cfg.get("declared_aliases", []), menu)
    coders = cfg["anchor_review"]["coders"]
    owner_col = {a: cons["owner_columns"][a] for a in AXES}
    domain_norm = _domains(PROJECT_ROOT / cons["menu"])

    review_path = PROJECT_ROOT / cons["review_sheet"]
    ruler_path = PROJECT_ROOT / cons["ruler_sheet"]
    n_anchor = int(cons["n_anchor_rows"])

    review = {r["item_id"]: r for r in read_csv_rows(review_path)}
    # regression guard (mirror of BUG-368): every owner_* column present in the sheet must
    # be consumed by a mapping, and every mapping must exist -- otherwise fail loudly (C16)
    if review:
        header = set(next(iter(review.values())).keys())
        declared = set(owner_col.values()) | {cons["keep_missing_column"], cons["notes_column"]}
        unmapped = {c for c in header if c.startswith("owner_")} - declared
        missing = declared - header
        if unmapped or missing:
            raise SystemExit(
                f"owner-column mapping broken: unmapped_in_sheet={sorted(unmapped)} "
                f"declared_but_absent={sorted(missing)} (a column nobody reads is indistinguishable "
                f"from free space -- BUG-368)"
            )
        for axis, col in owner_col.items():
            filled = sum(1 for r in review.values() if str(r.get(col, "")).strip())
            print(f"owner col    : {col:<12} axis={axis:<15} filled={filled}/{len(review)}")
    ruler_stats: dict[str, int] = {}
    ruler = read_csv_rows(ruler_path, stats=ruler_stats)
    coder_labels = {c["tag"]: read_jsonl(PROJECT_ROOT / c["path"]) for c in coders}

    print(f"config       : {CONFIG_PATH.relative_to(PROJECT_ROOT)}")
    print(f"review sheet : {review_path.name}  rows={len(review)}")
    print(f"ruler sheet  : {ruler_path.name}  rows={len(ruler)}  "
          f"blank_lines_skipped={ruler_stats.get('blank_lines', 0)}")
    for tag, labels in coder_labels.items():
        print(f"coder        : {tag:<8} rows={len(labels)}")
    print(f"menu         : " + ", ".join(f"{a}={len(ordered[a])}" for a in AXES))

    # --- anchor scope: the first n_anchor non-blank ruler rows, in sheet order
    anchor_ids = [r["item_id"] for r in ruler][:n_anchor]
    if len(anchor_ids) != n_anchor or len(set(anchor_ids)) != n_anchor:
        raise SystemExit(f"anchor scope violation: {len(anchor_ids)} ids / {len(set(anchor_ids))} unique")
    ruler_by_id = {r["item_id"]: r for r in ruler}

    rows: list[dict[str, str]] = []
    qc_counter: Counter[str] = Counter()
    tier_counter: dict[str, Counter[str]] = {a: Counter() for a in AXES}
    class_counter: dict[str, Counter[str]] = {a: Counter() for a in AXES}
    overrides: list[tuple[str, str, str, str]] = []
    unresolved: Counter[str] = Counter()
    unresolved_human: Counter[str] = Counter()
    offmenu_human: Counter[str] = Counter()
    off_review_unflagged: list[str] = []

    for iid in anchor_ids:
        src = {a: ruler_by_id[iid].get(cons["columns"][a], "") for a in AXES}
        rev = review.get(iid, {})
        if not rev:
            off_review_unflagged.append(iid)
        out: dict[str, str] = {"item_id": iid, "name": ruler_by_id[iid].get("name", "")}
        flags: list[str] = []

        for axis in AXES:
            human, human_raw, human_mech = canon(axis, src[axis])
            picks = {tag: canon(axis, labels.get(iid, {}).get(axis, ""))[0]
                     for tag, labels in coder_labels.items()}
            owner_raw = str(rev.get(owner_col[axis], "") or "").strip()
            owner, _, owner_mech = canon(axis, owner_raw)

            if human_raw and human is None:
                offmenu_human[human_raw] += 1
                flags.append(f"OFF_MENU_HUMAN:{axis}={human_raw}")
                unresolved_human[human_raw] += 1
            if owner_raw and owner is None:
                unresolved[owner_raw] += 1
                kind = "DOMAIN" if norm(owner_raw) in domain_norm else "OWNER"
                flags.append(f"OFF_MENU_{kind}:{axis}={owner_raw}")

            # F-1 fix: an alias note is a SUFFIX on the tier note, never a replacement for it.
            # The old chain let the tier branch overwrite the alias note (R030/R063 lost the
            # owner's verbatim spelling), and a prose note alone is not machine-checkable - so
            # the canonicalisation is also emitted as a qc_flag.
            alias_note = ""
            if owner_mech == "alias" and owner is not None:
                alias_note = (f"owner spelling {owner_raw!r} canonicalised via a declared alias to "
                              f"{owner!r} (C12)")
                flags.append(f"ALIAS_CANONICALISED:owner:{axis}")
            # NOTE (BUG-372): no "spelling differs from the ruler" flag is emitted on purpose.
            # A raw comparison fires on every legitimate OVERRIDE (50 rows) and a normalised one
            # fires on every separator/case variant (35 rows) - both expected. The two facts that
            # matter are already machine-readable: ALIAS_CANONICALISED:owner:<axis> (an
            # interpretation was applied) and the *_ruler_raw / owner_notes columns (verbatim).

            if owner_raw:
                if human is not None and owner is not None and owner == human:
                    tier, note = "owner-adjudicated", "owner reaffirms the ruler label"
                elif human is None:
                    tier, note = ("owner-supplied",
                                  "owner supplied the label; the ruler abstained on this axis")
                else:
                    tier, note = "owner-adjudicated", "owner overrules the ruler label"
                    if owner is not None:
                        overrides.append((iid, axis, human, owner))
                final = owner if owner is not None else owner_raw
                if owner is None:
                    near = nearest(axis, owner_raw, menu[axis])
                    note = "owner value is OFF-MENU; kept verbatim, NOT canonicalised"
                    if near:
                        note += f" (nearest menu value {near!r} - proposal only, not applied)"
                if alias_note:
                    note = f"{alias_note}; {note}"
            elif human is not None:
                tier, note = "human-ruled", "ruler label as written"
                final = human
                if human_mech == "alias":
                    note = f"ruler label canonicalised from {human_raw!r} via a declared alias"
                    flags.append(f"ALIAS_CANONICALISED:ruler:{axis}")
            else:
                tier, note = "declared-missing", "no human label; owner did not adjudicate"
                final = ""
                flags.append(f"MISSING:{axis}")

            tier_counter[axis][tier] += 1
            klass = agreement_class(human, picks.values())
            class_counter[axis][klass] += 1
            pair = " | ".join(f"{t}={v or '-'}" for t, v in picks.items())
            out[f"{axis}_final"] = final
            out[f"{axis}_ruler_raw"] = human_raw
            out[f"{axis}_human_present"] = "yes" if human else "no"
            out[f"{axis}_tier"] = tier
            out[f"{axis}_source_note"] = note
            out[f"{axis}_human"] = human or ""
            out[f"{axis}_coders"] = pair
            out[f"{axis}_class"] = klass

        notes = str(rev.get(cons["notes_column"], "") or "").strip()
        out["owner_notes"] = notes
        keep = str(rev.get(cons["keep_missing_column"], "") or "").strip().lower()
        if keep in ("yes", "y", "true", "1"):
            flags.append("OWNER_KEEPS_MISSING")
        out["owner_keep_missing"] = keep
        out["qc_flags"] = ";".join(flags)
        out["schema_version"] = str(cons["schema_version"])
        out["provenance_tier"] = str(cons["provenance_tier"])
        rows.append(out)
        qc_counter.update(flags)

    # --- integrity: anything absent from the review sheet must be unflagged
    for iid in off_review_unflagged:
        row = next(r for r in rows if r["item_id"] == iid)
        bad = [a for a in AXES if row[f"{a}_class"] in ("CONSENSUS_DIVERGENCE", "HUMAN_ABSTAIN")]
        if bad:
            raise SystemExit(
                f"review sheet is INCOMPLETE for {iid}: {bad} flagged but row absent (C16)"
            )

    print(f"\nanchor rows  : {len(rows)}  (not in review sheet: {len(off_review_unflagged)} -> "
          f"unflagged on every axis, verified)")
    for axis in AXES:
        t = tier_counter[axis]
        print(f"\n--- {axis} ---")
        for k, v in t.most_common():
            print(f"    tier  {k:<20} {v}")
        for k, v in class_counter[axis].most_common():
            print(f"    class {k:<20} {v}")

    print(f"\nowner overrides (ruler label replaced): {len(overrides)}")
    for iid, axis, human, owner in overrides:
        print(f"    {iid}  {axis:<14} {human!r} -> {owner!r}")
    if unresolved:
        print("\nOFF-MENU owner values (kept verbatim, need a taxonomy decision):")
        for value, count in unresolved.most_common():
            print(f"    {value!r} x{count}")
    if unresolved_human:
        print("\nOFF-MENU HUMAN (ruler) values -- the anchor vocabulary itself is violated:")
        for value, count in unresolved_human.most_common():
            print(f"    {value!r} x{count}")
    print(f"\nQC flags: {dict(qc_counter)}")
    if unresolved:
        print(f"\n\u26a0 {sum(unresolved.values())} OFF-MENU owner cell(s) preserved verbatim "
              f"({len(unresolved)} distinct) - taxonomy decision pending, nothing guessed.")

    if args.report:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return 0

    import hashlib

    input_hashes = {
        "ruler_sheet": ruler_path,
        "review_sheet": review_path,
        "ruling_map": PROJECT_ROOT / cons["ruling_map"],
        "menu": PROJECT_ROOT / cons["menu"],
    }
    for coder in coders:
        input_hashes[f"coder:{coder['tag']}"] = PROJECT_ROOT / coder["path"]

    cols: list[str] = ["item_id", "name"]
    for axis in AXES:
        cols += [f"{axis}_final", f"{axis}_ruler_raw", f"{axis}_human_present", f"{axis}_tier",
                 f"{axis}_source_note", f"{axis}_human", f"{axis}_coders", f"{axis}_class"]
    cols += ["owner_keep_missing", "owner_notes", "qc_flags",
             "schema_version", "provenance_tier"]

    buf = [",".join(cols)]
    for row in rows:
        buf.append(",".join(_quote(row.get(c, "")) for c in cols))
    out_csv = PROJECT_ROOT / cons["out_csv"].format(date=args.date)
    safe_write(out_csv, "\n".join(buf) + "\n", force=args.force)
    print(f"\n✅ wrote {out_csv.relative_to(PROJECT_ROOT)}  rows={len(rows)} cols={len(cols)}")

    md = render_md(cons, rows, cols, args.date, tier_counter, class_counter, overrides,
                   unresolved, unresolved_human, qc_counter, input_hashes, len(off_review_unflagged))
    out_md = PROJECT_ROOT / cons["out_md"].format(date=args.date)
    safe_write(out_md, md, force=args.force)
    print(f"✅ wrote {out_md.relative_to(PROJECT_ROOT)}  chars={len(md)}")
    return 0


def render_md(
    cons: dict[str, Any],
    rows: list[dict[str, str]],
    cols: list[str],
    stamp: str,
    tier_counter: dict[str, Counter[str]],
    class_counter: dict[str, Counter[str]],
    overrides: list[tuple[str, str, str, str]],
    unresolved: Counter[str],
    unresolved_human: Counter[str],
    qc_counter: Counter[str],
    input_hashes: dict[str, Path],
    off_review: int,
) -> str:
    """Render the human-readable companion for the consolidated anchor."""
    import hashlib

    L: list[str] = []
    add = L.append
    add(f"# Consolidated F-11 anchor - {len(rows)} rows (owner judgement of {stamp})")
    add("")
    add("**Provenance tier:** `" + cons["provenance_tier"] + "` - the label set is *human-mixed*")
    add("(the ruler's own labels plus the owner's adjudication) and *coder-attested* only as")
    add("context. It does not become independent human truth, and it **cannot unfreeze F-11,")
    add("D-300 adoption, or the floors in `config/eval_integrity.yaml`.**")
    add("")
    add(f"Schema version `{cons['schema_version']}` - generated by `scripts/consolidate_anchor_ruler.py`")
    add("(deterministic, no LLM involved) - append-only: the ruler sheet is never modified.")
    add("")
    add("## Inputs (sha256, R14)")
    add("")
    add("| input | sha256 |")
    add("|---|---|")
    for label, path in input_hashes.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "MISSING"
        add(f"| `{path.relative_to(PROJECT_ROOT)}` | `{digest[:32]}...` |")
    add("")
    add("## How to read a row")
    add("")
    add("| tier | meaning |")
    add("|---|---|")
    add("| `human-ruled` | the ruler label stands as written; the owner left the cell empty |")
    add("| `owner-adjudicated` | the owner reaffirmed or overruled a label the ruler had written |")
    add("| `owner-supplied` | the ruler abstained and the owner supplied the label (no human reference) |")
    add("| `declared-missing` | nobody has a label; deliberately NOT imputed (BUG-363) |")
    add("")
    add("`<axis>_ruler_raw` keeps the ruler's verbatim cell, so a canonicalisation is always")
    add("recoverable. `<axis>_class` records the pre-adjudication agreement state.")
    add("")
    add("## Per-axis outcome")
    add("")
    for axis in AXES:
        add(f"### {axis}")
        add("")
        add("| tier | n |")
        add("|---|---|")
        for k, v in tier_counter[axis].most_common():
            add(f"| `{k}` | {v} |")
        add("")
        add("| agreement class (pre-adjudication) | n |")
        add("|---|---|")
        for k, v in class_counter[axis].most_common():
            add(f"| `{k}` | {v} |")
        add("")
    add("## Owner overrules (ruler label replaced)")
    add("")
    add(f"{len(overrides)} cells. The ruler label remains visible in `<axis>_human`.")
    add("")
    add("| item | axis | ruler | owner |")
    add("|---|---|---|---|")
    for iid, axis, human, owner in overrides:
        add(f"| {iid} | {axis} | {human} | {owner} |")
    add("")
    add("## FORM was deliberately not adjudicated")
    add("")
    skipped = cons["skipped_axes"]["extraction_type"]
    add(f"Owner statement ({skipped['date']}): {skipped['reason']}")
    add("")
    add("Consequence: FORM is 100% human-ruled - no coder suggestion was ever put in front of")
    add("the owner, and the 5 rows where the ruler abstained stay `declared-missing` rather than")
    add("inheriting a model consensus.")
    add("")
    if unresolved or unresolved_human:
        add("## Open taxonomy items (nothing was guessed)")
        add("")
        for value, count in unresolved.most_common():
            add(f"- OFF-MENU owner value `{value}` x{count} - kept verbatim; the nearest menu")
            add("  candidate is recorded in that row's `discipline_source_note` for a one-line ruling")
        for value, count in unresolved_human.most_common():
            add(f"- OFF-MENU ruler value `{value}` x{count} - written as-is")
        add("")
    add("## QC flags")
    add("")
    add("| flag | n |")
    add("|---|---|")
    for k, v in qc_counter.most_common():
        add(f"| `{k}` | {v} |")
    add("")
    add(f"{off_review} rows were never flagged by the review sheet (unanimous or model-split with")
    add("a present human label); the harness re-verified them row by row and fails loudly if a")
    add("flagged row is missing from the sheet (C16).")
    add("")
    add("## Columns")
    add("")
    add("```")
    for i, c in enumerate(cols):
        add(f"{i + 1:>3}  {c}")
    add("```")
    add("")
    return "\n".join(L) + "\n"


def _quote(value: object) -> str:
    """CSV-escape a single cell (quote when it contains a delimiter, quote or newline)."""
    text = "" if value is None else str(value)
    if any(ch in text for ch in ',"\n\r'):
        return '"' + text.replace('"', '""') + '"'
    return text


if __name__ == "__main__":
    sys.exit(main())
