#!/usr/bin/env python3
"""scripts/bug695_recalibrate.py — BUG-695 D2547 recalibration + per_label repopulation.

FAIL-CLOSED one-invocation wrapper for BUG-695 steps 3–4 (safe-prep artifact; do
NOT run until RATIFY-2 / D-2727 has re-classified the corpus to v9 — the G3 gate
enforces this).

Step 3 (recalibrate): regenerate the two label audits against the v9-reclassified
canonical corpus, then rebuild the D2547 calibration table:
    1. pipeline/nli_label_audit.py --axis both   (local DeBERTa NLI — no OMLX)
    2. scripts/knn_label_disagreement.py          (bge-m3 via Ollama; advisory)
    3. scripts/build_mislabel_triage.py           -> governance/d2547_calibration.json
Step 4 (populate + verify): write the per_label block and assert coverage:
    4. scripts/populate_semantic_error_thresholds.py --apply
    5. verify no canonical label is stamped 0.0 from MISSING calibration data.

Why this wrapper exists (the naive re-run hazard):
    populate_semantic_error_thresholds.py computes
        error_rate(label) = nli_contradict(label) / nli_total(label)
    When a canonical label is ABSENT from d2547_calibration.json (or nli_total == 0),
    the numerator is 0 and the rate collapses to 0.0 — a FALSE ZERO that reads as
    "never mislabeled" when the truth is "never measured". A naive --apply therefore
    silently stamps 0.0 on every newly-ratified v9 label (e.g. marketing,
    research practice). This wrapper fails closed on that condition instead of
    emitting a misleading zero.

Preflight gates (all fail-closed; a failed gate blocks --apply):
    G1  taxonomy_v5.yaml == taxonomy_v9.yaml (the four downstream scripts read the
        misnamed "v5" file — if it ever diverges from v9 we must not silently
        calibrate against a stale taxonomy).
    G2  closed_menu_v9.json and taxonomy_v9.yaml agree up to the 'emerging'
        sentinel (no ontology drift between the D-2900 single pointer and the
        working snapshot).
    G3  DB contains no canonical-discipline value outside taxonomy_v9 (RATIFY-2
        re-classification is complete — no pre-v9 leftovers like visual semiotics,
        information retrieval, computational theory).
    G4  Ollama bge-m3 reachable (kNN audit; waived under --skip-knn).

Run:
    python3 scripts/bug695_recalibrate.py                # dry-run: preflight + coverage
    python3 scripts/bug695_recalibrate.py --apply        # full step 3 + 4 + verify
    python3 scripts/bug695_recalibrate.py --apply --skip-knn
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH  # noqa: E402

# ── C12: config-first paths (no hardcoded labels/thresholds) ─────────────────
_TAXONOMY_V9 = _ROOT / "config" / "taxonomy_v9.yaml"
_TAXONOMY_V5 = _ROOT / "config" / "taxonomy_v5.yaml"  # what the 4 scripts read
_CLOSED_MENU = _ROOT / "config" / "closed_menu_v9.json"
_CALIBRATION = _ROOT / "governance" / "d2547_calibration.json"
_CFG = _ROOT / "config" / "pipeline_config.yaml"

_NLI_AUDIT = _ROOT / "pipeline" / "nli_label_audit.py"
_KNN_AUDIT = _ROOT / "scripts" / "knn_label_disagreement.py"
_BUILD_TRIAGE = _ROOT / "scripts" / "build_mislabel_triage.py"
_POPULATE = _ROOT / "scripts" / "populate_semantic_error_thresholds.py"

_EMERGING_SENTINEL = "emerging"  # C20: non-canonical placeholder in closed_menu
_DEFAULT_MIN_SAMPLE = 10          # C20: fallback only (config wins)


def _load_taxonomy(path: Path) -> tuple[set[str], set[str]]:
    """Return (discipline, domain) canonical label sets from a taxonomy YAML."""
    tax = yaml.safe_load(path.read_text(encoding="utf-8"))
    disc = {d["canonical"] for d in tax["disciplines"]}
    dom = {d["canonical"] for d in tax["domains"]}
    return disc, dom


def _load_closed_menu() -> tuple[set[str], set[str]]:
    """Return (discipline, domain) label sets from the D-2900 single pointer."""
    cm = json.loads(_CLOSED_MENU.read_text(encoding="utf-8"))
    disc = {x["value"] for x in cm["disciplines"]}
    dom = {x["value"] for x in cm["domains"]}
    return disc, dom


def _min_sample() -> int:
    """Minimum corpus size for a label to receive a per-label rate (from config)."""
    cfg = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    return int((cfg.get("taxonomy") or {}).get("emerging_freq_threshold", _DEFAULT_MIN_SAMPLE))


def _parse_domains(raw: str | None) -> list[str]:
    """Mirror populate_semantic_error_thresholds._parse_domains (no divergence)."""
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _load_db_counts() -> tuple[dict[str, int], dict[str, int]]:
    """Return (discipline_total, domain_total) from the CANONICAL run (D-2881).

    The D2547 census must reflect only the serving corpus (the canonical run),
    never stale non-canonical runs (t11/e2e/bug198_reinject) that share the fbs
    table — those carry pre-v9 labels and would corrupt the per-label rates.
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        disc: dict[str, int] = {}
        for (label, n) in conn.execute(
            "SELECT discipline, COUNT(*) FROM fbs "
            "WHERE pipeline_run_id = ? AND discipline IS NOT NULL AND discipline != '' "
            "GROUP BY discipline",
            (CANONICAL_RUN,),
        ):
            disc[label] = n
        dom: dict[str, int] = {}
        for (raw,) in conn.execute(
            "SELECT domains FROM fbs WHERE pipeline_run_id = ?", (CANONICAL_RUN,)
        ):
            for d in _parse_domains(raw):
                dom[d] = dom.get(d, 0) + 1
    finally:
        conn.close()
    return disc, dom


