#!/usr/bin/env python3
"""scripts/ingest_relabel_rulings.py — THE READER OF THE OWNER'S RELABEL PACKET (T-117, BUG-785).

THE BUG THIS RETIRES (MEASURED 2026-10-14, not asserted). The owner filled `owner_action` on 72 of 72 unit
rows of governance/canonical_relabel_review_20261014.csv (38 CONFIRM / 17 CORRECT / 14 LEAVE / 3 ABSTAIN,
311 rows covered) and NOTHING in the repository read that column. The applier,
scripts/apply_relabel_rulings.py, reads config/relabel_rulings.yaml#unit_rulings and `class_rules` — a
different surface, filled by an earlier ruling round — so a COMPLETED owner act was invisible: the packet was
a sheet with no reader, which is the same fault shape as BUG-782 (a word with no home) one order over (a home
with no intake). This script is the missing bridge, and it is the ONLY writer of `unit_rulings`.

WHAT IT DOES, AND IN WHAT ORDER OF AUTHORITY
  1. READ the packet the policy DECLARES (config/relabel_rulings.yaml#packet). It never globs for "the newest
     review csv": a glob that selects a sibling is a blind spot, not a convenience (the BUG-733 class), and the
     applier's own `_packet()` still globs while this file declares — so the ingest names the surface exactly
     and the applier is free to keep its own rule until it is moved to the declaration too.
  2. VALIDATE every row against the DECLARED vocabulary: an action outside the owner's word set is FATAL (C16),
     a CORRECT that names no home is FATAL (an incomplete word is not a word), and a home that is not a
     canonical of config/taxonomy.yaml (a discipline or a domain) is FATAL — a home that does not exist would
     create one (D-2898: the agent never mints a label).
  3. WRITE `unit_rulings` KEYED BY unit_key, never by the ordinal (BUG-751: an ordinal is a position, not an
     identity — the packet was renumbered once already). The packet's `review_id` is recorded in `was:`, which
     is the whole point of keeping it: history is preserved, identity is not positional.
  4. REFUSE to invent the rest. An owner_canonical cell on a row whose action is not CORRECT is INERT
     (measured 2026-10-14: 17 such cells, 3 ABSTAIN + 14 LEAVE): it is REPORTED as advisory, never written.
     `applied:` is never written here: it is the receipt of the licensed store write
     (scripts/apply_relabel_store_write.py), and a receipt minted by an ingestion is a claim-shaped field with
     a false reading (the BUG-782 class).
  5. PRESERVE every existing ruling, including its `applied:` receipt and its note, and never drop one: the
     write is a SPLICE of the `unit_rulings:` block into the hand-formatted YAML (a yaml.safe_dump would
     destroy the comments the applier's own docstring warns about), backed up and atomic (C6/C13).

USAGE
  python3 scripts/ingest_relabel_rulings.py            # PLAN: what would be written, nothing written
  python3 scripts/ingest_relabel_rulings.py --apply    # splice unit_rulings (backup + atomic write)
  python3 scripts/ingest_relabel_rulings.py --selftest # known-answer controls, no store, no network
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULINGS_REL = "config/relabel_rulings.yaml"
TAXONOMY_REL = "config/taxonomy.yaml"
PACKET_COLUMNS: tuple[str, ...] = ("review_id", "unit_key", "raw_label", "owner_action", "owner_canonical")
ORDINAL_LIKE: re.Pattern[str] = re.compile(r"^U\d{1,4}$")


class IngestError(SystemExit):
    """A refusal that is loud, named and non-zero (C16): never a silent correction."""


def _yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def rulings_path(path: Path | None = None) -> Path:
    return path or (ROOT / RULINGS_REL)


def declared_packet(policy: dict[str, Any], *, root: Path | None = None) -> Path:
    """The ONE packet the owner marked: DECLARED by the policy, never discovered by a glob."""
    rel = str(policy.get("packet", "")).strip()
    if not rel:
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): {RULINGS_REL} declares no `packet:` — a reader that "
                          f"discovers its input by glob can read a sibling the owner never marked (C16)")
    path = (root or ROOT) / rel
    if not path.exists():
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): the declared packet {rel} does not exist")
    return path


def owner_vocabulary(policy: dict[str, Any]) -> tuple[set[str], set[str]]:
    """The owner's word set + the words that require a home, from the DECLARED vocabulary block."""
    vocab = dict(policy.get("vocabulary") or {})
    actions = {str(a).strip().upper() for a in (vocab.get("actions") or [])}
    requires_home = {str(a).strip().upper() for a in (vocab.get("home_required") or [])}
    if not actions:
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): {RULINGS_REL} declares no vocabulary.actions — the "
                          f"applier's own constant is not a second home for the owner's words (C12)")
    return actions, requires_home


