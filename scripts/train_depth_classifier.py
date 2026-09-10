#!/usr/bin/env python3
"""train_depth_classifier.py — D2577: dedicated 4-way depth classifier.

A SEPARATE ModernBERT-base classifier for the bespoke depth ontology
(universal / cross-domain / domain / specialized), fully fine-tuned (no LoRA),
with a single 4-way softmax head. Deliberately NOT sharing the 61/43-way
discipline/domain head: the rare depth classes must not be swamped by the
taxonomy head (D2577). Reuses the flat trainer's crash-safe write + class-weight
helpers (scripts/train_discipline_classifier.py) to avoid drift.

The depth ontology order is derived from pipeline.schemas.DEPTH_LITERAL
(single source of truth, C12) — no hardcoded class list.

Checkpoint artifacts (self-contained):
  model_state.pt, tokenizer/, metrics.yaml,
  label_maps.json (idx_to_depth / depth_to_idx / n_depth),
  confusion_matrix.npy.
"""
from __future__ import annotations

import io
import logging
import os
import sys
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
    NUM_EPOCHS,
    RANDOM_STATE,
    TRAIN_TEST_SPLIT_SIZE,
    WARMUP_RATIO,
    WEIGHT_DECAY,
    _flatten_golden_example,
    compute_class_weights,
    safe_write,
)

# Depth ontology (C12: single source of truth from schemas.py).
from pipeline.schemas import DEPTH_LITERAL  # noqa: E402

# R14 stamps (single source of truth: pipeline_paths).
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

DEPTH_CLASSES: Tuple[str, ...] = tuple(DEPTH_LITERAL.__args__)  # type: ignore[attr-defined]
NUM_DEPTH_CLASSES: int = len(DEPTH_CLASSES)

GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
CHECKPOINT = ROOT / "knowledge pipeline" / "classifier_depth"

MIN_EXAMPLES_PER_DEPTH: int = 2  # >=2 needed for a stratified train/test split
TARGET_MACRO_F1: float = 0.85  # D2577 gate

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def load_depth_examples(golden_path: str) -> List[Dict[str, Any]]:
    """Load flattened golden examples and keep only canonical-depth rows.

    Args:
        golden_path: Path to the golden/training YAML.

    Returns:
        Flat example rows with a canonical ``depth`` label.

    Raises:
        FileNotFoundError: If the golden file does not exist.
        ValueError: If no examples carry a canonical depth label.
    """
    path = Path(golden_path)
    if not path.exists():
        raise FileNotFoundError(f"Golden set not found at {golden_path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("examples", [])
    examples: List[Dict[str, Any]] = []
    skipped = 0
    for ex in raw:
        flat = _flatten_golden_example(ex)
        if flat.get("depth") in DEPTH_CLASSES:
            examples.append(flat)
        else:
            skipped += 1
    if skipped:
        logger.warning("Skipped %d examples with non-canonical depth", skipped)
    if len(examples) < len(DEPTH_CLASSES) * MIN_EXAMPLES_PER_DEPTH:
        raise ValueError(
            f"Only {len(examples)} canonical-depth examples; need at least "
            f"{len(DEPTH_CLASSES) * MIN_EXAMPLES_PER_DEPTH} to stratify-split."
        )
    return examples


class DepthDataset(Dataset):
    """PyTorch dataset wrapping depth-labeled examples with tokenized text."""

    def __init__(
        self,
        examples: List[Dict[str, Any]],
        tokenizer: AutoTokenizer,
        depth_label_map: Dict[str, int],
        max_length: int = MAX_LENGTH,
    ) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.depth_label_map = depth_label_map
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
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        depth_id = self.depth_label_map[ex["depth"]]
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "depth_label": torch.tensor(depth_id, dtype=torch.long),
        }


