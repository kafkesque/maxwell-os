#!/usr/bin/env python3
"""
Maxwell OS v3.0 — Matryoshka + ModernBERT Comparative Test
==========================================================
Tests:
  1. bge-m3 1024-dim vs 512-dim Matryoshka truncation quality
  2. DeBERTa-v3 vs ModernBERT-base NLI accuracy + speed

Compares clustering preservation (cosine similarity rank correlation) 
and NLI agreement (% of same label, speed).

Author: 2026-07-27
Schema: v1.0 | temp=0.0
"""

import json
import math
import time
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# ═══════════════════════════════════
# CONFIG — C12: no hardcoded values
# ═══════════════════════════════════
OLLAMA_URL = "http://localhost:11434/api/embeddings"
NLI_PAIRS_COUNT = 30  # number of claim-evidence pairs to test
TOP_K_OVERLAP = 10     # for clustering quality: top-K neighbor overlap

# ── Test prompts for embeddings ──
TEST_SEGMENTS: List[str] = [
    # Principles (from financial/business domain)
    "Compounding is the process where reinvested returns generate exponential growth over time. The longer the time horizon, the more dramatic the effect.",
    "Diversification reduces portfolio risk by spreading investments across uncorrelated assets. The key is finding assets that don't move in lockstep.",
    "Margin of safety is the principle of buying assets at a significant discount to intrinsic value. This provides a buffer against errors in analysis.",
    "Market efficiency theory suggests that asset prices reflect all available information. However, behavioral finance challenges this assumption.",
    "Incentives drive behavior. Understanding the incentive structure of any system is key to predicting outcomes.",
    "Circle of competence means investing within areas you understand deeply. Operating outside it leads to mistakes.",
    "Mr. Market is a metaphor for market volatility. The market offers prices daily - you decide whether to act.",
    "Moats are sustainable competitive advantages that protect a business from competition. Wide moats enable long-term profitability.",
    "Mean reversion is the tendency of asset prices to return to their long-term average. Extreme moves tend to be followed by opposite moves.",
    "Optionality is the value of having choices. Real options in business and investing can be worth more than their apparent cost.",
    # Different domain to test cross-domain clustering
    "Deliberate practice involves focused, structured effort on specific skills with immediate feedback. It's the key to expertise development.",
    "Sleep is essential for memory consolidation. During deep sleep, the brain replays and strengthens neural pathways formed during learning.",
    "First principles thinking breaks complex problems down to their fundamental truths and rebuilds from there. It avoids reasoning by analogy.",
    "The Pareto principle states that roughly 80% of effects come from 20% of causes. Identifying the vital few is key to leverage.",
    "Inversion is the practice of approaching problems backward. Instead of asking how to succeed, ask what would guarantee failure - then avoid it.",
]

