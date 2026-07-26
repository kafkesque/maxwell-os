# Maxwell OS v2.0 — MISSION.md

## WHY MAXWELL OS EXISTS

AI agents are everywhere — but they're ungrounded. They hallucinate. They can't cite sources. They don't know what actually works in practice.

Maxwell OS exists to solve this: **a sovereign system that extracts convergent, verified knowledge from the world's best books, tests every principle against reality through real execution, and renders that knowledge as executable skills that cite their sources.**

Your AI shouldn't guess. It should know. And you should own the system that knows.

## WHAT MAKES THIS DIFFERENT

| Every other system | Maxwell OS |
|-------------------|------------|
| Knowledge is claimed, not verified | **BORP-verified** — every claim grounded in ≥2 distinct sources |
| Principles are static, never tested | **fb_reliability** — every principle tracked across real executions. Does it actually work? |
| Vendor lock-in (API keys, cloud) | **100% sovereign** — M1 Max, local models, $0 marginal cost |
| Classification is fixed | **Taxonomy earns itself** — raw labels accumulate, earn canonical slots |
| Agent skills are hand-written prompts | **Skills cite verified FBs** — every step grounded in extracted, tested knowledge |

## THE THREE LAYERS

```
LAYER 3   BUSINESS OPS    Automated operations: trigger → retrieve FBs → execute skills → verify
  (post-scale)              ↑ "Live in the system. Dogfood everything."

LAYER 2   ORCHESTRATION   FB → PT → PI → Recipe → Trust Ledger
  (critical path)           ↑ "The bridge from knowledge to action. THE PRODUCT."

LAYER 1   KNOWLEDGE       SQLite + Parquet + FTS5 + hybrid search + fb_relationships
  (in progress)             ↑ "Queryable, classified, traced, reliability-scored."

LAYER 0   PIPELINE        7-stage extraction: books → principles → FBs → SQLite
  (built)                   ↑ "Phase 0 complete. Proven. Hardened. Property logic complete."
```

## THE ONE THING THAT MATTERS RIGHT NOW

> **Layer 2 is the product.** 7,299 lines of pipeline code produce FBs.
> 0 lines of orchestration code turn FBs into skills.
> The bridge from knowledge to action IS the product.
> **Build the bridge.**



---

## MAXWELL OS PHILOSOPHY — Infrastructure Independence (Ratified 2026-07-22)

### Core Principle: Every Component is Swappable

Maxwell OS is a **sovereign knowledge operating system** designed to survive any vendor, any model deprecation, any OS change. The architecture is built on one rule: **every infrastructure component must be replaceable without touching pipeline logic.**

### The Swappable Layers

| Layer | Default | Swappable To | Protocol |
|-------|---------|-------------|----------|
| **Inference** | OMLX (local MLX) | Ollama, vLLM, llama.cpp, OpenAI API, Anthropic API | InferenceProvider |
| **Embeddings** | Ollama bge-m3 | sentence-transformers, OpenAI embeddings | EmbeddingProvider |
| **Storage** | SQLite + FTS5 + sqlite-vec | PostgreSQL, LanceDB, JSON files | StorageBackend |
| **Memory** | psutil (cross-platform) | vm_stat (macOS), cgroups (Linux) | MemoryMonitor |
| **Process** | psutil (cross-platform) | systemd, launchd | ProcessManager |
| **Agent Interface** | MCP (stdio) | REST API, gRPC | Open protocols |
| **Sync** | None (local-only) | Syncthing, rsync, iCloud | SyncProvider |
| **Distribution** | pipx / pyproject.toml | Docker, Homebrew, PyInstaller | Standard packaging |

### Sovereignty is Non-Negotiable

Local-first, always. The user owns their data, their models, their knowledge base. Frontier API access is an **explicit opt-in** — never a default, never hidden. Verification (C8/R5) is always local.

### Hybrid Option

allow_api: true in config enables frontier models for non-verification roles. verify_always_local: true is constitutional (C22) and cannot be overridden.

### Future-Proof by Design

- **No vendor lock-in.** Every provider has a documented replacement path.
- **No model dependency.** Swap Qwen to Llama to Mistral by changing one config line.
- **No OS dependency.** psutil + pathlib throughout. macOS today, Linux tomorrow, Windows eventually.
- **No silent breakage.** Dependency updates tested against golden set before adoption.
- **No dead ends.** Every architectural decision preserves a migration path. Protocols first, implementations follow.

### Lightweight is the Default

Streamlined by design. Every feature starts behind a feature flag. Quality tiers (balanced | maximum | minimum) let the user choose their tradeoff. Bloat is always opt-in.

### Hardware-Adaptive

Minimum target: 16GB RAM, any modern CPU. Auto-detects available resources and selects appropriate model quant. Degrades gracefully — never crashes with OOM.


## PHASE 0: ALPHA KIT (NOW)

**Prove the full chain: book → FB → PT → execution → reliability score.**

