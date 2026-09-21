#!/usr/bin/env python3
"""Typed-decision bake-off for S5 (D-296; ADAPT framing D-275c — benchmark, not an integration).

Compares candidate typed-decision heads against the incumbent DeBERTa-v3 NLI verifier and a
constant-answer baseline, on the FROZEN 150-row ruler blind sheet (human label = ground truth,
D-275a: report ERROR RATE, never "accuracy").

Arms (swappable — C21):
  constant   — always predicts the modal HUMAN label.                       $0, deterministic.
  deberta    — DeBERTa-v3-large-mnli zero-shot over the closed discipline menu (incumbent family).
  qwen3coder — Qwen3-Coder-30B one-shot typed decision (choice + confidence + abstain) via oMLX.
  laya_mlx   — mizorewww/laya-mlx decision head (OPTIONAL, gated on install). benchmark-only.
  jevmlx     — bnsd55/jevmlx restricted-softmax head (OPTIONAL, gated on install).

C1/C3 fix (2026-09-21, D-297/D-298): the sheet is the 150-row RULER (not the 60-row R2
adjudication sheet whose key holds PIPELINE labels), the axis is config-declared (content_type is
degenerate here: the pipeline predicts a single class), and the arm layer joins item_id -> fb_id
through the frozen JSON + maps sheet column names through config.

C12: every path, column name, axis, model id and threshold comes from config/eval_integrity.yaml
(bakeoff: block). Nothing is hardcoded here.

Usage:
  python3 scripts/bakeoff_typed_decision.py --arm constant
  python3 scripts/bakeoff_typed_decision.py --arm deberta --arm qwen3coder --limit 150
  python3 scripts/bakeoff_typed_decision.py --source anchor2 --arm pairwise --arm qwen3coder

D-312 (C12): the label SOURCE is config-declared (`bakeoff.active_source`, CLI override --source).
  ruler   — the flat bakeoff block above: key['rows'] carries human + stored labels (truth = key).
  anchor2 — the R3 held-out (legacy name: anchor1) adjudication source (`bakeoff.sources.anchor1`): the SHEET carries the
            human verdicts, the key carries the pipeline labels.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG = ROOT / "config" / "eval_integrity.yaml"
OUT = ROOT / "governance" / "bakeoff_typed_decision_20260921.json"


def load_config() -> dict:
    """Read the bakeoff block; fail loudly if a required key is missing (C16)."""
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["bakeoff"]
    for key in ("sheet", "key", "axis", "sheet_columns", "frozen_fields", "row_id_column"):
        if key not in cfg:
            raise KeyError("config/eval_integrity.yaml bakeoff." + key + " is required")
    return cfg


ABSTAIN_TOKENS = {"", "abstain", "abstention", "none", "unknown", "n/a", "na", "undecided", "cannot"}


def arm_pairwise(rows: list[dict], truth: dict[str, str], cfg: dict, **_kw) -> dict[str, tuple]:
    """PRODUCTION-ROLE arm (D-300 v2): verify the STORED label instead of ranking the menu.

    The incumbent is S5, a pairwise verifier: it never picks among 61 hypotheses. This arm reproduces
    that role - predict the stored label (from the frozen key, config-driven) and expose the NLI margin
    for that one pairing, which is what an abstention threshold would actually consume.
    """
    import torch  # noqa: F401  (device selection happens inside _nli_scores)
    tmpl = cfg["hypothesis_template"]
    preds: dict[str, tuple] = {}
    for i, r in enumerate(rows, 1):
        label = r.get("pipeline_label")   # D-312: stored label comes from the source spec
        if not label:
            preds[r["fb_id"]] = (None, 0.0)
            continue
        s = _nli_scores(r["text"], [render(tmpl, label=label, definition="")])[0]
        margin = s.get("entailment", 0.0) - s.get("contradiction", 0.0)
        preds[r["fb_id"]] = (label, round(margin, 4))
        if i % 25 == 0:
            print("  pairwise " + str(i) + "/" + str(len(rows)), flush=True)
    return preds


def _norm_key(value: object) -> str:
    """Case/punctuation-insensitive key for menu lookup (models echo 'Design-Psychology' etc.)."""
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def _canon(value: object, lookup: dict[str, str]) -> str | None:
    """Map a model's free-text answer onto the canonical menu key, or None if unresolvable."""
    return lookup.get(_norm_key(value))


def render(template: str, **kw: object) -> str:
    """Substitute {named} tokens without str.format (config templates contain JSON braces).

    BUG-318: str.format() treated the literal {"choice": ...} in the config prompt as a format
    field and killed the arm with KeyError. Named replacement keeps the template config-plain.
    """
    out = template
    for key, value in kw.items():
        out = out.replace("{" + key + "}", str(value))
    return out


