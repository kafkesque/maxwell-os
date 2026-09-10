#!/usr/bin/env python3
"""train_hierarchical_classifier.py — D2607 (B): hierarchical discipline classifier.

Coarse 10-way group head + fine 61-way discipline head + 43-way domain head on a
shared ModernBERT backbone. At inference the coarse head picks the group, then the
fine head re-ranks WITHIN that group (out-of-group logits masked to -inf), shrinking
the confusion set from 61 -> <=15 and concentrating signal on confusable siblings.

Reuses the flat trainer's data-loading/eval utilities (scripts/train_discipline_classifier.py)
to avoid drift; adds the coarse head + masked-fine evaluation.

Checkpoint artifacts (self-contained, no live-golden reconstruction):
  model_state.pt, tokenizer/, metrics.yaml, label_maps.json (idx_to_coarse /
  idx_to_discipline / idx_to_domain / discipline_to_coarse_idx /
  coarse_to_discipline_idxs), discipline_groups.json (group -> [disciplines]).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
for p in (str(ROOT), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Reuse the flat trainer's helpers/constants (single source of truth, no drift).
from train_discipline_classifier import (  # noqa: E402
    BASE_MODEL_NAME,
    BATCH_SIZE,
    LEARNING_RATE,
    MAX_LENGTH,
    MIN_EXAMPLES_PER_CLASS,
    MIN_GOLDEN_EXAMPLES,
    NUM_DISCIPLINE_CLASSES,
    NUM_DOMAIN_CLASSES,
    NUM_EPOCHS,
    RANDOM_STATE,
    TARGET_MACRO_F1,
    TRAIN_TEST_SPLIT_SIZE,
    WARMUP_RATIO,
    WEIGHT_DECAY,
    WORST_CLASSES_TO_LOG,
    _filter_trainable,
    _save_confusion_matrix,
    compute_class_weights,
    load_golden_set,
    save_checkpoint,
)

# R14 stamps (single source of truth: pipeline_paths).
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

# C20: named constant for gradient clipping (no magic 1.0).
GRAD_CLIP_NORM: float = 1.0

# C12: paths overridable via env (same convention as the flat trainer).
TAXONOMY = Path(os.environ.get("TAXONOMY_YAML", ROOT / "config" / "taxonomy_v5.yaml"))
GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
CHECKPOINT = ROOT / "knowledge pipeline" / "classifier_hierarchical"


def load_discipline_groups() -> Dict[str, List[str]]:
    """Return {coarse_group_name: [discipline canonical, ...]} from taxonomy."""
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    groups = data.get("discipline_groups") or {}
    if not groups:
        raise ValueError("taxonomy_v5.yaml has no discipline_groups (D2607 B)")
    return {str(k): [str(d) for d in v] for k, v in groups.items()}


class HierarchicalClassifier(nn.Module):
    """Shared ModernBERT backbone + coarse (10) / fine discipline (61) / domain (43) heads."""

    def __init__(self, backbone: nn.Module, num_coarse: int,
                 num_discipline: int = NUM_DISCIPLINE_CLASSES,
                 num_domain: int = NUM_DOMAIN_CLASSES) -> None:
        super().__init__()
        self.backbone = backbone
        hidden = backbone.config.hidden_size
        self.coarse_head = nn.Linear(hidden, num_coarse)
        self.discipline_head = nn.Linear(hidden, num_discipline)
        self.domain_head = nn.Linear(hidden, num_domain)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor
                ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls_repr = out.last_hidden_state[:, 0, :]
        return (self.coarse_head(cls_repr), self.discipline_head(cls_repr),
                self.domain_head(cls_repr))


class HierarchicalDataset(Dataset):
    """Golden examples + coarse/fine/domain labels, tokenized."""

    def __init__(self, examples: List[Dict[str, Any]], tokenizer: AutoTokenizer,
                 coarse_label_map: Dict[str, int], discipline_label_map: Dict[str, int],
                 domain_label_map: Dict[str, int], discipline_to_coarse: Dict[str, int],
                 max_length: int = MAX_LENGTH) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.coarse_label_map = coarse_label_map
        self.discipline_label_map = discipline_label_map
        self.domain_label_map = domain_label_map
        self.discipline_to_coarse = discipline_to_coarse
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        ex = self.examples[idx]
        text = f"{ex['name']}: {ex['definition']}"
        if ex.get("mechanism"):
            text += f" Mechanism: {ex['mechanism']}"
        if ex.get("boundary"):
            text += f" Boundary: {ex['boundary']}"
        enc = self.tokenizer(text, max_length=self.max_length, padding="max_length",
                             truncation=True, return_tensors="pt")
        discipline_id = self.discipline_label_map.get(ex["discipline"], 0)
        coarse_id = self.discipline_to_coarse.get(ex["discipline"], 0)
        domain_labels = torch.zeros(NUM_DOMAIN_CLASSES)
        for d in ex.get("domains", []):
            if d in self.domain_label_map:
                domain_labels[self.domain_label_map[d]] = 1.0
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "coarse_label": torch.tensor(coarse_id, dtype=torch.long),
            "discipline_label": torch.tensor(discipline_id, dtype=torch.long),
            "domain_labels": domain_labels,
        }


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _masked_fine_pred(fine_logits: torch.Tensor, coarse_pred: np.ndarray,
                      coarse_to_disc_idxs: Dict[int, List[int]]) -> np.ndarray:
    """Argmax of fine logits restricted to the predicted coarse group's members."""
    fine = fine_logits.clone()
    for i, g in enumerate(coarse_pred):
        allowed = coarse_to_disc_idxs.get(int(g), [])
        mask = torch.full((fine.size(1),), float("-inf"), device=fine.device)
        for a in allowed:
            mask[a] = 0.0
        fine[i] = fine[i] + mask
    return fine.argmax(dim=-1).cpu().numpy()


