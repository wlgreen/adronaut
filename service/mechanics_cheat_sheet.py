"""
Performance Mechanics Cheat Sheet
Maps metrics to primary/secondary levers for causal reasoning in ad optimization
"""

# Universal patterns (platform-agnostic) - exported separately for use in prompts
UNIVERSAL_MECHANICS = """
## Universal Performance Patterns (Platform-Agnostic)

**Pattern 1: Efficiency Outliers**
Identify dimension values (segments) with significantly better efficiency metrics (2x+ vs average).
- Lever: budget (reallocate to winners)
- Example: "Segment X achieves 2.5x ROAS vs portfolio average → shift budget from underperformers"
- Detection: Sort by efficiency metric, find top 10-20%, check if >2x better than median

**Pattern 2: Waste Elimination**
Find segments with poor efficiency + high cost (bottom performers consuming significant budget).
- Lever: budget/audience (pause or reduce spend)
- Example: "15 keywords drove 0 orders with $78 wasted spend → pause immediately"
- Detection: Filter segments with efficiency <50% of average AND cost >10% of total

**Pattern 3: Comparative Gap Closure**
If current_metric < benchmark/suggested_metric → missed opportunity.
If current_metric > benchmark → potential waste/risk.
- Lever: bidding (if bid-related) or budget (if spend-related)
- Example: "Current bids 42% below suggested median across all keywords → missing volume opportunity"
- Detection: Calculate (current - suggested) / suggested for all segments, identify systematic gaps

**Pattern 4: Volume + Efficiency Matrix**
Classify segments by efficiency (high/low) × volume (high/low):
- High efficiency + Low volume = **Scale opportunity** (increase budget/bids)
- High efficiency + High volume = **Proven winner** (protect/maintain)
- Low efficiency + High volume = **Major waste** (reduce/pause urgently)
- Low efficiency + Low volume = **Test or kill** (experiment with small budget or pause)

**Pattern 5: Segment Concentration (Pareto Analysis)**
Calculate what % of segments drive 80% of performance.
- If >60% performance concentrated in <20% segments → reallocation opportunity
- Lever: budget
- Example: "Top 3 keywords (12% of total) drive 63% of orders → reallocate from long tail"
- Detection: Sort segments by target metric (orders, revenue, etc), calculate cumulative %

**Pattern 6: Metric Correlation Analysis**
Check relationship between metrics:
- Negative correlation (cost ↑ efficiency ↓) = Normal, expected
- Positive correlation = Anomaly worth investigating
- Use for contrastive reasoning ("Why X performs despite high cost")

**Pattern 7: Low-Data Segments**
Segments with <10 data points → insufficient for confident decisions.
- Lever: any (but action = experiment/test)
- Example: "Campaign Z has only 3 days of scattered data → run 14-day structured test with $500 budget cap"
- Detection: Count data points per segment, flag if <10

---

## Lever Selection for Universal Patterns

**Budget lever** when:
- Reallocating between proven segments (Pattern 1, 5)
- Volume opportunity exists with good efficiency (Pattern 4)
- Pausing wasteful spend (Pattern 2)

**Bidding lever** when:
- Comparative gap in bid/price metrics (Pattern 3)
- Cost inefficiency with auction dynamics
- Competition-related opportunities

**Audience lever** when:
- Targeting precision issue (broad match, geo spread)
- Quality mismatch (wrong segment targeting)
- Overlapping/redundant segments

**Creative lever** when:
- Message mismatch evident in engagement data
- A/B test results show creative impact
- High impressions but low click-through

**Funnel lever** when:
- High click but low conversion pattern
- Checkout/landing page issues indicated
- Post-click journey problems
"""

