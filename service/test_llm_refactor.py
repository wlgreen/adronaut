"""
Unit tests for LLM Service Refactoring (Phase 1 & 2)
Tests the 5 foundation modules and orchestrator integration
"""

import pytest
from typing import Dict, List

# Import the modules we're testing
from mechanics_cheat_sheet import (
    get_mechanics_for_metric,
    validate_lever_choice,
    MECHANICS_CHEAT_SHEET
)
from insights_selector import (
    score_insight,
    select_top_insights,
    validate_insight_structure,
    validate_confidence_alignment,
    count_data_support_distribution,
    calculate_insufficient_evidence_rate
)
from heuristic_filters import HeuristicFilters
from sanity_gate import SanityGate
from logging_metrics import LLMMetrics


class TestMechanicsCheatSheet:
    """Test the mechanics cheat sheet module"""

    def test_get_mechanics_for_ctr(self):
        """Test CTR mechanics mapping"""
        mechanics = get_mechanics_for_metric('CTR')

        assert 'creative' in mechanics['primary_levers']
        assert 'audience' in mechanics['primary_levers']
        assert 'bidding' in mechanics['secondary_levers']
        assert len(mechanics['typical_actions']) > 0

    def test_get_mechanics_for_conversion_rate(self):
        """Test conversion rate mechanics mapping"""
        mechanics = get_mechanics_for_metric('conversion_rate')

        assert 'funnel' in mechanics['primary_levers']
        assert 'creative' in mechanics['primary_levers']
        assert len(mechanics['typical_actions']) > 0

    def test_validate_lever_choice_valid(self):
        """Test valid lever choices"""
        assert validate_lever_choice('audience') is True
        assert validate_lever_choice('creative') is True
        assert validate_lever_choice('budget') is True
        assert validate_lever_choice('bidding') is True
        assert validate_lever_choice('funnel') is True

    def test_validate_lever_choice_invalid(self):
        """Test invalid lever choices"""
        assert validate_lever_choice('invalid_lever') is False
        assert validate_lever_choice('') is False
        assert validate_lever_choice(None) is False

    def test_cheat_sheet_is_string(self):
        """Test that cheat sheet is a valid string for prompts"""
        assert isinstance(MECHANICS_CHEAT_SHEET, str)
        assert len(MECHANICS_CHEAT_SHEET) > 100
        assert 'CTR' in MECHANICS_CHEAT_SHEET
        assert 'primary_lever' in MECHANICS_CHEAT_SHEET


class TestInsightsSelector:
    """Test the insights selector module"""

    def create_valid_insight(self, score_boost: int = 0) -> Dict:
        """Helper to create a valid insight for testing"""
        return {
            'insight': 'Test observation',
            'hypothesis': 'Test hypothesis',
            'proposed_action': 'Test action',
            'primary_lever': 'audience',
            'expected_effect': {
                'direction': 'increase',
                'metric': 'CTR',
                'magnitude': 'medium'
            },
            'confidence': 0.7,
            'data_support': 'strong' if score_boost > 0 else 'moderate',
            'evidence_refs': ['features.test_field'] if score_boost > 0 else [],
            'contrastive_reason': 'Because X instead of Y'
        }

    def test_score_insight_with_evidence(self):
        """Test scoring insight with strong evidence"""
        insight = self.create_valid_insight(score_boost=2)
        score = score_insight(insight)

        # Should get +2 for evidence_refs, +2 for strong support,
        # +1 for expected_effect, +1 for primary_lever = 6 raw -> 75/100
        assert score >= 50
        assert score <= 100

    def test_score_insight_without_evidence(self):
        """Test scoring insight without evidence"""
        insight = self.create_valid_insight(score_boost=0)
        insight['evidence_refs'] = []
        score = score_insight(insight)

        # Should get less than with evidence
        assert score >= 0
        assert score <= 100

    def test_validate_insight_structure_valid(self):
        """Test validation with valid insight"""
        insight = self.create_valid_insight()
        assert validate_insight_structure(insight) is True

    def test_validate_insight_structure_missing_fields(self):
        """Test validation with missing required fields"""
        insight = {'insight': 'Test'}  # Missing many fields
        assert validate_insight_structure(insight) is False

    def test_validate_confidence_alignment_valid(self):
        """Test confidence alignment with weak support"""
        insight = {
            'confidence': 0.3,
            'data_support': 'weak'
        }
        assert validate_confidence_alignment(insight) is True

    def test_validate_confidence_alignment_invalid(self):
        """Test invalid confidence alignment"""
        insight = {
            'confidence': 0.8,  # Too high for weak support
            'data_support': 'weak'
        }
        assert validate_confidence_alignment(insight) is False

    def test_select_top_insights(self):
        """Test selecting top k insights"""
        candidates = [
            self.create_valid_insight(score_boost=i)
            for i in range(5)
        ]

        top_3 = select_top_insights(candidates, k=3)

        assert len(top_3) == 3
        assert all('impact_rank' in insight for insight in top_3)
        assert all('impact_score' in insight for insight in top_3)
        assert top_3[0]['impact_rank'] == 1
        assert top_3[1]['impact_rank'] == 2
        assert top_3[2]['impact_rank'] == 3

    def test_count_data_support_distribution(self):
        """Test data support counting"""
        insights = [
            {'data_support': 'strong'},
            {'data_support': 'strong'},
            {'data_support': 'moderate'},
            {'data_support': 'weak'}
        ]

        counts = count_data_support_distribution(insights)

        assert counts['strong'] == 2
        assert counts['moderate'] == 1
        assert counts['weak'] == 1

    def test_calculate_insufficient_evidence_rate(self):
        """Test insufficient evidence rate calculation"""
        insights = [
            {'data_support': 'weak'},
            {'data_support': 'strong'},
            {'data_support': 'weak'},
            {'data_support': 'moderate'}
        ]

        rate = calculate_insufficient_evidence_rate(insights)

        # 2 weak out of 4 = 0.5
        assert rate == 0.5