def evaluate(model: nn.Module, dataloader: DataLoader, device: torch.device,
             coarse_to_disc_idxs: Dict[int, List[int]],
             num_coarse: int) -> Dict[str, float]:
    """Compute coarse / flat-fine / masked-fine / domain macro-F1."""
    model.eval()
    coarse_preds, coarse_trues = [], []
    flat_preds, masked_preds, disc_trues = [], [], []
    dom_preds, dom_trues = [], []
    with torch.no_grad():
        for batch in dataloader:
            c_logits, d_logits, m_logits = model(batch["input_ids"].to(device),
                                                 batch["attention_mask"].to(device))
            c_pred = c_logits.argmax(dim=-1).cpu().numpy()
            d_flat = d_logits.argmax(dim=-1).cpu().numpy()
            d_masked = _masked_fine_pred(d_logits, c_pred, coarse_to_disc_idxs)
            coarse_preds.extend(c_pred.tolist())
            coarse_trues.extend(batch["coarse_label"].numpy().tolist())
            flat_preds.extend(d_flat.tolist())
            masked_preds.extend(d_masked.tolist())
            disc_trues.extend(batch["discipline_label"].numpy().tolist())
            dom_preds.append((torch.sigmoid(m_logits) >= 0.5).cpu().numpy().astype(int))
            dom_trues.append(batch["domain_labels"].numpy())

    coarse_macro = f1_score(coarse_trues, coarse_preds, average="macro",
                            labels=list(range(num_coarse)), zero_division=0)
    flat_macro = f1_score(disc_trues, flat_preds, average="macro",
                          labels=list(range(NUM_DISCIPLINE_CLASSES)), zero_division=0)
    masked_macro = f1_score(disc_trues, masked_preds, average="macro",
                            labels=list(range(NUM_DISCIPLINE_CLASSES)), zero_division=0)
    dom_preds = np.vstack(dom_preds)
    dom_trues = np.vstack(dom_trues)
    dom_f1 = float(f1_score(dom_trues, dom_preds, average="macro", zero_division=0))
    return {
        "macro_f1_coarse": float(coarse_macro),
        "macro_f1_discipline_flat": float(flat_macro),
        "macro_f1_discipline_hierarchical": float(masked_macro),
        "macro_f1_domain": dom_f1,
    }


