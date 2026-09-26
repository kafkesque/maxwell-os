# Dropbox conflict register

Mode: DRY RUN | decided D-2647 | one live artifact, one source of truth. The resolution rule is measured, never guessed: index > head > 3-way merge (git merge-file).

| live path | verdict | why | action |
|---|---|---|---|
| governance/anchor_adjudication_workbook_20260924.csv | CONFLICT:1 | hunks need a human - NOT written | held |
| governance/bug_status.json | CONFLICT:3 | hunks need a human - NOT written | held |
| governance/bug_status.md | CONFLICT:2 | hunks need a human - NOT written | held |
| knowledge pipeline/stage4_merge/smoke_live_cribs/checkpoint.jsonl | OWNER:pipeline-state | never text-merged | held |
| knowledge pipeline/stage4_merge/smoke_live_cribs/checkpoint.jsonl.expected_count.json | OWNER:pipeline-state | never text-merged | held |
| knowledge pipeline/stage5_verify/t11/checkpoint.jsonl.input_fingerprint.json | OWNER:pipeline-state | never text-merged | held |
