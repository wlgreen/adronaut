"""
Predefined Insight Directions Framework

Defines strategic insight categories that the LLM evaluates and fills
only when supported by data evidence.
"""

INSIGHT_DIRECTIONS = [
    {
        "id": "outlier_scaling",
        "name": "High-Performer Scaling Opportunity",
        "description": "Identify segments/campaigns with 2x+ better efficiency than average → increase budget allocation",
        "primary_lever": "budget",
        "when_applicable": "When data shows clear performance outliers (2x+ difference)",
        "data_requirements": ["efficiency_metrics", "segment_performance", "baseline_average"]
    },
    {
        "id": "waste_elimination",
        "name": "Budget Waste Reduction",
        "description": "Identify poor-performing segments with high spend → reduce or pause budget",
        "primary_lever": "budget",
        "when_applicable": "When segments show poor efficiency + significant spend",
        "data_requirements": ["efficiency_metrics", "cost_metrics", "segment_performance"]
    },
    {
        "id": "audience_refinement",
        "name": "Audience Targeting Refinement",
        "description": "Narrow or expand audience based on demographic/geographic performance patterns",
        "primary_lever": "audience",
        "when_applicable": "When geographic/demographic data shows clear patterns",
        "data_requirements": ["geographic_insights", "demographic_data", "performance_by_segment"]
    },
    {
        "id": "creative_optimization",
        "name": "Creative/Messaging Optimization",
        "description": "Adjust creative themes, messaging, or formats based on engagement patterns",
        "primary_lever": "creative",
        "when_applicable": "When creative performance data is available",
        "data_requirements": ["creative_performance", "engagement_metrics", "message_themes"]
    },
    {
        "id": "channel_rebalancing",
        "name": "Channel Mix Rebalancing",
        "description": "Shift budget between channels based on relative performance",
        "primary_lever": "budget",
        "when_applicable": "When multi-channel data shows performance differences",
        "data_requirements": ["channel_performance", "cross_channel_metrics"]
    },
    {
        "id": "temporal_optimization",
        "name": "Timing & Schedule Optimization",
        "description": "Adjust dayparting, days of week, or seasonal timing based on performance patterns",
        "primary_lever": "bidding",
        "when_applicable": "When temporal performance data is available",
        "data_requirements": ["temporal_patterns", "time_based_performance"]
    },
    {
        "id": "bidding_strategy",
        "name": "Bidding Strategy Adjustment",
        "description": "Modify bid amounts or strategies based on cost efficiency",
        "primary_lever": "bidding",
        "when_applicable": "When cost/efficiency data suggests bid adjustments",
        "data_requirements": ["cost_metrics", "efficiency_metrics", "bidding_data"]
    },
    {
        "id": "funnel_optimization",
        "name": "Conversion Funnel Improvement",
        "description": "Address funnel drop-offs or optimize conversion steps",
        "primary_lever": "funnel",
        "when_applicable": "When funnel/conversion data is available",
        "data_requirements": ["conversion_metrics", "funnel_data", "drop_off_points"]
    },
    {
        "id": "test_and_learn",
        "name": "Structured Learning Experiment",
        "description": "Design experiments to gather data in areas with insufficient evidence",
        "primary_lever": "audience",  # Can vary
        "when_applicable": "When data is sparse/insufficient for confident decisions",
        "data_requirements": ["data_completeness_assessment"]
    },
    {
        "id": "concentration_play",
        "name": "Concentration Strategy",
        "description": "Focus budget on top performers when 80/20 rule applies (top 20% drive >60% results)",
        "primary_lever": "budget",
        "when_applicable": "When top performers show strong concentration",
        "data_requirements": ["segment_performance", "concentration_metrics"]
    }
]


def get_insight_directions_prompt() -> str:
    """Generate prompt section describing insight directions"""

    directions_text = "\n".join([
        f"""
{i+1}. **{d['name']}** (ID: {d['id']}, Lever: {d['primary_lever']})
   - {d['description']}
   - When applicable: {d['when_applicable']}
   - Required data: {', '.join(d['data_requirements'])}
"""
        for i, d in enumerate(INSIGHT_DIRECTIONS)
    ])

    return f"""
**PREDEFINED INSIGHT DIRECTIONS:**

Evaluate the following {len(INSIGHT_DIRECTIONS)} insight directions. For EACH direction:
- Check if you have the required data to support it
- If YES and evidence is strong: Fill in the complete insight structure
- If NO or evidence is weak: Return null for that direction OR convert to test_and_learn experiment

{directions_text}

**CRITICAL RULES:**
1. ONLY fill directions where you have actual supporting data
2. Use "null" or omit directions that don't apply to this dataset
3. Each filled direction must include ALL 11 required insight fields
4. Prioritize directions with strongest data support
5. Can use same direction multiple times if targeting different segments (e.g., outlier_scaling for multiple high performers)
"""


def filter_empty_insights(insights_by_direction: dict) -> list:
    """
    Filter out null/empty insights from LLM response

    Args:
        insights_by_direction: Dict mapping direction IDs to insight objects or null

    Returns:
        List of valid insight objects
    """
    valid_insights = []

    for direction_id, insight in insights_by_direction.items():
        # Skip null, empty, or placeholder insights
        if insight is None:
            continue
        if not isinstance(insight, dict):
            continue
        if insight.get('insight') in [None, '', 'N/A', 'Not applicable', 'Insufficient data']:
            continue
        if insight.get('data_support') == 'none':
            continue

        # Add direction metadata
        insight['direction_id'] = direction_id

        # Find direction metadata
        direction_meta = next((d for d in INSIGHT_DIRECTIONS if d['id'] == direction_id), None)
        if direction_meta:
            insight['direction_name'] = direction_meta['name']

        valid_insights.append(insight)

    return valid_insights


def get_direction_coverage(insights: list) -> dict:
    """
    Calculate which directions were filled vs empty

    Args:
        insights: List of insight objects with direction_id

    Returns:
        Dict with coverage statistics
    """
    filled_directions = set(i.get('direction_id') for i in insights if i.get('direction_id'))
    all_direction_ids = set(d['id'] for d in INSIGHT_DIRECTIONS)

    return {
        'total_directions': len(INSIGHT_DIRECTIONS),
        'filled_directions': len(filled_directions),
        'coverage_rate': len(filled_directions) / len(INSIGHT_DIRECTIONS),
        'filled_ids': list(filled_directions),
        'empty_ids': list(all_direction_ids - filled_directions)
    }