def train(model: nn.Module, train_loader: DataLoader, val_loader: DataLoader,
          coarse_weights: torch.Tensor, disc_weights: torch.Tensor,
          device: torch.device, coarse_to_disc_idxs: Dict[int, List[int]],
          num_coarse: int) -> Dict[str, float]:
    """Multi-task train: coarse CE + discipline CE (class-weighted) + domain BCE."""
    model.to(device)
    coarse_weights = coarse_weights.to(device)
    disc_weights = disc_weights.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE,
                                  weight_decay=WEIGHT_DECAY)
    total_steps = len(train_loader) * NUM_EPOCHS
    warmup = int(total_steps * WARMUP_RATIO)

    def lr_lambda(step: int) -> float:
        if step < warmup:
            return step / max(1, warmup)
        return max(0.0, 1.0 - (step - warmup) / max(1, total_steps - warmup))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    for epoch in range(NUM_EPOCHS):
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            c_labels = batch["coarse_label"].to(device)
            d_labels = batch["discipline_label"].to(device)
            m_labels = batch["domain_labels"].to(device)

            c_logits, d_logits, m_logits = model(input_ids, attention_mask)

            c_loss = (F.cross_entropy(c_logits, c_labels, reduction="none")
                      * coarse_weights[c_labels]).mean()
            d_loss = (F.cross_entropy(d_logits, d_labels, reduction="none")
                      * disc_weights[d_labels]).mean()
            m_loss = F.binary_cross_entropy_with_logits(m_logits, m_labels)
            loss = c_loss + d_loss + m_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP_NORM)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        print(f"epoch {epoch + 1}/{NUM_EPOCHS} avg loss {total_loss / len(train_loader):.4f}",
              flush=True)

    return evaluate(model, val_loader, device, coarse_to_disc_idxs, num_coarse)


