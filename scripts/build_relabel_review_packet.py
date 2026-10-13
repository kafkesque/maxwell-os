#!/usr/bin/env python3
"""scripts/build_relabel_review_packet.py — D-2976/BUG-749: the OWNER review packet for discipline labels.

WHY THIS EXISTS. A canonical row's discipline is only defensible if the LIVE production mapper
reproduces it from the row's OWN raw label (R14: a decision belongs in the declaration, not in the
row). Two cohorts do not satisfy that today:

  QUEUE A — MENU-RESCOPE. D-2928 moved the DEFINITIONS of `business administration` and
            `organizational theory` (composite be323543… -> cc800a32…) without moving the ANSWER SPACE,
            and deliberately refused to rewrite the frozen rows (I2/D-2896: the stamp records what a
            row WAS adjudicated against, and rewriting it would falsify history). The differential
            audit (scripts/audit_menu_rescope_cohort.py, D-2974) measures that delta with the
            RECORDED-menu arm as the CONTROL: a movement is attributable to the re-scope only if the
            control reproduces the stored label; where the control fails too it is instrument noise.

  QUEUE B — RE-DERIVATION GAP. BUG-749: 1,072 of 6,587 in-subject rows (16.3%) carry a canonical
            discipline their own raw label no longer produces.

THE REVIEW UNIT IS THE DECISION, NOT THE ROW — the whole point of this packet. 1,072 rows collapse
into the distinct (raw label -> canonical home) decisions, ordered by how many rows each one governs,
so the largest unit is settled first and one verdict applies mechanically to every row it covers.
Queue B's dominant cause is MEASURED, not guessed: D-2814 (2026-10-09) RETIRED the alias_map.yaml
layer from the synonym index, and the canonical run (rechunk-v4-20260929) was admitted ten days
EARLIER, while that layer was live. The rows are not random drift; they are the legacy of a retired
compensating control.

WHAT THE OWNER WRITES — one word in `owner_action`, plus `owner_canonical` only when CORRECT:
  CONFIRM  the stored canonical IS the right home for this raw label. Apply = DECLARE the raw as an
           alias in config/taxonomy.yaml (the ONE synonym home). MEASURED (this script's selftest):
           a raw-alias declaration does NOT move menu_hash and does NOT move the answer space —
           closed_menu._taxonomy_entries renders value+definition+group ONLY, so raws are not menu
           fields. The label becomes reproducible with ZERO provenance disturbance and NO relabel.
  CORRECT  the stored canonical is wrong -> name the home in `owner_canonical`; every row of the unit
           is relabelled to it (an owner-gated re-classification, D-2898).
  ABSTAIN  no canonical home fits -> the label becomes the declared absence `emerging` (D-2830).
  LEAVE    the mapping stands as a historical artefact and nothing is written (I2).

AUTHORITY. The classifier of record is ADVISORY (kappa ~0.45 against the owner's discipline anchor,
D-2868/D-2770 class): no LLM answer relabels a canonical row (D-2898). This script proposes nothing it
cannot derive from bytes — it names each gap's CAUSE and ranks candidate homes by token overlap, both
labelled advisory — and it writes no store, config or label byte (store opened read-only).

READ-ONLY + C6 writes: three artifacts are rendered to tempfile -> fsync -> os.replace.
Config-first (C12): every label, definition and group is read from config, never restated here.

Usage:
    python3 scripts/build_relabel_review_packet.py --selftest
    python3 scripts/build_relabel_review_packet.py [--date YYYYMMDD]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.serving_gate import content_types_without_factual_claim  # noqa: E402

_TAXONOMY = ROOT / "config" / "taxonomy.yaml"
_ALIAS_MAP = ROOT / "config" / "alias_map.yaml"
_ANCHOR_FAMILY = ROOT / "config" / "anchor_family.yaml"
_JOURNAL = ROOT / "governance" / "menu_rescope_cohort_audit.jsonl"
_GOV = ROOT / "governance"
_AUDIT_SCRIPT = ROOT / "scripts" / "audit_menu_rescope_cohort.py"

# The review form's closed vocabulary (D-2976). A module constant rather than config, by the
# pipeline/closed_menu._CONTENT_TYPE_ROLES precedent: it is this artifact's contract with its
# reader, not a tunable. Rendered into the reference sheet so the form explains itself.
ACTIONS = (
    ("CONFIRM", "the stored canonical IS the right home; declare the raw as an alias (no relabel)"),
    ("CORRECT", "the stored canonical is wrong; name the home in owner_canonical (relabels the unit)"),
    ("ABSTAIN", "no canonical home fits; the label becomes the declared absence `emerging`"),
    ("LEAVE", "the mapping stands as a historical artefact; nothing is written (I2)"),
)
QUEUE_REDERIVE = "DISCIPLINE-RE-DERIVATION"
QUEUE_RESCOPE = "MENU-RESCOPE"
LATE_HOME = "LATE-HOME"
ALIAS_RETIRED = "ALIAS-LAYER-RETIRED (D-2814)"
REPOINTED = "DECLARATION-REPOINTED"
UNRESOLVED = "PROVENANCE-UNRESOLVED"
FB_FIELDS = ("name", "definition", "mechanism", "boundary", "consequence")
SEGMENT_CHARS = 800
TOP_UNITS = 12
CANDIDATES = 3
_GENERIC = frozenset({"studies", "science", "theory", "research", "practice", "general", "applied"})

UNIT_COLUMNS = (
    "review_id", "unit_key", "queue", "n_rows", "raw_label", "stored_canonical", "live_mapper_says",
    "cause", "evidence", "candidates_advisory", "owner_action", "owner_canonical", "owner_comment",
    "sample_fb_id", "sample_name",
)
SEGMENT_COLUMNS = ("review_id", "unit_key", "fb_id", "name", "content_type", "stored_canonical",
                   "raw_label", "live_mapper_says", *FB_FIELDS)


def _yaml(path: Path) -> dict:
    """Load a YAML mapping, fail-closed on a missing or non-mapping document (C16)."""
    if not path.exists():
        raise SystemExit(f"FAIL-CLOSED (packet): {path.name} does not exist (C16)")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit(f"FAIL-CLOSED (packet): {path.relative_to(ROOT)} is not a mapping (C16)")
    return doc


def _norm(x: object) -> str:
    """Collapse a label for comparison (case- and whitespace-insensitive)."""
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()


def _sha(path: Path) -> str:
    """Short content hash of a source, for the packet's provenance header (R14 spirit)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else "ABSENT"


