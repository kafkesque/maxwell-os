#!/usr/bin/env python3
"""Benchmark Ollama MiniCheck vs Phi-4-mini for NLI factuality."""

import json, time, requests, statistics

TEST_CASES = [
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
    ("A diet rich in fruits and vegetables may reduce the risk of chronic disease.", "Eating fruits prevents all disease.", "NO"),
    ("Moderate coffee consumption has been linked to lower risk of depression.", "Drinking coffee cures depression.", "NO"),
    ("Regular exercise can help maintain a healthy weight.", "Exercise guarantees weight loss.", "NO"),
    ("Some studies suggest vitamin D may boost immune function.", "Vitamin D definitely boosts immunity.", "NO"),
    ("The company reported a 15% increase in quarterly revenue.", "The company's revenue decreased.", "NO"),
]

def test_ollama(doc, claim):
    p = f"Document: {doc}\nClaim: {claim}\nIs the claim supported? Answer only YES or NO."
    t0 = time.time()
    try:
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": "bespoke-minicheck:latest", "prompt": p, "stream": False,
            "options": {"temperature": 0.0, "num_predict": 10}
        }, timeout=30)
        resp = r.json().get("response", "").strip().upper()
        return (time.time()-t0)*1000, "YES" if "YES" in resp else ("NO" if "NO" in resp else resp)
    except Exception as e:
        return (time.time()-t0)*1000, f"ERR"

def test_phi(doc, claim):
    p = f"Document: {doc}\nClaim: {claim}\nIs the claim supported? Answer only YES or NO."
    t0 = time.time()
    try:
        r = requests.post("http://127.0.0.1:11435/v1/chat/completions", json={
            "model": "Phi-4-mini-instruct-8bit",
            "messages": [{"role": "user", "content": p}],
            "max_tokens": 5, "temperature": 0.0
        }, timeout=30)
        content = r.json()["choices"][0]["message"]["content"].strip().upper()
        return (time.time()-t0)*1000, "YES" if "YES" in content else ("NO" if "NO" in content else content)
    except Exception as e:
        return (time.time()-t0)*1000, f"ERR"

def run(name, fn):
    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")
    times, correct = [], 0
    for i, (d, c, exp) in enumerate(TEST_CASES, 1):
        t, r = fn(d, c)
        times.append(t); ok = r == exp
        if ok: correct += 1
        print(f"  {'✅' if ok else '❌'} [{i:2d}] {t:6.0f}ms  exp={exp} got={r}")
    acc = correct/len(TEST_CASES)*100
    print(f"\n  Accuracy: {acc:.0f}%  avg={statistics.mean(times):.0f}ms  med={statistics.median(times):.0f}ms  p95={sorted(times)[int(len(times)*0.95)]:.0f}ms")
    return {"acc": acc, "avg": statistics.mean(times), "med": statistics.median(times), "p95": sorted(times)[int(len(times)*0.95)]}

# Warm up
test_ollama("warmup", "warmup"); test_phi("warmup", "warmup")

o = run("Ollama bespoke-minicheck (7.7B GGUF)", test_ollama)
p = run("Phi-4-mini (1.5GB MLX 8-bit)", test_phi)

print(f"\n{'='*55}")
print(f"  FINAL")
print(f"{'='*55}")
print(f"  {'':20s} {'Ollama 7.7B':>12s} {'Phi-4 1.5B':>12s}")
print(f"  Accuracy:    {o['acc']:>10.0f}% {p['acc']:>10.0f}%")
print(f"  Avg:         {o['avg']:>10.0f}ms {p['avg']:>10.0f}ms")
print(f"  Median:      {o['med']:>10.0f}ms {p['med']:>10.0f}ms")
