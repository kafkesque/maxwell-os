# Maxwell OS v2.0 — justfile
# Authority: CONSTITUTION.md §6

# ── Health ───────────────────────────────────────────────────
health:
    @echo "=== Maxwell OS v2.0 Health Check ==="
    python3 pipeline/status.py

preflight:
    @echo "=== Preflight Checks ==="
    @python3 -c "from pipeline.pipeline_paths import ensure_dirs; ensure_dirs(); print('✅ Directories OK')"
    @python3 -c "from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES; print(f'✅ Taxonomy: {len(CANONICAL_DOMAINS)} domains, {len(CANONICAL_DISCIPLINES)} disciplines')"
    @python3 -c "from pipeline.omlx_call import check_omlx_health; ok = check_omlx_health(); print('✅ OMLX UP' if ok else '❌ OMLX DOWN')"
    @python3 tools/sync_decisions.py
    just stress

# ── Stress-test OMLX chat (catches the 'health endpoint lies' bug) ──
stress:
    @echo "=== Pre-flight: Memory ==="
    PYTHONPATH=. python3 pipeline/memory_guard.py --min-gb 6 || exit 1
    @echo "=== OMLX Chat Stress Test ==="
    PYTHONPATH=. python3 pipeline/stress_test.py

# ── Pipeline ──────────────────────────────────────────────────
status:
    python3 pipeline/status.py

# v3.0 cluster-before-extract pipeline (D2115: updated stage order)
triad:
    @echo "=== v3.0 Pipeline Run (cluster-before-extract) ==="
    python3 pipeline/stage0_convert.py
    python3 pipeline/stage0_5_extract_metadata.py
    python3 pipeline/stage1_chunk.py
    python3 pipeline/stage1_3_prefilter.py
    python3 pipeline/stage1_5_embed_cluster.py
    python3 pipeline/stage2_extract.py
    python3 pipeline/stage3_cluster.py
    python3 pipeline/stage4_merge.py
    python3 pipeline/stage5_verify.py
    python3 pipeline/stage6_commit.py
    python3 pipeline/status.py

# ── Delegate Safety Check (DELEGATE-001) ──────────────────────────
delegate-check:
    python3 tools/delegate_safe.py

delegate-fix:
    python3 tools/delegate_safe.py --fix

# ── Two-tier Smoke Tests (D2120) ────────────────────────────────────────

# Tier 1: Plumbing smoke — no LLM, validates pipeline plumbing (<30s)
smoke-plumbing:
    @echo "=== Plumbing Smoke (no LLM, <30s) ==="
    MAXWELL_RUN_ID=smoke MAXWELL_SKIP_LLM=1 python3 pipeline/stage0_convert.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_chunk.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_3_prefilter.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_5_embed_cluster.py
    @echo "✅ Plumbing smoke complete (LLM stages skipped)."

# Tier 2: Fast smoke — Phi-4-mini, skip Gemma deep check (<2min)
smoke-fast:
    @echo "=== Fast Smoke (Phi-4-mini, <2min) ==="
    MAXWELL_RUN_ID=smoke python3 pipeline/stage0_convert.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_chunk.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_3_prefilter.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_5_embed_cluster.py
    MAXWELL_RUN_ID=smoke MAXWELL_FAST_MODEL=Phi-4-mini-instruct-8bit python3 pipeline/stage2_extract.py
    MAXWELL_RUN_ID=smoke MAXWELL_SKIP_GEMMA=1 python3 pipeline/stage5_verify.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage6_commit.py
    @echo "✅ Fast smoke complete. Check output in stage6_commit/smoke/"

# Full smoke: default models (Qwen3.6 + Gemma, ~5min)
smoke: smoke-fast
    @echo "ℹ️  For plumbing-only (<30s no LLM): just smoke-plumbing"

# ── E2E test (P1.5) ───────────────────────────────────────────
e2e-test:
    python3 pipeline/e2e_test.py "$@"

e2e-test-fast:
    python3 pipeline/e2e_test.py --quality fast "$@"

e2e-test-dry:
    python3 pipeline/e2e_test.py --dry-run "$@"

# ── MLX direct inference (2-3× faster, needs OMLX stopped) ─────
mlx-smoke:
    MAXWELL_INFERENCE_BACKEND=mlx just smoke-fast

mlx-e2e:
    MAXWELL_INFERENCE_BACKEND=mlx just e2e-test

# ── Individual stages ─────────────────────────────────────────
stage0:
    python3 pipeline/stage0_convert.py
stage0_5:
    python3 pipeline/stage0_5_extract_metadata.py
stage1:
    python3 pipeline/stage1_chunk.py
stage1_3:
    python3 pipeline/stage1_3_prefilter.py
stage1_5:
    python3 pipeline/stage1_5_embed_cluster.py
stage2:
    python3 pipeline/stage2_extract.py
stage3:
    python3 pipeline/stage3_cluster.py
stage4:
    python3 pipeline/stage4_merge.py
stage5:
    python3 pipeline/stage5_verify.py
stage6:
    python3 pipeline/stage6_commit.py

# ── Export & Backup ───────────────────────────────────────────
export:
    python3 pipeline/query.py --export > data/fbs_export.jsonl
    @echo "✅ Exported to data/fbs_export.jsonl"

backup:
    bash pipeline/backup_guardian.sh

# ── Vibecheck — Ruff + format on changed files (D2109) ───────
vibecheck:
    @echo "=== Vibecheck ==="
    @python3 -m ruff check --fix pipeline/ 2>&1 | tail -3
    @python3 -m ruff format --check pipeline/ 2>&1 | tail -1
    @echo "✅ Vibecheck complete"

vibecheck-full:
    @echo "=== Full Vibecheck (all checks) ==="
    python3 -m ruff check pipeline/
    python3 -m ruff format --check pipeline/
    @echo "=== Syntax check on all pipeline .py files ==="
    @for f in pipeline/*.py; do python3 -c "compile(open('$$f').read(), '$$f', 'exec')" && echo "✅ $$f" || echo "❌ $$f"; done
    @echo "✅ Full vibecheck complete"

# ── Cleanup ───────────────────────────────────────────────────
clean:
    @echo "Use pipeline/safe_delete.py for safe deletion"
    @echo "  python3 pipeline/safe_delete.py data/checkpoints/ --reason 'reset pipeline'"
