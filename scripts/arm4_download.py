#!/usr/bin/env python3
"""ARM-4 model downloads via huggingface_hub (avoids CLI shim ambiguity)."""
from huggingface_hub import snapshot_download

MODELS = [
    "mlx-community/Ornith-1.5-9B-OptiQ-4bit",
    "mlx-community/gemma-4-12B-it-qat-OptiQ-4bit",
    "mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B",
]

for m in MODELS:
    print(f"=== downloading {m} ===", flush=True)
    try:
        p = snapshot_download(m)
        print(f"=== done {m} -> {p}", flush=True)
    except Exception as e:
        print(f"=== FAIL {m}: {e}", flush=True)
print("ALL DOWNLOADS COMPLETE", flush=True)