def _atomic_write_json(path: Path, obj: Any) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main() -> None:
    groups = load_discipline_groups()
    coarse_names = sorted(groups.keys())
    coarse_label_map = {g: i for i, g in enumerate(coarse_names)}

    golden = load_golden_set(os.environ.get("GOLDEN_YAML", str(GOLDEN)))
    examples = _filter_trainable(golden["examples"], MIN_EXAMPLES_PER_CLASS)

    disciplines = sorted({ex["discipline"] for ex in examples})
    domains = sorted({d for ex in examples for d in ex.get("domains", []) if d})
    discipline_label_map = {d: i for i, d in enumerate(disciplines)}
    for i in range(len(disciplines), NUM_DISCIPLINE_CLASSES):
        discipline_label_map[f"__pad_{i}"] = i
    domain_label_map = {d: i for i, d in enumerate(domains)}
    for i in range(len(domains), NUM_DOMAIN_CLASSES):
        domain_label_map[f"__pad_{i}"] = i

    # discipline -> coarse group (name -> idx), only over trainable disciplines.
    group_of: Dict[str, str] = {}
    for gname, disc_list in groups.items():
        for d in disc_list:
            group_of[d] = gname
    discipline_to_coarse = {
        d: coarse_label_map[group_of[d]] for d in disciplines if d in group_of
    }
    coarse_to_disc_idxs: Dict[int, List[int]] = {}
    for d in disciplines:
        gi = discipline_to_coarse.get(d)
        if gi is None:
            continue
        coarse_to_disc_idxs.setdefault(gi, []).append(discipline_label_map[d])

    print(f"coarse groups: {len(coarse_names)} | trainable disciplines: {len(disciplines)} "
          f"| domains: {len(domains)}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
    base = AutoModel.from_pretrained(BASE_MODEL_NAME)
    model = HierarchicalClassifier(base, num_coarse=len(coarse_names))

    dataset = HierarchicalDataset(examples, tokenizer, coarse_label_map,
                                  discipline_label_map, domain_label_map,
                                  discipline_to_coarse)
    labels = np.array([discipline_label_map[ex["discipline"]] for ex in examples])
    coarse_labels = np.array([discipline_to_coarse.get(ex["discipline"], 0) for ex in examples])
    indices = np.arange(len(examples))
    train_idx, test_idx = train_test_split(indices, test_size=TRAIN_TEST_SPLIT_SIZE,
                                           random_state=RANDOM_STATE, stratify=labels)
    train_examples = [examples[i] for i in train_idx]
    test_examples = [examples[i] for i in test_idx]

    train_ds = HierarchicalDataset(train_examples, tokenizer, coarse_label_map,
                                   discipline_label_map, domain_label_map,
                                   discipline_to_coarse)
    test_ds = HierarchicalDataset(test_examples, tokenizer, coarse_label_map,
                                  discipline_label_map, domain_label_map,
                                  discipline_to_coarse)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    coarse_weights = compute_class_weights(coarse_labels[train_idx], len(coarse_names))
    disc_weights = compute_class_weights(labels[train_idx], NUM_DISCIPLINE_CLASSES)

    device = _device()
    print(f"device: {device} | train {len(train_idx)} / val {len(test_idx)}", flush=True)
    metrics = train(model, train_loader, test_loader, coarse_weights, disc_weights,
                    device, coarse_to_disc_idxs, len(coarse_names))

    print("metrics:", json.dumps(metrics, indent=2), flush=True)

    checkpoint_dir = os.environ.get("CHECKPOINT_DIR", str(CHECKPOINT))
    save_checkpoint(model, tokenizer, metrics, checkpoint_dir=checkpoint_dir)

    # Self-contained frozen maps (D2608 F4 pattern): no live-golden reconstruction.
    idx_to_coarse = {i: g for g, i in coarse_label_map.items()}
    idx_to_disc = {i: d for i, d in enumerate(disciplines)}
    idx_to_dom = {i: d for i, d in enumerate(domains)}
    label_maps = {
        "idx_to_coarse": {str(k): v for k, v in idx_to_coarse.items()},
        "idx_to_discipline": {str(k): v for k, v in idx_to_disc.items()},
        "idx_to_domain": {str(k): v for k, v in idx_to_dom.items()},
        "discipline_to_coarse_idx": {d: discipline_to_coarse.get(d, -1) for d in disciplines},
        "coarse_to_discipline_idxs": {str(k): v for k, v in coarse_to_disc_idxs.items()},
        "n_coarse": len(coarse_names),
        "n_discipline": len(disciplines),
        "n_domain": len(domains),
        "frozen_from": str(GOLDEN),
        # R14 stamps (persistent artifact traceability).
        "schema_version": SCHEMA_VERSION,
        "gen_model": BASE_MODEL_NAME,
        "pipeline_commit": PIPELINE_COMMIT,
    }
    disc_groups = {
        "coarse_names": coarse_names,
        "group_to_disciplines": groups,
        "discipline_to_group": {d: group_of.get(d) for d in disciplines},
        "note": "D2607 (B) hierarchical coarse groups (source: taxonomy_v5.yaml discipline_groups)",
        # R14 stamps.
        "schema_version": SCHEMA_VERSION,
        "gen_model": BASE_MODEL_NAME,
        "pipeline_commit": PIPELINE_COMMIT,
    }
    _atomic_write_json(Path(checkpoint_dir) / "label_maps.json", label_maps)
    _atomic_write_json(Path(checkpoint_dir) / "discipline_groups.json", disc_groups)
    print(f"✅ hierarchical checkpoint + maps -> {checkpoint_dir}")


if __name__ == "__main__":
    main()
