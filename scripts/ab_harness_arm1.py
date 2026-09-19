#!/usr/bin/env python3
"""ab_harness_arm1.py — D2618 A/B harness ARM-1 (+ARM-3 abstention) on gold_4axis.

Evaluates the EXISTING classifier checkpoints on the FROZEN verified 4-axis core
(governance/gold_4axis.jsonl) — contract-first authority (D2618 P0.5), never the
silver stage4_golden_mined.yaml.

  ARM-1a  flat:          classifier_modernbert_p5final  (dual-head 56 discipline / 43 domain)
  ARM-1b  hierarchical:  classifier_hierarchical        (coarse 10 + fine 56 + domain 43)

Metrics (identical across arms, D2618): discipline macro-F1, domain macro-F1
(multi-label), and ARM-3 abstention risk-coverage (coverage@precision at abstain
thresholds on softmax confidence).

Read-only: loads checkpoints, runs inference, writes governance/ab_harness_arm1.json.
NO training, NO DB writes. The gold_4axis split is never mutated.

Usage:
  python3 scripts/ab_harness_arm1.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from train_discipline_classifier import (  # noqa: E402
    BASE_MODEL_NAME, BATCH_SIZE, MAX_LENGTH,
    DisciplineClassifier, load_gold_4axis,
)
from train_hierarchical_classifier import (  # noqa: E402
    HierarchicalClassifier, _masked_fine_pred,
)

# ── C12/C20: named constants ───────────────────────────────────────────────
GOLD_EVAL = ROOT / "governance" / "gold_4axis.jsonl"
FLAT_CKPT = ROOT / "knowledge pipeline" / "classifier_modernbert_p5final"
HIER_CKPT = ROOT / "knowledge pipeline" / "classifier_hierarchical"
OUT = ROOT / "governance" / "ab_harness_arm1.json"

DEVICE = torch.device("mps") if (
    getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
) else torch.device("cuda" if torch.cuda.is_available() else "cpu")

DOMAIN_THRESHOLD = 0.5
ABSTAIN_STEPS = (0.0, 0.35, 0.50, 0.70, 0.80, 0.90)


def _invert(idx_to_name: Dict[str, str]) -> Dict[str, int]:
    return {name: int(idx) for idx, name in idx_to_name.items()}


def _text(ex: Dict[str, Any]) -> str:
    t = f"{ex['name']}: {ex['definition']}"
    if ex.get("mechanism"):
        t += f" Mechanism: {ex['mechanism']}"
    if ex.get("boundary"):
        t += f" Boundary: {ex['boundary']}"
    return t


class _InferDataset(Dataset):
    def __init__(self, examples: List[Dict[str, Any]], tokenizer: AutoTokenizer) -> None:
        self.examples = examples
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        enc = self.tokenizer(_text(self.examples[idx]), max_length=MAX_LENGTH,
                             padding="max_length", truncation=True, return_tensors="pt")
        return {"input_ids": enc["input_ids"].squeeze(0),
                "attention_mask": enc["attention_mask"].squeeze(0)}


def _discipline_conf_and_pred(logits: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()
    conf = probs.max(axis=-1)
    pred = probs.argmax(axis=-1)
    return conf, pred


def _risk_coverage(labels: np.ndarray, preds: np.ndarray, conf: np.ndarray,
                   n_classes: int) -> List[Dict[str, Any]]:
    """Abstention risk-coverage: abstain where confidence < threshold."""
    out = []
    for t in ABSTAIN_STEPS:
        keep = conf >= t
        if keep.sum() == 0:
            out.append({"threshold": t, "coverage": 0.0, "precision": None,
                        "macro_f1": None, "abstain_rate": 1.0})
            continue
        preds_k = preds[keep]
        labels_k = labels[keep]
        prec = float((preds_k == labels_k).mean())
        f1 = float(f1_score(labels_k, preds_k, average="macro",
                            labels=list(range(n_classes)), zero_division=0))
        out.append({
            "threshold": t,
            "coverage": float(keep.sum() / len(labels)),
            "precision": prec,
            "macro_f1": f1,
            "abstain_rate": float(1.0 - keep.sum() / len(labels)),
        })
    return out


def _load_model(ckpt: Path, hierarchical: bool):
    maps = json.loads((ckpt / "label_maps.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(str(ckpt))
    backbone = AutoModel.from_pretrained(BASE_MODEL_NAME)
    state = torch.load(str(ckpt / "model_state.pt"), map_location="cpu")
    # Infer TRUE head sizes from the saved state_dict (label_maps.json may
    # under-report n_discipline: 56 labelable classes vs 61-wide raw head).
    n_disc = int(state["discipline_head.weight"].shape[0])
    n_dom = int(state["domain_head.weight"].shape[0])
    disc_map = _invert(maps["idx_to_discipline"])
    dom_map = _invert(maps["idx_to_domain"])

    if hierarchical:
        n_coarse = int(state["coarse_head.weight"].shape[0])
        coarse_to_disc = {int(k): [int(x) for x in v]
                          for k, v in maps["coarse_to_discipline_idxs"].items()}
        model = HierarchicalClassifier(backbone=backbone, num_coarse=n_coarse,
                                       num_discipline=n_disc, num_domain=n_dom)
        model.load_state_dict(state)
        model.to(DEVICE)
        return model, tokenizer, disc_map, dom_map, n_disc, n_dom, coarse_to_disc
    model = DisciplineClassifier(backbone=backbone, num_discipline=n_disc, num_domain=n_dom)
    model.load_state_dict(state)
    model.to(DEVICE)
    return model, tokenizer, disc_map, dom_map, n_disc, n_dom, None


def _run_arm(examples: List[Dict[str, Any]], ckpt: Path, hierarchical: bool) -> Dict[str, Any]:
    model, tokenizer, disc_map, dom_map, n_disc, n_dom, coarse_to_disc = \
        _load_model(ckpt, hierarchical)
    ds = _InferDataset(examples, tokenizer)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False)

    disc_true: List[int] = []
    disc_pred: List[int] = []
    disc_conf: List[float] = []
    dom_pred_all: List[np.ndarray] = []
    dom_true_all: List[np.ndarray] = []

    model.eval()
    with torch.no_grad():
        for batch in loader:
            ids = batch["input_ids"].to(DEVICE)
            mask = batch["attention_mask"].to(DEVICE)
            if hierarchical:
                c_logits, d_logits, m_logits = model(ids, mask)
                c_pred = c_logits.argmax(dim=-1).cpu().numpy()
                d_flat_pred = d_logits.argmax(dim=-1).cpu().numpy()
                d_pred = _masked_fine_pred(d_logits, c_pred, coarse_to_disc)
                d_conf = torch.softmax(d_logits, dim=-1).max(dim=-1).values.cpu().numpy()
            else:
                d_logits, m_logits = model(ids, mask)
                d_pred = d_logits.argmax(dim=-1).cpu().numpy()
                d_conf = torch.softmax(d_logits, dim=-1).max(dim=-1).values.cpu().numpy()
            dom_probs = torch.sigmoid(m_logits).cpu().numpy()

            # Predictions are recorded in-order (DataLoader shuffle=False == example
            # order); truth is derived in-order below and aligned positionally.
            disc_pred.extend(d_pred.tolist())
            disc_conf.extend(d_conf.tolist())
            dom_pred_all.append((dom_probs >= DOMAIN_THRESHOLD).astype(int))
    # Truth labels (in-order) from the examples.
    disc_true = [disc_map.get(ex["discipline"], -1) for ex in examples]
    # drop OOV discipline rows (label not in this checkpoint's 56-class map)
    keep_disc = [i for i, t in enumerate(disc_true) if t >= 0]
    disc_true_a = np.array([disc_true[i] for i in keep_disc])
    disc_pred_a = np.array([disc_pred[i] for i in keep_disc])
    disc_conf_a = np.array([disc_conf[i] for i in keep_disc])

    dom_true = np.zeros((len(examples), n_dom))
    for i, ex in enumerate(examples):
        for d in ex.get("domains", []):
            if d in dom_map:
                dom_true[i, dom_map[d]] = 1.0
    dom_pred = np.vstack(dom_pred_all)

    macro_f1_disc = float(f1_score(disc_true_a, disc_pred_a, average="macro",
                                   labels=list(range(n_disc)), zero_division=0))
    dom_f1_macro = float(f1_score(dom_true, dom_pred, average="macro", zero_division=0))
    dom_f1_micro = float(f1_score(dom_true, dom_pred, average="micro", zero_division=0))
    rc = _risk_coverage(disc_true_a, disc_pred_a, disc_conf_a, n_disc)

    return {
        "checkpoint": str(ckpt),
        "architecture": "hierarchical" if hierarchical else "flat",
        "n_eval": len(examples),
        "n_disc_oov": int(len(examples) - len(keep_disc)),
        "n_disc_eval": int(len(keep_disc)),
        "discipline_macro_f1": macro_f1_disc,
        "domain_macro_f1": dom_f1_macro,
        "domain_micro_f1": dom_f1_micro,
        "abstention_risk_coverage": rc,
    }


def main() -> int:
    global DEVICE
    ap = argparse.ArgumentParser()
    ap.add_argument("--flat", default=str(FLAT_CKPT))
    ap.add_argument("--hier", default=str(HIER_CKPT))
    ap.add_argument("--gold", default=str(GOLD_EVAL))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--device", default=str(DEVICE), help="torch device (cpu avoids OMLX GPU contention)")
    args = ap.parse_args()
    DEVICE = torch.device(args.device)

    loaded = load_gold_4axis(args.gold)
    examples = loaded["examples"]
    print(f"gold_4axis eval examples: {len(examples)} (device={DEVICE})")

    arms = [
        _run_arm(examples, Path(args.flat), hierarchical=False),
        _run_arm(examples, Path(args.hier), hierarchical=True),
    ]

    result = {
        "gold_eval": args.gold,
        "n_examples": len(examples),
        "device": str(DEVICE),
        "arms": arms,
        "policy": "D2618 ARM-1 classifier architecture + ARM-3 abstention on frozen gold_4axis",
    }

    print("\n=== ARM-1 discipline/domain architecture comparison (gold_4axis) ===")
    for a in arms:
        print(f"\n{a['architecture']:14} {a['checkpoint']}")
        print(f"  eval rows: {a['n_disc_eval']} (OOV {a['n_disc_oov']})")
        print(f"  discipline macro-F1: {a['discipline_macro_f1']:.4f}")
        print(f"  domain macro-F1:     {a['domain_macro_f1']:.4f}")
        print(f"  domain micro-F1:     {a['domain_micro_f1']:.4f}")
        print(f"  abstention risk-coverage (threshold | coverage | precision | macro-F1):")
        for rc in a["abstention_risk_coverage"]:
            p = f"{rc['precision']:.3f}" if rc["precision"] is not None else "  -  "
            f = f"{rc['macro_f1']:.3f}" if rc["macro_f1"] is not None else "  -  "
            print(f"    t={rc['threshold']:.2f}  cov={rc['coverage']:.3f}  prec={p}  f1={f}")

    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
