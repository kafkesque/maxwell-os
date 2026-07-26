# Recipe: Styleboard
# Generated: 2026-07-04 15:56 UTC
# Source: Anytype PT (id=bafyreidjtkwpkrbpsogk46a6fgmuqg5phzxrh5dtgh6btq6oupflfhgjuy)

## Metadata
- **name:** Styleboard
- **slug:** styleboard
- **domain:** any
- **trigger:** Manual (invoked by Goose agent)
- **output:** Execution log via `tools/mcp_fb_server.py`

## Execution Flow

### Phase 1: [Name]

1. - [ ] [Required step — solid checkbox in Anytype]
2. - [ ] [Required step]
3. - [ ] [Optional step — mark as optional]

**Gate:** [condition must be true before Phase 2]

### Phase 2: [Name]

1. - [ ] [Required step]

**Gate:** [condition must be true before Phase 3]

## FB Integration

This recipe integrates with the Maxwell OS knowledge base:

```python
from tools.mcp_fb_server import FBQueryServer
server = FBQueryServer(index_batch="domain_2_visual_design")

# For each principle extracted during execution:
results = server.query_fbs(
    domain="graphic design",
    intent_text="<extracted principle>",
    top_k=3
)

# Log each application:
server.log_execution(
    fb_name=result["name"],
    pt_name="Styleboard",
    pi_id="<principle_instance_id>",
    outcome="confirmed|violated|not_applicable",
    notes="<specific observation>"
)
```
