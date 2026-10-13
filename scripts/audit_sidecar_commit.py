#!/usr/bin/env python3
"""scripts/audit_sidecar_commit.py - Layer-2 sidecar truthfulness rail (D2590 / BUG-715).

WHY THIS EXISTS
---------------
S4 ROUTES non-principle FBs into sidecar JSONL files (process_templates / process_instances /
growth_edges / tool_instructions / quarantined) and S6 ingests ONLY checkpoint.jsonl. So those
rows are EXTRACTED, ROUTED, WRITTEN - and then never committed, never indexed, never
retrievable. D2590 already DECIDED to enable this ("commit_non_fb_types: ENABLE") and specified
a scoped S6 build; config S6_COMMIT_NON_FB is DEAD (read by no S6 code).

The failure mode this rail prevents is SILENCE: no stage declares the drop, so the corpus looks
complete at 6,591 rows while 1,619 extracted records sit unreachable on disk. C16 (no silent
errors) + C23 (resilient by design) both require this to be LOUD.

WHAT IT DOES (read-only, deterministic, LLM-free)
-------------------------------------------------
Reconciles, for one run:  S2 extracted  ->  S4 checkpoint + S4 sidecars  ->  committed in SQLite
and reports, per content_type, the EXPLAINED drop (sidecars, by design) and the UNEXPLAINED
drop (must be 0 - a nonzero value is a real defect, exit 2).

USAGE
    python3 scripts/audit_sidecar_commit.py              # advisory (exit 2 only on unexplained drop)
    python3 scripts/audit_sidecar_commit.py --strict     # also exit 2 when a declared type is uncommitted
    python3 scripts/audit_sidecar_commit.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import CANONICAL_RUN, required  # noqa: E402
from pipeline.retrieve import get_conn  # noqa: E402

CFG_PATH = ROOT / "config" / "pipeline_config.yaml"
# D-2982: the `where=` provenance of a loud read is DERIVED from the path constant - a second
# hand-written copy of the path would be one more value with two homes (C12/C20).
CFG_HOME = str(CFG_PATH.relative_to(CFG_PATH.parent.parent))


def _cfg() -> dict:
    """Load pipeline config (C12: the rail is configured, never hardcoded)."""
    with CFG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _pipeline_root(cfg: dict) -> Path:
    """Resolve the pipeline artifact root from config; fail loud instead of guessing (C16)."""
    configured = (cfg.get("paths") or {}).get("knowledge_pipeline_root")
    if configured:
        root = ROOT / str(configured)
        if root.is_dir():
            return root
        raise SystemExit(f"paths.knowledge_pipeline_root={configured!r} does not exist ({root})")
    for candidate in sorted(ROOT.glob("*/stage2_extract")):
        return candidate.parent
    raise SystemExit(
        "cannot resolve the pipeline artifact root: declare paths.knowledge_pipeline_root in "
        "config/pipeline_config.yaml (C12) - refusing to guess (C16)"
    )


def _count_lines(path: Path) -> tuple[int, Counter]:
    """Count records in a JSONL checkpoint, grouped by content_type (never raises on one bad line)."""
    total = 0
    by_type: Counter = Counter()
    if not path.exists():
        return 0, by_type
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                by_type[json.loads(line).get("content_type") or "<none>"] += 1
            except json.JSONDecodeError:
                by_type["<unparsable>"] += 1
    return total, by_type


def _declared_residuals(
    sidecars: dict[str, tuple[int, Counter]], sidecar_keys: dict[str, str]
) -> dict:
    """Rows that are correctly NOT committed, NAMED (D2590 disclosure half).

    After the D2590 build the ingestable set is committed, so the remaining uncommitted records must
    be attributable one by one or the rail is silent about them:

      * NOT A COMMIT ROLE — the row's OWN content_type is not a role the non-principle tier may
        commit (measured 2026-10-12: 196 `principle`-typed rows sitting in the growth_edge/process
        template sidecars). Excluded by the row's own content_type, and NOT a routing bug: these are
        classification drift, the BUG-712/BUG-719 family, repaired by their own item.
      * QUARANTINE SHELF — the D2616 hold shelf is never a commit source: a shelf is a decision to
        WAIT, not a queue to drain.
    """
    commit_roles = {"process_template", "process_instance", "tool_instruction", "growth_edge"}
    not_a_role: Counter = Counter()
    for _name, (_total, by_type) in sidecars.items():
        if _name == "quarantine":
            continue
        for content_type, n in by_type.items():
            if content_type not in commit_roles and content_type != "<none>":
                not_a_role[content_type] += n
    shelf = sidecars.get("quarantine", (0, Counter()))[0]
    return {
        "not_a_commit_role_rows": sum(not_a_role.values()),
        "not_a_commit_role_by_content_type": dict(not_a_role.most_common()),
        "not_a_commit_role_reason": (
            "the row's own content_type is not a non-principle role — classification drift "
            "(BUG-712/BUG-719 family), repaired by its own item, never by routing"
        ),
        "quarantine_shelf_rows": shelf,
        "quarantine_shelf_reason": "D2616 hold shelf: a decision to WAIT, never a commit source",
    }


def _db_counts(run: str) -> Counter:
    """Committed rows for a run, grouped by content_type."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT content_type, COUNT(*) FROM fbs WHERE pipeline_run_id = ? GROUP BY 1", (run,)
        ).fetchall()
    finally:
        conn.close()
    return Counter({(r[0] or "<none>"): r[1] for r in rows})


