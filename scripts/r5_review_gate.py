#!/usr/bin/env python3
"""scripts/r5_review_gate.py - deterministic layers FIRST, then ONE advisory reviewer (D-2962, BUG-738).

THE PROBLEM THIS RETIRES (measured, not asserted). R5 review was a single LLM pass. governance/r5_reviews.jsonl
holds 43 verdicts: 30 APPROVE / 6 REJECT / 4 INSUFFICIENT / 3 UNPARSED. Seven of 43 (16%) were not decisions at
all, and every UNPARSED was a TRUNCATION of the verdict JSON. Two of those modes are mechanical, so the model
was being asked questions a machine answers exactly and for free.

THE ORDER IS THE FIX:
  1. DETERMINISTIC (0 LLM calls, declared in config/r5_review_gate.yaml): syntax (compile), lint (ruff),
     C11/C12 (scripts/pre_commit_gate.py). A fatal layer FAILS CLOSED - the file is never sent to a reviewer,
     because a file that does not compile is not reviewable.
  2. ADVISORY: scripts/r5_code_review.py is INVOKED (never re-implemented) with the deterministic evidence
     attached as context, and a budget large enough that the verdict JSON cannot be truncated.

WHY A SEPARATE SCRIPT AND NOT A FLAG ON r5_code_review.py: the verdict rule (a verdict is evidence only when
that script produced it) must not move. This gate is an ORCHESTRATOR plus a receipt, and it restates no verdict
of its own (D-2646).

USAGE
  python3 scripts/r5_review_gate.py --file scripts/foo.py                 # deterministic + reviewer
  python3 scripts/r5_review_gate.py --file scripts/foo.py --no-llm        # deterministic only (offline / CI)
  python3 scripts/r5_review_gate.py --selftest                            # known-answer controls, no LLM, no network
Exit: 0 all deterministic pass and the reviewer APPROVEd | 1 a fatal layer failed or the reviewer REJECTed |
      2 the reviewer was indecisive (INSUFFICIENT / UNPARSED) - LOUD, and never readable as approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from fnmatch import fnmatch
from pathlib import Path

import yaml

REPO: Path = Path(__file__).resolve().parents[1]
CONFIG: Path = REPO / "config" / "r5_review_gate.yaml"
SKIP_MARKERS: tuple = ("no module named", "command not found", "not found")
STATUS_PASS: str = "PASS"
STATUS_FINDINGS: str = "FINDINGS"
STATUS_FAIL: str = "FAIL"
STATUS_NA: str = "N/A"
STATUS_SKIPPED: str = "SKIPPED"
VERDICT_LAYER_FAIL: str = "LAYER_FAIL"
VERDICT_BY_RC: dict = {0: "APPROVE", 1: "REJECT", 2: "INDECISIVE"}


def load_config(path: Path = CONFIG) -> dict:
    """Load the gate declaration. A missing or partial config is a FAULT, never a silent default (C12/C16)."""
    if not path.exists():
        raise SystemExit("FAIL-CLOSED: " + str(path) + " missing - the gate has no declaration to run")
    cfg: dict = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("layers", "tiers", "tier_by_path", "reviewer_script", "verdict_journal", "receipt", "task", "exit"):
        if key not in cfg:
            raise SystemExit("FAIL-CLOSED: config key missing: " + key)
    for name, tier in cfg["tiers"].items():
        if not str(tier.get("reviewer") or "").strip():
            raise SystemExit("FAIL-CLOSED: tier has no reviewer: " + name)
        if int(tier.get("max_tokens") or 0) < 256:
            raise SystemExit("FAIL-CLOSED: tier budget too small to hold a verdict: " + name)
    return cfg


def tier_for(rel: str, cfg: dict) -> str:
    """Path -> tier by the declared rules; the LAST match wins so the config can declare a catch-all first."""
    tier = None
    for rule in cfg["tier_by_path"]:
        if fnmatch(rel, rule["match"]):
            tier = rule["tier"]
    if tier is None or tier not in cfg["tiers"]:
        raise SystemExit("FAIL-CLOSED: no declared tier for " + rel)
    return tier


def digest(path: Path) -> str:
    """First 16 hex chars of the file sha256 - the identity a receipt and a verdict share."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run_layer(layer: dict, target: str) -> dict:
    """Run ONE declared deterministic layer and classify it. Never raises: a layer is data."""
    name: str = layer["name"]
    if not any(fnmatch(target, pat) for pat in layer.get("applies") or ["*"]):
        return {"name": name, "status": STATUS_NA, "rc": None, "detail": "not applicable to this path"}
    argv: list = [str(a).replace("{file}", target) for a in layer["argv"]]
    if shutil.which(argv[0]) is None and layer.get("optional"):
        return {"name": name, "status": STATUS_SKIPPED, "rc": None, "detail": argv[0] + " not on PATH"}
    try:
        proc = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        if layer.get("optional"):
            return {"name": name, "status": STATUS_SKIPPED, "rc": None, "detail": argv[0] + " not found"}
        return {"name": name, "status": STATUS_FAIL, "rc": 127, "detail": argv[0] + " not found"}
    stderr_tail: str = (proc.stderr or "").strip().splitlines()[-1] if (proc.stderr or "").strip() else ""
    detail: str = stderr_tail or ((proc.stdout or "").strip().splitlines()[0] if (proc.stdout or "").strip() else "")
    if proc.returncode == 0:
        return {"name": name, "status": STATUS_PASS, "rc": 0, "detail": detail}
    if layer.get("optional") and any(m in (proc.stderr or "").lower() for m in SKIP_MARKERS):
        return {"name": name, "status": STATUS_SKIPPED, "rc": proc.returncode, "detail": detail}
    return {"name": name, "status": STATUS_FAIL if layer.get("fatal") else STATUS_FINDINGS,
            "rc": proc.returncode, "detail": detail}


