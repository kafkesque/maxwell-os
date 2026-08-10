#!/usr/bin/env python3
"""Add 3 descriptive_model examples to reach 12 (D2234 completion)."""
import yaml, tempfile, os, subprocess
from collections import Counter

with open('config/golden/stage2_fewshot_convergent.yaml', 'r') as f:
    data = yaml.safe_load(f)

examples = data['examples']

new_examples = [
    # ── DM-004: Big Five (OCEAN) personality taxonomy ──
    {
        'id': 'CONV-051',
        'domain': 'psychology',
        'discipline': 'personality psychology',
        'source_books': [
            'Quiet — Susan Cain',
            'Grit — Angela Duckworth',
        ],
        'cluster_segments': [
            {
                'source_book': 'Quiet — Susan Cain',
                'text': (
                    'Personality traits can be organized along five broad dimensions — '
                    'Openness to experience, Conscientiousness, Extraversion, Agreeableness, '
                    'and Neuroticism (OCEAN). Each dimension is a spectrum, not a binary, '
                    'and most people fall somewhere in the middle on most traits. The model '
                    'is descriptive: it classifies the landscape of human personality into '
                    'five empirically-derived factors that emerge consistently across cultures '
                    'and measurement methods. It does not explain WHY someone has a particular '
                    'trait level — it describes WHAT the major dimensions of variation are.'
                ),
            },
            {
                'source_book': 'Grit — Angela Duckworth',
                'text': (
                    'The Big Five personality model identifies conscientiousness as the trait '
                    'most consistently associated with achievement across domains — more than '
                    'IQ, more than talent measures, more than socioeconomic background. But '
                    'conscientiousness itself can be decomposed into sub-facets: self-control '
                    '(the ability to resist temptation) and grit (the ability to sustain '
                    'passion and effort toward long-term goals). The model provides the '
                    'vocabulary for distinguishing between different flavors of achievement-'
                    'oriented personality — a taxonomy that guides where to intervene.'
                ),
            },
        ],
        'is_convergent': True,
        'should_extract': True,
        'expected_fb': {
            'is_summary': False,
            'route': 'FB',
            'name': 'Five-Factor Personality Taxonomy (OCEAN)',
            'definition': (
                'Human personality variation is organized along five empirically-derived '
                'dimensions — Openness, Conscientiousness, Extraversion, Agreeableness, '
                'Neuroticism — each representing a spectrum of behavioral, emotional, and '
                'cognitive tendencies. A descriptive model that classifies personality into '
                'broad trait domains, not a causal mechanism explaining why traits develop.'
            ),
            'mechanism': (
                'This is a DESCRIPTIVE MODEL — a classification system for human personality. '
                'The Big Five (OCEAN) emerged from factor analysis of personality descriptors '
                'across languages and cultures. It categorizes traits into five orthogonal '
                'dimensions, each with sub-facets. Cain describes the model as a landscape of '
                'variation (particularly the introversion-extraversion spectrum), Duckworth '
                'describes conscientiousness and its achievement-related sub-facets (self-control '
                'vs. grit). Neither claims a causal mechanism for WHY individuals differ — the '
                'model describes WHAT the dimensions ARE and HOW they relate to behavior.'
            ),
            'boundary': (
                'Applies as a descriptive framework for understanding personality at the '
                'population level. Fails for: (1) predicting any individual\'s specific '
                'behavior in a specific situation (traits predict averages, not instances); '
                '(2) cultures where the five-factor structure has not been validated; '
                '(3) capturing personality change over the lifespan (traits are moderately '
                'stable but not fixed). The model describes, it does not prescribe — knowing '
                'someone\'s OCEAN profile does not tell you what they SHOULD do.'
            ),
            'consequence': (
                'The model enables systematic study of personality-outcome relationships: '
                'conscientiousness predicts longevity and achievement, neuroticism predicts '
                'anxiety disorders, extraversion predicts leadership emergence. Organizations '
                'using personality assessments for hiring or development should understand '
                'that the Big Five describes tendencies, not destinies — and that situational '
                'factors often override trait dispositions.'
            ),
            'evidence_passages': [
                'Personality traits can be organized along five broad dimensions — Openness to experience, Conscientiousness, Extraversion, Agreeableness, and Neuroticism',
                'The model is descriptive: it classifies the landscape of human personality into five empirically-derived factors',
                'conscientiousness as the trait most consistently associated with achievement across domains',
                'The model provides the vocabulary for distinguishing between different flavors of achievement-oriented personality',
            ],
            'extraction_type': 'descriptive_model',
            'content_type': 'principle',
            'depth': 'cross-domain',
        },
        'rationale': (
            'NEW DESCRIPTIVE MODEL (D2234 completion: DM 9→12). '
            'Cain and Duckworth converge on the same descriptive model of personality '
            '(the Big Five/OCEAN taxonomy), using it for different purposes: Cain to '
            'describe the introversion-extraversion spectrum, Duckworth to decompose '
            'conscientiousness into achievement-relevant sub-facets. This is a DESCRIPTIVE '
            'MODEL because it is a classification system for personality traits — it '
            'tells us WHAT the major dimensions are and HOW they\'re organized, not WHY '
            'individuals differ.'
        ),
    },
    
    # ── DM-005: Porter's Five Forces ──
    {
        'id': 'CONV-052',
        'domain': 'strategy',
        'discipline': 'competitive strategy',
        'source_books': [
            'Understanding Michael Porter — Joan Magretta',
            'The Lean Startup — Eric Ries',
        ],
        'cluster_segments': [
            {
                'source_book': 'Understanding Michael Porter — Joan Magretta',
                'text': (
                    'Porter\'s five forces framework classifies the competitive pressures '
                    'that shape every industry: (1) threat of new entry — how easily can '
                    'new competitors enter? (2) bargaining power of suppliers — can suppliers '
                    'raise prices or reduce quality? (3) bargaining power of buyers — can '
                    'customers force prices down? (4) threat of substitute products — can '
                    'alternatives serve the same need? (5) rivalry among existing competitors '
                    '— how intense is the competition for market share? This is a descriptive '
                    'model: it categorizes the structural forces that determine industry '
                    'profitability, not a causal mechanism predicting any specific outcome.'
                ),
            },
            {
                'source_book': 'The Lean Startup — Eric Ries',
                'text': (
                    'Startups operate under extreme uncertainty, which makes traditional '
                    'strategy frameworks difficult to apply directly. But the five forces '
                    'still provide a useful diagnostic lens: a startup entering a market '
                    'with high supplier power and intense rivalry faces fundamentally '
                    'different challenges than one in a fragmented market with weak buyers. '
                    'The framework does not tell you what to do — it tells you which '
                    'competitive pressures exist, so you can decide where to focus. The '
                    'categories themselves are descriptive, not prescriptive.'
                ),
            },
        ],
        'is_convergent': True,
        'should_extract': True,
        'expected_fb': {
            'is_summary': False,
            'route': 'FB',
            'name': 'Five Forces — Competitive Pressure Taxonomy',
            'definition': (
                'Industry competition is structured by five categories of pressure: threat '
                'of new entry, supplier bargaining power, buyer bargaining power, threat of '
                'substitutes, and rivalry among existing competitors. Together, these five '
                'forces determine the profit potential of an industry. A descriptive model '
                'that classifies competitive pressures, not a causal mechanism.'
            ),
            'mechanism': (
                'This is a DESCRIPTIVE MODEL — a classification framework for competitive '
                'analysis. It categorizes industry pressures into five buckets with clear '
                'definitions and indicators for each. Magretta explains the framework as '
                'Porter intended it: a diagnostic tool for understanding industry structure. '
                'Ries acknowledges its descriptive value even in uncertain startup environments '
                'where traditional strategy tools break down. Neither presents the five forces '
                'as a causal mechanism — the model describes WHAT competitive pressures exist '
                'and HOW they relate to profitability, not WHY any specific firm succeeds '
                'or fails.'
            ),
            'boundary': (
                'Applies to industry-level analysis where the five-force structure is '
                'relatively stable. Fails for: (1) nascent industries where the forces '
                'have not yet crystallized; (2) platform/multi-sided markets where the '
                'boundaries between buyers, suppliers, and competitors blur; (3) industries '
                'shaped primarily by regulation rather than market forces. The framework '
                'describes structure, not dynamics — it captures a snapshot of competitive '
                'pressure at a point in time.'
            ),
            'consequence': (
                'The framework implies that strategy should focus on positioning the firm '
                'where the five forces are weakest — not on being "better" than competitors '
                'in an inherently unattractive industry. An industry with high rivalry, low '
                'entry barriers, powerful buyers, and strong substitutes will destroy value '
                'for even the best-run firms. Strategy begins with industry analysis, not '
                'operational excellence.'
            ),
            'evidence_passages': [
                'five forces framework classifies the competitive pressures that shape every industry',
                'This is a descriptive model: it categorizes the structural forces that determine industry profitability',
                'The framework does not tell you what to do — it tells you which competitive pressures exist',
                'The categories themselves are descriptive, not prescriptive',
            ],
            'extraction_type': 'descriptive_model',
            'content_type': 'principle',
            'depth': 'domain',
        },
        'rationale': (
            'NEW DESCRIPTIVE MODEL (D2234 completion: DM 9→12). '
            'Magretta and Ries converge on Porter\'s Five Forces as a descriptive model for '
            'classifying competitive pressures. Magretta explains the framework as Porter '
            'intended (industry structure analysis), Ries acknowledges its diagnostic value '
            'even in uncertain startup contexts. Both emphasize that it is a taxonomy of '
            'competitive forces — it categorizes WHAT pressures exist, not WHY specific '
            'outcomes occur. Essential for teaching S2 that strategic frameworks are often '
            'descriptive models, not causal mechanisms.'
        ),
    },
    
    # ── DM-006: Kano Model ──
    {
        'id': 'CONV-053',
        'domain': 'product management',
        'discipline': 'customer experience design',
        'source_books': [
            'Inspired — Marty Cagan',
            'Hooked — Nir Eyal',
        ],
        'cluster_segments': [
            {
                'source_book': 'Inspired — Marty Cagan',
                'text': (
                    'The Kano model classifies product features into three categories based '
                    'on how they affect customer satisfaction. Basic features (must-haves) '
                    'cause dissatisfaction when absent but do not increase satisfaction when '
                    'present — customers expect them. Performance features produce proportional '
                    'satisfaction: more is better, less is worse. Delighters (excitement '
                    'features) cause disproportionate satisfaction when present but no '
                    'dissatisfaction when absent — customers did not expect them. This is '
                    'a descriptive model: it categorizes features by their satisfaction '
                    'response curve, not by their technical implementation or cost.'
                ),
            },
            {
                'source_book': 'Hooked — Nir Eyal',
                'text': (
                    'Products succeed not by adding more features but by understanding which '
                    'type of value each feature creates. Some features are table stakes — '
                    'users expect them and are angry when they\'re missing but never grateful '
                    'when they work. Other features create delight precisely because they '
                    'were not expected. The skill is not in building all three types equally '
                    'but in recognizing that the same feature migrates from delighter to '
                    'performance to basic over time as competitors adopt it and customer '
                    'expectations shift.'
                ),
            },
        ],
        'is_convergent': True,
        'should_extract': True,
        'expected_fb': {
            'is_summary': False,
            'route': 'FB',
            'name': 'Kano Model — Feature Satisfaction Taxonomy',
            'definition': (
                'Product features can be classified into three categories based on their '
                'satisfaction response: basic features (must-haves that prevent dissatisfaction), '
                'performance features (proportional satisfaction), and delighters (unexpected '
                'features that create disproportionate satisfaction). Features migrate from '
                'delighter → performance → basic over time as expectations rise. A descriptive '
                'model, not a causal mechanism.'
            ),
            'mechanism': (
                'This is a DESCRIPTIVE MODEL — a classification system for product features '
                'based on their satisfaction dynamics. The model categorizes features into '
                'three types defined by their asymmetric satisfaction curves: basic features '
                'have a floor (dissatisfaction when absent) but no ceiling; performance features '
                'are linear; delighters have a ceiling but no floor. Cagan describes the model '
                'as a product management diagnostic, Eyal extends it with the time-migration '
                'dynamic (features shift categories as expectations evolve). Neither claims '
                'a causal mechanism — the model describes WHAT types of feature-satisfaction '
                'relationships exist and HOW they change over time.'
            ),
            'boundary': (
                'Applies to products and services where customer satisfaction can be measured '
                'and features can be categorized. Fails for: (1) completely novel product '
                'categories where "basic" expectations don\'t yet exist; (2) products where '
                'satisfaction is driven by factors other than features (brand, network effects, '
                'ecosystem lock-in); (3) B2B purchasing where the user and the buyer are '
                'different people with different satisfaction criteria. The model is a lens, '
                'not a formula — it helps you think about features, not calculate what to build.'
            ),
            'consequence': (
                'The model implies that product teams should invest asymmetrically: ensure '
                'basic features work flawlessly (but don\'t over-invest), compete on performance '
                'features (where more IS better), and selectively invest in delighters (where '
                'ROI is highest but temporary). It also predicts that yesterday\'s delighter '
                'becomes today\'s performance feature and tomorrow\'s basic expectation — '
                'continuous innovation is structural, not optional.'
            ),
            'evidence_passages': [
                'Basic features (must-haves) cause dissatisfaction when absent but do not increase satisfaction when present',
                'Delighters (excitement features) cause disproportionate satisfaction when present but no dissatisfaction when absent',
                'the same feature migrates from delighter to performance to basic over time as competitors adopt it',
                'The skill is not in building all three types equally but in recognizing that the same feature migrates',
            ],
            'extraction_type': 'descriptive_model',
            'content_type': 'principle',
            'depth': 'domain',
        },
        'rationale': (
            'NEW DESCRIPTIVE MODEL (D2234 completion: DM 9→12). '
            'Cagan and Eyal converge on the Kano model as a descriptive taxonomy for '
            'classifying product features by their satisfaction dynamics. Cagan describes '
            'the three categories and their asymmetric curves, Eyal adds the temporal '
            'migration dynamic (features shift categories over time). Both present it as '
            'a classification framework — it tells you WHAT types of features exist and '
            'HOW their satisfaction impact differs, not WHY any specific feature produces '
            'satisfaction. Essential for teaching S2 that product/design taxonomies are '
            'valid descriptive models.'
        ),
    },
]

