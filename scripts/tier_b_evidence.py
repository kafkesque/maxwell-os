#!/usr/bin/env python3
"""tier_b_evidence.py — the MEASURED sheet the owner rules tier-B FROM (T-195 / D-3100 / D-3130).

WHY THIS EXISTS. A tier-B ruling is FLOORED: `config/extraction_recall.yaml#floors.expectation_recall` is
1.0 and a MATCH folds the candidate into the floored expectation set keyed by (source_id, concept_key).
So a wrong MATCH leaves the recall rail permanently RED until the concept is extracted, and a wrong NONE
loses the concept silently — both are unrecoverable without a human noticing. A ruling must therefore rest
on a READING, not on a recollection (D-3100).

WHAT THIS SCRIPT DOES *NOT* DO (measured, not assumed — 2026-10-23):
  * It does not ask a model for a verdict. The proposer (Qwen3-Coder) is the family that already wrote the
    candidates; asking it again measures its agreement with itself. BUG-053 is the standing finding that an
    open-ended delegated judgement hallucinates, and D-2658 is the standing rule that a two-model agreement
    is ADVISORY ONLY — it never writes a ruling. A model opinion cannot be a certification (D-2898).
  * It does not borrow the re-anchor bridge's question. `adjudicate_reanchor_two_model.py` (D-3116/D-2658)
    asks "is this already-certified label present in the STORE under another name?" and answers
    MATCH(fb_id)/NONE. Tier-B asks TWO OTHER questions, and only these two are measured here:
      Q1 GROUNDING — does this SOURCE contain this concept at all? (a scan of the bytes can answer; a third
         LLM cannot answer better than the bytes it would have to read)
      Q2 NOVELTY   — is it absent from the STORE for THIS source? (exact token identity already skipped the
         candidate via concept_key; a PARAPHRASE of a stored row is what this cosine measures)

WHAT IT MEASURES, per candidate (deterministic except the embedding dot product):
  * name_verbatim_hits      occurrences of the folded name in the folded source text
  * name_tokens_present     k/n of `content_tokens(name)` (pipeline/dedup_identity — the SAME token space
                            concept_key mints from) found in the source, and which are MISSING
  * excerpt                 the source paragraph with the best coverage of those tokens (the reading)
  * store_best              bge-m3 cosine of the candidate name against the store rows of THAT source,
                            top 3 as (name, fb_id, cos) — bge-m3 is the SAME non-LLM instrument the re-anchor
                            triage used, whose errors are decorrelated from a generator's

C12: the artifact path and the excerpt cap load from config/extraction_recall.yaml — never a literal here.
C6: crash-safe write (tempfile -> fsync -> os.replace). R14: schema_version / gen_model / pipeline_commit.
Cost: zero generation; one embedding batch + local text math. Exit: 0 clean | 1 fatal | 2 OWED (loud).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home

CONFIG_PATH = ROOT / "config" / "extraction_recall.yaml"

EXIT_OK = 0
EXIT_FATAL = 1
EXIT_OWED = 2

SCHEMA_VERSION = "1"
ARTIFACT_ID = "EXTRACTION-RECALL-TIER-B-EVIDENCE"
TOP_STORE_MATCHES = 3


def load_cfg() -> dict[str, Any]:
    """Load `extraction_recall` and REFUSE a config that omits the block this instrument writes to."""
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = (data or {}).get("extraction_recall")
    if not isinstance(cfg, dict):
        raise SystemExit(f"FAIL-CLOSED: {CONFIG_PATH.name} has no extraction_recall block (C12)")
    block = cfg.get("tier_b_evidence")
    if not isinstance(block, dict) or not str(block.get("path") or "").strip():
        raise SystemExit(
            "FAIL-CLOSED: extraction_recall.tier_b_evidence.path is NOT declared (C12 — a derived "
            "artifact needs a declared home, never a CLI default)"
        )
    for key in ("max_excerpt_chars", "prefer_explanatory_chars"):
        if key not in block:
            raise SystemExit(f"FAIL-CLOSED: extraction_recall.tier_b_evidence.{key} is NOT declared (C12)")
    return cfg


def semantic_near_threshold() -> float:
    """Return the store's OWN declared "semantically near" cosine (stage4), never an invented one.

    Quoting this band is the difference between evidence and tuning: 0.8 is the threshold the pipeline
    already uses to call two rows semantically near, so a candidate at or above it is close to something
    the store already carries for that source — evidence AGAINST a MATCH, not proof against it.
    """
    data = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
    block = (data or {}).get("stage4") or {}
    if "semantic_near_threshold" not in block:
        raise SystemExit("FAIL-CLOSED: stage4.semantic_near_threshold is NOT declared (C12)")
    return float(block["semantic_near_threshold"])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL sheet, fail-closed on a non-JSON line (a malformed sheet must not read as empty)."""
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"FAIL-CLOSED: {path.name}:{i} is not valid JSONL: {exc} (C16)") from exc
    return rows


