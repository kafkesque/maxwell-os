#!/usr/bin/env python3
"""Add CONV-050 (Hanlon's Razor) and finalize meta."""
import yaml, tempfile, os, subprocess, json, re
from collections import Counter

with open('config/golden/stage2_fewshot_convergent.yaml', 'r') as f:
    data = yaml.safe_load(f)

examples = data['examples']

examples.append({
    'id': 'CONV-050',
    'domain': 'decision making',
    'discipline': 'cognitive bias mitigation',
    'source_books': [
        'The Art of Thinking Clearly — Rolf Dobelli',
        'Crucial Conversations — Kerry Patterson et al.',
    ],
    'cluster_segments': [
        {
            'source_book': 'The Art of Thinking Clearly — Rolf Dobelli',
            'text': (
                "Hanlon's Razor advises: never attribute to malice that which is "
                "adequately explained by incompetence, neglect, or misunderstanding. "
                "The human mind has a systematic bias toward intentionality — we "
                "assume that actions that harm us were intended to harm us, even "
                "when the far more likely explanation is carelessness, systems "
                "failure, or simple error. This bias is costly: it escalates "
                "conflicts that could be resolved, burns relationships that could "
                "be repaired, and directs investigative energy toward motive when "
                "it should be directed toward process."
            ),
        },
        {
            'source_book': 'Crucial Conversations — Kerry Patterson et al.',
            'text': (
                'When someone does something that hurts or offends us, the brain '
                'instantly constructs a villain story: they did it because they are '
                'selfish, malicious, or indifferent to our wellbeing. The alternative '
                '— the victim story — casts us as innocent targets of their '
                'character flaw. But most harmful actions arise from incompetence, '
                'conflicting priorities, or incomplete information — not malice. '
                'The heuristic is: before assuming bad intent, ask "what else could '
                'explain this?" The answer is usually less personal and more fixable '
                'than the villain story suggests.'
            ),
        },
    ],
    'is_convergent': True,
    'should_extract': True,
    'expected_fb': {
        'is_summary': False,
        'route': 'FB',
        'name': "Hanlon's Razor — Incompetence Over Malice Default",
        'definition': (
            'When interpreting harmful or frustrating behavior, default to the '
            'explanation of incompetence, neglect, or misunderstanding over the '
            'explanation of malice. Most harm arises from error and systems failure, '
            'not intent. A prescriptive cognitive heuristic for conflict de-escalation.'
        ),
        'mechanism': (
            'This is a NORMATIVE HEURISTIC — a rule of procedure for interpreting '
            "others' behavior. It says DO this: assume incompetence before malice. "
            'The heuristic works because the human mind has a systematic intentionality '
            'bias — the tendency to attribute agency and intent to events that affect '
            'us, even when those events are random or systemic. This bias serves an '
            'evolutionary function (better to false-alarm a predator than miss one) '
            'but is maladaptive in modern organizational life, where most harm is '
            'caused by process failures, miscommunication, and misaligned incentives, '
            'not hostile intent. Dobelli provides the cognitive bias framework, '
            'Patterson provides the interpersonal application.'
        ),
        'boundary': (
            'Applies to ambiguous harmful actions where intent is uncertain. Fails '
            'when: (1) there is clear evidence of malice (documented threats, history '
            'of targeted harm); (2) the actor has a track record of malevolent behavior '
            'in similar situations; (3) the heuristic is used to excuse genuine abuse '
            'or to avoid necessary confrontation. The razor is a default, not a dogma '
            '— it shifts the burden of proof toward the malice hypothesis but does '
            'not rule it out.'
        ),
        'consequence': (
            "Systematic application of Hanlon's Razor reduces interpersonal conflict, "
            'preserves professional relationships, and redirects problem-solving effort '
            'from blame (who did this to me?) to process (what failed and how do we fix '
            'it?). In organizations, it shifts culture from paranoid to learning-oriented. '
            'The counterfactual — defaulting to malice attribution — produces escalating '
            'cycles of retaliation and defensiveness that amplify the original harm.'
        ),
        'evidence_passages': [
            'never attribute to malice that which is adequately explained by incompetence, neglect, or misunderstanding',
            'most harmful actions arise from incompetence, conflicting priorities, or incomplete information — not malice',
            'before assuming bad intent, ask "what else could explain this?"',
            'the brain instantly constructs a villain story: they did it because they are selfish, malicious, or indifferent',
        ],
        'extraction_type': 'normative_heuristic',
        'content_type': 'heuristic',
        'depth': 'cross-domain',
    },
    'rationale': (
        'NEW NORMATIVE HEURISTIC (D2234: extraction type expansion). '
        'Dobelli and Patterson converge on the same prescriptive cognitive heuristic: '
        'default to incompetence over malice when interpreting harmful behavior. '
        'Dobelli provides the cognitive bias framing (intentionality bias), Patterson '
        'provides the interpersonal application (villain stories in crucial conversations). '
        'This is a NORMATIVE HEURISTIC because it prescribes HOW to interpret ambiguous '
        'behavior — a rule of cognitive procedure, not a causal mechanism.'
    ),
})

data['meta']['example_count'] = len(examples)
print(f'Added CONV-050, now {len(examples)} examples')

# Save
tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, dir='config/golden')
yaml.dump(data, tmp, allow_unicode=True, sort_keys=False, width=120)
tmp.flush()
os.fsync(tmp.fileno())
tmp.close()
os.replace(tmp.name, 'config/golden/stage2_fewshot_convergent.yaml')

# Validate
result = subprocess.run(['python3', 'pipeline/golden_validate.py'], capture_output=True, text=True)
print(result.stdout.strip())
if result.stderr:
    for line in result.stderr.strip().split('\n'):
        if any(x in line for x in ['NON_VERBATIM', 'MISSING', 'FAIL']):
            print(f'  {line[:120]}')

# Summary
tc = Counter()
for ex in examples:
    ef = ex.get('expected_fb', {})
    fbs = ef if isinstance(ef, list) else [ef]
    for fb in fbs:
        if isinstance(fb, dict) and fb.get('extraction_type'):
            tc[fb['extraction_type']] += 1
print(f'\n── TYPE DISTRIBUTION ──')
for t, c in tc.most_common():
    target = ' ✅' if c >= 12 else f' (need {12-c} more)'
    print(f'  {t}: {c}{target}')
print(f'  Total FBs: {sum(tc.values())}')

# Author check
print(f'\n── AUTHOR CHECK ──')
for author, pattern in [('Kahneman', r'\bKahneman\b'), ('Taleb', r'\bTaleb\b'),
                          ('James Clear', r'James Clear|Atomic Habits'), ('Gladwell', r'\bGladwell\b')]:
    hits = []
    for ex in examples:
        if re.search(pattern, json.dumps(ex), re.IGNORECASE):
            hits.append(ex.get('id'))
    print(f'  {author}: {len(hits)} -> {hits}')
