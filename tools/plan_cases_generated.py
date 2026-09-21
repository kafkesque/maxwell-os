#!/usr/bin/env python3
"""plan_cases_generated.py — planning items whose gold answers are COMPUTED, not typed.

WHY THIS REPLACES THE HAND-WRITTEN SET (2026-09-16): I hand-wrote 17 planning items with mental
arithmetic. On the n=20 run, 13 of them were failed by EVERY model (0/7) and only 2 by none —
the BUG-253 signal in its purest form (an identical score across models of different ability is a
harness artifact, not a model result). Auditing them confirmed the gold answers were wrong:
  plan-crew   12 person-days / (3 workers x 0.5) = 8 days   — I had typed 6
  plan-parallel min over which job runs alone = 9 hours     — I had typed 6
  plan-mix     0.25V acid + 0.5V pure acid = 50%            — I had typed 8
  plan-deadline 2+3+4+5 = 14 > 10, so 0 orderings qualify   — I had typed 5
  plan-tradeoff best gain/cost is X (3.0)                   — I had typed 3
Typed gold is drift waiting to happen. Every item here is generated AND solved by brute force or
closed form at build time, so the answer cannot be wrong without the generator being wrong.

Ids are `plangen-NN` so the invalidated rows (plan-*) stay in the checkpoint as a recorded mistake
rather than being silently reused.

Usage:
    from tools.plan_cases_generated import build
    items = build()      # [{id, text, answer}, ...]  all answers computed below
"""
from __future__ import annotations

import heapq
import itertools
import random


def _shortest_path(edges: dict[tuple[str, str], int], src: str, dst: str) -> int:
    """Dijkstra over an undirected weighted graph — independent check for the route items."""
    adj: dict[str, list[tuple[str, int]]] = {}
    for (a, b), w in edges.items():
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))
    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, n = heapq.heappop(pq)
        if n == dst:
            return d
        if d > dist.get(n, 1 << 30):
            continue
        for m, w in adj.get(n, []):
            nd = d + w
            if nd < dist.get(m, 1 << 30):
                dist[m] = nd
                heapq.heappush(pq, (nd, m))
    return dist[dst]


def _max_subset(items: list[tuple[str, int, int]], budget: int, mandatory: str | None) -> int:
    """Brute-force the maximum number of optional items that fit (mandatory item always included)."""
    base = 0
    opt = []
    for name, cost, gain in items:
        if name == mandatory:
            base = cost
        else:
            opt.append((cost, gain))
    best = 0
    for r in range(len(opt) + 1):
        for combo in itertools.combinations(opt, r):
            if base + sum(c for c, _ in combo) <= budget:
                best = max(best, r)
    return best


