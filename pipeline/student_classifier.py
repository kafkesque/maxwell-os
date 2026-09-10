#!/usr/bin/env python3
"""pipeline/student_classifier.py — ModernBERT student pre-classifier (D2607, B+C).

LLM-hybrid: the cheap ModernBERT student classifies first; on low confidence it
ABSTAINS so the caller falls back to gpt-oss (the production S4 classifier).

Two checkpoint shapes are supported (auto-detected from label_maps.json):
  * FLAT (e.g. classifier_modernbert_p5final) — 2 heads: discipline (61) + domain (43).
  * HIERARCHICAL (e.g. classifier_hierarchical) — 3 heads: coarse group (10) +
    discipline (61) + domain (43). D2607 (B) measured: the coarse head (10-way,
    top-1 54%, 90% precision @ 20% coverage) is a far better abstention signal
    than the flat 61-way (28.7%, cannot reach 90% precision). In hierarchical
    mode `predict()` gates on coarse confidence AND coarse↔fine agreement, so the
    student only overrides a discipline when both heads agree and are confident.

Fully local (C1 $0 / C3 sovereign), lazy-loaded (C24), config-driven (C12).
OFF by default (`stage4.student_preclassifier_enabled: false`) — enable only after
R5 review (generator != verifier) + an agreement-threshold A/B against gpt-oss.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)

# C20: named constants — mirror scripts/train_discipline_classifier.py exactly so
# the reconstructed label maps stay byte-consistent with the trained checkpoint.
BASE_MODEL_NAME: str = "answerdotai/ModernBERT-base"
NUM_DISCIPLINE_CLASSES: int = 61
NUM_DOMAIN_CLASSES: int = 43
MIN_EXAMPLES_PER_CLASS: int = 5
MAX_LENGTH: int = 320

DEFAULT_CHECKPOINT: str = "knowledge pipeline/classifier_modernbert_p5final"
DEFAULT_GOLDEN: str = "config/golden/stage4_golden_mined.yaml"
DEFAULT_THRESHOLD: float = 0.35
DEFAULT_COARSE_THRESHOLD: float = 0.70  # D2607 (B): measured 90%-precision coarse point
DOMAIN_SIGMOID_THRESHOLD: float = 0.5


class DisciplineClassifier(nn.Module):
    """Flat dual-head classifier (61-way discipline softmax, 43-way domain sigmoid)."""

    def __init__(self, backbone: nn.Module, num_discipline: int = NUM_DISCIPLINE_CLASSES,
                 num_domain: int = NUM_DOMAIN_CLASSES) -> None:
        super().__init__()
        self.backbone = backbone
        hidden_size = backbone.config.hidden_size
        self.discipline_head = nn.Linear(hidden_size, num_discipline)
        self.domain_head = nn.Linear(hidden_size, num_domain)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor
                ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Return (discipline_logits, domain_logits) for the batch.

        Args:
            input_ids: Token IDs (batch, seq_len).
            attention_mask: Attention mask (batch, seq_len).

        Returns:
            Tuple of (discipline_logits, domain_logits).
        """
        outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls_repr = outputs.last_hidden_state[:, 0, :]
        return self.discipline_head(cls_repr), self.domain_head(cls_repr)