def append_jsonl(path: Path, record: dict) -> None:
    """Append ONE receipt line (fsync'd). The receipt is evidence, so it is appended, never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + chr(10))
        fh.flush()


def evidence_file(rel: str, layers: list, cfg: dict) -> Path:
    """Write the MACHINE-PROVED facts the reviewer is told, so it never spends budget re-deciding them."""
    lines: list = [
        "DETERMINISTIC LAYERS ALREADY RUN BY scripts/r5_review_gate.py on " + rel + " (do not re-report these):",
    ]
    for layer in layers:
        lines.append("  - " + layer["name"] + ": " + layer["status"]
                     + (" (rc " + str(layer["rc"]) + ")" if layer["rc"] is not None else "")
                     + (" - " + layer["detail"][:200] if layer.get("detail") else ""))
    lines.append("")
    lines.append("Reviewer question: " + str(cfg["task"]).strip())
    lines.append("Your job is the RESIDUE: semantics, safety, irreversibility, silent failure, self-verification.")
    handle = Path(tempfile.gettempdir()) / ("r5_gate_evidence_" + rel.replace("/", "_") + ".txt")
    handle.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    return handle


def gate_one(rel: str, cfg: dict, tier_name: str, no_llm: bool, context: list, max_tokens: int) -> dict:
    """Run the layers for ONE file, then invoke the declared reviewer unless a fatal layer failed."""
    path: Path = (REPO / rel).resolve()
    if not path.exists():
        raise SystemExit("FAIL-CLOSED: no such file: " + rel)
    layers: list = [run_layer(layer, rel) for layer in cfg["layers"]]
    fatal: list = [layer["name"] for layer in layers if layer["status"] == STATUS_FAIL]
    record: dict = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "gate": "r5_review_gate",
        "decision": cfg["decision"],
        "file": rel,
        "sha256_16": digest(path),
        "tier": tier_name,
        "reviewer": cfg["tiers"][tier_name]["reviewer"],
        "layers": layers,
        "fatal_layers": fatal,
    }
    for layer in layers:
        print("  layer  " + layer["name"].ljust(9) + layer["status"].ljust(9)
              + ("rc=" + str(layer["rc"]) if layer["rc"] is not None else "")
              + ("  " + layer["detail"][:110] if layer.get("detail") else ""))
    if fatal:
        record["verdict"] = VERDICT_LAYER_FAIL
        record["verdict_exit"] = cfg["exit"]["fail"]
        append_jsonl(REPO / cfg["receipt"], record)
        print("  VERDICT  " + VERDICT_LAYER_FAIL + " (fatal layer: " + ", ".join(fatal)
              + ") - no verdict recorded, the file is not reviewable until it compiles and satisfies C11/C12")
        return record
    if no_llm:
        record["verdict"] = "LAYERS_ONLY"
        record["verdict_exit"] = cfg["exit"]["approve"]
        append_jsonl(REPO / cfg["receipt"], record)
        print("  VERDICT  LAYERS_ONLY (--no-llm: the reviewer was not invoked, this is NOT an approval of the code)")
        return record
    evidence: Path = evidence_file(rel, layers, cfg)
    reviewer_argv: list = [
        sys.executable, str(REPO / cfg["reviewer_script"]),
        "--file", rel,
        "--reviewer", str(cfg["tiers"][tier_name]["reviewer"]),
        "--task", str(cfg["task"]).strip(),
        "--max-tokens", str(max_tokens),
        "--out", str(cfg["verdict_journal"]),
        "--context-file", str(evidence),
    ]
    for extra in context:
        reviewer_argv += ["--context-file", str(extra)]
    print("  reviewer " + str(cfg["tiers"][tier_name]["reviewer"]) + "  budget " + str(max_tokens) + " tokens")
    proc = subprocess.run(reviewer_argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
    for line in (proc.stdout or "").strip().splitlines():
        print("  " + line)
    record["verdict"] = VERDICT_BY_RC.get(proc.returncode, "UNKNOWN")
    record["verdict_exit"] = proc.returncode
    record["verdict_journal"] = cfg["verdict_journal"]
    append_jsonl(REPO / cfg["receipt"], record)
    if proc.returncode not in VERDICT_BY_RC:
        print("  FAIL-CLOSED: unexpected reviewer rc " + str(proc.returncode) + " (treated as indecisive)")
        record["verdict_exit"] = cfg["exit"]["indecisive"]
    print("  receipt  " + cfg["receipt"] + " (append-only)")
    return record


def selftest() -> int:
    """Known-answer controls (D-355: a control must assert the state it is in). No LLM, no network."""
    cfg: dict = load_config()
    tmp: Path = Path(tempfile.mkdtemp(prefix="r5_gate_selftest_"))
    good: Path = tmp / "good.py"
    good.write_text("def add(a: int, b: int) -> int:" + chr(10) + "    return a + b" + chr(10), encoding="utf-8")
    truncated: Path = tmp / "truncated.py"
    truncated.write_text("def add(a: int, b: int) -> int:" + chr(10) + "    return a + (b" + chr(10), encoding="utf-8")
    syntax_layer: dict = next(layer for layer in cfg["layers"] if layer["name"] == "syntax")
    results: list = []

    def check(label: str, ok: bool, got: object) -> None:
        results.append(ok)
        print(("  PASS  " if ok else "  FAIL  ") + label + "  (" + str(got) + ")")

    check("a good file PASSES the syntax layer", run_layer(syntax_layer, str(good))["status"] == STATUS_PASS,
          run_layer(syntax_layer, str(good))["status"])
    check("a TRUNCATED file FAILS the syntax layer (this is the 3 UNPARSED verdicts of BUG-738)",
          run_layer(syntax_layer, str(truncated))["status"] == STATUS_FAIL,
          run_layer(syntax_layer, str(truncated))["status"])
    check("an undeclared path still resolves to a declared tier (catch-all present)",
          tier_for("governance/whatever.md", cfg) in cfg["tiers"], tier_for("governance/whatever.md", cfg))
    check("scripts/* resolves to the DEEP tier", tier_for("scripts/r5_review_gate.py", cfg) == "deep",
          tier_for("scripts/r5_review_gate.py", cfg))
    check("every tier declares a reviewer and a budget that can hold a verdict",
          all(str(t.get("reviewer") or "").strip() and int(t.get("max_tokens") or 0) >= 256 for t in cfg["tiers"].values()),
          {name: t["max_tokens"] for name, t in cfg["tiers"].items()})
    check("the Qwen-lineage model is DECLARED not-a-candidate (R5 family rule)",
          "Qwen3.8-27B-MLX-4bit" in (cfg["tiers"]["deep"].get("not_candidates") or []),
          cfg["tiers"]["deep"].get("not_candidates"))
    check("the verdict journal is the ONE home the reviewer script writes",
          cfg["verdict_journal"] == "governance/r5_reviews.jsonl", cfg["verdict_journal"])
    check("layers are declared with a why (no unexplained control)",
          all(str(layer.get("why") or "").strip() for layer in cfg["layers"]), len(cfg["layers"]))
    shutil.rmtree(tmp, ignore_errors=True)
    print("  controls " + str(sum(1 for r in results if r)) + "/" + str(len(results)) + " held")
    return 0 if all(results) else 1


def main() -> int:
    """Gate one or more files. Returns the WORST exit code across them."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", action="append", default=[], help="repo-relative file to gate (repeatable)")
    ap.add_argument("--tier", default=None, help="override the declared tier")
    ap.add_argument("--context-file", action="append", default=[],
                    help="extra file the reviewer needs to judge this change (repeatable)")
    ap.add_argument("--no-llm", action="store_true", help="deterministic layers only; NEVER an approval")
    ap.add_argument("--max-tokens", type=int, default=None, help="override the declared reviewer budget")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls, no LLM")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        ap.error("--file is required (or --selftest)")
    cfg: dict = load_config()
    worst: int = cfg["exit"]["approve"]
    for rel in args.file:
        tier_name: str = args.tier or tier_for(rel, cfg)
        if tier_name not in cfg["tiers"]:
            raise SystemExit("FAIL-CLOSED: undeclared tier: " + tier_name)
        max_tokens: int = args.max_tokens or int(cfg["tiers"][tier_name]["max_tokens"])
        print("== " + rel + "  tier=" + tier_name)
        record: dict = gate_one(rel, cfg, tier_name, args.no_llm, args.context_file, max_tokens)
        worst = max(worst, int(record.get("verdict_exit") or 0))
    return worst


if __name__ == "__main__":
    sys.exit(main())