| Step | What | Success Criteria |
|------|------|-----------------|
| 0.1 | Run pipeline on 3 pricing books (E-Myth, Profit First, $100 Startup) | 30-50 convergent FBs, ≥60% PASS |
| 0.2 | Extract 1 PT ("Price a New Client Project") | PT cites ≥5 verified FBs |
| 0.3 | Execute 1 PI manually | All consulted FBs logged with outcomes |
| 0.4 | Build fb_reliability table | Scores update after PI execution |
| 0.5 | Build render_recipe.py v2 | PT + FBs → Goose Recipe YAML |

**Kill criteria (any one):**
- 3 pricing books produce <20 convergent FBs → pipeline yield broken at domain level
- render_recipe.py v2 exceeds 2,000 lines → bridge too heavy; simplify
- End-to-end cycle >30 minutes → optimize retrieval or reduce FB corpus per recipe
- PT doesn't produce useful output → FB quality or PT design insufficient

## PHASE 1: RELIABILITY INFRASTRUCTURE

**Make every FB track its own usefulness.**

| Step | What |
|------|------|
| 1.1 | Port fb_reliability from v1 (`tools/render_recipe.py`, 1070 lines) to v2 |
| 1.2 | Wire PI execution logging — every FB consulted gets an outcome |
| 1.3 | Dynamic Zone 3 rendering — STABLE GATE shows reliability_score + total_executions |
| 1.4 | Add fb_relationships table (supports/contradicts/extends/applies_to) |
| 1.5 | Spike: test Outlines/XGrammar with OMLX for schema-constrained Stage 4 generation |

## PHASE 2: DOMAIN SATURATION

**200-400 convergent FBs across 2 domains.**

| Domain | Books | Target FBs | PTs |
|--------|-------|-----------|-----|
| Pricing | 50 | 50-100 FBs | Price a Project, Scope Fixed-Bid, Negotiate Terms |
| Branding | 50 | 50-100 FBs | Position Your Niche, Write Brand Story, Design Visual Identity |

## PHASE 3: LIVE IN THE SYSTEM (DOGFOOD)

**Use Maxwell OS for your actual business operations. Every use is a data point.**

| Business Task | Component Tested |
|--------------|-----------------|
| Price new client projects | Pricing PTs + FB reliability logging |
| Write proposals | Proposal PT (new) |
| Design brand identity | Branding PTs + cross-domain retrieval |
| Build websites | Web UI PT (new) |
| Run marketing | Marketing PT (new) |

**Weekly retrospective:** What worked? What failed? Which FBs were irrelevant? Which were missing?

## PHASE 4: FRIEND BETA

**3 friends use Maxwell OS for THEIR businesses.**

**Binary gate:** Would 2/3 pay £500+ for this? → Go / No-Go for commercial launch.

## PHASE 5: COMMERCIAL LAUNCH

**Lifetime license + upgrade engine. Sovereign product, not SaaS.**

| Tier | What | Price |
|------|------|-------|
| Beta Kit | 1 domain + 3-5 PTs + installation | £750-1,000 |
| Domain Expansion | Additional domain kits | £300-500 |
| Major Upgrade | New features (MCP, multi-agent, conformal) | £400-600 |
| Support Retainer | Email support, bug fixes, priority features | Optional |
| Custom Build | Bespoke knowledge system for client domain | £5,000-15,000 |

## CONSTRAINTS (NON-NEGOTIABLE)

| ID | Constraint | Why |
|----|-----------|-----|
| C1 | $0 marginal cost | M1 Max 64GB, local only. All models run locally. |
| C3 | Sovereign | No cloud. No API keys. No vendor lock-in. Your knowledge, your hardware. |
| C2/C4 | Future-proof | Open formats (SQLite + Parquet). Multiple model families. No single-provider dependency. |
| R5 | Generator ≠ Verifier | Different model family for extraction vs. verification. No self-grading. |
| R7 | temp=0.0 | Deterministic generation. Reproducible results. |
| R14 | Every object stamped | schema_version, gen_model, pipeline_commit, pipeline_run_id. Full lineage. |

## THE COMPETITIVE MOAT

| Moat | Defensibility | Status |
|------|--------------|--------|
| **Convergent extraction (BORP + clustering)** | High — no competitor has cross-source convergence as a first-class gate | Built |
| **Execution-based reliability (fb_reliability)** | High — novel. "Does this principle actually work?" unanswered by any competitor | Spec'd |
| **Sovereign stack ($0 marginal, local only)** | Structural — cloud competitors can't match economics at scale | Built |
| **Self-evolving taxonomy** | Medium — raw label accumulation earns canonical slots | Built (P1.5-A/B) |
| **Dogfooding as distribution** | Personal — time-limited (12-18 months), not replicable | Strategy |

## THE KILL CRITERIA (ANY ONE = PIVOT)

1. Pipeline can't produce ≥20 convergent FBs from 3 same-domain books
2. Friends won't use it after 2 weeks in Alpha
3. No friend willing to pay after Alpha ("would you pay £500+ for this?")
4. Verification catches >30% false positives in FB extraction
5. End-to-end cycle (book → FB → PT → execution) >30 minutes
6. 12 months in, you're not using it for your own business

---

*Maxwell OS v2.0 — Build the bridge. Test everything. Own your AI.*
*Cross-examined: Kimi (2026-07-19), Goose (2026-07-19)*
