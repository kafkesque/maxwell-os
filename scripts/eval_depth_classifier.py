#!/usr/bin/env python3
"""eval_depth_classifier.py — evaluate a trained depth checkpoint on a labelled set.

Loads a depth classifier checkpoint (`knowledge pipeline/classifier_depth*`) and
computes macro-F1 / per-class F1 / confusion against an INDEPENDENT labelled YAML.
Used for the D2577 controlled comparison: the same FBs + same held-out test set
are scored against different TRAINING label sources (clean vote vs gpt-oss silver)
so the effect of label cleaning is isolated from class-proportion effects.

Usage:
    python3 scripts/eval_depth_classifier.py \
        --checkpoint "knowledge pipeline/classifier_depth_clean" \
        --eval-yaml governance/depth_clean_test.yaml \
        --out governance/depth_eval_clean.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
for p in (str(ROOT), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402
from train_depth_classifier import (  # noqa: E402
    BASE_MODEL_NAME,
    BATCH_SIZE,
    DepthClassifier,
    DepthDataset,
    _device,
    evaluate,
    load_depth_examples,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--eval-yaml", required=True)
    ap.add_argument("--out", default="", help="optional JSON output path")
    args = ap.parse_args()

    ckpt = Path(args.checkpoint)
    maps = json.loads((ckpt / "label_maps.json").read_text(encoding="utf-8"))
    depth_label_map: Dict[str, int] = {k: int(v) for k, v in maps["depth_to_idx"].items()}
    idx_to_depth: Dict[int, str] = {int(k): v for k, v in maps["idx_to_depth"].items()}
    ordered = [idx_to_depth[i] for i in range(len(idx_to_depth))]

    examples = load_depth_examples(args.eval_yaml)
    tokenizer = AutoTokenizer.from_pretrained(str(ckpt))
    backbone = AutoModel.from_pretrained(BASE_MODEL_NAME)
    model = DepthClassifier(backbone=backbone, num_depth=len(depth_label_map))
    model.load_state_dict(torch.load(str(ckpt / "model_state.pt"), map_location="cpu"))

    device = _device()
    model.to(device)  # inputs are moved to `device` in evaluate() — model must match
    dataset = DepthDataset(examples, tokenizer, depth_label_map)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False)
    metrics = evaluate(model, loader, device)

    result = {
        "checkpoint": str(ckpt),
        "eval_yaml": args.eval_yaml,
        "n_examples": len(examples),
        "macro_f1_depth": metrics["macro_f1_depth"],
        "per_class_f1_depth": dict(zip(ordered, metrics["per_class_f1_depth"])),
        "test_rows_per_class": metrics["confusion_matrix"].sum(axis=1).tolist(),
        "confusion_matrix": metrics["confusion_matrix"].tolist(),
        "classes": ordered,
        # R14 stamps.
        "schema_version": SCHEMA_VERSION,
        "gen_model": BASE_MODEL_NAME,
        "pipeline_commit": PIPELINE_COMMIT,
    }

    print(f"checkpoint: {ckpt.name}")
    print(f"eval set:   {args.eval_yaml} ({len(examples)} examples)")
    print(f"macro-F1:   {result['macro_f1_depth']:.4f}")
    for c, f1 in result["per_class_f1_depth"].items():
        print(f"  {c:<14} F1 {f1:.3f}  (n={result['test_rows_per_class'][ordered.index(c)]})")
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
