# Maxwell OS v3.0 — justfile
# Authority: CONSTITUTION.md §6

# ── Health ───────────────────────────────────────────────────
health:
    @echo "=== Maxwell OS v3.0 Health Check ==="
    python3 scripts/guard_stacks_single_source.py || exit 1
    python3 pipeline/status.py
    python3 pipeline/integrity_check.py --quick

healthcheck: health

# ── One-panel inference stack monitor (D2456): versions + drift + single-source ──
stacks:
    @python3 scripts/monitor_stacks.py

preflight:
    @echo "=== Maxwell OS Preflight ==="
    @python3 scripts/monitor_stacks.py || exit 1
    @python3 -c "from pipeline.pipeline_paths import ensure_dirs; ensure_dirs(); print('✅ Directories OK')"
    @python3 -c "from pipeline.pipeline_paths import check_books_source; ok, msg = check_books_source(); print(msg); exit(0 if ok else 1)"
    @python3 -c "from pipeline.pipeline_paths import check_pipeline_state; print(check_pipeline_state())"
    @python3 tools/verify_golden_hash.py || { echo "  ❌ Golden hash mismatch — golden set changed without re-stamping .golden_meta.json (D2367)"; exit 1; }
    @python3 pipeline/config_audit.py --check-unchecked --strict || { echo "  ❌ Config drift or unchecked hardcoded values — fix before continuing"; exit 1; }
    @python3 -c "from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES; print(f'✅ Taxonomy: {len(CANONICAL_DOMAINS)} domains, {len(CANONICAL_DISCIPLINES)} disciplines')"
    @python3 -c "from pipeline.omlx_call import check_omlx_health; ok = check_omlx_health(); print('✅ OMLX UP' if ok else '❌ OMLX DOWN')"
    @python3 scripts/recompute_decision_summary.py --check || { echo "  ❌ Decision summary drift — run scripts/recompute_decision_summary.py"; exit 1; }
    @echo "  🔍 Dependency check..."
    @pip3 check 2>&1 || echo "    ⚠️  Dependency conflicts found (non-blocking — see above)"
    @echo "    📦 Outdated packages:"
    @pip3 list --outdated --format=columns 2>/dev/null | wc -l | xargs -I{} echo "      {} total (run 'pip3 list --outdated' for details)"
    @echo "  🖥️  Hardware-model fit..."
    @llmfit 2>&1 | head -5 || echo "    ⚠️  llmfit unavailable"
    just integrity-quick
    just stress

# ── Stress-test OMLX chat (catches the 'health endpoint lies' bug) ──
stress:
    @echo "=== Pre-flight: Memory ==="
    PYTHONPATH=. python3 pipeline/memory_guard.py --min-gb 6 || exit 1
    @echo "=== OMLX Chat Stress Test ==="
    PYTHONPATH=. python3 pipeline/stress_test.py

# ── G10: OMLX wired-memory leak stress test (D2020 Layer 1, pre-26h-run gate) ──
wired-stress:
    PYTHONPATH=. python3 pipeline/omlx_wired_stress.py

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
    python3 pipeline/stage4_merge.py
    python3 scripts/gate_emerging_rate.py || exit 1
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

# Full smoke: default models (Qwen3-Coder-30B + gpt-oss-20b, ~5min)
smoke: smoke-fast
    @echo "ℹ️  For plumbing-only (<30s no LLM): just smoke-plumbing"

# ── E2E test (P1.5) ───────────────────────────────────────────
e2e-test:
    python3 pipeline/e2e_test.py "$@"

e2e-test-fast:
    python3 pipeline/e2e_test.py --quality fast "$@"

e2e-test-dry:
    python3 pipeline/e2e_test.py --dry-run "$@"

# Alias: full pipeline evaluation (end-to-end validation)
eval: e2e-test

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

# P2-1 / BUG-152 (2026-08-21): re-extract the t11 single-source clusters with the
# balanced golden + per-type body schemas, skipping the already-correct convergent
# FBs. S2 ONLY — stops before S4/S5/S6 so the single-source output can be visually
# inspected before any classification/verification/commit. Logs to
# knowledge pipeline/stage2_extract/t11/single_source_rerun.log AND stdout (tee).
s2-single-source-rerun:
    @echo "=== S2 single-source rerun (t11, P2-1/BUG-152) — convergent skipped ==="
    @mkdir -p "knowledge pipeline/stage2_extract/t11"
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-single-source --reset-single-source 2>&1 | tee "knowledge pipeline/stage2_extract/t11/single_source_rerun.log"

# Tail the live S2 single-source rerun log (progress tracker).
s2-single-source-status:
    @tail -n 60 -f "knowledge pipeline/stage2_extract/t11/single_source_rerun.log"

# Resume the t11 single-source rerun from its checkpoint. NO --reset-single-source:
# keeps the already-extracted single-source FBs (incl. backfilled elaboration) and
# continues the remaining clusters with the FIXED elaboration-required prompt.
s2-single-source-resume:
    @echo "=== S2 single-source RESUME (t11) — continues from checkpoint, fixed prompt ==="
    @mkdir -p "knowledge pipeline/stage2_extract/t11"
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-single-source 2>&1 | tee "knowledge pipeline/stage2_extract/t11/single_source_rerun_resume.log"

