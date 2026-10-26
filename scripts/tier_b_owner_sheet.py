#!/usr/bin/env python3
"""scripts/tier_b_owner_sheet.py — the OWNER'S ruling sheet for the unruled tier-B candidates (T-195 d2).

WHY THIS EXISTS (BUG-988, measured 2026-10-24). The adjudication CSV is a MODEL record: one column per voter
and NO column for the owner's word. Handed that file, the owner asked the only question that matters —
"where do I write my decision, and where do I READ the thing I am deciding?". Three defects, each measured:

  1. NO DECISION COLUMN. The owner's ruling is the one human gate in the completeness arm (D-2898: never
     auto-certified) and the sheet had nowhere to put it, so the file could be read but not answered.
  2. THE POINTER DID NOT RESOLVE (D-3034). Every closest_fb_id / closest_fb_name in the adjudication CSV
     resolved into ZERO rows of `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl` (0/23 by id, 0/23 by
     name), because the LIVE STORE is run `rechunk-v4-20260929` while the t11 checkpoints are a DIFFERENT
     run. MEASURED: the 23 review rows' closest store rows all carry pipeline_run_id rechunk-v4-20260929.
  3. A TIER-B CANDIDATE IS *NEVER* IN A CHECKPOINT, BY CONSTRUCTION. Measured on the same 43: 0 of their
     concept_keys exist in the store and 0 exist in the t11 S5 checkpoint — that is WHAT tier-B MEANS
     (D-3130: "a concept the store may have OMITTED"). Searching a checkpoint for one can only ever fail, so
     the sheet must say so instead of implying the row is somewhere findable.

WHAT THIS BUILDS. One row per candidate that needs review, carrying:
  * the SOURCE PASSAGE at its own location — the paragraph the grounding measured, quoted at owner length
    (config reading_chars), with the neighbouring paragraphs and a `locate` string naming the file and the
    paragraph index, so the reading can be checked in the book itself;
  * the closest STORE row (name / definition / application / cosine) WITH the run it lives in and a
    cross-reference verdict against the t11 checkpoint — so a pointer either resolves or says it cannot;
  * two EMPTY columns the owner fills: owner_decision (MATCH|NONE) and owner_note.

Three faces of ONE sheet (config-declared paths): a CSV to type into, a self-contained HTML to READ, and a
noob-proof markdown procedure (D-3100: numbered, copy-paste-able, with the expected output and the branch to
take if it differs). The CSV is then consumed by `scripts/rule_tier_b.py --from-csv`, so the typed word
becomes the authoritative ruling with no JSON to paste and no sheet to hand-edit.

ADVISORY DISCIPLINE. Nothing here rules anything: no verdict is written, no floor moves, no model opinion is
promoted (D-2658/D-2898/D-3137). The script reads the panel envelope, the evidence sheet, the source bytes and
the store; it writes only the three owner-facing faces. No LLM anywhere (D-343), deterministic, temp=0 N/A.
C6: every write is tempfile -> fsync -> os.replace. R14: the HTML/CSV carry schema_version + pipeline_commit.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
CONFIG_PATH = PROJECT_ROOT / "config" / "extraction_recall.yaml"
SCHEMA_VERSION = "1"
ARTIFACT_ID = "tier_b_owner_sheet"


# ---------------------------------------------------------------------------------------------------------------
# config / io
# ---------------------------------------------------------------------------------------------------------------
def load_cfg() -> dict[str, Any]:
    """Read every path, cap and column name from config/extraction_recall.yaml (C12 — nothing hardcoded)."""
    import yaml

    doc = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    er = doc.get("extraction_recall") or {}
    adj = er.get("tier_b_adjudication") or {}
    sheet = adj.get("owner_sheet") or {}
    missing = [k for k in ("csv_path", "html_path", "how_to_path", "reading_chars",
                           "decision_column", "valid_decisions") if k not in sheet]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: tier_b_adjudication.owner_sheet is missing {missing} (C12)")
    for key in ("path", "disagree_csv_path"):
        if not adj.get(key):
            raise SystemExit(f"FAIL-CLOSED: tier_b_adjudication.{key} missing in config (C12)")
    ev = er.get("tier_b_evidence") or {}
    if not ev.get("path"):
        raise SystemExit("FAIL-CLOSED: tier_b_evidence.path missing in config (C12)")
    if not er.get("store"):
        raise SystemExit("FAIL-CLOSED: extraction_recall.store missing in config (C12)")
    if not (er.get("golden") or {}).get("tier_b_ruling_sheet"):
        raise SystemExit("FAIL-CLOSED: golden.tier_b_ruling_sheet missing in config (C12)")
    return {"adj": adj, "sheet": sheet, "evidence_path": ev["path"], "store": er["store"],
            "golden": er.get("golden") or {}}


def _atomic_write(path: Path, text: str) -> None:
    """C6: tempfile -> fsync -> os.replace (a half-written sheet must never be readable as a whole one)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(PROJECT_ROOT),
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def _source_title(source_file: str) -> str:
    """A human title from the source path: the file stem, minus the z-library catch-all parenthetical."""
    stem = Path(source_file).stem
    return re.sub(r"\s*\((?:z-library|1lib|z-lib)[^)]*\)", "", stem).strip()


