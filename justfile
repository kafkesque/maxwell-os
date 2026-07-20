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

triad:
    @echo "=== Triad Pipeline Run ==="
    python3 pipeline/stage0_convert.py
    python3 pipeline/stage1_chunk.py
    python3 pipeline/stage2_extract.py
    python3 pipeline/stage3_cluster.py
    python3 pipeline/stage4_merge.py
    python3 pipeline/stage5_verify.py
    python3 pipeline/stage6_commit.py
    python3 pipeline/status.py

# ── Individual stages ─────────────────────────────────────────
stage0:
    python3 pipeline/stage0_convert.py
stage1:
    python3 pipeline/stage1_chunk.py
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

# ── Cleanup ───────────────────────────────────────────────────
clean:
    @echo "Use pipeline/safe_delete.py for safe deletion"
    @echo "  python3 pipeline/safe_delete.py data/checkpoints/ --reason 'reset pipeline'"