for ex in new_examples:
    examples.append(ex)
    print(f'  Added {ex["id"]}: {ex["expected_fb"]["name"]} (descriptive_model)')

# Update meta
data['meta']['example_count'] = len(examples)
data['meta']['total_examples'] = len(examples)
data['meta']['version'] = '4.4'
data['meta']['notes'] = 'D2234 completion: 3 descriptive_model examples added (DM 9→12)'

# Save
tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, dir='config/golden')
yaml.dump(data, tmp, allow_unicode=True, sort_keys=False, width=120)
tmp.flush()
os.fsync(tmp.fileno())
tmp.close()
os.replace(tmp.name, 'config/golden/stage2_fewshot_convergent.yaml')

# Validate
result = subprocess.run(['python3', 'pipeline/golden_validate.py'], capture_output=True, text=True)
print(f'\n{result.stdout.strip()}')
if result.stderr:
    for line in result.stderr.strip().split('\n'):
        if any(x in line for x in ['NON_VERBATIM', 'MISSING', 'FAIL']):
            print(f'  {line[:120]}')

# Type distribution
tc = Counter()
for ex in examples:
    ef = ex.get('expected_fb', {})
    fbs = ef if isinstance(ef, list) else [ef]
    for fb in fbs:
        if isinstance(fb, dict) and fb.get('extraction_type'):
            tc[fb['extraction_type']] += 1
print(f'\n── TYPE DISTRIBUTION ──')
for t in ['causal_mechanism', 'empirical_pattern', 'normative_heuristic', 'descriptive_model']:
    c = tc.get(t, 0)
    target = ' ✅' if c >= 12 else f' (need {12-c} more)'
    print(f'  {t}: {c}{target}')
print(f'  Total FBs: {sum(tc.values())}')
print(f'  Total examples: {len(examples)}')