RULER_SOURCE = "ruler"   # name of the flat `bakeoff:` block above (D-312)


def source_spec(cfg: dict, name: str | None = None) -> dict:
    """Return a self-contained spec for a named label source (C12: named, never inferred).

    D-312: `ruler` is the flat block above (key['rows'] carries human + stored labels);
    `anchor2` is the R3 held-out (legacy name: `anchor1`) adjudication source (the SHEET carries the human verdicts, the
    key carries the pipeline labels). A run names one source; the loader never guesses from a
    filename, and every path/column/shape below comes from config.
    """
    src_name = str(name or cfg.get("active_source") or RULER_SOURCE)
    if src_name == RULER_SOURCE:
        return {"name": RULER_SOURCE, "key_shape": "rows", "truth_from": "key",
                "sheet": cfg["sheet"], "key": cfg["key"], "axis": cfg["axis"],
                "row_id_column": cfg["row_id_column"], "limit": int(cfg.get("limit") or 0),
                "sheet_columns": cfg["sheet_columns"], "key_truth_fields": cfg["frozen_fields"],
                "key_stored_fields": cfg["frozen_fields"], "verdict_columns": {},
                "definition_column": cfg.get("definition_column") or "DEFINITION",
                "name_column": cfg.get("name_column") or "name",
                "include_catch_all": bool(cfg.get("include_catch_all") or False),
                "exclude_rows_without_truth": False, "output": str(OUT)}
    block = (cfg.get("sources") or {}).get(src_name)
    if not block:
        raise KeyError("config/eval_integrity.yaml bakeoff.sources." + src_name + " is not declared")
    spec = dict(block)
    spec["name"] = src_name
    for key in ("sheet", "key", "key_shape", "row_id_column", "verdict_columns",
                "key_stored_fields", "definition_column", "name_column"):
        if key not in spec:
            raise KeyError("bakeoff.sources." + src_name + "." + key + " is required (C12/C16)")
    spec.setdefault("truth_from", "sheet")
    spec.setdefault("axis", cfg["axis"])
    spec.setdefault("limit", int(cfg.get("limit") or 0))
    spec.setdefault("include_catch_all", False)
    spec.setdefault("normalize_through_menu", True)
    spec.setdefault("exclude_rows_without_truth", False)
    spec.setdefault("output", str(OUT))
    return spec


def _menu_lookup(cfg: dict, spec: dict) -> dict[str, str]:
    """Normalised menu surface -> canonical label, for BOTH truth and stored labels (symmetric)."""
    return {_norm_key(l): l for l in closed_menu(cfg, bool(spec.get("include_catch_all")))}


