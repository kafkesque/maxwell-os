# FLAG REGISTRATION PROPOSAL — 2026-09-23 (D-339)

40 `enabled`/`*_enabled` keys in `config/*.yaml` have no registry entry. D-339 keeps them a WARN, not a
RED, because the registry is a *decisions → config* link and every entry CLAIMS a consumer. Registering one is
your one-word call (`REGISTER FLAGS`). This table is the evidence, so the call needs no reading:

| flag (config::path) | files referencing the flag | first files | proposal |
|---|---|---|---|
| `config/bakeoff_laya.yaml::enabled` | 31 | pipeline/s4_golden.py, pipeline/runner.py, pipeline/stage4_merged_call.py | register: required state = its current value, decisions = [D-339] |
| `config/omlx_m1_best_config.yaml::models.Phi-4-mini-instruct-8bit.apply.guided_grammar_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::models.Qwen3-Coder-30B-A3B-Instruct-MLX-4bit.apply.guided_grammar_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::models.Qwen3.8-27B-MLX-4bit.apply.guided_grammar_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::models.gemma-4-E4B-it-MLX-4bit.apply.guided_grammar_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::models.gpt-oss-20b-MXFP4-Q8.apply.guided_grammar_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::models.gpt-oss-20b-MXFP4-Q8.apply.specprefill_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::universal_apply.dflash_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::universal_apply.mtp_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::universal_apply.qwen35_ane_prefill_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/omlx_m1_best_config.yaml::universal_apply.vlm_mtp_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::contextual_embed.enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::e2e.corpus_aware_pass_rate.enabled` | 1 | pipeline/config_audit.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::hyde.enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::ranking.quality_score_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::rerank.enabled` | 2 | pipeline/retrieval_benchmark.py, pipeline/retrieve.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::s2.dspy_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::s2.gate.enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::services.omlx.circuit_breaker_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::services.omlx.mtp_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage1_3.enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage1_5.embed_checkpoint_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage2.gate_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage2.golden_inject_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage2.golden_single_source_inject_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage2.singleton_prefilter_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage2.split_probe_enabled` | 1 | pipeline/config_audit.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::stage4.batch_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage4.depth_batch_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage4.depth_frugal_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage4.golden_inject_enabled` | 2 | pipeline/s4_golden.py, pipeline/stage4_merge.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::stage4.grammar_decoding_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage4.merged_call_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage4.student_preclassifier_enabled` | 1 | pipeline/student_classifier.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::stage4_5.edge_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage4_5.enabled` | 2 | pipeline/pipeline_paths.py, pipeline/stage4_5_enrich.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::stage4_5.procedural_skill_enabled` | 0 | - | exempt_reason (no consumer: it enforces nothing today — the C-1 pattern) |
| `config/pipeline_config.yaml::stage5.factscore_enabled` | 1 | pipeline/config_audit.py | register: required state = its current value, decisions = [D-339] |
| `config/pipeline_config.yaml::stage6.okf_export_enabled` | 2 | pipeline/config_audit.py, pipeline/stage6_okf_export.py | register: required state = its current value, decisions = [D-339] |
| `config/version.yaml::version_gate_enabled` | 1 | pipeline/runner.py | register: required state = its current value, decisions = [D-339] |