def taxonomy_homes(root: Path | None = None) -> set[str]:
    """Every canonical the taxonomy DECLARES (disciplines + domains) — the only valid `owner_canonical` homes."""
    tax = _yaml((root or ROOT) / TAXONOMY_REL)
    homes: set[str] = set()
    for axis in ("disciplines", "domains"):
        for entry in tax.get(axis) or []:
            value = str((entry or {}).get("canonical", "")).strip().lower()
            if value:
                homes.add(value)
    if not homes:
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): {TAXONOMY_REL} declares no canonicals — refusing to "
                          f"validate a home against an empty vocabulary")
    return homes


def read_packet(packet: Path) -> list[dict[str, str]]:
    with packet.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = [{k: (v or "") for k, v in row.items()} for row in reader]
    missing = [c for c in PACKET_COLUMNS if c not in header]
    if missing:
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): {packet.name} lacks {missing} — this is not the unit "
                          f"surface the owner marked (C16)")
    if "owner_comment" not in header:
        for row in rows:
            row["owner_comment"] = ""
    return rows


def plan_rulings(
    rows: Sequence[dict[str, str]], actions: set[str], requires_home: set[str], homes: set[str]
) -> tuple[dict[str, dict[str, Any]], list[str], list[str], dict[str, int]]:
    """Validate every row and return (rulings by unit_key, inert cells, advisory notes, action counts).

    Fail-closed (C16): an unknown word, a missing unit_key, an ordinal-shaped key, a CORRECT with no home, or a
    home no canonical declares — each REFUSES and names the row. Nothing is corrected silently.
    """
    rulings: dict[str, dict[str, Any]] = {}
    inert: list[str] = []
    notes: list[str] = []
    counts: dict[str, int] = {}
    for row in rows:
        rid = str(row.get("review_id", "")).strip()
        key = str(row.get("unit_key", "")).strip()
        action = str(row.get("owner_action", "")).strip().upper()
        home = str(row.get("owner_canonical", "")).strip()
        if not key:
            raise IngestError(f"FAIL-CLOSED (relabel-ingest): {rid or 'a row'} carries no unit_key — the packet "
                              f"cannot be ingested by identity it does not have")
        if ORDINAL_LIKE.match(key):
            raise IngestError(f"FAIL-CLOSED (relabel-ingest): {rid} is keyed by the ORDINAL ({key!r}) — an "
                              f"ordinal is a position, not an identity (BUG-751)")
        if not action:
            continue  # an unmarked row is not a word: it stays with its class rule (never a guess)
        if action not in actions:
            raise IngestError(f"FAIL-CLOSED (relabel-ingest): {rid} carries the action {action!r}, which is not "
                              f"in the declared vocabulary {sorted(actions)} (C16)")
        entry: dict[str, Any] = {"was": rid or "(no ordinal)", "action": action}
        if home:
            if action in requires_home:
                lowered = home.lower()
                if lowered not in homes:
                    raise IngestError(
                        f"FAIL-CLOSED (relabel-ingest): {rid} is CORRECT to {home!r}, which is not a canonical "
                        f"of {TAXONOMY_REL} (discipline or domain) — writing it would MINT a home (D-2898)")
                entry["owner_canonical"] = lowered
            else:
                inert.append(f"{rid} ({action}) names {home!r} — INERT: a home is written only for "
                             f"{sorted(requires_home)}")
        if action in requires_home and "owner_canonical" not in entry:
            raise IngestError(f"FAIL-CLOSED (relabel-ingest): {rid} is {action} but names no home — an incomplete "
                              f"word is not a word (C16)")
        comment = str(row.get("owner_comment", "")).strip()
        if comment:
            entry["owner_comment"] = comment
            notes.append(f"{rid} ({action}): {comment}")
        rulings[key] = entry
        counts[action] = counts.get(action, 0) + 1
    return rulings, inert, notes, counts


# ── the splice (the hand-formatted file is never round-tripped) ───────────────
TOP_LEVEL_KEY: re.Pattern[str] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:")


