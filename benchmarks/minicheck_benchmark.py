#!/usr/bin/env python3
"""Benchmark Ollama MiniCheck vs MLX MiniCheck: speed + factuality."""

import json, time, requests, statistics

# ── Test cases: (document, claim, expected: YES/NO) ──
TEST_CASES = [
    # Factual support
    ("The sky appears blue due to Rayleigh scattering.", "The sky appears blue.", "YES"),
    ("Water freezes at 0 degrees Celsius.", "Water freezes at 0 degrees Celsius.", "YES"),
    ("Exercise improves cardiovascular health.", "Exercise is good for heart health.", "YES"),
    ("The Earth orbits the Sun once every 365 days.", "The Earth orbits the Sun.", "YES"),
    ("Humans need oxygen to survive.", "Humans require oxygen.", "YES"),
    ("Photosynthesis converts sunlight into chemical energy.", "Photosynthesis uses sunlight.", "YES"),
    ("The human heart pumps blood through the body.", "The heart circulates blood.", "YES"),
    ("DNA contains genetic information.", "DNA carries genetic code.", "YES"),
    ("Gravity pulls objects toward Earth.", "Objects fall due to gravity.", "YES"),
    ("The brain controls voluntary and involuntary actions.", "The brain controls the body.", "YES"),
    # Contradictions
    ("The sky appears blue due to Rayleigh scattering.", "The sky is green.", "NO"),
    ("Water freezes at 0 degrees Celsius.", "Water freezes at 100 degrees.", "NO"),
    ("Exercise improves cardiovascular health.", "Exercise damages the heart.", "NO"),
    ("The Earth orbits the Sun once every 365 days.", "The Earth is flat.", "NO"),
    ("Humans need oxygen to survive.", "Humans can breathe underwater.", "NO"),
    ("Photosynthesis converts sunlight into chemical energy.", "Plants eat soil for energy.", "NO"),
    ("The human heart pumps blood through the body.", "The heart produces thoughts.", "NO"),
    ("DNA contains genetic information.", "DNA is found in plants only.", "NO"),
    ("Gravity pulls objects toward Earth.", "Objects float away from Earth.", "NO"),
    ("The brain controls voluntary and involuntary actions.", "The brain is not involved in breathing.", "NO"),
    # Subtle / nuanced
    ("A diet rich in fruits and vegetables may reduce the risk of chronic disease.", "Eating fruits prevents all disease.", "NO"),
    ("Moderate coffee consumption has been linked to lower risk of depression.", "Drinking coffee cures depression.", "NO"),
    ("Regular exercise can help maintain a healthy weight.", "Exercise guarantees weight loss.", "NO"),
    ("Some studies suggest vitamin D may boost immune function.", "Vitamin D definitely boosts immunity.", "NO"),
    ("The company reported a 15% increase in quarterly revenue.", "The company's revenue decreased.", "NO"),
]

def test_ollama_minicheck(doc: str, claim: str) -> tuple[float, str | None]:
    """Test via Ollama's bespoke-minicheck. Returns (time_ms, response_text)."""
    prompt = f"Document: {doc}\nClaim: {claim}\nIs the claim supported by the document? Answer only YES or NO."
    t0 = time.time()
    try:
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": "bespoke-minicheck:latest",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 10}
        }, timeout=30)
        resp = r.json().get("response", "").strip().upper()
        t = (time.time() - t0) * 1000
        return t, "YES" if "YES" in resp else ("NO" if "NO" in resp else resp)
    except Exception as e:
        return (time.time() - t0) * 1000, f"ERROR: {e}"


def test_mlx_minicheck(doc: str, claim: str) -> tuple[float, str | None]:
    """Test via OMLX (MLX format). Returns (time_ms, response_text)."""
    prompt = f"Document: {doc}\nClaim: {claim}\nIs the claim supported by the document? Answer only YES or NO."
    t0 = time.time()
    try:
        r = requests.post("http://127.0.0.1:11435/v1/chat/completions", json={
            "model": "Bespoke-MiniCheck-7B-mlx",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 10,
            "temperature": 0.0
        }, timeout=60)
        content = r.json()["choices"][0]["message"]["content"].strip().upper()
        t = (time.time() - t0) * 1000
        return t, "YES" if "YES" in content else ("NO" if "NO" in content else content)
    except Exception as e:
        return (time.time() - t0) * 1000, f"ERROR: {e}"


