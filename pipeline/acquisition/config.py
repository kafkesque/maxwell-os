"""Where the acquisition lane reads its own declaration (D-3078).

Every value the acquirer uses comes from `config/acquisition.yaml`, and every value THAT file points at is
RESOLVED at read time from the document that owns it — a pen from the door's placement declaration, a name
template from the owner's name policy, a readability probe from the door's container integrity block. Nothing is
restated, so a change in the owner's declaration reaches the acquirer without an edit here (D-3034).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "acquisition.yaml"
GATE_PATH = ROOT / "config" / "ingest_identity_gate.yaml"


class AcquisitionError(RuntimeError):
    """A refusal: the lane cannot act, and the reason is named rather than worked around."""


@dataclass(frozen=True)
class Pen:
    """A declared arrival pen, resolved from the door's own declaration."""

    name: str
    path: Path
    why: str


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Read the acquisition declaration, refusing a file that is absent or not a mapping."""
    target = Path(path or CONFIG_PATH)
    if not target.exists():
        raise AcquisitionError(f"no acquisition declaration at {target}")
    document = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AcquisitionError(f"{target} does not hold a mapping")
    return document


def gate_document() -> dict[str, Any]:
    """Read the ingest door's declaration — the document that owns pens, names and probes."""
    document = yaml.safe_load(GATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AcquisitionError(f"{GATE_PATH} does not hold a mapping")
    return document


def walk_pointer(document: Any, dotted: str) -> Any:
    """Resolve a dotted path inside a loaded document, refusing rather than returning a default."""
    node = document
    for key in [part for part in dotted.split(".") if part]:
        if not isinstance(node, dict) or key not in node:
            raise AcquisitionError(f"pointer `{dotted}` does not resolve: `{key}` is absent")
        node = node[key]
    return node


def resolve_pen(pen_name: str) -> Pen:
    """Resolve a pen NAME through the door's placement declaration, never from a path typed in the config."""
    pens = walk_pointer(gate_document(), "source_library.placement.pens")
    if pen_name not in pens:
        raise AcquisitionError(
            f"pen `{pen_name}` is not declared in config/ingest_identity_gate.yaml"
            f"#source_library.placement.pens (declared: {sorted(pens)})"
        )
    entry = pens[pen_name] or {}
    raw = str(entry.get("path") or "").strip()
    if not raw:
        raise AcquisitionError(f"pen `{pen_name}` declares no path")
    return Pen(name=pen_name, path=Path(raw).expanduser(), why=str(entry.get("why") or "").strip())


def land_pen(config: dict[str, Any]) -> Pen:
    """The ONE pen an acquisition may land in: `pens.land` is a name, `pens.land_from` says who declares it."""
    declared_from = str(walk_pointer(config, "pens.land_from") or "").strip()
    if not declared_from.endswith("#source_library.placement.pens"):
        raise AcquisitionError(
            f"pens.land_from is `{declared_from}`: the only declaration that owns a pen is"
            " config/ingest_identity_gate.yaml#source_library.placement.pens"
        )
    pen = resolve_pen(str(walk_pointer(config, "pens.land")))
    if not pen.path.exists():
        raise AcquisitionError(f"pen `{pen.name}` resolves to {pen.path}, which does not exist")
    return pen


def name_template() -> str:
    """The owner's own filename template, read from the name policy that owns it."""
    declared_from = str(
        walk_pointer(load_config(), "download.name_template_from")
        or "config/ingest_identity_gate.yaml#source_library.name_policy.template"
    )
    path_part, _, key = declared_from.partition("#")
    if Path(ROOT / path_part).resolve() != GATE_PATH.resolve():
        raise AcquisitionError(f"name_template_from points outside the door's name policy: {declared_from}")
    return str(walk_pointer(gate_document(), key))


def probe_map() -> dict[str, str]:
    """The door's extension → probe-token map, found by SHAPE (a block holding both `module` and `probes`).

    The block sits under a nested key and its depth is not this module's business; what makes it the right block
    is that it names the module that implements the probes.
    """
    found: dict[str, Any] | None = None

    def visit(node: Any) -> None:
        nonlocal found
        if found is not None:
            return
        if isinstance(node, dict):
            if "probes" in node and "module" in node and isinstance(node["probes"], dict):
                found = node["probes"]
                return
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(gate_document())
    if not found:
        raise AcquisitionError(
            "config/ingest_identity_gate.yaml declares no container integrity block (needs `module` and `probes`)"
        )
    return {str(key).lstrip("."): str(value) for key, value in found.items()}


def pipeline_commit() -> str:
    """R14: every persistent object carries the commit that produced it."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False
        )
        return done.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"
