"""Apply cost-weighted semantic-error thresholds to per-label gate decisions.

Reads empirical per-label contradiction rates from ``config/pipeline_config.yaml``
(``taxonomy.semantic_error_rate_max.per_label`` and ``.default``), computes a
retrieval-impact cost weight from label frequencies in the ``fbs`` table of the
Maxwell SQLite database, derives an effective per-label threshold, and emits a
governance report via ``pipeline.io_guard.safe_write``.

The script is read-only with respect to the database.  By default it runs in
dry-run mode (prints the report to stdout); pass ``--apply`` to persist the
report to ``governance/cost_weighted_gate.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ---------------------------------------------------------------------------
# C20 – named constants (no magic numbers)
# ---------------------------------------------------------------------------

_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_PATH: Path = _ROOT / "config" / "pipeline_config.yaml"
DEFAULT_DB_PATH: Path = _ROOT / "knowledge pipeline" / "maxwell.db"
REPORT_PATH: Path = _ROOT / "governance" / "cost_weighted_gate.json"

# C12 – thresholds and clip bounds live here, not in config, because they are
# decision-policy parameters, not data.
DEFAULT_RATE: float = 0.05
THRESHOLD_FLOOR: float = 0.02
THRESHOLD_CEILING: float = 0.30
MIN_FBS_FOR_COST: int = 1

# C20 – logging level
LOG_LEVEL: int = logging.INFO

logger: logging.Logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# C12 / C17 – config loading
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and return the pipeline YAML configuration.

    Args:
        config_path: Path to the YAML file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        try:
            data: Dict[str, Any] = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            logger.error("Failed to parse YAML config %s: %s", config_path, exc)
            raise
    if data is None:
        data = {}
    return data


def extract_semantic_error_rates(config: Dict[str, Any]) -> Tuple[Dict[str, float], float]:
    """Extract per-label rates and the default rate from the config dict.

    Args:
        config: Parsed pipeline configuration.

    Returns:
        A tuple of (per_label_rates, default_rate).

    Raises:
        KeyError: If the expected taxonomy keys are missing.
    """
    taxonomy: Dict[str, Any] = config.get("taxonomy", {})
    sem_max: Dict[str, Any] = taxonomy.get("semantic_error_rate_max", {})

    per_label_raw: Dict[str, Any] = sem_max.get("per_label", {})
    default_raw: Any = sem_max.get("default", DEFAULT_RATE)

    per_label: Dict[str, float] = {}
    for label, rate in per_label_raw.items():
        try:
            per_label[str(label)] = float(rate)
        except (TypeError, ValueError) as exc:
            logger.error(
                "Invalid rate for label %r: %r (%s)", label, rate, exc
            )
            raise

    try:
        default_rate: float = float(default_raw)
    except (TypeError, ValueError) as exc:
        logger.error("Invalid default rate: %r (%s)", default_raw, exc)
        raise

    return per_label, default_rate


# ---------------------------------------------------------------------------
# C17 / C20 – cost model
# ---------------------------------------------------------------------------

def load_label_frequencies(db_path: Path) -> Dict[str, int]:
    """Query the ``fbs`` table for per-discipline (label) feedback counts.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        Mapping of label (discipline) to count of feedback rows.

    Raises:
        sqlite3.Error: If the query fails.
        FileNotFoundError: If the DB file does not exist.
    """
    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor: sqlite3.Cursor = conn.cursor()
        cursor.execute(
            "SELECT discipline, COUNT(*) AS n FROM fbs GROUP BY discipline"
        )
        rows: List[Tuple[str, int]] = cursor.fetchall()
    except sqlite3.Error as exc:
        logger.error("SQLite query failed on %s: %s", db_path, exc)
        raise
    finally:
        if conn is not None:
            conn.close()

    frequencies: Dict[str, int] = {}
    for discipline, count in rows:
        frequencies[str(discipline)] = int(count)
    return frequencies


def compute_cost_weights(
    frequencies: Dict[str, int],
) -> Dict[str, float]:
    """Compute retrieval-impact cost weights from label frequencies.

    High-frequency labels are more retrieval-critical, so a mislabel on them is
    costlier. weight(label) = n_fbs(label) / median(n_fbs)  (>= 1 for
    above-median labels, < 1 for below-median). The effective threshold is
    DIVIDED by this weight (see effective_threshold), so high-frequency labels
    get a STRICTER (lower) threshold.

    Args:
        frequencies: Mapping of label to raw feedback count.

    Returns:
        Mapping of label to cost weight in (0, +inf), centered on 1.0.
    """
    if not frequencies:
        return {}
    counts = [max(MIN_FBS_FOR_COST, n) for n in frequencies.values()]
    median_n = float(sorted(counts)[len(counts) // 2]) or 1.0
    return {
        label: max(MIN_FBS_FOR_COST, count) / median_n
        for label, count in frequencies.items()
    }


# ---------------------------------------------------------------------------
# C17 / C20 – threshold derivation and gate
# ---------------------------------------------------------------------------

def effective_threshold(
    label: str,
    cost_weight: float,
    default_rate: float,
) -> float:
    """Compute the effective per-label threshold, clipped to [FLOOR, CEILING].

    Args:
        label: Label name (used only for logging on clip).
        cost_weight: Normalised cost weight for the label.
        default_rate: Base default rate from config.

    Returns:
        Clipped effective threshold.
    """
    raw: float = default_rate / max(1.0, cost_weight)
    clipped: float = max(THRESHOLD_FLOOR, min(THRESHOLD_CEILING, raw))
    if clipped != raw:
        logger.debug(
            "Threshold for %s clipped from %.6f to %.6f", label, raw, clipped
        )
    return clipped


def gate(
    label: str,
    rate: float,
    n_label: int,
    cost_weight: float,
    default_rate: float,
) -> Tuple[str, float]:
    """Evaluate the gate decision for a single label.

    Args:
        label: Label / discipline name.
        rate: Empirical contradiction rate for the label.
        n_label: Number of feedback samples for the label.
        cost_weight: Normalised cost weight.
        default_rate: Base default rate.

    Returns:
        A tuple of (verdict, effective_threshold) where verdict is
        ``"REJECT"`` if ``rate > threshold`` else ``"PASS"``.
    """
    threshold: float = effective_threshold(label, cost_weight, default_rate)
    verdict: str = "REJECT" if rate > threshold else "PASS"
    return verdict, threshold


# ---------------------------------------------------------------------------
# C17 / C20 – report assembly
# ---------------------------------------------------------------------------

def build_report(
    per_label_rates: Dict[str, float],
    default_rate: float,
    frequencies: Dict[str, int],
    cost_weights: Dict[str, float],
) -> Dict[str, Any]:
    """Assemble the full per-label gate report dictionary.

    Args:
        per_label_rates: Empirical rates from config.
        default_rate: Default rate from config.
        frequencies: Label -> feedback count.
        cost_weights: Label -> normalised cost weight.

    Returns:
        Report dictionary with metadata and per-label entries.
    """
    entries: List[Dict[str, Any]] = []
    for label, rate in sorted(per_label_rates.items()):
        n_fbs: int = frequencies.get(label, 0)
        weight: float = cost_weights.get(label, 0.0)
        verdict, threshold = gate(label, rate, n_fbs, weight, default_rate)
        entries.append(
            {
                "label": label,
                "rate": rate,
                "n_fbs": n_fbs,
                "cost_weight": weight,
                "threshold": threshold,
                "verdict": verdict,
            }
        )

    n_reject: int = sum(1 for e in entries if e["verdict"] == "REJECT")
    n_pass: int = len(entries) - n_reject

    report: Dict[str, Any] = {
        "default_rate": default_rate,
        "threshold_floor": THRESHOLD_FLOOR,
        "threshold_ceiling": THRESHOLD_CEILING,
        "n_labels": len(entries),
        "n_reject": n_reject,
        "n_pass": n_pass,
        "labels": entries,
    }
    return report


# ---------------------------------------------------------------------------
# C17 – CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed namespace.
    """
    parser: argparse.ArgumentParser = (
        argparse.ArgumentParser(
            description="Apply cost-weighted semantic-error thresholds."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the Maxwell SQLite database (default: %(default)s).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Path to pipeline YAML config (default: %(default)s).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the report to disk (default: dry-run, print to stdout).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Execute the cost-weighted gate pipeline.

    Args:
        argv: Optional argument list.

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s %(name)s: %(message)s")

    args: argparse.Namespace = parse_args(argv)

    try:
        config: Dict[str, Any] = load_config(args.config)
        per_label_rates, default_rate = extract_semantic_error_rates(config)
        logger.info(
            "Loaded %d per-label rates, default_rate=%.4f",
            len(per_label_rates),
            default_rate,
        )

        frequencies: Dict[str, int] = load_label_frequencies(args.db)
        logger.info("Loaded frequencies for %d labels from %s", len(frequencies), args.db)

        cost_weights: Dict[str, float] = compute_cost_weights(frequencies)

        report: Dict[str, Any] = build_report(
            per_label_rates, default_rate, frequencies, cost_weights
        )

        report_json: str = json.dumps(report, indent=2, ensure_ascii=False)

        if args.apply:
            from pipeline.io_guard import safe_write

            safe_write(REPORT_PATH, report_json)
            logger.info("Report written to %s", REPORT_PATH)
        else:
            print(report_json)
            logger.info("Dry-run: report printed to stdout (use --apply to persist).")

    except (FileNotFoundError, KeyError, sqlite3.Error, yaml.YAMLError, OSError) as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())