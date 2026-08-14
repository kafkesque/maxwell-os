#!/usr/bin/env bash
# qwen38_curl_download.sh — pull Qwen3.8-27B-MLX-4bit via curl (resume, sequential)
set -uo pipefail

REPO="lmstudio-community/Qwen3.8-27B-MLX-4bit"
BASE="https://huggingface.co/$REPO/resolve/main"
DEST="$HOME/.omlx/models/Qwen3.8-27B-MLX-4bit"
LOG="/tmp/qwen38_curl_download.log"

mkdir -p "$DEST"
cd "$DEST"

SHARDS=(
  model-00001-of-00003.safetensors
  model-00002-of-00003.safetensors
  model-00003-of-00003.safetensors
)

SMALL=(
  config.json generation_config.json tokenizer.json tokenizer_config.json
  vocab.json chat_template.jinja preprocessor_config.json processor_config.json
  video_preprocessor_config.json model.safetensors.index.json README.md .gitattributes
)

{
  echo "=== Qwen3.8 curl download start $(date) ==="
  echo "dest: $DEST"

  # 1. small files
  for f in "${SMALL[@]}"; do
    [ -s "$f" ] && continue
    curl -sS -L --fail -o "$f" "$BASE/$f" && echo "  ✅ $f" || echo "  ⚠️ $f (rc=$?)"
  done

  # 2. shards, sequential, resume
  for f in "${SHARDS[@]}"; do
    echo "  ⬇️  $f $(date)"
    curl -L --fail -C - -o "$f" "$BASE/$f"
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "  ❌ $f FAILED rc=$rc $(date)"
      exit $rc
    fi
    echo "  ✅ $f done $(date)  ($(du -h "$f" | cut -f1))"
  done

  echo "=== Qwen3.8 curl download COMPLETE $(date) ==="
} >>"$LOG" 2>&1