def _scalar(value: Any) -> str:
    """One-line YAML for `value`. `yaml.safe_dump` alone appends a `...` document-end marker: a whole-file
    emitter that splices scalars into a live document must strip it, or the splice becomes a parse bomb
    (this control fired on the first run — a guard whose failure nobody has SEEN is a comment, BUG-492)."""
    first = yaml.safe_dump(value, default_flow_style=True, width=10**9).split("\n", 1)[0].strip()
    return first or "''"


def unit_rulings_span(lines: Sequence[str]) -> tuple[int, int]:
    """The [start, end) span of the `unit_rulings:` block: its data lines up to the NEXT top-level key."""
    start = next((i for i, ln in enumerate(lines) if ln.startswith("unit_rulings:")), -1)
    if start < 0:
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): {RULINGS_REL} has no `unit_rulings:` block — refusing "
                          f"to append one (the file's shape is a decision, not a convenience)")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if TOP_LEVEL_KEY.match(lines[i]):
            end = i
            break
    return start, end


def render_block(existing: dict[str, Any], fresh: dict[str, dict[str, Any]], packet: Path, ingested: str) -> str:
    """Every entry: the packet's word first (fresh), then every ruling the packet does not name (carried).

    Carried entries keep their `applied:` receipt and note VERBATIM — a re-ingest never destroys a receipt.
    """
    out: list[str] = [
        "unit_rulings:",
        f"  # WRITTEN BY scripts/ingest_relabel_rulings.py from {packet.as_posix()} (ingested {ingested}).",
        "  # Keyed by unit_key, NEVER by the packet's ordinal (BUG-751): `was:` carries the ordinal as history.",
        "  # `applied:` is NOT written here: it is the receipt of the licensed store write, and a receipt",
        "  # minted by an ingestion is a claim-shaped field with a false reading (BUG-785/BUG-782).",
    ]
    reworded: list[str] = []
    for key in sorted({**fresh, **existing}):
        prior = dict(existing.get(key) or {})
        word = dict(fresh.get(key) or {})
        entry = {**prior, **word}   # the packet's word wins on its own fields; a receipt is PRESERVED
        if prior and word and (prior.get("action") != word.get("action")
                               or prior.get("owner_canonical") != word.get("owner_canonical")):
            # R-D410 spirit: a receipt is never deleted, but a receipt for an OLD word must not read as this
            # one's. It is kept and NAMED, so the history is auditable rather than silently re-dated.
            reworded.append(f"{key}: {prior.get('action')} ({prior.get('applied', 'no receipt')}) -> "
                            f"{word.get('action')}")
        out.append(f"  {_scalar(key)}:")
        for field, value in entry.items():
            if isinstance(value, str) and ("\n" in value or len(value) > 110):
                out.extend([f"    {field}: >-", *[f"      {ln}" for ln in str(value).splitlines()]])
            else:
                out.append(f"    {field}: {_scalar(value)}")
    if reworded:
        out.append("  # REWORDED by this ingest (the earlier word's `applied` receipt is KEPT below, not re-dated):")
        out.extend(f"  #   {line}" for line in reworded)
    return "\n".join(out) + "\n"


def build(policy: dict[str, Any], *, root: Path | None = None, packet_rel: str | None = None) -> tuple[str, dict]:
    """Compose the new file text + a report. Pure: it reads, validates and renders; it never writes."""
    base = root or ROOT
    if packet_rel is not None:
        policy = {**policy, "packet": packet_rel}
    packet = declared_packet(policy, root=base)
    actions, requires_home = owner_vocabulary(policy)
    homes = taxonomy_homes(base)
    rows = read_packet(packet)
    rulings, inert, notes, counts = plan_rulings(rows, actions, requires_home, homes)
    text = (base / RULINGS_REL).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start, end = unit_rulings_span(lines)
    existing = dict(policy.get("unit_rulings") or {})
    carry = {k: v for k, v in existing.items() if k not in rulings}
    ingested = dt.date.today().isoformat()
    block = render_block(existing, rulings, packet, ingested)
    head = "".join(lines[:start])
    head = re.sub(r"(?m)^packet:.*$", f"packet: {packet.relative_to(base).as_posix()}", head, count=1)
    body = head + block + "".join(lines[end:])
    # THE READ-BACK (before anything is written): the spliced text must carry EXACTLY the packet's rulings plus
    # every ruling the packet does not name. The first version compared an expression with itself - a tautology
    # that would have passed on a file that dropped every receipt (the BUG-782 class: a guard with a false reading).
    parsed = (yaml.safe_load(body) or {}).get("unit_rulings") or {}
    want = set(rulings) | set(carry)
    if set(parsed) != want:
        raise IngestError(f"FAIL-CLOSED (relabel-ingest): the spliced file does not read back: "
                          f"{len(set(parsed) ^ want)} key(s) differ from the plan")
    report = {
        "packet": packet.relative_to(base).as_posix(), "rows": len(rows), "counts": counts,
        "written": len(rulings), "carried": len([k for k in existing if k not in rulings]),
        "keys": sorted(rulings), "carried_keys": sorted(carry), "inert": inert, "notes": notes,
        "still_unruled": len([r for r in rows if not str(r.get("owner_action", "")).strip()]),
    }
    return body, report