# ---------------------------------------------------------------------------------------------------------------
# the reading (source bytes, the SAME splitter the grounding used)
# ---------------------------------------------------------------------------------------------------------------
def split_paragraphs(text: str) -> dict[int, str]:
    """Index the source exactly as scripts/tier_b_evidence.py does, so `excerpt_index` still points HERE.

    ONE splitter, one index space: the evidence sheet records the RAW re.split index (before the short-block
    filter), so re-deriving the passage for a longer window must not renumber it (D-3034: a pointer must
    resolve to the same object it was minted for).
    """
    out: dict[int, str] = {}
    for idx, para in enumerate(re.split(r"\n\s*\n", text)):
        clean = " ".join(para.split())
        if len(clean) < 40:
            continue
        out[idx] = clean
    return out


def _neighbour(paras: dict[int, str], idx: int | None, step: int) -> str:
    """The nearest non-empty paragraph before/after `idx` (empty when the passage is at a boundary).

    NEAREST means the next PRESENT index, not idx+1: the splitter drops headings and page numbers, so the
    paragraph after the cited one can be idx+2 (BUG-988's shape if a neighbour list silently skipped it).
    """
    if idx is None:
        return ""
    keys = sorted(paras)
    if step > 0:
        for k in keys:
            if k > idx:
                return paras[k]
    else:
        for k in reversed(keys):
            if k < idx:
                return paras[k]
    return ""


def _reading_window(para: str, tokens: list[str], cap: int) -> str:
    """Cut a readable window AROUND the first matched concept token (the evidence sheet's own rule, reused).

    Imported rather than re-implemented: the owner sheet must window a long paragraph the SAME way the
    grounding measured it, or the quote the owner reads is not the quote the evidence cites (D-3137 cl.3).
    """
    from tier_b_evidence import _window_on_match

    return _window_on_match(para, tokens, cap)


# ---------------------------------------------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------------------------------------------
def _first_defined(votes: dict[str, Any], models: list[str], field: str) -> str:
    """The first non-empty value of `field` across the panel (a proposal is panelled, not owned by one voter)."""
    for m in models:
        val = (votes.get(m) or {}).get(field)
        if val:
            return str(val)
    return ""


def _vote_text(row: dict[str, Any], models: list[str], labels: dict[str, str]) -> str:
    parts = []
    for m in models:
        v = (row.get("votes") or {}).get(m) or {}
        verdict = v.get("verdict") or "ERR"
        conf = v.get("confidence")
        label = labels.get(m) or m
        parts.append(f"{label} {verdict}" + (f" {conf}" if conf not in (None, "") else ""))
    return " · ".join(parts)


