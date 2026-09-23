# FLAG HYGIENE / INTENT TASKS — 2026-09-23 (D-339, D-338)

Registry now holds 27 entries. Remaining unregistered flags are reported by `python3 scripts/audit_flag_consumers.py` as WARN.

## A. Registered but nothing reads them (exempt_reason, listed for deletion-or-wiring)

- `config/verify_abstention.yaml::enabled`
- `config/omlx_m1_best_config.yaml::universal_apply.dflash_enabled`
- `config/omlx_m1_best_config.yaml::universal_apply.qwen35_ane_prefill_enabled`
- `config/omlx_m1_best_config.yaml::universal_apply.vlm_mtp_enabled`

## B. ON and nothing reads them (if any: a claimed control that does not exist — C-1 pattern)

- (none)

## C. Dropped from the registry because the declared consumer does not actually read the flag

The audit's `consumer_reads` check REFUSED these claims (D-338: no state/consumer is asserted without a receipt).
Each needs one owner call: **wire it** (name the file that reads it) or **turn it off** (it is ON and enforces nothing).

- `config/bakeoff_laya.yaml::enabled` — required=False, claimed consumers ['pipeline/config_audit.py', 'pipeline/embeddings.py', 'pipeline/hybrid_gate.py', 'pipeline/omlx_call.py'], audit: `['pipeline/config_audit.py', 'pipeline/embeddings.py', 'pipeline/hybrid_gate.py', 'pipeline/omlx_call.py']`
- `config/omlx_m1_best_config.yaml::universal_apply.mtp_enabled` — required=False, claimed consumers ['scripts/mtp_ab.py'], audit: `['scripts/mtp_ab.py']`
- `config/omlx_m1_best_config.yaml::models.Qwen3-Coder-30B-A3B-Instruct-MLX-4bit.apply.guided_grammar_enabled` — required=True, claimed consumers ['scripts/_omlx_apply_settings.py'], audit: `['scripts/_omlx_apply_settings.py']`
- `config/omlx_m1_best_config.yaml::models.gpt-oss-20b-MXFP4-Q8.apply.guided_grammar_enabled` — required=True, claimed consumers ['scripts/_omlx_apply_settings.py'], audit: `['scripts/_omlx_apply_settings.py']`
- `config/omlx_m1_best_config.yaml::models.gpt-oss-20b-MXFP4-Q8.apply.specprefill_enabled` — required=False, claimed consumers ['scripts/omlx_lever_ab.py'], audit: `['scripts/omlx_lever_ab.py']`
- `config/omlx_m1_best_config.yaml::models.Phi-4-mini-instruct-8bit.apply.guided_grammar_enabled` — required=True, claimed consumers ['scripts/_omlx_apply_settings.py'], audit: `['scripts/_omlx_apply_settings.py']`
- `config/omlx_m1_best_config.yaml::models.gemma-4-E4B-it-MLX-4bit.apply.guided_grammar_enabled` — required=True, claimed consumers ['scripts/_omlx_apply_settings.py'], audit: `['scripts/_omlx_apply_settings.py']`
- `config/pipeline_config.yaml::services.omlx.mtp_enabled` — required=True, claimed consumers ['scripts/mtp_ab.py'], audit: `['scripts/mtp_ab.py']`
- `config/pipeline_config.yaml::stage1_3.enabled` — required=True, claimed consumers ['pipeline/pipeline_paths.py', 'pipeline/run_monitor.py', 'pipeline/stage1_3_prefilter.py', 'pipeline/stage1_5_domain_cluster.py'], audit: `['pipeline/run_monitor.py']`
- `config/pipeline_config.yaml::stage4.merged_call_enabled` — required=True, claimed consumers ['pipeline/run_diagnostic.py', 'pipeline/stage4_merge.py', 'scripts/run_forensic_audit_parallel.py'], audit: `['scripts/run_forensic_audit_parallel.py']`
- `config/pipeline_config.yaml::stage4.batch_enabled` — required=False, claimed consumers ['pipeline/pipeline_paths.py', 'pipeline/reclassify_merged_axis.py', 'pipeline/stage4_merge.py', 'scripts/run_forensic_audit_parallel.py'], audit: `['pipeline/reclassify_merged_axis.py', 'scripts/run_forensic_audit_parallel.py']`
- `config/pipeline_config.yaml::stage4.depth_batch_enabled` — required=True, claimed consumers ['pipeline/pipeline_paths.py', 'scripts/run_forensic_audit_parallel.py'], audit: `['scripts/run_forensic_audit_parallel.py']`
- `config/pipeline_config.yaml::stage4.student_preclassifier_enabled` — required=False, claimed consumers ['pipeline/pipeline_paths.py', 'pipeline/student_classifier.py', 'scripts/calibrate_student_thresholds.py'], audit: `['pipeline/student_classifier.py', 'scripts/calibrate_student_thresholds.py']`
- `config/pipeline_config.yaml::s2.gate.enabled` — required=False, claimed consumers ['pipeline/axis_authority.py', 'pipeline/e2e_test.py', 'pipeline/embeddings.py', 'pipeline/golden_validate.py'], audit: `['pipeline/axis_authority.py', 'pipeline/golden_validate.py']`
- `config/pipeline_config.yaml::stage6.okf_export_enabled` — required=True, claimed consumers ['pipeline/config_audit.py', 'pipeline/pipeline_paths.py', 'pipeline/stage6_okf_export.py'], audit: `['pipeline/stage6_okf_export.py']`
- `config/pipeline_config.yaml::stage4_5.enabled` — required=False, claimed consumers ['pipeline/pipeline_paths.py', 'pipeline/stage4_5_enrich.py'], audit: `['pipeline/stage4_5_enrich.py']`
- `config/pipeline_config.yaml::rerank.enabled` — required=True, claimed consumers ['pipeline/pipeline_paths.py', 'pipeline/rerank.py', 'pipeline/retrieval_benchmark.py', 'pipeline/retrieve.py'], audit: `['pipeline/retrieve.py']`

## D. Disposition policy

- Delete-or-wire is a `C19`/`C12` hygiene call: config should be intentional, not aspirational.
- Never blanket-exempt on faith: an exemption must stay verifiable, and `scripts/audit_flag_consumers.py`
  now REDs a STALE EXEMPTION (an entry that has an exempt_reason AND a real consumer).



## E. Deferred registrations (2026-09-23) — registered: 43, deferred: 1
Deferred = the audit could NOT verify the entry, so it was NOT registered (D-338: no unverified claim in the register).
Two distinct causes, two different owner calls:

**E1. Path grammar cannot express the key (1)** — dotted MODEL names (`Qwen3.8-27B-MLX-4bit`) make the
registry's dotted path unparseable, so the audit reports `path MISSING` for a flag that exists. This is BUG-375's class
again, third instance (BUG-382). Owner call: none — it is a checker fix (path quoting), queued.

**E2. ON and the audit found no reader (0)** — a flag that is ON and whose reader cannot be
verified is exactly the C-1 pattern (a claimed control that does not exist). Owner call, per flag: **wire it** (name the
file that reads it) or **turn it off**.
- `config/omlx_m1_best_config.yaml::models.Qwen3.8-27B-MLX-4bit.apply.guided_grammar_enabled`

## G. Final deferred set (2026-09-23, one owner call each)

Cause A = path grammar (BUG-382, checker fix, no owner call). Cause B = ON with no verifiable reader
(the C-1 pattern: a claimed control that may not exist) — **wire it** (name the reading file) or **turn it off**.