class DepthClassifier(nn.Module):
    """Single 4-way softmax head on a full-fine-tuned ModernBERT backbone."""

    def __init__(self, backbone: nn.Module, num_depth: int = NUM_DEPTH_CLASSES) -> None:
        super().__init__()
        self.backbone = backbone
        hidden_size = backbone.config.hidden_size
        self.depth_head = nn.Linear(hidden_size, num_depth)

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        """Return depth logits for the batch.

        Args:
            input_ids: Token IDs (batch, seq_len).
            attention_mask: Attention mask (batch, seq_len).

        Returns:
            Depth logits (batch, num_depth).
        """
        outputs = self.backbone(
            input_ids=input_ids, attention_mask=attention_mask
        )
        cls_repr = outputs.last_hidden_state[:, 0, :]
        return self.depth_head(cls_repr)


def build_model(base_model_name: str) -> Tuple[AutoTokenizer, nn.Module]:
    """Build tokenizer + 4-way depth classifier over the ModernBERT backbone.

    Args:
        base_model_name: HuggingFace model id of the encoder backbone.

    Returns:
        Tuple of (tokenizer, depth_classifier_model).
    """
    logger.info("Loading base model: %s", base_model_name)
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    base_model = AutoModel.from_pretrained(base_model_name)
    return tokenizer, DepthClassifier(backbone=base_model)


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
) -> Dict[str, Any]:
    """Evaluate the depth classifier.

    Args:
        model: The classifier model.
        dataloader: DataLoader yielding batches.
        device: Torch device.

    Returns:
        Dict with macro_f1, per-class F1, and a 4x4 confusion matrix.
    """
    model.eval()
    all_pred: List[int] = []
    all_true: List[int] = []
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            logits = model(input_ids, attention_mask)
            pred = logits.argmax(dim=-1).cpu().numpy()
            all_pred.extend(pred.tolist())
            all_true.extend(batch["depth_label"].numpy().tolist())

    all_pred = np.array(all_pred)
    all_true = np.array(all_true)
    macro_f1 = float(f1_score(all_true, all_pred, average="macro", zero_division=0))
    per_class_f1 = [
        float(x)
        for x in f1_score(
            all_true,
            all_pred,
            average=None,
            labels=list(range(NUM_DEPTH_CLASSES)),
            zero_division=0,
        )
    ]
    confusion = np.zeros(
        (NUM_DEPTH_CLASSES, NUM_DEPTH_CLASSES), dtype=np.int64
    )
    for t, p in zip(all_true.tolist(), all_pred.tolist()):
        confusion[t, p] += 1
    return {
        "macro_f1_depth": macro_f1,
        "per_class_f1_depth": per_class_f1,
        "confusion_matrix": confusion,
    }


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    class_weights: torch.Tensor,
    device: torch.device,
) -> Dict[str, Any]:
    """Train the depth classifier for NUM_EPOCHS epochs.

    Args:
        model: The classifier model.
        train_loader: Training DataLoader.
        val_loader: Validation DataLoader.
        class_weights: Per-class weights for the depth loss.
        device: Torch device.

    Returns:
        Final validation metrics dict.
    """
    model.to(device)
    class_weights = class_weights.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    total_steps = len(train_loader) * NUM_EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        return max(
            0.0, 1.0 - (step - warmup_steps) / max(1, total_steps - warmup_steps)
        )

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    for epoch in range(NUM_EPOCHS):
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            depth_labels = batch["depth_label"].to(device)

            logits = model(input_ids, attention_mask)
            sample_weights = class_weights[depth_labels]
            loss = F.cross_entropy(logits, depth_labels, reduction="none")
            loss = (loss * sample_weights).mean()

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()
        logger.info(
            "Epoch %d/%d - avg loss: %.4f",
            epoch + 1, NUM_EPOCHS, total_loss / max(1, len(train_loader)),
        )

    return evaluate(model, val_loader, device)