# ── NLI claim-evidence pairs ──
NLI_TEST_PAIRS: List[Dict[str, Any]] = [
    # ENTAILMENT pairs
    {"claim": "Compounding generates exponential growth through reinvested returns", 
     "evidence": "Compounding is the process where reinvested returns generate exponential growth over time.", 
     "expected": "ENTAILMENT"},
    {"claim": "Diversification works by holding uncorrelated assets", 
     "evidence": "Diversification reduces portfolio risk by spreading investments across uncorrelated assets.", 
     "expected": "ENTAILMENT"},
    {"claim": "Investors should only operate within their circle of competence", 
     "evidence": "Circle of competence means investing within areas you understand deeply. Operating outside it leads to mistakes.", 
     "expected": "ENTAILMENT"},
    {"claim": "Economic moats enable long-term profitability through competitive advantages", 
     "evidence": "Moats are sustainable competitive advantages that protect a business from competition. Wide moats enable long-term profitability.", 
     "expected": "ENTAILMENT"},
    {"claim": "Margin of safety protects against valuation errors", 
     "evidence": "Margin of safety is the principle of buying assets at a significant discount to intrinsic value providing a buffer against errors.", 
     "expected": "ENTAILMENT"},
    {"claim": "First principles thinking rebuilds understanding from fundamental truths", 
     "evidence": "First principles thinking breaks complex problems down to their fundamental truths and rebuilds from there. It avoids reasoning by analogy.", 
     "expected": "ENTAILMENT"},
    {"claim": "The Pareto principle identifies a minority of causes behind majority of effects", 
     "evidence": "The Pareto principle states that roughly 80% of effects come from 20% of causes.", 
     "expected": "ENTAILMENT"},
    {"claim": "Deliberate practice requires focused structured effort with feedback", 
     "evidence": "Deliberate practice involves focused, structured effort on specific skills with immediate feedback. It's the key to expertise development.", 
     "expected": "ENTAILMENT"},
    {"claim": "Sleep consolidates memories through neural replay during deep sleep", 
     "evidence": "Sleep is essential for memory consolidation. During deep sleep, the brain replays and strengthens neural pathways formed during learning.", 
     "expected": "ENTAILMENT"},
    {"claim": "Inversion approaches problems backward by asking what would cause failure", 
     "evidence": "Inversion is the practice of approaching problems backward. Instead of asking how to succeed, ask what would guarantee failure - then avoid it.", 
     "expected": "ENTAILMENT"},
    
    # CONTRADICTION pairs
    {"claim": "Compounding only works for short time horizons", 
     "evidence": "The longer the time horizon, the more dramatic the compounding effect.", 
     "expected": "CONTRADICTION"},
    {"claim": "Diversification is most effective when assets are highly correlated", 
     "evidence": "Diversification reduces portfolio risk by spreading investments across uncorrelated assets.", 
     "expected": "CONTRADICTION"},
    {"claim": "Market prices are always perfectly rational and efficient", 
     "evidence": "Behavioral finance challenges the assumption that asset prices reflect all available information.", 
     "expected": "CONTRADICTION"},
    {"claim": "Investors should actively trade outside their circle of competence to learn", 
     "evidence": "Circle of competence means investing within areas you understand deeply. Operating outside it leads to mistakes.", 
     "expected": "CONTRADICTION"},
    {"claim": "Competitive advantages have no impact on business profitability", 
     "evidence": "Moats are sustainable competitive advantages that protect a business from competition enabling long-term profitability.", 
     "expected": "CONTRADICTION"},
    {"claim": "Mean reversion means extreme price moves tend to continue indefinitely", 
     "evidence": "Mean reversion is the tendency of asset prices to return to their long-term average. Extreme moves tend to be followed by opposite moves.", 
     "expected": "CONTRADICTION"},
    {"claim": "First principles thinking relies on reasoning by analogy", 
     "evidence": "First principles thinking avoids reasoning by analogy and breaks problems to fundamental truths.", 
     "expected": "CONTRADICTION"},
    {"claim": "Deliberate practice primarily involves passive repetition without feedback", 
     "evidence": "Deliberate practice involves focused, structured effort on specific skills with immediate feedback.", 
     "expected": "CONTRADICTION"},
    
    # NEUTRAL pairs (related but not entailed/contradicted)
    {"claim": "Compounding is the eighth wonder of the world according to Einstein", 
     "evidence": "Compounding is the process where reinvested returns generate exponential growth over time.", 
     "expected": "NEUTRAL"},
    {"claim": "Warren Buffett popularized the Mr. Market metaphor in his annual letters", 
     "evidence": "Mr. Market is a metaphor for market volatility where the market offers prices daily.", 
     "expected": "NEUTRAL"},
    {"claim": "Diversification was first mathematically formalized by Markowitz in 1952", 
     "evidence": "Diversification reduces portfolio risk by spreading investments across uncorrelated assets.", 
     "expected": "NEUTRAL"},
    {"claim": "The Pareto principle was discovered by Vilfredo Pareto observing Italian land ownership", 
     "evidence": "The Pareto principle states that roughly 80% of effects come from 20% of causes.", 
     "expected": "NEUTRAL"},
]


