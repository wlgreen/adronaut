"""
LLM Metrics Logging
Enhanced observability for LLM job performance and quality metrics
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMMetrics:
    """Enhanced logging for LLM job observability"""

    @staticmethod
    def log_insights_job(
        job_id: str,
        latency_ms: int,
        temperature: float,
        candidate_count: int,
        selected_score: int,
        has_evidence_refs: bool,
        data_support_counts: Dict[str, int],
        insufficient_evidence_rate: float,
        project_id: Optional[str] = None
    ):
        """
        Log INSIGHTS job metrics

        Args:
            job_id: Unique job identifier
            latency_ms: Job latency in milliseconds
            temperature: Temperature used for LLM call
            candidate_count: Number of candidates generated
            selected_score: Score of top-ranked insight (0-100)
            has_evidence_refs: Whether top insight has evidence references
            data_support_counts: Distribution of data_support levels
            insufficient_evidence_rate: Rate of insights with weak support (0-1)
            project_id: Optional project identifier
        """
        log_data = {
            'event': 'INSIGHTS_JOB',
            'job_id': job_id,
            'project_id': project_id,
            'latency_ms': latency_ms,
            'temperature': temperature,
            'candidate_count': candidate_count,
            'selected_score': selected_score,
            'has_evidence_refs': has_evidence_refs,
            'data_support_strong': data_support_counts.get('strong', 0),
            'data_support_moderate': data_support_counts.get('moderate', 0),
            'data_support_weak': data_support_counts.get('weak', 0),
            'insufficient_evidence_rate': round(insufficient_evidence_rate, 3),
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"📊 INSIGHTS_JOB | job={job_id[:8]} | " +
                   f"latency={latency_ms}ms | temp={temperature} | " +
                   f"candidates={candidate_count} | score={selected_score} | " +
                   f"evidence={'yes' if has_evidence_refs else 'no'} | " +
                   f"support=[S:{data_support_counts.get('strong', 0)} " +
                   f"M:{data_support_counts.get('moderate', 0)} " +
                   f"W:{data_support_counts.get('weak', 0)}] | " +
                   f"insuff_rate={insufficient_evidence_rate:.1%}")

        return log_data

    @staticmethod
    def log_patch_job(
        job_id: str,
        latency_ms: int,
        temperature: float,
        heuristic_flags_count: int,
        sanity_flags_count: int,
        passed_validation: bool,
        project_id: Optional[str] = None,
        auto_downscoped: bool = False
    ):
        """
        Log PATCH job metrics

        Args:
            job_id: Unique job identifier
            latency_ms: Job latency in milliseconds
            temperature: Temperature used for LLM call
            heuristic_flags_count: Number of heuristic filter violations
            sanity_flags_count: Number of sanity gate flags
            passed_validation: Whether patch passed all validations
            project_id: Optional project identifier
            auto_downscoped: Whether patch was auto-downscoped
        """
        log_data = {
            'event': 'PATCH_JOB',
            'job_id': job_id,
            'project_id': project_id,
            'latency_ms': latency_ms,
            'temperature': temperature,
            'heuristic_flags_count': heuristic_flags_count,
            'sanity_flags_count': sanity_flags_count,
            'passed_validation': passed_validation,
            'auto_downscoped': auto_downscoped,
            'timestamp': datetime.utcnow().isoformat()
        }

        status_emoji = '✅' if passed_validation else '⚠️'
        logger.info(f"{status_emoji} PATCH_JOB | job={job_id[:8]} | " +
                   f"latency={latency_ms}ms | temp={temperature} | " +
                   f"heuristic_flags={heuristic_flags_count} | " +
                   f"sanity_flags={sanity_flags_count} | " +
                   f"valid={'yes' if passed_validation else 'no'} | " +
                   f"downscoped={'yes' if auto_downscoped else 'no'}")

        return log_data

    @staticmethod
    def log_edit_job(
        job_id: str,
        latency_ms: int,
        temperature: float,
        delta_size: int,
        passed_filters: bool,
        project_id: Optional[str] = None,
        original_patch_id: Optional[str] = None
    ):
        """
        Log EDIT_PATCH job metrics

        Args:
            job_id: Unique job identifier
            latency_ms: Job latency in milliseconds
            temperature: Temperature used for LLM call
            delta_size: Number of fields changed in patch
            passed_filters: Whether edited patch passed filters
            project_id: Optional project identifier
            original_patch_id: ID of original patch being edited
        """
        log_data = {
            'event': 'EDIT_PATCH_JOB',
            'job_id': job_id,
            'project_id': project_id,
            'original_patch_id': original_patch_id,
            'latency_ms': latency_ms,
            'temperature': temperature,
            'delta_size': delta_size,
            'passed_filters': passed_filters,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"✏️ EDIT_PATCH_JOB | job={job_id[:8]} | " +
                   f"latency={latency_ms}ms | temp={temperature} | " +
                   f"delta={delta_size} fields | " +
                   f"valid={'yes' if passed_filters else 'no'}")

        return log_data

    @staticmethod
    def log_features_job(
        job_id: str,
        latency_ms: int,
        temperature: float,
        artifact_count: int,
        features_extracted: int,
        has_metrics: bool,
        project_id: Optional[str] = None
    ):
        """
        Log FEATURES extraction job metrics

        Args:
            job_id: Unique job identifier
            latency_ms: Job latency in milliseconds
            temperature: Temperature used for LLM call
            artifact_count: Number of artifacts processed
            features_extracted: Number of features extracted
            has_metrics: Whether performance metrics were found
            project_id: Optional project identifier
        """
        log_data = {
            'event': 'FEATURES_JOB',
            'job_id': job_id,
            'project_id': project_id,
            'latency_ms': latency_ms,
            'temperature': temperature,
            'artifact_count': artifact_count,
            'features_extracted': features_extracted,
            'has_metrics': has_metrics,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"🔍 FEATURES_JOB | job={job_id[:8]} | " +
                   f"latency={latency_ms}ms | temp={temperature} | " +
                   f"artifacts={artifact_count} | features={features_extracted} | " +
                   f"metrics={'yes' if has_metrics else 'no'}")

        return log_data

    @staticmethod
    def log_analyze_job(
        job_id: str,
        latency_ms: int,
        temperature: float,
        metrics_analyzed: int,
        alerts_count: int,
        actions_proposed: int,
        project_id: Optional[str] = None,
        campaign_id: Optional[str] = None
    ):
        """
        Log ANALYZE performance job metrics

        Args:
            job_id: Unique job identifier
            latency_ms: Job latency in milliseconds
            temperature: Temperature used for LLM call
            metrics_analyzed: Number of metrics analyzed
            alerts_count: Number of alerts generated
            actions_proposed: Number of candidate actions proposed
            project_id: Optional project identifier
            campaign_id: Optional campaign identifier
        """
        log_data = {
            'event': 'ANALYZE_JOB',
            'job_id': job_id,
            'project_id': project_id,
            'campaign_id': campaign_id,
            'latency_ms': latency_ms,
            'temperature': temperature,
            'metrics_analyzed': metrics_analyzed,
            'alerts_count': alerts_count,
            'actions_proposed': actions_proposed,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"📈 ANALYZE_JOB | job={job_id[:8]} | " +
                   f"latency={latency_ms}ms | temp={temperature} | " +
                   f"metrics={metrics_analyzed} | alerts={alerts_count} | " +
                   f"actions={actions_proposed}")

        return log_data

    @staticmethod
    def log_llm_call(
        task: str,
        provider: str,
        model: str,
        temperature: float,
        latency_ms: int,
        prompt_length: int,
        response_length: int,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Log individual LLM API call metrics

        Args:
            task: Task name (FEATURES, INSIGHTS, PATCH, etc.)
            provider: Provider name (gemini, openai)
            model: Model name
            temperature: Temperature used
            latency_ms: Call latency in milliseconds
            prompt_length: Prompt character count
            response_length: Response character count
            success: Whether call succeeded
            error: Error message if failed
        """
        log_data = {
            'event': 'LLM_CALL',
            'task': task,
            'provider': provider,
            'model': model,
            'temperature': temperature,
            'latency_ms': latency_ms,
            'prompt_length': prompt_length,
            'response_length': response_length,
            'success': success,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }

        status = '✅' if success else '❌'
        logger.debug(f"{status} LLM_CALL | task={task} | {provider}:{model} | " +
                    f"temp={temperature} | latency={latency_ms}ms | " +
                    f"prompt={prompt_length}ch | response={response_length}ch" +
                    (f" | error={error}" if error else ""))

        return log_data

    @staticmethod
    def calculate_aggregate_metrics(job_logs: list) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from job logs

        Args:
            job_logs: List of job log dictionaries

        Returns:
            dict with aggregate statistics
        """
        if not job_logs:
            return {}

        insights_jobs = [j for j in job_logs if j.get('event') == 'INSIGHTS_JOB']
        patch_jobs = [j for j in job_logs if j.get('event') == 'PATCH_JOB']

        aggregates = {
            'total_jobs': len(job_logs),
            'insights_jobs': len(insights_jobs),
            'patch_jobs': len(patch_jobs),
            'avg_latency_ms': sum(j.get('latency_ms', 0) for j in job_logs) / len(job_logs) if job_logs else 0,
            'insights_metrics': {},
            'patch_metrics': {}
        }

        # Insights aggregates
        if insights_jobs:
            aggregates['insights_metrics'] = {
                'avg_candidate_count': sum(j.get('candidate_count', 0) for j in insights_jobs) / len(insights_jobs),
                'avg_selected_score': sum(j.get('selected_score', 0) for j in insights_jobs) / len(insights_jobs),
                'avg_insufficient_evidence_rate': sum(j.get('insufficient_evidence_rate', 0) for j in insights_jobs) / len(insights_jobs),
                'evidence_refs_rate': sum(1 for j in insights_jobs if j.get('has_evidence_refs')) / len(insights_jobs)
            }

        # Patch aggregates
        if patch_jobs:
            aggregates['patch_metrics'] = {
                'validation_pass_rate': sum(1 for j in patch_jobs if j.get('passed_validation')) / len(patch_jobs),
                'avg_heuristic_flags': sum(j.get('heuristic_flags_count', 0) for j in patch_jobs) / len(patch_jobs),
                'avg_sanity_flags': sum(j.get('sanity_flags_count', 0) for j in patch_jobs) / len(patch_jobs),
                'auto_downscope_rate': sum(1 for j in patch_jobs if j.get('auto_downscoped')) / len(patch_jobs)
            }

        logger.info(f"📊 AGGREGATE_METRICS | total_jobs={aggregates['total_jobs']} | " +
                   f"avg_latency={aggregates['avg_latency_ms']:.0f}ms | " +
                   f"insights={len(insights_jobs)} | patches={len(patch_jobs)}")

        return aggregates
