#!/usr/bin/env python3
"""scripts/rederive_anchor_axes_v6.py — D-2820 anchor re-derivation harness (D-2839 pre-A/B referee).

WHY
---
The 201-row v8 discipline/domain authority (governance/discipline_anchor_rederived_v8_20261007.json)
was adjudicated against the PRE-D-2814 free-generation menu (menu v5). Menu v6 (D-2814/D-2815/D-2816)
changed the discipline slots, the domain slots and the abstention token to 'emerging', so the anchor's
discipline/domain axis is FROZEN-INVALID (D-2820) and a full-204 A/B (D-2767) against it would be CIRCULAR
(BUG-650). This harness re-derives BOTH menu-derived axes (discipline + domain) against menu v6 so the
output can serve as the D-2767 referee ONLY after owner sign-off (D-2839).

The depth axis is intentionally NOT re-derived here: menu v6 did not change the 4-way depth axis
(universal / cross-domain / domain / specialized), so the depth anchor (D-2760/D-274f/D-2611) stays valid.

PIPELINE (each stage fail-closed, C16)
--------------------------------------
  --plan         load + join text + render menu v6 + verify pins. NO inference, NO writes.
  --selftest     known-answer controls for the pure functions (stamp/adjudication/manifest). NO LLM/DB.
  --generate     classify each anchor against menu v6 (definition-anchored) -> candidate worklist.
                 GENERATOR is INPUT ONLY; the owner is the only ground truth (D-2839 criterion 2).
  --adjudicate   apply owner decisions (per-item override / accept-candidate) -> owner-finalized labels.
                 REFUSES to proceed if any row is left unadjudicated (never auto-finalize, D-2839 c2).
  --verify       second-coder (different model family, R5) + DeBERTa-NLI cross-check the owner labels.
                 Disagreements are SURFACED, never averaged and never auto-flip (D-2839 criterion 3).
  --finalize     stamp every cell per D-274d (anchor_version/menu_hash/taxonomy_version/coder/date/
                 abstention) + top-level menu_hash/answer_space_hash (live menu-v6 pins) -> write the
                 re-derived manifest. Exit non-zero unless the manifest passes the BUG-650 referee guard.

The owner runs --generate, adjudicates, then --adjudicate -> --verify -> --finalize. The finalize step
is the ONLY step that can flip D-2839 from PROPOSED to RATIFIED (a HUMAN gate this script cannot self-sign).

Config-first (C12): generator/second-coder model names, anchor version and the anchor/menu/db paths are
read from config/pipeline_config.yaml + config/taxonomy.yaml + config/menu_axis_hashes.yaml. No pin value
and no model name is hardcoded here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from pipeline.closed_menu import canonical_json, definition_anchored_block, render_closed_menu  # noqa: E402

DEFAULT_ANCHOR = REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json"
DEFAULT_STORE = REPO / "knowledge pipeline" / "maxwell.db"
TAXONOMY_YAML = REPO / "config" / "taxonomy.yaml"
PIPELINE_CFG = REPO / "config" / "pipeline_config.yaml"
PINS_YAML = REPO / "config" / "menu_axis_hashes.yaml"

ABSTENTION = "emerging"
NOISE_DROP_SOURCE = "noise_drop"  # D-2811: discipline/domain do NOT apply; excluded from re-derivation (BUG-698c / GATE-3)
_OUT_DIR = REPO / "governance"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _crash_safe_write(path: Path, payload: dict) -> None:
    """Write JSON crash-safely (C6): tempfile -> fsync -> os.replace, same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_stage4_config() -> dict:
    """Read the re-derivation keys from pipeline_config.yaml stage4 (C12)."""
    cfg = _load_yaml(PIPELINE_CFG)
    return cfg.get("stage4", {}) or {}


