#!/usr/bin/env python3
"""scripts/calibrate_classifier.py — D2585 P4 temperature scaling + conformal/selective abstention.

Loads a trained DisciplineClassifier checkpoint, reproduces the trainer's
stratified held-out split (same RANDOM_STATE / TRAIN_TEST_SPLIT_SIZE so the
macro-F1 is directly comparable to the training report), then:

  1. Fits a scalar temperature T on a calibration slice of the test logits
     (NLL-minimizing — the standard Platt-style temperature scaling);
  2. Reports discipline macro-F1 + ECE at T=1 (raw) vs T=T* (scaled);
  3. Builds the selective-prediction risk-coverage curve (abstain by
     temperature-scaled confidence) — D2585 "selective prediction for the
     61-way rare classes";
  4. Reports split-conformal abstention: the calibration quantile that yields
     (1-alpha) coverage, with the implied coverage / set size on the eval slice.

Usage:
  python3 scripts/calibrate_classifier.py \
      --checkpoint "knowledge pipeline/classifier_modernbert_p4" \
      --golden config/golden/stage4_golden_mined_p4.yaml

Read-only. Writes governance/classifier_calibration.{json,md} (+ name suffix).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

# Heavy module — import the pieces we must mirror EXACTLY.
from train_discipline_classifier import (  # noqa: E402
    BASE_MODEL_NAME,
    BATCH_SIZE,
    NUM_DISCIPLINE_CLASSES,
    RANDOM_STATE,
    TRAIN_TEST_SPLIT_SIZE,
    DisciplineClassifier,
    GoldenDataset,
    _filter_trainable,
    build_model,
    load_golden_set,
)

_GOV_DIR = _ROOT / "governance"


def _ece(labels: np.ndarray, preds: np.ndarray, conf: np.ndarray, n_bins: int = 10) -> float:
    """Expected calibration error over equal-width confidence bins.

    ECE = sum_b (|bin_b| / n) * |acc(bin_b) - mean_conf(bin_b)|.
    """
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        m = (conf >= lo) & (conf < hi)
        if not m.any():
            continue
        bin_acc = float((preds[m] == labels[m]).mean())
        ece += (m.sum() / len(conf)) * abs(bin_acc - float(conf[m].mean()))
    return float(ece)


def _macro_f1(labels: np.ndarray, logits: np.ndarray, temperature: float) -> float:
    """Macro-F1 of argmax(logits / T) over the fixed 61-class head."""
    probs = _softmax(logits / temperature)
    preds = probs.argmax(axis=1)
    return float(f1_score(labels, preds, labels=list(range(NUM_DISCIPLINE_CLASSES)),
                          average="macro", zero_division=0))


def _softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def _fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Grid-then-refine search for the NLL-minimizing temperature."""
    def nll(t: float) -> float:
        p = _softmax(logits / t)
        n = np.arange(len(labels))
        return float(-np.log(p[n, labels] + 1e-12).mean())

    best_t, best_nll = 1.0, nll(1.0)
    for t in np.linspace(0.3, 5.0, 48):
        v = nll(t)
        if v < best_nll:
            best_nll, best_t = v, t
    # local refine
    for _ in range(3):
        for t in (best_t * 0.9, best_t * 1.1):
            v = nll(t)
            if v < best_nll:
                best_nll, best_t = v, t
    return float(best_t)


def _run_inference(model: torch.nn.Module, loader: DataLoader, device: torch.device):
    """Return (labels, discipline_logits) over the loader."""
    model.eval()
    labels: list[int] = []
    logits: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attn = batch["attention_mask"].to(device)
            disc_logits, _ = model(input_ids, attn)
            labels.extend(batch["discipline_label"].tolist())
            logits.append(disc_logits.float().cpu().numpy())
    return np.array(labels), np.vstack(logits)


