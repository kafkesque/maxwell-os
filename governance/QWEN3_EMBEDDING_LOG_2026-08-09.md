# Qwen3-Embedding — Download Log & Future Test Plan

## Status (2026-08-09 14:12)
- **Download**: Pulling via `ollama pull qwen3-embedding` — ~69% complete (3.2GB/4.7GB) at 5.3 MB/s
- **PID**: 45751 (background)
- **Log**: `/tmp/qwen3_embed_pull.log`
- **Ollama model name**: `qwen3-embedding:latest`
- **Already in HF cache**: `mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ` (335MB) — MLX version

## Why Test
Current embedder: `bge-m3` (Ollama, 1.2GB, 1024-dim)
Candidate: `qwen3-embedding` (Ollama, 4.7GB, dim TBD)
MLX alternative: `Qwen3-Embedding-0.6B-4bit-DWQ` (335MB, 4-bit quantized)

The OMLX 4-bit version is 14× smaller than the Ollama qwen3-embedding and 3.5× smaller than bge-m3. If quality is comparable, it could replace bge-m3 entirely and keep embedding local (no Ollama dependency).

## Test Plan (to run after download completes)

### 1. Speed Benchmark
```python
# Compare batch-64 encode of 1000 passages
models = {
    "bge-m3": "ollama",           # current, 1.2GB
    "qwen3-embedding": "ollama",  # new, 4.7GB  
    "qwen3-emb-4bit": "mlx",      # OMLX, 335MB
}
```
Measure:
- Wall clock for 1000 embeddings (batch_size=64)
- Tokens/sec
- Memory usage

### 2. Quality Benchmark (Retrieval Precision@5)
- Take 50 clusters from stage1_5 (known ground-truth groupings)
- Embed all passages with each model
- For each cluster's centroid passage, retrieve top-5 nearest neighbors
- Measure: % of retrieved neighbors that belong to the same cluster

### 3. Dimensionality
- bge-m3: 1024-dim
- qwen3-embedding: check output dim (likely 1024 or 2048)
- If dim differs, test with and without PCA reduction to 512 (current FAISS config uses embed_dim: 512)

### 4. Integration Path
If qwen3-embedding (or the 4-bit variant) proves superior:
- Update `config/pipeline_config.yaml`: `embeddings.model`, `embeddings.provider`
- Update `pipeline/stage1_5_embed_cluster.py` embedding call
- Re-index all passages (or verify existing index compatibility)

## Notes
- The Ollama qwen3-embedding (4.7GB) is surprisingly large — likely the full FP16 model
- The MLX 4-bit version (335MB) would be far more Maxwell-appropriate (local, sovereign, fast)
- If the MLX version quality matches ollama, it's the clear winner (C1: $0 marginal cost, C3: sovereign)