# Tail the elaboration-backfill log (BUG-155 post-hoc fix, ~1760 records).
s2-backfill-status:
    @tail -n 40 -f "knowledge pipeline/stage2_extract/t11/backfill_elaboration.log"

# D2437/D2452: deterministic pre-LLM singleton gate (EXTRACT/SKIP verdicts, model-free).
# Produces singletons.prefiltered.jsonl consumed by s2-singletons below. Re-run only
# when singletons.jsonl or config/filtering.yaml changes.
s2-singletons-prefilter:
    python3 scripts/prefilter_clusters.py \
        --clusters "knowledge pipeline/stage1_5_embed_cluster/t11/singletons.jsonl" \
        --chunks "knowledge pipeline/stage1_chunk/t11/checkpoint.jsonl" \
        --config config/filtering.yaml \
        --out "knowledge pipeline/stage1_5_embed_cluster/t11/singletons.prefiltered.jsonl"

# D2452/D2453: singleton extraction — gated by singletons.prefiltered.jsonl (EXTRACT only).
# --only-singletons skips run_stage2 (single-source/convergent already extracted +
# post-hoc filtered). Skips the 28,805 SKIP (noise/junk) singletons, extracts only the
# ~6,317 EXTRACT. Crash-safe + resumable (D2453 checkpoint/resume). Stops before S4/S5/S6.
s2-singletons:
    @echo "=== S2 singleton extraction (t11, prefilter-gated, resumable) ==="
    @python3 -c "from pipeline.omlx_call import assert_omlx_no_cache; assert_omlx_no_cache()"
    @mkdir -p "knowledge pipeline/stage2_extract/t11"
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-singletons 2>&1 | tee "knowledge pipeline/stage2_extract/t11/singleton_run.log"

# D2177: stage3 removed (D2120) — redirects to runner
stage4:
    @python3 -c "from pipeline.omlx_call import assert_omlx_no_cache; assert_omlx_no_cache()"
    python3 pipeline/stage4_merge.py
stage5:
    @python3 -c "from pipeline.omlx_call import assert_omlx_no_cache; assert_omlx_no_cache()"
    python3 pipeline/stage5_verify.py
stage6:
    python3 pipeline/stage6_commit.py

# D2485 (D2491): post-S4 emerging-rate gate (BUG-150) — fail-closed between S4 and S5.
# Measures discipline/domain/unmapped emerging rates; exit 1 if any exceed config
# thresholds (config/pipeline_config.yaml → taxonomy.*). Never promote stale labels.
gate-emerging:
    python3 scripts/gate_emerging_rate.py

# ── Export & Backup ───────────────────────────────────────────
export:
    python3 pipeline/query.py --export > data/fbs_export.jsonl
    @echo "✅ Exported to data/fbs_export.jsonl"

backup:
    bash pipeline/backup_guardian.sh

# ── Integrity — 17 automated checks (D2203) ──────────────────
integrity:
    @echo "=== Maxwell OS Integrity Check (D2203) ==="
    python3 pipeline/integrity_check.py

integrity-quick:
    python3 pipeline/integrity_check.py --quick

# ── Full audit: config drift + integrity + lint + delegate safety ──
audit:
    @echo "=== Maxwell OS Full Audit ==="
    python3 pipeline/config_audit.py --check-unchecked --strict || { echo "  ❌ Config drift or hardcoded values — fix before continuing"; exit 1; }
    python3 pipeline/integrity_check.py --quick
    @python3 -m ruff check pipeline/ 2>&1 | tail -5
    python3 tools/delegate_safe.py
    @echo "✅ Audit complete"

# ── D2205 Retrieval Tools ─────────────────────────────────────
# Graph-aware retrieval (FTS + vector + keyword + graph expansion)
retrieve-graph query:
    python3 pipeline/retrieve.py --graph-aware "{{query}}" --limit 15

# Agentic retrieval (iterative with critique loop)
retrieve-agentic query:
    python3 pipeline/retrieve.py --agentic "{{query}}" --limit 15

# Retrieval evaluator — test critique on current DB
retrieve-eval query fb_ids:
    python3 pipeline/retrieval_evaluator.py --critique-only --fb-ids "{{fb_ids}}"

# D2205 Migration — two-axis epistemic model
migrate-epistemic:
    python3 pipeline/migrate_D2205_epistemic.py

migrate-epistemic-dry:
    python3 pipeline/migrate_D2205_epistemic.py --dry-run

migrate-epistemic-verify:
    python3 pipeline/migrate_D2205_epistemic.py --verify

# MCP Server — start Maxwell knowledge server for agents
mcp-server:
    @echo "=== Maxwell MCP Knowledge Server ==="
    @echo "Starting... Register with Claude Desktop or Goose."
    @echo "Config: { 'mcpServers': { 'maxwell': {"
    @echo "  'command': 'python3',"
    @echo "  'args': ['maxwell_mcp_server.py'] } } }"
    python3 maxwell_mcp_server.py

mcp-test:
    python3 maxwell_mcp_server.py --test

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