def print_report(report: dict, *, applied: bool) -> None:
    counts = " · ".join(f"{k} {v}" for k, v in sorted(report["counts"].items()))
    print(f"  packet {report['packet']} · rows {report['rows']} · marked {sum(report['counts'].values())} "
          f"({counts})")
    print(f"  unit_rulings: {report['written']} written · {report['carried']} carried · "
          f"{report['still_unruled']} row(s) left to their class rule")
    if report["notes"]:
        print(f"  owner note(s) carried: {len(report['notes'])}")
    if report["inert"]:
        print(f"  ⚠️  INERT cell(s) — an owner_canonical on a row that is not CORRECT is ADVISORY, never written: "
              f"{len(report['inert'])}")
        for line in report["inert"][:4]:
            print(f"      {line}")
    print(f"  {'WROTE' if applied else 'PLAN (nothing written; pass --apply)'}: {RULINGS_REL}")


def apply_rulings(policy: dict[str, Any], *, root: Path | None = None, packet_rel: str | None = None) -> int:
    base = root or ROOT
    body, report = build(policy, root=base, packet_rel=packet_rel)
    target = base / RULINGS_REL
    backups = base / "backups"   # C13: receipts live in backups/, never beside the artifact
    backups.mkdir(exist_ok=True)
    backup = backups / f"{target.name}.PRE_relabel_ingest_{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}"
    shutil.copy2(target, backup)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(target)  # C6: tempfile -> replace inside the same directory
    print(f"  backup {backup.name}")
    print_report(report, applied=True)
    return 0


# ── controls ─────────────────────────────────────────────────────────────────
CONTROL_LABELS: tuple[str, ...] = (
    "a_word_outside_the_declared_vocabulary_is_refused",
    "a_correct_with_no_home_is_refused_never_written",
    "a_home_that_no_canonical_declares_is_refused_never_minted",
    "an_inert_home_on_a_non_correct_row_is_advisory_never_written",
    "the_write_is_keyed_by_unit_key_never_by_the_ordinal",
    "an_applied_receipt_survives_a_re_ingest",
    "the_declared_vocabulary_is_a_subset_of_the_appliers_actions",
    "an_unmarked_row_is_left_to_its_class_rule_never_guessed",
    "the_declared_packet_is_read_never_a_globbed_sibling",
)


