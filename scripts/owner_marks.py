#!/usr/bin/env python3
"""scripts/owner_marks.py — THE OWNER'S WORD: render, check, apply (T-129/T-130, BUG-782).

THE PROBLEM THIS RETIRES (measured 2026-10-14, not asserted). Every MUST task in the owner lane carried its owed
act as PROSE in config/task_register.yaml#gate — "one owner word per pair", "one word per unit" — so the words had
no home, no vocabulary, no validator and no coverage reading. The one artifact that LOOKED like an answer,
governance/work_identity_collapse_review_20261014.csv, carried a machine screen (68 yes / 16 no) in a column NAMED
`owner_ruling`, written by NO script in this repo; and its `identical_text` column said 42 while the rail and the
census both measured 37 (BUG-782). A lane whose only machine-readable "ruling" is minted by nobody, and whose
deterministic tier is off by five, is a lane an agent can read as RELEASED without the owner having spoken.

THE FIX IS NOT A BETTER SHEET. It is the missing INTAKE, in the same shape as the ingest door (D-2997): the word
gets ONE home of its vocabulary (config/owner_marks.yaml), the sheet is RENDERED from the instrument that measures
it (scripts/check_corroboration_collapse.py --voice --pairs-out) instead of hand-built, and the act is read as a
rail so a road that stops in prose stops in the ladder instead.

WHAT EACH MODE DOES
  --render   rebuild the sheet from the pair OBJECT + the store, with per-row proposals and provenance; build the
             ledger PROJECTION (the ledger stays the one home of its verdicts). Carries every owner word and note
             already on disk, and FAILS CLOSED rather than drop one (an uncarried word is an un-ruling).
  --check    read both homes, validate the vocabulary, DERIVE the effective word per row (override > signature >
             none), test the conflict rule, and bind the sheet to the census. rc 0 released | 2 owed (loud, NOT
             fatal: BUG-457) | 1 error. This is the ONE reading the ladder needs.
  --apply    expand the signed tiers over their DECLARED predicates and write the result with its provenance into
             `derived_column` / the ledger's `verdict`. Backs up, writes atomically (C6), deletes nothing (R-D410).
  --sign     THE OWNER'S ACT: stamp `signed: <date>` on the NAMED tiers. It is the ONLY writer of that field.
             It never chooses a tier (the ids are the owner's word), it refuses an unknown id and a tier whose word
             is null (there is nothing to sign), it refuses to overwrite an existing signature silently, and it
             re-parses the file and reads back the date it just wrote before it returns - a signature that did not
             land is not an act (D-2676).
  --selftest known-answer controls over the pure parts: no store, no network, no LLM (BUG-492).

WHAT IT REFUSES TO DO (stated, because an unstated scope reads as coverage)
  - It never chooses a word. `signed:` in the policy is the only owner act the file accepts; a proposal is not a
    word and the derivation ignores it (D-2898).
  - It never guesses a tier: without the pair object it REFUSES to render, because the object is what makes the
    deterministic class deterministic (the v1 sheet guessed and drifted by five).
  - It never touches a home it does not declare (T-101/T-117/T-121/T-124 live in their own homes, listed in the
    policy as `other_owner_lanes` so the act is one page without one script pretending to apply them).
  - It never writes a ledger verdict that changes identity: the ledger's own policy keeps MERGE post-run; --apply
    records the WORD, and the identity repair stays T-129's separately-gated pipeline act.

USAGE
  python3 scripts/owner_marks.py --sign A B C L-A L-B   # THE OWNER'S WORD (the only writer of `signed:`)
  python3 scripts/owner_marks.py --render            # sheet + ledger projection
  python3 scripts/owner_marks.py --check             # rc 0 released | 2 owed | 1 error
  python3 scripts/owner_marks.py --apply             # expand signatures, write derived words + receipt
  python3 scripts/owner_marks.py --selftest          # known-answer controls, no store
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from collections.abc import Sequence
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIG_REL = "config/owner_marks.yaml"
BACKUP_DIR_REL = "backups"
RECEIPT_REL = "governance/owner_marks_receipt.json"
CSV_LINETERMINATOR = "\n"


class OwnerMarksError(RuntimeError):
    """A fault that must stop the run: the lane fails closed, it never guesses (C16)."""


# ── policy ───────────────────────────────────────────────────────────────────

def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Read the ONE home of the owner-word contract (vocabulary, homes, tiers, derivation, coverage)."""
    target = path or (ROOT / CONFIG_REL)
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "homes" not in data or "vocabularies" not in data:
        raise OwnerMarksError(f"{target} is not an owner-marks policy (C12: the contract has ONE home)")
    return data


def resolve(policy: dict[str, Any], rel: str) -> Path:
    """Resolve a repo-relative path declared in the policy (no path is ever typed inside this module)."""
    return ROOT / rel


