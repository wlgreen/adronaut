"""
Sanity Reflection Gate
LLM-based final validation before outputting patches
Reviews proposed actions for logical coherence, risk level, and evidence support
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SanityGate:
    """LLM-based final validation before output"""

    REFLECTION_PROMPT_TEMPLATE = """
You are a Marketing Strategy Reviewer conducting a final safety check.

Review the following proposed strategy patch:

{patch_json}

**Your Task:**
Evaluate each action in the patch for:
1. **Logical Coherence:** Does the action logically follow from available evidence?
2. **Realistic Outcomes:** Are expected effects reasonable and achievable?
3. **Risk Level:** What is the execution risk (budget, brand safety, operational complexity)?

**Risk Assessment Criteria:**
- HIGH RISK: Budget shifts >25%, brand-sensitive messaging changes, untested channels with large budgets
- MEDIUM RISK: Moderate budget shifts (10-25%), new audience segments, creative refreshes
- LOW RISK: Minor optimizations, A/B tests, small pilots

**Rules:**
- DO NOT approve high-risk actions without strong evidence (data_support="strong")
- Flag any action where confidence <0.5 but proposed changes are significant
- If budget allocation is missing or vague, flag for clarification

Return ONLY valid JSON in this exact format:
{{
  "approved_actions": [
    {{
      "action_id": "budget_allocation" | "audience_targeting" | "messaging_strategy" | "channel_strategy",
      "reasoning": "Brief explanation of why this is safe/supported"
    }}
  ],
  "flagged": [
    {{
      "action_id": "budget_allocation" | "audience_targeting" | "messaging_strategy" | "channel_strategy",
      "reason": "Specific concern (e.g., 'Insufficient evidence for 50% budget shift')",
      "risk": "high" | "medium" | "low",
      "recommendation": "Suggested mitigation (e.g., 'Reduce shift to 15%' or 'Run pilot first')"
    }}
  ],
  "overall_assessment": "safe" | "review_recommended" | "high_risk"
}}