MECHANICS_CHEAT_SHEET = """
## Performance Mechanics Guide

**CTR (Click-Through Rate):**
- Primary levers: creative (headline, image, hook), audience (targeting precision)
- Secondary: bidding (ad position impact)
- Typical actions: A/B test headlines, refine audience targeting, adjust ad creative format

**Conversion Rate:**
- Primary levers: funnel (landing page UX, checkout flow), creative (message-match with landing page)
- Secondary: audience (intent alignment, qualification)
- Typical actions: Optimize landing page UX, improve ad-to-page message match, qualify audience better

**CPA (Cost Per Acquisition):**
- Primary levers: bidding (bid strategy, bid amount), audience (quality targeting, LTV segments)
- Secondary: creative (ad relevance score impact on cost)
- Typical actions: Adjust bid strategy, refine audience to higher-intent users, improve ad quality score

**ROAS (Return on Ad Spend):**
- Primary levers: audience (high-LTV segments, purchase propensity), budget (allocation efficiency across channels)
- Secondary: funnel (upsell/cross-sell optimization), creative (value proposition clarity)
- Typical actions: Shift budget to high-ROAS segments, implement upsell tactics, clarify value prop

**Engagement Rate (likes, shares, comments):**
- Primary levers: creative (format, hook, emotional appeal), audience (interest alignment)
- Secondary: budget (frequency management to avoid fatigue)
- Typical actions: Test video vs image, align content with audience interests, manage frequency caps

**Impression Share:**
- Primary levers: budget (daily/lifetime budget size), bidding (competitiveness)
- Secondary: audience (pool size, competition level)
- Typical actions: Increase budget, raise bids in key geos/times, expand audience (carefully)

**Cost Per Click (CPC):**
- Primary levers: bidding (manual vs auto, bid amounts), creative (ad quality/relevance score)
- Secondary: audience (competition level in segment)
- Typical actions: Optimize ad relevance score, switch bid strategy, target less competitive segments

**Brand Lift:**
- Primary levers: creative (messaging, brand storytelling), audience (reach + frequency balance)
- Secondary: budget (sufficient exposure for recall), funnel (consistent brand experience)
- Typical actions: Test brand messaging variants, optimize reach/frequency, ensure cross-channel consistency

---

## Universal Performance Patterns (Platform-Agnostic)

**Pattern 1: Efficiency Outliers**
Identify dimension values (segments) with significantly better efficiency metrics (2x+ vs average).
- Lever: budget (reallocate to winners)
- Example: "Segment X achieves 2.5x ROAS vs portfolio average → shift budget from underperformers"
- Detection: Sort by efficiency metric, find top 10-20%, check if >2x better than median

**Pattern 2: Waste Elimination**
Find segments with poor efficiency + high cost (bottom performers consuming significant budget).
- Lever: budget/audience (pause or reduce spend)
- Example: "15 keywords drove 0 orders with $78 wasted spend → pause immediately"
- Detection: Filter segments with efficiency <50% of average AND cost >10% of total

**Pattern 3: Comparative Gap Closure**
If current_metric < benchmark/suggested_metric → missed opportunity.
If current_metric > benchmark → potential waste/risk.
- Lever: bidding (if bid-related) or budget (if spend-related)
- Example: "Current bids 42% below suggested median across all keywords → missing volume opportunity"
- Detection: Calculate (current - suggested) / suggested for all segments, identify systematic gaps

**Pattern 4: Volume + Efficiency Matrix**
Classify segments by efficiency (high/low) × volume (high/low):
- High efficiency + Low volume = **Scale opportunity** (increase budget/bids)
- High efficiency + High volume = **Proven winner** (protect/maintain)
- Low efficiency + High volume = **Major waste** (reduce/pause urgently)
- Low efficiency + Low volume = **Test or kill** (experiment with small budget or pause)

**Pattern 5: Segment Concentration (Pareto Analysis)**
Calculate what % of segments drive 80% of performance.
- If >60% performance concentrated in <20% segments → reallocation opportunity
- Lever: budget
- Example: "Top 3 keywords (12% of total) drive 63% of orders → reallocate from long tail"
- Detection: Sort segments by target metric (orders, revenue, etc), calculate cumulative %

**Pattern 6: Metric Correlation Analysis**
Check relationship between metrics:
- Negative correlation (cost ↑ efficiency ↓) = Normal, expected
- Positive correlation = Anomaly worth investigating
- Use for contrastive reasoning ("Why X performs despite high cost")

**Pattern 7: Low-Data Segments**
Segments with <10 data points → insufficient for confident decisions.
- Lever: any (but action = experiment/test)
- Example: "Campaign Z has only 3 days of scattered data → run 14-day structured test with $500 budget cap"
- Detection: Count data points per segment, flag if <10

---

## Action Selection Rules

**Rule 1: Single Primary Lever**
Each recommendation MUST target exactly ONE primary lever. Multi-lever actions are harder to measure and optimize.

**Rule 2: Evidence-Based Lever Selection**
- If you have funnel dropout data → funnel lever
- If you have creative performance data → creative lever
- If you have audience segment data → audience lever
- If you have cost/bid data → bidding lever
- If you have allocation data → budget lever

**Rule 3: When Evidence is Weak (data_support = "weak")**
Prefer "learn/test" actions:
- "Run 3-day pilot in single geo with 10% budget"
- "A/B test 2 creative variants for 5 days"
- "Test new audience segment with $500 budget cap"
- "Trial bid strategy change in lowest-spend campaign"

**Rule 4: Expected Effect Estimation**
- Small: 5-15% improvement
- Medium: 15-30% improvement
- Large: >30% improvement
- Base on: historical benchmarks, similar case studies, or conservative estimates when data is limited

---

## Common Anti-Patterns to Avoid

❌ Multi-lever recommendations: "Improve creative AND bidding AND audience"
✅ Single lever: "Improve creative by testing video format vs static image"

❌ Vague effects: "Will likely improve performance"
✅ Specific effects: "Expected to increase CTR by 15-25% (medium impact)"

❌ High confidence without data: "This will definitely work" with data_support="weak"
✅ Honest uncertainty: "Hypothesis worth testing - propose pilot with 10% budget" with data_support="weak", confidence=0.3

❌ No contrastive reasoning: Just states the recommendation
✅ With contrast: "Why this (video outperforms static in mobile feed). Why not alternative (carousel tested poorly in previous campaign)"
"""