class HierarchicalClassifier(nn.Module):
    """Shared backbone + coarse (group) / discipline (fine) / domain heads."""

    def __init__(self, backbone: nn.Module, num_coarse: int,
                 num_discipline: int = NUM_DISCIPLINE_CLASSES,
                 num_domain: int = NUM_DOMAIN_CLASSES) -> None:
        super().__init__()
        self.backbone = backbone
        hidden_size = backbone.config.hidden_size
        self.coarse_head = nn.Linear(hidden_size, num_coarse)
        self.discipline_head = nn.Linear(hidden_size, num_discipline)
        self.domain_head = nn.Linear(hidden_size, num_domain)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor
                ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return (coarse_logits, discipline_logits, domain_logits) for the batch.

        Args:
            input_ids: Token IDs (batch, seq_len).
            attention_mask: Attention mask (batch, seq_len).

        Returns:
            Tuple of (coarse_logits, discipline_logits, domain_logits).
        """
        outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls_repr = outputs.last_hidden_state[:, 0, :]
        return (self.coarse_head(cls_repr), self.discipline_head(cls_repr),
                self.domain_head(cls_repr))


def _load_frozen_label_maps(checkpoint_dir: Path) -> Optional[Tuple[Dict[int, str], Dict[int, str], int, int]]:
    """Load flat label maps frozen alongside the checkpoint (label_maps.json).

    Returns None if absent (older checkpoints) — caller falls back to reconstruction.
    """
    p = checkpoint_dir / "label_maps.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        idx_disc = {int(k): v for k, v in d["idx_to_discipline"].items()}
        idx_dom = {int(k): v for k, v in d["idx_to_domain"].items()}
        return idx_disc, idx_dom, int(d["n_discipline"]), int(d["n_domain"])
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        # C16: corrupted/missing label_maps.json is OBSERVABLE; fall back to
        # reconstruction rather than crashing the load path silently.
        logger.warning(
            "Failed to load label_maps.json %s (%s) — will reconstruct from golden",
            p, e,
        )
        return None


def _load_coarse_maps(checkpoint_dir: Path) -> Optional[Dict[str, Any]]:
    """Load the hierarchical coarse maps from label_maps.json (D2607 B).

    Returns None when the checkpoint is flat (no idx_to_coarse). The coarse maps
    are: idx_to_coarse (coarse_idx -> group name), n_coarse,
    discipline_to_coarse_idx (discipline name -> coarse idx), and
    coarse_to_discipline_idxs (coarse idx -> [discipline idx]) for the
    coarse<->fine agreement gate.
    """
    p = checkpoint_dir / "label_maps.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to read label_maps.json %s (%s) — treating as flat", p, e)
        return None
    if "idx_to_coarse" not in d:
        return None
    try:
        return {
            "idx_to_coarse": {int(k): v for k, v in d["idx_to_coarse"].items()},
            "n_coarse": int(d["n_coarse"]),
            "discipline_to_coarse_idx": {str(k): int(v) for k, v in d.get("discipline_to_coarse_idx", {}).items()},
            "coarse_to_discipline_idxs": {int(k): [int(x) for x in v] for k, v in d.get("coarse_to_discipline_idxs", {}).items()},
        }
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Malformed coarse maps in %s (%s) — treating as flat", p, e)
        return None


def _build_label_maps(golden_path: str) -> Tuple[Dict[int, str], Dict[int, str], int, int]:
    """Reconstruct index->name maps exactly as the training script did.

    The training checkpoint stores no label maps; they are derived from the
    golden set with the SAME logic as main() (flatten -> drop <5-per-class ->
    sorted(set(...)) -> pad). As long as `golden_path` is the file the checkpoint
    was trained on, the maps are byte-identical.

    Returns:
        (idx_to_discipline, idx_to_domain, n_discipline, n_domain).
    """
    try:
        data = yaml.safe_load(Path(golden_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.error("Failed to read golden set %s: %s", golden_path, exc)
        raise ValueError(f"Golden set {golden_path} unreadable: {exc}") from exc
    raw = data.get("examples", [])
    flat: List[Dict[str, Any]] = []
    for ex in raw:
        exp = ex.get("expected_classification") or {}
        if not exp.get("discipline"):
            continue
        flat.append({"discipline": exp["discipline"],
                     "domains": exp.get("domains") or []})

    counts = Counter(e["discipline"] for e in flat)
    flat = [e for e in flat if counts[e["discipline"]] >= MIN_EXAMPLES_PER_CLASS]

    disciplines = sorted({e["discipline"] for e in flat})
    domains = sorted({d for e in flat for d in e["domains"] if d})

    idx_to_discipline = {i: d for i, d in enumerate(disciplines)}
    idx_to_domain = {i: d for i, d in enumerate(domains)}
    return idx_to_discipline, idx_to_domain, len(disciplines), len(domains)


def _load_thresholds(checkpoint_dir: Path) -> Optional[Tuple[float, Dict[str, float]]]:
    """Load per-class selective thresholds frozen alongside the checkpoint.

    Returns:
        (global_threshold, {discipline_name: threshold}) or None if absent.
        Absent thresholds.json -> caller falls back to the flat `threshold` arg
        (backward compatible).
    """
    p = checkpoint_dir / "thresholds.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        per_class = {str(k): float(v) for k, v in d.get("per_class_thresholds", {}).items()}
        return float(d.get("global_threshold", DEFAULT_THRESHOLD)), per_class
    except (OSError, ValueError, TypeError) as e:
        # C16: a corrupted thresholds.json must be OBSERVABLE, not a silent crash.
        logger.warning(
            "Failed to load thresholds.json %s (%s) — falling back to flat threshold",
            p, e,
        )
        return None


class StudentClassifier:
    """Lazy-loading ModernBERT student with conformal-style abstain on confidence.

    Flat mode: discipline/domain heads, per-class discipline abstention.
    Hierarchical mode (D2607 B): coarse head gates abstention AND coarse<->fine
    agreement is required before a discipline is emitted.
    """

    def __init__(self, checkpoint_dir: str = DEFAULT_CHECKPOINT,
                 golden_path: str = DEFAULT_GOLDEN,
                 threshold: float = DEFAULT_THRESHOLD,
                 coarse_threshold: float = DEFAULT_COARSE_THRESHOLD) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.golden_path = golden_path
        self.threshold = threshold
        self.coarse_threshold = coarse_threshold
        self._model: Optional[nn.Module] = None
        self._tokenizer: Optional[AutoTokenizer] = None
        self._is_hierarchical: bool = False
        self._idx_disc: Dict[int, str] = {}
        self._idx_dom: Dict[int, str] = {}
        self._n_disc: int = 0
        self._n_dom: int = 0
        self._idx_coarse: Dict[int, str] = {}
        self._n_coarse: int = 0
        self._coarse_to_disc_idxs: Dict[int, List[int]] = {}
        self._global_threshold: float = threshold
        self._per_class_thresholds: Dict[str, float] = {}

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        logger.info("Loading ModernBERT student from %s", self.checkpoint_dir)
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.checkpoint_dir))
        base = AutoModel.from_pretrained(BASE_MODEL_NAME)

        coarse_maps = _load_coarse_maps(self.checkpoint_dir)
        if coarse_maps is not None:
            self._is_hierarchical = True
            self._idx_coarse = coarse_maps["idx_to_coarse"]
            self._n_coarse = coarse_maps["n_coarse"]
            self._coarse_to_disc_idxs = coarse_maps["coarse_to_discipline_idxs"]
            self._model = HierarchicalClassifier(base, num_coarse=self._n_coarse)
        else:
            self._model = DisciplineClassifier(backbone=base)

        state_path = self.checkpoint_dir / "model_state.pt"
        if not state_path.exists():
            raise FileNotFoundError(f"student checkpoint missing: {state_path}")
        try:
            state_dict = torch.load(str(state_path), map_location="cpu")
            self._model.load_state_dict(state_dict)
        except (OSError, RuntimeError, KeyError) as exc:
            # C16: a corrupt/incompatible checkpoint must fail LOUD with context.
            logger.error("Failed to load student checkpoint %s: %s", state_path, exc)
            raise RuntimeError(
                f"Student checkpoint {state_path} failed to load ({exc})"
            ) from exc
        self._model.eval()

        frozen = _load_frozen_label_maps(self.checkpoint_dir)
        if frozen is not None:
            (self._idx_disc, self._idx_dom, self._n_disc, self._n_dom) = frozen
            logger.info(
                "Student loaded FROZEN label maps: %d disciplines, %d domains%s",
                self._n_disc, self._n_dom,
                f", {self._n_coarse} coarse groups" if self._is_hierarchical else "",
            )
        else:
            logger.warning(
                "No label_maps.json in %s — reconstructing from live golden %s "
                "(D2608: freeze label maps to avoid silent misalignment if golden drifts)",
                self.checkpoint_dir, self.golden_path)
            (self._idx_disc, self._idx_dom,
             self._n_disc, self._n_dom) = _build_label_maps(self.golden_path)

        # D2609 (C calibration): per-class selective thresholds frozen alongside
        # the checkpoint (thresholds.json). Absent -> flat self.threshold.
        loaded_thresholds = _load_thresholds(self.checkpoint_dir)
        if loaded_thresholds is not None:
            (self._global_threshold, self._per_class_thresholds) = loaded_thresholds
            logger.info(
                "Student loaded thresholds: global=%.3f, per-class=%d",
                self._global_threshold, len(self._per_class_thresholds),
            )
        else:
            self._global_threshold = self.threshold
            self._per_class_thresholds = {}

    def _encode(self, text: str) -> Tuple[torch.Tensor, torch.Tensor]:
        """Tokenize ``text`` into (input_ids, attention_mask) tensors.

        Args:
            text: The FB text to encode.

        Returns:
            Tuple of (input_ids, attention_mask) as 2-D tensors (1, seq_len).
        """
        assert self._tokenizer is not None
        encoding = self._tokenizer(
            text, max_length=MAX_LENGTH, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        return encoding["input_ids"], encoding["attention_mask"]

    def raw_predict(self, text: str) -> Dict[str, Any]:
        """Return the raw argmax prediction WITHOUT abstention.

        Used by scripts/calibrate_student_thresholds.py to observe the raw
        confidence distribution on a held-out set. `predict()` wraps this with
        per-class (and, in hierarchical mode, coarse-gated) selective abstention.

        Returns:
            dict with keys discipline, domains, confidence, discipline_idx, and
            (hierarchical only) coarse_group, coarse_confidence, coarse_idx.
            `discipline` is None only for a pad/untrainable class.
        """
        self._ensure_loaded()
        assert self._model is not None

        input_ids, attention_mask = self._encode(text)
        with torch.no_grad():
            if self._is_hierarchical:
                coarse_logits, disc_logits, dom_logits = self._model(input_ids, attention_mask)
                coarse_probs = F.softmax(coarse_logits, dim=-1)[0]
                coarse_idx = int(coarse_probs.argmax())
            else:
                disc_logits, dom_logits = self._model(input_ids, attention_mask)
                coarse_idx = None

        disc_probs = F.softmax(disc_logits, dim=-1)[0]
        max_prob = float(disc_probs.max())
        max_idx = int(disc_probs.argmax())

        result: Dict[str, Any] = {
            "discipline": None, "domains": [],
            "confidence": max_prob, "discipline_idx": max_idx,
        }
        if self._is_hierarchical and coarse_idx is not None:
            result["coarse_group"] = self._idx_coarse.get(coarse_idx)
            result["coarse_confidence"] = float(coarse_probs.max())
            result["coarse_idx"] = coarse_idx

        if max_idx >= self._n_disc:
            return result

        dom_probs = torch.sigmoid(dom_logits)[0]
        result["discipline"] = self._idx_disc[max_idx]
        result["domains"] = [self._idx_dom[i] for i in range(self._n_dom)
                             if float(dom_probs[i]) >= DOMAIN_SIGMOID_THRESHOLD]
        return result

    def predict_coarse(self, text: str) -> Dict[str, Any]:
        """Predict only the coarse group (hierarchical checkpoints only).

        Returns:
            dict with keys coarse_group, confidence, abstained.
            Raises RuntimeError for flat checkpoints (no coarse head).
        """
        self._ensure_loaded()
        if not self._is_hierarchical:
            raise RuntimeError("predict_coarse requires a hierarchical checkpoint")
        r = self.raw_predict(text)
        group = r.get("coarse_group")
        conf = r.get("coarse_confidence", 0.0)
        abstained = group is None or conf < self.coarse_threshold
        return {"coarse_group": group, "confidence": conf, "abstained": abstained}

    def predict(self, text: str) -> Dict[str, Any]:
        """Predict discipline + domains with selective abstention.

        Flat mode: abstain when the argmax class is a pad class, or below its
        per-class threshold (global fallback).
        Hierarchical mode (D2607 B): additionally abstain when the coarse head is
        below `coarse_threshold`, or when the fine argmax lies OUTSIDE the coarse
        head's predicted group (coarse<->fine disagreement -> fall back).

        Returns:
            dict with keys discipline, domains, confidence, abstained.
            `abstained=True` signals the caller to fall back to gpt-oss.
        """
        r = self.raw_predict(text)
        disc = r["discipline"]
        if disc is None:
            return {"discipline": None, "domains": [],
                    "confidence": r["confidence"], "abstained": True}

        if self._is_hierarchical:
            coarse_idx = r.get("coarse_idx")
            if coarse_idx is None or r.get("coarse_confidence", 0.0) < self.coarse_threshold:
                return {"discipline": None, "domains": [],
                        "confidence": r["confidence"], "abstained": True}
            if r["discipline_idx"] not in self._coarse_to_disc_idxs.get(coarse_idx, []):
                return {"discipline": None, "domains": [],
                        "confidence": r["confidence"], "abstained": True}

        tau = self._per_class_thresholds.get(disc, self._global_threshold)
        if r["confidence"] < tau:
            return {"discipline": None, "domains": [],
                    "confidence": r["confidence"], "abstained": True}
        return {"discipline": disc, "domains": r["domains"],
                "confidence": r["confidence"], "abstained": False}

    def predict_with_fallback(self, text: str, fallback_discipline: str,
                              fallback_domains: List[str]) -> Dict[str, Any]:
        """Hybrid: student if confident, else gpt-oss fallback values."""
        r = self.predict(text)
        if r["abstained"]:
            return {"discipline": fallback_discipline,
                    "domains": fallback_domains,
                    "confidence": r["confidence"],
                    "abstained": True, "source": "gpt-oss"}
        return {"discipline": r["discipline"], "domains": r["domains"],
                "confidence": r["confidence"],
                "abstained": False, "source": "student"}


# C24: lazy module-level singleton — the checkpoint (596 MB) is loaded only on
# first use, and only if the feature flag is enabled by the caller.
_SINGLETON: Optional[StudentClassifier] = None


def get_student_classifier(checkpoint_dir: str = DEFAULT_CHECKPOINT,
                           golden_path: str = DEFAULT_GOLDEN,
                           threshold: float = DEFAULT_THRESHOLD,
                           coarse_threshold: float = DEFAULT_COARSE_THRESHOLD) -> StudentClassifier:
    """Return the process-wide student singleton (built on first call)."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = StudentClassifier(checkpoint_dir, golden_path, threshold,
                                       coarse_threshold)
    return _SINGLETON