class TestHeuristicFilters:
    """Test the heuristic filters module"""

    def create_valid_patch(self) -> Dict:
        """Helper to create a valid patch for testing"""
        return {
            'audience_targeting': {
                'segments': [
                    {
                        'name': 'Segment 1',
                        'demographics': {'age': '25-35', 'location': 'US'},
                        'interests': []
                    }
                ]
            },
            'messaging_strategy': {
                'primary_message': 'Test message',
                'key_themes': ['theme1', 'theme2']
            },
            'channel_strategy': {
                'primary_channels': ['social', 'search']
            },
            'budget_allocation': {
                'total_budget': '$10000',
                'channel_breakdown': {
                    'social': '50%',
                    'search': '50%'
                }
            }
        }

    def test_validate_patch_valid(self):
        """Test validation with valid patch"""
        patch = self.create_valid_patch()
        validation = HeuristicFilters.validate_patch(patch)

        assert validation['passed'] is True
        assert len(validation['heuristic_flags']) == 0

    def test_validate_patch_budget_violation(self):
        """Test budget sanity check violation"""
        patch = self.create_valid_patch()
        # Create budget shift >25%
        patch['budget_allocation']['channel_breakdown'] = {
            'social': '80%',  # 30% shift from 50%
            'search': '20%'
        }

        validation = HeuristicFilters.validate_patch(patch)

        assert validation['passed'] is False
        assert any('budget_shift' in flag for flag in validation['heuristic_flags'])

    def test_validate_patch_audience_overlap(self):
        """Test audience overlap detection"""
        patch = self.create_valid_patch()
        # Add overlapping segment
        patch['audience_targeting']['segments'].append({
            'name': 'Segment 2',
            'demographics': {'age': '25-35', 'location': 'US'},  # Same as Segment 1
            'interests': []
        })

        validation = HeuristicFilters.validate_patch(patch)

        assert validation['passed'] is False
        assert any('overlapping_segment' in flag for flag in validation['heuristic_flags'])

    def test_validate_patch_excessive_creatives(self):
        """Test creative sanity check"""
        patch = self.create_valid_patch()
        # Add excessive themes (>3 per segment, 1 segment = max 3 themes)
        patch['messaging_strategy']['key_themes'] = [
            'theme1', 'theme2', 'theme3', 'theme4', 'theme5'
        ]

        validation = HeuristicFilters.validate_patch(patch)

        # Should flag excessive creatives
        assert validation['passed'] is False
        assert any('excessive_creatives' in flag for flag in validation['heuristic_flags'])

    def test_downscope_patch_if_needed(self):
        """Test auto-downscoping functionality"""
        patch = self.create_valid_patch()
        patch['budget_allocation']['channel_breakdown'] = {
            'social': '80%',
            'search': '20%'
        }

        validation = HeuristicFilters.validate_patch(patch)
        modified_patch, was_modified = HeuristicFilters.downscope_patch_if_needed(
            patch, validation
        )

        assert was_modified is True
        # Budget should be scaled down
        assert modified_patch != patch


class TestSanityGate:
    """Test the sanity gate module (mocked LLM calls)"""

    def test_sanity_gate_structure(self):
        """Test that sanity gate methods exist and have correct signatures"""
        # Check that required methods exist
        assert hasattr(SanityGate, 'reflect_on_patch')
        assert hasattr(SanityGate, 'apply_sanity_gate')
        assert hasattr(SanityGate, 'should_block_patch')
        assert hasattr(SanityGate, 'get_review_summary')

    def test_should_block_patch_with_high_risk_flags(self):
        """Test blocking logic for high-risk patches"""
        patch = {
            'annotations': {
                'sanity_flags': [
                    {'risk': 'high'},
                    {'risk': 'high'}
                ]
            }
        }

        should_block = SanityGate.should_block_patch(patch)
        assert should_block is True

    def test_should_block_patch_with_low_risk_flags(self):
        """Test non-blocking for low-risk patches"""
        patch = {
            'annotations': {
                'sanity_flags': [
                    {'risk': 'low'},
                    {'risk': 'medium'}
                ]
            }
        }

        should_block = SanityGate.should_block_patch(patch)
        assert should_block is False