def get_mechanics_for_metric(metric: str) -> dict:
    """
    Get lever mapping for a specific metric

    Args:
        metric: Performance metric name (e.g., 'CTR', 'conversion_rate', 'ROAS')

    Returns:
        dict with primary_levers, secondary_levers, typical_actions
    """
    metric_upper = metric.upper().replace('_', ' ').replace('-', ' ')

    mechanics_map = {
        'CTR': {
            'primary_levers': ['creative', 'audience'],
            'secondary_levers': ['bidding'],
            'typical_actions': [
                'A/B test headlines',
                'Refine audience targeting',
                'Adjust ad creative format'
            ]
        },
        'CONVERSION RATE': {
            'primary_levers': ['funnel', 'creative'],
            'secondary_levers': ['audience'],
            'typical_actions': [
                'Optimize landing page UX',
                'Improve ad-to-page message match',
                'Qualify audience better'
            ]
        },
        'CPA': {
            'primary_levers': ['bidding', 'audience'],
            'secondary_levers': ['creative'],
            'typical_actions': [
                'Adjust bid strategy',
                'Refine audience to higher-intent users',
                'Improve ad quality score'
            ]
        },
        'ROAS': {
            'primary_levers': ['audience', 'budget'],
            'secondary_levers': ['funnel', 'creative'],
            'typical_actions': [
                'Shift budget to high-ROAS segments',
                'Implement upsell tactics',
                'Clarify value prop'
            ]
        },
        'ENGAGEMENT RATE': {
            'primary_levers': ['creative', 'audience'],
            'secondary_levers': ['budget'],
            'typical_actions': [
                'Test video vs image',
                'Align content with audience interests',
                'Manage frequency caps'
            ]
        }
    }

    return mechanics_map.get(metric_upper, {
        'primary_levers': ['creative', 'audience'],
        'secondary_levers': ['budget', 'bidding', 'funnel'],
        'typical_actions': ['Analyze metric-specific data', 'Run controlled experiment']
    })


def validate_lever_choice(lever: str, metric: str = None) -> bool:
    """
    Validate if a lever choice is valid

    Args:
        lever: Chosen lever (audience, creative, budget, bidding, funnel)
        metric: Optional metric to check if lever is appropriate

    Returns:
        bool indicating if lever is valid
    """
    valid_levers = {'audience', 'creative', 'budget', 'bidding', 'funnel'}

    if lever not in valid_levers:
        return False

    if metric:
        mechanics = get_mechanics_for_metric(metric)
        if mechanics and lever not in (mechanics.get('primary_levers', []) + mechanics.get('secondary_levers', [])):
            # Lever not optimal for this metric, but not invalid
            return True

    return True