def load_pins() -> dict[str, str]:
    """Verify the live menu-v6 pins are reproducible from config (drift guard), then return them.

    Fail-closed (C16): if config/closed_menu_v7.json does not render to the declared live
    composite/answer-space pins, the re-derivation cannot certify against menu v7.
    """
    menu = render_closed_menu()
    live_composite = hashlib.sha256(canonical_json(menu).encode("utf-8")).hexdigest()
    declared = _load_yaml(PINS_YAML)
    want_composite = str(declared.get("composite_hash_live", "")).strip()
    want_answer = str(declared.get("answer_space_hash", "")).strip()
    if not want_composite or not want_answer:
        raise SystemExit(f"FAIL: {PINS_YAML.name} missing live pins (C16) — cannot certify menu v6.")
    if live_composite != want_composite:
        raise SystemExit(
            f"FAIL: menu drift — rendered composite {live_composite[:16]} != declared live pin "
            f"{want_composite[:16]} (D-277: the live menu must render to its pin before re-deriving)."
        )
    frozen = str(declared.get("composite_hash_frozen_pin", "")).strip()
    if frozen and live_composite == frozen:
        raise SystemExit("FAIL: live composite equals the frozen pin — menu-v6 certification is incoherent (C16).")
    return {
        "composite": live_composite,
        "answer_space": want_answer,
        "frozen_composite": frozen,
        "frozen_answer": str(declared.get("answer_space_hash_frozen_pin", "")).strip(),
    }


def load_taxonomy_version() -> str:
    """Return the taxonomy source version (single source: config/taxonomy.yaml)."""
    tax = _load_yaml(TAXONOMY_YAML)
    return str(tax.get("version") or tax.get("classification_version") or "unknown").strip()


def load_anchor_rows(path: Path) -> list[dict]:
    """Load the anchor rows, enforcing the declared count (count-drift guard)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("rows", [])
    declared = doc.get("total")
    if not rows:
        raise SystemExit(f"FAIL: anchor has no rows: {path}")
    if declared is not None and len(rows) != int(declared):
        raise SystemExit(f"FAIL: anchor drifted — {len(rows)} rows vs declared {declared}: {path}")
    return rows


def partition_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split anchor rows into re-derivable vs noise_drop (D-2811 / BUG-698c / GATE-3).

    noise_drop rows carry discipline=None + domains=[] and mean "no extractable object — the
    discipline/domain axes do NOT apply". They must be EXCLUDED from the re-derivation (the
    generator must never fabricate a discipline on a no-extractable-object row), and are instead
    preserved verbatim in the final manifest with their noise_drop provenance intact.
    Returns ``(rederive_rows, noise_rows)``, each in original relative order.
    """
    rederive: list[dict] = []
    noise: list[dict] = []
    for r in rows:
        if (r.get("discipline_source") or "") == NOISE_DROP_SOURCE:
            noise.append(r)
        else:
            rederive.append(r)
    return rederive, noise


def normalize_discipline(value: str) -> str:
    """GATE-3(b)/BUG-698b: an empty discipline on an abstained row means abstention, not an error.

    Normalize '' (or None) -> the 'emerging' abstention token so abstention is a first-class on-menu
    cell. The v8 anchor stored discipline='' with discipline_source='abstained' — an invalid off-menu
    value that the re-derivation must not re-mint.
    """
    v = (value or "").strip()
    return ABSTENTION if v == "" else v


def join_text(rows: list[dict], store: Path) -> list[dict]:
    """Join the classifier input text (definition/mechanism/boundary/consequence/source_text) by name.

    Mirrors scripts/discipline_conformance_gate.py load_anchor(): the anchor carries name+label but NOT
    the classifier input fields, so the text is joined from maxwell.db by collapsed-whitespace name.
    Fail-closed if any anchor row fails to join.
    """
    db = sqlite3.connect(str(store))
    cur = db.cursor()
    cur.execute("SELECT name, definition, mechanism, boundary, consequence, source_text FROM fbs")
    by_name = {_collapse(n): (d, m, b, c, s) for n, d, m, b, c, s in cur.fetchall()}
    db.close()
    out: list[dict] = []
    for r in rows:
        key = _collapse(r.get("name", ""))
        hit = by_name.get(key)
        if hit is None:
            raise SystemExit(f"FAIL: anchor row {r.get('item_id')} name not joinable to maxwell.db")
        definition, mechanism, boundary, consequence, source_text = hit
        out.append(
            {
                "item_id": r["item_id"],
                "name": r["name"],
                "definition": definition or "",
                "mechanism": mechanism or "",
                "boundary": boundary or "",
                "consequence": consequence or "",
                "source_text": source_text or "",
            }
        )
    return out


def _collapse(s: str) -> str:
    return " ".join((s or "").split())