def save_checkpoint(
    model: nn.Module,
    tokenizer: AutoTokenizer,
    metrics: Dict[str, Any],
    depth_label_map: Dict[str, int],
    checkpoint_dir: str = str(CHECKPOINT),
) -> Path:
    """Save model, tokenizer, metrics, and label maps crash-safely (C6).

    Args:
        model: The trained model.
        tokenizer: The tokenizer.
        metrics: Evaluation metrics (confusion matrix is popped first).
        depth_label_map: Canonical depth -> index map.
        checkpoint_dir: Destination checkpoint directory.

    Returns:
        Path to the saved checkpoint directory.
    """
    ckpt = Path(checkpoint_dir)
    ckpt.mkdir(parents=True, exist_ok=True)

    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    safe_write(ckpt / "model_state.pt", buffer.getvalue())
    tokenizer.save_pretrained(str(ckpt))

    idx_to_depth = {i: d for d, i in depth_label_map.items()}
    maps = {
        "idx_to_depth": idx_to_depth,
        "depth_to_idx": depth_label_map,
        "n_depth": len(depth_label_map),
        "depth_classes": list(DEPTH_CLASSES),
        # R14 stamps (persistent artifact traceability).
        "schema_version": SCHEMA_VERSION,
        "gen_model": BASE_MODEL_NAME,
        "pipeline_commit": PIPELINE_COMMIT,
    }
    safe_write(
        ckpt / "label_maps.json",
        (__import__("json").dumps(maps, indent=2) + "\n").encode("utf-8"),
    )

    confusion = metrics.pop("confusion_matrix", None)
    safe_write(
        ckpt / "metrics.yaml",
        yaml.safe_dump(metrics, default_flow_style=False).encode("utf-8"),
    )
    if confusion is not None:
        buf = io.BytesIO()
        np.save(buf, confusion)
        safe_write(ckpt / "confusion_matrix.npy", buf.getvalue())

    logger.info("Checkpoint saved to %s", ckpt)
    return ckpt


def _device() -> torch.device:
    """Select CUDA > MPS (Apple Silicon) > CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main() -> None:
    """Load depth examples, train the 4-way classifier, evaluate, checkpoint."""
    golden_path = os.environ.get("GOLDEN_YAML", str(GOLDEN))
    checkpoint_dir = os.environ.get("CHECKPOINT_DIR", str(CHECKPOINT))
    logger.info("Golden: %s | checkpoint: %s", golden_path, checkpoint_dir)

    examples = load_depth_examples(golden_path)
    logger.info(
        "Loaded %d canonical-depth examples (classes: %s)",
        len(examples), ", ".join(DEPTH_CLASSES),
    )

    # Canonical label map (fixed order — do NOT derive from data; the ontology
    # is closed at 4 classes and padding to a wider head is meaningless).
    depth_label_map: Dict[str, int] = {d: i for i, d in enumerate(DEPTH_CLASSES)}
    counts = {d: 0 for d in DEPTH_CLASSES}
    for ex in examples:
        counts[ex["depth"]] = counts.get(ex["depth"], 0) + 1
    logger.info("Depth distribution: %s", counts)

    tokenizer, model = build_model(BASE_MODEL_NAME)

    # Stratified split by depth label.
    labels_array = np.array([depth_label_map[ex["depth"]] for ex in examples])
    indices = np.arange(len(examples))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=TRAIN_TEST_SPLIT_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels_array,
    )
    train_examples = [examples[i] for i in train_idx]
    test_examples = [examples[i] for i in test_idx]

    train_dataset = DepthDataset(train_examples, tokenizer, depth_label_map)
    test_dataset = DepthDataset(test_examples, tokenizer, depth_label_map)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    train_labels = np.array([depth_label_map[ex["depth"]] for ex in train_examples])
    class_weights = compute_class_weights(train_labels, NUM_DEPTH_CLASSES)

    device = _device()
    logger.info("Using device: %s", device)

    metrics = train(model, train_loader, test_loader, class_weights, device)

    macro_f1 = metrics["macro_f1_depth"]
    logger.info("Depth macro-F1: %.4f", macro_f1)
    if macro_f1 < TARGET_MACRO_F1:
        logger.warning(
            "Macro-F1 %.4f is below D2577 gate %.2f — depth labels are the "
            "gpt-oss silver set (D2576: over-assigns universal/cross-domain); "
            "the 3-model-vote clean set is the intended fix.",
            macro_f1, TARGET_MACRO_F1,
        )
    for d, f1 in zip(DEPTH_CLASSES, metrics["per_class_f1_depth"]):
        logger.info("  %-14s F1: %.3f", d, f1)

    save_checkpoint(model, tokenizer, metrics, depth_label_map, checkpoint_dir)
    logger.info("Training complete.")


if __name__ == "__main__":
    main()
