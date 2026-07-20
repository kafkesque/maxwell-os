# Max Document Lifecycle v1.0

## Creation Rules
- New file in root/ → Must be one of: constitution, mission, decision-log, drift-check, task-register, spec
- New file in handoff/ → Must be AI-HANDOFF-YYYY-MM-DD-*.md format
- New file in audit/ → Must be YYYY-MM-DD_*.md format
- New file in temp/ → Auto-purged after 7 days

## Archive Rules (One-In-One-Out)
| Folder | Max Active | Overflow → | Trigger |
|--------|-----------|------------|---------|
| handoff/ | 5 | archive/handoffs/YYYY-MM/ | New handoff |
| audit/ | 5 | archive/audits/YYYY-MM/ | New audit |
| reports/ | 5 | archive/reports/ | New report |
| research/ | 10 | archive/research/ | New research |
| temp/ | 5 | archive/temp/ | Daily purge |
| logs/ | 20 | archive/logs/ | Monthly rotation |

## Forbidden in Root
- Backups (*.bak, *backup*)
- Logs (*.log)
- Archives (archive/, _historical/)
- IDE configs (should be in agent/ or .*/)
- Data files (should be in data/ or external/)