def render_menu_v6() -> dict:
    """Render the menu-v6 definition-anchored block + the canonical label sets, fail-closed if empty."""
    block = definition_anchored_block()
    menu = render_closed_menu()
    disciplines = [e["value"] for e in menu["disciplines"] if e["value"] != ABSTENTION]
    domains = [e["value"] for e in menu["domains"] if e["value"] != ABSTENTION]
    if not disciplines or not domains or not block:
        raise RuntimeError("D-2814: definition-anchored menu v6 empty — fail closed (C16)")
    # fail-closed: every canonical label must carry a non-empty definition (definition-anchored)
    defs = {e["value"]: (e.get("definition") or "").strip() for e in menu["disciplines"] + menu["domains"]}
    missing_def = [v for v in disciplines + domains if not defs.get(v)]
    if missing_def:
        raise RuntimeError(f"menu v6 has labels without definitions: {missing_def[:5]} — cannot anchor (C16)")
    return {"menu": menu, "block": block, "disciplines": disciplines, "domains": domains, "defs": defs}


# ── Pure, unit-testable functions ────────────────────────────────────────────────────────────────


def build_cell_stamp(
    *,
    pins: dict[str, str],
    taxonomy_version: str,
    anchor_version: str,
    coder: str,
    second_coder: str,
    date: str,
    discipline_abstained: bool,
    domains_abstained: bool,
) -> dict:
    """Build the D-274d per-cell stamp (anchor_version/menu_hash/taxonomy_version/coder/date/abstention)."""
    return {
        "anchor_version": anchor_version,
        "menu_hash": pins["composite"],
        "answer_space_hash": pins["answer_space"],
        "taxonomy_version": taxonomy_version,
        "coder": coder,
        "date": date,
        "abstention": ABSTENTION,
        "discipline_abstained": bool(discipline_abstained),
        "domains_abstained": bool(domains_abstained),
        "second_coder": second_coder,
    }


def apply_owner_decisions(rows: list[dict], decisions: dict) -> list[dict]:
    """Apply owner decisions to candidate rows. Fail-closed: every row MUST be adjudicated.

    ``decisions`` maps item_id -> {"discipline": str, "domains": [str]} (an explicit owner label).
    A row not present in decisions raises — the owner is the only ground truth (D-2839 c2).
    """
    by_id = {r["item_id"]: r for r in rows}
    unknown = sorted(set(decisions) - set(by_id))
    if unknown:
        raise SystemExit(f"FAIL: owner decisions reference unknown item_ids {unknown[:5]} (C16)")
    missing = sorted(set(by_id) - set(decisions))
    if missing:
        raise SystemExit(
            f"FAIL: {len(missing)} rows unadjudicated (never auto-finalize, D-2839 c2): {missing[:5]}"
        )
    out: list[dict] = []
    for r in rows:
        d = decisions[r["item_id"]]
        if "discipline" not in d:
            raise SystemExit(f"FAIL: row {r['item_id']} owner decision is missing 'discipline' (D-2839 c2)")
        discipline = normalize_discipline(d.get("discipline"))
        domains = d.get("domains") or []
        if not isinstance(domains, list) or not domains:
            raise SystemExit(f"FAIL: row {r['item_id']} owner decision has no domains list")
        out.append(
            {
                **r,
                "discipline": discipline,
                "domains": [str(x).strip() for x in domains],
                "discipline_source": "owner_finalized",
                "domain_source": "owner_finalized",
            }
        )
    return out


def validate_on_menu(finalized: list[dict], menu: dict) -> None:
    """Fail-closed: every owner-finalized label must be ON the menu-v6 answer space (or the abstention token).

    BUG-653: an off-menu discipline that is actually a DOMAIN-axis value (e.g. 'urban planning')
    gets a targeted hint naming the axis confusion + the closest on-menu disciplines, so the
    owner self-corrects in one round instead of guessing.
    """
    disc_set = set(menu["disciplines"]) | {ABSTENTION}
    dom_set = set(menu["domains"]) | {ABSTENTION}
    for r in finalized:
        if r["discipline"] not in disc_set:
            raise SystemExit(_off_menu_discipline_hint(r["item_id"], r["discipline"], menu))
        off = [d for d in r["domains"] if d not in dom_set]
        if off:
            raise SystemExit(f"FAIL: row {r['item_id']} domains {off} are OFF menu v6 (C16)")