class TestLoggingMetrics:
    """Test the logging metrics module"""

    def test_log_insights_job_structure(self):
        """Test insights job logging"""
        log_data = LLMMetrics.log_insights_job(
            job_id='test-job-123',
            latency_ms=1500,
            temperature=0.35,
            candidate_count=5,
            selected_score=85,
            has_evidence_refs=True,
            data_support_counts={'strong': 2, 'moderate': 1, 'weak': 0},
            insufficient_evidence_rate=0.0
        )

        assert log_data['event'] == 'INSIGHTS_JOB'
        assert log_data['job_id'] == 'test-job-123'
        assert log_data['latency_ms'] == 1500
        assert log_data['temperature'] == 0.35
        assert log_data['candidate_count'] == 5

    def test_log_patch_job_structure(self):
        """Test patch job logging"""
        log_data = LLMMetrics.log_patch_job(
            job_id='test-patch-456',
            latency_ms=2000,
            temperature=0.2,
            heuristic_flags_count=1,
            sanity_flags_count=0,
            passed_validation=True
        )

        assert log_data['event'] == 'PATCH_JOB'
        assert log_data['job_id'] == 'test-patch-456'
        assert log_data['passed_validation'] is True

    def test_calculate_aggregate_metrics(self):
        """Test aggregate metrics calculation"""
        job_logs = [
            {
                'event': 'INSIGHTS_JOB',
                'latency_ms': 1000,
                'candidate_count': 5,
                'selected_score': 80,
                'has_evidence_refs': True,
                'insufficient_evidence_rate': 0.0
            },
            {
                'event': 'INSIGHTS_JOB',
                'latency_ms': 1500,
                'candidate_count': 5,
                'selected_score': 90,
                'has_evidence_refs': True,
                'insufficient_evidence_rate': 0.2
            },
            {
                'event': 'PATCH_JOB',
                'latency_ms': 2000,
                'heuristic_flags_count': 1,
                'sanity_flags_count': 0,
                'passed_validation': True,
                'auto_downscoped': False
            }
        ]

        aggregates = LLMMetrics.calculate_aggregate_metrics(job_logs)

        assert aggregates['total_jobs'] == 3
        assert aggregates['insights_jobs'] == 2
        assert aggregates['patch_jobs'] == 1
        assert aggregates['avg_latency_ms'] == 1500.0
        assert 'insights_metrics' in aggregates
        assert 'patch_metrics' in aggregates


class TestIntegration:
    """Integration tests for the full workflow"""

    def test_end_to_end_insights_scoring_and_selection(self):
        """Test complete insights generation workflow"""
        # Create 5 candidates with varying quality
        candidates = [
            {
                'insight': f'Insight {i}',
                'hypothesis': f'Hypothesis {i}',
                'proposed_action': f'Action {i}',
                'primary_lever': 'audience',
                'expected_effect': {
                    'direction': 'increase',
                    'metric': 'CTR',
                    'magnitude': 'medium'
                },
                'confidence': 0.5 + (i * 0.1),
                'data_support': 'strong' if i >= 3 else 'moderate',
                'evidence_refs': [f'features.field_{i}'] if i >= 2 else [],
                'contrastive_reason': f'Reason {i}'
            }
            for i in range(5)
        ]

        # Validate all candidates
        valid_candidates = [c for c in candidates if validate_insight_structure(c)]
        assert len(valid_candidates) == 5

        # Select top 3
        top_3 = select_top_insights(valid_candidates, k=3)
        assert len(top_3) == 3

        # Check ranking
        assert top_3[0]['impact_rank'] == 1
        assert top_3[1]['impact_rank'] == 2
        assert top_3[2]['impact_rank'] == 3

        # Check scores are sorted
        assert top_3[0]['impact_score'] >= top_3[1]['impact_score']
        assert top_3[1]['impact_score'] >= top_3[2]['impact_score']

    def test_end_to_end_patch_validation_and_filtering(self):
        """Test complete patch validation workflow"""
        patch = {
            'audience_targeting': {
                'segments': [
                    {
                        'name': 'Segment 1',
                        'demographics': {'age': '25-35', 'location': 'US'}
                    }
                ]
            },
            'messaging_strategy': {
                'key_themes': ['theme1', 'theme2']
            },
            'budget_allocation': {
                'channel_breakdown': {
                    'social': '55%',  # 5% shift
                    'search': '45%'
                }
            }
        }

        # Validate
        validation = HeuristicFilters.validate_patch(patch)
        assert validation['passed'] is True

        # Try downscope (should not modify since it passes)
        modified_patch, was_modified = HeuristicFilters.downscope_patch_if_needed(
            patch, validation
        )
        assert was_modified is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