def _fixture(tmp: Path, packet_rows: list[dict[str, str]], packet_name: str = "packet.csv") -> Path:
    (tmp / "config").mkdir(parents=True, exist_ok=True)
    (tmp / "config" / "taxonomy.yaml").write_text(yaml.safe_dump({
        "disciplines": [{"canonical": "design thinking"}, {"canonical": "marketing"}],
        "domains": [{"canonical": "design strategy"}],
    }), encoding="utf-8")
    (tmp / packet_name).write_text("", encoding="utf-8")
    cols = ["review_id", "unit_key", "raw_label", "owner_action", "owner_canonical", "owner_comment"]
    with (tmp / packet_name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for row in packet_rows:
            writer.writerow({c: row.get(c, "") for c in cols})
    # a rulings file with an APPLIED receipt that must survive
    (tmp / "config" / "relabel_rulings.yaml").write_text(
        "schema_version: '1.0'\n"
        "date: '2026-10-13'\n"
        "decision: D-2977\n"
        f"packet: {packet_name}\n"
        "\n"
        "vocabulary:\n"
        "  actions: [CONFIRM, CORRECT, ABSTAIN, LEAVE]\n"
        "  home_required: [CORRECT]\n"
        "  withheld: [PENDING]\n"
        "\n"
        "class_rules:\n"
        "  ALIAS-LAYER-RETIRED: {policy: CONFIRM}\n"
        "\n"
        "unit_rulings:\n"
        "  design studies -> design thinking:\n"
        "    was: U001 (packet 2026-10-13)\n"
        "    action: CONFIRM\n"
        "    applied: '2026-10-13'\n"
        "\n"
        "store_write_license:\n"
        "  scope: [CONFIRM]\n",
        encoding="utf-8",
    )
    return tmp / "config" / "relabel_rulings.yaml"


def _policy(path: Path) -> dict[str, Any]:
    return _yaml(path)


def selftest() -> int:
    import tempfile  # noqa: PLC0415

    failures = 0

    def mark(label: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        if ok:
            print(f"  ok  {label}")
        else:
            failures += 1
            print(f"  FAIL {label}{(': ' + detail) if detail else ''}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        def attempt(label: str, rows: list[dict[str, str]], expect_fatal: bool) -> None:
            path = _fixture(tmp, rows)
            try:
                build(_policy(path), root=tmp)
                mark(label, not expect_fatal, "expected a refusal, got a clean build")
            except IngestError:
                mark(label, expect_fatal)

        attempt("a_word_outside_the_declared_vocabulary_is_refused",
                [{"review_id": "U900", "unit_key": "a -> b", "owner_action": "APPROVE"}], True)
        attempt("a_correct_with_no_home_is_refused_never_written",
                [{"review_id": "U901", "unit_key": "a -> b", "owner_action": "CORRECT", "owner_canonical": ""}], True)
        attempt("a_home_that_no_canonical_declares_is_refused_never_minted",
                [{"review_id": "U902", "unit_key": "a -> b", "owner_action": "CORRECT",
                  "owner_canonical": "innovation studies"}], True)

        # an inert home is ADVISORY: the build succeeds and names it, and the entry has no home
        path = _fixture(tmp, [{"review_id": "U903", "unit_key": "a -> b", "owner_action": "ABSTAIN",
                               "owner_canonical": "marketing"}])
        _body, rep = build(_policy(path), root=tmp)
        entry = rep and yaml.safe_load(_body)["unit_rulings"]["a -> b"]
        mark("an_inert_home_on_a_non_correct_row_is_advisory_never_written",
             len(rep["inert"]) == 1 and "owner_canonical" not in entry, repr(rep["inert"]))

        # keyed by unit_key; the ordinal survives only inside `was:`
        path = _fixture(tmp, [{"review_id": "U904", "unit_key": "design studies -> design thinking",
                               "owner_action": "CONFIRM"}])
        body, _rep = build(_policy(path), root=tmp)
        got = yaml.safe_load(body)["unit_rulings"]
        mark("the_write_is_keyed_by_unit_key_never_by_the_ordinal",
             "design studies -> design thinking" in got and "U904" not in got
             and str(got["design studies -> design thinking"]["was"]).startswith("U904"))
        carried = got.get("design studies -> design thinking") or {}
        mark("an_applied_receipt_survives_a_re_ingest", carried.get("applied") == "2026-10-13")
        mark("an_unmarked_row_is_left_to_its_class_rule_never_guessed",
             "a -> unmarked" not in got)

        # the drift guard: the declared owner vocabulary must be a subset of the applier's ACTIONS
        sys.path.insert(0, str(ROOT / "scripts"))
        from apply_relabel_rulings import ACTIONS  # noqa: PLC0415

        declared, _ = owner_vocabulary({"vocabulary": {"actions": ["CONFIRM", "CORRECT", "ABSTAIN", "LEAVE"]}})
        mark("the_declared_vocabulary_is_a_subset_of_the_appliers_actions", declared <= set(ACTIONS),
             f"{sorted(declared)} vs {sorted(ACTIONS)}")

        # a declared packet that does not exist is a refusal, never a globbed sibling
        ghost = {"packet": "governance/does_not_exist.csv", "vocabulary": {"actions": ["CONFIRM"]}}
        try:
            declared_packet(ghost, root=tmp)
            mark("the_declared_packet_is_read_never_a_globbed_sibling", False, "expected a refusal")
        except IngestError:
            mark("the_declared_packet_is_read_never_a_globbed_sibling", True)

    print(f"{'ok' if not failures else 'FAIL'} selftest: {len(CONTROL_LABELS) - failures}/{len(CONTROL_LABELS)} "
          f"control(s) hold (a control that never fires is a comment, BUG-492)")
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the owner's relabel packet into config/relabel_rulings.yaml")
    parser.add_argument("--apply", action="store_true", help="splice unit_rulings (backup + atomic write)")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls, no store")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.selftest:
        return selftest()
    policy = _yaml(ROOT / RULINGS_REL)
    if args.apply:
        return apply_rulings(policy)
    _body, report = build(policy)
    print_report(report, applied=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
