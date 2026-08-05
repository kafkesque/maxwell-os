Yes. I re-ran the review against the **current `main` state**, and this time I explicitly cross-checked the repository's recent commits against the files that are actually exposed on `main`, rather than carrying forward findings from the previous review.

The repository now shows **27 commits**, with the latest commits including D2177, D2178, D2179, D2180 and **D2181**. ([GitHub][1])

I am also correcting two findings from my previous review: **the Stage 2 `book_count/is_conv` issue and the `definition`/MinHash issue are not bugs**. They are inside the enclosing `main()` scope / `_build_fb_from_result()` scope, so Python closures make those references valid. I would **not change them**.

[Maxwell OS repository](https://github.com/kafkesque/maxwell-os?utm_source=chatgpt.com)

# Executive verdict

The codebase has improved materially.

The recent work is not cosmetic. D2177–D2181 addressed real architectural problems: dead Stage 3 removal, `networkx` dependency, crash-safe writes, retrieval classification filtering, source identity, schema validation, singleton handling, and an attempted embedding unification. ([GitHub][2])

But the latest audit exposes a new class of problem:

> **The architecture is becoming cleaner faster than the configuration/runtime contract is becoming authoritative.**

That is now the dominant risk.

My current assessment:

| Area                        | Verdict                                              |
| --------------------------- | ---------------------------------------------------- |
| Core RAG architecture       | **Strong**                                           |
| Source-aware clustering     | **Strong**                                           |
| Principle extraction design | **Strong conceptually**                              |
| Verification architecture   | **Good, but calibration incomplete**                 |
| Retrieval                   | **Good baseline**                                    |
| Provenance                  | **Good foundation**                                  |
| Dependency declaration      | **Incomplete**                                       |
| Config authority            | **Not trustworthy enough yet**                       |
| Provider abstraction        | **Still incomplete**                                 |
| Reproducibility             | **Not yet production-grade**                         |
| Evaluation maturity         | **Improving, but insufficient for claiming quality** |
| Production readiness        | **Not yet**                                          |

The biggest thing I would **not** do now is redesign the RAG architecture.

The biggest thing I **would** do is make the current architecture executable from one authoritative configuration and prove it with a clean-room run.

---

# 1. First: what has actually changed

The recent commit history matters.

### D2177

The repository explicitly says it fixed:

* `fsync` omission;
* `LIMIT 5000` in principle indexing;
* dead Stage 3 symbols;
* `networkx` dependency;
* dead `umap-learn`/`hdbscan`;
* silent exception paths in Stage 2;
* Stage 1.5 documentation.

It also claims all 69 Python files compile. ([GitHub][2])

### D2178

Added:

* source/book preflight validation;
* pipeline-state inspection;
* Stage 2 JSON validation;
* dead Stage 3 cleanup.

It also identified an **embedding model mismatch** between S1.5 and S4. ([GitHub][3])

### D2179

Fixed retrieval filtering so `classification_status='FAILED'` records aren't accidentally returned by the three search paths. It also corrected the Stage 1.5 performance documentation. ([GitHub][4])

### D2180

Added schema validation at the Stage 2 extraction boundary. That's good and I would keep it. ([GitHub][3])

### D2181

Attempted to unify S1.5 embeddings to `bge-m3`, 512-dimensional Matryoshka vectors, and added `nli_calibrate.py`. ([GitHub][5])

That last change is important because it is **not actually cleanly reflected in the current repository state**.

That is now my #1 issue.

---

# 2. P0 — There is a direct D2181/current-file contradiction

This is the most important thing I found.

The latest D2181 commit says:

```text
S1.5 embed_model_hf → BAAI/bge-m3
embed_dim → 512
embed_model → bge-m3
embed_backend → mps
```

and explicitly says the old 384-dimensional `bge-small` data was cleaned up. ([GitHub][5])

But the current `config/pipeline_config.yaml` exposed on `main` says:

```yaml
stage1_5:
  ...
  embed_model: BAAI/bge-small-en-v1.5
  embed_dim: 384
  embed_backend: mps
  embed_model_hf: BAAI/bge-small-en-v1.5
```

while `pipeline_paths.py` contains defaults for the newer 512-dimensional bge-m3 configuration. 

And `stage1_5_embed_cluster.py` now describes itself as:

> bge-m3 → 1024 native → Matryoshka 512d.



So we currently have three conflicting truths:

```text
D2181:
    bge-m3 / 512

pipeline_config.yaml:
    bge-small / 384

stage1_5_embed_cluster.py:
    bge-m3 / 512
```

This is not a documentation nit.

It affects the actual embedding geometry.

### Why this is dangerous

`pipeline_paths.py` reads the YAML configuration at import time. 

Therefore the actual runtime configuration currently appears to be:

```text
S15_EMBED_MODEL_HF = BAAI/bge-small-en-v1.5
S15_EMBED_DIM      = 384
S15_EMBED_BACKEND  = mps
```

because those YAML values override the defaults.

And Stage 1.5 explicitly checks:

```text
actual model output dimension == S15_EMBED_DIM
```

rather than silently padding/truncating. 

So the code itself is defensively written here.

The problem is that the **repository's declared intent and runtime config disagree**.

## Pragmatic resolution

Do not guess which is correct.

Run:

```bash
git rev-parse HEAD

git show HEAD:config/pipeline_config.yaml | \
  sed -n '/^stage1_5:/,/^stage1_3:/p'

git show HEAD:pipeline/stage1_5_embed_cluster.py | \
  sed -n '100,150p'
```

If HEAD really contains bge-small/384, then D2181's configuration change did not survive.

If HEAD contains bge-m3/512, then the raw GitHub representation I am seeing is stale/inconsistent.

**Do not run a large corpus until this is resolved.**

---

# 3. P0 — The Stage 2 configuration is definitely drifting from code

This one is not ambiguous.

Current configuration says:

```yaml
stage2:
  split_probe_enabled: true
  split_probe_min_size: 50
  split_probe_max_cohesion: 0.85
```



But current Stage 2 code has:

```python
SPLIT_PROBE_ENABLED = True
SPLIT_PROBE_MIN_SIZE = 20
SPLIT_PROBE_MAX_COHESION = 0.85
SPLIT_KMEANS_RANDOM_STATE = 42
```

and comments explicitly say the threshold was lowered from 50 → 20. 

This means:

# `pipeline_config.yaml` does not control the actual Stage 2 split threshold.

That's a real reproducibility defect.

The code will use:

```text
20
```

not:

```text
50
```

because the Stage 2 module's constants are used.

This is particularly important because this parameter directly controls **knowledge fragmentation/compression**.

### Fix

Move these into config:

```yaml
stage2:
  split_probe_enabled: true
  split_probe_min_size: 20
  split_probe_max_cohesion: 0.85
  split_probe_random_state: 42
  max_cluster_samples: 15
  max_probe_samples: 15
  workers: 3
```

Then:

```python
SPLIT_PROBE_MIN_SIZE = int(...)
```

etc.

No duplicated policy values.

---

# 4. P0 — The "single source of truth" claim is currently not true enough

`version.yaml` explicitly says:

> all version strings MUST be read from here. 

Good.

But the same principle needs to apply to **runtime behavior**, not just versions.

Right now you effectively have:

```text
version.yaml
pipeline_config.yaml
pipeline_paths.py
stage2 constants
stage1.5 constants
stage4 direct defaults
provider defaults
CLI defaults
documentation
```

The problem isn't having defaults.

The problem is having **multiple authoritative-looking values**.

---

# 5. P0 — The version gate still has a cwd vulnerability

This has not been fixed.

`runner.py` uses:

```python
Path("config/version.yaml")
Path("config/pipeline_config.yaml")
```

rather than the already available repository root. 

So the version gate depends on the caller's working directory.

You already have:

```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
```

at the top of the file. 

Use:

```python
version_yaml_path = _PROJECT_ROOT / "config" / "version.yaml"
pipeline_config_path = _PROJECT_ROOT / "config" / "pipeline_config.yaml"
```

This is a tiny fix and removes an unnecessary source of non-determinism.

---

# 6. P0 — Dependency declaration is still incomplete

This remains important.

`requirements.txt` now correctly includes:

* pydantic;
* PyYAML;
* tqdm;
* pyarrow;
* requests;
* numpy;
* scikit-learn;
* FAISS;
* sentence-transformers;
* transformers;
* networkx;
* datasketch;
* sqlite-vec.

That's substantially better. 

And I would **not** re-add `umap-learn` or `hdbscan`; D2177 correctly removed those dead dependencies. ([GitHub][2])

However:

## `ollama` is actually imported

`ollama_embed.py` has:

```python
import ollama
```

in its fallback path. 

But `ollama` is commented out in requirements:

```text
# ollama>=0.4
```

So the code's fallback path depends on an undeclared Python package.

### Fix

Either:

```text
ollama>=...
```

must be declared,

or better:

**remove the Python client dependency entirely** and make the fallback use the already-declared `requests` path.

For Maxwell, I prefer the latter.

You don't need two Ollama client mechanisms.

---

# 7. P0 — MLX is an optional provider, but optional dependencies aren't formally declared

`mlx_provider.py` imports:

```python
mlx.core
mlx_lm
```

and optionally `outlines`. 

Those aren't in `requirements.txt`. 

That's defensible **only if MLX is formally an optional extra**.

Right now the repository presents MLX as part of the supported provider architecture but does not have:

```toml
[project.optional-dependencies]
mlx = [...]
```

because `pyproject.toml` isn't actually a project definition at all. 

I would make this:

```toml
[project.optional-dependencies]
mlx = [
    "mlx",
    "mlx-lm",
    "outlines"
]
dev = [
    "pytest",
    "ruff",
    "mypy"
]
```

The exact versions can be pinned separately.

---

# 8. P0 — `pyproject.toml` is still only a tooling config

This is still a weak point.

It contains Ruff, mypy and pytest configuration, but no:

```toml
[project]
name
version
requires-python
dependencies
```



So Maxwell doesn't have one authoritative Python environment definition.

This matters more now because you're trying to support:

* MPS;
* MLX;
* OMLX;
* Ollama;
* FAISS;
* sentence-transformers;
* Transformers/NLI;
* sqlite-vec.

## Pragmatic solution

Don't over-engineer it.

Use:

```text
pyproject.toml
uv.lock
```

with optional:

```text
mlx
dev
```

extras.

That gives you:

```text
same commit
+
same lockfile
=
same Python environment
```

---

# 9. P1 — D2181 says "embedding unification", but the current Stage 1.5 implementation does not perform the advertised Matryoshka truncation

This is subtle.

The D2181 description says:

> native 1024d → Matryoshka 512d. ([GitHub][5])

But the MPS path in `stage1_5_embed_cluster.py` does:

```python
embeddings = np.array(raw, dtype=np.float32)

if embeddings.shape[1] != S15_EMBED_DIM:
    raise ValueError(...)
```

It doesn't truncate there. 

So if the actual model returns 1024 dimensions and config says 512, this code **fails**.

That isn't necessarily bad—fail-fast is better than silent corruption.

But then the architecture isn't actually:

```text
bge-m3 1024
      ↓
Matryoshka truncation
      ↓
512
```

It's:

```text
model output
      ↓
must already equal configured dimension
      ↓
FAISS
```

If bge-m3 sentence-transformers is really being used, verify whether the model call is explicitly configured to emit/truncate to 512.

If not, D2181's claimed implementation is incomplete.

---

# 10. P1 — Stage 1.5 is now much safer than it was

I want to explicitly preserve what is good here.

The embedding failure alignment bug was addressed properly.

The code tracks successful segment indices and filters the segments in lockstep. 

That is exactly the right response to an embedding batch failure.

Previously:

```text
segments[i]
      ↕
embedding[i]
```

could become misaligned.

Now the code explicitly reconstructs:

```text
successful_indices
        ↓
segments = [segments[i] ...]
```

before clustering. 

**Keep this.**

---

# 11. P1 — Source identity is now materially better

The current Stage 1.5 implementation uses canonical source IDs rather than raw filenames for source diversity. 

That's the right abstraction.

This prevents:

```text
same book
different filename
```

from being incorrectly treated as:

```text
two independent sources
```

And singleton preservation is now explicit:

```text
is_singleton = True
is_noise = False
```

which is also correct. 

I would **not change this**.

---

# 12. P1 — But Stage 1.5 still has hard-coded operational policy

This remains:

```python
FAISS_SEED = 42
BATCH_SIZE = 64
```



These aren't necessarily dangerous.

But if reproducibility is a constitutional requirement, I'd eventually put them under:

```yaml
stage1_5:
```

I would not make this a blocker right now.

---

# 13. P1 — The Stage 2 "principle discovery gate" is conceptually good

The current code probes clusters to determine whether one cluster contains multiple distinct mechanisms. 

That's a much better approach than blindly:

```text
cluster = principle
```

And the threshold was intentionally reduced from 50 to 20 to fight over-compression. 

I agree with the direction.

But I would make the resulting split **measurable**, not merely intuitive.

You need:

```text
probe says N=2
KMeans produces 2 groups
```

followed by:

```text
intra-group cohesion
inter-group separation
source coverage
```

and ideally an LLM consistency check.

Otherwise:

```text
LLM says 2
KMeans decides what 2 means
```

is still a weak epistemic bridge.

---

# 14. P1 — The split-probe fallback still biases toward merging

The current code logs probe failure but returns 1. 

That means:

```text
probe failure
     ↓
assume one principle
```

This isn't neutral.

It biases toward:

```text
false merge
```

rather than:

```text
false split
```

For Maxwell, that may be the wrong failure mode because your historical problem has explicitly been **compression death**.

I would change the state to:

```text
UNKNOWN
```

and record:

```json
{
  "split_probe_status": "FAILED",
  "split_probe_reason": "...",
  "fallback_policy": "single_principle"
}
```

Then the output remains usable but becomes auditable.

---

# 15. P1 — Stage 2 schema validation is a real improvement

The current `_build_fb_from_result()` calls `validate_fb_output()` before constructing the FB. 

Malformed output becomes a NULL/quarantined path rather than entering the pipeline.

That's good.

I would keep that.

---

# 16. P1 — Stage 2 checkpointing is also materially better

The current implementation:

* tracks processed cluster IDs;
* writes incremental checkpoints;
* uses `fsync`;
* logs corrupted resume state;
* continues in a controlled way.



And D2177 explicitly addressed the silent-error behavior around this area. ([GitHub][2])

Again: **keep it.**

---

# 17. P1 — The current MinHash code is not the bug I previously called it

This deserves an explicit correction.

Current `_build_fb_from_result()` defines:

```python
definition
```

and later uses it for MinHash within the same function. 

Likewise `book_count` and `is_conv` are defined in the enclosing `main()` scope and are available to the nested `_build_fb_from_result()` closure. 

So:

### Previous review finding:

> `NameError` due to `book_count`, `is_conv`, `definition`

### Current verdict:

**Withdrawn. Not a bug.**

This is exactly why verifying against the actual current code matters.

---

# 18. P1 — But MinHash state management still deserves cleanup

The current implementation inserts into LSH during FB construction:

```text
construct FB
→ is_near_duplicate()
→ insert into LSH
```

and later the main collection loop performs additional dedup logic.

I would simplify the lifecycle to:

```text
LLM result
 ↓
schema validation
 ↓
FB construction
 ↓
MinHash computation
 ↓
duplicate test
 ↓
ACCEPT / DROP
 ↓
insert accepted item into index
```

This is not a correctness emergency.

It's a state-machine simplification that will make future debugging easier.

---

# 19. P1 — The NLI calibration tool is currently not sufficient to calibrate NLI

This is the most important new conceptual problem in D2181.

The new tool says its automatic mode creates:

> positive = own evidence

and:

> negative = random evidence from another FB. ([GitHub][5])

But the implementation itself acknowledges:

```text
same FB evidence:
    should ENTAIL or NEUTRAL

other FB evidence:
    should CONTRADICT or NEUTRAL
```

([GitHub][5])

Yet the actual binary calibration logic treats:

```text
same FB = POSITIVE
other FB = NEGATIVE
```

That's not an NLI ground truth.

### Example

A generated definition:

> "Feedback loops can amplify small changes."

Its own evidence passage may merely discuss feedback loops without entailing that precise statement.

That is:

```text
NEUTRAL
```

not necessarily:

```text
ENTAILMENT
```

Similarly, another FB's evidence might genuinely entail a generic definition.

That is:

```text
ENTAILMENT
```

even though it came from another FB.

Therefore the auto calibration dataset has **label noise by construction**.

### Consequence

You can optimize F1 on the wrong target.

That's dangerous because you're calibrating the verifier that decides what knowledge enters the trusted store.

---

# 20. Correct NLI calibration design

Use three labels:

```text
ENTAILMENT
NEUTRAL
CONTRADICTION
```

and build the dataset deliberately:

### Positive entailment

Human confirms:

```text
FB claim
     ↓
directly supported by evidence
```

### Neutral

Evidence is related but does not establish the claim.

### Contradiction

Evidence conflicts with the claim.

At minimum I'd want:

```text
100 entailment
100 neutral
100 contradiction
```

before changing production thresholds.

And split:

```text
train/calibration
+
held-out test
```

so the threshold isn't optimized on the same examples used to report its performance.

---

# 21. P0/P1 — Current NLI threshold language is internally inconsistent

`pipeline_config.yaml` says:

```yaml
nli_model: tasksource/ModernBERT-base-nli
nli_model_fallback: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
```



But `stage5_verify.py` documentation currently describes the NLI path as DeBERTa and even gives DeBERTa benchmark numbers. 

That is another configuration/documentation mismatch.

The code may correctly select ModernBERT.

The problem is that the operator cannot reliably infer from the documentation which model actually performed verification.

### Fix

At runtime emit:

```json
{
  "nli_model": "...",
  "nli_model_revision": "...",
  "nli_provider": "...",
  "thresholds": {...}
}
```

into the verification record.

Then stop relying on prose.

---

# 22. P1 — Stage 5's fail-closed architecture is good

This part is worth preserving.

The current design explicitly:

```text
BORP
+
completeness
+
NLI
+
Gemma escalation
```

and does not allow verifier failures to become PASS. 

That's the correct philosophy for a knowledge compiler.

---

# 23. But call it "source consistency", not factual truth

The verifier is checking:

```text
FB
vs
source evidence
```

It is not establishing:

```text
FB
vs
reality
```

That distinction matters enormously.

If two books repeat the same unsupported claim, Maxwell can establish:

```text
multi-source consistency
```

without establishing:

```text
objective truth
```

So I recommend the vocabulary:

```text
SOURCE_SUPPORTED
SOURCE_UNCERTAIN
SOURCE_CONTRADICTED
```

rather than:

```text
FACT_VERIFIED
```

This will make the epistemic contract much cleaner.

---

# 24. P1 — BORP is still a corroboration rule, not an independence model

The source identity work is better now.

But:

```text
source_count >= 2
```

does not mean:

```text
independent evidence_count >= 2
```

You eventually want:

```text
source_id
author
title
edition
publication_year
relationship_to_other_source
```

and ideally:

```text
independent_source_count
```

rather than simply:

```text
source_diversity
```

Not a blocker for MVP.

Very important for the mature system.

---

# 25. Retrieval architecture: keep it

The current retrieval stack is sensible:

```text
keyword
+
FTS
+
vector
+
RRF
```

and the vector path embeds only the query while stored FB vectors live in sqlite-vec. 

The classification-status filter was also correctly added to all search paths. D2179 explicitly fixed this. ([GitHub][4])

I would **not introduce another vector database**.

No Pinecone.

No Weaviate.

No Qdrant.

No Elasticsearch.

No LangChain.

Not yet.

SQLite + FTS5 + sqlite-vec is perfectly reasonable at this stage.

---

# 26. Retrieval's biggest remaining issue is observability

The vector path falls back to FTS when embedding/vector search fails. 

That's operationally friendly.

But from an evaluation perspective:

```text
query
 ↓
expected hybrid retrieval
 ↓
vector failed
 ↓
FTS fallback
```

can look like a successful hybrid result.

That contaminates evaluation.

Every retrieval result should expose:

```json
{
  "retrieval_mode": "rrf",
  "fts_used": true,
  "vector_used": true,
  "metadata_used": true,
  "embedding_model": "bge-m3",
  "embedding_dim": 1024
}
```

or:

```json
{
  "retrieval_mode": "fts_fallback",
  "vector_used": false,
  "failure": "..."
}
```

Then your benchmark results mean something.

---

# 27. P1 — The embedding unification needs an explicit fingerprint

If you really move to:

```text
bge-m3
512d
Matryoshka
```

you need to stamp the vector space with:

```text
embedding_model
embedding_revision
embedding_dimension
normalization
truncation_dimension
provider
```

The DB should never contain an anonymous vector.

Otherwise six months from now:

```text
bge-m3 512
```

and:

```text
another embedding model 512
```

are indistinguishable at the schema level.

That's a classic silent retrieval corruption problem.

---

# 28. Stage 4 still bypasses the provider abstraction

This remains a genuine architectural weakness.

The provider contract explicitly says:

> pipeline stages call `resolve_provider(role)` — never a specific provider. 

But Stage 4 still directly calls:

```python
call_omlx_json(...)
```



Stage 2 supports MLX through the provider but still contains a direct OMLX path. 

So the actual architecture remains:

```text
provider abstraction
       +
direct provider calls
```

rather than:

```text
stage
 ↓
provider registry
 ↓
provider
```

## Pragmatic fix

Don't rewrite everything.

Create one resolver:

```python
generator = resolve_provider("generator")
```

and use:

```python
generator.generate_json(...)
```

in Stage 2, Stage 4 and Stage 5.

Then the C21 claim becomes real.

---

# 29. MLX structured JSON is better, but the "zero malformed output" claim is too strong

The provider supports `json_schema`, and when Outlines works it attempts schema-constrained generation. 

But the implementation explicitly falls back to unconstrained generation if Outlines/schema generation fails. 

So:

> "zero malformed output"

is not actually guaranteed.

The real contract is:

```text
try structured generation
→ fallback to unconstrained generation
→ parse/extract JSON
→ validate downstream
```

That's okay.

Just document it honestly.

---

# 30. The provider cache is also not doing what its comments imply

The code stores:

```text
system → token IDs + []
```

and later `_build_prompt()` simply returns:

```text
system + prompt
```

The actual KV cache isn't being reused by `_build_prompt()`. 

The comments themselves admit:

> MLX batch_generate supports prompt_caches for true KV reuse.

But the implementation currently creates:

```python
prompt_caches = [None] * len(prompts)
```

for batch generation. 

So the claimed:

> system prompt KV caching

appears to be **partially implemented / mostly bookkeeping**, not the full optimization described.

This is not a correctness blocker.

But I would not advertise `<50ms TTFT` or true KV reuse until benchmarked.

---

# 31. P1 — `batch_generate()` latency accounting is misleading

The code reports:

```python
latency_ms = elapsed / len(prompts)
```



That's an amortized batch latency, not the actual per-request latency.

For benchmarking:

```text
batch latency
throughput
per-item amortized latency
```

should be separate metrics.

Otherwise performance dashboards can become misleading.

---

# 32. P1 — Stage 6 documentation and SQL semantics are still slightly misleading

The file says:

> insert with upsert / `ON CONFLICT REPLACE`. 

But the implementation still uses:

```sql
INSERT OR REPLACE
```



SQLite `REPLACE` is delete-then-insert semantics, not a normal update.

I would eventually change it to:

```sql
INSERT ...
ON CONFLICT(fb_id)
DO UPDATE SET ...
```

especially once feedback/utilization history becomes important.

Not my current P0, but definitely worth fixing before persistent user feedback is treated as authoritative.

---

# 33. P1 — The repository still has stale v2/v3 headers

Examples include:

```text
justfile → Maxwell OS v2.0
.env.example → Maxwell OS v2.0
schemas.py → v2.0 wording
```

while `version.yaml` says:

```text
3.0
```



This is exactly the sort of drift the new version governance is supposed to eliminate.

The solution isn't manually editing every file forever.

Add CI:

```text
grep/version audit
```

that fails if stale version banners exist.

Better still, stop putting version numbers in banners unless they are generated.

---

# 34. P1 — `.env.example` still contains developer-specific absolute paths

It currently contains:

```text
/Users/barn/Library/CloudStorage/Dropbox/...
```



That's not a functional RAG bug.

But it is poor repository hygiene and contradicts the project's portability goal.

Use:

```text
MAXWELL_PIPELINE_ROOT=/path/to/maxwell-os
```

or simply:

```text
# MAXWELL_PIPELINE_ROOT=
```

with the repository root as default.

---

# 35. P1 — `pipeline_config.yaml` still contains obsolete HDBSCAN terminology

Even though Stage 3 is removed, the current config still contains:

```yaml
pipeline:
  hdbscan_min_cluster_size: 15
```

and `pipeline_paths.py` still creates an `HDBSCAN_MIN_CLUSTER_SIZE` compatibility value. 

D2177 intentionally removed the actual Stage 3 dependency/symbols, which is good. ([GitHub][2])

But this is now **dead configuration**.

Remove it once you are certain no compatibility tool consumes it.

Do not reintroduce HDBSCAN.

Just remove the ghost.

---

# 36. P1 — The current Stage 1.5 performance story needs to be based on actual benchmarks

D2179 did something good: it corrected the old unrealistic speed documentation. ([GitHub][4])

The repository now acknowledges the large cost of embedding hundreds of thousands of segments.

That's good.

But D2181 changes the embedding model from the previous bge-small path toward bge-m3.

Therefore the old benchmark numbers should now be treated as invalid until re-measured.

You need:

```text
model
hardware
dimension
batch size
segments/sec
peak RAM
peak unified memory
FAISS time
total S1.5 time
```

for the exact current configuration.

---

# 37. P0 — Clean-room reproducibility is still the missing proof

This is the test I care about most now.

Not:

```text
"69 files compile"
```

and not:

```text
"3-book E2E passed"
```

Those are useful but insufficient.

The repository should pass:

```text
fresh checkout
      ↓
fresh Python environment
      ↓
declared dependencies only
      ↓
no developer-specific env
      ↓
small deterministic fixture
      ↓
S0
 ↓
S1
 ↓
S1.3
 ↓
S1.5
 ↓
S2
 ↓
S4
 ↓
S5
 ↓
S6
      ↓
query
      ↓
expected result
```

D2179/D2180 have improved preflight substantially. ([GitHub][3])

Now use that machinery to prove the entire contract.

---

# 38. What I would NOT change

Because you explicitly asked me not to keep proposing changes to things that have already been fixed, here is the important "leave it alone" list.

### Keep the current:

**FAISS + reciprocal-neighbor + Louvain architecture.**

The implementation now properly preserves isolated nodes and handles failed embeddings in lockstep. 

**Canonical source identity.**

The switch away from filename-based diversity is correct. 

**Singleton preservation.**

Don't bring back "noise" semantics that silently discard unique knowledge. 

**Stage 2 schema validation.**

Keep it. 

**Incremental checkpoint + fsync work.**

Keep it. D2177 specifically addressed this. ([GitHub][2])

**Retrieval classification-status filtering.**

Keep it. ([GitHub][4])

**RRF hybrid retrieval.**

Keep it. 

**Fail-closed verification philosophy.**

Keep it. 

**Removal of Stage 3/HDBSCAN dependencies.**

Keep it. ([GitHub][2])

I would not spend engineering time replacing any of those.

---

# 39. The real architecture I recommend now

Don't add more RAG machinery.

Make the current system:

```text
SOURCE
  ↓
NORMALIZE
  ↓
CHUNK
  ↓
PREFILTER
  ↓
EMBED
  ↓
R-NN
  ↓
LOUVAIN
  ↓
SOURCE-DIVERSE CLUSTERS
  ↓
PRINCIPLE DISCOVERY
  ↓
PRINCIPLE EXTRACTION
  ↓
SCHEMA VALIDATION
  ↓
CLASSIFICATION
  ↓
SOURCE CONSISTENCY
  ↓
NLI
  ↓
CROSS-FAMILY REVIEW
  ↓
CANONICAL STORAGE
  ↓
FTS + VECTOR + RRF
```

That is already a good knowledge-compiler architecture.

The next improvement is not:

```text
add another retriever
```

It is:

```text
make every transition measurable and reproducible
```

---

# 40. What Maxwell should measure now

You are at the point where I would stop judging the system by:

```text
number of FBs generated
compression ratio
number of clusters
```

and start measuring:

### Ingestion

```text
source coverage
segment coverage
parse failure rate
prefilter recall
```

### Clustering

```text
cluster purity
cluster fragmentation
source diversity
singleton rate
intra-cluster similarity
inter-cluster separation
```

### Extraction

```text
principle precision
principle recall
false merge rate
false split rate
NULL rate
schema failure rate
```

### Verification

```text
entailment precision
neutral rejection
contradiction recall
quarantine rate
human overturn rate
```

### Retrieval

```text
Recall@5
Recall@10
nDCG@10
MRR
source coverage
verified-principle Recall@10
```

The last one is the KPI I would care about most:

# **Verified Principle Recall@10**

---

# 41. The most important new evaluation problem: compression

You already identified the historical compression problem in Stage 2.

The current code explicitly references the prior:

> 291:1 compression death spiral. 

So the system needs an explicit measurement:

```text
input principles
----------------
surviving principles
```

but **human-labelled**, not simply:

```text
segments / FBs
```

A better metric is:

```text
Gold principles represented in final verified FBs
-------------------------------------------------
Gold principles
```

Then compare:

```text
old Stage 2
vs
current Stage 2
```

with the same gold set.

That will tell you whether the new 20-segment split gate actually fixed the underlying problem.

---

# 42. My final priority order

## P0 — before another serious corpus run

### 1. Resolve the D2181 embedding contradiction

Prove whether HEAD is:

```text
bge-small / 384
```

or:

```text
bge-m3 / 512
```

Do not infer it from comments.

### 2. Make Stage 2 config authoritative

Especially:

```text
split_probe_min_size
split_probe_enabled
split_probe_max_cohesion
random seed
worker count
sampling limits
```

### 3. Make provider selection authoritative

No direct `call_omlx_json()` from stages.

### 4. Make dependencies reproducible

At minimum:

```text
project metadata
optional MLX dependencies
dev dependencies
lockfile
```

### 5. Run clean-room E2E

No stale checkpoints.

No developer paths.

No undocumented packages.

---

# P1 — immediately afterward

### 6. Fix NLI calibration methodology

Use real:

```text
ENTAILMENT
NEUTRAL
CONTRADICTION
```

labels.

### 7. Stamp embedding fingerprints

### 8. Stamp actual NLI model + revision + thresholds

### 9. Remove ghost HDBSCAN config

### 10. Remove stale v2 banners

### 11. Remove absolute paths from `.env.example`

---

# P2 — after the system is trustworthy

Then—and only then—I would work on:

```text
claim-level provenance
typed epistemic relationships
reranking
better query routing
source independence modeling
adaptive clustering
```

Those are worthwhile.

They are **not** the current bottleneck.

---

# Bottom line

My updated S-tier assessment is actually **more positive about the architecture and more negative about the configuration discipline**.

The previous audit found several implementation defects. The latest repository shows that the team has genuinely acted on many of them:

```text
Stage 3 removal          ✓
dead dependencies        ✓
networkx                 ✓
fsync                    ✓
source identity          ✓
singleton preservation   ✓
classification filter    ✓
schema validation        ✓
embedding failure align  ✓
retrieval RRF            ✓
checkpoint robustness    ✓
```

The repository history confirms those changes rather than merely claiming them. ([GitHub][6])

But the latest D2181/D2180 work has introduced—or exposed—a more fundamental problem:

```text
                    ┌──────────────────────┐
                    │  INTENDED ARCHITECTURE│
                    └──────────┬───────────┘
                               │
                   bge-m3 / 512 / NLI
                               │
                               ▼
                    ┌──────────────────────┐
                    │  ACTUAL RUNTIME      │
                    └──────────┬───────────┘
                               │
                 YAML / code / docs disagree
```

That is the thing I would fix **before touching the RAG algorithm again**.

And one important correction to my previous answer:

> **I would remove the two Stage 2 "P0 bugs" I previously reported from the bug list. They are not bugs in the current code.**

The current real P0 is **configuration/runtime divergence**, especially the embedding configuration and Stage 2 split threshold.

If you fix those five things—**embedding state, config authority, provider authority, dependency reproducibility, and clean-room E2E**—I would consider Maxwell ready for the next serious empirical phase: **measure whether the system actually preserves and retrieves knowledge, rather than adding more architecture.**

[1]: https://github.com/kafkesque/maxwell-os "GitHub - kafkesque/maxwell-os · GitHub"
[2]: https://github.com/kafkesque/maxwell-os/commit/392e69a "D2177: P0 fixes from cross-examination of 4 LLM evaluations (Aug 5) · kafkesque/maxwell-os@392e69a · GitHub"
[3]: https://github.com/kafkesque/maxwell-os/commit/b49831a "D2180: Preflight sync + bloat cleanup + T2.2 JSON schema validation · kafkesque/maxwell-os@b49831a · GitHub"
[4]: https://github.com/kafkesque/maxwell-os/commit/5b1a703 "D2179: Tier 0 fixes — classification filter, book validation, speed docs · kafkesque/maxwell-os@5b1a703 · GitHub"
[5]: https://github.com/kafkesque/maxwell-os/commit/7ad4236 "D2181: T1.2 embedding unification + T1.4 NLI calibration tool · kafkesque/maxwell-os@7ad4236 · GitHub"
[6]: https://github.com/kafkesque/maxwell-os/commits/main "Commits · kafkesque/maxwell-os · GitHub"
