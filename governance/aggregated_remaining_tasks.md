# Maxwell OS — Aggregated Remaining Tasks (Post T0/T1 De-hardcoding)
> **Updated:** 2026-08-05 19:45 | **Source:** D2184–D2186 comprehensive audit
> **Total remaining:** 14 tasks across 4 tiers
> **Completed:** All Tier 0 and Tier 1 de-hardcoding. All C16 silent excepts fixed.
> **Config drift protection:** 48 registered mappings, --strict enforcement, zero drift.

---

## TIER 1 — THIS WEEK (Unblock Pipeline Scaling)

| # | Action | Effort | Why | Status |
|---|--------|--------|-----|--------|
| 1 | **Run S1.3→S6 pipeline** | 4h | S0 (922 MDs) + S1 (323K segments) done. S1.3–S6 need first run with bge-m3 512d. Embed models aligned. | 🔴 HIGHEST PRIORITY |
| 2 | NLI calibration on real data | 2h | Thresholds (0.5/0.6/0.8) unvalidated on bge-m3 embeddings. nli_calibrate.py exists. | ⬜ TODO |
| 3 | 20-book E2E test | 3h | Validate v3.0 at scale. Thresholds now configurable via e2e.* config. | ⬜ TODO |
| 4 | LightRAG overlay (Layer 1c) | 4h | Graph memory > vector memory (validated). Stage 4 edges ready. | ⬜ TODO |
| 5 | Stage 3: REMOVED | — | D2120: archived, cosine dedup in S4 | ✅ DONE |

## TIER 2 — THIS MONTH (Quality + Layer 2 Foundation)

| # | Action | Effort | Why | Status |
|---|--------|--------|-----|--------|
| 6 | Golden set audit (Q3) | 2h | 225-checklist calibration for v3.0 schema | ⬜ TODO |
| 7 | Manual FB audit (Q7) | 2h | <10% hallucination rate target | ⬜ TODO |
| 8 | Add convergent golden examples (Q4) | 1h | Need examples with cross-book convergence | ⬜ TODO |
| 9 | Implement skill.md standard (Layer 2 MVP) | 4h | IBM production-proven. Progressive disclosure. | ⬜ TODO |
| 10 | MCP server for knowledge access (C25) | 8h | Agent-agnostic. Makes Maxwell accessible to any MCP agent. | ⬜ TODO |
| 11 | Hardware probe (C24) | 3h | Auto-detect RAM/CPU. Select model quant dynamically. | ⬜ TODO |

## TIER 3 — 6-8 WEEKS (Graph Substrate + Speed)

| # | Action | Effort | Why | Status |
|---|--------|--------|-----|--------|
| 12 | Benchmark USearch vs FAISS | 2h | feed.opml: 10x faster on Apple Silicon | ⬜ TODO |
| 13 | Evaluate Zep/Graphiti for cognitive graph | 4+8h | Weekly research: temporal provenance solved problem | ⬜ TODO |
| 14 | Benchmark MLX vs OMLX (S1) | 2h | MTR Tier 3: native MLX may be 2x faster | ⬜ TODO |
| 15 | Schema migration scripts | 3h | v2.x FBs → v3.0 schema. Recover v1's 19,863 FBs. | ⬜ TODO |
| 16 | Integration test suite | 4h | `just test` golden-file regression tests | ⬜ TODO |
| 17 | Dry-run mode on all stages | 4h | Reports "Would process X books → Y chunks → Z clusters → N LLM calls" | ⬜ TODO |

## TIER 4 — 12-16 WEEKS (Cognitive Architecture)

| # | Foundation | Weekly Research Refinement | Status |
|---|-----------|---------------------------|--------|
| F1 | Typed Graph Storage | Evaluate Zep/Graphiti FIRST (purpose-built agent memory). Neo4j fallback. | ⬜ TODO |
| F2 | Edge Type Ontology | 10-15 edge types with formal properties (transitivity, symmetry). Machine-checkable. | ⬜ TODO |
| F3 | Skill Subgraph Templates | Start with skill.md (Tier 2 #9). Graduate to graph when 50+ skills. | ⬜ TODO |
| F4 | Constitutional Constraint Graph | C1-C28 as graph invariants. `validate_all_constraints(graph)` → violations. | ⬜ TODO |
| F5 | Self-Observation Protocol | OBSERVATION nodes. Agent queries own graph. IBM: "forgetting is an engineering problem." | ⬜ TODO |

## URGENT — FROM WEEKLY RESEARCH (D2116)

| # | Action | Why | Effort | Status |
|---|--------|-----|--------|--------|
| R1 | Study IBM course transcript for Layer 2 | 3-module structure maps 1:1 to Maxwell needs | 16h | ⬜ TODO |
| R2 | Add "Trust But Verify" citation pattern | Brightwave validated Maxwell's Stage 5 approach | 2h | ⬜ TODO |
| R3 | Implement GAAMA 4-node memory | Episodes + facts + reflections + concepts | 8h | ⬜ TODO |
| R4 | Evaluate `awesome-agent-skills` repo | Accelerates skill.md adoption | 1h | ⬜ TODO |
| R5 | Evaluate `caveman` prompt framework | Local-first prompt engineering for Stage 2 | 2h | ⬜ TODO |

---

## BUGS — OPEN FROM GOVERNANCE/BUGLOG

| Bug ID | Severity | Description | Status |
|--------|----------|-------------|--------|
| BUG-044 | 🟡 MED | Stage 3 bypassed (bridge script) → clusters not used | ✅ DONE — S3 removed (D2120) |
| BUG-045 | 🟡 MED | evidence_passages inflates (fixed: evidence_passages_shown) | ✅ DONE (2026-07-26) |
| BUG-046 | 🟡 MED | Stage 4 complexity for v3.0 | ⬜ OPEN |
| BUG-047 | 🟡 MED | OMLX memory leak (watchdog enhanced) | ✅ DONE (2026-07-26) |
| BUG-048 | 🟡 MED | Stage 3 semantic dedup not functioning | ✅ DONE — S3 removed, cosine dedup in S4 |
| BUG-050 | 🟡 MED | governance drift (CONSTITUTION stale refs) | ✅ DONE (2026-07-26) |
| BUG-001 | 🔴 CRITICAL | OMLX model crashes on large context | ⬜ MITIGATED (watchdog) |
| — | ✅ FIXED | C16: batch_convert_epubs.py bare except | ✅ DONE (D2186) |
| — | ✅ FIXED | C16: fix_remaining.py bare except | ✅ DONE (D2186) |

---

## IMMEDIATE NEXT ACTION

```bash
# Run preflight (now enforces config-code parity)
just preflight

# Run the pipeline from S1.3 through S6
python3 pipeline/stage1_3_prefilter.py
python3 pipeline/stage1_5_embed_cluster.py
python3 pipeline/stage2_extract.py --process-singletons
python3 pipeline/stage4_merge.py
python3 pipeline/stage5_verify.py
python3 pipeline/stage6_commit.py

# Or use the unified runner
python3 pipeline/runner.py --from-stage 1_3
```

**Current state:** S0 (922 MDs) ✅ S1 (323K segments) ✅ → S1.3–S6 need first run.
Embed models aligned (bge-m3/512d). All tuning constants in config. Zero drift.