# ═══════════════════════════════════
# TEST 1: MATRYOSHKA EMBEDDINGS
# ═══════════════════════════════════

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_bge_embedding(text: str, dims: int = 1024) -> List[float]:
    """Get bge-m3 embedding from Ollama, optionally truncated."""
    import urllib.request
    data = json.dumps({"model": "bge-m3", "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=data, 
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    embedding = result["embedding"]
    if dims < len(embedding):
        # Matryoshka truncation: keep first N dimensions
        # Normalize after truncation for fair comparison
        norm = math.sqrt(sum(x * x for x in embedding[:dims]))
        if norm > 0:
            embedding = [x / norm for x in embedding[:dims]]
        else:
            embedding = embedding[:dims]
    return embedding


def test_matryoshka_quality() -> Dict[str, Any]:
    """Compare 1024-dim vs 512-dim clustering quality on test segments."""
    print("\n" + "=" * 70)
    print("  TEST 1: Matryoshka Embedding Quality (1024-dim vs 512-dim)")
    print("=" * 70)
    
    # Get embeddings at both dimensions
    embeddings_1024: List[List[float]] = []
    embeddings_512: List[List[float]] = []
    times_1024: List[float] = []
    times_512: List[float] = []
    
    for i, segment in enumerate(TEST_SEGMENTS):
        # 1024-dim (full, from Ollama)
        t0 = time.time()
        emb_1024 = get_bge_embedding(segment, dims=1024)
        t_1024 = time.time() - t0
        embeddings_1024.append(emb_1024)
        times_1024.append(t_1024)
        
        # 512-dim (Matryoshka truncation from same 1024-dim)
        emb_512 = emb_1024[:512]
        # Re-normalize
        norm = math.sqrt(sum(x * x for x in emb_512))
        if norm > 0:
            emb_512 = [x / norm for x in emb_512]
        embeddings_512.append(emb_512)
        
        print(f"  Segment {i+1:2}: 1024-dim={t_1024:.3f}s")
    
    # Compute neighbor overlap
    n = len(TEST_SEGMENTS)
    overlap_scores: List[float] = []
    rank_correlations: List[float] = []
    
    for i in range(n):
        # Get top-K neighbors in 1024-dim space
        sims_1024 = [(j, cosine_similarity(embeddings_1024[i], embeddings_1024[j]))
                     for j in range(n) if j != i]
        sims_1024.sort(key=lambda x: -x[1])
        top_k_1024 = {j for j, _ in sims_1024[:TOP_K_OVERLAP]}
        
        # Get top-K neighbors in 512-dim space
        sims_512 = [(j, cosine_similarity(embeddings_512[i], embeddings_512[j]))
                    for j in range(n) if j != i]
        sims_512.sort(key=lambda x: -x[1])
        top_k_512 = {j for j, _ in sims_512[:TOP_K_OVERLAP]}
        
        # Overlap
        overlap = len(top_k_1024 & top_k_512) / TOP_K_OVERLAP
        overlap_scores.append(overlap)
        
        # Rank correlation (Spearman's footrule on neighbor ordering)
        rank_1024 = {j: r for r, (j, _) in enumerate(sims_1024)}
        rank_512 = {j: r for r, (j, _) in enumerate(sims_512)}
        rank_diff = sum(abs(rank_1024.get(j, n) - rank_512.get(j, n)) 
                       for j in range(n) if j != i)
        max_diff = n * (n - 1)  # worst case
        rank_corr = 1.0 - (rank_diff / max_diff) if max_diff > 0 else 1.0
        rank_correlations.append(rank_corr)
    
    avg_overlap = sum(overlap_scores) / len(overlap_scores)
    avg_rank_corr = sum(rank_correlations) / len(rank_correlations)
    avg_time_1024 = sum(times_1024) / len(times_1024)
    
    print(f"\n  Results (n={n} segments, top-K={TOP_K_OVERLAP}):")
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │ Avg neighbor overlap:     {avg_overlap:.1%}             │")
    print(f"  │ Avg rank preservation:    {avg_rank_corr:.1%}             │")
    print(f"  │ Avg embedding time:       {avg_time_1024:.3f}s (same for both) │")
    print(f"  │ 512-dim speedup (search): ~2× (half the multiply-adds) │")
    print(f"  └─────────────────────────────────────────────┘")
    
    # Quality classification
    if avg_overlap >= 0.90:
        quality = "EXCELLENT — 512-dim preserves clustering structure"
    elif avg_overlap >= 0.75:
        quality = "GOOD — minor degradation, acceptable tradeoff"
    elif avg_overlap >= 0.60:
        quality = "FAIR — noticeable degradation, test on real pipeline data"
    else:
        quality = "POOR — significant information loss, do not use"
    
    print(f"  Verdict: {quality}")
    
    return {
        "avg_overlap": avg_overlap,
        "avg_rank_corr": avg_rank_corr,
        "avg_time": avg_time_1024,
        "quality": quality,
    }


# ═══════════════════════════════════
# TEST 2: MODERNBERT vs DEBERTA NLI
# ═══════════════════════════════════

def load_nli_models():
    """Load both DeBERTa and ModernBERT NLI models."""
    from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
    
    print("\n" + "=" * 70)
    print("  TEST 2: ModernBERT-base-nli vs DeBERTa-v3 NLI Comparison")
    print("=" * 70)
    
    models = {}
    
    # DeBERTa-v3 (current)
    print("\n  Loading DeBERTa-v3-base-mnli-fever-anli...")
    t0 = time.time()
    try:
        deberta = pipeline(
            "zero-shot-classification",
            model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
            device=-1,  # CPU
        )
        models["deberta"] = deberta
        print(f"  ✅ DeBERTa loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"  ❌ DeBERTa load failed: {e}")
        models["deberta"] = None
    
    # ModernBERT-base-nli
    print("\n  Loading ModernBERT-base-nli (tasksource)...")
    t0 = time.time()
    try:
        modernbert = pipeline(
            "zero-shot-classification",
            model="tasksource/ModernBERT-base-nli",
            device=-1,  # CPU
        )
        models["modernbert"] = modernbert
        print(f"  ✅ ModernBERT loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"  ❌ ModernBERT load failed: {e}")
        models["modernbert"] = None
    
    return models


def run_nli_comparison(models: dict) -> Dict[str, Any]:
    """Compare DeBERTa and ModernBERT on NLI pairs."""
    results = []
    deberta_times: List[float] = []
    modernbert_times: List[float] = []
    agreements = 0
    deberta_correct = 0
    modernbert_correct = 0
    total = len(NLI_TEST_PAIRS)
    
    for i, pair in enumerate(NLI_TEST_PAIRS):
        claim = pair["claim"]
        evidence = pair["evidence"]
        expected = pair["expected"]
        
        result_row = {"pair": i+1, "claim": claim[:60], "expected": expected}
        
        # DeBERTa
        if models.get("deberta"):
            t0 = time.time()
            try:
                d_out = models["deberta"](
                    claim, candidate_labels=[evidence],
                    hypothesis_template="This text: {}"
                )
                d_label = "ENTAILMENT" if d_out["scores"][0] > 0.5 else "NOT_ENTAILMENT"
                d_score = d_out["scores"][0]
                d_time = time.time() - t0
                deberta_times.append(d_time)
                result_row["deberta_label"] = d_label
                result_row["deberta_score"] = d_score
                result_row["deberta_time"] = d_time
                if d_label == "ENTAILMENT" and expected == "ENTAILMENT":
                    deberta_correct += 1
                elif d_label == "NOT_ENTAILMENT" and expected != "ENTAILMENT":
                    deberta_correct += 1
            except Exception as e:
                result_row["deberta_error"] = str(e)
        
        # ModernBERT
        if models.get("modernbert"):
            t0 = time.time()
            try:
                m_out = models["modernbert"](
                    claim, candidate_labels=[evidence],
                    hypothesis_template="This text: {}"
                )
                m_label = "ENTAILMENT" if m_out["scores"][0] > 0.5 else "NOT_ENTAILMENT"
                m_score = m_out["scores"][0]
                m_time = time.time() - t0
                modernbert_times.append(m_time)
                result_row["modernbert_label"] = m_label
                result_row["modernbert_score"] = m_score
                result_row["modernbert_time"] = m_time
                if m_label == "ENTAILMENT" and expected == "ENTAILMENT":
                    modernbert_correct += 1
                elif m_label == "NOT_ENTAILMENT" and expected != "ENTAILMENT":
                    modernbert_correct += 1
            except Exception as e:
                result_row["modernbert_error"] = str(e)
        
        # Agreement check
        if "deberta_label" in result_row and "modernbert_label" in result_row:
            if result_row["deberta_label"] == result_row["modernbert_label"]:
                agreements += 1
        
        status = "✅" if result_row.get("deberta_label") == expected else "❌"
        print(f"  {status} Pair {i+1:2}: D={result_row.get('deberta_label','?')} "
              f"M={result_row.get('modernbert_label','?')} | "
              f"expected={expected}")
        
        results.append(result_row)
    
    # Summary
    print(f"\n  ┌──────────────────────────────────────────────┐")
    
    avg_d_time = sum(deberta_times)/len(deberta_times) if deberta_times else 0
    avg_m_time = sum(modernbert_times)/len(modernbert_times) if modernbert_times else 0
    
    print(f"  │ DeBERTa accuracy:   {deberta_correct}/{total} ({deberta_correct/total:.0%})        │")
    print(f"  │ ModernBERT accuracy:{modernbert_correct}/{total} ({modernbert_correct/total:.0%})        │")
    print(f"  │ Inter-model agreement: {agreements}/{total} ({agreements/total:.0%})     │")
    print(f"  │ DeBERTa avg time:   {avg_d_time:.4f}s              │")
    print(f"  │ ModernBERT avg time: {avg_m_time:.4f}s              │")
    
    speedup = avg_d_time / avg_m_time if avg_m_time > 0 else 0
    print(f"  │ ModernBERT speedup: {speedup:.1f}×                  │")
    print(f"  └──────────────────────────────────────────────┘")
    
    # Assessment
    if modernbert_correct >= deberta_correct and speedup >= 1.0:
        verdict = "✅ ModernBERT IS BETTER — higher or equal accuracy, faster"
    elif modernbert_correct >= deberta_correct - 1 and speedup >= 1.2:
        verdict = "⚠️ ModernBERT VIABLE — slight accuracy tradeoff for speed"
    elif speedup < 0.8:
        verdict = "❌ ModernBERT SLOWER — no benefit"
    else:
        verdict = "⚠️ INCONCLUSIVE — needs more test pairs"
    
    print(f"  Verdict: {verdict}")
    
    return {
        "deberta_accuracy": deberta_correct / total,
        "modernbert_accuracy": modernbert_correct / total,
        "agreement": agreements / total,
        "deberta_avg_time": avg_d_time,
        "modernbert_avg_time": avg_m_time,
        "speedup": speedup,
        "verdict": verdict,
        "details": results,
    }


# ═══════════════════════════════════
# MAIN
# ═══════════════════════════════════

def main():
    print("=" * 70)
    print("  Maxwell OS — Matryoshka + ModernBERT Comparative Test")
    print("  Date: 2026-07-27 | Hardware: M1 Max 64GB")
    print("  C12: all values from config | temp=0.0")
    print("=" * 70)
    
    # Test 1: Matryoshka
    try:
        matryoshka_result = test_matryoshka_quality()
    except Exception as e:
        print(f"\n  ❌ Matryoshka test failed: {e}")
        matryoshka_result = {"error": str(e)}
    
    # Test 2: ModernBERT vs DeBERTa NLI
    try:
        models = load_nli_models()
        if models.get("deberta") or models.get("modernbert"):
            nli_result = run_nli_comparison(models)
        else:
            print("\n  ❌ No NLI models available to compare")
            nli_result = {"error": "no models loaded"}
    except Exception as e:
        print(f"\n  ❌ NLI test failed: {e}")
        import traceback
        traceback.print_exc()
        nli_result = {"error": str(e)}
    
    # Final summary
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    
    if "avg_overlap" in matryoshka_result:
        print(f"  Matryoshka 512-dim: {matryoshka_result['avg_overlap']:.1%} neighbor overlap")
        print(f"  Status: {matryoshka_result.get('quality', 'unknown')}")
    
    if "verdict" in nli_result:
        print(f"  ModernBERT vs DeBERTa: {nli_result['verdict']}")
        print(f"  DeBERTa: {nli_result['deberta_accuracy']:.0%} acc @ {nli_result['deberta_avg_time']:.4f}s")
        print(f"  ModernBERT: {nli_result['modernbert_accuracy']:.0%} acc @ {nli_result['modernbert_avg_time']:.4f}s")
    
    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "hardware": "M1 Max 64GB",
        "matryoshka": matryoshka_result,
        "nli": nli_result,
    }
    
    out_path = Path("temp/test_matryoshka_nli_results.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