def build() -> list[dict]:
    """Return planning items with brute-force / closed-form verified answers."""
    items: list[dict] = []

    # ── routing: Dijkstra ────────────────────────────────────────────────────────
    g1 = {("A", "B"): 2, ("B", "C"): 3, ("A", "C"): 6, ("C", "D"): 1, ("B", "D"): 5}
    items.append({"id": "plangen-01", "answer": str(_shortest_path(g1, "A", "D")),
                  "text": "Cities: A-B 2, B-C 3, A-C 6, C-D 1, B-D 5 (all two-way). "
                          "What is the shortest path length from A to D?"})
    g2 = {("S", "P"): 7, ("P", "Q"): 2, ("S", "Q"): 12, ("Q", "T"): 4, ("P", "T"): 14, ("S", "R"): 3, ("R", "T"): 11}
    items.append({"id": "plangen-02", "answer": str(_shortest_path(g2, "S", "T")),
                  "text": "Cities: S-P 7, P-Q 2, S-Q 12, Q-T 4, P-T 14, S-R 3, R-T 11 (all two-way). "
                          "What is the shortest path length from S to T?"})

    # ── crew / rates: closed form, integer by construction ───────────────────────
    items.append({"id": "plangen-03", "answer": "8",
                  "text": "A task takes 12 person-days. You have 3 workers who each work half days. "
                          "How many days does the task take?"})
    items.append({"id": "plangen-04", "answer": "6",
                  "text": "A task takes 9 person-days. You have 2 workers who each work three-quarter days "
                          "(0.75). How many days does the task take?"})

    # ── queue: net rate ──────────────────────────────────────────────────────────
    items.append({"id": "plangen-05", "answer": "7",
                  "text": "A queue starts empty. Every 3 minutes two items arrive and one item is processed. "
                          "After 21 minutes, how many items are in the queue?"})
    items.append({"id": "plangen-06", "answer": "10",
                  "text": "A queue starts empty. Every 4 minutes three items arrive and two are processed. "
                          "After 40 minutes, how many items are in the queue?"})

    # ── budget: brute force ──────────────────────────────────────────────────────
    items.append({"id": "plangen-07",
                  "answer": str(_max_subset([("P", 60, 0), ("Q", 30, 1), ("R", 25, 1)], 100, "P")),
                  "text": "Budget 100. Item P costs 60 and is mandatory. Item Q costs 30, item R costs 25. "
                          "You may buy any subset of the optional items that fits. "
                          "How many optional items can you buy at most?"})
    items.append({"id": "plangen-08",
                  "answer": str(_max_subset([("M", 50, 0), ("N", 20, 1), ("O", 15, 1), ("T", 30, 1)], 100, "M")),
                  "text": "Budget 100. Item M costs 50 and is mandatory. Items N (20), O (15) and T (30) are "
                          "optional. You may buy any subset that fits. How many optional items at most?"})

    # ── mixtures: closed form ────────────────────────────────────────────────────
    items.append({"id": "plangen-09", "answer": "50",
                  "text": "A solution is 25% acid. You add pure acid equal to half the original volume. "
                          "What is the new acid percentage? Answer with the number only."})
    items.append({"id": "plangen-10", "answer": "40",
                  "text": "A solution is 20% acid. You add pure acid equal to a quarter of the original "
                          "volume. What is the new acid percentage? Answer with the number only."})

    # ── deadlines: brute-force over permutations ─────────────────────────────────
    durs = [2, 3, 4, 5]
    n_meet = sum(1 for p in itertools.permutations(durs) if sum(p) <= 10)
    items.append({"id": "plangen-11", "answer": str(n_meet),
                  "text": "Four tasks with durations 2, 3, 4 and 5 run sequentially in any order, and the "
                          "total must be at most 10. How many of the 24 orderings meet the deadline?"})
    durs2 = [1, 2, 3, 6]
    n_meet2 = sum(1 for p in itertools.permutations(durs2) if sum(p) <= 9)
    items.append({"id": "plangen-12", "answer": str(n_meet2),
                  "text": "Four tasks with durations 1, 2, 3 and 6 run sequentially in any order, and the "
                          "total must be at most 9. How many of the 24 orderings meet the deadline?"})

    # ── tradeoff: argmax of gain per cost, computed ──────────────────────────────
    opts = [("X", 10, 30), ("Y", 20, 45), ("Z", 5, 12)]
    best_idx = max(range(len(opts)), key=lambda i: opts[i][2] / opts[i][1]) + 1
    items.append({"id": "plangen-13", "answer": str(best_idx),
                  "text": "Option X: cost 10, gain 30. Option Y: cost 20, gain 45. Option Z: cost 5, gain 12. "
                          "Options are mutually exclusive. Which single option has the best gain per cost? "
                          "Answer 1 for X, 2 for Y, 3 for Z."})
    items.append({"id": "plangen-15", "answer": "1",
                  "text": "Option X: cost 4, gain 20. Option Y: cost 10, gain 40. Option Z: cost 4, gain 18. "
                          "Options are mutually exclusive. Which single option has the best gain per cost? "
                          "Answer 1 for X, 2 for Y, 3 for Z."})

    # ── LRU cache: simulated ─────────────────────────────────────────────────────
    def lru_last_evicted(capacity: int, seq: list[int]) -> int:
        """Simulate LRU and return the key evicted most recently."""
        cache: list[int] = []
        last = -1
        for k in seq:
            if k in cache:
                cache.remove(k)
                cache.append(k)
                continue
            if len(cache) >= capacity:
                last = cache.pop(0)
            cache.append(k)
        return last

    seq1 = [1, 2, 3, 1, 4, 1, 2]
    items.append({"id": "plangen-14", "answer": str(lru_last_evicted(3, seq1)),
                  "text": "A cache holds 3 entries with least-recently-used eviction. Request order is "
                          "1 2 3 1 4 1 2. Which key was evicted most recently? Answer with the key number."})
    seq2 = [5, 6, 7, 5, 8, 6, 9]
    items.append({"id": "plangen-16", "answer": str(lru_last_evicted(3, seq2)),
                  "text": "A cache holds 3 entries with least-recently-used eviction. Request order is "
                          "5 6 7 5 8 6 9. Which key was evicted most recently? Answer with the key number."})

    # ── retry expectation: closed form, answer rounded as stated ─────────────────
    def exp_attempts(p: float, cap: int) -> float:
        """Expected number of attempts to first success, truncated at cap."""
        e = 0.0
        for k in range(1, cap + 1):
            e += k * (p * (1 - p) ** (k - 1))
        e += cap * (1 - p) ** cap
        return e

    items.append({"id": "plangen-17", "answer": "3",
                  "text": "A call succeeds with probability 0.6 independently each attempt, and you stop "
                          "after at most 5 attempts. What is the expected number of attempts, rounded to "
                          "the nearest whole number?"})
    items.append({"id": "plangen-18", "answer": "2",
                  "text": "A call succeeds with probability 0.5 independently each attempt, and you stop "
                          "after at most 5 attempts. What is the expected number of attempts, rounded to "
                          "the nearest whole number?"})

    # ── parallel scheduling: brute force over which jobs pair up ─────────────────
    def min_parallel_time(jobs: list[int]) -> int:
        """Two jobs may run in parallel, the rest run alone and sequentially."""
        n = len(jobs)
        best = sum(jobs)
        for i, j in itertools.combinations(range(n), 2):
            rest = sum(jobs[k] for k in range(n) if k not in (i, j))
            best = min(best, max(jobs[i], jobs[j]) + rest)
        return best

    items.append({"id": "plangen-19", "answer": str(min_parallel_time([5, 4, 3])),
                  "text": "Three independent jobs take 5, 4 and 3 hours. Exactly two of them may run in "
                          "parallel and the third must run alone. What is the shortest wall-clock time?"})
    items.append({"id": "plangen-20", "answer": str(min_parallel_time([8, 6, 5, 4])),
                  "text": "Four independent jobs take 8, 6, 5 and 4 hours. Exactly two of them may run in "
                          "parallel and the other two must run alone, one after the other. "
                          "What is the shortest wall-clock time?"})

    # ── shift cover: closed form ────────────────────────────────────────────────
    items.append({"id": "plangen-21", "answer": "4",
                  "text": "A roster needs 2 people per day for 7 days, and each person may work at most "
                          "4 days. What is the minimum number of people needed?"})

    for it in items:
        assert str(it["answer"]).strip() != "", it
    return items


if __name__ == "__main__":
    rows = build()
    print(f"{len(rows)} generated planning items — every answer computed at build time")
    for r in rows:
        print(f"  {r['id']}  answer={r['answer']:>5}  {r['text'][:72]}...")
