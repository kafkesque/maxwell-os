I re-audited the **current `main` branch as it exists today**, this time treating it as a codebase rather than merely an architecture document: dependency declarations, configuration, pipeline entry points, stage contracts, provider abstraction, extraction, clustering, verification, persistence, retrieval, and governance were cross-checked against one another.

[Maxwell OS — current main repository](https://github.com/kafkesque/maxwell-os?utm_source=chatgpt.com)

I also want to explicitly correct the earlier review where appropriate: **some issues I previously flagged have been fixed**. The current repository now has `networkx` declared, Stage 3 is largely removed from the actual runner/path layer, hybrid retrieval really does fuse FTS + vector + metadata, singleton handling exists, and the NLI marginal path now escalates rather than automatically passing.

However, this deeper pass uncovered **two much more serious Stage 2 defects** that I would treat as blockers.

# Executive verdict

**The architecture is promising. The current implementation is not yet safe for a serious corpus run.**

My assessment now:

| Area                          |            Assessment |
| ----------------------------- | --------------------: |
| Overall RAG architecture      |            **8.5/10** |
| Retrieval architecture        |              **8/10** |
| Semantic clustering           |              **8/10** |
| Provenance design             | **8/10 conceptually** |
| Verification architecture     |            **7.5/10** |
| Persistence                   |            **7.5/10** |
| Provider abstraction          |              **5/10** |
| Runtime contracts             |              **5/10** |
| Dependency reproducibility    |              **5/10** |
| Configuration discipline      |            **4.5/10** |
| Current production readiness  |              **5/10** |
| Potential after consolidation |              **9/10** |

The key distinction is:

> **Maxwell's problem is no longer primarily “wrong RAG architecture.” It is “the implementation has outrun its own contracts.”**

And there are now concrete bugs demonstrating that.

---

# 1. P0: Stage 2 has a real variable-scope bug

This is the most important finding in this audit.

Inside `_process_cluster()`, these variables are local:

```python
is_conv
book_count
```

But `_build_fb_from_result()` is defined as a separate top-level function and does **not** receive them:

```python
def _build_fb_from_result(
    result,
    cluster,
    evidence_passages,
    cid,
):
```

Yet it later constructs:

```python
"source_diversity": book_count,
"is_convergent": is_conv,
```

Those names are not parameters of `_build_fb_from_result()`. 

The caller does:

```python
fb = _build_fb_from_result(
    principle,
    cluster,
    evidence_passages,
    cid
)
```

It does **not** pass `book_count` or `is_conv`. 

### Consequence

When extraction reaches those fields, Python will raise:

```text
NameError: name 'book_count' is not defined
```

or:

```text
NameError: name 'is_conv' is not defined
```

The worker exception is then caught by the outer future loop:

```python
except Exception as e:
    print(...)
    continue
```

So this is especially nasty.

The pipeline can appear to be "continuing" while **dropping extracted principles**.



## Fix

Make the function contract explicit:

```python
def _build_fb_from_result(
    result: dict,
    cluster: dict,
    evidence_passages: list[str],
    cid: str,
    *,
    is_convergent: bool,
    source_diversity: int,
) -> dict | None:
```

Then:

```python
fb = _build_fb_from_result(
    principle,
    cluster,
    evidence_passages,
    cid,
    is_convergent=is_conv,
    source_diversity=book_count,
)
```

Even better:

**derive them inside the function from `cluster`.**

```python
source_diversity = int(
    cluster.get(
        "source_diversity",
        len(cluster.get("source_ids", cluster.get("source_books", [])))
    )
)

is_convergent = bool(cluster.get("is_convergent", False))
```

That is the cleaner design because the cluster is already the authoritative source.

### Priority: **P0**

---

# 2. P0: the Stage 2 MinHash dedup code has another scope bug

There is a second concrete defect immediately after that.

In the post-extraction loop:

```python
if minhash_ok and fb.get("minhash_signature"):
    ...
    cur_mh = make_minhash(definition)
```

But `definition` is not defined in that scope. 

The definition exists inside `_build_fb_from_result()`:

```python
definition = result.get("definition", "").strip()
```

but that local variable is not returned separately.

So this code should be:

```python
cur_mh = make_minhash(
    fb.get("definition", "")
)
```

or preferably:

```python
cur_mh = make_minhash(fb_definition(fb))
```

using the schema accessor.

### Why this matters

Unlike the first bug, this one occurs **after the future has successfully returned an FB**.

So it can terminate the main Stage 2 loop rather than merely losing one cluster.

And it means your "D2152 fixed MinHash dedup" path is not actually safe.

---

# 3. The Stage 2 dedup architecture itself is unnecessarily complicated

There is also a design issue underneath the bug.

`_build_fb_from_result()` immediately calls:

```python
is_near_duplicate(...)
```

and inserts the MinHash into the LSH/cache. 

Then later the main loop performs another explicit Jaccard comparison against previous FBs.

So you effectively have:

```text
FB generation
   ↓
LSH insertion
   ↓
later explicit comparison
```

The code comments say the comparison was "fixed," but the responsibilities are mixed.

I'd simplify it to:

```text
generate candidate
      ↓
construct FB
      ↓
compute MinHash
      ↓
compare against accepted FBs
      ↓
accept / reject
      ↓
ONLY THEN insert into dedup index
```

This makes the dedup state machine deterministic.

---

# 4. P0: your schema claims are stronger than the runtime enforcement

`scehmas.py` says:

> Every pipeline stage reads/writes typed objects.

and says Pydantic contracts make invalid labels structurally impossible. 

But the actual Stage 2/4/5 pipeline operates predominantly on:

```python
dict
```

with `.get()`.

The `schema_accessor.py` layer explicitly exists to provide compatibility over dictionaries. 

That's pragmatic—but it means the repository should **not claim that Pydantic is the enforced inter-stage contract**.

Right now you have:

```text
Pydantic models
        +
dict-based runtime
        +
compatibility accessors
```

rather than:

```text
Pydantic boundary
        ↓
validated artifact
        ↓
Pydantic boundary
```

## Pragmatic solution

Do **not** convert the whole pipeline to Pydantic internally.

Instead validate at stage boundaries:

```text
Stage 0 → SegmentMeta
Stage 1 → Segment
Stage 1.5 → Cluster
Stage 2 → Principle
Stage 4 → FB
Stage 5 → VerifiedFB
Stage 6 → FBRecord
```

Inside each stage, dictionaries are fine.

At ingress/egress:

```python
validated = Cluster.model_validate(raw)
```

and:

```python
jsonl.write(validated.model_dump_json())
```

That gives you actual contracts without turning Maxwell into a Pydantic-heavy application.

---

# 5. The provider abstraction is currently mostly aspirational

This is a major architectural point.

The provider protocol is actually nicely defined:

```text
InferenceProvider
EmbeddingProvider
```

and explicitly says stages should call the abstraction rather than a concrete provider. 

Good design.

But the actual code does not consistently follow it.

For example Stage 2 directly imports:

```python
pipeline.providers.mlx_provider
pipeline.omlx_call
```



Stage 4 directly invokes:

```python
call_omlx_json(...)
```



Stage 5 directly works with OMLX.

Retrieval directly imports:

```python
pipeline.ollama_embed.batch_embed
```



Stage 6 directly imports the same embedding implementation. 

So the actual architecture is:

```text
Protocol
   │
   ├── some code uses protocol
   │
   └── lots of code directly calls provider
```

rather than:

```text
Pipeline
   ↓
Provider registry
   ↓
Provider implementation
```

## Pragmatic fix

Create:

```text
pipeline/runtime.py
```

with:

```python
resolve_generation_provider(role)
resolve_embedding_provider(role)
```

Then all stages call:

```python
generator.generate_json(...)
embedder.embed(...)
```

No stage should import:

```text
omlx_call
ollama_embed
mlx_provider
```

directly.

That would make C21 real rather than documentary.

---

# 6. Dependency management is still not production-grade

The good news:

`requirements.txt` is now much better.

It contains:

* pydantic
* pyyaml
* tqdm
* pyarrow
* requests
* numpy
* scikit-learn
* faiss-cpu
* sentence-transformers
* transformers
* networkx
* datasketch
* sqlite-vec



So I **withdraw my previous criticism about `networkx` missing**.

That was fixed.

But there is another issue.

## MLX is not declared

`mlx` and `mlx_lm` are imported directly by the MLX provider. 

`outlines` is also imported for structured generation. 

None of those appear in `requirements.txt`. 

Now, if MLX is intentionally an optional Apple-only provider, that's fine.

But then declare that explicitly:

```toml
[project.optional-dependencies]
mlx = [
    "mlx",
    "mlx-lm",
    "outlines"
]
```

and document:

```bash
pip install -e '.[mlx]'
```

Otherwise the claim:

> "all imports ⊂ requirements.txt"

is false.

And Maxwell's Constitution explicitly states that rule. 

---

# 7. Pandoc and Docling are hidden system dependencies

Stage 0 executes:

```text
pandoc
docling
```

as external binaries. 

These are not Python dependencies.

That's fine—but they must be treated as **system prerequisites**.

Right now the actual dependency graph is:

```text
Python packages
+
Pandoc
+
Docling
+
OMLX
+
Ollama
+
local models
+
Apple/MPS environment
```

This is much larger than `requirements.txt` suggests.

I'd create:

```text
docs/INSTALL.md
```

with an explicit dependency matrix:

| Component   | Type                    | Required?           |
| ----------- | ----------------------- | ------------------- |
| Python 3.12 | runtime                 | yes                 |
| Pandoc      | system binary           | EPUB / PDF fallback |
| Docling     | system/model runtime    | PDF preferred path  |
| OMLX        | local service           | generation          |
| Ollama      | local service           | embeddings          |
| MLX         | Python optional         | direct MLX provider |
| outlines    | Python optional         | structured MLX JSON |
| FAISS       | Python                  | clustering          |
| sqlite-vec  | Python/native extension | vector retrieval    |

This is a much more honest install contract.

---

# 8. `pyproject.toml` is still not the project definition

Current `pyproject.toml` only configures Ruff, mypy and pytest. 

It does not define:

```toml
[project]
name =
version =
requires-python =
dependencies =
```

So Maxwell has:

```text
requirements.txt
pyproject.toml
config/version.yaml
```

but no single authoritative packaging environment.

And the dependencies are not pinned.

For a pipeline that claims reproducibility, I'd move to:

```text
pyproject.toml
+
uv.lock
```

or:

```text
pyproject.toml
+
requirements.in
+
requirements.txt
```

with hashes.

The point isn't which package manager you choose.

The point is:

> **same Git commit + same lockfile = same Python environment.**

---

# 9. The versioning system is conceptually good but not actually single-source

`config/version.yaml` explicitly claims:

> Single Source of Truth for Versioning. 

That's good.

The runner even performs a consistency check. 

But the repository still has obvious stale version/architecture declarations.

For example:

### `CONSTITUTION.md`

It says:

```text
3 layers: Pipeline (9-stage)
```

then immediately describes the current pipeline as:

```text
8-stage
```

and the bottom still says:

```text
Schema: 2.1
Commit: v2.1.1
```



### `AGENTS.md`

It still explicitly lists:

```text
stage3_cluster.py
UMAP + HDBSCAN
```

even though the actual pipeline has Stage 3 removed. 

It also says:

```text
Generator: Qwen3-Coder
```

while the current pipeline configuration specifies:

```text
Qwen3.6-35B-A3B-4bit
```



### `.env.example`

Still says:

```text
Maxwell OS v2.0
```

and contains an absolute developer-specific filesystem path:

```text
/Users/barn/Library/CloudStorage/Dropbox/...
```



That violates the spirit—and arguably the letter—of C12.

---

# 10. The version gate itself has a subtle portability bug

`runner.py` does:

```python
Path("config/version.yaml")
```

rather than resolving relative to the repository/module root. 

So:

```bash
cd /repo
python -m pipeline.runner
```

works.

But from another working directory:

```bash
python /repo/pipeline/runner.py
```

the version gate can fail to find:

```text
config/version.yaml
```

and explicitly says:

> skipping version gate.

That's exactly the opposite of what a startup integrity gate should do.

### Fix

Use:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
version_yaml = PROJECT_ROOT / "config" / "version.yaml"
```

Then the gate is independent of `cwd`.

---

# 11. Configuration discipline is still a significant problem

Maxwell's C12 says:

> NEVER hardcode ANY value.



But Stage 2 contains:

```python
MAX_PROBE_SAMPLES = 15
MAX_PER_BOOK = 2
SPLIT_PROBE_MIN_SIZE = 20
SPLIT_PROBE_MAX_COHESION = 0.85
SPLIT_KMEANS_RANDOM_STATE = 42
```



And the worker count is:

```python
max_workers = 3
```



Meanwhile configuration already has many Stage 2 controls. 

This is exactly the kind of drift C12 was created to prevent.

## Fix

Move them into:

```yaml
stage2:
  split_probe:
    enabled: true
    min_size: 20
    max_cohesion: 0.85
    max_samples: 15
    max_per_book: 2
    random_seed: 42

  workers: 3
```

Then there should be **zero policy numbers in Stage 2 code**.

---

# 12. Your `stage1.5` clustering design is still one of Maxwell's strongest decisions

The current implementation is:

```text
segment embeddings
        ↓
FAISS KNN
        ↓
reciprocal nearest-neighbor edges
        ↓
Louvain
        ↓
clusters + singletons
```



I would keep this.

The R-NN constraint is sensible because it reduces one-way semantic bridges.

The code also correctly handles embedding failures by filtering the segment list in lockstep with successful embeddings. 

That is an excellent correction.

---

# 13. But the clustering stage has an epistemic weakness: similarity is doing too much

The current cluster formation is still ultimately driven by:

```text
cosine similarity >= 0.75
+
reciprocal neighborhood
```



That is fine as a candidate generator.

It should **not be treated as proof of conceptual identity**.

This is important because the downstream Stage 2 prompt assumes:

> these passages are semantically related.

That's reasonable.

But semantic proximity can mean:

```text
same topic
same vocabulary
same author
same example
same causal mechanism
```

Those are very different things.

### My recommendation

Do not replace clustering.

Instead treat it explicitly as:

> **candidate semantic neighborhoods**

Then let Stage 2 establish:

```text
mechanism identity
```

That is much cleaner epistemically.

---

# 14. The Stage 2 principle-discovery gate is a good idea

This is one of the best recent changes.

Current flow:

```text
large / lower-cohesion cluster
          ↓
principle-count probe
          ↓
N = 1
       or
N = 2–4
          ↓
KMeans split
          ↓
extract
```



This is much better than blindly forcing:

```text
one cluster = one principle
```

The source-stratified sampling is also sensible. 

---

# 15. But LLM → integer → KMeans is still fragile

The architecture is:

```text
Phi
 ↓
"3 principles"
 ↓
KMeans(k=3)
```

The LLM doesn't identify:

```text
Principle A → segments 1,4,7
Principle B → segments 2,8,9
Principle C → segments 3,5,6
```

It only provides the cardinality.

Then geometry determines the actual split.

That's a weak bridge.

## Better version

Ask the discovery model for:

```json
{
  "principles": [
    {
      "id": "A",
      "description": "...",
      "segment_indices": [1,4,7]
    }
  ]
}
```

Then:

```text
LLM hypothesis
       ↓
embedding partition
       ↓
agreement check
       ↓
split
```

You don't have to trust either the LLM or KMeans alone.

---

# 16. Stage 2's fallback behavior is dangerous

The discovery function explicitly says:

> return 1 on any error — fail-safe: don't split. 

This is operationally convenient.

But semantically:

```text
LLM fails
 ↓
assume one principle
 ↓
compress everything
```

That is not actually a neutral fallback.

It's biased toward **false merging**.

For Maxwell, I would rather use:

```text
probe failure
 ↓
mark split_status = UNKNOWN
 ↓
use conservative extraction
 ↓
flag for evaluation
```

rather than pretending:

```text
N = 1
```

---

# 17. Stage 2's singleton strategy is useful but expensive

Singletons are correctly preserved as a separate semantic state. The code treats isolated nodes as singleton clusters. 

The optional singleton extraction path then sends viable singleton text to the LLM. 

Good idea.

But:

```text
singleton
+
text >= 50 chars
```

is not enough to justify an expensive generation call.

You need a cheap gate first:

```text
singleton
 ↓
content quality
 ↓
principle likelihood
 ↓
LLM extraction
```

Otherwise headings, broken extraction fragments, bibliographic fragments and isolated prose all consume generation capacity.

---

# 18. Stage 1.3 is appropriately conservative in one respect

The code explicitly says the causal/definition/procedure markers are:

> heuristic, not a gate.



That's good.

However, the actual dropping logic includes:

```text
too short
structural patterns
citation density
```



The danger is that a legitimate principle can be:

```text
short
descriptive
counterintuitive
mathematical
historical
```

and have no obvious causal marker.

So Stage 1.3 should be evaluated by:

# **principle recall loss**

not by how many junk chunks it removes.

I'd require:

```text
<1–2% gold-principle recall loss
```

before calling the prefilter production-safe.

---

# 19. Stage 4's single-FB optimization is pragmatic

This is good engineering.

Instead of:

```text
one principle
 ↓
LLM rewrite
```

the code reuses the existing FB and runs CRIBS-style enrichment. 

That saves a lot of local inference.

Keep it.

---

# 20. But Stage 4's relationship graph has a scalability problem

The current relationship builder compares FB pairs.

It creates relationships based on:

```text
domain overlap
discipline overlap
source crossover
semantic_near
```



For `N` FBs this is:

```text
N(N-1)/2
```

comparisons.

At:

```text
10,000 FBs → ~50 million pairs
50,000 FBs → ~1.25 billion pairs
```

That is not a sustainable graph-building strategy.

## Correct evolution

Use:

```text
FB embeddings
 ↓
FAISS top-k
 ↓
candidate pairs
 ↓
metadata overlap
 ↓
typed relationship classifier
```

instead of:

```text
every FB × every FB
```

Don't add Neo4j.

Don't add LightRAG.

Just fix candidate generation.

---

# 21. And don't call those relationships a knowledge graph yet

Current edges are:

```text
domain_overlap
discipline_overlap
source_crossover
semantic_near
```



Those are useful **retrieval relationships**.

They aren't yet:

```text
supports
contradicts
requires
refines
generalizes
causes
```

So I would call it:

> semantic relationship index

until typed epistemic edges actually exist.

---

# 22. Retrieval is now structurally good

This is another area where the current repository deserves credit.

`search_hybrid()` really does:

```text
FTS
+
vector
+
metadata
↓
RRF
```



And it uses a candidate pool:

```python
POOL_SIZE = min(limit * 5, 100)
```

before fusion. 

That's a perfectly respectable baseline.

I would **not replace it**.

---

# 23. But vector retrieval is still too failure-tolerant

`search_vector()` has several broad fallbacks:

```text
vector failure
 ↓
FTS
```

and even catches broad exceptions. 

Operationally that's friendly.

For evaluation, it's dangerous.

A query that you think was evaluated with:

```text
FTS + vector + metadata
```

might actually have been evaluated as:

```text
FTS
```

without the caller knowing.

### Fix

Return:

```json
{
  "results": [...],
  "retrieval_mode": "rrf_fts_vector_metadata",
  "vector_available": true
}
```

or attach metadata to the result.

Then evaluation knows what actually happened.

---

# 24. The embedding architecture needs stronger version stamping

There are actually two embedding spaces:

### Clustering

```text
BAAI/bge-small-en-v1.5
384d
MPS
```



### Persistent retrieval

```text
bge-m3
1024d
Ollama
```



That's completely acceptable.

But the DB vector index needs explicit metadata:

```text
embedding_model
embedding_provider
embedding_dimension
embedding_revision
normalization
```

Otherwise changing:

```text
bge-m3 → Qwen embedding
```

can produce a database whose vectors are technically present but semantically incompatible.

---

# 25. Stage 5 verification is directionally strong

The current flow is:

```text
BORP
+
completeness
+
NLI
 ↓
high confidence → pass
marginal → Gemma
low → Gemma
 ↓
fail closed
```



That's substantially better than using embedding similarity as "factual verification."

And the current marginal NLI behavior is correct:

```text
0.5–0.8
→ unknown
→ escalate
```



I would keep this architecture.

---

# 26. But the epistemic naming should change

The verifier is fundamentally asking:

> Does the generated FB agree with the supplied source evidence?

That is **source consistency**, not objective factual truth.

I'd change the status vocabulary toward:

```text
SOURCE_SUPPORTED
SOURCE_INCONSISTENT
SOURCE_UNCERTAIN
```

rather than implying:

```text
FACT_VERIFIED
```

because:

```text
source says X
FB faithfully says X
```

does not mean:

```text
X is objectively true.
```

This becomes critical when Maxwell contains:

* scientific literature;
* philosophy;
* business books;
* historical claims;
* speculative writing;
* normative advice.

---

# 27. BORP is a corroboration heuristic, not truth

The `BORP` requirement for multiple sources is useful.

But:

```text
two books agree
```

does not necessarily mean:

```text
two independent sources
```

They may copy each other.

You have already started addressing this with canonical `source_ids`, which is good. 

Next step:

```text
source_id
edition_id
author
publisher
year
```

and eventually:

```text
independent_source_count
```

rather than simply `source_count`.

---

# 28. Stage 6 persistence is solid—but `INSERT OR REPLACE` is still the wrong long-term primitive

The code explicitly uses:

```sql
INSERT OR REPLACE
```



The file's own documentation calls this:

> upsert.

But SQLite `REPLACE` semantics are delete + insert.

That becomes dangerous once you rely on:

```text
usage_count
feedback
relationships
history
audit metadata
```

because row identity and associated records can be destroyed.

Use:

```sql
INSERT ...
ON CONFLICT(fb_id)
DO UPDATE SET ...
```

instead.

And define explicitly which fields are immutable:

```text
fb_id
created_at
source provenance
```

and which are mutable:

```text
usage_count
feedback_score
last_retrieved_at
```

---

# 29. Provenance is good, but not yet claim-level

Stage 6 stores:

```text
source_clusters
source_books
source_principle_ids
source_text
verification_results
```



That's a strong foundation.

But the actual epistemic unit is still:

```text
FB → source evidence
```

rather than:

```text
FB
 ├── claim A → evidence A/B
 ├── claim B → evidence C
 └── claim C → evidence A
```

That's the next major upgrade I'd make.

Not another vector DB.

Not another RAG framework.

# Claim-level provenance.

---

# 30. There is a major contradiction inside the Constitution itself

The Constitution requires:

```text
C16: no silent errors; except clauses must log and raise
```

and:

```text
C23: resilient; survive component failures
```



But the actual code frequently does:

```python
except Exception:
    pass
```

or:

```python
except Exception:
    return fallback
```

Examples exist in Stage 0, Stage 2, retrieval and other infrastructure. 

The problem isn't necessarily the fallback.

The problem is the lack of an explicit distinction between:

```text
RECOVERABLE
DEGRADED
FATAL
```

## Replace C16 operationally with:

```text
RECOVERABLE
→ structured log + degraded flag + continue

FATAL
→ structured log + raise

UNKNOWN
→ quarantine artifact
```

Then resilience and fail-fast can coexist.

---

# 31. Maxwell needs a formal run-quality contract

This is, in my opinion, the most important system-level addition after fixing Stage 2.

Right now a pipeline can partially degrade and still look successful.

You need:

```json
{
  "run_status": "SUCCESS_WITH_DEGRADATION",
  "embedding_coverage": 0.997,
  "llm_success_rate": 0.991,
  "verification_success_rate": 0.986,
  "fallback_count": 31,
  "quarantined_count": 14,
  "source_coverage": 0.994
}
```

with:

```text
SUCCESS
SUCCESS_WITH_DEGRADATION
FAILED
```

Then the system can enforce:

```text
embedding_coverage < 99%
→ don't publish
```

That's far safer than "the script finished."

---

# 32. Your biggest RAG evaluation gap remains recall

The repository has a golden set and evaluation infrastructure, which is good.

But Maxwell needs to answer:

> **How much knowledge from the source corpus did we lose?**

The pipeline should be evaluated end-to-end:

```text
SOURCE
 ↓
CHUNK
 ↓
PREFILTER
 ↓
CLUSTER
 ↓
PRINCIPLE
 ↓
FB
 ↓
VERIFICATION
 ↓
RETRIEVAL
```

Measure:

```text
segment recall
cluster recall
principle recall
verified-principle recall
retrieval Recall@k
nDCG@k
```

The single most important number:

# Verified Principle Recall@10

For example:

> Of 500 human-labelled principles, how many can be retrieved in the top 10 as a source-supported FB?

That tells you whether Maxwell is actually preserving knowledge.

---

# 33. Do not optimize compression ratio

This is important.

A system that goes:

```text
1,000,000 segments
↓
1,000 FBs
```

is not necessarily better than:

```text
1,000,000 segments
↓
20,000 FBs
```

If the first lost half the knowledge.

Your objective should be:

```text
knowledge preserved
-------------------
retrieval cost
```

not:

```text
compression ratio
```

---

# 34. I would freeze the current semantic architecture

After this audit, I am **more strongly opposed to architectural churn**.

I would not introduce:

* HDBSCAN;
* UMAP;
* ColBERT;
* SPLADE;
* Neo4j;
* LightRAG;
* Cognee;
* LangChain;
* another vector database.

The current stack is adequate:

```text
FAISS
R-NN
Louvain
LLM principle extraction
MinHash
NLI
RRF
SQLite
sqlite-vec
```

The problem is implementation integrity.

---

# 35. My P0 list — exactly what I would fix before another large run

## P0-1 — Fix Stage 2 scope bug

Pass or derive:

```text
source_diversity
is_convergent
```

inside `_build_fb_from_result()`. 

## P0-2 — Fix Stage 2 MinHash scope bug

Replace:

```python
make_minhash(definition)
```

with the FB's actual definition. 

## P0-3 — Make MinHash state transition clean

```text
candidate
→ compare
→ accept
→ insert
```

## P0-4 — Run a true clean-room smoke test

Not:

```text
developer machine
```

but:

```text
fresh environment
+ declared dependencies
+ empty data
+ smoke fixture
```

## P0-5 — Make provider abstraction real

No stage-level direct provider imports.

## P0-6 — Fix governance drift

Especially:

```text
AGENTS.md
CONSTITUTION.md
.env.example
schemas.py
justfile
README/docs
```

---

# 36. P1 — quality improvements

Then:

### P1.1

Move every Stage 2 hardcoded policy value into YAML.

### P1.2

Introduce stage-boundary validation.

### P1.3

Add embedding metadata to vector index.

### P1.4

Add run-quality/degradation metrics.

### P1.5

Build 200–500 manually labelled cluster/principle examples.

### P1.6

Build 100–200 real retrieval queries.

### P1.7

Benchmark:

```text
FTS
vector
metadata
RRF
RRF + reranker
```

---

# 37. P2 — the real Maxwell differentiator

After the above:

```text
source passages
      ↓
claims
      ↓
claim → evidence
      ↓
claim-level NLI
      ↓
source independence
      ↓
typed relationships
      ↓
FB synthesis
```

Then you can answer:

> "Why does Maxwell believe this?"

with an actual evidence graph rather than merely a generated paragraph.

That is where Maxwell becomes genuinely interesting as a knowledge compiler.

---

# My recommended target architecture

I would converge on this:

```text
                    SOURCE
                       │
                       ▼
              parse / normalize
                       │
                       ▼
                     chunk
                       │
                       ▼
                quality prefilter
                       │
                       ▼
              semantic candidates
                       │
                       ▼
            R-NN + Louvain clusters
                       │
                       ▼
             principle discovery
                       │
                ┌──────┴──────┐
                │             │
              1:N             1
                │             │
                ▼             ▼
           split / merge   extract
                │             │
                └──────┬──────┘
                       ▼
                 CLAIM SET
                       │
             claim → evidence
                       │
                       ▼
                FB synthesis
                       │
                       ▼
                classification
                       │
                       ▼
            NLI + cross-family LLM
                       │
                       ▼
              epistemic status
                       │
                       ▼
            SQLite + FTS + vectors
                       │
                       ▼
                 RRF retrieval
                       │
                       ▼
                optional rerank
                       │
                       ▼
                agent context
```

The key change is:

# **Evidence → Claims → FB**

instead of:

# Evidence → FB

---

# Final S-tier judgement

After this deeper audit, I would **not call Maxwell a production-ready RAG system yet**.

But I also would **not redesign it**.

That's an important distinction.

The core ideas are strong:

* cluster before synthesis;
* reciprocal-neighbor clustering;
* source-diversity gating;
* singleton preservation;
* principle discovery;
* MinHash dedup;
* cross-family verification;
* NLI escalation;
* RRF retrieval;
* SQLite/FTS/vector persistence;
* provenance stamping.

Several of those have been implemented thoughtfully. The current clustering implementation, in particular, is much better than a naïve "embedding threshold → connected components" design. 

But the repository has entered the dangerous phase where:

```text
architecture maturity
        >
implementation-contract maturity
```

and that's exactly when subtle bugs become expensive.

The two Stage 2 defects are the clearest example:

```text
local variable
     ↓
cross-function assumption
     ↓
exception swallowed by worker
     ↓
missing knowledge
     ↓
pipeline may still "complete"
```

That is **more dangerous than a hard crash**, because a hard crash tells you the system is broken.

A silent missing-principle pipeline tells you:

> everything worked.

when it didn't.

---

# My pragmatic recommendation

**Stop adding RAG features for one short consolidation cycle.**

Do this in order:

```text
1. Fix Stage 2 P0 bugs
        ↓
2. Clean provider boundaries
        ↓
3. Make dependencies reproducible
        ↓
4. Make config actually authoritative
        ↓
5. Synchronize governance/docs
        ↓
6. Add stage-boundary validation
        ↓
7. Add run-quality contract
        ↓
8. Build gold evaluation set
        ↓
9. Measure Verified Principle Recall@10
        ↓
10. Only then optimize models/thresholds
```

If Maxwell passes that sequence, **then** I would be comfortable calling the architecture production-grade.

Right now my strongest recommendation is:

> **Do not change the semantic architecture. Make the existing architecture trustworthy first.**

That is the highest-ROI engineering move for this repository.