def run_benchmark(name, test_fn):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    times = []
    correct = 0
    total = len(TEST_CASES)

    for i, (doc, claim, expected) in enumerate(TEST_CASES, 1):
        t, response = test_fn(doc, claim)
        times.append(t)

        is_correct = response == expected
        if is_correct:
            correct += 1

        status = "✅" if is_correct else "❌"
        print(f"  {status} [{i:2d}/{total}] {t:7.0f}ms  expected={expected} got={response}")

    acc = correct / total * 100
    avg_t = statistics.mean(times)
    med_t = statistics.median(times)
    p95 = sorted(times)[int(len(times) * 0.95)]

    print(f"\n  {'─'*50}")
    print(f"  Results: {correct}/{total} correct ({acc:.1f}%)")
    print(f"  Speed:   avg={avg_t:.0f}ms  median={med_t:.0f}ms  p95={p95:.0f}ms")
    return {"accuracy": acc, "avg_ms": avg_t, "median_ms": med_t, "p95_ms": p95}


# ── Verify both models are live ──
print("Checking model availability...")
try:
    ollama_ok = requests.get("http://localhost:11434/api/tags", timeout=5).status_code == 200
    print(f"  Ollama:  {'✅' if ollama_ok else '❌'} bespoke-minicheck")
except:
    ollama_ok = False
    print(f"  Ollama:  ❌ not reachable")

try:
    mlx_ok = any("MiniCheck" in m["id"] for m in requests.get("http://127.0.0.1:11435/v1/models", timeout=5).json().get("data", []))
    print(f"  OMLX:    {'✅' if mlx_ok else '❌'} Bespoke-MiniCheck-7B-mlx")
except:
    mlx_ok = False
    print(f"  OMLX:    ❌ not reachable")

if not (ollama_ok and mlx_ok):
    print("\n❌ Both models need to be running. Exiting.")
    exit(1)

# Warm up
print("\nWarming up both models...")
test_ollama_minicheck("Warm up.", "This is a warm up.")
test_mlx_minicheck("Warm up.", "This is a warm up.")
print("Ready.")

ollama_results = run_benchmark("OLLAMA bespoke-minicheck (GGUF Q4_K_M)", test_ollama_minicheck)
mlx_results = run_benchmark("MLX Bespoke-MiniCheck-7B-mlx (4-bit)", test_mlx_minicheck)

print(f"\n{'='*60}")
print(f"  BENCHMARK SUMMARY")
print(f"{'='*60}")
print(f"  {'':25s} {'Ollama GGUF':>15s} {'MLX 4-bit':>15s}")
print(f"  {'─'*25} {'─'*15} {'─'*15}")
print(f"  {'Accuracy':25s} {ollama_results['accuracy']:>14.1f}% {mlx_results['accuracy']:>14.1f}%")
print(f"  {'Avg time':25s} {ollama_results['avg_ms']:>14.0f}ms {mlx_results['avg_ms']:>14.0f}ms")
print(f"  {'Median time':25s} {ollama_results['median_ms']:>14.0f}ms {mlx_results['median_ms']:>14.0f}ms")
print(f"  {'P95 time':25s} {ollama_results['p95_ms']:>14.0f}ms {mlx_results['p95_ms']:>14.0f}ms")
print()
if ollama_results['accuracy'] == mlx_results['accuracy']:
    print("  Factuality: IDENTICAL")
elif ollama_results['accuracy'] > mlx_results['accuracy']:
    print(f"  Factuality: Ollama {ollama_results['accuracy']-mlx_results['accuracy']:.1f}% better")
else:
    print(f"  Factuality: MLX {mlx_results['accuracy']-ollama_results['accuracy']:.1f}% better")

speedup = ollama_results['avg_ms'] / mlx_results['avg_ms']
if speedup > 1:
    print(f"  Speed: MLX is {speedup:.1f}x faster")
else:
    print(f"  Speed: Ollama is {1/speedup:.1f}x faster")