def _audit() -> Any:
    """Import the D-2974 audit for its PRODUCTION mapper — never a restatement of it (C12)."""
    spec = importlib.util.spec_from_file_location("audit_menu_rescope_cohort", _AUDIT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _revisions() -> dict[str, dict[str, set[str]]]:
    """Frozen taxonomy revisions: raw alias -> the canonicals it was declared under, per revision.

    "Then" cannot be inferred from a version string alone (the live v9 file is AMENDED in place — the
    D-2928 re-scope moved definitions without moving the answer space), so the frozen snapshots are
    compared against the live file and the packet reports the DIFFERENCE, never a reconstruction.
    """
    out: dict[str, dict[str, set[str]]] = {}
    for path in sorted((ROOT / "config").glob("taxonomy*.yaml")):
        doc = _yaml(path)
        idx: dict[str, set[str]] = {}
        for e in (doc.get("disciplines") or []) + (doc.get("domains") or []):
            canon = _norm(e.get("canonical"))
            for raw in e.get("raw") or []:
                idx.setdefault(_norm(raw), set()).add(canon)
        out[path.name] = idx
    return out


def _alias_layer() -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """alias_map.yaml: discipline targets, domain targets, and the LINE each declaration sits on."""
    path = _ALIAS_MAP
    doc = _yaml(path)
    disc = {_norm(k): _norm(v) for k, v in (doc.get("discipline_aliases") or {}).items()}
    dom = {_norm(k): _norm(v) for k, v in (doc.get("domain_aliases") or {}).items()}
    lines: dict[str, int] = {}
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        key = _norm(line.split(":", 1)[0]) if ":" in line else ""
        if key and key not in lines and key in disc:
            lines[key] = i
    return disc, dom, lines


def _cause(raw: str, stored: str, live: str, revs: dict[str, dict[str, set[str]]],
           disc_alias: dict[str, str], lines: dict[str, int]) -> tuple[str, str]:
    """Name WHY the live mapper no longer reproduces the stored label — bytes only, ordered ladder."""
    r, s = _norm(raw), _norm(stored)
    if not s:
        return UNRESOLVED, "the row carries no stored canonical"
    if s == "emerging":
        return LATE_HOME, (f"stored `emerging` (no home at admission); the LIVE revision declares "
                           f"`{live}` — a home added after this row was admitted")
    if disc_alias.get(r) == s:
        return ALIAS_RETIRED, (f"config/alias_map.yaml:{lines.get(r, '?')} declares "
                               f"`{r}` -> `{s}`; the layer is RETIRED from the synonym index "
                               f"(D-2814, 2026-10-09) and this run was admitted BEFORE that")
    then = sorted({c for name, idx in revs.items() if name != _TAXONOMY.name
                   for c in idx.get(r, ())})
    if then and s in then:
        return REPOINTED, (f"a frozen revision declares `{r}` -> `{s}`, the LIVE revision declares it "
                           f"under `{live}`; the DECLARATION was re-pointed after this row")
    return UNRESOLVED, (f"neither the live taxonomy raws, nor any frozen revision, nor the RETIRED "
                        f"config/alias_map.yaml declares `{r}` under `{s}`: the admission-time resolver "
                        f"is not recoverable from bytes (F-02 family) — this one needs the owner's eyes")


def _unit_rows(revs: dict[str, dict[str, set[str]]], mapper: Any) -> tuple[list[dict], dict]:
    """Every in-subject canonical-run row whose own raw label does not reproduce its stored label."""
    run = str((_yaml(_ANCHOR_FAMILY).get("store_bridge") or {}).get("canonical_run") or "")
    if not run:
        raise SystemExit("FAIL-CLOSED (packet): config/anchor_family.yaml declares no "
                         "store_bridge.canonical_run — the packet cannot name its subject (C16)")
    outside = sorted(content_types_without_factual_claim())
    marks = ", ".join("?" * len(outside))
    cols = ", ".join(f"COALESCE({c}, '')" for c in FB_FIELDS)
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            f"SELECT fb_id, {cols}, COALESCE(discipline, ''), COALESCE(discipline_raw, ''), "
            "COALESCE(taxonomy_match_method, ''), COALESCE(content_type, '') FROM fbs "
            f"WHERE pipeline_run_id = ? AND COALESCE(content_type, '') NOT IN ({marks}) "
            "ORDER BY discipline, fb_id", [run, *outside]).fetchall()
    keys = ("fb_id", *FB_FIELDS, "stored_canonical", "raw_label", "match_method", "content_type")
    out = []
    for r in rows:
        rec = dict(zip(keys, r, strict=True))
        rec["live_mapper_says"] = mapper(rec["raw_label"])
        if _norm(rec["live_mapper_says"]) != _norm(rec["stored_canonical"]):
            out.append(rec)
    return out, {"run": run, "in_subject": len(rows), "gap": len(out)}


