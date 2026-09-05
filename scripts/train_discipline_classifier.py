"""Discriminative taxonomy classifier for the local RAG pipeline.

Trains a DeBERTa-v3-base model with LoRA adapters and dual heads
(discipline: 61-way softmax, domain: 43-way sigmoid) on the golden
training set. Implements class-balanced loss, abstain logic, and
crash-safe checkpointing.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from peft import LoraConfig, TaskType, get_peft_model
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer, DebertaV3Config

# ---------------------------------------------------------------------------
# C12 / C20: Named constants (no magic numbers)
# ---------------------------------------------------------------------------

BASE_MODEL_NAME: str = "microsoft/deberta-v3-base"
LORA_RANK: int = 16
LORA_ALPHA: int = 32
LORA_TARGET_MODULES: Tuple[str, ...] = ("q_proj", "v_proj")

NUM_DISCIPLINE_CLASSES: int = 61
NUM_DOMAIN_CLASSES: int = 43

ABSTAIN_THRESHOLD: float = 0.35
EMERGING_LABEL: str = "emerging"

MIN_GOLDEN_EXAMPLES: int = 100
GOLDEN_CONFIG_PATH: str = "config/golden/stage4_golden.yaml"
CHECKPOINT_DIR: str = "knowledge_pipeline/classifier_deberta_lora"

TRAIN_TEST_SPLIT_SIZE: float = 0.2
RANDOM_STATE: int = 42
TARGET_MACRO_F1: float = 0.75

BATCH_SIZE: int = 8
MAX_LENGTH: int = 512
LEARNING_RATE: float = 2e-5
NUM_EPOCHS: int = 3
WARMUP_RATIO: float = 0.1
WEIGHT_DECAY: float = 0.01

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# C6: Crash-safe write helper (tempfile -> fsync -> os.replace)
# ---------------------------------------------------------------------------


def safe_write(path: Path, data: bytes) -> None:
    """Write data to path atomically using tempfile, fsync, and os.replace.

    Args:
        path: Destination file path.
        data: Raw bytes to write.

    Raises:
        OSError: If the write or replace operation fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        logger.error("safe_write failed for %s: %s", path, exc)
        raise


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_golden_set(config_path: str) -> Dict[str, Any]:
    """Load and validate the golden training set from YAML.

    Args:
        config_path: Path to the golden YAML file.

    Returns:
        Parsed dictionary with 'meta' and 'examples' keys.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the number of examples is below MIN_GOLDEN_EXAMPLES.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Golden config not found at {config_path}. "
            "Ensure config/golden/stage4_golden.yaml exists."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"Golden config {config_path} is empty.")

    examples: List[Dict[str, Any]] = data.get("examples", [])
    if len(examples) < MIN_GOLDEN_EXAMPLES:
        raise ValueError(
            f"Golden set has only {len(examples)} examples; "
            f"minimum required is {MIN_GOLDEN_EXAMPLES}. "
            "Expand the golden set in config/golden/stage4_golden.yaml "
            "before running the classifier training."
        )

    logger.info("Loaded %d golden examples from %s", len(examples), config_path)
    return data


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class GoldenDataset(Dataset):
    """PyTorch dataset wrapping golden examples with tokenized text."""

    def __init__(
        self,
        examples: List[Dict[str, Any]],
        tokenizer: AutoTokenizer,
        discipline_label_map: Dict[str, int],
        domain_label_map: Dict[str, int],
        max_length: int = MAX_LENGTH,
    ) -> None:
        self.examples = examples
        self.tokenizer = tokenizer
        self.discipline_label_map = discipline_label_map
        self.domain_label_map = domain_label_map
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        ex = self.examples[idx]
        text = f"{ex['name']}: {ex['definition']}"
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        discipline_id = self.discipline_label_map.get(ex["discipline"], 0)
        domain_ids = [
            self.domain_label_map[d]
            for d in ex.get("domains", [])
            if d in self.domain_label_map
        ]
        domain_labels = torch.zeros(NUM_DOMAIN_CLASSES)
        for did in domain_ids:
            domain_labels[did] = 1.0

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "discipline_label": torch.tensor(discipline_id, dtype=torch.long),
            "domain_labels": domain_labels,
        }


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class DisciplineClassifier(nn.Module):
    """Dual-head classifier on top of a LoRA-adapted DeBERTa backbone.

    Heads:
        - discipline: 61-way softmax (multi-class)
        - domain: 43-way sigmoid (multi-label)
    """

    def __init__(
        self,
        backbone: nn.Module,
        num_discipline: int = NUM_DISCIPLINE_CLASSES,
        num_domain: int = NUM_DOMAIN_CLASSES,
    ) -> None:
        super().__init__()
        self.backbone = backbone
        hidden_size = backbone.config.hidden_size
        self.discipline_head = nn.Linear(hidden_size, num_discipline)
        self.domain_head = nn.Linear(hidden_size, num_domain)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Run forward pass through backbone and both heads.

        Args:
            input_ids: Token IDs tensor of shape (batch, seq_len).
            attention_mask: Attention mask tensor of shape (batch, seq_len).

        Returns:
            Tuple of (discipline_logits, domain_logits).
        """
        outputs = self.backbone(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        # Use the  token representation (index 0)
        cls_repr = outputs.last_hidden_state[:, 0, :]
        discipline_logits = self.discipline_head(cls_repr)
        domain_logits = self.domain_head(cls_repr)
        return discipline_logits, domain_logits


def build_model() -> Tuple[AutoTokenizer, nn.Module]:
    """Build the LoRA-adapted DeBERTa backbone and dual-head classifier.

    Returns:
        Tuple of (tokenizer, classifier_model).
    """
    logger.info("Loading base model: %s", BASE_MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
    base_model = AutoModel.from_pretrained(BASE_MODEL_NAME)

    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.1,
        target_modules=list(LORA_TARGET_MODULES),
    )
    peft_model = get_peft_model(base_model, lora_config)
    peft_model.print_trainable_parameters()

    classifier = DisciplineClassifier(
        backbone=peft_model,
        num_discipline=NUM_DISCIPLINE_CLASSES,
        num_domain=NUM_DOMAIN_CLASSES,
    )
    return tokenizer, classifier


# ---------------------------------------------------------------------------
# Training utilities
# ---------------------------------------------------------------------------


def compute_class_weights(
    labels: np.ndarray, num_classes: int
) -> torch.Tensor:
    """Compute class-balanced weights for the discipline head.

    Args:
        labels: Array of integer class labels.
        num_classes: Total number of classes.

    Returns:
        Tensor of shape (num_classes,) with per-class weights.
    """
    weights = compute_class_weight(
        class_weight="balanced",
        classes=np.arange(num_classes),
        y=labels,
    )
    return torch.tensor(weights, dtype=torch.float32)


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluate the model on a dataloader and compute metrics.

    Args:
        model: The classifier model.
        dataloader: DataLoader yielding batches.
        device: Torch device.

    Returns:
        Dictionary with 'macro_f1_discipline' and per-domain F1 scores.
    """
    model.eval()
    all_disc_pred: List[int] = []
    all_disc_true: List[int] = []
    all_dom_pred: List[np.ndarray] = []
    all_dom_true: List[np.ndarray] = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            disc_logits, dom_logits = model(input_ids, attention_mask)

            disc_probs = F.softmax(disc_logits, dim=-1)
            disc_pred = disc_probs.argmax(dim=-1).cpu().numpy()
            all_disc_pred.extend(disc_pred.tolist())
            all_disc_true.extend(batch["discipline_label"].numpy().tolist())

            dom_probs = torch.sigmoid(dom_logits).cpu().numpy()
            dom_pred = (dom_probs >= 0.5).astype(int)
            all_dom_pred.append(dom_pred)
            all_dom_true.append(batch["domain_labels"].numpy())

    all_disc_pred = np.array(all_disc_pred)
    all_disc_true = np.array(all_disc_true)
    all_dom_pred = np.vstack(all_dom_pred)
    all_dom_true = np.vstack(all_dom_true)

    macro_f1_disc = f1_score(
        all_disc_true, all_disc_pred, average="macro", zero_division=0
    )

    per_domain_f1: Dict[str, float] = {}
    for i in range(NUM_DOMAIN_CLASSES):
        f1_i = f1_score(
            all_dom_true[:, i], all_dom_pred[:, i], zero_division=0
        )
        per_domain_f1[f"domain_{i}"] = float(f1_i)

    return {
        "macro_f1_discipline": float(macro_f1_disc),
        **per_domain_f1,
    }


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    class_weights: torch.Tensor,
    device: torch.device,
) -> Dict[str, float]:
    """Train the classifier for NUM_EPOCHS epochs.

    Args:
        model: The classifier model.
        train_loader: Training DataLoader.
        val_loader: Validation DataLoader.
        class_weights: Per-class weights for the discipline loss.
        device: Torch device.

    Returns:
        Dictionary of final validation metrics.
    """
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    total_steps = len(train_loader) * NUM_EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        return max(
            0.0,
            1.0 - (step - warmup_steps) / max(1, total_steps - warmup_steps),
        )

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    for epoch in range(NUM_EPOCHS):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            disc_labels = batch["discipline_label"].to(device)
            dom_labels = batch["domain_labels"].to(device)

            disc_logits, dom_logits = model(input_ids, attention_mask)

            # Class-balanced cross-entropy for discipline
            sample_weights = class_weights[disc_labels]
            disc_loss = F.cross_entropy(
                disc_logits, disc_labels, reduction="none"
            )
            disc_loss = (disc_loss * sample_weights).mean()

            # Binary cross-entropy for domain (multi-label)
            dom_loss = F.binary_cross_entropy_with_logits(
                dom_logits, dom_labels
            )

            loss = disc_loss + dom_loss
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        logger.info(
            "Epoch %d/%d - avg loss: %.4f", epoch + 1, NUM_EPOCHS, avg_loss
        )

    final_metrics = evaluate(model, val_loader, device)
    return final_metrics


# ---------------------------------------------------------------------------
# Prediction with abstain
# ---------------------------------------------------------------------------


def predict(
    model: nn.Module,
    tokenizer: AutoTokenizer,
    text: str,
    device: torch.device,
    abstain_threshold: float = ABSTAIN_THRESHOLD,
) -> Dict[str, Any]:
    """Predict discipline and domains for a single text with abstain logic.

    Args:
        model: The trained classifier model.
        tokenizer: The tokenizer.
        text: Input text.
        device: Torch device.
        abstain_threshold: Confidence threshold for abstaining.

    Returns:
        Dictionary with 'discipline', 'domains', and 'abstained' keys.
    """
    model.eval()
    encoding = tokenizer(
        text,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    input_ids = encoding["input_ids"].to(device)
    attention_mask = encoding["attention_mask"].to(device)

    with torch.no_grad():
        disc_logits, dom_logits = model(input_ids, attention_mask)

    disc_probs = F.softmax(disc_logits, dim=-1).cpu().numpy()[0]
    max_prob = float(disc_probs.max())
    max_idx = int(disc_probs.argmax())

    if max_prob < abstain_threshold:
        return {
            "discipline": EMERGING_LABEL,
            "domains": [],
            "abstained": True,
            "confidence": max_prob,
        }

    dom_probs = torch.sigmoid(dom_logits).cpu().numpy()[0]
    dom_pred = (dom_probs >= 0.5).astype(int)
    domain_indices = np.where(dom_pred == 1)[0].tolist()

    return {
        "discipline": max_idx,
        "domains": domain_indices,
        "abstained": False,
        "confidence": max_prob,
    }


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------


def save_checkpoint(
    model: nn.Module,
    tokenizer: AutoTokenizer,
    metrics: Dict[str, float],
    checkpoint_dir: str = CHECKPOINT_DIR,
) -> Path:
    """Save model, tokenizer, and metrics crash-safely.

    Args:
        model: The trained model.
        tokenizer: The tokenizer.
        metrics: Evaluation metrics dictionary.
        checkpoint_dir: Directory for checkpoint files.

    Returns:
        Path to the saved model directory.
    """
    ckpt_path = Path(checkpoint_dir)
    ckpt_path.mkdir(parents=True, exist_ok=True)

    # Save model state dict
    state_bytes = torch.save(model.state_dict())
    safe_write(ckpt_path / "model_state.pt", state_bytes)

    # Save tokenizer
    tokenizer.save_pretrained(str(ckpt_path))

    # Save metrics
    metrics_bytes = yaml.safe_dump(metrics, default_flow_style=False).encode(
        "utf-8"
    )
    safe_write(ckpt_path / "metrics.yaml", metrics_bytes)

    logger.info("Checkpoint saved to %s", ckpt_path)
    return ckpt_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: load data, build model, train, evaluate, and checkpoint."""
    # Load golden set (raises if < MIN_GOLDEN_EXAMPLES)
    golden_data = load_golden_set(GOLDEN_CONFIG_PATH)
    examples: List[Dict[str, Any]] = golden_data["examples"]

    # Build label maps
    disciplines = sorted(
        {ex["discipline"] for ex in examples}
    )
    domains = sorted(
        {d for ex in examples for d in ex.get("domains", [])}
    )

    # Pad to fixed class counts
    discipline_label_map: Dict[str, int] = {
        d: i for i, d in enumerate(disciplines)
    }
    for i in range(len(disciplines), NUM_DISCIPLINE_CLASSES):
        discipline_label_map[f"__pad_{i}"] = i

    domain_label_map: Dict[str, int] = {
        d: i for i, d in enumerate(domains)
    }
    for i in range(len(domains), NUM_DOMAIN_CLASSES):
        domain_label_map[f"__pad_{i}"] = i

    logger.info(
        "Discipline classes: %d (padded to %d), Domain classes: %d (padded to %d)",
        len(disciplines),
        NUM_DISCIPLINE_CLASSES,
        len(domains),
        NUM_DOMAIN_CLASSES,
    )

    # Tokenizer and model
    tokenizer, model = build_model()

    # Dataset and split
    dataset = GoldenDataset(
        examples=examples,
        tokenizer=tokenizer,
        discipline_label_map=discipline_label_map,
        domain_label_map=domain_label_map,
    )

    # Stratified split
    labels_array = np.array(
        [discipline_label_map[ex["discipline"]] for ex in examples]
    )
    indices = np.arange(len(examples))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=TRAIN_TEST_SPLIT_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels_array,
    )

    train_examples = [examples[i] for i in train_idx]
    test_examples = [examples[i] for i in test_idx]

    train_dataset = GoldenDataset(
        examples=train_examples,
        tokenizer=tokenizer,
        discipline_label_map=discipline_label_map,
        domain_label_map=domain_label_map,
    )
    test_dataset = GoldenDataset(
        examples=test_examples,
        tokenizer=tokenizer,
        discipline_label_map=discipline_label_map,
        domain_label_map=domain_label_map,
    )

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True
    )
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # Class weights
    train_labels = np.array(
        [discipline_label_map[ex["discipline"]] for ex in train_examples]
    )
    class_weights = compute_class_weights(
        train_labels, NUM_DISCIPLINE_CLASSES
    )

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using device: %s", device)

    # Train
    metrics = train(model, train_loader, test_loader, class_weights, device)

    # Report
    macro_f1 = metrics["macro_f1_discipline"]
    logger.info("Discipline macro-F1: %.4f", macro_f1)
    if macro_f1 < TARGET_MACRO_F1:
        logger.warning(
            "Macro-F1 %.4f is below target %.2f. "
            "Consider expanding the golden set or tuning hyperparameters.",
            macro_f1,
            TARGET_MACRO_F1,
        )

    for key, val in metrics.items():
        if key.startswith("domain_"):
            logger.info("  %s: %.4f", key, val)

    # Checkpoint
    save_checkpoint(model, tokenizer, metrics)

    logger.info("Training complete.")


if __name__ == "__main__":
    main()