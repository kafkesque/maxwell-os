"""Executable contract for specs/retrieval_serving.spec.md.

The machine runner (pytest) is the grader. Do NOT edit a test to make it pass unless the
SPEC changes (R5: generator != verifier; R7: temp=0 on the runner). A local LLM may draft
a spec/test; the runner is the grade.
"""
from pathlib import Path

import pytest

import pipeline.retrieve as retrieve
from pipeline.pipeline_paths import CANONICAL_RUN

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"


def _load_goldens():
    import yaml

    return yaml.safe_load(GOLDEN_PATH.read_text())["queries"]


def test_golden_set_pinned_to_canonical_run():
    """INV-1 (BUG-710): goldens must live in the served run, never a superseded one."""
    queries = _load_goldens()
    assert queries, "golden set is empty"
    for q in queries:
        assert q["verified_run"] == CANONICAL_RUN, (
            f"golden {q['query']!r} pinned to {q['verified_run']!r}, expected {CANONICAL_RUN!r}"
        )


def test_golden_anchors_are_names():
    """INV-1 (D-2939): the anchor is a NAME; the id is resolved per run."""
    for q in _load_goldens():
        assert q.get("expected_names"), f"golden {q['query']!r} has no expected_names"


def test_every_pool_leg_pins_to_canonical_run():
    """INV-2 (D-2881): each pool leg filters pipeline_run_id and binds CANONICAL_RUN."""
    import inspect

    for name in ("search_keyword", "search_fts", "search_vector"):
        src = inspect.getsource(getattr(retrieve, name))
        assert "pipeline_run_id" in src, f"{name} does not filter pipeline_run_id"
        assert "CANONICAL_RUN" in src, f"{name} does not bind CANONICAL_RUN"


def test_ranking_signal_is_not_a_dead_constant():
    """INV-3 (D-2537): the ranking ORDER BY must use a non-degenerate signal.

    The dead fallback is `ORDER BY borp_score DESC` — borp_score is retired debt (constant
    0.0, nothing writes it). Correct: _rank_sql() references confidence_score (D-2537), and
    that signal must VARY across served PASS rows. Red before the config flip; green after.
    """
    # Code-level: the rank clause must not be the dead borp_score fallback.
    rank_sql = retrieve._rank_sql()
    assert "borp_score" not in rank_sql, f"ranking still falls back to dead borp_score: {rank_sql!r}"
    assert "confidence_score" in rank_sql, f"ranking does not use confidence_score: {rank_sql!r}"

    # Data-level: the effective signal must vary across served PASS rows.
    conn = retrieve.get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT confidence_score) FROM fbs "
            "WHERE pipeline_run_id = ? AND status = 'PASS'",
            (CANONICAL_RUN,),
        ).fetchone()
    finally:
        conn.close()
    n, distinct_vals = row[0], row[1]
    assert distinct_vals > 1, (
        f"effective ranking signal (confidence_score) is constant: {distinct_vals} distinct "
        f"across {n} served PASS rows"
    )



# ── INV-5 (D-2980): ONE production entry point - every serving surface is DECLARED ─────
import ast  # noqa: E402
import glob  # noqa: E402
import inspect  # noqa: E402

MATRIX_PATH = PROJECT_ROOT / "config" / "serving_call_sites.yaml"


def _matrix() -> dict:
    """The declared serving call-site matrix (this file is its declared reader - D-2669)."""
    import yaml

    return yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))


def _retrieve_calls(path) -> dict:
    """{enclosing function: {names called that are BOUND from pipeline.retrieve}}."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bound: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("pipeline.retrieve"):
            bound |= {a.asname or a.name for a in node.names}
    if path.name == "retrieve.py":  # the definition home: its own module-level defs are bound
        bound |= {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    out: dict = {}
    stack = ["<module>"]

    class _V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            stack.append(node.name)
            self.generic_visit(node)
            stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            f = node.func
            nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if nm in bound:
                out.setdefault(stack[-1], set()).add(nm)
            self.generic_visit(node)

    _V().visit(tree)
    return out


def _scope_files() -> list:
    return [Path(p) for pat in _matrix()["scope_globs"] for p in sorted(glob.glob(str(PROJECT_ROOT / pat)))]


def test_production_call_sites_route_through_the_dispatcher():
    """INV-5 (D-2980): a surface that SERVES must call the dispatcher, never a leg (D-2724)."""
    m = _matrix()
    disp = m["dispatcher"]
    missing = []
    for site in m["production_call_sites"]:
        calls = _retrieve_calls(PROJECT_ROOT / site["file"]).get(site["function"], set())
        if disp not in calls:
            missing.append(f"{site['file']}::{site['function']} (calls: {sorted(calls)})")
    assert not missing, (
        f"production serving call site(s) do NOT call the dispatcher {disp}() - the adopted "
        f"retrieval method (D-2724) is bypassed: {missing}"
    )


def test_leg_caller_inventory_is_declared_both_directions():
    """INV-5 (D-2980): every leg call is declared AND every declaration is live."""
    m = _matrix()
    legs = set(m["leg_functions"])
    measured: dict = {}
    for p in _scope_files():
        rel = str(p.relative_to(PROJECT_ROOT))
        for fn, calls in _retrieve_calls(p).items():
            hit = calls & legs
            if hit:
                measured[(rel, fn)] = hit
    declared = {(e["file"], e["function"]): set(e["legs"]) for e in m["leg_callers"]}
    undeclared = {f"{k[0]}::{k[1]}": sorted(v) for k, v in measured.items()
                  if k not in declared or not (v <= declared[k])}
    assert not undeclared, f"undeclared direct leg caller(s) - a silent bypass of the dispatcher: {undeclared}"
    stale = {f"{k[0]}::{k[1]}": sorted(v) for k, v in declared.items() if k not in measured}
    assert not stale, f"declared leg caller(s) that no longer exist (a declaration outliving its subject): {stale}"


def test_benchmark_measures_the_production_path():
    """INV-6 (D-2980): the harness must bench what serving DOES, not only A/B controls."""
    import pipeline.retrieval_benchmark as bench

    assert "production" in bench.DEFAULT_METHODS, f"no production leg in {bench.DEFAULT_METHODS}"
    assert "search(conn" in inspect.getsource(bench._run_method), (
        "the harness has no leg that calls the dispatcher - the served path is unbechable (BUG-710)"
    )
    import yaml

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "pipeline_config.yaml").read_text())
    legs = cfg["retrieval_benchmark"]["self_retrieval"]["legs"]
    assert "production" in legs, f"the label-free regression rail does not measure the served path: {legs}"


def test_candidate_pool_policy_has_one_home():
    """INV-7 (D-2980): the pool policy lives in config with ONE code home (C12/C20)."""
    import pipeline.pipeline_paths as pp

    assert retrieve._rerank_pool_size(10) == min(
        max(10 * pp.RERANK_POOL_MULTIPLIER, pp.RERANK_POOL_FLOOR), pp.RERANK_POOL_CAP
    )
    assert retrieve._rrf_leg_pool_size(10) == min(10 * pp.RRF_LEG_POOL_MULTIPLIER, pp.RRF_LEG_POOL_CAP)
    src = inspect.getsource(retrieve)
    for literal in ("min(max(limit * 5, 20), 100)", "min(limit * 5, 100)"):
        assert literal not in src, f"hardcoded pool literal is back in pipeline/retrieve.py: {literal!r}"