def _rescope_units() -> list[dict]:
    """Queue A: the ATTRIBUTABLE movements the D-2974 differential proved (control-validated)."""
    if not _JOURNAL.exists():
        return []
    recs: dict[tuple[str, str], dict] = {}
    for line in _JOURNAL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            recs[(str(rec.get("fb_id")), str(rec.get("arm")))] = rec
    out = []
    for (fb_id, arm), rec in sorted(recs.items()):
        if arm != "live" or rec.get("error"):
            continue
        control = recs.get((fb_id, "recorded"))
        if not control or control.get("error") or not control.get("agrees"):
            continue  # the CONTROL does not reproduce the stored label => instrument uncertainty
        if _norm(rec.get("pred_canonical")) == _norm(rec.get("stored_discipline")):
            continue
        out.append({"fb_id": fb_id, "name": str(rec.get("name") or ""),
                    "raw_label": str(rec.get("stored_discipline_raw") or ""),
                    "stored_canonical": str(rec.get("stored_discipline") or ""),
                    "live_mapper_says": str(rec.get("pred_canonical") or ""),
                    "recorded_revision": str(rec.get("recorded_revision") or "")})
    return out


def _candidates(raw: str, stored: str, live: str, tax: dict) -> str:
    """Rank candidate homes by token overlap — ADVISORY, deterministic, never applied (D-2898)."""
    tokens = {t for t in re.split(r"[^a-z0-9]+", _norm(raw)) if t and t not in _GENERIC}
    if not tokens:
        return ""
    scored: list[tuple[int, str]] = []
    for e in tax.get("disciplines") or []:
        canon = _norm(e.get("canonical"))
        if canon in {_norm(stored), _norm(live)}:
            continue
        name_t = {t for t in re.split(r"[^a-z0-9]+", canon) if t}
        raw_t = {t for t in re.split(r"[^a-z0-9]+", _norm(" ".join(e.get("raw") or []))) if t}
        def_t = {t for t in re.split(r"[^a-z0-9]+", _norm(e.get("definition") or "")) if t}
        score = 3 * len(tokens & name_t) + len(tokens & raw_t) + len(tokens & def_t) // 4
        if score:
            scored.append((score, str(e.get("canonical"))))
    scored.sort(key=lambda kv: (-kv[0], kv[1]))
    return " | ".join(name for _, name in scored[:CANDIDATES])


