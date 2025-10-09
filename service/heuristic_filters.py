"""
Heuristic Patch Filters
Lightweight validation rules that don't require external data
Checks: budget sanity, audience sanity, creative sanity
"""

import logging
import re
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class HeuristicFilters:
    """Lightweight validation rules for strategy patches"""

    @staticmethod
    def check_budget_sanity(patch: Dict[str, Any]) -> List[str]:
        """
        Budget sanity: Do not shift >25% total budget in a single patch

        Args:
            patch: Strategy patch dictionary

        Returns:
            List of flag strings if violations found
        """
        flags = []

        budget_allocation = patch.get('budget_allocation', {})
        channel_breakdown = budget_allocation.get('channel_breakdown', {})

        if not channel_breakdown:
            logger.debug("[BUDGET] No channel_breakdown found, skipping budget check")
            return flags

        # Calculate total percentage shift
        total_shift = 0.0
        for channel, value in channel_breakdown.items():
            # Extract percentage from strings like "30%", "+15%", "-10%"
            if isinstance(value, str):
                # Remove currency symbols and extract number
                cleaned = re.sub(r'[^\d.+-]', '', value)
                try:
                    if cleaned:
                        # If it's a delta (+ or -), use absolute value
                        if cleaned.startswith(('+', '-')):
                            shift = abs(float(cleaned))
                        else:
                            # If it's an absolute percentage, assume it's a shift
                            shift = float(cleaned)
                        total_shift += shift
                        logger.debug(f"[BUDGET] Channel {channel}: shift={shift}%, cumulative={total_shift}%")
                except ValueError:
                    logger.warning(f"[BUDGET] Could not parse budget value: {value}")

        if total_shift > 25:
            flag = f"budget_shift_exceeds_25_percent: total_shift={total_shift:.1f}%"
            flags.append(flag)
            logger.warning(f"[BUDGET] {flag}")
        else:
            logger.debug(f"[BUDGET] Check passed: total_shift={total_shift:.1f}% (≤25%)")

        return flags

    @staticmethod
    def check_audience_sanity(patch: Dict[str, Any]) -> List[str]:
        """
        Audience sanity: Avoid overlapping geo+age segment definitions

        Args:
            patch: Strategy patch dictionary

        Returns:
            List of flag strings if violations found
        """
        flags = []

        audience_targeting = patch.get('audience_targeting', {})
        segments = audience_targeting.get('segments', [])

        if not segments:
            logger.debug("[AUDIENCE] No segments found, skipping audience check")
            return flags

        # Track (location, age) combinations
        seen_combinations = set()

        for i, segment in enumerate(segments):
            criteria = segment.get('targeting_criteria', {})
            location = criteria.get('location', '').strip().lower()
            age = criteria.get('age', '').strip().lower()

            if not location or not age:
                logger.debug(f"[AUDIENCE] Segment {i} missing location or age, skipping: {criteria}")
                continue

            combination = (location, age)

            if combination in seen_combinations:
                flag = f"overlapping_segment: location='{location}', age='{age}' (segment_index={i})"
                flags.append(flag)
                logger.warning(f"[AUDIENCE] {flag}")
            else:
                seen_combinations.add(combination)
                logger.debug(f"[AUDIENCE] Segment {i} unique: {combination}")

        if not flags:
            logger.debug(f"[AUDIENCE] Check passed: {len(seen_combinations)} unique geo+age combinations")

        return flags

    @staticmethod
    def check_creative_sanity(patch: Dict[str, Any]) -> List[str]:
        """
        Creative sanity: Do not add >3 creatives per audience in one patch

        Args:
            patch: Strategy patch dictionary

        Returns:
            List of flag strings if violations found
        """
        flags = []

        # Get segment count
        audience_targeting = patch.get('audience_targeting', {})
        segments = audience_targeting.get('segments', [])
        segment_count = len(segments)

        # Get messaging/creative count
        messaging_strategy = patch.get('messaging_strategy', {})
        key_themes = messaging_strategy.get('key_themes', [])
        theme_count = len(key_themes)

        if segment_count == 0:
            logger.debug("[CREATIVE] No segments found, skipping creative check")
            return flags

        # Rule: Maximum 3 themes (creatives) per segment
        max_allowed_themes = segment_count * 3

        if theme_count > max_allowed_themes:
            flag = f"excessive_creatives: {theme_count} themes for {segment_count} segments (max={max_allowed_themes})"
            flags.append(flag)
            logger.warning(f"[CREATIVE] {flag}")
        else:
            logger.debug(f"[CREATIVE] Check passed: {theme_count} themes for {segment_count} segments (≤{max_allowed_themes})")

        return flags

    @classmethod
    def validate_patch(cls, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all heuristic checks and return validation result

        Args:
            patch: Strategy patch dictionary to validate

        Returns:
            dict with validation results:
            {
                'heuristic_flags': [...],
                'passed': bool,
                'reasons': [...]
            }
        """
        logger.info("[HEURISTIC] Starting patch validation...")

        all_flags = []

        # Run all checks
        budget_flags = cls.check_budget_sanity(patch)
        audience_flags = cls.check_audience_sanity(patch)
        creative_flags = cls.check_creative_sanity(patch)

        all_flags.extend(budget_flags)
        all_flags.extend(audience_flags)
        all_flags.extend(creative_flags)

        # Extract reason types (before colon)
        reasons = [flag.split(':')[0] for flag in all_flags]

        result = {
            'heuristic_flags': all_flags,
            'passed': len(all_flags) == 0,
            'reasons': reasons,
            'budget_flags': len(budget_flags),
            'audience_flags': len(audience_flags),
            'creative_flags': len(creative_flags)
        }

        if result['passed']:
            logger.info("[HEURISTIC] ✅ Validation passed: no flags")
        else:
            logger.warning(f"[HEURISTIC] ❌ Validation failed: {len(all_flags)} flags - {reasons}")

        return result

    @staticmethod
    def downscope_patch_if_needed(patch: Dict[str, Any], validation_result: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Attempt to auto-downscope patch to fix heuristic violations

        Args:
            patch: Original patch
            validation_result: Validation result from validate_patch()

        Returns:
            (modified_patch, was_modified) tuple
        """
        if validation_result['passed']:
            return patch, False

        modified = False
        new_patch = patch.copy()

        # Auto-fix budget violations by scaling down shifts
        if validation_result['budget_flags'] > 0:
            budget_allocation = new_patch.get('budget_allocation', {})
            channel_breakdown = budget_allocation.get('channel_breakdown', {})

            if channel_breakdown:
                logger.info("[DOWNSCOPE] Scaling budget shifts to meet 25% limit...")
                # Scale all shifts by 0.8 (20% reduction)
                for channel, value in channel_breakdown.items():
                    if isinstance(value, str) and '%' in value:
                        cleaned = re.sub(r'[^\d.+-]', '', value)
                        if cleaned and (cleaned.startswith(('+', '-'))):
                            try:
                                original = float(cleaned)
                                scaled = original * 0.8
                                new_value = f"{'+' if scaled > 0 else ''}{scaled:.1f}%"
                                channel_breakdown[channel] = new_value
                                logger.debug(f"[DOWNSCOPE] {channel}: {value} → {new_value}")
                                modified = True
                            except ValueError:
                                pass

        # Auto-fix creative violations by trimming themes
        if validation_result['creative_flags'] > 0:
            messaging_strategy = new_patch.get('messaging_strategy', {})
            key_themes = messaging_strategy.get('key_themes', [])
            segments = new_patch.get('audience_targeting', {}).get('segments', [])

            if len(key_themes) > len(segments) * 3:
                max_themes = len(segments) * 3
                logger.info(f"[DOWNSCOPE] Trimming key_themes from {len(key_themes)} to {max_themes}...")
                messaging_strategy['key_themes'] = key_themes[:max_themes]
                modified = True

        if modified:
            logger.info("[DOWNSCOPE] ✅ Patch auto-downscoped to fix violations")
        else:
            logger.info("[DOWNSCOPE] ❌ Could not auto-downscope, manual review required")

        return new_patch, modified
