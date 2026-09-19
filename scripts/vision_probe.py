#!/usr/bin/env python3
"""vision_probe.py — RETIRED 2026-09-16 by user ruling. This entry point is a NO-OP.

The vision/OCR gap was an open question: Qwen3.8-27B-MLX-4bit, Ornith-1.5-35B-A3B-REAP-19B
and gemma-4-E4B-it-MLX-4bit all declare vision_config and ship preprocessor_config.json, and
oMLX reports engine_type=vlm for them, so they may be able to transcribe images — which would
matter for ingesting image-heavy sources.

The user ruled (2026-09-16) that the vision probe is NOT needed for the current model-stack
consolidation. Keeping this as a no-op means scripts/run_final_chain.sh step 7 exits instantly
instead of spending oMLX time on a test we do not act on. The implementation is preserved at
archive/vision_probe.py and can be restored if a vision role is ever added to the pipeline.
"""
from __future__ import annotations

import sys


def main() -> int:
    """Print the retirement notice and exit without touching oMLX."""
    print("vision_probe: SKIPPED — retired 2026-09-16 by user ruling "
          "(implementation preserved at archive/vision_probe.py)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