def _clamp(text: object) -> str:
    """Collapse whitespace and clamp a segment field to the readable width."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s if len(s) <= SEGMENT_CHARS else s[:SEGMENT_CHARS].rstrip() + " …"


def _atomic(path: Path, text: str) -> None:
    """C6: tempfile -> fsync -> os.replace, so a reader never sees a half-written artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _csv_text(header: tuple[str, ...], rows: list[dict]) -> str:
    """Render one CSV against a fixed header contract (a missing column is loud, never silent)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for rec in rows:
        writer.writerow([rec.get(c, "") for c in header])
    return buf.getvalue()


def build(date: str) -> int:
    """Derive both queues, render the reference sheet and the two review CSVs."""
    tax = _yaml(_TAXONOMY)
    revs = _revisions()
    disc_alias, _dom_alias, lines = _alias_layer()
    mapper = _audit()._map_discipline
    gap_rows, meta = _unit_rows(revs, mapper)
    rescope = _rescope_units()

    units: list[dict] = []
    for rec in gap_rows:
        cause, evidence = _cause(rec["raw_label"], rec["stored_canonical"],
                                 rec["live_mapper_says"], revs, disc_alias, lines)
        key = (_norm(rec["raw_label"]), _norm(rec["stored_canonical"]),
               _norm(rec["live_mapper_says"]), cause)
        unit = next((u for u in units if u["_key"] == key), None)
        if unit is None:
            unit = {"_key": key, "queue": QUEUE_REDERIVE, "n_rows": 0,
                    "raw_label": rec["raw_label"], "stored_canonical": rec["stored_canonical"],
                    "live_mapper_says": rec["live_mapper_says"], "cause": cause,
                    "evidence": evidence,
                    "candidates_advisory": _candidates(rec["raw_label"], rec["stored_canonical"],
                                                       rec["live_mapper_says"], tax),
                    "owner_action": "", "owner_canonical": "", "owner_comment": "",
                    "sample_fb_id": rec["fb_id"], "sample_name": rec["name"], "rows": []}
            units.append(unit)
        unit["n_rows"] += 1
        unit["rows"].append(rec)
    for rec in rescope:
        units.append({"_key": ("rescope", rec["fb_id"]), "queue": QUEUE_RESCOPE, "n_rows": 1,
                      "raw_label": rec["raw_label"], "stored_canonical": rec["stored_canonical"],
                      "live_mapper_says": rec["live_mapper_says"],
                      "cause": "DEFINITION-RE-SCOPE (D-2928)",
                      "evidence": (f"the RECORDED-menu control ({rec['recorded_revision']}) "
                                   "reproduces the stored label, so the LIVE movement is attributable "
                                   "to the sharpened v10 definition, not to instrument noise"),
                      "candidates_advisory": _candidates(rec["raw_label"], rec["stored_canonical"],
                                                         rec["live_mapper_says"], tax),
                      "owner_action": "", "owner_canonical": "", "owner_comment": "",
                      "sample_fb_id": rec["fb_id"], "sample_name": rec["name"],
                      "rows": [{"fb_id": rec["fb_id"], **{k: "" for k in FB_FIELDS}}]})

    units.sort(key=lambda u: (u["queue"] != QUEUE_REDERIVE, -u["n_rows"], u["raw_label"]))
    for i, u in enumerate(units, 1):
        # review_id is a PRINTED ORDINAL: it is recomputed every build, so it is NOT an identity and a
        # ruling must never be keyed on it. unit_key IS the identity - the decision's own content
        # (raw -> stored for a mapping decision; the fb_id for a per-row re-scope decision).
        u["review_id"] = f"U{i:03d}"
        u["unit_key"] = (f"{_norm(u['raw_label'])} -> {_norm(u['stored_canonical'])}"
                         if u["queue"] == QUEUE_REDERIVE else f"row:{u['sample_fb_id']}")

    segs: list[dict] = []
    for u in units:
        for rec in u["rows"]:
            segs.append({"review_id": u["review_id"], "unit_key": u["unit_key"], "fb_id": rec["fb_id"],
                         "name": _clamp(rec.get("name")), "content_type": rec.get("content_type", ""),
                         "stored_canonical": u["stored_canonical"], "raw_label": u["raw_label"],
                         "live_mapper_says": u["live_mapper_says"],
                         **{f: _clamp(rec.get(f)) for f in FB_FIELDS}})

    md = _render_md(date, tax, units, segs, meta, len(rescope))
    csv_units = _csv_text(UNIT_COLUMNS, units)
    csv_segs = _csv_text(SEGMENT_COLUMNS, segs)
    names = (f"CANONICAL_RELABEL_REVIEW_{date}.md", f"canonical_relabel_review_{date}.csv",
             f"canonical_relabel_review_segments_{date}.csv")
    for name, text in zip(names, (md, csv_units, csv_segs), strict=True):
        _atomic(_GOV / name, text)
    _summary(units, segs, meta, names)
    return 0


def _render_md(date: str, tax: dict, units: list[dict], segs: list[dict], meta: dict,
               n_rescope: int) -> str:
    """Render the review reference sheet: the law, the form, then the closed menu."""
    counts: dict[str, int] = {}
    for u in units:
        counts[u["cause"]] = counts.get(u["cause"], 0) + u["n_rows"]
    covered = sum(u["n_rows"] for u in units[:TOP_UNITS])
    total = sum(u["n_rows"] for u in units) or 1
    head = [
        f"# CANONICAL RELABEL REVIEW — reference sheet ({date[:4]}-{date[4:6]}-{date[6:]})",
        "",
        "Generated by `scripts/build_relabel_review_packet.py` (D-2976). **DO NOT hand-edit: regenerate.**",
        "",
        f"- Subject: `{meta['run']}` — {meta['in_subject']} in-subject rows; "
        f"**{meta['gap']} rows ({round(100 * meta['gap'] / max(meta['in_subject'], 1), 1)}%)** carry a "
        "discipline their own raw label no longer produces (BUG-749).",
        f"- Review units: **{len(units)}** decisions (queue A re-scope {n_rescope}, "
        f"queue B re-derivation {len(units) - n_rescope}); the top {TOP_UNITS} units carry "
        f"{round(100 * covered / total, 1)}% of the rows — **settle those first**.",
        "- Cause census (rows): " + ", ".join(f"`{k}` {v}" for k, v in sorted(counts.items(),
                                                                              key=lambda kv: -kv[1])),
        f"- Sources: config/taxonomy.yaml `{_sha(_TAXONOMY)}` · config/alias_map.yaml `{_sha(_ALIAS_MAP)}` · "
        f"store `{_sha(Path(DB_PATH))}` · audit journal `{_sha(_JOURNAL)}`",
        "",
        "---",
        "",
        "## HOW TO REVIEW (fast path)",
        "",
        f"1. Open `canonical_relabel_review_{date}.csv` — **one row = one decision**, biggest leverage "
        "first (`n_rows`).",
        "2. `cause` and `evidence` say WHY the label is not reproducible today; `candidates_advisory` "
        "proposes homes (token overlap — advisory, you may name ANY canonical below).",
        f"3. Read the segments for a unit by filtering `canonical_relabel_review_segments_{date}.csv` "
        "on its `review_id`.",
        "4. Write ONE word in `owner_action` and, only if CORRECT, a home in `owner_canonical`. "
        "Leave `owner_comment` for a nuance. Nothing is applied until the packet is returned.",
        "",
        "## THE FOUR ACTIONS (`owner_action`)",
        "",
        "| Action | Meaning | What the system then does |",
        "|---|---|---|",
    ]
    apply = {
        "CONFIRM": "declares the raw as an alias in `config/taxonomy.yaml` — MEASURED: no menu_hash "
                   "move, no answer-space move, no relabel",
        "CORRECT": "relabels every row of the unit to `owner_canonical` (owner-gated re-classification, "
                   "D-2898), then re-derives",
        "ABSTAIN": "writes the declared absence `emerging` for the unit (D-2830)",
        "LEAVE": "writes nothing; the stored label stands and its stamp is NOT rewritten (I2/D-2896)",
    }
    for action, meaning in ACTIONS:
        head.append(f"| `{action}` | {meaning} | {apply[action]} |")
    head += [
        "",
        "An unrecognised word, or `CORRECT` with an empty or non-canonical `owner_canonical`, "
        "**fails closed** at application time.",
        "",
        "## THE TWO QUEUES",
        "",
        f"- **{QUEUE_REDERIVE}** (BUG-749) — a retired or re-pointed synonym declaration: the live "
        "mapper is correct-by-design, the row is a legacy of an earlier map.",
        f"- **{QUEUE_RESCOPE}** (D-2928/D-2974) — a DEFINITION moved without moving the answer space, so "
        "the row is judged against a definition that has since been sharpened. Each row is its own "
        "unit: only rows whose RECORDED-menu control reproduced the stored label are listed.",
        "",
        "---",
        "",
        f"## THE CLOSED MENU — {len([d for d in tax.get('disciplines') or [] if d.get('canonical') != 'emerging'])} "
        "canonical disciplines + `emerging`",
        "",
        "Pick ONLY from these. `emerging` is the declared absence (D-2830), never a preference.",
        "",
    ]
    by_group: dict[str, list[dict]] = {}
    for e in tax.get("disciplines") or []:
        if e.get("canonical") != "emerging":
            by_group.setdefault(str(e.get("group") or "Uncategorized"), []).append(e)
    for group in sorted(by_group):
        head += [f"### {group}", "", "| Canonical label | Definition |", "|---|---|"]
        for e in sorted(by_group[group], key=lambda x: str(x["canonical"])):
            head.append(f"| `{e['canonical']}` | {_clamp(e.get('definition'))} |")
        head.append("")
    return "\n".join(head) + "\n"


def _summary(units: list[dict], segs: list[dict], meta: dict, names: tuple[str, ...]) -> None:
    """Print the measured headline so the run answers 'what must I relabel' in ONE screen (BUG-492)."""
    counts: dict[str, int] = {}
    for u in units:
        counts[u["cause"]] = counts.get(u["cause"], 0) + u["n_rows"]
    print(f"subject        : {meta['run']} — {meta['in_subject']} in-subject rows")
    print(f"gap            : {meta['gap']} rows ({round(100 * meta['gap'] / max(meta['in_subject'], 1), 1)}%)")
    print(f"review units   : {len(units)} decisions core the {len(segs)} flagged rows")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"   {v:5d} rows  {k}")
    print("top units:")
    for u in units[:8]:
        print(f"   {u['review_id']} {u['n_rows']:5d} rows  {u['raw_label'][:30]:30s} "
              f"stored={u['stored_canonical'][:24]:24s} live={u['live_mapper_says'][:24]}")
    for name in names:
        print("wrote          : governance/" + name)


def selftest() -> int:
    """Known-answer controls: the decision shape must be SEEN to be right (BUG-492)."""
    fails: list[str] = []

    def expect(name: str, got: object, want: object) -> None:
        if got == want:
            print(f"  ok selftest/{name}")
        else:
            fails.append(f"{name}: got {got!r}, want {want!r}")
            print(f"  FAIL selftest/{name}: {got!r} != {want!r}")

    revs = {"taxonomy_v9.yaml": {"innovation management": {"creative process"}}, "taxonomy.yaml": {}}
    cause, _ = _cause("design studies", "design thinking", "emerging",
                      {"taxonomy_v9.yaml": {"design studies": {"design thinking"}}, "taxonomy.yaml": {}},
                      {"design studies": "design thinking"}, {"design studies": 362})
    expect("alias-retired-wins-over-repoint", cause, ALIAS_RETIRED)
    cause, _ = _cause("innovation management", "creative process", "entrepreneurship studies", revs,
                      {}, {})
    expect("frozen-revision-declares-it-elsewhere-is-repointed", cause, REPOINTED)
    cause, _ = _cause("nonesuch", "design thinking", "emerging", revs, {}, {})
    expect("not-recoverable-from-bytes", cause, UNRESOLVED)
    cause, _ = _cause("marketing science", "emerging", "marketing", revs, {}, {})
    expect("stored-abstention-is-late-home", cause, LATE_HOME)

    tax = _yaml(_TAXONOMY)
    cands = _candidates("design studies", "design thinking", "emerging", tax)
    expect("candidates-never-restate-the-existing-position", "design thinking" in cands, False)

    # The load-bearing measurement: a raw-alias declaration moves NEITHER the composite NOR the answer
    # space (raws are not menu fields). If this ever fails, CONFIRM is no longer a free repair.
    import pipeline.closed_menu as cm  # noqa: PLC0415

    before = cm.menu_hash(cm.render_closed_menu())
    mutated = {"disciplines": [dict(e) for e in (tax.get("disciplines") or [])],
               "domains": tax.get("domains"), "meta": tax.get("meta")}
    for e in mutated["disciplines"]:
        if e.get("canonical") == "design thinking":
            e["raw"] = list(e.get("raw") or []) + ["design studies <selftest>"]
    import tempfile as _tf  # noqa: PLC0415

    tmp = Path(_tf.mkdtemp()) / "taxonomy.yaml"
    tmp.write_text(yaml.safe_dump(mutated, sort_keys=False, allow_unicode=True), encoding="utf-8")
    original = cm._TAXONOMY_PATH
    try:
        cm._TAXONOMY_PATH = tmp
        cm.render_closed_menu.cache_clear()
        after = cm.menu_hash(cm.render_closed_menu())
    finally:
        cm._TAXONOMY_PATH = original
        cm.render_closed_menu.cache_clear()
        tmp.unlink(missing_ok=True)
        tmp.parent.rmdir()
    expect("raw-alias-declaration-is-menu-neutral", before == after, True)

    expect("action-vocabulary-is-closed", [a for a, _ in ACTIONS], ["CONFIRM", "CORRECT", "ABSTAIN",
                                                                   "LEAVE"])
    expect("unit-header-contract", set(UNIT_COLUMNS) >= {"owner_action", "owner_canonical",
                                                        "n_rows", "cause", "review_id"}, True)
    expect("segment-header-contract", set(SEGMENT_COLUMNS) >= set(FB_FIELDS) | {"review_id"}, True)
    if fails:
        print(f"FAIL-CLOSED (packet): {len(fails)} control(s) failed: " + "; ".join(fails))
        return 1
    print("ok selftest: the packet's premises hold (a control that never fires is a comment, BUG-492)")
    return 0


def main(argv: list[str]) -> int:
    """CLI: --selftest (no writes) or build the packet for --date (default today)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    parser.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"), help="artifact date stamp")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not re.fullmatch(r"\d{8}", str(args.date)):
        raise SystemExit("FAIL-CLOSED (packet): --date must be YYYYMMDD (C16)")
    return build(str(args.date))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
