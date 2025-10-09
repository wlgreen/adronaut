"""
Insights Selector with Deterministic Scoring Rubric
Selects top k insights from candidates based on evidence quality and actionability
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def score_insight(insight: Dict[str, Any]) -> int:
    """
    Deterministic scoring rubric for insight quality (no external data)

    Scoring rules:
    - +2 if evidence_refs present
    - +2 if data_support == 'strong', +1 if 'moderate'
    - +1 if expected_effect has both direction AND magnitude
    - +1 if single primary_lever is targeted
    - -1 if data_support='weak' without learn/test action

    Args:
        insight: Insight dictionary with required fields

    Returns:
        int score from 0-100
    """
    score = 0

    # Evidence quality (max +4)
    if insight.get('evidence_refs') and len(insight.get('evidence_refs', [])) > 0:
        score += 2
        logger.debug(f"[SCORE] +2 for evidence_refs: {insight.get('evidence_refs')}")

    data_support = insight.get('data_support', '')
    if data_support == 'strong':
        score += 2
        logger.debug(f"[SCORE] +2 for strong data_support")
    elif data_support == 'moderate':
        score += 1
        logger.debug(f"[SCORE] +1 for moderate data_support")

    # Expected effect specificity (max +1)
    expected_effect = insight.get('expected_effect', {})
    if expected_effect.get('direction') and expected_effect.get('magnitude'):
        score += 1
        logger.debug(f"[SCORE] +1 for specific expected_effect: {expected_effect.get('direction')} / {expected_effect.get('magnitude')}")

    # Single lever focus (max +1)
    primary_lever = insight.get('primary_lever', '')
    if primary_lever in ['audience', 'creative', 'budget', 'bidding', 'funnel']:
        score += 1
        logger.debug(f"[SCORE] +1 for valid primary_lever: {primary_lever}")

    # Penalize insufficient evidence without learn/test action (max -1)
    if data_support == 'weak':
        proposed_action = insight.get('proposed_action', '').lower()
        learn_test_keywords = ['pilot', 'test', 'experiment', 'trial', 'a/b', 'validate']

        if not any(kw in proposed_action for kw in learn_test_keywords):
            score -= 1
            logger.warning(f"[SCORE] -1 for weak data_support without learn/test action: {proposed_action}")
        else:
            logger.debug(f"[SCORE] No penalty - weak support with learn/test action: {proposed_action}")

    # Normalize to 0-100 range (max possible score is ~8, scale up)
    normalized_score = int(min(max(score * 12.5, 0), 100))  # Scale: 8 * 12.5 = 100

    logger.info(f"[SCORE] Final score: {normalized_score} (raw: {score}) for insight: {insight.get('insight', 'N/A')[:50]}...")

    return normalized_score


def select_top_insights(candidates: List[Dict[str, Any]], k: int = 3) -> List[Dict[str, Any]]:
    """
    Select top k insights using deterministic rubric

    Args:
        candidates: List of insight candidate dictionaries
        k: Number of top insights to select (default 3)

    Returns:
        List of top k insights with impact_rank and impact_score added
    """
    if not candidates:
        logger.warning("[SELECT] No candidates provided, returning empty list")
        return []

    logger.info(f"[SELECT] Scoring {len(candidates)} insight candidates...")

    # Score all candidates
    scored = []
    for i, candidate in enumerate(candidates):
        score = score_insight(candidate)
        scored.append((score, i, candidate))  # (score, original_index, insight)
        logger.debug(f"[SELECT] Candidate {i}: score={score}")

    # Sort by score (descending), use original index as tiebreaker for determinism
    scored.sort(key=lambda x: (-x[0], x[1]))

    # Select top k
    top_k = []
    for rank, (score, original_idx, insight) in enumerate(scored[:k], 1):
        insight['impact_rank'] = rank
        insight['impact_score'] = score
        top_k.append(insight)
        logger.info(f"[SELECT] Rank {rank}: score={score}, insight={insight.get('insight', 'N/A')[:60]}...")

    logger.info(f"[SELECT] Selected {len(top_k)} insights with scores: {[i['impact_score'] for i in top_k]}")

    return top_k


def validate_insight_structure(insight: Dict[str, Any]) -> bool:
    """
    Validate that an insight has all required fields

    Args:
        insight: Insight dictionary to validate

    Returns:
        bool indicating if insight is valid
    """
    required_fields = [
        'insight',
        'hypothesis',
        'proposed_action',
        'primary_lever',
        'expected_effect',
        'confidence',
        'data_support',
        'evidence_refs',
        'contrastive_reason'
    ]

    missing_fields = []
    for field in required_fields:
        if field not in insight or insight[field] is None:
            missing_fields.append(field)

    if missing_fields:
        logger.error(f"[VALIDATE] Missing required fields: {missing_fields}")
        return False

    # Validate nested expected_effect
    expected_effect = insight.get('expected_effect', {})
    if not expected_effect.get('direction') or not expected_effect.get('metric'):
        logger.error(f"[VALIDATE] expected_effect missing direction or metric: {expected_effect}")
        return False

    # Validate lever
    if insight.get('primary_lever') not in ['audience', 'creative', 'budget', 'bidding', 'funnel']:
        logger.error(f"[VALIDATE] Invalid primary_lever: {insight.get('primary_lever')}")
        return False

    # Validate data_support
    if insight.get('data_support') not in ['strong', 'moderate', 'weak']:
        logger.error(f"[VALIDATE] Invalid data_support: {insight.get('data_support')}")
        return False

    # Validate confidence range
    confidence = insight.get('confidence', 0)
    if not (0 <= confidence <= 1):
        logger.error(f"[VALIDATE] Invalid confidence (must be 0-1): {confidence}")
        return False

    logger.debug(f"[VALIDATE] Insight structure valid")
    return True


def validate_confidence_alignment(insight: Dict[str, Any]) -> bool:
    """
    Ensure confidence aligns with data support

    Args:
        insight: Insight dictionary to validate

    Returns:
        bool indicating if confidence/support are aligned
    """
    support = insight.get('data_support')
    confidence = insight.get('confidence', 0)

    # Rule: weak support must have confidence ≤ 0.4
    if support == 'weak' and confidence > 0.4:
        logger.warning(f"[VALIDATE] Weak data support with high confidence: {confidence} (should be ≤0.4)")
        return False

    # Rule: weak support must propose learn/test action
    if support == 'weak':
        proposed_action = insight.get('proposed_action', '').lower()
        learn_test_keywords = ['pilot', 'test', 'experiment', 'trial', 'a/b', 'validate']

        if not any(kw in proposed_action for kw in learn_test_keywords):
            logger.warning(f"[VALIDATE] Weak support without learn/test action: {proposed_action}")
            return False

    logger.debug(f"[VALIDATE] Confidence/support alignment valid: support={support}, confidence={confidence}")
    return True


def count_data_support_distribution(insights: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count distribution of data_support levels

    Args:
        insights: List of insights

    Returns:
        dict with counts for 'strong', 'moderate', 'weak'
    """
    distribution = {'strong': 0, 'moderate': 0, 'weak': 0}

    for insight in insights:
        support = insight.get('data_support', 'unknown')
        if support in distribution:
            distribution[support] += 1

    logger.debug(f"[STATS] Data support distribution: {distribution}")
    return distribution


def calculate_insufficient_evidence_rate(insights: List[Dict[str, Any]]) -> float:
    """
    Calculate rate of insights with insufficient evidence

    Args:
        insights: List of insights

    Returns:
        float rate (0-1) of insights with weak data support
    """
    if not insights:
        return 0.0

    weak_count = sum(1 for i in insights if i.get('data_support') == 'weak')
    rate = weak_count / len(insights)

    logger.debug(f"[STATS] Insufficient evidence rate: {rate:.2%} ({weak_count}/{len(insights)})")
    return rate
