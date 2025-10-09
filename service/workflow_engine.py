#!/usr/bin/env python3
"""
Workflow Engine - Reusable LLM Workflow Logic

This module extracts the core LLM workflow logic from main.py to enable:
- Single source of truth for workflow steps
- Automatic sync between production and test environments
- Dependency injection for logging, database, orchestrator

Usage in production (main.py):
    engine = WorkflowEngine(db, orchestrator)
    result = await engine.run_llm_workflow(artifacts, save_to_db=True)

Usage in tests (test_llm_flow.py):
    engine = WorkflowEngine(mock_db, orchestrator)
    result = await engine.run_llm_workflow(artifacts, save_to_db=False, logger_callback=custom_log)
"""

import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Executes the LLM workflow: FEATURES → INSIGHTS → PATCH_GENERATION"""

    def __init__(self, database=None, orchestrator=None):
        """
        Initialize workflow engine with dependencies

        Args:
            database: Database instance (can be None for tests)
            orchestrator: GeminiOrchestrator instance (required)
        """
        self.db = database
        self.orchestrator = orchestrator

    async def run_llm_workflow(
        self,
        artifacts: List[Dict[str, Any]],
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        save_to_db: bool = True,
        logger_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run the complete LLM workflow: FEATURES → INSIGHTS → PATCH_GENERATION

        Args:
            artifacts: List of artifact dicts with file_name, file_type, content
            project_id: Project ID (required if save_to_db=True)
            run_id: Run ID for logging (optional)
            save_to_db: Whether to save snapshots/patches to database
            logger_callback: Custom logging function (msg: str, level: str = 'info')

        Returns:
            Dict with keys: features, insights_result, patch, annotations, metadata
        """
        # Helper for logging
        def log(message: str, level: str = 'info'):
            if logger_callback:
                logger_callback(message, level)
            else:
                getattr(logger, level)(message)

        workflow_result = {
            'features': None,
            'insights_result': None,
            'patch': None,
            'annotations': None,
            'metadata': {}
        }

        try:
            # ================================================================
            # STEP 1: FEATURES EXTRACTION
            # ================================================================
            log("🔍 STEP 1: FEATURES EXTRACTION", 'info')
            log(f"📊 Processing {len(artifacts)} artifacts", 'info')

            # Prepare artifacts for extraction
            artifact_list = [
                {
                    'file_name': a.get('file_name', a.get('filename', 'unknown')),
                    'file_type': a.get('file_type', a.get('mime', 'unknown')),
                    'summary_json': a.get('summary_json', {'content_preview': a.get('content', '')[:1000]})
                }
                for a in artifacts
            ]

            features = await self.orchestrator.extract_features(artifact_list)
            workflow_result['features'] = features

            log(f"✅ Features extracted: {len(features) if isinstance(features, dict) else 0} keys", 'info')

            if isinstance(features, dict):
                for key in list(features.keys())[:5]:  # Log first 5 keys
                    log(f"   ✓ {key}", 'info')

            # Save snapshot to database
            if save_to_db and self.db and project_id:
                snapshot_id = await self.db.create_snapshot(project_id, features)
                log(f"💾 Snapshot saved: {snapshot_id}", 'info')
                workflow_result['metadata']['snapshot_id'] = snapshot_id

            # ================================================================
            # STEP 2: INSIGHTS GENERATION
            # ================================================================
            log("\n💡 STEP 2: INSIGHTS GENERATION", 'info')
            log("🧠 Generating k=5 candidates, selecting top 3...", 'info')

            insights_result = await self.orchestrator.generate_insights(features)
            workflow_result['insights_result'] = insights_result

            insights_list = insights_result.get('insights', [])
            candidates_evaluated = insights_result.get('candidates_evaluated', 0)
            selection_method = insights_result.get('selection_method', 'unknown')

            log(f"✅ Insights generated", 'info')
            log(f"   📊 Candidates evaluated: {candidates_evaluated}", 'info')
            log(f"   🎯 Selection method: {selection_method}", 'info')
            log(f"   ✅ Top insights selected: {len(insights_list)}", 'info')

            for i, insight in enumerate(insights_list, 1):
                score = insight.get('impact_score', 0)
                lever = insight.get('primary_lever', 'unknown')
                support = insight.get('data_support', 'unknown')
                confidence = insight.get('confidence', 0)
                log(f"   {i}. [{score}/100] {lever} - {support} support, {confidence:.2f} confidence", 'info')

            # Update snapshot with insights
            if save_to_db and self.db and project_id:
                combined_snapshot = {**features, 'insights': insights_result}
                snapshot_id = await self.db.create_snapshot(project_id, combined_snapshot)
                log(f"💾 Snapshot updated with insights: {snapshot_id}", 'info')

            # ================================================================
            # STEP 3: PATCH GENERATION (with filters and sanity gate)
            # ================================================================
            log("\n🔧 STEP 3: PATCH GENERATION", 'info')
            log("🛡️  Applying heuristic filters and sanity gate...", 'info')

            patch_with_annotations = await self.orchestrator.generate_patch(insights_result)
            workflow_result['patch'] = patch_with_annotations

            # Extract validation results
            annotations = patch_with_annotations.get('annotations', {})
            sanity_review = patch_with_annotations.get('sanity_review', 'safe')
            heuristic_flags = annotations.get('heuristic_flags', [])
            sanity_flags = annotations.get('sanity_flags', [])
            requires_hitl_review = annotations.get('requires_hitl_review', False)
            auto_downscoped = annotations.get('auto_downscoped', False)

            workflow_result['annotations'] = annotations

            log(f"✅ Patch generation completed", 'info')
            log(f"📋 Validation results:", 'info')
            log(f"   🔍 Heuristic flags: {len(heuristic_flags)}", 'info')
            if heuristic_flags:
                for flag in heuristic_flags:
                    log(f"      ⚠️  {flag}", 'warning')

            log(f"   🛡️  Sanity flags: {len(sanity_flags)}", 'info')
            if sanity_flags:
                for flag in sanity_flags:
                    risk = flag.get('risk', 'unknown')
                    reason = flag.get('reason', 'No reason')
                    log(f"      ⚠️  [{risk.upper()}] {reason}", 'warning' if risk != 'high' else 'error')

            log(f"   📊 Sanity review: {sanity_review}", 'info')
            log(f"   🔧 Auto-downscoped: {auto_downscoped}", 'info')
            log(f"   👤 Requires HITL review: {requires_hitl_review}", 'info')

            # Save patch to database
            if save_to_db and self.db and project_id:
                # Remove annotations from patch_json (they go in separate field)
                patch_data = {k: v for k, v in patch_with_annotations.items()
                             if k not in ['annotations', 'sanity_review', 'insufficient_evidence']}

                # Create justification from insights
                import json
                justification_obj = {
                    'insights': insights_result.get('insights', []),
                    'candidates_evaluated': insights_result.get('candidates_evaluated', 0),
                    'selection_method': insights_result.get('selection_method', 'unknown')
                }
                justification = json.dumps(justification_obj, indent=2)

                patch_id = await self.db.create_patch(
                    project_id=project_id,
                    source="insights",
                    patch_json=patch_data,
                    justification=justification,
                    annotations=annotations  # Store heuristic/sanity flags
                )
                log(f"💾 Patch saved to database: {patch_id}", 'info')
                workflow_result['metadata']['patch_id'] = patch_id

            # ================================================================
            # WORKFLOW COMPLETE
            # ================================================================
            workflow_result['metadata'].update({
                'artifacts_processed': len(artifacts),
                'features_count': len(features) if isinstance(features, dict) else 0,
                'insights_count': len(insights_list),
                'candidates_evaluated': candidates_evaluated,
                'heuristic_flags_count': len(heuristic_flags),
                'sanity_flags_count': len(sanity_flags),
                'sanity_review': sanity_review,
                'requires_hitl_review': requires_hitl_review,
                'auto_downscoped': auto_downscoped
            })

            log(f"\n✅ Workflow completed successfully", 'info')
            return workflow_result

        except Exception as e:
            log(f"❌ Workflow failed: {e}", 'error')
            import traceback
            log(traceback.format_exc(), 'error')
            workflow_result['metadata']['error'] = str(e)
            workflow_result['metadata']['error_type'] = type(e).__name__
            raise


    async def run_llm_workflow_with_file_processing(
        self,
        artifact_files: List[str],
        file_processor,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        save_to_db: bool = True,
        logger_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Convenience method that processes files first, then runs workflow

        Args:
            artifact_files: List of file paths to process
            file_processor: FileProcessor instance for content extraction
            project_id: Project ID (required if save_to_db=True)
            run_id: Run ID for logging (optional)
            save_to_db: Whether to save to database
            logger_callback: Custom logging function

        Returns:
            Dict with keys: features, insights_result, patch, annotations, metadata
        """
        def log(message: str, level: str = 'info'):
            if logger_callback:
                logger_callback(message, level)
            else:
                getattr(logger, level)(message)

        log("📥 STEP 0: ARTIFACT PROCESSING", 'info')

        artifacts = []
        for file_path in artifact_files:
            try:
                import os
                from pathlib import Path

                if not os.path.exists(file_path):
                    log(f"❌ File not found: {file_path}", 'error')
                    continue

                file_size = os.path.getsize(file_path)
                file_ext = Path(file_path).suffix

                log(f"📄 Processing: {file_path} ({file_size:,} bytes)", 'info')

                # Read and extract content
                with open(file_path, 'rb') as f:
                    file_content = f.read()

                # Simple extraction for text-based files
                if file_ext in ['.csv', '.json', '.txt', '.md']:
                    content_text = file_content.decode('utf-8')
                else:
                    # For other types, use FileProcessor's internal method
                    content_text = await file_processor._extract_content_from_bytes(
                        file_content,
                        f"text/{file_ext[1:]}",
                        Path(file_path).name
                    )

                artifacts.append({
                    'file_path': file_path,
                    'file_name': Path(file_path).name,
                    'file_type': file_ext,
                    'content': content_text,
                    'summary_json': {'content_preview': content_text[:1000]}
                })

                log(f"   ✅ Extracted {len(content_text):,} characters", 'info')

            except Exception as e:
                log(f"❌ Error processing {file_path}: {e}", 'error')

        if not artifacts:
            log("❌ No valid artifacts to process", 'error')
            return {
                'features': None,
                'insights_result': None,
                'patch': None,
                'annotations': None,
                'metadata': {'error': 'No valid artifacts'}
            }

        log(f"✅ Processed {len(artifacts)} artifacts\n", 'info')

        # Run the workflow
        return await self.run_llm_workflow(
            artifacts=artifacts,
            project_id=project_id,
            run_id=run_id,
            save_to_db=save_to_db,
            logger_callback=logger_callback
        )