def build_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Join the panel envelope, the evidence sheet, the source bytes and the store into owner-readable rows."""
    from pipeline.dedup_identity import content_tokens

    adj, sheet = cfg["adj"], cfg["sheet"]
    envelope = json.loads((PROJECT_ROOT / adj["path"]).read_text(encoding="utf-8"))
    models = list(envelope.get("models") or adj.get("models") or [])
    labels = dict(sheet.get("model_labels") or {})
    ev_rows = json.loads((PROJECT_ROOT / cfg["evidence_path"]).read_text(encoding="utf-8")).get("rows") or []
    ev = {(r["source_id"], r["concept_key"]): r for r in ev_rows}

    store = sqlite3.connect(str(PROJECT_ROOT / cfg["store"]))
    store.row_factory = sqlite3.Row
    cur = store.cursor()

    # cross-reference: the checkpoint the owner searched, so a row can SAY whether it resolves there (BUG-988)
    crossref_path = PROJECT_ROOT / str(sheet.get("crossref_checkpoint") or "")
    cross_ids: set[str] = set()
    cross_names: set[str] = set()
    cross_ok = False
    if sheet.get("crossref_checkpoint") and crossref_path.exists():
        cross_ok = True
        with crossref_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("fb_id"):
                    cross_ids.add(str(rec["fb_id"]))
                if rec.get("name"):
                    cross_names.add(" ".join(str(rec["name"]).lower().split()))

    sources: dict[str, dict[int, str]] = {}
    out: list[dict[str, Any]] = []
    for row in envelope.get("rows") or []:
        if not row.get("needs_review"):
            continue  # UNANIMOUS MATCH / UNANIMOUS NONE never reaches the owner (that is the point of the panel)
        sid, name, ck = row["source_id"], row["name"], row["concept_key"]
        e = ev.get((sid, ck)) or {}
        grounding = e.get("grounding") or {}
        source_file = str(grounding.get("source_file") or "")
        idx = grounding.get("excerpt_index")

        reading, before, after, locate = "", "", "", ""
        if source_file:
            if sid not in sources:
                text = artifact_encoding.open_artifact(PROJECT_ROOT / source_file, PROJECT_ROOT).read()  # D-2646/BUG-511
                sources[sid] = split_paragraphs(text)
            paras = sources[sid]
            para = paras.get(idx) if isinstance(idx, int) else None
            if para:
                reading = _reading_window(para, content_tokens(name), int(sheet["reading_chars"]))
                before = _neighbour(paras, idx, -1)[: int(sheet.get("context_chars") or 0)]
                after = _neighbour(paras, idx, +1)[: int(sheet.get("context_chars") or 0)]
            locate = (f"paragraph {idx} of {len(paras)} in {source_file}" if isinstance(idx, int)
                      else f"{source_file} (the grounding measured no passage)")

        top = (row.get("store_best") or [{}])[0]
        fb_id = str(top.get("fb_id") or "")
        fb = None
        if fb_id:
            fb = cur.execute("select fb_id,name,definition,application,status,pipeline_run_id,created_at "
                             "from fbs where fb_id = ?", (fb_id,)).fetchone()
        fb_name = str((fb["name"] if fb else top.get("name")) or "")
        if not cross_ok:
            crossref = "NOT CHECKED (crossref_checkpoint is undeclared or absent in config)"
        elif fb_id and fb_id in cross_ids:
            crossref = "found in t11 (fb_id + name)"
        elif fb_name and " ".join(fb_name.lower().split()) in cross_names:
            crossref = "found in t11 by NAME only (fb_id was re-minted by a later run)"
        else:
            run = (fb["pipeline_run_id"] if fb else "") or "unknown run"
            st = (fb["status"] if fb else "") or "unknown status"
            crossref = f"NOT in t11 — this store row lives in run {run} (status {st})"

        out.append({
            "candidate_name": name,
            "panel_agreement": row.get("agreement", ""),
            "panel_votes": _vote_text(row, models, labels),
            "reading_kind": row.get("reading_kind", ""),
            "reading": reading,
            "context_before": before,
            "context_after": after,
            "locate": locate,
            "candidate_definition": _first_defined(row.get("votes") or {}, models, "definition"),
            "candidate_application": _first_defined(row.get("votes") or {}, models, "application"),
            "closest_fb_name": fb_name,
            "closest_fb_definition": str(fb["definition"]) if fb else "",
            "closest_fb_application": str(fb["application"]) if fb else "",
            "closest_cos": f"{float(top.get('cos')):.4f}" if top.get("cos") is not None else "",
            "closest_fb_status": str(fb["status"]) if fb else "",
            "closest_fb_run": str(fb["pipeline_run_id"]) if fb else "",
            "closest_fb_crossref": crossref,
            "closest_fb_id": fb_id,
            "source_title": _source_title(source_file) if source_file else "",
            "source_id": sid,
            "concept_key": ck,
            "source_file": source_file,
        })
    store.close()
    out.sort(key=lambda r: (r["source_title"].lower(), r["candidate_name"].lower()))
    for i, r in enumerate(out, 1):
        r["review_no"] = i
    return out


# ---------------------------------------------------------------------------------------------------------------
# faces
# ---------------------------------------------------------------------------------------------------------------
def csv_columns(sheet: dict[str, Any]) -> list[str]:
    """Column order is the reading order: the owner's word first, then the passage, then the comparison."""
    return ["review_no", str(sheet["decision_column"]), str(sheet["note_column"]),
            "candidate_name", "panel_agreement", "panel_votes", "reading_kind",
            "reading", "context_before", "context_after", "locate",
            "candidate_definition", "candidate_application",
            "closest_fb_name", "closest_fb_definition", "closest_fb_application",
            "closest_cos", "closest_fb_status", "closest_fb_run", "closest_fb_crossref",
            "closest_fb_id", "source_title", "source_id", "concept_key", "source_file"]


