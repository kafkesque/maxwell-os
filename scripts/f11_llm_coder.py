#!/usr/bin/env python3
"""F-11 second-coder harness: blind-export the 150-row ruler, then score coder agreement.

Two modes, both driven by config/f11_llm_coder.yaml (C12 — no hardcoded paths or thresholds):

  --export   strip the 9 answer columns from the filled single-coder ruler sheet and write
             ROWS_BLIND_150.csv + MANIFEST.json (sha256 of every input and output).
  --score F  read a second coder's JSONL answers and write the inter-coder agreement
             artifact (governance/f11_llm_coder_<date>.{json,md}).

GUARD RAILS (fail-closed, C16):
  * export refuses if any row is missing a human answer, or if any answer column survives the strip
    (a leaked label destroys the second coder's blindness and the whole measurement);
  * score refuses on any row count other than the full sheet, on duplicate/missing item_ids, or on a
    label outside the declared vocabulary, and never writes a partial artifact;
  * the output artifact stamps provenance tier `llm-attested` and states that it cannot unfreeze
    the eval floors (D-317 / F-11). It never writes anything named human-blind.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.io_guard import safe_write  # noqa: E402 — C6 crash-safe writes (tmp→fsync→os.replace)
from pipeline.pipeline_paths import PROJECT_ROOT  # noqa: E402 — single source for the repo root

CFG_PATH = PROJECT_ROOT / "config" / "f11_llm_coder.yaml"


def _cfg() -> dict[str, Any]:
    """Load the package config (C12: every path, axis and identity comes from here).

    Returns:
        The parsed config mapping.
    """
    import yaml

    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) or {}
    if not cfg.get("enabled"):
        raise SystemExit("f11_llm_coder.yaml: enabled is not true — refusing to run")
    return cfg


def _sha(p: Path) -> str:
    """sha256 hex digest of a file's bytes.

    Args:
        p: file to hash.

    Returns:
        Hex digest.
    """
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _read_sheet(p: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read the ruler sheet as (header, rows), dropping trailing blank lines.

    Args:
        p: sheet path.

    Returns:
        Tuple of the header field names and the non-empty rows.
    """
    with p.open(encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        rows = [r for r in rdr if any((v or "").strip() for v in r.values())]
        if not rdr.fieldnames:
            raise SystemExit(f"{p}: no header row")
        return list(rdr.fieldnames), rows


def cmd_export(cfg: dict[str, Any]) -> int:
    """Write the blind row export plus a manifest of every input/output hash.

    Args:
        cfg: package config.

    Returns:
        Process exit code.
    """
    sheet = PROJECT_ROOT / cfg["sheet"]
    menus = PROJECT_ROOT / cfg["menus"]
    out_rows = PROJECT_ROOT / cfg["blind_rows"]
    out_manifest = PROJECT_ROOT / cfg["manifest"]
    ident, answer = list(cfg["identity_columns"]), list(cfg["answer_columns"])
    axes = list(cfg["axes"].values())

    header, rows = _read_sheet(sheet)
    missing_cols = [c for c in ident + answer if c not in header]
    if missing_cols:
        raise SystemExit(f"{sheet}: missing expected columns {missing_cols} (sheet changed, C16)")

    unanswered = [r["item_id"] for r in rows if any(not (r.get(a) or "").strip() for a in axes)]
    excluded: list[str] = []
    # export_all_rows (2026-09-22): the owner asked for ALL rows to go to the coders, so that the
    # 28 rows the human left unanswered are adjudicated by the SAME coders instead of being dropped.
    if unanswered and not cfg.get("export_all_rows"):
        if not cfg.get("allow_partial"):
            raise SystemExit(
                f"{sheet}: {len(unanswered)} row(s) lack a human answer on one of {axes} "
                f"(first: {unanswered[:5]}) — an incomplete ruler cannot measure reliability"
            )
        excluded = list(unanswered)
        rows = [r for r in rows if r["item_id"] not in set(excluded)]
        print(f"   ⚠️  DECLARED PARTIAL: {len(excluded)} row(s) lack a human answer and are EXCLUDED "
              f"({cfg.get('partial_policy')})")
        print(f"      excluded item_ids: {', '.join(excluded)}")
        if not rows:
            raise SystemExit(f"{sheet}: every row is incomplete — nothing to export")

    out_rows.parent.mkdir(parents=True, exist_ok=True)
    # A trailing EMPTY separator column: a blank column that has a header saying what it is for
    # cannot again be mistaken for free space to write answers into (BUG-368).
    sep = str(cfg.get("blank_separator_header") or "").strip()
    cols = ident + ([sep] if sep else [])
    buf = [",".join(cols)]
    for r in rows:
        cells = ['"' + (r.get(c) or "").replace('"', '""') + '"' for c in ident] + (['""'] if sep else [])
        buf.append(",".join(cells))
    text = "\n".join(buf) + "\n"
    leaked = [c for c in answer if f'"{c}"' in buf[0] or f",{c}," in buf[0]]
    if leaked:
        raise SystemExit(f"blind export still carries answer column(s) {leaked} — refusing (blindness)")
    safe_write(out_rows, text, force_shrink=True)

    manifest = {
        "schema_version": "1.0",
        "decision": cfg["decision"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provenance_tier": cfg["provenance_tier"],
        "cannot_unfreeze": cfg["cannot_unfreeze"],
        "n_rows": len(rows),
        "n_excluded_incomplete_rows": len(excluded),
        "excluded_item_ids": excluded,
        "partial": bool(excluded),
        "identity_columns": ident,
        "human_answer_columns_removed": answer,
        "inputs": {str(sheet.relative_to(PROJECT_ROOT)): _sha(sheet),
                   str(menus.relative_to(PROJECT_ROOT)): _sha(menus),
                   "PROMPT.md": _sha(out_rows.parent / "PROMPT.md"),
                   "README.md": _sha(out_rows.parent / "README.md")},
        "outputs": {str(out_rows.relative_to(PROJECT_ROOT)): hashlib.sha256(text.encode()).hexdigest()},
    }
    safe_write(out_manifest, json.dumps(manifest, indent=2) + "\n", force_shrink=True)
    print(f"✅ blind export: {len(rows)} rows → {out_rows.relative_to(PROJECT_ROOT)}")
    print(f"   answer columns removed: {', '.join(answer)}")
    print(f"   PROMPT.md sha256: {manifest['inputs']['PROMPT.md']}")
    print(f"   manifest → {out_manifest.relative_to(PROJECT_ROOT)}")
    print("\n   NEXT: fill coder.* in config/f11_llm_coder.yaml (model, family, sovereign_opt_in, prompt_sha256)")
    return 0


def _canon(v: str, aliases: dict[str, str]) -> str:
    """Normalise a label to a comparison key (lowercase, alphanumeric only).

    Args:
        v: raw label as written by a coder.
        aliases: declared as_written → canonical aliases (C12d: explicit, never guessed).

    Returns:
        Comparison key.
    """
    s = "".join(ch for ch in str(v or "").lower() if ch.isalnum())
    return aliases.get(s, s)


def _kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa for two coders over paired categorical labels.

    Args:
        pairs: list of (coder_a_key, coder_b_key).

    Returns:
        Kappa, or float('nan') when expected agreement is 1.0 (degenerate).
    """
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if math.isclose(pe, 1.0):
        return float("nan")
    return round((po - pe) / (1 - pe), 4)


def cmd_score(cfg: dict[str, Any], llm_path: Path, tag: str = "", model: str = "",
              family: str = "", allow_partial: bool = False) -> int:
    """Compare a second coder's JSONL answers against the human coder's sheet.

    Args:
        cfg: package config.
        llm_path: the second coder's JSONL output.
        tag: short coder tag for the artifact filename (one artifact per coder).
        model: coder model id recorded in the artifact (overrides config).
        family: coder model family recorded in the artifact (overrides config).
        allow_partial: accept a coder who answered only part of the rows and score the intersection
            (declared in the artifact; the default refuses, because a partial coder silently
            compared against the wrong denominator is how a kappa becomes fiction).

    Returns:
        Process exit code.
    """
    llm_path = llm_path.resolve()
    try:
        rel = str(llm_path.relative_to(PROJECT_ROOT))
    except ValueError:
        rel = str(llm_path)  # coder file outside the repo: recorded absolutely, never truncated
    sheet = PROJECT_ROOT / cfg["sheet"]
    aliases = {_canon(a["as_written"], {}): _canon(a["canonical"], {})
               for a in cfg.get("declared_aliases") or []}
    header, rows = _read_sheet(sheet)
    axes = dict(cfg["axes"])

    blind = PROJECT_ROOT / cfg["blind_rows"]
    if not blind.exists():
        raise SystemExit(f"{blind} missing — run --export first (the exported blind row set defines "
                         f"exactly which rows the two coders are compared on)")
    _, brow = _read_sheet(blind)
    keep = {r["item_id"] for r in brow}
    human: dict[str, dict[str, str]] = {r["item_id"]: r for r in rows if r["item_id"] in keep}
    llm: dict[str, dict[str, Any]] = {}
    for lineno, line in enumerate(llm_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("```"):
            raise SystemExit(f"{llm_path}:{lineno}: markdown fence in the answer file — re-save as raw JSONL")
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{llm_path}:{lineno}: not valid JSON ({exc}) — refusing (C16)") from exc
        iid = str(obj.get("item_id", "")).strip()
        if not iid:
            raise SystemExit(f"{llm_path}:{lineno}: missing item_id")
        if iid in llm:
            raise SystemExit(f"{llm_path}:{lineno}: duplicate item_id {iid} — refusing")
        llm[iid] = obj

    want, got = set(human), set(llm)
    missing, extra = sorted(want - got), sorted(got - want)
    if missing or extra:
        if not allow_partial:
            raise SystemExit(
                f"coder answered {len(got)}/{len(want)} rows; missing={missing[:5]} extra={extra[:5]} — "
                f"a partial second coder is not a reliability measurement (pass --partial to score the "
                f"intersection with the shortfall declared)"
            )
        compared = want & got
        if not compared:
            raise SystemExit(f"{llm_path}: zero overlap with the exported row set — nothing to compare")
        print(f"   ⚠️  DECLARED PARTIAL: scoring {len(compared)} of {len(want)} rows; "
              f"{len(missing)} unanswered by this coder ({', '.join(missing[:8])}"
              f"{' …' if len(missing) > 8 else ''}), {len(extra)} not in the export")
        human = {k: v for k, v in human.items() if k in compared}
        llm = {k: v for k, v in llm.items() if k in compared}

    per_axis: dict[str, Any] = {}
    for axis, col in axes.items():
        pairs: list[tuple[str, str]] = []
        confs: list[float] = []
        distinct: dict[str, Counter[str]] = {"human": Counter(), "llm": Counter()}
        disagreements: list[dict[str, str]] = []
        blank_human = blank_llm = 0
        blank_human_ids: list[str] = []
        for iid in sorted(human):
            a_raw, b_raw = human[iid].get(col, ""), str(llm[iid].get(axis, ""))
            a, b = _canon(a_raw, aliases), _canon(b_raw, aliases)
            # BUG-369: an UNANSWERED cell is NOT a disagreement. A blank human axis (the rows of
            # BUG-363 that no human ever labelled) or a blank coder axis is excluded from the pair
            # set and counted separately - otherwise the blanks deflate agreement/kappa by exactly
            # their share, and round 1 (complete human cells) becomes incomparable to round 2.
            if not a or not b:
                if not a:
                    blank_human += 1
                    blank_human_ids.append(iid)
                if not b:
                    blank_llm += 1
                continue
            pairs.append((a, b))
            distinct["human"][a] += 1
            distinct["llm"][b] += 1
            conf = llm[iid].get((cfg.get("conf_columns") or {}).get(axis, ""))
            if isinstance(conf, (int, float)):
                confs.append(float(conf))
            if a != b:
                disagreements.append({"item_id": iid, "human": a_raw.strip(), "llm": b_raw})
        novel_h = [l for l in distinct["llm"] if l not in distinct["human"]]
        novel_l = [l for l in distinct["human"] if l not in distinct["llm"]]
        per_axis[axis] = {
            "column": col,
            "n": len(pairs),
            "n_excluded_human_blank": blank_human,
            "n_excluded_llm_blank": blank_llm,
            "excluded_human_blank_item_ids": blank_human_ids,
            "agreement_pct": round(100 * sum(1 for a, b in pairs if a == b) / len(pairs), 1) if pairs else None,
            "cohen_kappa": _kappa(pairs) if pairs else None,
            "n_distinct_human": len(distinct["human"]),
            "n_distinct_llm": len(distinct["llm"]),
            "labels_llm_used_human_never_used": [l for l in sorted(novel_h) if l],
            "labels_human_used_llm_never_used": [l for l in sorted(novel_l) if l],
            "mean_llm_conf": round(sum(confs) / len(confs), 3) if confs else None,
            "n_disagreements": len(disagreements),
            "disagreements": disagreements,
        }

    stamp = time.strftime("%Y%m%d")
    alias_note = [f"{a['as_written']} → {a['canonical']} ({a['axis']}): {a['reason']}"
                  for a in cfg.get("declared_aliases") or []]
    coder_id = dict(cfg.get("coder") or {})
    if model:
        coder_id["model"] = model
    if family:
        coder_id["family"] = family
    out_json = (PROJECT_ROOT / cfg["out_json"] if not tag else
                PROJECT_ROOT / f"governance/f11_llm_coder_{tag}_{stamp}.json")
    out_md = (PROJECT_ROOT / cfg["out_md"] if not tag else
              PROJECT_ROOT / f"governance/f11_llm_coder_{tag}_{stamp}.md")
    art = {
        "schema_version": "1.0",
        "decision": cfg["decision"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provenance_tier": cfg["provenance_tier"],
        "cannot_unfreeze": cfg["cannot_unfreeze"],
        "STATUS": ("ADVISORY — this is a THIRD attested label set produced by a model. It measures RULER "
                   "RELIABILITY (human↔LLM agreement). It is NOT human-blind, it is NOT independent human "
                   "truth, and it CANNOT license adoption (D-300) or unfreeze config/eval_integrity.yaml (F-11)."),
        "first_coder": {"sheet": cfg["sheet"], "sha256": _sha(sheet), "reviewer_field": "human (single coder)"},
        "second_coder": {"file": rel, "sha256": _sha(llm_path), **coder_id},
        "n_rows": len(human),
        "n_rows_exported": len(want),
        "rows_unanswered_by_this_coder": missing,
        "rows_not_in_export": extra,
        "partial": bool(missing or extra),
        "declared_aliases_applied": alias_note,
        "axes": per_axis,
    }
    safe_write(out_json, json.dumps(art, indent=2) + "\n", force_shrink=True)
    md = [f"# F-11 second coder — human↔LLM agreement ({stamp})", "", f"> {art['STATUS']}", "",
          f"First coder: single human, `{cfg['sheet']}` (sha256 `{art['first_coder']['sha256'][:16]}`)  ",
          f"Second coder: `{art['second_coder'].get('model')}` (tier `{cfg['provenance_tier']}`, "
          f"temp {art['second_coder'].get('temperature')})", "", "| axis | n | agreement | kappa | LLM labels human never used | disagreements |",
          "|---|---|---|---|---|---|"]
    for axis, r in per_axis.items():
        md.append(f"| {axis} | {r['n']} | {r['agreement_pct']}% | {r['cohen_kappa']} | "
                  f"{len(r['labels_llm_used_human_never_used'])} | {r['n_disagreements']} |")
    md += ["", "## Reading rule", "",
           "* high kappa → the ruler is reliable on that axis; *low kappa* → read the disagreement list: if the",
           "  same class pair recurs, the TAXONOMY is ambiguous there (a boundary decision in",
           "  `config/boundary_discriminators.yaml`), not a model failure.",
           "* a coder label that leaves the closed menu is an EMISSION error (the menu-compliance defect",
           "  measured in D-327), never a wrong label.", ""]
    safe_write(out_md, "\n".join(md), force_shrink=True)
    for axis, r in per_axis.items():
        print(f"   {axis:16} agreement {r['agreement_pct']:5}%  kappa {r['cohen_kappa']:>7}  "
              f"disagreements {r['n_disagreements']:3}  LLM-novel labels {r['labels_llm_used_human_never_used']}")
    print(f"\n✅ advisory artifact → {out_md} (+ .json). Advisory only: F-11 stays open.")
    return 0


def main() -> int:
    """CLI entry point.

    Returns:
        Process exit code.
    """
    ap = argparse.ArgumentParser(description="F-11 blind export + second-coder agreement scorer")
    ap.add_argument("--export", action="store_true", help="write ROWS_BLIND_150.csv + MANIFEST.json")
    ap.add_argument("--score", metavar="JSONL", help="score a second coder's JSONL answers")
    ap.add_argument("--tag", default="", help="coder tag for the artifact filename, e.g. claude-sonnet")
    ap.add_argument("--model", default="", help="coder model id recorded in the artifact")
    ap.add_argument("--family", default="", help="coder model family recorded in the artifact")
    ap.add_argument("--partial", action="store_true",
                    help="score the intersection if the coder answered only part of the rows (declared)")
    args = ap.parse_args()
    cfg = _cfg()
    if args.export:
        return cmd_export(cfg)
    if args.score:
        return cmd_score(cfg, Path(args.score), args.tag, args.model, args.family, args.partial)
    ap.error("choose --export or --score <file>")


if __name__ == "__main__":
    raise SystemExit(main())