def main() -> int:
    ap = argparse.ArgumentParser(description="P4 calibration (temp + conformal)")
    ap.add_argument("--checkpoint", required=True, help="Checkpoint dir (model_state.pt)")
    ap.add_argument("--golden", default="config/golden/stage4_golden_mined_p4.yaml")
    ap.add_argument("--name", default="p4", help="Suffix for governance outputs")
    ap.add_argument("--alpha", type=float, default=0.1, help="Conformal 1-alpha coverage")
    args = ap.parse_args()

    ckpt = Path(args.checkpoint)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    # Rebuild the trainer's exact split.
    golden = load_golden_set(str(_ROOT / args.golden))
    examples = _filter_trainable(golden["examples"], 5)
    disciplines = sorted({ex["discipline"] for ex in examples})
    disc_map = {d: i for i, d in enumerate(disciplines)}
    inv_map = {i: d for d, i in disc_map.items()}
    labels_arr = np.array([disc_map[ex["discipline"]] for ex in examples])
    idx = np.arange(len(examples))
    _, test_idx = train_test_split(idx, test_size=TRAIN_TEST_SPLIT_SIZE,
                                   random_state=RANDOM_STATE, stratify=labels_arr)
    test_examples = [examples[i] for i in test_idx]
    print(f"test examples: {len(test_examples)} | classes: {len(disciplines)}")

    tokenizer, model = build_model(BASE_MODEL_NAME)
    state = torch.load(ckpt / "model_state.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(state)
    model.to(device)

    test_ds = GoldenDataset(test_examples, tokenizer, disc_map, {})
    loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)
    labels, logits = _run_inference(model, loader, device)
    print(f"inference done: {len(labels)} samples")

    # Calibration / eval split of the TEST slice (fixed seed, random — the test
    # set has singleton classes (206 ex / 61 classes) so stratify is impossible).
    cal_idx, ev_idx = train_test_split(
        np.arange(len(labels)), test_size=0.5, random_state=0,
    )
    cal_logits, cal_labels = logits[cal_idx], labels[cal_idx]
    ev_logits, ev_labels = logits[ev_idx], labels[ev_idx]

    t_star = _fit_temperature(cal_logits, cal_labels)
    f1_raw = _macro_f1(ev_labels, ev_logits, 1.0)
    f1_cal = _macro_f1(ev_labels, ev_logits, t_star)

    # Confidence + ECE at T*.
    p_ev = _softmax(ev_logits / t_star)
    conf = p_ev.max(axis=1)
    pred = p_ev.argmax(axis=1)
    acc = float((pred == ev_labels).mean())
    ece = _ece(ev_labels, pred, conf)

    # Selective risk-coverage curve.
    order = np.argsort(-conf)
    cover_curve: dict[str, float] = {}
    for cov in (1.0, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5):
        k = int(round(cov * len(ev_labels)))
        k = max(k, 1)
        sel_labels, sel_logits = ev_labels[order[:k]], ev_logits[order[:k]]
        cover_curve[str(cov)] = _macro_f1(sel_labels, sel_logits, t_star)

    # Split-conformal (score = 1 - p_true_class): threshold from calibration.
    p_cal = _softmax(cal_logits / t_star)
    scores_cal = 1.0 - p_cal[np.arange(len(cal_labels)), cal_labels]
    q_level = np.ceil((len(scores_cal) + 1) * (1.0 - args.alpha)) / len(scores_cal)
    q_hat = float(np.quantile(scores_cal, min(q_level, 1.0)))
    # Prediction set: classes with p_c >= 1 - q_hat (split-conformal, marginal
    # coverage >= 1-alpha). Size-1 sets = confident prediction; >1 = ambiguous.
    set_sizes = (p_ev >= (1.0 - q_hat)).sum(axis=1)
    set_coverage = _set_coverage(p_ev, ev_labels, q_hat)
    out = {
        "checkpoint": str(ckpt),
        "golden": args.golden,
        "n_test": int(len(labels)),
        "n_calib": int(len(cal_labels)),
        "n_eval": int(len(ev_labels)),
        "temperature_T_star": round(t_star, 4),
        "macro_f1_raw_T1": round(f1_raw, 4),
        "macro_f1_temp_scaled": round(f1_cal, 4),
        "delta_f1_temperature": round(f1_cal - f1_raw, 4),
        "eval_accuracy_at_T_star": round(acc, 4),
        "eval_ece_at_T_star": round(ece, 4),
        "selective_macro_f1_by_coverage": {k: round(v, 4) for k, v in cover_curve.items()},
        "conformal": {
            "alpha": args.alpha,
            "q_hat": round(q_hat, 4),
            "avg_set_size": round(float(set_sizes.mean()), 3),
            "empirical_coverage": round(set_coverage, 4),
        },
    }
    _GOV_DIR.mkdir(exist_ok=True)
    (_GOV_DIR / f"classifier_calibration_{args.name}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )
    md = [
        f"# CLASSIFIER CALIBRATION — {args.name} (D2585 P4)",
        "",
        f"Checkpoint: `{ckpt}`  |  golden: `{args.golden}`",
        "",
        "| metric | value |",
        "|---|---|",
        f"| temperature T* | {out['temperature_T_star']} |",
        f"| macro-F1 @T=1 | {out['macro_f1_raw_T1']} |",
        f"| macro-F1 @T* | {out['macro_f1_temp_scaled']} (Δ {out['delta_f1_temperature']:+}) |",
        f"| eval accuracy @T* | {out['eval_accuracy_at_T_star']} |",
        f"| ECE @T* | {out['eval_ece_at_T_star']} |",
        "",
        "## Selective macro-F1 by coverage (abstain low-confidence, @T*)",
        "",
        "| coverage | macro-F1 |",
        "|---|---|",
        *[f"| {c} | {v} |" for c, v in cover_curve.items()],
        "",
        f"## Conformal abstention (α={args.alpha})",
        "",
        f"q_hat = {out['conformal']['q_hat']} | avg set size = "
        f"{out['conformal']['avg_set_size']} | empirical coverage = "
        f"{out['conformal']['empirical_coverage']}",
        "",
    ]
    (_GOV_DIR / f"classifier_calibration_{args.name}.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    print(json.dumps(out, indent=2))
    return 0


def _set_coverage(p: np.ndarray, labels: np.ndarray, q_hat: float) -> float:
    """Fraction of eval rows whose true class is in the conformal set."""
    in_set = p[np.arange(len(p)), labels] >= (1.0 - q_hat)
    return float(in_set.mean())


if __name__ == "__main__":
    raise SystemExit(main())