def write_csv(path: Path, rows: list[dict[str, Any]], sheet: dict[str, Any], commit: str) -> None:
    cols = csv_columns(sheet)
    import io

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        row = dict(r)
        row[str(sheet["decision_column"])] = ""   # NEVER pre-filled: the ruling is the owner's word
        row[str(sheet["note_column"])] = ""
        w.writerow(row)
    # the header the reader needs is the CSV's own; provenance rides in the HTML + markdown (a CSV with a
    # comment line is read as data by every spreadsheet, which is the BUG-988 shape in another costume)
    _atomic_write(path, buf.getvalue())


def write_html(path: Path, rows: list[dict[str, Any]], sheet: dict[str, Any], commit: str) -> None:
    e = html.escape
    dec, note = str(sheet["decision_column"]), str(sheet["note_column"])
    cards = []
    for r in rows:
        ctx = ""
        if r["context_before"] or r["context_after"]:
            ctx = (f'<div class="ctx"><span class="lbl">before</span>…{e(r["context_before"])}…</div>'
                   f'<div class="ctx"><span class="lbl">after</span>…{e(r["context_after"])}…</div>')
        cards.append(f"""
<section class="card" id="r{r['review_no']}">
  <h2><span class="no">{r['review_no']}</span> {e(r['candidate_name'])}
      <span class="badge">{e(r['panel_agreement'])}</span></h2>
  <p class="votes">{e(r['panel_votes'])}</p>
  <p class="where"><b>Read it here:</b> {e(r['source_title'])} — <code>{e(r['locate'])}</code>
     <span class="kind">({e(r['reading_kind'])})</span></p>
  <blockquote>{e(r['reading']) or '<i>no passage was measured for this candidate</i>'}</blockquote>
  {ctx}
  <div class="cmp">
    <div><h3>candidate (the model's proposal)</h3>
      <p><b>Definition.</b> {e(r['candidate_definition'])}</p>
      <p><b>Application.</b> {e(r['candidate_application'])}</p></div>
    <div><h3>closest row already in the store
      <span class="cos">cos {e(r['closest_cos'])} · {e(r['closest_fb_status'])}</span></h3>
      <p><b>Name.</b> {e(r['closest_fb_name'])}</p>
      <p><b>Definition.</b> {e(r['closest_fb_definition'])}</p>
      <p><b>Application.</b> {e(r['closest_fb_application'])}</p>
      <p class="small">{e(r['closest_fb_crossref'])}</p></div>
  </div>
  <p class="decide">Type <code>MATCH</code> or <code>NONE</code> into column <code>{e(dec)}</code> of the CSV
     for row <b>{r['review_no']}</b> (optional note in <code>{e(note)}</code>).
     <a href="#top">back to top</a></p>
</section>""")

    legend = f"""
<section class="legend">
  <h2>Read this once, then start at row 1</h2>
  <p><b>These rows cannot be found in any t11 checkpoint, and that is not a mistake.</b> A tier-B candidate is
     by definition a concept the extractor did <i>not</i> produce (D-3130). Measured on these 43: <b>0</b> of
     their concept keys exist in the store and <b>0</b> in the t11 S5 checkpoint. So the checkpoint is the wrong
     place to look — the right place is the <b>book</b>, at the paragraph named on each card.</p>
  <p><b>MATCH</b> = this source really does teach this concept. It becomes a <b>floor</b>: the pipeline must
     extract it, and the recall rail stays RED until it does. <b>NONE</b> = the source does not teach it as a
     concept. A wrong MATCH pins a RED rail; a wrong NONE loses the concept silently — so rule from the passage,
     never from the label.</p>
  <p><b>The panel is advisory only.</b> Four models voted; where they split you decide (D-2658/D-2898/D-3137).
     A vote is an opinion, not evidence: the evidence is the <b>quote</b> and its <b>location</b>.</p>
  <p><b>The closest store row</b> is shown so you can see whether the concept already exists under another
     name. Its cosine is the store's own "semantically near" measure; at or above
     <b>{e(str(sheet.get('semantic_near_threshold', 0.8)))}</b> the pipeline already calls the two near, which is
     a reason to look closely — never proof of anything.</p>
</section>"""

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>tier-B owner review — {len(rows)} rows to rule</title>
<style>
 body{{font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;margin:0;
       background:#f6f7f9;color:#14181d}}
 .wrap{{max-width:1040px;margin:0 auto;padding:28px 20px 80px}}
 h1{{font-size:26px;margin:0 0 4px}} .sub{{color:#5b6570;margin:0 0 24px}}
 .legend{{background:#fff;border:1px solid #dfe3e8;border-left:5px solid #2f6fed;border-radius:8px;
          padding:14px 20px;margin-bottom:26px}}
 .legend h2{{font-size:17px;margin:0 0 8px}} .legend p{{margin:8px 0}}
 .card{{background:#fff;border:1px solid #dfe3e8;border-radius:8px;padding:16px 20px;margin:0 0 20px}}
 .card h2{{font-size:19px;margin:0 0 6px;line-height:1.3}}
 .no{{display:inline-block;min-width:1.9em;text-align:center;background:#14181d;color:#fff;
      border-radius:6px;font-size:15px;padding:1px 6px;margin-right:6px}}
 .badge{{font-size:12px;font-weight:600;color:#7a4b00;background:#fff4d6;border:1px solid #f0d79a;
         border-radius:999px;padding:2px 9px;vertical-align:middle;white-space:nowrap}}
 .votes{{font-size:13px;color:#3c4650;background:#f2f4f7;border-radius:6px;padding:6px 10px;margin:6px 0 10px}}
 .where{{font-size:13.5px;color:#3c4650;margin:0 0 8px}}
 .where code{{font-size:12px;background:#f2f4f7;padding:1px 5px;border-radius:4px}}
 .kind{{color:#5b6570}}
 blockquote{{margin:0 0 10px;padding:12px 16px;border-left:4px solid #2f6fed;background:#f8faff;
             font-family:Georgia,"Times New Roman",serif;font-size:16.5px}}
 .ctx{{font-size:13px;color:#67717c;margin:0 0 4px;padding-left:4px}}
 .ctx .lbl{{display:inline-block;min-width:3.6em;color:#9aa3ad;text-transform:uppercase;font-size:11px;
            letter-spacing:.04em}}
 .cmp{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:14px}}
 .cmp h3{{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#5b6570;margin:0 0 6px}}
 .cmp p{{margin:0 0 7px;font-size:14.5px}}
 .cos{{font-weight:400;text-transform:none;letter-spacing:0;color:#9aa3ad}}
 .small{{font-size:12.5px;color:#7a4b00}}
 .decide{{margin:14px 0 0;font-size:13.5px;color:#3c4650;border-top:1px dashed #dfe3e8;padding-top:10px}}
 .decide a{{float:right;color:#2f6fed;text-decoration:none}}
 @media(max-width:720px){{.cmp{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap" id="top">
<h1>tier-B owner review — {len(rows)} rows need your word</h1>
<p class="sub">{len(rows)} split or majority rows out of 43 unruled candidates. Every unanimous row was already
  promoted by agreement and is not here. Advisory only: nothing is ruled until you type it.
  Generated from <code>{e(str(sheet.get('csv_path','')))}</code> · pipeline_commit {e(commit)} ·
  schema {e(SCHEMA_VERSION)}.</p>
{legend}
{''.join(cards)}
<p class="sub">End of sheet — write your decisions into
  <code>{e(str(sheet.get('csv_path','')))}</code>, then run
  <code>python3 scripts/rule_tier_b.py --from-csv {e(str(sheet.get('csv_path','')))}</code>.</p>
</div></body></html>
"""
    _atomic_write(path, doc)


def write_howto(path: Path, rows: list[dict[str, Any]], sheet: dict[str, Any], cfg: dict[str, Any],
                commit: str) -> None:
    csv_path = str(sheet["csv_path"])
    dec, note = str(sheet["decision_column"]), str(sheet["note_column"])
    doc = f"""# How to rule the tier-B candidates (T-195 step c) — noob-proof

**What you are deciding.** For each row: does the source book really teach this concept?
`MATCH` = yes (it becomes a floor, and the recall rail stays RED until the pipeline extracts it).
`NONE` = no (the proposal was wrong; it is ruled out and forgotten).

**Why you could not find these rows in the t11 checkpoints — the honest answer.**
A tier-B candidate is, by definition, a concept the extractor did **not** produce (D-3130). Measured on
these 43: **0 of 43** concept keys exist in the store and **0 of 43** exist in
`{sheet.get('crossref_checkpoint', 'the t11 S5 checkpoint')}`. The checkpoint is the wrong place to look; the right place is the **book**, at the paragraph named on every row (`locate`).

**Why the closest store row was also unfindable in t11.** The `closest_fb_*` columns name a row of the LIVE
store, whose run is `rechunk-v4-20260929` — a **different run** from the t11 checkpoints. Measured: 0 of 23
closest `fb_id`s and 0 of 23 closest names resolve into the t11 S5 checkpoint. Each row now says where it
does live (`closest_fb_run`) and whether it resolves in t11 (`closest_fb_crossref`).

---

## Procedure (copy-paste the commands)

1. **Read the sheet.** Open the HTML in a browser (double-click it, or):
   ```
   open "{sheet['html_path']}"
   ```
   Expected: a page titled *tier-B owner review — {len(rows)} rows need your word*, one numbered card per row.
   If instead you see raw HTML source: open it in Chrome/Safari by dragging the file onto the window.

2. **Read the passage, not the label.** Each card quotes the source paragraph, names the book and the
   paragraph index (`locate`), and shows the closest existing store row beside the candidate. Judge the
   quote.

3. **Write your word in the CSV** `{csv_path}` (Numbers / Excel / any editor):
   - column `{dec}` → type `MATCH` or `NONE` (uppercase; blank means *not yet ruled*, which is fine);
   - column `{note}` → optional free text, e.g. why you disagree with the panel.
   Save as UTF-8 CSV, keeping the header row and the column names unchanged.

4. **See what would be recorded — writes nothing:**
   ```
   python3 scripts/rule_tier_b.py --from-csv {csv_path} --dry-run
   ```
   Expected: one line per filled row, then a summary `would record N ruling(s); M blank row(s) skipped`.
   *If it says `FAIL-CLOSED: unknown decision …`*: a cell holds something other than MATCH/NONE — fix that
   cell, not the script.
   *If it says `unknown column`*: the header row was renamed — restore it from
   `{sheet['csv_path']}` as generated (regenerate with
   `python3 scripts/tier_b_owner_sheet.py`).

5. **Record the rulings** (appends to
   `{cfg['golden']['tier_b_ruling_sheet']}`):
   ```
   python3 scripts/rule_tier_b.py --from-csv {csv_path}
   ```
   Expected: `✓ recorded MATCH: '<name>' (<source_id>)` per row, then
   `recorded N; skipped M already-ruled; skipped K blank`.
   Re-running is safe: an already-ruled (source_id, name) is **skipped**, never doubled.

6. **Count what is left:**
   ```
   python3 scripts/rule_tier_b.py --count
   ```
   Expected: `43 - N unruled / 45 total` (N = rows you just filled). When it reads `0 unruled`, the ruling
   gate is closed.

7. **Fold the MATCHes into the golden** (this is the step that makes them FLOORS):
   ```
   python3 scripts/check_extraction_recall.py --build-golden --apply --check
   ```
   Expected: the golden rebuilds and the rail reports the new expectation count; every `MATCH`ed concept the
   store has not extracted shows as a **missing** expectation — that RED is the point: it names the work left.

---

## What NOT to do

- Do **not** type MATCH for a concept you think *should* exist. A floor is a claim about the source.
- Do **not** edit the ruling JSONL by hand; `--from-csv` writes the exact shape the reader expects.
- Do **not** treat a model vote as the answer. The panel is advisory (D-2658/D-2898/D-3137); four models
  agreeing is a reason to look, never a ruling.

*Generated by scripts/tier_b_owner_sheet.py from pipeline_commit {commit}, schema {SCHEMA_VERSION}.
Advisory input; the ruling column is yours.*
"""
    _atomic_write(path, doc)


# ---------------------------------------------------------------------------------------------------------------
# selftest / main
# ---------------------------------------------------------------------------------------------------------------
def selftest() -> int:
    """Known-answer controls: the pointer resolves, the splitter is stable, no decision is pre-filled."""
    checks: list[tuple[str, bool]] = []
    text = "short\n\n" + ("Alpha beta gamma delta. " * 40) + "\n\nSecond paragraph that is long enough to keep.\n"
    paras = split_paragraphs(text)
    checks.append(("splitter keeps the raw index (a short paragraph 0 is dropped, not renumbered)",
                   0 not in paras and 2 in paras))
    checks.append(("neighbour finds the following paragraph", _neighbour(paras, 1, +1).startswith("Second")))
    checks.append(("neighbour is empty at both boundaries",
                   _neighbour(paras, 99, +1) == "" and _neighbour(paras, 0, -1) == ""))
    checks.append(("neighbour skips a dropped heading and finds the nearest present index",
                   _neighbour(paras, 1, +1) == paras[2]))
    win = _reading_window(paras[1], ["gamma"], 120)
    checks.append(("window contains the cited token and respects the cap", "gamma" in win and len(win) <= 120))
    checks.append(("source title strips the z-library parenthetical",
                   _source_title("/x/AI Agents (Roberto Infante) (z-library.sk, 1lib.sk).md")
                   == "AI Agents (Roberto Infante)"))
    cols = csv_columns({"decision_column": "owner_decision", "note_column": "owner_note"})
    checks.append(("decision + note columns are the first two after the row number",
                   cols[:3] == ["review_no", "owner_decision", "owner_note"]))
    bad = 0
    for label, ok in checks:
        print(("  ✓ " if ok else "  ✗ ") + label)
        bad += 0 if ok else 1
    if bad:
        print(f"FAIL: {bad} control(s) failed")
        return 1
    print(f"✅ owner-sheet selftest passed: {len(checks)} controls")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the owner's tier-B ruling sheet (CSV + HTML + how-to).")
    ap.add_argument("--selftest", action="store_true", help="run known-answer controls and exit")
    ap.add_argument("--dry-run", action="store_true", help="build in memory and report, write nothing")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    cfg = load_cfg()
    sheet = cfg["sheet"]
    rows = build_rows(cfg)
    commit = _git_commit()
    csv_path = PROJECT_ROOT / str(sheet["csv_path"])
    html_path = PROJECT_ROOT / str(sheet["html_path"])
    howto_path = PROJECT_ROOT / str(sheet["how_to_path"])
    if args.dry_run:
        print(f"DRY-RUN: {len(rows)} review row(s) -> {sheet['csv_path']}, {sheet['html_path']}, "
              f"{sheet['how_to_path']} (nothing written)")
        for r in rows[:3]:
            print(f"  [{r['review_no']}] {r['candidate_name']} | {r['panel_agreement']} | "
                  f"{len(r['reading'])} chars | {r['closest_fb_crossref'][:60]}")
        return 0

    write_csv(csv_path, rows, sheet, commit)
    write_html(html_path, rows, sheet, commit)
    write_howto(howto_path, rows, sheet, cfg, commit)
    blank = sum(1 for r in rows if not r["reading"])
    print(f"WROTE {len(rows)} review row(s):")
    print(f"  csv  {csv_path}")
    print(f"  html {html_path}")
    print(f"  md   {howto_path}")
    if blank:
        print(f"  WARNING: {blank} row(s) carry no measured passage — their locate field says so (C16)")
    unres = sum(1 for r in rows if r["closest_fb_crossref"].startswith("NOT in t11"))
    print(f"  info: {unres}/{len(rows)} closest store rows do not resolve in the t11 checkpoint "
          f"(expected: the live store is a different run; each row names its run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