def _preflight(canon_disc: set[str]) -> list[str]:
    """Run fail-closed preflight gates G1–G4. Return list of failure strings."""
    failures: list[str] = []

    # G1 — taxonomy_v5 must equal taxonomy_v9 (downstream scripts read "v5").
    if _TAXONOMY_V5.read_bytes() != _TAXONOMY_V9.read_bytes():
        failures.append(
            f"G1: {_TAXONOMY_V5.name} != {_TAXONOMY_V9.name} — the four downstream "
            "scripts read the misnamed v5 file; refuse to calibrate against a "
            "divergent taxonomy."
        )

    # G2 — closed_menu and taxonomy agree up to the 'emerging' sentinel.
    cm_disc, cm_dom = _load_closed_menu()
    tx_disc, tx_dom = _load_taxonomy(_TAXONOMY_V9)
    if (cm_disc - {_EMERGING_SENTINEL}) != tx_disc or not (tx_disc <= cm_disc):
        failures.append(
            "G2: closed_menu_v9.json discipline set drifted from taxonomy_v9.yaml "
            f"(closed_menu-only: {sorted(cm_disc - tx_disc - {_EMERGING_SENTINEL})}, "
            f"taxonomy-only: {sorted(tx_disc - cm_disc)})."
        )
    if (cm_dom - {_EMERGING_SENTINEL}) != tx_dom or not (tx_dom <= cm_dom):
        failures.append(
            "G2: closed_menu_v9.json domain set drifted from taxonomy_v9.yaml "
            f"(closed_menu-only: {sorted(cm_dom - tx_dom - {_EMERGING_SENTINEL})}, "
            f"taxonomy-only: {sorted(tx_dom - cm_dom)})."
        )

    # G3 — RATIFY-2 complete: no non-canonical discipline value left in the
    # canonical run (D-2881 scoping; stale non-canonical runs are out of scope).
    disc_counts, _ = _load_db_counts()
    leftover = sorted(set(disc_counts) - canon_disc - {_EMERGING_SENTINEL, ""})
    if leftover:
        detail = ", ".join(f"{l} ({disc_counts[l]})" for l in leftover)
        failures.append(
            f"G3: RATIFY-2 re-classification is INCOMPLETE in the canonical run — "
            f"{len(leftover)} pre-v9 discipline value(s) still present: {detail}. "
            "Re-run RATIFY-2 (D-2727) before recalibrating."
        )

    return failures


def _coverage_gaps(calibration: dict, canon_disc: set[str], canon_dom: set[str],
                   disc_counts: dict[str, int], dom_counts: dict[str, int],
                   min_sample: int) -> list[str]:
    """Return labels that would be falsely stamped 0.0 (missing calibration data)."""
    disc_measured: dict[str, int] = {}
    dom_measured: set[str] = set()
    for rec in calibration.get("labels", []):
        axis, label = rec["axis"], rec["label"]
        nli_total = int(rec.get("nli_total") or 0)
        if axis == "discipline":
            disc_measured[label] = nli_total
        elif axis == "domain":
            for p in label.split("|"):
                if p in canon_dom:
                    dom_measured.add(p)

    gaps: list[str] = []
    for label in sorted(canon_disc):
        total = disc_counts.get(label, 0)
        if total >= min_sample and disc_measured.get(label, 0) == 0:
            gaps.append(f"discipline '{label}' (DB={total}, calibration nli_total=0)")
    for label in sorted(canon_dom):
        total = dom_counts.get(label, 0)
        if total >= min_sample and label not in dom_measured:
            gaps.append(f"domain '{label}' (DB={total}, no calibration combo)")
    return gaps


