#!/usr/bin/env python3
"""BUG-623 dependency smoke test — S5 NLI + S1.5 embedding under the ACTIVE transformers/ST versions.

Deterministic known-answer smoke (no LLM, no OMLX). Proves the two quality-critical ML legs
(S5 DeBERTa-v3 NLI + S1.5 bge-m3 embedding) still load and discriminate correctly under the
current installed transformers / sentence-transformers versions, and reports the
requests/urllib3/charset_normalizer mismatch tell.

Exit codes:
  0 = all legs GREEN
  1 = a leg FAILED (fail-closed: a silent 5.x regression would be invisible without this)
  2 = a leg could not be loaded (import/model path error)
"""
from __future__ import annotations

import sys
import warnings

CPU = "cpu"
NLI_MODEL = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
EMBED_MODEL = "BAAI/bge-m3"

# Known-answer NLI pairs (premise, hypothesis, expected_relation)
NLI_CASES = [
    ("A cat is sitting on the mat.", "There is an animal on the mat.", "entailment"),
    ("A cat is sitting on the mat.", "A dog is sitting on the mat.", "contradiction"),
]

# Known-answer embedding triples (anchor, similar, dissimilar)
EMBED_CASES = [
    ("the cat sat on the mat", "a kitten sits on a rug", "the car drove down the highway"),
]


def _report_versions() -> None:
    import requests  # noqa: F401
    import urllib3  # noqa: F401

    import sentence_transformers
    import transformers

    print(f"[versions] transformers={transformers.__version__} "
          f"sentence_transformers={sentence_transformers.__version__}")
    print(f"[versions] requests={__import__('requests').__version__} "
          f"urllib3={__import__('urllib3').__version__}")


def _probe_requests_mismatch() -> str:
    """Capture the loud (not silent) RequestsDependencyWarning tell, if any."""
    import io
    import warnings as _w

    buf = io.StringIO()
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        import requests  # noqa: F401
    for w in caught:
        if "urllib3" in str(w.message) or "charset_normalizer" in str(w.message) \
                or "chardet" in str(w.message):
            buf.write(str(w.message))
    return buf.getvalue().strip() or "(none)"


def smoke_nli() -> bool:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(NLI_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL)
    model.eval()
    id2label = model.config.id2label  # {0: 'entailment', 1: 'neutral', 2: 'contradiction'}

    def _score(premise: str, hypothesis: str) -> dict:
        enc = tok(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**enc).logits[0]
        probs = torch.softmax(logits, dim=-1).tolist()
        return {id2label[i]: p for i, p in enumerate(probs)}

    for premise, hypothesis, expected in NLI_CASES:
        p = _score(premise, hypothesis)
        ent = p.get("entailment", 0.0)
        contra = p.get("contradiction", 0.0)
        print(f"[nli] {expected!r}: entail={ent:.3f} contra={contra:.3f}")
        if expected == "entailment" and not ent > contra:
            print("  FAIL: expected entailment to dominate contradiction")
            return False
        if expected == "contradiction" and not contra > ent:
            print("  FAIL: expected contradiction to dominate entailment")
            return False
    return True


def smoke_embed() -> bool:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL, device=CPU)
    anchor, similar, dissimilar = EMBED_CASES[0]
    emb = model.encode([anchor, similar, dissimilar], normalize_embeddings=True)
    sim = float(emb[0] @ emb[1])
    dis = float(emb[0] @ emb[2])
    print(f"[embed] sim(similar)={sim:.4f} sim(dissimilar)={dis:.4f}")
    return sim > dis


def main() -> int:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _report_versions()
    print(f"[requests-mismatch] {_probe_requests_mismatch()}")

    # Embedding leg first (lighter), then NLI.
    print("[embed] loading bge-m3 ...")
    embed_ok = smoke_embed()
    if not embed_ok:
        print("FAIL-CLOSED: bge-m3 embedding leg failed to discriminate")
        return 1

    print("[nli] loading DeBERTa-v3-large ...")
    nli_ok = smoke_nli()
    if not nli_ok:
        print("FAIL-CLOSED: DeBERTa-v3 NLI leg failed to discriminate")
        return 1

    print("GREEN: S5 NLI + S1.5 embedding legs load and discriminate under the active versions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