def store_rows_for_sources(db_path: Path, source_ids: set[str]) -> dict[str, list[dict[str, str]]]:
    """Return {source_id: [{fb_id, name}, ...]} for the store rows of each source (read-only)."""
    from pipeline.dedup_identity import source_set

    out: dict[str, list[dict[str, str]]] = {sid: [] for sid in source_ids}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for fb_id, name, raw in conn.execute("select fb_id, name, source_ids from fbs"):
            for sid in source_set(raw):
                if sid in out:
                    out[sid].append({"fb_id": str(fb_id), "name": str(name or "")})
    finally:
        conn.close()
    return out


def paragraphs_with_tokens(text: str) -> list[tuple[int, str, set[str]]]:
    """Split source text into (index, paragraph, token set) once per source — the excerpt search space."""
    import re

    out: list[tuple[int, str, set[str]]] = []
    for idx, para in enumerate(re.split(r"\n\s*\n", text)):
        clean = " ".join(para.split())
        if len(clean) < 40:  # a heading or a page number is not evidence (a reading must be a passage)
            continue
        out.append((idx, clean, set(re.findall(r"[a-z0-9]+", clean.lower()))))
    return out


def is_prose(para: str) -> bool:
    """Return True when a passage reads as ARGUMENT rather than as a table-of-contents or bullet fragment.

    MEASURED (2026-10-23): markdown books split into list items at blank lines, so the highest token coverage
    often lands on a TOC entry ("LangChain's modular architecture and components"). That line IS evidence of
    PRESENCE — which is exactly what a tier-B ruling certifies — but it explains nothing, so a prose passage
    with equal coverage is the better reading and the owner is told which kind they are looking at.
    """
    head = para.lstrip()[:2]
    if head.startswith(("-", "*", "#", "|", ">")) or "{#" in para[:60]:
        return False
    return ". " in para or para.rstrip().endswith(".")


