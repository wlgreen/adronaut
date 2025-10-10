#!/usr/bin/env python3
"""
Test sparse data insights generation

Validates that the LLM generates actionable insights and experiment proposals
even when provided with minimal data (e.g., only channel information, no metrics).
"""

import asyncio
import pytest
from gemini_orchestrator import GeminiOrchestrator


@pytest.mark.asyncio
async def test_insights_generated_from_sparse_data():
    """Test that LLM generates insights even with minimal data"""
    # Setup: Minimal features (only channel detected, everything else insufficient)
    sparse_features = {
        "metrics": {"campaigns": "insufficient_evidence", "data_completeness": "minimal"},
        "channels": ["Google Ads"],
        "messaging": "insufficient_evidence",
        "objectives": "insufficient_evidence",
        "budget_data": {"total_budget": "insufficient_evidence", "by_campaign": "insufficient_evidence"},
        "target_audience": {"segments": "insufficient_evidence", "data_source": "insufficient_evidence"},
        "geographic_insights": "insufficient_evidence",
        "creative_performance": "insufficient_evidence",
        "recommendations_from_data": "insufficient_evidence"
    }

    # Execute
    orchestrator = GeminiOrchestrator()
    result = await orchestrator.generate_insights(sparse_features)

    # Assert: Should generate exactly 3 insights
    assert "insights" in result, "Result should contain 'insights' key"
    insights = result["insights"]
    assert len(insights) == 3, f"Should generate exactly 3 insights, got {len(insights)}"

    # Assert: At least 1 insight should have weak data support
    weak_insights = [i for i in insights if i.get("data_support") == "weak"]
    assert len(weak_insights) >= 1, f"Should have at least 1 weak insight, got {len(weak_insights)}"

    print(f"\n✅ Generated {len(insights)} insights")
    print(f"   └─ {len(weak_insights)} with weak data support")

    # Validate each weak insight has experiment proposal with required elements
    for idx, insight in enumerate(weak_insights, 1):
        action = insight.get("proposed_action", "").lower()

        print(f"\n📊 Weak Insight #{idx}:")
        print(f"   Insight: {insight.get('insight', '')[:80]}...")
        print(f"   Proposed Action: {action[:100]}...")

        # Check for learning keywords
        learning_keywords = ["pilot", "test", "experiment", "a/b", "validate", "trial"]
        has_learning_keyword = any(kw in action for kw in learning_keywords)
        assert has_learning_keyword, f"Weak insight must contain learning keyword, got: {action}"
        print(f"   ✓ Contains learning keyword")

        # Check for budget cap
        has_budget = "$" in action and "budget" in action
        assert has_budget, f"Weak insight must include budget cap, got: {action}"
        print(f"   ✓ Includes budget cap")

        # Check for timeline
        timeline_indicators = ["day", "week", "month"]
        has_timeline = any(t in action for t in timeline_indicators)
        assert has_timeline, f"Weak insight must include timeline, got: {action}"
        print(f"   ✓ Includes timeline")

        # Check for success metrics (including verb forms like "measuring")
        metrics_keywords = ["measur", "track", "monitor", "metric"]  # Partial matches for verb forms
        has_metrics = any(m in action for m in metrics_keywords)
        assert has_metrics, f"Weak insight must include success metrics, got: {action}"
        print(f"   ✓ Includes success metrics")

    # Assert: All insights have required 11 fields
    required_fields = [
        "insight", "hypothesis", "proposed_action", "primary_lever",
        "expected_effect", "confidence", "data_support", "evidence_refs",
        "contrastive_reason", "impact_rank", "impact_score"
    ]

    for idx, insight in enumerate(insights, 1):
        missing_fields = [f for f in required_fields if f not in insight]
        assert not missing_fields, f"Insight #{idx} missing fields: {missing_fields}"

    print(f"\n✅ All insights have required 11 fields")
    print(f"✅ All weak insights include experiment proposals")


@pytest.mark.asyncio
async def test_experiment_proposal_format():
    """Test that experiment proposals are well-structured and actionable"""
    sparse_features = {
        "metrics": {"campaigns": "insufficient_evidence", "data_completeness": "minimal"},
        "channels": ["Facebook Ads", "Google Ads"],
        "messaging": "insufficient_evidence",
        "target_audience": {"segments": "insufficient_evidence"},
    }

    orchestrator = GeminiOrchestrator()
    result = await orchestrator.generate_insights(sparse_features)
    insights = result["insights"]

    # Find at least one weak insight with experiment
    weak_insights = [i for i in insights if i.get("data_support") == "weak"]
    assert len(weak_insights) > 0, "Should have at least one weak insight"

    experiment_insight = weak_insights[0]
    action = experiment_insight["proposed_action"]

    print(f"\n🧪 Experiment Proposal Analysis:")
    print(f"   Proposed Action: {action}")

    # Validate structure
    assert len(action) > 50, "Experiment proposal should be detailed (>50 chars)"
    assert ":" in action or "." in action, "Should have proper sentence structure"

    # Check expected_effect mentions learning or data collection
    # Look in both the action and expected_effect fields
    effect = experiment_insight["expected_effect"]
    effect_text = f"{effect.get('metric', '')} {effect.get('range', '')}".lower()
    action_text = action.lower()
    combined_text = f"{effect_text} {action_text}"
    learning_indicators = ["data", "learn", "identify", "baseline", "measure", "validate", "track", "monitor"]

    has_learning_focus = any(ind in combined_text for ind in learning_indicators)
    print(f"   Expected Effect: {effect_text}")
    print(f"   ✓ Focuses on learning: {has_learning_focus}")

    assert has_learning_focus, f"Weak insight should focus on learning, got effect: {effect_text}"


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_insights_generated_from_sparse_data())
    asyncio.run(test_experiment_proposal_format())
    print("\n✅ All sparse data tests passed!")