def main() -> int:
    ap = argparse.ArgumentParser(description="Layer-2 sidecar commit reconciliation (D2590/BUG-715)")
    ap.add_argument("--run", default=CANONICAL_RUN, help="pipeline run id (default: CANONICAL_RUN)")
    ap.add_argument("--strict", action="store_true", help="also fail when a declared type is uncommitted")
    ap.add_argument("--tolerance", type=int, default=0,
                    help="ratified residual (e.g. the S4 valid_ids cluster filter); default 0 = every record must be attributed")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    cfg = _cfg()
    root = _pipeline_root(cfg)
    s2_dir = root / "stage2_extract" / args.run
    s4_dir = root / "stage4_merge" / args.run
    if not s4_dir.is_dir():
        raise SystemExit(f"stage4 dir for run {args.run!r} not found: {s4_dir} (C16)")

    # D-2982 (C16/D-2644): the sidecar FILENAMES are declared in config/pipeline_config.yaml#stage4.
    # Read LOUDLY: a code default here made an absent declaration silently audit a DIFFERENT file set
    # than the pipeline writes - the rail would then pass on a run it never looked at.
    sidecar_keys = {
        "process_template": str(required(cfg, "stage4", "process_template_output", where=CFG_HOME)),
        "process_instance": str(required(cfg, "stage4", "process_instance_output", where=CFG_HOME)),
        "growth_edge": str(required(cfg, "stage4", "growth_edge_output", where=CFG_HOME)),
        "tool_instruction": str(required(cfg, "stage4", "tool_instruction_output", where=CFG_HOME)),
        "quarantine": str(required(cfg, "stage4", "quarantine_output", where=CFG_HOME)),
    }

    s2_total, s2_types = _count_lines(s2_dir / "checkpoint.jsonl")
    s4_total, s4_types = _count_lines(s4_dir / "checkpoint.jsonl")
    sidecars = {
        name: _count_lines(s4_dir / filename) for name, filename in sidecar_keys.items()
    }
    sidecar_total = sum(t for t, _ in sidecars.values())
    db_types = _db_counts(args.run)
    db_total = sum(db_types.values())

    explained = s4_total + sidecar_total
    unexplained = s2_total - explained
    report = {
        "run": args.run,
        "s2_extracted_total": s2_total,
        "s4_checkpoint_total": s4_total,
        "s4_sidecar_total": sidecar_total,
        "committed_total": db_total,
        "unexplained_drop": unexplained,
        "s2_by_content_type": dict(s2_types.most_common()),
        "s4_checkpoint_by_content_type": dict(s4_types.most_common()),
        "sidecars": {k: {"records": t, "by_content_type": dict(c.most_common())} for k, (t, c) in sidecars.items()},
        "committed_by_content_type": dict(db_types.most_common()),
        "uncommitted_types": {
            k: v for k, v in s2_types.items() if k != "principle" and v > 0 and db_types.get(k, 0) == 0
        },
        # D2590/D-2942: the records this rail can NEVER see committed, declared so that "not
        # committed" is always attributable. Without this the rail is silent about exactly the
        # rows a reader would otherwise assume were handled.
        "declared_residuals": _declared_residuals(sidecars, sidecar_keys),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n=== LAYER-2 SIDECAR COMMIT RECONCILIATION (D2590 / BUG-715) ===")
        print(f"run: {args.run}")
        print(f"  S2 extracted            : {s2_total}")
        print(f"  S4 checkpoint (merged)  : {s4_total}")
        print(f"  S4 sidecars (NOT merged): {sidecar_total}")
        for name, (total, by_type) in sidecars.items():
            if total:
                print(f"      {name:18s} {total:5d}  {dict(by_type.most_common(4))}")
        print(f"  committed in SQLite     : {db_total}")
        print(f"  unexplained drop        : {unexplained}")
        print(f"  committed by type       : {dict(db_types.most_common())}")
        res = report["declared_residuals"]
        print(f"  declared residuals      : {res['not_a_commit_role_rows']} row(s) whose own content_type "
              f"is not a commit role {res['not_a_commit_role_by_content_type']}; "
              f"{res['quarantine_shelf_rows']} on the D2616 hold shelf")
        if report["uncommitted_types"]:
            print("\n  🚩 DECLARED TYPES EXTRACTED BUT NEVER COMMITTED (D2590 scoped-S6 build pending):")
            for k, v in report["uncommitted_types"].items():
                print(f"      {k:18s} extracted={v:5d} committed={db_types.get(k, 0)}")
            print("      spec: decisions.yaml D2590 (a) ingest sidecars (b) type-specific body "
                  "(c) wire S6_COMMIT_NON_FB (d) defer non-principle cross-ref producer")

    if unexplained > args.tolerance:
        print(f"\n  ❌ UNATTRIBUTED DROP {unexplained} (tolerance {args.tolerance}) — S2 records that "
              f"reached NEITHER the checkpoint NOR a sidecar (C16). Candidate legitimate cause: S4's "
              f"cluster-level valid_ids gate drops clusters that S5 did not gate in. Either attribute "
              f"the residual to that filter (or another named rule) and re-run with --tolerance N, or "
              f"fix the leak — an un-attributed drop is not allowed to pass silently.", file=sys.stderr)
        return 2
    if args.strict and report["uncommitted_types"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