def _window_on_match(para: str, tokens: list[str], max_chars: int) -> str:
    """Cut a readable window AROUND the first matched concept token, never off the end of a long paragraph.

    MEASURED (2026-10-23): truncating a long paragraph at its first max_chars characters showed a passage
    whose matched tokens sat beyond the cut — the owner would read "evidence" that does not contain the
    words it is cited for. A citation must contain its own evidence.
    """
    import re

    if len(para) <= max_chars:
        return para
    first = None
    for tok in sorted(tokens, key=len, reverse=True):  # longest token first: the most specific anchor
        m = re.search(rf"\b{re.escape(tok)}\b", para.lower())
        if m and (first is None or m.start() < first):
            first = m.start()
    start = 0 if first is None else max(0, first - max_chars // 4)
    if start + max_chars >= len(para):
        start = max(0, len(para) - max_chars)
    end = start + max_chars
    pre = "…" if start > 0 else ""
    post = "…" if end < len(para) else ""
    budget = max_chars - len(pre) - len(post)  # the CAP includes its own ellipses: a citation may not overflow it
    out = para[start:start + budget] if budget > 0 else para[start:start + max_chars]
    return (pre + out + post).strip()


def measure_grounding(name: str, rationale: str, text: str, folded: str,
                      paras: list[tuple[int, str, set[str]]], max_chars: int,
                      explanatory_chars: int) -> dict[str, Any]:
    """Measure whether the SOURCE grounds this candidate, and return the best-matching passage.

    Grounding is reported as counts and a quote — NEVER as a verdict: a label may legitimately paraphrase
    the passage it names ("Prompt Engineering as a Design Discipline" need not appear verbatim), so a low
    token count is a reading to weigh, not a ruling.
    """
    from pipeline.dedup_identity import content_tokens, normalize_name

    tokens = content_tokens(name)
    missing = [t for t in tokens if t not in folded]
    present = len(tokens) - len(missing)
    rationale_tokens = [t for t in content_tokens(rationale) if t not in set(tokens)][:12]

    # Rank the reading by EVIDENTIAL WEIGHT, not by first mention: a heading that merely repeats both
    # tokens ("Why Kennedy's goal was a proximate and strategic objective") is a weaker reading than the
    # passage that EXPLAINS them, so ties on token coverage break toward rationale coverage and then toward
    # a substantial passage (capped — beyond a few hundred chars extra length stops adding evidence).
    best: tuple[int, int, int, int, int] | None = None  # (-hits, not_prose, -rat, -length, idx)
    best_para: dict[int, str] = {}
    for idx, para, ptoks in paras:
        hits = sum(1 for t in tokens if t in ptoks)
        if hits == 0:
            continue
        best_para[idx] = para
        rat = sum(1 for t in rationale_tokens if t in ptoks)
        key = (-hits, 0 if is_prose(para) else 1, -rat, -min(len(para), explanatory_chars), idx)
        if best is None or key < best:
            best = key
    excerpt = ""
    excerpt_idx: int | None = None
    excerpt_hits = 0
    excerpt_kind = "none"
    if best is not None:
        excerpt_hits = -best[0]
        excerpt_idx = best[4]
        excerpt_kind = "fragment/list" if best[1] else "prose"
        para = best_para[excerpt_idx]
        excerpt = _window_on_match(para, tokens, max_chars)
    return {
        "name_verbatim_hits": folded.count(normalize_name(name)) if normalize_name(name) else 0,
        "name_tokens": tokens,
        "name_tokens_present": f"{present}/{len(tokens)}",
        "name_tokens_missing": missing,
        "excerpt_index": excerpt_idx,
        "excerpt_name_coverage": f"{excerpt_hits}/{len(tokens)}",
        "excerpt_kind": excerpt_kind,
        "excerpt": excerpt,
    }


def measure_novelty(name: str, rows: list[dict[str, str]], cache: dict[str, Any]) -> dict[str, Any]:
    """Measure how close this candidate is to a store row of the SAME source (bge-m3 cosine, top N).

    A high cosine against a stored row means the concept is already carried for this source under another
    label (the store is not missing it) — that is evidence against a MATCH, never proof. A low maximum on a
    source with many rows is evidence that the concept is genuinely absent.
    """
    if not rows:
        return {"store_rows_for_source": 0, "store_best": [], "store_novelty": "NO STORE ROWS for this source"}
    try:
        import numpy as np

        from pipeline.embeddings import embed_texts_bge_m3
    except Exception as exc:  # C16: report, never degrade silently
        return {"store_rows_for_source": len(rows), "store_best": [],
                "store_novelty": f"NOT MEASURED: embeddings unavailable ({type(exc).__name__}: {exc})"}
    if "store" not in cache:
        cache["store"] = embed_texts_bge_m3([r["name"] for r in rows])
    if name not in cache:
        cache[name] = embed_texts_bge_m3([name])[0]
    sims = cache["store"] @ np.asarray(cache[name])
    order = np.argsort(-sims)[:TOP_STORE_MATCHES]
    return {
        "store_rows_for_source": len(rows),
        "store_best": [
            {"name": rows[int(i)]["name"], "fb_id": rows[int(i)]["fb_id"], "cos": round(float(sims[int(i)]), 4)}
            for i in order
        ],
    }


def build(cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the evidence envelope for EVERY tier-B candidate (ruled ones included: a ruling leaves a trace)."""
    from pipeline.dedup_identity import concept_key, normalize_name
    from pipeline.stamp import get_pipeline_commit
    from scripts.propose_tier_b import resolve_source_files, window_sha16, windowize

    golden = cfg["golden"]
    sheet = ROOT / str(golden.get("tier_b_sheet") or "")
    if not sheet.exists():
        raise SystemExit(f"FAIL-CLOSED: tier_b_sheet declared but absent: {sheet} (C16)")
    cands = read_jsonl(sheet)
    if not cands:
        raise SystemExit(f"FAIL-CLOSED: {sheet.name} holds no candidate — nothing to measure")

    ev = cfg["tier_b_evidence"]
    max_chars = int(ev["max_excerpt_chars"])
    explanatory = int(ev["prefer_explanatory_chars"])
    source_ids = {str(c["source_id"]) for c in cands}
    files = resolve_source_files(sorted(source_ids))
    store = store_rows_for_sources(ROOT / str(cfg["store"]), source_ids)

    cache: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    owed: list[str] = []
    warnings: list[str] = []
    window_chars = int(cfg["proposer"]["max_window_chars"])
    for cand in cands:
        sid = str(cand["source_id"])
        name = str(cand.get("name") or "").strip()
        rationale = str(cand.get("rationale") or "").strip()
        if not name:
            raise SystemExit(f"FAIL-CLOSED: candidate with empty name for {sid} (D-3034)")
        row: dict[str, Any] = {
            "source_id": sid,
            "name": name,
            "concept_key": concept_key(name),
            "rationale": rationale,
        }
        path = files.get(sid)
        if not path:
            row["grounding"] = {"source_file": "NOT RESOLVED", "name_tokens_present": "0/0",
                                "name_tokens_missing": [], "excerpt": ""}
            owed.append(f"{sid}: source file NOT RESOLVED (grounding not measured)")
        else:
            text = artifact_encoding.open_artifact(Path(path), ROOT).read()  # D-2646/BUG-511: no silent U+FFFD
            folded = normalize_name(text)
            grounding = measure_grounding(name, rationale, text, folded,
                                          paragraphs_with_tokens(text), max_chars, explanatory)
            grounding["source_file"] = str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else str(path)
            grounding["source_chars"] = len(text)
            row["grounding"] = grounding
            # BUG-985: a candidate that names the window it came from gets that claim CHECKED, not trusted —
            # the index is deterministic but the bytes may have been re-converted under it.
            if isinstance(cand.get("window_index"), int):
                ws = windowize(text, window_chars)
                wi = int(cand["window_index"])
                if wi >= len(ws):
                    warnings.append(f"{sid}/{name}: cited window {wi} is beyond the source's {len(ws)} window(s)")
                    row["cited_window"] = {"index": wi, "verified": False, "reason": "INDEX OUT OF RANGE"}
                else:
                    ok = str(cand.get("window_sha16") or "") == window_sha16(ws[wi])
                    row["cited_window"] = {"index": wi, "sha16": str(cand.get("window_sha16") or ""),
                                           "verified": ok}
                    if not ok:
                        warnings.append(f"{sid}/{name}: cited window {wi} does not match its sha16 — the source "
                                        f"bytes changed since the proposal; the whole-source scan below is authoritative")
        row.update(measure_novelty(name, store.get(sid, []), cache))
        if str(row.get("store_novelty") or "").startswith("NOT MEASURED"):
            owed.append(f"{sid}/{name}: store novelty NOT MEASURED")
        rows.append(row)

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "gen_model": "none (deterministic text math; bge-m3 embeddings for store cosine — no LLM verdict)",
        "pipeline_commit": get_pipeline_commit(),
        "authority": "ADVISORY EVIDENCE ONLY (D-2658/D-2898): it carries no ruling and certifies nothing. "
                     "The owner's MATCH/NONE in the ruling sheet is the only authority.",
        "method": {
            "token_space": "pipeline.dedup_identity.content_tokens — the SAME tokens concept_key mints from",
            "grounding": "folded-name occurrences + concept-token coverage + the best-covering source paragraph",
            "novelty": f"bge-m3 cosine of the candidate name vs the store rows of THAT source (top {TOP_STORE_MATCHES})",
            "excerpt_cap_chars": max_chars,
            "prefer_explanatory_chars": explanatory,
            "reference_band": {
                "semantic_near_threshold": semantic_near_threshold(),
                "source": "config/pipeline_config.yaml#stage4.semantic_near_threshold (QUOTED, not invented)",
                "meaning": "at/above this cosine a candidate is as close to a stored row of its source as the "
                           "pipeline already calls 'semantically near' — evidence AGAINST a MATCH, never proof",
            },
        },
        "owed": owed,
        "warnings": warnings,
        "rows": rows,
    }


def write_envelope(path: Path, envelope: dict[str, Any]) -> None:
    """Crash-safe write (C6): tempfile in the same directory -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(envelope, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def print_table(envelope: dict[str, Any], ruled: set[tuple[str, str]]) -> None:
    """Print one line per candidate: the numbers an owner can rule from without opening another file."""
    band = float(envelope["method"]["reference_band"]["semantic_near_threshold"])
    print(f"reference band: the store's declared semantic_near_threshold = {band} (a '≈' row is at/above it)")
    print(f"{'':2} {'concept':52} {'src tokens':>10} {'verb':>4} {'store best (cos)':>44}")
    for row in envelope["rows"]:
        key = (row["source_id"], row["name"])
        mark = "  " if key in ruled else "• "
        g = row.get("grounding") or {}
        best = (row.get("store_best") or [{}])[0]
        best_s = f"{best.get('cos')} {str(best.get('name'))[:30]}" if best else "—"
        if best and float(best.get("cos") or 0.0) >= band:
            best_s = f"≈ {best_s}"
        print(f"{mark}{row['name'][:52]:52} {str(g.get('name_tokens_present')):>10} "
              f"{str(g.get('name_verbatim_hits')):>4} {best_s:>44}")
    print("\n• = still unruled. verb = occurrences of the verbatim name in the source; "
          "src tokens = concept tokens found in the source; store best = closest store row of that source.")


def selftest() -> int:
    """Known-answer controls: the measurement must SEE a grounded concept and a near-duplicate store row."""
    text = (
        "Chapter 2. Strategy is not a goal.\n\n"
        "The kernel of strategy is a diagnosis, a guiding policy, and coherent action. A good strategy "
        "identifies the one crucial obstacle and concentrates effort against it.\n\n"
        "Chapter 3. Bad strategy is fluff.\n"
    )
    paras = paragraphs_with_tokens(text)
    from pipeline.dedup_identity import content_tokens, normalize_name

    g = measure_grounding("The Kernel of Strategy", "defines the kernel", text, normalize_name(text), paras, 120, 800)
    assert g["name_verbatim_hits"] >= 1, f"selftest: verbatim name not seen: {g}"
    assert "kernel" in g["name_tokens"] and "kernel" not in g["name_tokens_missing"], g
    assert "kernel" in g["excerpt"].lower(), f"selftest: excerpt did not land on the grounding passage: {g}"
    assert len(g["excerpt"]) <= 120, "selftest: excerpt cap not respected"

    miss = measure_grounding("Quantum Chromodynamic Confinement", "", text, normalize_name(text), paras, 120, 800)
    assert miss["name_verbatim_hits"] == 0 and miss["excerpt"] == "", f"selftest: absence not measured: {miss}"
    assert set(miss["name_tokens_missing"]) == set(content_tokens("Quantum Chromodynamic Confinement"))

    # novelty: a self-match must score ~1.0 and a distant concept clearly lower (no embedding service needed)
    import numpy as np

    class _Cache(dict):
        pass

    def fake_embed(texts: list[str]) -> Any:
        vecs = []
        for t in texts:
            v = np.zeros(8, dtype=np.float32)
            for tok in content_tokens(t):
                v[hash(tok) % 8] += 1.0
            n = float(np.linalg.norm(v)) or 1.0
            vecs.append(v / n)
        return np.stack(vecs)

    rows = [{"fb_id": "a" * 64, "name": "The Kernel of Strategy"}]
    cache: dict[str, Any] = {"store": fake_embed([r["name"] for r in rows])}
    cache["The Kernel of Strategy"] = fake_embed(["The Kernel of Strategy"])[0]
    import pipeline.embeddings as _emb

    real = _emb.embed_texts_bge_m3
    _emb.embed_texts_bge_m3 = fake_embed  # type: ignore[assignment]
    try:
        nov = measure_novelty("The Kernel of Strategy", rows, cache)
        assert abs(float(nov["store_best"][0]["cos"]) - 1.0) < 1e-6, nov
        nov2 = measure_novelty("Designing With Slime Mould", rows, cache)
        assert float(nov2["store_best"][0]["cos"]) < 1.0, nov2
    finally:
        _emb.embed_texts_bge_m3 = real

    assert paragraphs_with_tokens("tiny\n\n" + "x" * 60) != [], "selftest: a real passage must be kept"
    assert paragraphs_with_tokens("hi\n") == [], "selftest: a heading must not count as a passage"
    print("✅ tier_b_evidence selftest passed: grounding seen, absence seen, excerpt cap, novelty self-match 1.0")
    return EXIT_OK


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return EXIT_OK
    if "--selftest" in argv:
        return selftest()
    cfg = load_cfg()
    envelope = build(cfg)
    out_path = ROOT / str(cfg["tier_b_evidence"]["path"])
    if "--dry-run" in argv:
        print(json.dumps({k: v for k, v in envelope.items() if k != "rows"}, indent=2))
        print(f"preview only ({len(envelope['rows'])} row(s)); re-run with no flag to write {out_path.name}")
        ruled: set[tuple[str, str]] = set()
    else:
        write_envelope(out_path, envelope)
        ruled_rel = str(cfg["golden"].get("tier_b_ruling_sheet") or "")
        ruled = set()
        if ruled_rel and (ROOT / ruled_rel).exists():
            ruled = {(str(r["source_id"]), str(r["name"])) for r in read_jsonl(ROOT / ruled_rel)}
        print(f"wrote {len(envelope['rows'])} evidence row(s) to {out_path.relative_to(ROOT)}")
    print_table(envelope, ruled)
    for line in envelope.get("warnings") or []:
        print(f"WARNING: {line}")
    if envelope["owed"]:
        print(f"\nOWED ({len(envelope['owed'])}): a reading is missing — the owner should not rule from a hole")
        for line in envelope["owed"]:
            print(f"  - {line}")
        return EXIT_OWED
    print("\nADVISORY EVIDENCE ONLY — no verdict is recorded here; the owner's ruling is the authority "
          "(D-2658/D-2898).")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
