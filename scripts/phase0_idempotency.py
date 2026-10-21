#!/usr/bin/env python3
"""D-3036 Phase 0 idempotency test harness.

Runs the S0→S5 pipeline TWICE on a FIXED corpus + FIXED chunker and diffs the
per-stage checkpoints to attribute "rerun regenerates new principles/non-principles"
to (a) the D-2703 chunker change or (b) residual LLM/embedding non-determinism.

The decisive question this answers: on the SAME source bytes and the SAME chunker,
do two runs produce the SAME fb_id set and the SAME 8-field bodies? If not, the
regeneration observed between t11 and rechunk-v4 is NOT (only) the chunker change —
it is sampling non-determinism in S0.5/S1.5/S2/S4, and the store must be made
invariant to wording (canonicalization). If yes, the t11-vs-rechunk-v4 divergence
was mostly the D-2703 chunker swap and the LLM decode is "mostly deterministic".

Modes:
  --selftest   Fixture diff, no LLM, proves the diff math (exit 0 on success).
  --run        Two subprocess S0→S5 runs (idem_a, idem_b). S6 commit is SKIPPED
               so the live store is never touched (see config header).
  --diff       Compare the two runs' per-stage fingerprints + S5 overlap metrics.
  --all        --run then --diff.

Exit codes: 0 clean, 1 stage failure, 2 confound (corpus not identical between arms),
            3 configuration error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config" / "phase0_idempotency.yaml"
PIPELINE_CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline_config.yaml"

EXIT_CLEAN = 0
EXIT_STAGE_FAIL = 1
EXIT_CONFOUND = 2
EXIT_CONFIG = 3


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as e:  # C16: no silent error
        raise RuntimeError(f"PyYAML unavailable ({e}); cannot read {path}") from e
    with open(path, encoding='utf-8') as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise RuntimeError(f"{path} is not a YAML mapping")
    return doc


def _cfg() -> dict[str, Any]:
    doc = _load_yaml(CONFIG_PATH)
    block = doc.get("phase0_idempotency")
    if not isinstance(block, dict):
        raise RuntimeError(f"{CONFIG_PATH}: missing 'phase0_idempotency' block (C16)")
    return block


def _pipeline_cfg() -> dict[str, Any]:
    return _load_yaml(PIPELINE_CONFIG_PATH)


def body_hash(fb: dict[str, Any], fields: list[str]) -> str:
    """Byte-exact full-body hash of the 8 CRIBS fields (Phase 2 body_hash).

    None fields are normalised to the empty string so a missing elaboration and an
    empty elaboration hash identically. Order is the config-declared canonical order.
    """
    parts: list[str] = []
    for f in fields:
        v = fb.get(f)
        parts.append("" if v is None else str(v))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _canonical_json(row: Any) -> str:
    """Stable, order-independent serialisation of a checkpoint row for digesting."""
    return json.dumps(row, sort_keys=True, default=str, ensure_ascii=False)


# Run-identity / wall-clock fields that legitimately differ between arms but carry
# no CONTENT signal. Digesting them makes every stage appear non-identical even when
# the two arms converted the same bytes (the false "corpus_confound" seen on the
# first real run: stage0/stage1 were byte-identical except pipeline_run_id + created_at).
_RUN_IDENTITY_FIELDS = frozenset({
    "pipeline_run_id",
    "created_at",
    "elapsed_s",
})


def _content_row(row: Any) -> dict[str, Any]:
    """Strip run-identity fields so the digest compares CONTENT, not provenance."""
    return {k: v for k, v in row.items() if k not in _RUN_IDENTITY_FIELDS}


def _row_digest(row: Any) -> str:
    return hashlib.sha256(_canonical_json(_content_row(row)).encode("utf-8")).hexdigest()


def _checkpoint_path(pipeline_cfg: dict[str, Any], stage_dir_key: str, run_id: str) -> Path:
    """Resolve {stage_dir}/{run_id}/{checkpoint} from pipeline_config.yaml (C12).

    stage_dir_key is the key under `stages:` in pipeline_config.yaml
    (e.g. 'stage5_verify'). The checkpoint filename is `stage_files.checkpoint`.
    """
    stage_rel = pipeline_cfg["stages"][stage_dir_key]
    checkpoint_name = pipeline_cfg["stage_files"]["checkpoint"]
    return PROJECT_ROOT / stage_rel / run_id / checkpoint_name


# stage script -> stages key in pipeline_config.yaml
_STAGE_DIR_KEY = {
    "stage0_convert.py": "stage0_convert",
    "stage0_5_extract_metadata.py": "stage0_5_extract_metadata",
    "stage1_chunk.py": "stage1_chunk",
    "stage1_3_prefilter.py": "stage1_3_prefilter",
    "stage1_5_embed_cluster.py": "stage1_5_embed",
    "stage2_extract.py": "stage2_extract",
    "stage4_merge.py": "stage4_merge",
    "stage5_verify.py": "stage5_verify",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # tolerate a trailing/blank line; count reflects valid rows
    return rows


def fingerprint(
    pipeline_cfg: dict[str, Any], block: dict[str, Any], run_id: str
) -> dict[str, dict[str, Any]]:
    """Per-stage fingerprint: row count + digest set of canonical row JSON.

    Identical digests => that stage's output is byte-identical between arms
    (deterministic). A divergence pinpoints the FIRST stage where non-determinism
    entered the chain.
    """
    fp: dict[str, dict[str, Any]] = {}
    for script in block["stages"]:
        key = _STAGE_DIR_KEY[script]
        path = _checkpoint_path(pipeline_cfg, key, run_id)
        if not path.exists():
            fp[script] = {"count": 0, "missing": True, "digests": set()}
            continue
        rows = _load_jsonl(path)
        fp[script] = {
            "count": len(rows),
            "missing": False,
            "digests": {_row_digest(r) for r in rows},
        }
    return fp


def run_once(
    pipeline_cfg: dict[str, Any], block: dict[str, Any], run_id: str
) -> bool:
    """Run the S0→S5 stages once via subprocess with a fresh run_id. No S6 commit."""
    python_bin = pipeline_cfg.get("run", {}).get("python_bin") or sys.executable
    corpus = block["corpus"]
    extra_args = block.get("stage_extra_args", {})
    ok = True
    for script in block["stages"]:
        env = dict(os.environ)
        env["MAXWELL_RUN_ID"] = run_id
        env["MAXWELL_BOOK_LIMIT"] = str(corpus["book_limit"])
        env["MAXWELL_BOOK_SUBDIR"] = str(corpus["subdir"])
        argv = [
            python_bin,
            str(PROJECT_ROOT / "pipeline" / script),
            *extra_args.get(script, []),
        ]
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=env
            )
        except subprocess.TimeoutExpired:
            print(f"  ❌ {script} timed out")
            ok = False
            continue
        mark = "✅" if result.returncode == 0 else "❌"
        print(f"  {mark} {script} (rc={result.returncode})")
        if result.returncode != 0:
            print(f"     STDERR: {result.stderr[:600]}")
            ok = False
    return ok


def _set_stats(a: set[str], b: set[str]) -> dict[str, Any]:
    inter = a & b
    union = a | b
    jaccard = len(inter) / len(union) if union else 0.0
    return {
        "a": len(a),
        "b": len(b),
        "intersection": len(inter),
        "a_only": len(a - b),
        "b_only": len(b - a),
        "jaccard": round(jaccard, 4),
    }


def diff(block: dict[str, Any]) -> dict[str, Any]:
    """Diff the two arms' per-stage fingerprints + S5 overlap metrics."""
    pipeline_cfg = _pipeline_cfg()
    runs = block["runs"]
    a, b = runs[0], runs[1]
    fa = fingerprint(pipeline_cfg, block, a)
    fb = fingerprint(pipeline_cfg, block, b)

    # Corpus-identity guard: the two arms must convert the SAME source docs, or the
    # test is a confound (D-3036: an intermittent/corpus mismatch is a named fault).
    corpus_confound = False
    if "stage0_convert.py" in fa and "stage0_convert.py" in fb:
        da = fa["stage0_convert.py"]["digests"]
        db = fb["stage0_convert.py"]["digests"]
        corpus_confound = da != db

    stage_report: list[dict[str, Any]] = []
    for script in block["stages"]:
        sa, sb = fa[script]["digests"], fb[script]["digests"]
        stage_report.append(
            {
                "stage": script,
                "count_a": fa[script]["count"],
                "count_b": fb[script]["count"],
                "identical": sa == sb,
                "digest_stats": _set_stats(sa, sb),
            }
        )

    # S5 overlap metrics (the full-FB diff point).
    s5 = {"metrics": {}, "present": False}
    key = "stage5_verify.py"
    if not fa[key]["missing"] and not fb[key]["missing"]:
        s5["present"] = True
        rows_a = _load_jsonl(_checkpoint_path(pipeline_cfg, "stage5_verify", a))
        rows_b = _load_jsonl(_checkpoint_path(pipeline_cfg, "stage5_verify", b))
        fields = block["diff"]["body_fields"]
        ids_a = {r.get("fb_id") for r in rows_a if r.get("fb_id")}
        ids_b = {r.get("fb_id") for r in rows_b if r.get("fb_id")}
        names_a = {r.get("name") for r in rows_a if r.get("name")}
        names_b = {r.get("name") for r in rows_b if r.get("name")}
        body_a = {body_hash(r, fields) for r in rows_a}
        body_b = {body_hash(r, fields) for r in rows_b}
        defn_by_name_a = {r["name"]: r.get("definition") for r in rows_a if r.get("name")}
        defn_by_name_b = {r["name"]: r.get("definition") for r in rows_b if r.get("name")}
        shared_names = names_a & names_b
        shared_same_defn = sum(
            1
            for n in shared_names
            if defn_by_name_a.get(n) == defn_by_name_b.get(n)
        )
        s5["metrics"] = {
            "fb_id": _set_stats(ids_a, ids_b),
            "name": _set_stats(names_a, names_b),
            "body_hash_8field": _set_stats(body_a, body_b),
            "shared_name_identical_definition": shared_same_defn,
            "shared_name_different_definition": len(shared_names) - shared_same_defn,
        }

    return {
        "run_a": a,
        "run_b": b,
        "corpus_confound": corpus_confound,
        "stage_report": stage_report,
        "s5": s5,
    }


