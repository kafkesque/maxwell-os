"""Discriminative taxonomy classifier for the local RAG pipeline.

Trains a ModernBERT-base encoder (FULL fine-tune, NO LoRA) with dual heads
(discipline: 61-way softmax, domain: 43-way sigmoid) on the mined golden
training set. Implements class-balanced loss, abstain logic, and crash-safe
checkpointing.

D2577: LoRA was dropped — (a) peft adds a dependency and (b) the old
target_modules (q_proj/value_proj) were a silent no-op on DeBERTa's disentangled
attention. Full fine-tune removes both failure modes. Base swapped
microsoft/deberta-v3-base -> answerdotai/ModernBERT-base (8192 ctx, ~2x faster).
"""

from __future__ import annotations

import io
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
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

# ---------------------------------------------------------------------------
# C12 / C20: Named constants (no magic numbers)
# ---------------------------------------------------------------------------

BASE_MODEL_NAME: str = "answerdotai/ModernBERT-base"

NUM_DISCIPLINE_CLASSES: int = 61
NUM_DOMAIN_CLASSES: int = 43

ABSTAIN_THRESHOLD: float = 0.35
EMERGING_LABEL: str = "emerging"

MIN_GOLDEN_EXAMPLES: int = 100
MIN_EXAMPLES_PER_CLASS: int = 5
# The few-shot golden (config/golden/stage4_golden.yaml, 7 hand-curated examples)
# is WIRED into the S4 prompt and stays small. This is the SEPARATE classifier
# TRAINING set, mined from convergent FBs by scripts/mine_classifier_golden.py.
TRAINING_DATA_PATH: str = "config/golden/stage4_golden_mined.yaml"
CHECKPOINT_DIR: str = "knowledge pipeline/classifier_modernbert"

TRAIN_TEST_SPLIT_SIZE: float = 0.2
RANDOM_STATE: int = 42
TARGET_MACRO_F1: float = 0.75

BATCH_SIZE: int = 8
MAX_LENGTH: int = 320  # p99 token length is 247; 512 wasted >50% compute on padding
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


def _load_training_config() -> Dict[str, Any]:
    """Load classifier-training config from config/pipeline_config.yaml (C12).

    The student model and checkpoint dir live in the `classifier_training` block
    of the canonical config. Module-level constants are fallbacks so the script
    remains runnable standalone (e.g. CI without a full config tree).

    Returns:
        Dict with keys `student_model` and `checkpoint_dir` (possibly empty).
    """
    cfg_path = Path("config/pipeline_config.yaml")
    if not cfg_path.exists():
        logger.warning("%s not found — using in-script defaults", cfg_path)
        return {}
    try:
        full = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Could not read %s (%s) — using in-script defaults", cfg_path, exc)
        return {}
    return full.get("classifier_training") or {}


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