**Critical:** Base your assessment ONLY on the patch content. Do not speculate or add information not present.
"""

    @staticmethod
    async def reflect_on_patch(orchestrator, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to review proposed patch actions

        Args:
            orchestrator: GeminiOrchestrator instance for LLM calls
            patch: Strategy patch to review

        Returns:
            dict with approved_actions, flagged items, and overall_assessment
        """
        try:
            logger.info("[SANITY_GATE] Starting LLM reflection on patch...")

            # Format patch for review (remove meta fields)
            review_patch = {k: v for k, v in patch.items()
                           if k not in ['patch_id', 'created_at', 'project_id', 'annotations']}

            prompt = SanityGate.REFLECTION_PROMPT_TEMPLATE.format(
                patch_json=json.dumps(review_patch, indent=2)
            )

            logger.debug(f"[SANITY_GATE] Reflection prompt length: {len(prompt)} chars")

            # Use PATCH task for reflection (temperature=0.2 for deterministic review)
            response_text = await orchestrator._call_llm('PATCH', prompt)

            logger.debug(f"[SANITY_GATE] Raw LLM response length: {len(response_text)} chars")

            # Parse JSON response
            clean_json = orchestrator._extract_json_from_response(response_text)
            if not clean_json:
                raise ValueError("No JSON content found in sanity gate response")

            review = json.loads(clean_json)

            # Validate response structure
            if 'approved_actions' not in review or 'flagged' not in review:
                raise ValueError(f"Invalid sanity gate response structure: {list(review.keys())}")

            logger.info(f"[SANITY_GATE] ✅ Review complete: {len(review.get('approved_actions', []))} approved, " +
                       f"{len(review.get('flagged', []))} flagged")

            return review

        except Exception as e:
            logger.error(f"[SANITY_GATE] ❌ Reflection failed: {e}")
            # Fallback: assume safe but log the failure
            return {
                'approved_actions': [],
                'flagged': [{
                    'action_id': 'sanity_gate_failed',
                    'reason': f'Sanity gate error: {str(e)}',
                    'risk': 'unknown',
                    'recommendation': 'Manual review required'
                }],
                'overall_assessment': 'review_recommended',
                'error': str(e)
            }

    @classmethod
    async def apply_sanity_gate(cls, orchestrator, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply sanity reflection gate and annotate patch

        Args:
            orchestrator: GeminiOrchestrator instance
            patch: Strategy patch to validate

        Returns:
            Patch with sanity gate annotations added
        """
        logger.info("[SANITY_GATE] Applying sanity reflection gate...")

        review = await cls.reflect_on_patch(orchestrator, patch)

        # Initialize annotations if not present
        if 'annotations' not in patch:
            patch['annotations'] = {}

        # Add sanity flags if any
        if review.get('flagged'):
            patch['annotations']['sanity_flags'] = review['flagged']
            patch['annotations']['requires_review'] = True
            logger.warning(f"[SANITY_GATE] ⚠️ {len(review['flagged'])} issues flagged")

            # Check for insufficient evidence flags
            insufficient_evidence_flags = [
                f for f in review['flagged']
                if 'insufficient evidence' in f.get('reason', '').lower() or
                   'no evidence' in f.get('reason', '').lower() or
                   'weak data' in f.get('reason', '').lower()
            ]

            if insufficient_evidence_flags:
                patch['insufficient_evidence'] = True
                logger.warning(f"[SANITY_GATE] Marked insufficient_evidence=True due to {len(insufficient_evidence_flags)} flags")

        # Add approved actions
        if review.get('approved_actions'):
            patch['annotations']['approved_actions'] = review['approved_actions']
            logger.info(f"[SANITY_GATE] ✅ {len(review['approved_actions'])} actions approved")

        # Add overall assessment
        patch['sanity_review'] = review.get('overall_assessment', 'unknown')

        # Log final assessment
        if review.get('overall_assessment') == 'high_risk':
            logger.error("[SANITY_GATE] 🚨 HIGH RISK patch - HITL review strongly recommended")
        elif review.get('overall_assessment') == 'review_recommended':
            logger.warning("[SANITY_GATE] ⚠️ Review recommended - some concerns flagged")
        else:
            logger.info("[SANITY_GATE] ✅ Patch assessed as safe")

        return patch

    @staticmethod
    def should_block_patch(patch: Dict[str, Any]) -> bool:
        """
        Determine if patch should be blocked (not sent to HITL)

        Args:
            patch: Patch with sanity gate annotations

        Returns:
            bool indicating if patch should be blocked
        """
        # Never auto-block - always let HITL review
        # But we can provide a recommendation
        if patch.get('sanity_review') == 'high_risk':
            flagged = patch.get('annotations', {}).get('sanity_flags', [])
            high_risk_count = sum(1 for f in flagged if f.get('risk') == 'high')

            if high_risk_count >= 2:
                logger.error(f"[SANITY_GATE] 🚨 Recommendation: BLOCK patch (>= 2 high-risk flags)")
                return True

        return False

    @staticmethod
    def get_review_summary(patch: Dict[str, Any]) -> str:
        """
        Generate human-readable review summary

        Args:
            patch: Patch with sanity gate annotations

        Returns:
            str summary for logging/display
        """
        review = patch.get('sanity_review', 'unknown')
        annotations = patch.get('annotations', {})
        flagged = annotations.get('sanity_flags', [])
        approved = annotations.get('approved_actions', [])

        summary_parts = [
            f"Assessment: {review.upper()}",
            f"Approved: {len(approved)} actions",
            f"Flagged: {len(flagged)} issues"
        ]

        if flagged:
            risk_counts = {}
            for flag in flagged:
                risk = flag.get('risk', 'unknown')
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            summary_parts.append(f"Risk distribution: {dict(risk_counts)}")

        return " | ".join(summary_parts)
