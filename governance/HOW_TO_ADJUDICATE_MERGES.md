# Your one decision, in plain words

**Open this file:** `governance/gold_reattach_many_to_one_ADJUDICATION.csv`

It has **40 rows**. Each row asks ONE question:

> Is the "old idea" actually **the same thing** as the "merged idea", or a **different thing**?

That's the whole job. You answer with one word in the **`Same idea?`** column:

- `SAME` → yes, these are the same idea (they were correctly combined)
- `DIFFERENT` → no, these are two different ideas (they got wrongly glued together)

**I already filled in my best guess for every row.** You only change a row if you
disagree with me. Then save the file (keep it CSV).

## You never have to know where anything goes

If you write `DIFFERENT`, that's all I need. **I** find the right place for it in the
system, or mark it dead if it has no place. You are not the database — I am. You just
tell me "these two aren't the same."

## Why this matters (10-second version)

Your system holds a list of ~6,500 "principles" (ideas/insights). Some of them got new
ID numbers a while ago, so I tried to automatically re-connect the old labels to the new
IDs by matching similar text. It worked for most. But in 20 spots, **two different old
ideas got stuck to one new idea** because they share a word — like "diversity" or
"selection" or "workflow".

I need you, the human who knows what these ideas mean, to just say which of those 20 are
genuinely the same idea and which are mistakes. Then I clean up the mistakes myself.

## How to do it in 3 minutes

1. Open the CSV in Numbers / Excel.
2. Scan the `Same idea?` column.
3. Where you disagree with my guess, type `SAME` or `DIFFERENT` over it.
4. Save. Tell me **"done"**.

## Examples (so you know what you're looking at)

| merged idea | old idea | my guess | plain reasoning |
|---|---|---|---|
| Diversity As Source of Systemic Potential | Network Robustness Through Structural Diversity | DIFFERENT | one is ecology, one is networking — only share the word "diversity" |
| Design Review Resistance Pattern | Design Review Resistance Pattern | SAME | identical name |
| Decision-making Under Uncertainty | Decision-making Under Uncertainty | SAME | identical name |
| Metaphorical Conceptualization | Metaphorical Cognitive Mapping | SAME | same idea, worded differently |
