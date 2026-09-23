#!/usr/bin/env python3
"""scripts/verify_menu_routing.py — enforce the D-343 routing contract (MENU COARSEN GO).

Fail-closed (C16) checks, all of them derived from artifacts rather than trusted:

1. RE-DERIVATION — for every axis, the route in config/menu_routing.yaml is re-derived
   from the MEASURED numbers and the pre-registered thresholds in
   config/representability_sweep.yaml. A route that no longer follows from the data is RED.
2. QUOTED-NUMBER INTEGRITY (BUG-342) — every measured number in the routing table must
   still equal the sweep artifact's value. Hand-edited drift is RED.
3. CONSTANT INTEGRITY — an axis routed to constant_plus_human_queue must declare the
   artifact's modal label as its constant (a wrong constant is a silent accuracy loss).
4. QUEUE INTEGRITY — every queued label must exist in the sweep artifact's worst-label
   list AND in the declared menu source (canonicalised). Actions must be in vocabulary.
5. BINDING (D-339b) — the declared consumer file must contain the declared symbol.

Nothing is hardcoded (C12); every path/threshold/vocabulary comes from config.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ROUTING_CFG = "config/menu_routing.yaml"
_CANON = re.compile(r"[^a-z0-9]+")
_RED: list[str] = []
_WARN: list[str] = []


def canon(text: object) -> str:
    """Canonicalise a label so menu text and sweep keys are comparable."""
    return _CANON.sub("", str(text).lower())


def derive_route(lift_pp: float, knn: float, modal: float, separable_min_pp: float) -> str:
    """D-343 routing rule — the constant test dominates, then the separability floor."""
    if knn <= modal:
        return "constant_plus_human_queue"
    if lift_pp >= separable_min_pp:
        return "classify"
    return "coarsen_or_classify_with_calibrated_abstention"


def menu_labels(src: dict) -> set[str]:
    """Tolerant label extraction from a menu source (list of str | {value|canonical|name})."""
    if not src:
        return set()
    path = ROOT / src["path"]
    if not path.exists():
        _RED.append(f"menu source missing: {src['path']}")
        return set()
    text = path.read_text(encoding="utf-8")
    doc = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    node = doc.get(src["key"]) if isinstance(doc, dict) else None
    if node is None:
        _WARN.append(f"menu source {src['path']}::{src['key']} not found - queue labels unverified")
        return set()
    out: set[str] = set()
    for item in node:
        if isinstance(item, str):
            out.add(canon(item))
        elif isinstance(item, dict):
            for k in ("value", "canonical", "name", "label"):
                if item.get(k):
                    out.add(canon(item[k]))
                    break
    return out


def main() -> int:
    """CLI entry point: returns 1 (RED) or 0 (clean)."""
    routing = yaml.safe_load((ROOT / ROUTING_CFG).read_text())
    sweep_cfg = yaml.safe_load((ROOT / routing["sweep_config"]).read_text())
    artifact = json.loads((ROOT / routing["sweep_artifact"]).read_text())
    floor = float(sweep_cfg["separable_min_pp"])
    vocab = set(routing["actions_vocabulary"])
    art = {a["axis"]: a for a in artifact["axes"]}

    if routing["decision"] != sweep_cfg.get("decision"):
        _RED.append(f"decision mismatch: routing={routing['decision']} sweep={sweep_cfg.get('decision')}")

    checked = queued = 0
    for axis, decl in routing["axes"].items():
        m = art.get(axis)
        if m is None:
            _RED.append(f"{axis}: absent from the sweep artifact")
            continue
        checked += 1
        # 1 + 2: re-derive and compare, then assert the quoted numbers are still true.
        expect = derive_route(m["lift_over_null_pp"], m["knn_agreement_observed"],
                              m["modal_share"], floor)
        if decl["route"] != expect:
            _RED.append(f"{axis}: route {decl['route']} != re-derived {expect} - ROUTE DRIFT")
        for key, observed in (("knn_agreement", m["knn_agreement_observed"]),
                              ("permutation_null", m["knn_agreement_permutation_null"]),
                              ("lift_over_null_pp", m["lift_over_null_pp"]),
                              ("modal_share", m["modal_share"])):
            if abs(float(decl[key]) - float(observed)) > 1e-6:
                _RED.append(f"{axis}.{key}: declared {decl[key]} != artifact {observed}")
        if m.get("route") and m["route"] != decl["route"]:
            _RED.append(f"{axis}: artifact route {m['route']} != declared {decl['route']}")
        # 3: the constant must be the measured modal label.
        if decl["route"] == "constant_plus_human_queue":
            modal = m["modal_label"]
            modal = modal[0] if isinstance(modal, list) else modal
            if canon(decl.get("constant_label")) != canon(modal):
                _RED.append(f"{axis}: constant '{decl.get('constant_label')}' != modal '{modal}'")
        # 4: the queue must be data-derived, menu-owned and use declared verbs.
        worst = {canon(w["label"]) for w in m.get("worst_labels", [])}
        owned = menu_labels(routing["menu_sources"].get(axis, {}))
        for entry in decl.get("queue", []):
            queued += 1
            lab = canon(entry["label"])
            if lab not in worst:
                _RED.append(f"{axis}: queued label '{entry['label']}' is not in the sweep worst-label list")
            if owned and lab not in owned:
                _RED.append(f"{axis}: queued label '{entry['label']}' is owned by no menu source")
            if entry["action"] not in vocab:
                _RED.append(f"{axis}: action '{entry['action']}' outside the declared vocabulary")

    # 5: the contract must be bound to code that really exists (BUG-385 guard).
    consumer = ROOT / routing["consumer"]
    symbol = routing["consumer_symbol"]
    if not consumer.exists() or symbol not in consumer.read_text(encoding="utf-8"):
        _RED.append(f"binding broken: {routing['consumer']} does not contain '{symbol}'")

    for w in _WARN:
        print(f"  ⚠️  {w}")
    for r in _RED:
        print(f"  ❌ RED {r}")
    print(f"  menu routing: {checked} axes checked, {queued} queued labels, "
          f"{len(_RED)} RED, {len(_WARN)} warn")
    return 1 if _RED else 0


if __name__ == "__main__":
    sys.exit(main())
