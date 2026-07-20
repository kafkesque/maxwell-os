# Maxwell OS — Folder Protocol v1.1
## What belongs where, when to archive, when to delete

## ROOT CHARTER (only these file types at /)
- Canonical docs: CONSTITUTION.md, MISSION.md, DECISION-LOG.md, DRIFT-CHECK.md, MASTER-TASK-REGISTER.md
- Build: justfile, pyproject.toml, requirements.txt
- Environment: .env, .env.example
- Active data: push_ledger.jsonl, agent_knowledge.db (+ .db-shm, .db-wal)
- Loader: AGENTS.md → points to CONSTITUTION.md

## FOLDER TAXONOMY

| Folder | Purpose | Max Files |
|--------|---------|-----------|
| agent/ | Current session config + active skills | — |
| archive/ | ALL historical/dead material | — |
| audit/ | Recent audit reports | 5 newest |
| config/ | Active configuration | — |
| data/ | Runtime data, exports | — |
| governance/ | Folder protocol + lifecycle rules | — |
| handoff/ | Session handoffs | 5 newest |
| knowledge pipeline/ | Pipeline I/O | — |
| loop/ | Orchestration scripts | — |
| notes/ | Unstructured notes, PENDING-REPO | — |
| reports/ | Generated reports | 5 newest |
| research/ | Research intel | 10 newest |
| temp/ | Session scratch | auto-purge 7d |
| tools/ | Active scripts ONLY (no archive subfolder) | — |

## DOCUMENT LIFECYCLE

| Type | Max | Overflow → | Age limit |
|------|-----|-----------|-----------|
| Handoff | 5 | archive/handoffs/ | 30 days |
| Audit | 5 | archive/audits/ | 30 days |
| Root *.md | 6 canonical | Never | Never |
| Backup *.jsonl | 0 in root | archive/push_ledger/ | never in root |
| Temp | — | Delete | 7 days |

## ONE-IN-ONE-OUT
For any new file in handoff/, audit/, reports/ — archive oldest.
For any new file in root/ — justify why it can't go in a subfolder.