def home(policy: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one declared home by name; an undeclared home is a FATAL typo, never a silent empty."""
    try:
        return dict(policy["homes"][name])
    except KeyError as exc:
        raise OwnerMarksError(f"home {name!r} is not declared in {CONFIG_REL}") from exc


def vocabulary(policy: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one declared vocabulary by name (words + the withheld word)."""
    try:
        return dict(policy["vocabularies"][name])
    except KeyError as exc:
        raise OwnerMarksError(f"vocabulary {name!r} is not declared in {CONFIG_REL}") from exc


def tiers_for(policy: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """The tiers of one home, in DECLARATION ORDER (order is precedence: the strongest evidence first)."""
    return [dict(t) for t in policy.get("tiers", []) if str(t.get("home")) == name]


# ── predicates (declared, never eval) ────────────────────────────────────────

def predicate_matches(expr: str, row: dict[str, str]) -> bool:
    """Evaluate a DECLARED tier predicate over a row's own columns.

    The grammar is deliberately tiny — `field == "value"`, `field in ("a", "b")`, clauses joined by ` and ` —
    and any clause the matcher does not understand RAISES. A silently-false predicate would leave a lane owed
    for ever with a green rail, which is the failure mode this whole file exists to retire.
    """
    for clause in str(expr).split(" and "):
        clause = clause.strip()
        if not clause:
            raise OwnerMarksError(f"empty predicate clause in {expr!r}")
        if " in (" in clause:
            field, rest = clause.split(" in (", 1)
            values = [v.strip().strip('"').strip("'") for v in rest.rstrip(")").split(",")]
            if row.get(field.strip(), "") not in values:
                return False
        elif " == " in clause:
            field, value = clause.split(" == ", 1)
            if row.get(field.strip(), "") != value.strip().strip('"').strip("'"):
                return False
        else:
            raise OwnerMarksError(f"predicate clause not understood: {clause!r} (the matcher is not eval)")
    return True


# ── the measurement object (the rail's own output) ───────────────────────────

def measurement(policy: dict[str, Any]) -> dict[str, Any]:
    """The declared parameters + the published census counts, from the rule file that measures them."""
    rule = yaml.safe_load(
        resolve(policy, str(policy["sources"]["pair_object_parameters_home"])).read_text(encoding="utf-8"))
    limb = dict(rule["lexical_limb"])
    return {
        "collapse_at_or_above": float(limb["collapse_at_or_above"]),
        "min_words_per_side": int(limb["min_words_per_side"]),
        "certain_class": str(limb["certain_class"]),
        "measured": dict(limb["measured"]),
        "population": dict(rule["population"]),
    }


def resolve_pointer(policy: dict[str, Any], pointer: str) -> str:
    """Resolve a '<file>#<dotted.path>' declaration to the VALUE it points at (one home, no copy: C12)."""
    if "#" not in pointer:
        raise OwnerMarksError(f"declared pointer is not '<file>#<dotted.path>': {pointer!r}")
    rel, dotted = pointer.split("#", 1)
    node: Any = yaml.safe_load(resolve(policy, rel).read_text(encoding="utf-8"))
    for step in dotted.split("."):
        if not isinstance(node, dict) or step not in node:
            raise OwnerMarksError(f"{pointer} does not resolve: missing {step!r}")
        node = node[step]
    value = str(node).strip()
    if not value:
        raise OwnerMarksError(f"{pointer} resolves to an empty value")
    return value


def pair_object_path(policy: dict[str, Any]) -> Path:
    """Where the pair object lives — declared with the measurement, read through a pointer (never a copy)."""
    return resolve(policy, resolve_pointer(policy, str(policy["sources"]["pair_object"])))


def rule_digest(policy: dict[str, Any]) -> str:
    """sha256 of the rule file: an object measured under OTHER parameters is STALE, not merely suspect."""
    return hashlib.sha256(
        resolve(policy, str(policy["sources"]["pair_object_parameters_home"])).read_bytes()).hexdigest()


def build_pair_object(policy: dict[str, Any]) -> dict[str, Any]:
    """Measure and write the pair OBJECT by IMPORTING the limb that owns the measurement (D-2646).

    `voice_limb` returns the pairs it found through `pair_sink`; this intake turns them into the artifact the sheet
    is rendered from. The object carries the rule's DIGEST and its parameters, so a rule changed after the
    measurement can never be reconciled silently against the older numbers.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_corroboration_collapse as rail  # ONE HOME: the measurement, imported and never reimplemented

    rule = yaml.safe_load(
        resolve(policy, str(policy["sources"]["pair_object_parameters_home"])).read_text(encoding="utf-8"))
    sink: list[dict[str, Any]] = []
    stats = rail.voice_limb(rule, 0, pair_sink=sink)
    if str(stats.get("state")) != "measured":
        raise OwnerMarksError(f"the measurement is {stats.get('state')}: {stats.get('why')}")
    limb = dict(rule["lexical_limb"])
    obj = {
        "schema_version": "1",
        "kind": "corroboration_collapse_pair_object",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule_file": str(policy["sources"]["pair_object_parameters_home"]),
        "rule_digest": rule_digest(policy),
        "parameters": {"collapse_at_or_above": float(limb["collapse_at_or_above"]),
                       "min_words_per_side": int(limb["min_words_per_side"]),
                       "shingle_words": int(limb["shingle_words"]),
                       "sketch_width": int(limb["sketch_width"])},
        "counts": {k: stats[k] for k in ("rows_tested", "pairs_at_bar", "pairs_identical_text", "groups",
                                         "rows_collapsed", "segments_matched") if k in stats},
        "pairs": sink,
    }
    atomic_write_text(pair_object_path(policy), json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    return obj


def load_pair_object(policy: dict[str, Any]) -> dict[str, Any]:
    """Read the pair OBJECT and REFUSE a stale one: a tier is deterministic only while it is in phase with the rule."""
    path = pair_object_path(policy)
    if not path.exists():
        raise OwnerMarksError(
            f"the pair object {path.relative_to(ROOT) if ROOT in path.parents else path} does not exist: the sheet "
            f"is rendered FROM the instrument, never from a column — run: python3 scripts/owner_marks.py --render")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if str(obj.get("kind")) != "corroboration_collapse_pair_object":
        raise OwnerMarksError(f"{path.name} is not a corroboration-collapse pair object (kind={obj.get('kind')!r})")
    if str(obj.get("rule_digest")) != rule_digest(policy):
        raise OwnerMarksError(
            f"the pair object is STALE: it was measured under a different "
            f"{policy['sources']['pair_object_parameters_home']} (digest mismatch) — re-render")
    declared = measurement(policy)
    params = dict(obj.get("parameters", {}))
    for key in ("collapse_at_or_above", "min_words_per_side"):
        if float(params.get(key, -1)) != float(declared[key]):
            raise OwnerMarksError(
                f"the pair object is STALE: it was measured at {key}={params.get(key)!r} while "
                f"{policy['sources']['pair_object_parameters_home']} declares {declared[key]!r} — re-render")
    pairs = list(obj.get("pairs", []))
    identical = sum(1 for p in pairs if p.get("identical"))
    if identical != int(obj.get("counts", {}).get("pairs_identical_text", -1)):
        raise OwnerMarksError("the pair object disagrees with itself: its identical count is not its own pairs")
    covered = {str(fb) for p in pairs for fb in p.get("rows", [])}
    if len(covered) != int(obj.get("counts", {}).get("rows_collapsed", -1)):
        raise OwnerMarksError(
            f"the pair object is not arithmetic: its pairs cover {len(covered)} DISTINCT row(s) while it publishes "
            f"rows_collapsed={obj.get('counts', {}).get('rows_collapsed')!r} (per-group counts are NOT additive)")
    return obj


# ── facts from the store (read-only) ─────────────────────────────────────────

def row_facts(policy: dict[str, Any]) -> dict[str, dict[str, str]]:
    """status / epistemic_status for every row of the declared population. READ-ONLY, one home for the fields."""
    pop = measurement(policy)["population"]
    from pipeline.pipeline_paths import DB_PATH  # ONE HOME (D-2646)

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        table = str(pop["table"])
        rows = con.execute(
            f"SELECT fb_id, {pop['status_field']}, {pop['epistemic_field']} FROM {table} "
            f"WHERE {pop['predicate']}").fetchall()
    finally:
        con.close()
    return {str(r[0]): {"status": str(r[1] or ""), "epistemic_status": str(r[2] or "")} for r in rows}


# ── the collapse sheet ───────────────────────────────────────────────────────

def work_key(a: str, b: str) -> str:
    """The unordered key both the sheet and the ledger can carry (a detector pair has no pair_id: BUG-781)."""
    return "|".join(sorted((str(a), str(b))))


def components(pairs: Sequence[dict[str, Any]]) -> list[list[tuple[str, str]]]:
    """Connected components over the collapsing pairs, numbered deterministically (largest first, ties by name)."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        parent[find(str(p["a"]))] = find(str(p["b"]))
    grouped: dict[str, list[tuple[str, str]]] = {}
    for p in pairs:
        grouped.setdefault(find(str(p["a"])), []).append((str(p["a"]), str(p["b"])))
    ordered = sorted(grouped.values(), key=lambda ps: (-len(ps), min(work_key(a, b) for a, b in ps)))
    return [sorted(ps, key=lambda ab: work_key(*ab)) for ps in ordered]


def prescreen_v1(policy: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Carry the v1 sheet's screen, its notes and its group numbering, keyed by the work pair.

    The v1 `owner_ruling` column is a MACHINE SCREEN with no writer in this repo (BUG-782): it is carried into
    `prescreen_verdict` where it can only ever be a PROPOSAL input, never an owner word. The two hand notes are
    carried verbatim into `owner_note`.
    """
    src = policy["sources"]
    path = resolve(policy, str(src["prescreen_v1_file"]))
    if not path.exists():
        return {}, {}, {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    # A v2 render CARRIES its own columns. Reading the v1 names off a v2 file would silently blank the screen
    # (MEASURED 2026-10-14: the pre-screen vanished on the second render) — so the carried columns win.
    v2 = "pair_object_digest" in header
    screen_col = "prescreen_verdict" if v2 else str(src.get("prescreen_v1_column", ""))
    group_col = "group_v1" if v2 else "group"
    notes: dict[str, str] = {}
    screens: dict[str, str] = {}
    groups: dict[str, str] = {}
    for row in rows:
        key = work_key(row.get("work_a", ""), row.get("work_b", ""))
        if screen_col and row.get(screen_col):
            screens[key] = str(row[screen_col]).strip()
        if row.get(group_col):
            groups[key] = str(row[group_col]).strip()
        if v2:
            note = str(row.get("owner_note") or "").strip()
        else:
            note = str(list(row.values())[-1] or "").strip() if len(list(row.values())) > 1 else ""
        if note:
            notes[key] = note
    return screens, notes, groups


def carried_words(policy: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Every owner word and note already on disk for the sheet, keyed by the work pair (never dropped)."""
    cfg = home(policy, "collapse_sheet")
    path = resolve(policy, str(cfg["path"]))
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if "owner_override" not in list(reader.fieldnames or []):
            return {}
        out: dict[str, dict[str, str]] = {}
        for row in reader:
            override = str(row.get(str(cfg["word_column"])) or "").strip()
            note = str(row.get(str(cfg["note_column"])) or "").strip()
            if override or note:
                out[work_key(row.get("work_a", ""), row.get("work_b", ""))] = {"override": override, "note": note}
        return out


def propose(policy: dict[str, Any], name: str, row: dict[str, str]) -> tuple[str, str]:
    """Propose a word from the strongest DECLARED evidence the row has, and name that evidence.

    A proposal is never a word: it lives in its own columns and the derivation never reads it.
    """
    for tier in tiers_for(policy, name):
        if predicate_matches(str(tier["predicate"]), row):
            word = tier.get("word")
            return ("" if word is None else str(word)), f"tier:{tier['id']}({tier['evidence']})"
    return "", "none"


def build_sheet_rows(policy: dict[str, Any]) -> list[dict[str, str]]:
    """Build the review sheet from the pair object + the store. One row per collapsing pair, groups numbered."""
    cfg = home(policy, "collapse_sheet")
    obj = load_pair_object(policy)
    facts = row_facts(policy)
    pop = measurement(policy)["population"]
    served_value, advertised_value = str(pop["served_value"]), str(pop["advertised_value"])
    screens, notes, groups_v1 = prescreen_v1(policy)
    carried = carried_words(policy)
    object_digest = hashlib.sha256(pair_object_path(policy).read_bytes()).hexdigest()
    columns = [str(c) for c in cfg["columns"]]
    rows: list[dict[str, str]] = []
    for gid, members in enumerate(components(list(obj["pairs"])), start=1):
        by_key = {work_key(str(p["a"]), str(p["b"])): p for p in obj["pairs"]}
        group_rows = {fb for a, b in members for fb in by_key[work_key(a, b)]["rows"]}
        distinct = {
            "group_rows_distinct": str(len(group_rows)),
            "group_rows_served": str(sum(1 for fb in group_rows if facts.get(fb, {}).get("status") == served_value)),
            "group_rows_advertised": str(
                sum(1 for fb in group_rows if facts.get(fb, {}).get("epistemic_status") == advertised_value)),
            "pair_object_digest": object_digest,
        }
        for a, b in members:
            key = work_key(a, b)
            pair = by_key[key]
            group_fb = [str(fb) for fb in pair["rows"]]
            row = {
                "group": str(gid),
                "group_v1": groups_v1.get(key, ""),
                "work_a": a,
                "work_b": b,
                "evidence_class": str(measurement(policy)["certain_class"] if pair.get("identical")
                                      else "containment_at_or_above_bar"),
                "similarity": f"{float(pair.get('similarity', 0.0)):.2f}",
                "rows_affected": str(len(group_fb)),
                "served_rows": str(sum(1 for fb in group_fb if facts.get(fb, {}).get("status") == served_value)),
                "advertised_corroborated_rows": str(
                    sum(1 for fb in group_fb if facts.get(fb, {}).get("epistemic_status") == advertised_value)),
                "prescreen_verdict": screens.get(key, ""),
                "owner_note": carried.get(key, {}).get("note", notes.get(key, "")),
                "owner_override": carried.get(key, {}).get("override", ""),
            }
            row.update(distinct)
            word, basis = propose(policy, "collapse_sheet", row)
            row["proposed_ruling"] = word
            row["proposal_basis"] = basis
            row["owner_ruling"], row["ruling_source"] = "", "none"
            rows.append({c: row.get(c, "") for c in columns})
    loss = [k for k in carried if k not in {work_key(r["work_a"], r["work_b"]) for r in rows}]
    if loss:
        raise OwnerMarksError(
            f"an owner word/note could not be carried to the new render ({len(loss)} row(s), e.g. {loss[0][:70]}): "
            f"refusing to render rather than DROP a word the owner already gave")
    for fault in bind_to_census(policy, rows):
        print(f"!! sheet vs census: {fault}", file=sys.stderr)
    return rows


# ── the ledger projection ────────────────────────────────────────────────────

def load_ledger(policy: dict[str, Any]) -> dict[str, Any]:
    """Read the D-2738 owner ledger (the ONE home of its verdicts)."""
    return json.loads(resolve(policy, str(home(policy, "ledger")["path"])).read_text(encoding="utf-8"))


def ledger_projection_rows(policy: dict[str, Any]) -> list[dict[str, str]]:
    """Project the ledger into the CSV the owner can mark; the ledger stays the one home of its verdicts."""
    ledger = load_ledger(policy)
    existing = carried_ledger_words(policy)
    rows: list[dict[str, str]] = []
    for pair in list(ledger.get("pairs", [])):
        hint = str(pair.get("hint", ""))
        fields = {"hint": hint, "max_similarity": str(pair.get("max_similarity", ""))}
        word, basis = propose(policy, "ledger", fields)
        pair_id = str(pair.get("pair_id", ""))
        rows.append({
            "pair_id": pair_id,
            "a_id": str(pair.get("a_id", "")),
            "b_id": str(pair.get("b_id", "")),
            "a": str(pair.get("a", "")),
            "b": str(pair.get("b", "")),
            "detectors": ",".join(str(x) for x in (pair.get("detectors") or [])),
            "max_similarity": str(pair.get("max_similarity", "")),
            "hint": hint,
            "proposed_verdict": word,
            "proposal_basis": basis,
            "owner_verdict": existing.get(pair_id, {}).get("verdict", ""),
            "owner_note": existing.get(pair_id, {}).get("note", ""),
        })
    if set(existing) != {r["pair_id"] for r in rows}:
        loss = set(existing) - {r["pair_id"] for r in rows}
        if loss:
            raise OwnerMarksError(f"a ledger word could not be carried ({len(loss)} pair(s)): refusing to render")
    return rows


def carried_ledger_words(policy: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Owner words already written in the ledger PROJECTION, keyed by pair_id (never dropped by a re-render)."""
    cfg = home(policy, "ledger")
    path = resolve(policy, str(cfg["projection"]))
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            verdict = str(row.get(str(cfg["projection_word_column"])) or "").strip()
            note = str(row.get(str(cfg["projection_note_column"])) or "").strip()
            if verdict or note:
                out[str(row.get("pair_id", ""))] = {"verdict": verdict, "note": note}
    return out


# ── atomic writes (C6) ───────────────────────────────────────────────────────

def atomic_write_text(path: Path, text: str) -> None:
    """tempfile -> fsync -> os.replace: a reader never sees a half-written artifact (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_csv(path: Path, columns: Sequence[str], rows: Sequence[dict[str, Any]]) -> None:
    """Write a CSV atomically, in the declared column order (LF newlines: a diff must be readable)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns), lineterminator=CSV_LINETERMINATOR)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    atomic_write_text(path, buf.getvalue())


def backup(path: Path, tag: str) -> str:
    """Copy an artifact aside before a write (C13). Returns the backup path ('' when there was nothing to keep)."""
    if not path.exists():
        return ""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = ROOT / BACKUP_DIR_REL / f"{path.name}.PRE_{tag}_{stamp}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return str(dest.relative_to(ROOT))


# ── derivation + coverage ────────────────────────────────────────────────────

def derive(policy: dict[str, Any], name: str, row: dict[str, str], override: str) -> tuple[str, str]:
    """The effective word: a per-row word, else the word of the first SIGNED tier the row satisfies, else ''."""
    if override:
        return override, "row"
    for tier in tiers_for(policy, name):
        if not tier.get("signed"):
            continue
        if tier.get("word") is None:
            continue
        if predicate_matches(str(tier["predicate"]), row):
            return str(tier["word"]), f"signature:{tier['id']}@{tier['signed']}"
    return "", "none"


def sheet_state(policy: dict[str, Any]) -> dict[str, Any]:
    """Derive every sheet row's word and check the vocabulary, the conflict rule and the census binding."""
    cfg = home(policy, "collapse_sheet")
    path = resolve(policy, str(cfg["path"]))
    if not path.exists():
        raise OwnerMarksError(f"the review sheet {cfg['path']} does not exist: run --render")
    vocab = vocabulary(policy, str(cfg["vocabulary"]))
    allowed = set(str(w) for w in vocab["words"])
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    derived: list[dict[str, str]] = []
    bad: list[str] = []
    for row in rows:
        override = str(row.get(str(cfg["word_column"])) or "").strip()
        if override and override not in allowed:
            bad.append(f"{work_key(row.get('work_a', ''), row.get('work_b', ''))}: {override!r} is not in "
                       f"{sorted(allowed)}")
        word, source = derive(policy, "collapse_sheet", row, override)
        derived.append({"a": row.get("work_a", ""), "b": row.get("work_b", ""),
                        "group": row.get("group", ""), "word": word, "source": source})
    if bad:
        raise OwnerMarksError("an owner word is not in the declared vocabulary: " + "; ".join(bad[:5]))
    withheld = str(vocab["withheld_word"])
    owed = [d for d in derived if not d["word"]]
    conflicts = conflict_pairs(policy, derived)
    binding = bind_to_census(policy, rows)
    return {"rows": len(rows), "owed": owed, "withheld": [d for d in derived if d["word"] == withheld],
            "conflicts": conflicts, "binding": binding, "derived": derived}


def conflict_pairs(policy: dict[str, Any], derived: Sequence[dict[str, str]]) -> list[str]:
    """A group cannot be one work AND two works: a DISTINCT edge inside a CONFIRM component is FATAL."""
    rule = dict(policy.get("conflict_rule", {}))
    if "collapse_sheet" not in list(rule.get("homes", [])):
        return []
    confirm = {str(w) for w in rule.get("confirm_words", [])}
    distinct = {str(w) for w in rule.get("distinct_words", [])}
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for d in derived:
        if d["word"] in confirm:
            parent[find(str(d["a"]))] = find(str(d["b"]))
    out = [f"{d['a'][:50]} != {d['b'][:50]}" for d in derived
           if d["word"] in distinct and find(str(d["a"])) == find(str(d["b"]))]
    return out


def bind_to_census(policy: dict[str, Any], rows: Sequence[dict[str, str]]) -> list[str]:
    """The sheet must NAME the measurement it was rendered from, and agree with it. Stale is FATAL.

    BUG-782, MEASURED: the v1 sheet was hand-built and drifted to 42 "identical" rows where the rail and the
    census both measured 37 — nothing compared them, so nothing could notice. Three checks close it:
      (a) every row carries the digest of the pair object it was rendered from, so a RE-MEASURED object makes the
          sheet stale until it is re-rendered;
      (b) the sheet's row count and its group count equal the published pair/group counts;
      (c) the object's own arithmetic (its pairs, its identical pairs, its groups and the DISTINCT rows it covers)
          equals the census. This is also what makes double-counting visible: rows can appear in MORE THAN ONE
          group, so the per-group columns are NOT additive (measured 2026-10-14: Σ per-group distinct = 717 over a
          corpus-wide distinct of 530, because 117 rows sit in more than one collapsing pair).
    """
    cfg = home(policy, "collapse_sheet")
    bind = dict(cfg["binding"])
    faults: list[str] = []
    obj_path = pair_object_path(policy)
    digest = hashlib.sha256(obj_path.read_bytes()).hexdigest() if obj_path.exists() else ""
    column = str(bind["digest_column"])
    seen = sorted({str(r.get(column, "")) for r in rows})
    if seen != [digest]:
        faults.append(f"the sheet does not name the current measurement ({column}={seen[:1]} vs object "
                      f"{digest[:12] or 'absent'}) — the sheet is STALE, re-render")
    declared = measurement(policy)["measured"]
    arithmetic = [str(k) for k in bind["object_arithmetic"]]
    counts = dict(load_pair_object(policy).get("counts", {}))
    want_pairs = int(declared[str(bind["sheet_pairs_field"])])
    if len(rows) != want_pairs:
        faults.append(f"the sheet carries {len(rows)} row(s) while {bind['sheet_pairs_field']} publishes {want_pairs}")
    want_groups = int(declared[str(bind["sheet_groups_field"])])
    groups = len({str(r.get("group", "")) for r in rows})
    if groups != want_groups:
        faults.append(f"the sheet carries {groups} group(s) while {bind['sheet_groups_field']} publishes "
                      f"{want_groups}")
    for key in arithmetic:
        if int(counts.get(key, -1)) != int(declared[key]):
            faults.append(f"the pair object's {key}={counts.get(key)!r} while the census publishes "
                          f"{declared[key]!r}")
    return faults


def ledger_state(policy: dict[str, Any]) -> dict[str, Any]:
    """Derive every ledger pair's verdict from the projection + signed tiers, and check the vocabulary."""
    cfg = home(policy, "ledger")
    vocab = vocabulary(policy, str(cfg["vocabulary"]))
    allowed = set(str(w) for w in vocab["words"])
    ledger = load_ledger(policy)
    pairs = list(ledger.get("pairs", []))
    projection = {r["pair_id"]: r for r in ledger_projection_rows(policy)}
    missing = [str(p.get("pair_id")) for p in pairs if str(p.get("pair_id")) not in projection]
    if missing:
        raise OwnerMarksError(f"the ledger projection is STALE: {len(missing)} pair(s) are not covered "
                              f"(e.g. {missing[0]}): run --render")
    derived: list[dict[str, str]] = []
    bad: list[str] = []
    for pair in pairs:
        row = projection[str(pair.get("pair_id"))]
        override = str(row.get("owner_verdict") or "").strip()
        if override and override not in allowed:
            bad.append(f"{pair.get('pair_id')}: {override!r} is not in {sorted(allowed)}")
        fields = {"hint": str(pair.get("hint", "")), "max_similarity": str(pair.get("max_similarity", ""))}
        word, source = derive(policy, "ledger", fields, override)
        derived.append({"pair_id": str(pair.get("pair_id")), "word": word, "source": source,
                        "current": str(pair.get("verdict", ""))})
    if bad:
        raise OwnerMarksError("a ledger word is not in the declared vocabulary: " + "; ".join(bad[:5]))
    withheld = str(vocab["withheld_word"])
    return {"pairs": len(derived), "owed": [d for d in derived if not d["word"]],
            "withheld": [d for d in derived if d["word"] == withheld], "derived": derived}


# ── the owner's act ──────────────────────────────────────────────────────────

TIER_ID_LINE: re.Pattern[str] = re.compile(r"^(\s*)-\s*id:\s*(\S+)\s*$")
SIGNED_LINE: re.Pattern[str] = re.compile(r"^(\s*)signed:\s*(\S.*)$")
DATE_LINE: re.Pattern[str] = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def tier_line_spans(lines: Sequence[str]) -> dict[str, tuple[int, int]]:
    """Map every tier id in the `tiers:` list to the [start, end) line span of its block.

    Scoped to the `tiers:` section ON PURPOSE: a `- id:` line elsewhere in the file is not a tier, and a signer that
    edits the first match it finds stamps the wrong rule (the BUG-751 ordinal class, one file over).
    """
    spans: dict[str, tuple[int, int]] = {}
    inside = False
    current: str | None = None
    for i, line in enumerate(lines):
        if not inside:
            if TIER_ID_LINE.match(line) is None and line.startswith("tiers:"):
                inside = True
            continue
        if line.strip() and not line[0].isspace():
            break
        match = TIER_ID_LINE.match(line)
        if match:
            if current is not None:
                spans[current] = (spans[current][0], i)
            current = match.group(2)
            spans[current] = (i, len(lines))
    return spans


def sign_tiers(
    policy: dict[str, Any], ids: Sequence[str], date: str, path: Path | None = None, *, take_backup: bool = True
) -> int:
    """THE OWNER'S WORD: stamp `signed: <date>` on the named tiers. The only writer of that field (D-2676)."""
    target = path or (ROOT / CONFIG_REL)
    if not DATE_LINE.match(date):
        raise OwnerMarksError(f"--date {date!r} is not YYYY-MM-DD: an act with no date is not auditable")
    known = {str(t["id"]): t for t in policy.get("tiers", [])}
    if not ids:
        raise OwnerMarksError(
            "--sign names NO tier: the ids ARE the owner's word, and a signature the tool chose for him is a "
            "minted rule (D-2898)")
    if len(set(ids)) != len(ids):
        raise OwnerMarksError(f"--sign names a tier twice ({list(ids)}): refusing an ambiguous act")
    for tid in ids:
        if tid not in known:
            raise OwnerMarksError(
                f"unknown tier id {tid!r}: {CONFIG_REL} declares {sorted(known)} - a signature over a rule that "
                f"does not exist MINTS one (D-2898)")
        if known[tid].get("word") is None:
            raise OwnerMarksError(
                f"tier {tid} names NO word (word: null): there is nothing to sign - those rows take a per-row word "
                f"or stay WITHHELD, and a signature would invent the word the contract refused to generalise")

    text = target.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    spans = tier_line_spans(lines)
    stamps: list[str] = []
    for tid in ids:
        if tid not in spans:
            raise OwnerMarksError(
                f"tier {tid!r} is in the parsed policy but not in {target.name}: refusing to write a signature the "
                f"file cannot carry")
        start, end = spans[tid]
        hits = [i for i in range(start, end) if SIGNED_LINE.match(lines[i])]
        if len(hits) != 1:
            raise OwnerMarksError(
                f"tier {tid}: expected exactly ONE `signed:` line inside its block, found {len(hits)} - refusing to "
                f"guess which line is the act")
        i = hits[0]
        previous = str(SIGNED_LINE.match(lines[i]).group(2)).strip()
        if previous not in ("null", "~"):
            raise OwnerMarksError(
                f"tier {tid} already carries a signature ({previous}): a re-sign is a deliberate act, never a silent "
                f"overwrite - remove it by hand if the word is being re-taken (D-2676)")
        indent = SIGNED_LINE.match(lines[i]).group(1)
        lines[i] = f"{indent}signed: '{date}'\n"
        stamps.append(tid)

    body = "".join(lines)
    reloaded = yaml.safe_load(body) or {}
    landed = {str(t["id"]): str(t.get("signed") or "") for t in reloaded.get("tiers", [])}
    before = {str(t["id"]): str(t.get("signed") or "") for t in policy.get("tiers", [])}
    for tid in ids:
        if landed.get(tid) != date:
            raise OwnerMarksError(
                f"tier {tid}: the signature did not land (read back {landed.get(tid)!r}) - refusing to write")
    for tid, value in landed.items():
        if tid not in ids and value != before.get(tid, ""):
            raise OwnerMarksError(
                f"the edit moved a signature it was not asked to touch ({tid}: {before.get(tid, '')!r} -> "
                f"{value!r}) - refusing to write")
    saved = backup(target, "owner_marks_sign") if take_backup else ""
    atomic_write_text(target, body)
    print(f"ok owner-marks --sign: {len(stamps)} tier(s) signed {date} ({', '.join(stamps)}) - THE OWNER'S WORD, "
          f"the only writer of `signed:`")
    if saved:
        print(f"   backup: {saved}")
    print("   next: python3 scripts/owner_marks.py --check   (rc 2 while words are still owed)")
    return int(policy["coverage"]["rc_released"])


# ── modes ────────────────────────────────────────────────────────────────────

def render(policy: dict[str, Any]) -> int:
    """Render the sheet and the ledger projection from their instruments, carrying every word already given."""
    cfg = home(policy, "collapse_sheet")
    sheet_path = resolve(policy, str(cfg["path"]))
    build_pair_object(policy)   # measure FIRST: the sheet is rendered from the instrument, never from a column
    rows = build_sheet_rows(policy)
    saved = backup(sheet_path, "owner_marks_render")
    write_csv(sheet_path, [str(c) for c in cfg["columns"]], rows)
    lcfg = home(policy, "ledger")
    projection = resolve(policy, str(lcfg["projection"]))
    proj_rows = ledger_projection_rows(policy)
    saved_proj = backup(projection, "owner_marks_render")
    write_csv(projection, [str(c) for c in lcfg["projection_columns"]], proj_rows)
    identical = sum(1 for r in rows if r["evidence_class"] == str(measurement(policy)["certain_class"]))
    print(f"ok owner-marks --render: sheet {cfg['path']} ({len(rows)} row(s), {identical} "
          f"{measurement(policy)['certain_class']}) | ledger projection {lcfg['projection']} "
          f"({len(proj_rows)} pair(s))")
    if saved:
        print(f"   backup: {saved}" + (f" | {saved_proj}" if saved_proj else ""))
    return int(policy["coverage"]["rc_released"])


def check(policy: dict[str, Any]) -> int:
    """The ONE reading the ladder needs. rc 0 released | 2 owed (loud, not fatal) | 1 error."""
    cov = dict(policy["coverage"])
    sheet, ledger = sheet_state(policy), ledger_state(policy)
    owed = len(sheet["owed"]) + len(ledger["owed"])
    conflicts = list(sheet["conflicts"])
    binding = list(sheet["binding"])
    if conflicts or binding:
        for fault in conflicts:
            print(f"!! owner-marks: CONFLICT — {fault} (a group cannot be one work and two works)", file=sys.stderr)
        for fault in binding:
            print(f"!! owner-marks: the sheet is OUT OF PHASE with the census — {fault}", file=sys.stderr)
        print("FAIL owner-marks: the words contradict each other or the measurement (D-2898: never resolved by "
              "preferring one word)", file=sys.stderr)
        return int(cov["rc_error"])
    print(f"OWED owner-marks: sheet {len(sheet['owed'])}/{sheet['rows']} row(s) without a word "
          f"| ledger {len(ledger['owed'])}/{ledger['pairs']} pair(s) without a verdict | withheld "
          f"{len(sheet['withheld'])} + {len(ledger['withheld'])} (a withheld word keeps the ingest door CLOSED by "
          f"the owner's own word: D-2997#door.ingest_reading)")
    if owed:
        print("   tiers signed: " + ", ".join(f"{t['id']}={'yes' if t.get('signed') else 'no'}"
                                               for t in policy.get("tiers", [])))
        return int(cov["rc_owed"])
    print("ok owner-marks: every row of both homes carries a word or a WITHHELD word — the act is complete")
    return int(cov["rc_released"])


def apply_words(policy: dict[str, Any]) -> int:
    """Expand the signed tiers over their predicates and write the result WITH its provenance. Deletes nothing."""
    cfg = home(policy, "collapse_sheet")
    sheet_path = resolve(policy, str(cfg["path"]))
    rows = build_sheet_rows(policy)
    sheet = sheet_state(policy)
    by_key = {work_key(d["a"], d["b"]): d for d in sheet["derived"]}
    written = 0
    for row in rows:
        d = by_key[work_key(row["work_a"], row["work_b"])]
        row["owner_ruling"], row["ruling_source"] = d["word"], d["source"]
        written += 1 if d["word"] and d["source"] != "none" else 0
    saved = backup(sheet_path, "owner_marks_apply")
    write_csv(sheet_path, [str(c) for c in cfg["columns"]], rows)
    lcfg = home(policy, "ledger")
    ledger = load_ledger(policy)
    words = {d["pair_id"]: d for d in ledger_state(policy)["derived"]}
    changed = 0
    for pair in list(ledger.get("pairs", [])):
        d = words.get(str(pair.get("pair_id")), {"word": "", "source": "none"})
        if d["word"] and str(pair.get("verdict")) != d["word"]:
            pair["verdict"] = d["word"]
            pair["owner_note"] = pair.get("owner_note", "")
            pair["ruling_source"] = d["source"]
            changed += 1
    pairs = list(ledger.get("pairs", []))
    withheld = str(vocabulary(policy, "ledger")["withheld_word"])
    ledger["adjudicated"] = sum(1 for p in pairs if str(p.get("verdict")) != withheld)
    ledger["pending"] = len(pairs) - int(ledger["adjudicated"])
    if changed:
        # Never a stamp for an act that did not happen: an `adjudicated_at` written while nothing was adjudicated is
        # a claim-shaped field with a false reading (the BUG-782 class the intake exists to retire).
        ledger["adjudicated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        ledger["adjudicated_from"] = (f"{CONFIG_REL}#tiers (owner signatures) + "
                                      f"{lcfg['projection']}#{lcfg['projection_word_column']}")
    ledger_path = resolve(policy, str(lcfg["path"]))
    saved_ledger = backup(ledger_path, "owner_marks_apply")
    atomic_write_text(ledger_path, json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    atomic_write_text(resolve(policy, RECEIPT_REL), json.dumps({
        "schema_version": "1", "kind": "owner_marks_apply_receipt",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sheet": {"path": cfg["path"], "rows": len(rows), "words_written": written,
                  "backup": saved},
        "ledger": {"path": lcfg["path"], "pairs": len(pairs), "verdicts_written": changed,
                   "adjudicated": ledger["adjudicated"], "pending": ledger["pending"], "backup": saved_ledger},
        "tiers": [{"id": t["id"], "signed": t.get("signed")} for t in policy.get("tiers", [])],
    }, indent=2) + "\n")
    print(f"ok owner-marks --apply: sheet {written} row(s) resolved | ledger {changed} verdict(s) written "
          f"(adjudicated {ledger['adjudicated']} / pending {ledger['pending']}) | receipt {RECEIPT_REL}")
    return int(policy["coverage"]["rc_released"])


# ── selftest ─────────────────────────────────────────────────────────────────

CONTROL_LABELS: tuple[str, ...] = (
    "the_vocabulary_rejects_a_word_no_owner_can_say",
    "a_signature_over_a_declared_predicate_expands_to_the_rows_it_names",
    "an_unsigned_tier_leaves_its_rows_owed",
    "a_withheld_word_counts_as_a_word_and_keeps_the_door_closed",
    "a_transitivity_violation_is_fatal_never_resolved",
    "a_sheet_out_of_phase_with_the_census_is_fatal",
    "an_owners_word_is_never_dropped_by_a_re_render",
    "the_matcher_raises_on_a_predicate_it_does_not_understand",
    "a_stale_pair_object_is_refused_never_rendered",
    "a_signature_is_written_on_the_named_tier_and_nowhere_else",
    "an_unknown_tier_id_is_refused_never_guessed",
    "a_tier_that_names_no_word_is_never_signed",
)


def _synthetic_context(policy: dict[str, Any], tmp: Path, stale: bool = False) -> dict[str, Any]:
    """A policy whose MEASUREMENT lives under a temp dir, so the pure controls exercise the real code paths."""
    rule = yaml.safe_load(
        resolve(policy, str(policy["sources"]["pair_object_parameters_home"])).read_text(encoding="utf-8"))
    limb = dict(rule["lexical_limb"])
    obj_path = tmp / "object.json"
    limb["pair_object_file"] = str(obj_path)
    limb["measured"] = {"rows_tested": 2, "pairs_at_bar": 1, "pairs_identical_text": 1, "groups": 1,
                        "rows_collapsed": 2}
    rule["lexical_limb"] = limb
    (tmp / "rule.yaml").write_text(yaml.safe_dump(rule), encoding="utf-8")
    obj_path.write_text(json.dumps({
        "schema_version": "1", "kind": "corroboration_collapse_pair_object",
        "rule_digest": "deadbeef" if stale else hashlib.sha256((tmp / "rule.yaml").read_bytes()).hexdigest(),
        "parameters": {"collapse_at_or_above": float(limb["collapse_at_or_above"]),
                       "min_words_per_side": int(limb["min_words_per_side"])},
        "counts": {"pairs_at_bar": 1, "pairs_identical_text": 1, "groups": 1, "rows_collapsed": 2},
        "pairs": [{"a": "A", "b": "B", "identical": True, "similarity": 1.0, "rows": ["fb1", "fb2"]}]}),
        encoding="utf-8")
    ctx = json.loads(json.dumps(policy))
    ctx["sources"]["pair_object"] = f"{tmp / 'rule.yaml'}#lexical_limb.pair_object_file"
    ctx["sources"]["pair_object_parameters_home"] = str(tmp / "rule.yaml")
    return ctx


def selftest() -> int:
    """Known-answer controls over the pure parts. No store, no network, no LLM (BUG-492)."""
    policy = load_policy()
    failures: list[str] = []
    collapse_vocab = vocabulary(policy, str(home(policy, "collapse_sheet")["vocabulary"]))
    allowed = set(str(w) for w in collapse_vocab["words"])

    def control(label: str, ok: bool) -> None:
        if not ok:
            failures.append(label)

    control(CONTROL_LABELS[0], "MERGE" not in allowed and "CONFIRM-ONE-WORK" in allowed)

    tier = {"id": "T", "home": "collapse_sheet", "predicate": 'evidence_class == "identical_normalised_text"',
            "word": "CONFIRM-ONE-WORK", "evidence": "declared", "signed": None}
    signed = dict(tier, signed="2026-10-14")
    probe = dict(policy)
    probe["tiers"] = [tier]
    row = {"evidence_class": "identical_normalised_text"}
    control(CONTROL_LABELS[1],
            derive(probe, "collapse_sheet", row, "") == ("", "none")
            and derive(dict(probe, tiers=[signed]), "collapse_sheet", row, "")
            == ("CONFIRM-ONE-WORK", "signature:T@2026-10-14"))
    control(CONTROL_LABELS[2], derive(probe, "collapse_sheet", row, "")[1] == "none")

    withheld = str(collapse_vocab["withheld_word"])
    control(CONTROL_LABELS[3],
            derive(probe, "collapse_sheet", row, withheld) == (withheld, "row")
            and withheld not in ("", "CONFIRM-ONE-WORK"))

    derived = [{"a": "A", "b": "B", "group": "1", "word": "CONFIRM-ONE-WORK", "source": "row"},
               {"a": "B", "b": "C", "group": "1", "word": "CONFIRM-ONE-WORK", "source": "row"},
               {"a": "A", "b": "C", "group": "1", "word": "DISTINCT", "source": "row"}]
    control(CONTROL_LABELS[4], len(conflict_pairs(policy, derived)) == 1
            and len(conflict_pairs(policy, derived[:2])) == 0)

    tmp5 = Path(tempfile.mkdtemp(prefix="owner_marks_bind_"))
    try:
        ctx5 = _synthetic_context(policy, tmp5)
        fresh = hashlib.sha256(pair_object_path(ctx5).read_bytes()).hexdigest()
        good = [{"group": "1", "pair_object_digest": fresh}]
        bad = [{"group": "1", "pair_object_digest": "deadbeef"}]
        control(CONTROL_LABELS[5], bind_to_census(ctx5, good) == [] and bind_to_census(ctx5, bad) != [])
    finally:
        shutil.rmtree(tmp5, ignore_errors=True)

    tmp = Path(tempfile.mkdtemp(prefix="owner_marks_selftest_"))
    try:
        keep = {"group": "1", "work_a": "A", "work_b": "B", "owner_override": "DISTINCT", "owner_note": "keep 2e",
                "prescreen_verdict": "yes", "group_v1": "7"}
        write_csv(tmp / "sheet.csv", [str(c) for c in home(policy, "collapse_sheet")["columns"]], [keep])
        cfg = home(policy, "collapse_sheet")
        ctx = dict(policy)
        ctx["homes"] = dict(policy["homes"])
        ctx["homes"]["collapse_sheet"] = dict(cfg, path=str(tmp / "sheet.csv"))
        ctx["sources"] = dict(policy["sources"], prescreen_v1_file=str(tmp / "sheet.csv"))
        carried = carried_words(ctx)
        kept = carried.get(work_key("A", "B"), {})
        screens, notes, groups_v1 = prescreen_v1(ctx)
        key = work_key("A", "B")
        control(CONTROL_LABELS[6], kept.get("override") == "DISTINCT" and kept.get("note") == "keep 2e"
                and screens.get(key) == "yes" and notes.get(key) == "keep 2e" and groups_v1.get(key) == "7")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    try:
        predicate_matches("evidence_class ==", {})
    except OwnerMarksError:
        control(CONTROL_LABELS[7], True)
    else:
        control(CONTROL_LABELS[7], False)

    tmp2 = Path(tempfile.mkdtemp(prefix="owner_marks_stale_"))
    try:
        fresh_ctx = _synthetic_context(policy, tmp2)
        stale_dir = tmp2 / "stale"
        stale_dir.mkdir()
        stale_ctx = _synthetic_context(policy, stale_dir, stale=True)
        ok_fresh = True
        try:
            load_pair_object(fresh_ctx)
        except OwnerMarksError:
            ok_fresh = False
        stale_refused = False
        try:
            load_pair_object(stale_ctx)
        except OwnerMarksError:
            stale_refused = True
        control(CONTROL_LABELS[8], ok_fresh and stale_refused)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    tmp3 = Path(tempfile.mkdtemp(prefix="owner_marks_sign_"))
    try:
        sign_target = tmp3 / "owner_marks.yaml"
        sign_target.write_bytes((ROOT / CONFIG_REL).read_bytes())
        signed_ok = True
        try:
            with redirect_stdout(io.StringIO()):   # a control is not an act: keep the mode's own report quiet
                sign_tiers(policy, ["A"], "2026-10-14", path=sign_target, take_backup=False)
        except OwnerMarksError:
            signed_ok = False
        after = yaml.safe_load(sign_target.read_text(encoding="utf-8")) or {}
        got = {str(t["id"]): str(t.get("signed") or "") for t in after.get("tiers", [])}
        control(CONTROL_LABELS[9],
                signed_ok and got.get("A") == "2026-10-14" and not any(v for k, v in got.items() if k != "A"))
        unknown_refused = False
        try:
            with redirect_stdout(io.StringIO()):
                sign_tiers(policy, ["Z-NOT-A-TIER"], "2026-10-14", path=sign_target, take_backup=False)
        except OwnerMarksError:
            unknown_refused = True
        still_one = yaml.safe_load(sign_target.read_text(encoding="utf-8")) or {}
        control(CONTROL_LABELS[10],
                unknown_refused
                and {str(t["id"]): str(t.get("signed") or "") for t in still_one.get("tiers", [])}.get("A")
                == "2026-10-14")
        noword_refused = False
        try:
            with redirect_stdout(io.StringIO()):
                sign_tiers(policy, ["L-C"], "2026-10-14", path=sign_target, take_backup=False)
        except OwnerMarksError:
            noword_refused = True
        control(CONTROL_LABELS[11], noword_refused)
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)

    for label in CONTROL_LABELS:
        print(f"   {'PASS' if label not in failures else 'FAIL'} {label}")
    if failures:
        print(f"FAIL owner-marks --selftest: {len(failures)} of {len(CONTROL_LABELS)} control(s) failed: "
              f"{failures}")
        return 1
    print(f"ok owner-marks --selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} known-answer control(s) green")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """CLI: exactly one mode. A missing mode is a usage error, never an accidental write."""
    p = argparse.ArgumentParser(description="the owner's word: render | check | apply (T-129/T-130, BUG-782)")
    p.add_argument("--render", action="store_true", help="render the sheet + the ledger projection")
    p.add_argument("--check", action="store_true", help="validate both homes; rc 2 = words still owed")
    p.add_argument("--apply", action="store_true", help="expand signed tiers and write the derived words")
    p.add_argument("--selftest", action="store_true", help="known-answer controls, no store")
    p.add_argument(
        "--sign", nargs="+", metavar="TIER",
        help="THE OWNER'S ACT: stamp `signed: <date>` on the named tier(s) - the only writer of that field")
    p.add_argument(
        "--date", default=datetime.now().date().isoformat(),
        help="the date the owner's word lands (YYYY-MM-DD; default = today, local)")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one mode. Fail closed: an unreadable input is an error, never a clean reading (C16)."""
    args = _build_parser().parse_args(argv)
    modes = [m for m in (args.render, args.check, args.apply, args.selftest, bool(args.sign)) if m]
    if len(modes) != 1:
        print("FAIL-CLOSED (owner-marks): pass exactly ONE of --sign <TIER>... | --render | --check | --apply | "
              "--selftest", file=sys.stderr)
        return int(load_policy()["coverage"]["rc_error"]) if any(
            (args.check, args.render, args.apply, args.sign)) else 1
    try:
        if args.selftest:
            return selftest()
        policy = load_policy()
        if args.sign:
            return sign_tiers(policy, [str(t) for t in args.sign], str(args.date))
        if args.render:
            return render(policy)
        if args.apply:
            return apply_words(policy)
        return check(policy)
    except OwnerMarksError as exc:
        print(f"!! owner-marks: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # C16: log AND raise the exit — never a silent pass
        print(f"!! owner-marks: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