def _flatten_golden_example(ex: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a nested golden example into the flat row the Dataset consumes.

    On-disk form (stage4_golden*.yaml) is NESTED:
        {id, depth, input_fb{name,definition,mechanism,boundary},
         expected_classification{discipline,domains,depth,evidence,is_specialized}}
    The training Dataset consumes FLAT rows. Flatten here so the loader stays
    robust to the on-disk schema.

    Args:
        ex: Nested golden example dict.

    Returns:
        Flat dict with name/definition/mechanism/boundary/discipline/domains/depth.

    Raises:
        KeyError: If a required nested field (name, definition, discipline) is absent.
    """
    fb = ex.get("input_fb") or {}
    exp = ex.get("expected_classification") or {}
    return {
        "id": ex.get("id", ""),
        "name": fb["name"],
        "definition": fb["definition"],
        "mechanism": fb.get("mechanism", ""),
        "boundary": fb.get("boundary", ""),
        "discipline": exp["discipline"],
        "domains": exp.get("domains", []),
        "depth": exp.get("depth", ""),
        "evidence": exp.get("evidence", ""),
        "is_specialized": exp.get("is_specialized", False),
    }


def load_golden_set(config_path: str) -> Dict[str, Any]:
    """Load, validate, and flatten the golden training set from YAML.

    Args:
        config_path: Path to the golden/training YAML file.

    Returns:
        Dict with 'examples' key holding FLAT example rows.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the number of examples is below MIN_GOLDEN_EXAMPLES.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Training data not found at {config_path}. "
            "Run scripts/mine_classifier_golden.py to mine it from convergent FBs."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"Training config {config_path} is empty.")

    raw_examples: List[Dict[str, Any]] = data.get("examples", [])
    if len(raw_examples) < MIN_GOLDEN_EXAMPLES:
        raise ValueError(
            f"Training set has only {len(raw_examples)} examples; "
            f"minimum required is {MIN_GOLDEN_EXAMPLES}. "
            "Mine more via scripts/mine_classifier_golden.py before training."
        )

    examples = [_flatten_golden_example(ex) for ex in raw_examples]
    logger.info("Loaded %d training examples from %s", len(examples), config_path)
    return {"examples": examples}


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
    """Dual-head classifier on top of a full-fine-tuned ModernBERT backbone.

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


def build_model(base_model_name: str) -> Tuple[AutoTokenizer, nn.Module]:
    """Build the full-fine-tuned ModernBERT backbone and dual-head classifier.

    Args:
        base_model_name: HuggingFace model id of the encoder backbone.

    Returns:
        Tuple of (tokenizer, classifier_model).
    """
    logger.info("Loading base model: %s", base_model_name)
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    base_model = AutoModel.from_pretrained(base_model_name)

    classifier = DisciplineClassifier(
        backbone=base_model,
        num_discipline=NUM_DISCIPLINE_CLASSES,
        num_domain=NUM_DOMAIN_CLASSES,
    )
    return tokenizer, classifier


# ---------------------------------------------------------------------------
# Training utilities
# ---------------------------------------------------------------------------


def _filter_trainable(
    examples: List[Dict[str, Any]], min_per_class: int
) -> List[Dict[str, Any]]:
    """Drop examples whose discipline has too few samples to stratify-split.

    A discipline with < min_per_class examples cannot appear in BOTH the train
    and test folds (sklearn stratify requires >=2 per class), and its balanced
    class weight would be absurdly large. Drop them with a warning instead of
    crashing mid-run.

    Args:
        examples: Flat golden/training examples.
        min_per_class: Minimum examples per discipline to keep it trainable.

    Returns:
        Filtered examples.
    """
    counts: Dict[str, int] = {}
    for ex in examples:
        counts[ex["discipline"]] = counts.get(ex["discipline"], 0) + 1
    dropped = sorted(d for d, c in counts.items() if c < min_per_class)
    if dropped:
        logger.warning(
            "Dropping %d disciplines with < %d examples (untrainable): %s",
            len(dropped),
            min_per_class,
            dropped,
        )
    return [ex for ex in examples if counts[ex["discipline"]] >= min_per_class]


def compute_class_weights(
    labels: np.ndarray, num_classes: int
) -> torch.Tensor:
    """Compute class-balanced weights for the discipline head.

    Robust to missing classes: disciplines with zero training examples (e.g.
    robotics/computational theory, absent from the convergent set) get the
    uniform weight instead of raising a sklearn ValueError.

    Args:
        labels: Array of integer class labels (may not cover all num_classes).
        num_classes: Total number of classes (head width).

    Returns:
        Tensor of shape (num_classes,) with per-class weights.
    """
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    counts[counts == 0] = 1.0  # guard: avoid div-by-zero; missing classes -> uniform
    n = labels.shape[0]
    weights = n / (num_classes * counts)
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
            0.0,
            1.0 - (step - warmup_steps) / max(1, total_steps - warmup_steps),
        )

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    for epoch in range(NUM_EPOCHS):
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(train_loader):
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
            if (step + 1) % 25 == 0:
                logger.info(
                    "  epoch %d/%d step %d/%d",
                    epoch + 1,
                    NUM_EPOCHS,
                    step + 1,
                    len(train_loader),
                )

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

    # Save model state dict (serialize to a bytes buffer for crash-safe write)
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    state_bytes = buffer.getvalue()
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
    cfg = _load_training_config()
    student_model: str = cfg.get("student_model", BASE_MODEL_NAME)
    checkpoint_dir: str = cfg.get("checkpoint_dir", CHECKPOINT_DIR)
    logger.info("Training config: student=%s, checkpoint=%s", student_model, checkpoint_dir)

    # Load training set (raises if < MIN_GOLDEN_EXAMPLES)
    golden_data = load_golden_set(TRAINING_DATA_PATH)
    examples: List[Dict[str, Any]] = golden_data["examples"]
    examples = _filter_trainable(examples, MIN_EXAMPLES_PER_CLASS)

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
    tokenizer, model = build_model(student_model)

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

    # Device: prefer CUDA, then MPS (Apple Silicon), else CPU.
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
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
    save_checkpoint(model, tokenizer, metrics, checkpoint_dir=checkpoint_dir)

    logger.info("Training complete.")


if __name__ == "__main__":
    main()