def load_rows(cfg: dict, limit: int, spec: dict | None = None) -> tuple[list[dict], dict[str, str]]:
    """Load (rows, human truth) for a label source, normalised onto the closed menu (D-312).

    ruler  — key['rows'] carries human + stored labels; the sheet contributes text only.
    anchor2 — the SHEET carries the human verdicts, the key carries the pipeline labels.
    An unresolvable HUMAN verdict is a hard error (C16) rather than a silent wrong answer; an
    unresolvable STORED label becomes an abstention for the incumbent arm (never a false error).
    `row_allowlist_file` restricts the run to the pre-registered held-out ids.
    """
    src = spec or source_spec(cfg)
    axis = src["axis"]
    id_field = src["row_id_column"]
    key = json.loads((ROOT / src["key"]).read_text(encoding="utf-8"))
    lookup = _menu_lookup(cfg, src) if src.get("normalize_through_menu") else {}
    stored_raw: dict[str, str] = {}
    by_item: dict[str, str] = {}
    truth: dict[str, str] = {}
    if src["key_shape"] == "rows":
        truth_field = src["key_truth_fields"][axis]
        for r in key["rows"]:
            if not r.get("fb_id"):
                continue
            by_item[str(r[id_field])] = r["fb_id"]
            stored_raw[r["fb_id"]] = (r.get("stored") or {}).get(src["key_stored_fields"][axis])
            label = (r.get("human") or {}).get(truth_field)
            if label:
                truth[r["fb_id"]] = lookup.get(_norm_key(label), label) if lookup else label
    else:
        for fb, v in (key.get("key") or {}).items():
            by_item[str(fb)] = str(fb)
            stored_raw[str(fb)] = v.get(src["key_stored_fields"][axis])
    stored = {fb: (lookup.get(_norm_key(lab), None) if lookup else lab)
              for fb, lab in stored_raw.items()}
    allow: set[str] | None = None
    if src.get("row_allowlist_file"):
        payload = json.loads((ROOT / src["row_allowlist_file"]).read_text(encoding="utf-8"))
        allow = {str(x) for x in payload[src["row_allowlist_field"]]}
    with (ROOT / src["sheet"]).open(encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    truth_col = (src.get("verdict_columns") or {}).get(axis)
    rows: list[dict] = []
    unresolved: list[str] = []
    unlabelled = 0
    for r in (raw[:limit] if limit else raw):
        fb = by_item.get(str(r.get(id_field, "")).strip())
        if not fb:
            print("WARN no fb_id for " + str(r.get(id_field)), file=sys.stderr)
            continue
        if allow is not None and fb not in allow:
            continue
        if src.get("truth_from") == "sheet":
            raw_label = (r.get(truth_col) or "").strip()
            if not raw_label:
                unlabelled += 1
                if src.get("exclude_rows_without_truth"):
                    continue
            else:
                label = lookup.get(_norm_key(raw_label), None) if lookup else raw_label
                if label is None:
                    unresolved.append(fb + "=" + raw_label)
                    continue
                truth[fb] = label
        rows.append({"item_id": str(r.get(id_field, "")).strip(), "fb_id": fb,
                     "text": (r.get(src["definition_column"]) or "").strip(),
                     "name": (r.get(src["name_column"]) or "").strip(),
                     "pipeline_label": stored.get(fb)})
    if unresolved:
        raise ValueError("unresolvable HUMAN verdict(s) not on the closed menu: " + ", ".join(unresolved))
    print("loaded source=" + src["name"] + " rows=" + str(len(rows)) + " truth=" + str(len(truth)) +
          " unlabelled_excluded=" + str(unlabelled) + " allowlist=" + str(len(allow) if allow else "all"))
    return rows, truth


def closed_menu(cfg: dict, include_catch_all: bool = False) -> dict[str, str]:
    """Closed discipline menu: canonical label -> definition (taxonomy, C12).

    `include_catch_all` adds the taxonomy's DECLARED catch-all discipline (meta.catch_all_discipline)
    so an adjudicated "emerging" verdict has a legal slot instead of being silently scored wrong.
    """
    import yaml

    tax = yaml.safe_load((ROOT / cfg["taxonomy"]).read_text(encoding="utf-8"))
    out = {d["canonical"]: (d.get("definition") or "") for d in tax["disciplines"]}
    if include_catch_all:
        cat = str((tax.get("meta") or {}).get("catch_all_discipline") or "").strip()
        if cat:
            out.setdefault(cat, "declared catch-all discipline (config/taxonomy_v5.yaml meta)")
    return out


def menu(cfg: dict) -> dict[str, str]:
    """Back-compat wrapper: the closed menu without the catch-all slot (ruler source)."""
    return closed_menu(cfg, False)


def arm_constant(rows: list[dict], truth: dict[str, str], **_kw) -> dict[str, tuple]:
    """Always predict the modal HUMAN label (never the sheet column) with confidence 1.0."""
    from collections import Counter

    counts = Counter(truth[r["fb_id"]] for r in rows if r["fb_id"] in truth)
    modal = counts.most_common(1)[0][0] if counts else None
    return {r["fb_id"]: (modal, 1.0) for r in rows}


_NLI: dict = {}
_DEVICE_CFG: str = "auto"   # config: bakeoff.device (C24 hardware-adaptive; 'auto' = mps > cuda > cpu)


def _nli_scores(premise: str, hypotheses: list[str]) -> list[dict[str, float]]:
    """Batched raw DeBERTa NLI label scores: one premise vs N hypotheses (encoder, no generation).

    Batched on purpose: per-row sequential scoring of the 61-slot menu ran at ~1 s/pair (2.5 h for
    150 rows). One padded forward pass per batch is 10-20x faster with identical scores.
    """
    import torch
    from pipeline.pipeline_paths import S5_NLI_MODEL_LARGE
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if not _NLI:
        dev = _DEVICE_CFG
        if dev == "auto":
            dev = ("mps" if torch.backends.mps.is_available()
                   else "cuda" if torch.cuda.is_available() else "cpu")
        _NLI["device"] = dev
        _NLI["tok"] = AutoTokenizer.from_pretrained(S5_NLI_MODEL_LARGE)
        _NLI["model"] = AutoModelForSequenceClassification.from_pretrained(
            S5_NLI_MODEL_LARGE).to(dev).eval()
        _NLI["labels"] = [str(_NLI["model"].config.id2label.get(i, i)).lower()
                          for i in range(_NLI["model"].config.num_labels)]
    tok, model = _NLI["tok"], _NLI["model"]
    with torch.no_grad():
        enc = tok([premise] * len(hypotheses), hypotheses, return_tensors="pt", truncation=True,
                  padding=True, max_length=512).to(_NLI["device"])
        probs = torch.softmax(model(**enc).logits, dim=-1).to("cpu").tolist()
    return [{lab: p for lab, p in zip(_NLI["labels"], row)} for row in probs]


def arm_deberta(rows: list[dict], truth: dict[str, str], cfg: dict, **_kw) -> dict[str, tuple]:
    """Incumbent family: zero-shot NLI over the closed menu; score = entail - contradict."""
    tmpl = cfg["hypothesis_template"]
    labels = list(menu(cfg).items())
    batch = int(cfg["nli_batch_size"])
    preds: dict[str, tuple] = {}
    for i, r in enumerate(rows, 1):
        best, best_score = None, -9.9
        for j in range(0, len(labels), batch):
            chunk = labels[j:j + batch]
            scores = _nli_scores(r["text"], [render(tmpl, label=l, definition=d) for l, d in chunk])
            for (label, _d), s in zip(chunk, scores):
                score = s.get("entailment", 0.0) - s.get("contradiction", 0.0)
                if score > best_score:
                    best, best_score = label, score
        preds[r["fb_id"]] = (best, round(best_score, 4))
        if i % 10 == 0:
            print("  deberta " + str(i) + "/" + str(len(rows)) + " -> " + str(best), flush=True)
    return preds


def arm_qwen3coder(rows: list[dict], truth: dict[str, str], cfg: dict, **_kw) -> dict[str, tuple]:
    """Qwen3-Coder one-shot typed decision via oMLX (temp 0.0, R7). Single-shot only (DELEGATE-002)."""
    from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL

    labels = menu(cfg)
    menu_text = "\n".join("- " + k + ": " + v for k, v in labels.items())
    lookup = {_norm_key(l): l for l in labels}   # case/spacing-insensitive menu lookup (BUG-319)
    reasons: Counter = Counter()
    preds: dict[str, tuple] = {}
    for i, r in enumerate(rows, 1):
        prompt = render(cfg["prompt_template"], axis=cfg["axis"], menu=menu_text,
                        name=r["name"], definition=r["text"])
        body = json.dumps({"model": cfg["omlx_model"], "temperature": 0.0,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(
            OMLX_URL.rstrip("/") + cfg["omlx_path"], data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + OMLX_API_KEY})
        try:
            with urllib.request.urlopen(req, timeout=cfg["omlx_timeout_s"]) as resp:
                payload = json.loads(resp.read().decode())
            content = payload["choices"][0]["message"]["content"]
            start, end = content.find("{"), content.rfind("}")
            parsed = json.loads(content[start:end + 1])
            raw = str(parsed.get("choice", ""))
            choice = _canon(raw, lookup)
            if choice is None and _canon(raw, {}) is None or choice is None:
                if raw.strip().lower() in ABSTAIN_TOKENS:
                    reason = "model_abstained"      # the model refused: a legitimate decision
                else:
                    reason = "unresolved_choice"    # we could not map its answer onto our menu
                choice, conf = None, (-1.0 if reason == "unresolved_choice" else 0.0)
            else:
                conf, reason = float(parsed.get("confidence") or 0.0), "ok"
        except urllib.error.HTTPError as exc:  # noqa: BLE001 — no silent errors (C16)
            print("  WARN row " + str(r["item_id"]) + " HTTP " + str(exc.code), file=sys.stderr)
            choice, conf, reason = None, -1.0, "http_error_" + str(exc.code)
        except Exception as exc:  # noqa: BLE001 (C16)
            print("  WARN row " + str(r["item_id"]) + " failed: " + str(exc), file=sys.stderr)
            choice, conf, reason = None, -1.0, "parse_error_" + type(exc).__name__
        preds[r["fb_id"]] = (choice, conf)
        reasons[reason] += 1   # BUG-319: "we failed to read it" must never look like "it said no"
        if i % 5 == 0:
            print("  qwen3coder " + str(i) + "/" + str(len(rows)) + " -> " + str(choice) + " (" + reason + ")",
                  flush=True)
    print("  qwen3coder decided/abstain/parse breakdown: " + json.dumps(reasons.most_common()), flush=True)
    return preds


def arm_typed_head(rows: list[dict], head: str, **_kw) -> dict[str, tuple]:
    """Optional Jev-clone typed head (laya-mlx / jevmlx) — gated on install, benchmark-only."""
    raise NotImplementedError("head " + head + " not installed — benchmark-only arm")


ARMS: dict[str, Callable[..., dict[str, tuple]]] = {
    "constant": arm_constant,
    "deberta": arm_deberta,
    "qwen3coder": arm_qwen3coder,
    "pairwise": arm_pairwise,   # incumbent in its production role (D-300 v2)
    "laya_mlx": lambda rows, **kw: arm_typed_head(rows, "laya_mlx", **kw),
    "jevmlx": lambda rows, **kw: arm_typed_head(rows, "jevmlx", **kw),
}


def score(preds: dict[str, tuple], truth: dict[str, str]) -> dict:
    """Error rate (D-275a) + abstain rate over rows that carry ground truth."""
    scored = [(fb, lab) for fb, (lab, _c) in preds.items() if fb in truth]
    abstained = sum(1 for _fb, lab in scored if lab is None)
    decided = [(fb, lab) for fb, lab in scored if lab is not None]
    errs = sum(1 for fb, lab in decided if truth[fb] != lab)
    return {"n": len(scored), "abstained": abstained,
            "abstain_rate": round(abstained / len(scored), 4) if scored else None,
            "decided": len(decided),
            "error_rate": round(errs / len(decided), 4) if decided else None,
            "errors": errs}


def main() -> int:
    """Run the selected arms over the frozen sheet and write the comparison artifact."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, choices=sorted(ARMS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--source", default=None,
                    help="label source name from bakeoff.sources (default: bakeoff.active_source)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    global _DEVICE_CFG
    cfg = load_config()
    _DEVICE_CFG = str(cfg.get("device", "auto"))
    src = source_spec(cfg, args.source)
    limit = args.limit or int(src.get("limit") or cfg["limit"])
    rows, truth = load_rows(cfg, limit, src)
    out_path = Path(args.out or src.get("output") or OUT)
    print("source=" + src["name"] + " sheet=" + src["sheet"] + " rows=" + str(len(rows)) +
          " axis=" + src["axis"] + " truth=" + str(len([r for r in rows if r['fb_id'] in truth])))

    results: dict[str, dict] = {}
    for name in args.arm:
        try:
            preds = ARMS[name](rows, truth, cfg=cfg, spec=src)
            res = score(preds, truth)
            # BUG-321: persist the per-row MARGIN, not just the label - without it no calibrated
            # abstention curve and no "why did this arm fail" audit is possible from the artifact.
            res["predictions"] = {k: ([v[0], v[1]] if isinstance(v, (tuple, list)) and len(v) > 1 else v[0]
                                     if isinstance(v, (tuple, list)) else v)
                                 for k, v in preds.items()}
        except NotImplementedError as exc:
            res = {"n": len(rows), "stub": str(exc)}
        results[name] = res
        print(name + ": " + json.dumps({k: v for k, v in res.items() if k != "predictions"}),
              flush=True)
        # checkpoint per arm: a crash in a later arm must not discard a finished arm (BUG-318b)
        arms = dict(results)
        if out_path.exists():   # BUG-323: merge at write - an arm measured in an earlier run must survive
            try:
                prev = json.loads(out_path.read_text(encoding="utf-8"))
                # BUG-332: never merge across SOURCES - an anchor2 artifact must not swallow ruler arms
                if str(prev.get("source") or RULER_SOURCE) == src["name"]:
                    for k, v in (prev.get("arms") or {}).items():
                        arms.setdefault(k, v)
                else:
                    print("  WARN artifact holds source " + str(prev.get("source")) +
                          "; not merging into " + src["name"], file=sys.stderr)
            except Exception as exc:  # noqa: BLE001 - no silent errors (C16)
                print("  WARN could not merge previous artifact: " + str(exc), file=sys.stderr)
        stamp: dict = {"schema_version": "1.0", "source": src["name"], "sheet": src["sheet"],
                       "key": src["key"], "axis": src["axis"], "limit": limit,
                       "spec": {k: v for k, v in src.items() if k != "key_truth_fields"},
                       "arms": arms}
        try:
            from pipeline.closed_menu import menu_hash as _mh
            stamp["menu_hash"] = _mh()
        except Exception as exc:  # noqa: BLE001 (C16)
            print("  WARN menu_hash unavailable: " + str(exc), file=sys.stderr)
        out_path.write_text(json.dumps(stamp, indent=1), encoding="utf-8")
    print("wrote " + str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