def _run(cmd: list[str], *, label: str) -> int:
    """Run a subprocess fail-closed; print its output; return exit code."""
    print(f"\n▶ {label}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        print(f"❌ {label} failed (rc={proc.returncode}). Aborting.", file=sys.stderr)
    return proc.returncode


def _read_per_label() -> dict[str, float]:
    """Read the per_label block currently written into pipeline_config.yaml."""
    cfg = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    ser = cfg["taxonomy"]["semantic_error_rate_max"]
    return ser["per_label"]


def main() -> int:
    ap = argparse.ArgumentParser(description="BUG-695 D2547 recalibration wrapper (fail-closed).")
    ap.add_argument("--apply", action="store_true",
                    help="Run step 3 (recalibrate) + step 4 (populate + verify). "
                         "Default is dry-run: preflight + coverage report only.")
    ap.add_argument("--skip-knn", action="store_true",
                    help="Skip the kNN audit (its columns are advisory; populate only "
                         "consumes NLI contradict counts).")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ DB not found at {DB_PATH}", file=sys.stderr)
        return 1

    canon_disc, canon_dom = _load_taxonomy(_TAXONOMY_V9)
    disc_counts, dom_counts = _load_db_counts()
    min_sample = _min_sample()

    print(f"canonical disciplines: {len(canon_disc)}  domains: {len(canon_dom)}  "
          f"min_sample: {min_sample}")

    # ── Preflight (fail-closed) ──────────────────────────────────────────────
    failures = _preflight(canon_disc)
    if failures:
        print("\n❌ PREFLIGHT FAILED — blocked:")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("✅ preflight G1–G3 passed (taxonomy/closed-menu consistent; corpus is v9).")

    # ── Coverage report against the CURRENT calibration artifact ─────────────
    calibration = json.loads(_CALIBRATION.read_text(encoding="utf-8"))
    gaps = _coverage_gaps(calibration, canon_disc, canon_dom,
                          disc_counts, dom_counts, min_sample)
    if gaps:
        print(f"\n⚠️  {len(gaps)} canonical label(s) would be falsely stamped 0.0 "
              "by a naive populate --apply:")
        for g in gaps:
            print(f"   - {g}")
    else:
        print("\n✅ current calibration fully covers all canonical labels (no false zeros).")

    if not args.apply:
        print("\n(dry-run — no audit/populate executed. Re-run with --apply after RATIFY-2.)")
        return 1 if gaps else 0

    # ── Step 3: recalibrate ──────────────────────────────────────────────────
    rc = _run([sys.executable, str(_NLI_AUDIT), "--axis", "both"],
              label="step 3.1 nli_label_audit")
    if rc:
        return rc
    if not args.skip_knn:
        rc = _run([sys.executable, str(_KNN_AUDIT)], label="step 3.2 knn_label_disagreement")
        if rc:
            return rc
    rc = _run([sys.executable, str(_BUILD_TRIAGE)], label="step 3.3 build_mislabel_triage")
    if rc:
        return rc

    # Re-check coverage against the FRESH calibration BEFORE writing any config.
    calibration = json.loads(_CALIBRATION.read_text(encoding="utf-8"))
    gaps = _coverage_gaps(calibration, canon_disc, canon_dom,
                          disc_counts, dom_counts, min_sample)
    if gaps:
        print("\n❌ FRESH calibration still has coverage gaps — refusing to populate:")
        for g in gaps:
            print(f"   - {g}")
        return 1

    # ── Step 4: populate + verify ────────────────────────────────────────────
    rc = _run([sys.executable, str(_POPULATE), "--apply"], label="step 4.1 populate")
    if rc:
        return rc

    per_label = _read_per_label()
    expected = {l for l in canon_disc if disc_counts.get(l, 0) >= min_sample} | \
               {l for l in canon_dom if dom_counts.get(l, 0) >= min_sample}
    missing = expected - set(per_label)
    extra = set(per_label) - expected
    if missing or extra:
        print("\n❌ VERIFY FAILED — per_label block drifted from expected coverage:")
        if missing:
            print(f"   missing ({len(missing)}): {sorted(missing)}")
        if extra:
            print(f"   extra ({len(extra)}): {sorted(extra)}")
        return 1

    # A 0.0 is only a FALSE ZERO when it traces to MISSING calibration data
    # (nli_total == 0). A measured 0.0 (nli_total > 0, contradict == 0) is a
    # legitimate empirical rate and must NOT be refused (matches _coverage_gaps).
    measured: set[str] = set()
    for rec in calibration.get("labels", []):
        if int(rec.get("nli_total") or 0) <= 0:
            continue
        if rec.get("axis") == "discipline":
            measured.add(rec["label"])
        elif rec.get("axis") == "domain":
            measured.update(p for p in rec["label"].split("|") if p)

    false_zeros = [l for l, v in per_label.items()
                   if v == 0.0 and l not in measured]
    if false_zeros:
        print(f"\n❌ VERIFY FAILED — {len(false_zeros)} canonical label(s) stamped 0.0 "
              f"from MISSING calibration data (nli_total == 0): {sorted(false_zeros)}. "
              "Re-run step 3 (nli_label_audit) to audit them.")
        return 1

    print(f"\n✅ BUG-695 complete: {len(per_label)} per-label thresholds written and "
          "verified (no false zeros, no drift).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
