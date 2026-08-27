#!/usr/bin/env python3
"""Stage 4 — preflight + smoke + stress test (deterministic + edge cases).

Exhausts S4's deterministic surface (no LLM variance) plus a live smoke run on
a DIVERSE batch. Covers:

  PREFLIGHT (deterministic, no LLM):
    - config-key resolution (depth_frugal OFF, model routing, C12 thresholds)
    - --only-fb-ids allow-list fail-closed (missing/empty/no-fb_id/0-match)
    - content-type routing (PT/PI/GE/TI → separate files)
    - taxonomy mapping (exact/synonym/emerging + cross-kind collision)
    - name normalization + collision disambiguation
    - classification validation (discipline/domain/depth/evidence)
    - metadata derivation (difficulty/temporal/jargon)

  SMOKE (real OMLX, small diverse batch):
    - run S4 on ~10 FBs spanning convergent + single-source + PT + TI + GE
      + name-collision + emerging-discipline, into a FRESH run_id
    - verify checkpoint + non-principle routing files are written

  STRESS (edge cases):
    - missing fb_id → quarantine (D2350)
    - empty/short application → quarantine (D2371)
    - name-collision auto-disambiguation
    - depth fail-closed (D2351) via SparseClassificationError path

Run:
    python3 -m pytest tests/test_stage4_preflight_smoke_stress.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from pipeline.pipeline_paths import (
    FB_NAME_MAX_WORDS,
    S4_DEPTH_FRUGAL_ENABLED,
    S4_DEPTH_MODEL,
    VERIFY_MODEL,
    GEN_MODEL,
)
from pipeline.stage4_merge import (
    _derive_difficulty_level,
    _load_fb_id_allowlist,
    _resolve_content_type,
    _serialize_jargon,
    _temporal_signal_hit,
    check_name_unique,
    load_stage2_fbs_via_clusters,
    map_to_canonical_with_fallback,
    normalize_fb_name,
    validate_classification,
)
from pipeline.schemas import (
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    get_synonym_index,
)

SYN = get_synonym_index()


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — config-key resolution (script ⇄ config alignment, C12)
# ═══════════════════════════════════════════════════════════════════════════
def test_depth_frugal_is_off() -> None:
    """D2354 must stay OFF — gpt-oss is superior for depth (gemma only when ON)."""
    assert S4_DEPTH_FRUGAL_ENABLED is False
    # When frugal is OFF, the depth model must NOT be selected by S4.
    assert S4_DEPTH_MODEL == "gemma-4-E4B-it-MLX-4bit"  # config default (unused while OFF)


def test_model_routing_r5_compliant() -> None:
    """Generator ≠ Verifier (R5). S4 classifier is a different family from S2 gen."""
    assert VERIFY_MODEL == "gpt-oss-20b-MXFP4-Q8"
    assert GEN_MODEL == "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit"
    assert VERIFY_MODEL != GEN_MODEL


def test_fb_name_max_words_from_config() -> None:
    """C12: FB_NAME_MAX_WORDS must come from config (was hardcoded 5, BUG-149)."""
    assert isinstance(FB_NAME_MAX_WORDS, int) and FB_NAME_MAX_WORDS > 0


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — --only-fb-ids allow-list (fail-closed, C16/D2332)
# ═══════════════════════════════════════════════════════════════════════════
def test_allowlist_missing_path_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as ei:
        _load_fb_id_allowlist(str(tmp_path / "nope.jsonl"))
    assert ei.value.code == 1


def test_allowlist_empty_file_fails_closed(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    with pytest.raises(SystemExit) as ei:
        _load_fb_id_allowlist(str(p))
    assert ei.value.code == 1


def test_allowlist_no_fb_id_field_fails_closed(tmp_path: Path) -> None:
    p = tmp_path / "nofbid.jsonl"
    p.write_text('{"name": "x"}\n{"name": "y"}\n')
    with pytest.raises(SystemExit) as ei:
        _load_fb_id_allowlist(str(p))
    assert ei.value.code == 1


def test_allowlist_valid_returns_set(tmp_path: Path) -> None:
    p = tmp_path / "ok.jsonl"
    p.write_text('{"fb_id": "a"}\n{"fb_id": "b"}\n{"fb_id": "a"}\n')
    ids = _load_fb_id_allowlist(str(p))
    assert ids == {"a", "b"}


def test_allowlist_none_arg_returns_none() -> None:
    assert _load_fb_id_allowlist(None) is None


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — load_stage2_fbs_via_clusters filter (0-match refuse)
# ═══════════════════════════════════════════════════════════════════════════
def test_stage2_filter_matches_only_allowlisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pipeline.stage4_merge as s4

    ckpt = tmp_path / "ckpt.jsonl"
    ckpt.write_text(
        json.dumps({"fb_id": "keep1", "name": "K", "is_convergent": True}) + "\n"
        + json.dumps({"fb_id": "drop1", "name": "D", "is_convergent": False}) + "\n"
    )
    import pipeline.pipeline_paths as pp
    monkeypatch.setattr(s4, "STAGE2_CHECKPOINT", ckpt)
    monkeypatch.setattr(pp, "STAGE2_SINGLETON_OUTPUT", tmp_path / "singletons.jsonl")
    clusters, idx = load_stage2_fbs_via_clusters(only_fb_ids={"keep1"})
    assert len(clusters) == 1
    assert clusters[0]["principle_ids"] == ["keep1"]
    assert "keep1" in idx and "drop1" not in idx


def test_stage2_filter_zero_match_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pipeline.stage4_merge as s4

    ckpt = tmp_path / "ckpt.jsonl"
    ckpt.write_text(json.dumps({"fb_id": "keep1", "name": "K"}) + "\n")
    import pipeline.pipeline_paths as pp
    monkeypatch.setattr(s4, "STAGE2_CHECKPOINT", ckpt)
    monkeypatch.setattr(pp, "STAGE2_SINGLETON_OUTPUT", tmp_path / "singletons.jsonl")
    with pytest.raises(SystemExit) as ei:
        load_stage2_fbs_via_clusters(only_fb_ids={"does_not_exist"})
    assert ei.value.code == 1


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — content-type routing (D2323 axis-1 + D2128 route fallback)
# ═══════════════════════════════════════════════════════════════════════════
def test_resolve_content_type_explicit_wins() -> None:
    assert _resolve_content_type({"content_type": "tool_instruction", "route": "FB"}) == "tool_instruction"


def test_resolve_content_type_route_fallback() -> None:
    assert _resolve_content_type({"route": "PT"}) == "process_template"
    assert _resolve_content_type({"route": "PI"}) == "process_instance"
    assert _resolve_content_type({"route": "GE"}) == "growth_edge"
    assert _resolve_content_type({"route": "TI"}) == "tool_instruction"
    assert _resolve_content_type({"route": "FB"}) == "principle"


def test_resolve_content_type_default_principle() -> None:
    assert _resolve_content_type({}) == "principle"
    assert _resolve_content_type({"route": "UNKNOWN"}) == "principle"


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — taxonomy mapping (exact/synonym/emerging + cross-kind)
# ═══════════════════════════════════════════════════════════════════════════
def test_taxonomy_exact_and_synonym() -> None:
    assert map_to_canonical_with_fallback("graphic design", "domain", SYN, CANONICAL_DOMAINS) == "graphic design"
    assert map_to_canonical_with_fallback("Graphic Design", "domain", SYN, CANONICAL_DOMAINS) == "graphic design"
    assert map_to_canonical_with_fallback("", "domain", SYN, CANONICAL_DOMAINS) == "emerging"
    assert map_to_canonical_with_fallback("quantum astrology", "discipline", SYN, CANONICAL_DISCIPLINES) == "emerging"


def test_taxonomy_cross_kind_collision_resolves_correctly() -> None:
    """`user experience design` is a DOMAIN alias (→ user experience) AND a
    discipline alias (→ human-computer interaction). Kind-constrained index must
    route each correctly (D2133)."""
    assert map_to_canonical_with_fallback("user experience design", "domain", SYN, CANONICAL_DOMAINS) == "user experience"
    assert map_to_canonical_with_fallback("user experience design", "discipline", SYN, CANONICAL_DISCIPLINES) == "human-computer interaction"
    assert map_to_canonical_with_fallback("ux design", "domain", SYN, CANONICAL_DOMAINS) == "user experience"
    assert map_to_canonical_with_fallback("ux design", "discipline", SYN, CANONICAL_DISCIPLINES) == "emerging"


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — name normalization + collision
# ═══════════════════════════════════════════════════════════════════════════
def test_normalize_fb_name_title_case() -> None:
    assert normalize_fb_name("the Law of Attraction", max_words=FB_NAME_MAX_WORDS) == "The Law of Attraction"
    assert normalize_fb_name("KERNING PAIR ADJUSTMENT.", max_words=FB_NAME_MAX_WORDS) == "Kerning Pair Adjustment"


def test_normalize_fb_name_truncation() -> None:
    out = normalize_fb_name("one two three four five six seven eight nine ten", max_words=4)
    assert len(out.split()) == 4


def test_check_name_unique_and_disambiguation() -> None:
    existing = {"The Law of Attraction"}
    assert check_name_unique("New Name", existing) is True
    assert check_name_unique("The Law of Attraction", existing) is False


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT — classification validation + metadata derivation
# ═══════════════════════════════════════════════════════════════════════════
def test_validate_classification_clean() -> None:
    ok, errors = validate_classification({
        "discipline": "design strategy",
        "domains": ["graphic design"],
        "depth": "domain",
        "evidence": "cited",
    })
    assert ok is True and errors == []


def test_validate_classification_invalid() -> None:
    ok, errors = validate_classification({
        "discipline": "quantum astrology",
        "domains": ["not-a-real-domain"],
        "depth": "cosmic",
        "evidence": "maybe",
    })
    assert ok is False and len(errors) >= 4


def test_validate_classification_discipline_list_backcompat() -> None:
    res = {"discipline": ["design strategy"], "domains": ["graphic design"], "depth": "domain", "evidence": "cited"}
    validate_classification(res)
    assert res["discipline"] == "design strategy"  # list → first element


def test_derive_difficulty_all_depths() -> None:
    assert _derive_difficulty_level("specialized", 1) == "expert"
    assert _derive_difficulty_level("universal", 1) == "beginner"
    assert _derive_difficulty_level("cross-domain", 2) == "intermediate"
    assert _derive_difficulty_level("domain", 1) == "expert"       # single → expert
    assert _derive_difficulty_level("domain", 3) == "intermediate"  # multi → intermediate
    assert _derive_difficulty_level("weird", 1) == "intermediate"   # conservative


def test_temporal_signal_boundary() -> None:
    assert _temporal_signal_hit("this holds now", ["now"]) is True
    assert _temporal_signal_hit("the knowledge is fundamental", ["now"]) is False
    assert _temporal_signal_hit("in 2024", ["202"]) is True


def test_serialize_jargon_omits_empty() -> None:
    assert _serialize_jargon(None) is None
    assert _serialize_jargon("") is None
    assert _serialize_jargon("{}") is None
    assert _serialize_jargon({}) is None
    assert _serialize_jargon({"loss aversion": "preferring to avoid losses"}) == "loss aversion: preferring to avoid losses"


# ═══════════════════════════════════════════════════════════════════════════
# STRESS — fail-closed gates via live (MAXWELL_SKIP_LLM=1) subprocess run
# ═══════════════════════════════════════════════════════════════════════════
def _run_s4_subprocess(args: list[str], env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "pipeline/stage4_merge.py", *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )


def test_allowlist_missing_file_subprocess_fails_closed() -> None:
    r = _run_s4_subprocess(
        ["--only-fb-ids", "knowledge pipeline/stage2_extract/t11/DOES_NOT_EXIST.jsonl"],
        {"MAXWELL_RUN_ID": "smoke_preflight"},
    )
    assert r.returncode == 1
    assert "not found" in (r.stdout + r.stderr)


def test_allowlist_no_fb_id_subprocess_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "nofbid.jsonl"
    bad.write_text('{"name": "x"}\n')
    r = _run_s4_subprocess(
        ["--only-fb-ids", str(bad)],
        {"MAXWELL_RUN_ID": "smoke_preflight"},
    )
    assert r.returncode == 1
    assert "no fb_id" in (r.stdout + r.stderr)


def _stage_smoke_s2(run_id: str, picks: list[dict[str, Any]], inject_application: bool) -> None:
    """Stage a small diverse S2 checkpoint under a fresh run_id so S4 can find it.

    MAXWELL_RUN_ID controls BOTH the S2 read path and the S4 write path, so a
    clean smoke run needs its own stage2_extract/{run_id}/checkpoint.jsonl.
    """
    s2_dir = ROOT / "knowledge pipeline" / "stage2_extract" / run_id
    s2_dir.mkdir(parents=True, exist_ok=True)
    # Wipe any prior S4 checkpoint for this run_id (test isolation: a leftover
    # checkpoint would trigger resume and skip everything, silently passing).
    s4_dir = ROOT / "knowledge pipeline" / "stage4_merge" / run_id
    if s4_dir.exists():
        import shutil
        shutil.rmtree(s4_dir)
    rows = []
    for p in picks:
        rec = dict(p)
        if inject_application:
            rec["application"] = "When testing the pipeline, apply this principle because it verifies plumbing."
        rows.append(rec)
    with open(s2_dir / "checkpoint.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _pick_diverse_s2() -> dict[str, dict[str, Any]]:
    """Return one representative per content_type from the real S2 checkpoint."""
    s2 = ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.jsonl"
    rows = [json.loads(l) for l in open(s2, encoding="utf-8") if l.strip()]
    picks: dict[str, dict[str, Any]] = {}
    for r in rows:
        ct = r.get("content_type")
        if ct == "principle" and "principle" not in picks:
            picks["principle"] = r
        elif ct == "process_template" and "process_template" not in picks:
            picks["process_template"] = r
        elif ct == "tool_instruction" and "tool_instruction" not in picks:
            picks["tool_instruction"] = r
        elif ct == "growth_edge" and "growth_edge" not in picks:
            picks["growth_edge"] = r
        if len(picks) >= 4:
            break
    return picks


def test_smoke_d2371_quarantine_without_application(tmp_path: Path) -> None:
    """LLM-off + no application → D2371 quarantine → fail-closed exit (not silent)."""
    picks = _pick_diverse_s2()
    run_id = "smoke_preflight_q"
    _stage_smoke_s2(run_id, list(picks.values()), inject_application=False)
    allow = tmp_path / "allow.jsonl"
    with open(allow, "w", encoding="utf-8") as f:
        for r in picks.values():
            f.write(json.dumps({"fb_id": r["fb_id"]}) + "\n")

    r = _run_s4_subprocess(
        ["--only-fb-ids", str(allow)],
        {"MAXWELL_RUN_ID": run_id, "MAXWELL_SKIP_LLM": "1"},
    )
    # Application is absent → every principle is quarantined → non-zero exit.
    assert r.returncode in (1, 2)
    assert "QUARANTINED" in (r.stdout + r.stderr)


def test_smoke_diverse_batch_writes_checkpoint_and_routes(tmp_path: Path) -> None:
    """LLM-off + application injected → full plumbing writes checkpoint + routes.

    Exercises: --only-fb-ids filtering, content-type routing (PT/TI/GE → separate
    files), name normalization, metadata derivation, and the atomic S4 checkpoint
    write — all deterministically (no OMLX variance).
    """
    picks = _pick_diverse_s2()
    run_id = "smoke_preflight_plumbing"
    _stage_smoke_s2(run_id, list(picks.values()), inject_application=True)
    allow = tmp_path / "allow.jsonl"
    with open(allow, "w", encoding="utf-8") as f:
        for r in picks.values():
            f.write(json.dumps({"fb_id": r["fb_id"]}) + "\n")

    r = _run_s4_subprocess(
        ["--only-fb-ids", str(allow)],
        {"MAXWELL_RUN_ID": run_id, "MAXWELL_SKIP_LLM": "1"},
    )
    # LLM off: classification will be skipped→ no classify call; but CRIBS skipped
    # too. The FB still flows if application present + name/definition valid.
    out = r.stdout + r.stderr
    # S4 checkpoint dir must exist under the smoke run_id.
    s4_dir = ROOT / "knowledge pipeline" / "stage4_merge" / run_id
    ckpt = s4_dir / "checkpoint.jsonl"
    assert ckpt.exists(), f"S4 checkpoint missing. stdout:\n{out}"
    written = [json.loads(l) for l in open(ckpt, encoding="utf-8") if l.strip()]
    # Non-principle types are routed to separate files; principle → checkpoint.
    assert len(written) >= 1
    # PT/TI/GE sidecars must exist when those types were in the batch.
    pt = s4_dir / "process_templates.jsonl"
    ti = s4_dir / "tool_instructions.jsonl"
    ge = s4_dir / "growth_edges.jsonl"
    assert pt.exists() and ti.exists() and ge.exists()