def selftest() -> int:
    """Fixture-based proof of the diff math (no LLM)."""
    fb1 = {"fb_id": "x", "name": "A", "definition": "d1", "mechanism": "m",
           "boundary": "b", "consequence": "c", "application": "a",
           "failure_mode": "f", "elaboration": "e"}
    fb2 = dict(fb1)  # identical full body
    fb3 = dict(fb1, name="A", definition="d1-DIFFERENT")  # same name, drifted defn
    fb4 = dict(fb1, name="Z")  # different name
    fields = ["name", "definition", "mechanism", "boundary", "consequence",
              "application", "failure_mode", "elaboration"]
    assert body_hash(fb1, fields) == body_hash(fb2, fields), "identical body must hash equal"
    assert body_hash(fb1, fields) != body_hash(fb3, fields), "drifted defn must hash different"
    assert body_hash(fb1, fields) != body_hash(fb4, fields), "different name must hash different"
    st = _set_stats({"a", "b", "c"}, {"b", "c", "d"})
    assert st["intersection"] == 2 and abs(st["jaccard"] - 0.5) < 1e-9, st
    # fb_id is definition-sensitive: same name + different definition => different fb_id
    import pipeline.stamp as stamp
    assert stamp.make_hash_id("A", "d1") != stamp.make_hash_id("A", "d1-DIFFERENT")
    print("✅ selftest passed: body_hash, set stats, fb_id definition-sensitivity")
    return EXIT_CLEAN


def main() -> int:
    parser = argparse.ArgumentParser(description="D-3036 Phase 0 idempotency test")
    parser.add_argument("--selftest", action="store_true", help="fixture diff, no LLM")
    parser.add_argument("--run", action="store_true", help="run two S0→S5 arms")
    parser.add_argument("--diff", action="store_true", help="diff the two arms")
    parser.add_argument("--all", action="store_true", help="--run then --diff")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if not (args.run or args.diff or args.all):
        parser.print_help()
        return EXIT_CONFIG

    block = _cfg()
    pipeline_cfg = _pipeline_cfg()

    if args.run or args.all:
        for run_id in block["runs"]:
            print(f"=== arm {run_id} ===")
            if not run_once(pipeline_cfg, block, run_id):
                return EXIT_STAGE_FAIL

    if args.diff or args.all:
        result = diff(block)
        report_path = PROJECT_ROOT / block["diff"]["report_path"]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result["corpus_confound"] and block["diff"].get("assert_corpus_identical"):
            print("❌ CONFOUND: the two arms converted different source docs — test invalid")
            return EXIT_CONFOUND
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