def _off_menu_discipline_hint(item_id: str, label: str, menu: dict) -> str:
    """BUG-653: build a targeted off-menu discipline message.

    If `label` is a DOMAIN-axis value, call out the axis confusion explicitly and suggest the
    closest on-menu disciplines (token overlap + difflib ratio). Otherwise suggest the closest
    disciplines from a plain off-menu label. Deterministic, no LLM, no network.
    """
    disciplines = list(menu["disciplines"])
    domains = set(menu["domains"])
    closest = _closest_labels(label, disciplines, k=4)
    abstain = f", or '{ABSTENTION}' if no discipline fits"
    if label in domains:
        return (
            f"FAIL: row {item_id} discipline {label!r} is OFF the discipline axis (C16). "
            f"HINT: {label!r} is a DOMAIN value, not a discipline — pick a discipline instead{abstain}. "
            f"Closest disciplines: {closest}."
        )
    return (
        f"FAIL: row {item_id} discipline {label!r} is OFF menu v6 (C16). "
        f"Closest disciplines: {closest}{abstain}."
    )


def _closest_labels(label: str, candidates: list[str], k: int = 4) -> list[str]:
    """Return the k closest candidate labels by normalized token overlap + sequence ratio.

    Token overlap dominates (captures 'urban planning' -> 'urban studies'/'urban design'); the
    difflib ratio breaks ties on near-spellings.
    """
    import difflib

    lw = label.lower()
    lt = set(lw.split())
    scored: list[tuple[float, str]] = []
    for c in candidates:
        cw = c.lower()
        ct = set(cw.split())
        denom = len(lt | ct) or 1
        overlap = len(lt & ct) / denom
        seq = difflib.SequenceMatcher(None, lw, cw).ratio()
        scored.append((0.6 * overlap + 0.4 * seq, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


def finalize_manifest(
    *,
    finalized: list[dict],
    pins: dict[str, str],
    taxonomy_version: str,
    anchor_version: str,
    coder: str,
    second_coder: str,
    run_id: str | None = None,
    noise_rows: list[dict] | None = None,
) -> dict:
    """Assemble the re-derived manifest: top-level menu-v6 pins + per-cell D-274d stamps.

    noise_drop rows are merged back verbatim (empty discipline/domains + noise_drop provenance,
    re-stamped to the live menu pins) so the manifest carries all declared rows without the
    re-derivation fabricating a discipline on them (GATE-3c / BUG-698c / D-2811).
    """
    date = _now()
    rows = []
    for r in finalized:
        cross = r.get("_crosscheck") or {}
        rows.append(
            {
                "item_id": r["item_id"],
                "name": r["name"],
                "discipline": r["discipline"],
                "domains": r["domains"],
                "discipline_source": r.get("discipline_source", "owner_finalized"),
                "domain_source": r.get("domain_source", "owner_finalized"),
                "_stamp": build_cell_stamp(
                    pins=pins,
                    taxonomy_version=taxonomy_version,
                    anchor_version=anchor_version,
                    coder=coder,
                    second_coder=second_coder,
                    date=date,
                    discipline_abstained=(r["discipline"] == ABSTENTION),
                    domains_abstained=(ABSTENTION in r["domains"]),
                ),
                "_crosscheck": cross,
            }
        )
    # GATE-3(c)/BUG-698c: preserve noise_drop rows verbatim — discipline/domain do NOT apply (D-2811).
    for r in noise_rows or []:
        rows.append(
            {
                "item_id": r["item_id"],
                "name": r["name"],
                "discipline": None,
                "domains": [],
                "discipline_source": NOISE_DROP_SOURCE,
                "domain_source": NOISE_DROP_SOURCE,
                "_stamp": build_cell_stamp(
                    pins=pins,
                    taxonomy_version=taxonomy_version,
                    anchor_version=anchor_version,
                    coder=coder,
                    second_coder=second_coder,
                    date=date,
                    discipline_abstained=True,
                    domains_abstained=True,
                ),
                "_crosscheck": {},
            }
        )

    def _row_index(r: dict) -> int:
        digits = "".join(c for c in str(r.get("item_id", "")) if c.isdigit())
        return int(digits) if digits else 0

    rows.sort(key=_row_index)
    return {
        "artifact_id": f"discipline_anchor_rederived_{anchor_version}_{run_id or _run_id()}",
        "total": len(rows),
        "menu_hash": pins["composite"],
        "answer_space_hash": pins["answer_space"],
        "taxonomy_version": taxonomy_version,
        "anchor_version": anchor_version,
        "abstention": ABSTENTION,
        "axes_rederived": ["discipline", "domains"],
        "depth_axis_untouched": "depth is NOT menu-derived (D-2820) and remains valid",
        "rows": rows,
        "_provenance": {
            "schema_version": "1.0",
            "generated_by": "scripts/rederive_anchor_axes_v6.py",
            "gen_model": "human_owner (adjudicated) — classifier output was INPUT only (D-2839 c2)",
            "decision": "D-2820",
            "date": date,
        },
    }


# ── Classify / cross-check (LLM + NLI; owner-gated stages) ───────────────────────────────────────


def _classify_prompt(fb: dict, block: str) -> str:
    """Build the definition-anchored menu-v6 classify prompt (discipline + domains only).

    Mirrors pipeline/stage4_merge.py's definition-anchored CLASSIFY_SYSTEM_PROMPT for the
    discipline/domains axes so the candidate labels are generated under the SAME menu the
    A/B will measure. Depth is deliberately excluded (not menu-derived).
    """
    json_instruction = (
        'Return ONLY a JSON object: {"discipline": "<CLOSED DISCIPLINE MENU label, verbatim, or '
        + repr(ABSTENTION)[1:-1]
        + '>", "domains": ["1-7 CLOSED DOMAIN MENU labels, verbatim, or '
        + repr(ABSTENTION)[1:-1]
        + '"]}'
    )
    return (
        "Classify this Foundation Block against the CLOSED menu below. Express every label as an "
        "EXACT verbatim entry from the menu — the menu definitions are the anchor. Do NOT invent a "
        "new, more-specific, or hyphenated label.\n\n"
        f"FB name: {fb['name']}\n"
        f"FB definition: {fb['definition']}\n"
        f"FB mechanism: {fb['mechanism']}\n"
        f"FB boundary: {fb['boundary']}\n"
        f"FB consequence: {fb['consequence']}\n\n"
        + block
        + "\n\n"
        + json_instruction
    )


def generate_candidates(rows: list[dict], menu: dict, model: str, limit: int | None) -> list[dict]:
    """Classify each anchor against menu v6 and attach candidate labels. LLM output is INPUT only."""
    from pipeline.omlx_call import call_omlx_json

    disc_set = set(menu["disciplines"]) | {ABSTENTION}
    dom_set = set(menu["domains"]) | {ABSTENTION}
    total = len(rows)
    print(f"generating candidate labels for {total} anchors (model={model})...", flush=True)
    out: list[dict] = []
    for i, r in enumerate(rows):
        if limit is not None and i >= limit:
            break
        res = call_omlx_json(_classify_prompt(r, menu["block"]), model=model)
        if isinstance(res, list):
            res = res[0] if res else {}
        if not isinstance(res, dict):
            raise SystemExit(f"FAIL: classifier returned no JSON for row {r['item_id']} (C16)")
        cand_disc = str(res.get("discipline") or "").strip()
        cand_doms = res.get("domains") or []
        if not isinstance(cand_doms, list):
            cand_doms = [cand_doms]
        # clamp candidates to the on-menu answer space; off-menu -> abstention (fail-closed, never free-gen)
        if cand_disc not in disc_set:
            cand_disc = ABSTENTION
        cand_doms = [d for d in cand_doms if d in dom_set] or [ABSTENTION]
        out.append({**r, "candidate_discipline": cand_disc, "candidate_domains": cand_doms})
        print(f"  [{i + 1}/{total}] {r['item_id']} -> {cand_disc} | {', '.join(cand_doms)}", flush=True)
    return out


def cross_check(finalized: list[dict], menu: dict, second_coder: str, limit: int | None) -> list[dict]:
    """Second-coder (different family, R5) + DeBERTa-NLI cross-check. Surfaces disagreements, never averages.

    The second coder re-classifies each FB and its verdict is recorded; DeBERTa-NLI scores the owner label's
    menu definition against the FB definition (premise). A contra-dominant or low-entail pair is surfaced
    as a disagreement — it NEVER flips the owner label (D-2839 c3).
    """
    from pipeline.omlx_call import call_omlx_json
    from pipeline.stage5_verify import NLIInferenceError, _nli_pair_scores

    defs = menu["defs"]
    out: list[dict] = []
    for i, r in enumerate(finalized):
        if limit is not None and i >= limit:
            out.append(r)
            continue
        res = call_omlx_json(_classify_prompt(r, menu["block"]), model=second_coder)
        if isinstance(res, list):
            res = res[0] if res else {}
        if not isinstance(res, dict):
            raise SystemExit(f"FAIL: second coder returned no JSON for row {r['item_id']} (C16)")
        sc_disc = str(res.get("discipline") or "").strip()
        # NLI: does the FB definition entail the owner label's menu definition?
        hyp = defs.get(r["discipline"])
        nli = {"entail": None, "neutral": None, "contra": None, "verdict": "skipped"}
        if hyp:
            premise = (r.get("definition") or "")[:2048]
            try:
                entail, neutral, contra = _nli_pair_scores(premise, hyp, raise_on_error=True)
                nli = {
                    "entail": round(float(entail), 4),
                    "neutral": round(float(neutral), 4),
                    "contra": round(float(contra), 4),
                    "verdict": "contra-dominant" if contra >= 0.5 else ("entailed" if entail >= neutral and entail >= contra else "weak"),
                }
            except NLIInferenceError as e:
                nli = {"entail": None, "neutral": None, "contra": None, "verdict": f"nli-error: {e}"}
        agreement = "agree" if sc_disc == r["discipline"] else "disagree"
        out.append(
            {
                **r,
                "_crosscheck": {
                    "second_coder_discipline": sc_disc,
                    "second_coder_model": second_coder,
                    "second_coder_agreement": agreement,
                    "nli": nli,
                },
            }
        )
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────────────────────────


def _worklist_path(run_id: str | None = None) -> Path:
    return _OUT_DIR / f"rederive_v6_worklist_{run_id or _run_id()}.json"


def _finalized_path(run_id: str | None = None) -> Path:
    return _OUT_DIR / f"rederive_v6_finalized_{run_id or _run_id()}.json"


def _verified_path(run_id: str | None = None) -> Path:
    return _OUT_DIR / f"rederive_v6_verified_{run_id or _run_id()}.json"


def _manifest_path(run_id: str | None = None, anchor_version: str = "v9") -> Path:
    return _OUT_DIR / f"discipline_anchor_rederived_{anchor_version}_{run_id or _run_id()}.json"


def _selftest() -> int:
    """Known-answer controls for the pure functions (stamp/adjudication/manifest + guard acceptance)."""
    pins = {"composite": "c" * 64, "answer_space": "a" * 64, "frozen_composite": "f" * 64, "frozen_answer": "g" * 64}
    stamp = build_cell_stamp(
        pins=pins, taxonomy_version="v5.7", anchor_version="v6", coder="owner",
        second_coder="gemma", date="2026-10-05T00:00:00+00:00",
        discipline_abstained=False, domains_abstained=False,
    )
    assert stamp["menu_hash"] == pins["composite"], "stamp menu_hash mismatch"
    assert stamp["abstention"] == ABSTENTION, "stamp abstention mismatch"
    rows = [
        {"item_id": "R001", "name": "a", "definition": "d", "mechanism": "m", "boundary": "b", "consequence": "c", "source_text": "s"},
        {"item_id": "R002", "name": "b", "definition": "d", "mechanism": "m", "boundary": "b", "consequence": "c", "source_text": "s"},
    ]
    decisions = {"R001": {"discipline": "physics", "domains": ["ai & agents"]},
                 "R002": {"discipline": "emerging", "domains": ["emerging"]}}
    final = apply_owner_decisions(rows, decisions)
    assert len(final) == 2 and final[0]["discipline"] == "physics"
    # missing adjudication must fail closed
    try:
        apply_owner_decisions(rows, {"R001": decisions["R001"]})
        assert False, "expected SystemExit on unadjudicated row"
    except SystemExit:
        pass
    menu = {"disciplines": ["physics"], "domains": ["ai & agents"]}
    validate_on_menu(final, menu)
    try:
        validate_on_menu([{**final[0], "discipline": "alchemy"}], menu)
        assert False, "expected SystemExit on off-menu label"
    except SystemExit:
        pass
    manifest = finalize_manifest(
        finalized=final, pins=pins, taxonomy_version="v5.7", anchor_version="v6",
        coder="owner", second_coder="gemma",
    )
    assert manifest["menu_hash"] == pins["composite"] and manifest["total"] == 2
    print("  OK stamp builder")
    print("  OK adjudication fail-closed (unadjudicated / off-menu)")
    # the manifest must be accepted as a menu-v6 referee by the BUG-650 guard, which
    # reads the REAL live pins from config — so this check uses the real pins.
    from pipeline.anchor_menu_guard import referee_menu_current_verdict

    real_pins = load_pins()
    real_manifest = finalize_manifest(
        finalized=final, pins=real_pins, taxonomy_version=load_taxonomy_version(),
        anchor_version="v6", coder="owner", second_coder="gemma",
    )
    verdict = referee_menu_current_verdict(real_manifest, label="selftest.json", axis="discipline")
    assert verdict["ok"], f"manifest rejected by guard: {verdict['reason']}"
    print("  OK manifest assembly + BUG-650 guard acceptance")

    # GATE-3 / BUG-698: noise_drop partition + ''->'emerging' normalization + noise preservation.
    noisy = [
        {"item_id": "R010", "name": "n1", "discipline_source": "noise_drop", "discipline": None, "domains": []},
        {"item_id": "R020", "name": "n2", "discipline_source": "noise_drop", "discipline": None, "domains": []},
        {"item_id": "R030", "name": "k1", "discipline_source": "abstained", "discipline": "", "domains": ["ai & agents"]},
    ]
    rederive, noise = partition_rows(noisy)
    assert [r["item_id"] for r in rederive] == ["R030"], "partition_rows must keep non-noise rows"
    assert [r["item_id"] for r in noise] == ["R010", "R020"], "partition_rows must isolate noise_drop rows"
    assert normalize_discipline("") == ABSTENTION and normalize_discipline("physics") == "physics", "normalize ''->emerging"
    # owner abstention via empty discipline -> 'emerging' (GATE-3b); missing key still fails closed
    abstain_final = apply_owner_decisions(
        [{"item_id": "R030", "name": "k1", "definition": "d", "mechanism": "m", "boundary": "b", "consequence": "c", "source_text": "s"}],
        {"R030": {"discipline": "", "domains": ["ai & agents"]}},
    )
    assert abstain_final[0]["discipline"] == ABSTENTION, "empty discipline must normalize to 'emerging'"
    try:
        apply_owner_decisions(
            [{"item_id": "R030", "name": "k1", "definition": "d", "mechanism": "m", "boundary": "b", "consequence": "c", "source_text": "s"}],
            {"R030": {"domains": ["ai & agents"]}},
        )
        assert False, "expected SystemExit on missing discipline key"
    except SystemExit:
        pass
    # noise rows preserved verbatim (empty discipline/domains + noise_drop provenance) in the manifest
    noise_manifest = finalize_manifest(
        finalized=abstain_final, pins=real_pins, taxonomy_version=load_taxonomy_version(),
        anchor_version="v9", coder="owner", second_coder="gemma", noise_rows=noise,
    )
    assert noise_manifest["total"] == 3, f"manifest must carry rederive + noise rows (got {noise_manifest['total']})"
    by_id = {r["item_id"]: r for r in noise_manifest["rows"]}
    assert by_id["R010"]["discipline"] is None and by_id["R010"]["domains"] == [], "noise row must stay empty"
    assert by_id["R010"]["discipline_source"] == NOISE_DROP_SOURCE, "noise row must keep noise_drop provenance"
    assert [r["item_id"] for r in noise_manifest["rows"]] == ["R010", "R020", "R030"], "manifest order must be numeric item_id"
    print("  OK noise_drop partition + ''->emerging normalization + noise preservation (GATE-3/BUG-698)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="D-2820 anchor re-derivation harness (menu v6)")
    ap.add_argument("--anchor", default=None)
    ap.add_argument("--store", default=None)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--adjudicate", action="store_true")
    ap.add_argument("--decisions", default=None, help="owner decisions JSON {item_id: {discipline, domains}}")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--finalize", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    s4 = load_stage4_config()
    anchor_path = Path(args.anchor or s4.get("anchor_rederive_input_anchor") or str(DEFAULT_ANCHOR))
    store = Path(args.store or str(DEFAULT_STORE))
    generator = str(s4.get("anchor_rederive_generator_model") or s4.get("discipline_model") or "gpt-oss-20b-MXFP4-Q8")
    second_coder = str(s4.get("anchor_rederive_second_coder_model") or "gemma-4-E4B-it-MLX-4bit")
    anchor_version = str(s4.get("anchor_rederive_anchor_version") or "v6")
    if generator == second_coder:
        raise SystemExit("FAIL: generator == second coder (R5: generator != verifier) — set distinct models in config")

    pins = load_pins()
    taxonomy_version = load_taxonomy_version()
    menu = render_menu_v6()
    rows = load_anchor_rows(anchor_path)
    rederive_rows, noise_rows = partition_rows(rows)
    joined = join_text(rederive_rows, store)

    run_id = (args.run_id or _run_id()).strip()
    if not run_id or any(c in run_id for c in ("/", "\\")):
        raise SystemExit(f"FAIL: invalid --run-id {run_id!r} (no path separators)")

    if args.plan:
        print(f"anchor: {anchor_path}  ({len(joined)} rows re-derivable, {len(noise_rows)} noise_drop excluded)")
        print(f"noise_drop excluded (discipline/domain do NOT apply, D-2811): {[r['item_id'] for r in noise_rows]}")
        print(f"live menu: {len(menu['disciplines'])} disciplines, {len(menu['domains'])} domains, abstention='{ABSTENTION}'")
        print(f"composite pin: {pins['composite'][:16]}  answer-space pin: {pins['answer_space'][:16]}")
        print(f"taxonomy_version: {taxonomy_version}  anchor_version: {anchor_version}")
        print(f"generator: {generator}   second coder: {second_coder}  (families distinct: {generator != second_coder})")
        print("  DRY-RUN OK — ready for: --generate -> owner adjudicate -> --adjudicate -> --verify -> --finalize")
        return 0

    if args.generate:
        cands = generate_candidates(joined, menu, generator, args.limit)
        _crash_safe_write(_worklist_path(run_id), {"total": len(cands), "generator_model": generator, "rows": cands})
        print(f"wrote candidate worklist ({len(cands)} re-derivable rows; {len(noise_rows)} noise_drop excluded) -> {_worklist_path(run_id).name}")
        print("NEXT: owner adjudicates every re-derivable row, then: --adjudicate --decisions <file>")
        return 0

    if args.adjudicate:
        if not args.decisions:
            raise SystemExit("FAIL: --adjudicate requires --decisions <owner JSON> (never auto-finalize, D-2839 c2)")
        dec = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
        final = apply_owner_decisions(joined, dec)
        validate_on_menu(final, menu)
        _crash_safe_write(_finalized_path(run_id), {"total": len(final), "rows": final})
        print(f"wrote owner-finalized labels ({len(final)} rows, all on menu v6) -> {_finalized_path(run_id).name}")
        print("NEXT: --verify (second coder + DeBERTa-NLI cross-check)")
        return 0

    if args.verify:
        src = _finalized_path(run_id)
        if not src.exists():
            raise SystemExit(f"FAIL: {src.name} missing — run --adjudicate first")
        final = json.loads(src.read_text(encoding="utf-8"))["rows"]
        verified = cross_check(final, menu, second_coder, args.limit)
        _crash_safe_write(_verified_path(run_id), {"total": len(verified), "rows": verified})
        n_disagree = sum(1 for r in verified if (r.get("_crosscheck") or {}).get("second_coder_agreement") == "disagree")
        print(f"wrote verified rows ({len(verified)}) -> {_verified_path(run_id).name}; second-coder disagreements surfaced: {n_disagree}")
        print("NEXT: --finalize (stamp + write the re-derived manifest)")
        return 0

    if args.finalize:
        src = _verified_path(run_id)
        if not src.exists():
            raise SystemExit(f"FAIL: {src.name} missing — run --verify first")
        verified = json.loads(src.read_text(encoding="utf-8"))["rows"]
        manifest = finalize_manifest(
            finalized=verified, pins=pins, taxonomy_version=taxonomy_version,
            anchor_version=anchor_version, coder="owner", second_coder=second_coder,
            run_id=run_id, noise_rows=noise_rows,
        )
        # the re-derived manifest MUST be a valid menu-v6 referee (BUG-650 guard)
        from pipeline.anchor_menu_guard import assert_referee_menu_current

        assert_referee_menu_current(manifest, label=_manifest_path(run_id, anchor_version).name, axis="discipline")
        out = _manifest_path(run_id, anchor_version)
        if out.exists():
            raise SystemExit(f"REFUSED: {out.name} exists — a re-derived anchor is minted once (I2); use --run-id for a new run")
        _crash_safe_write(out, manifest)
        print(f"wrote re-derived anchor -> {out.name} (menu-v6 stamped; guard PASSED)")
        print("D-2839 may now flip PROPOSED -> RATIFIED ONLY after owner sign-off (human gate).")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
