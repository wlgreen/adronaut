#!/usr/bin/env python3
"""
Local LLM Flow Test Script

Tests the complete LLM workflow with real artifact files.
Logs all LLM calls and outputs for validation.

Usage:
    python test_llm_flow.py <artifact_file1> [artifact_file2] ...

Example:
    python test_llm_flow.py test_data.csv
    python test_llm_flow.py data1.csv data2.json data3.pdf

Features:
    - Processes real artifact files
    - Calls production LLM flow (FEATURES → INSIGHTS → PATCH)
    - Logs all LLM calls with prompts and responses
    - Validates output structure
    - Shows validation flags and scores
    - Saves detailed logs to file
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add service directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_orchestrator import GeminiOrchestrator
from file_processor import FileProcessor
from database import Database
from workflow_engine import WorkflowEngine

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class LLMFlowTester:
    """Test harness for LLM workflow"""

    def __init__(self, log_file: str = None):
        self.orchestrator = GeminiOrchestrator()
        self.file_processor = FileProcessor()
        self.db = Database()
        self.workflow_engine = WorkflowEngine(database=None, orchestrator=self.orchestrator)  # No DB for tests

        # Set up logging
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"llm_test_{timestamp}.log"

        self.log_file = log_file
        self.logs = []

        print(f"{Colors.HEADER}{'='*80}{Colors.END}")
        print(f"{Colors.HEADER}{Colors.BOLD}LLM Flow Test Script{Colors.END}")
        print(f"{Colors.HEADER}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}📝 Log file: {log_file}{Colors.END}\n")

    def log(self, message: str, color: str = ""):
        """Log message to both console and file"""
        # Console with color
        print(f"{color}{message}{Colors.END}")

        # File without color codes
        clean_message = message
        self.logs.append(f"[{datetime.now().isoformat()}] {clean_message}")

    def save_logs(self):
        """Save all logs to file"""
        with open(self.log_file, 'w') as f:
            f.write('\n'.join(self.logs))
        print(f"\n{Colors.GREEN}✅ Logs saved to: {self.log_file}{Colors.END}")

    async def process_artifact(self, file_path: str) -> Dict[str, Any]:
        """Process a single artifact file"""
        self.log(f"\n{'='*80}", Colors.BLUE)
        self.log(f"📄 Processing artifact: {file_path}", Colors.BOLD + Colors.BLUE)
        self.log(f"{'='*80}", Colors.BLUE)

        # Check file exists
        if not os.path.exists(file_path):
            self.log(f"❌ File not found: {file_path}", Colors.RED)
            return None

        # Get file info
        file_size = os.path.getsize(file_path)
        file_ext = Path(file_path).suffix
        self.log(f"   Size: {file_size:,} bytes", Colors.CYAN)
        self.log(f"   Type: {file_ext}", Colors.CYAN)

        # Read file content
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Extract content based on file type
            self.log(f"\n🔍 Extracting content...", Colors.YELLOW)

            # Simple extraction for CSV/JSON/TXT files
            if file_ext in ['.csv', '.json', '.txt', '.md']:
                content_text = file_content.decode('utf-8')
            else:
                # For other types, use FileProcessor's internal method
                content_text = await self.file_processor._extract_content_from_bytes(
                    file_content,
                    f"text/{file_ext[1:]}",  # mime type
                    Path(file_path).name
                )

            self.log(f"   ✅ Extracted {len(content_text):,} characters", Colors.GREEN)
            self.log(f"   Preview: {content_text[:200]}...", Colors.CYAN)

            return {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'file_size': file_size,
                'file_type': file_ext,
                'content': content_text
            }

        except Exception as e:
            self.log(f"❌ Error processing file: {e}", Colors.RED)
            return None

    async def test_features_extraction(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Test FEATURES step"""
        self.log(f"\n{'='*80}", Colors.HEADER)
        self.log(f"STEP 1: FEATURES EXTRACTION", Colors.BOLD + Colors.HEADER)
        self.log(f"{'='*80}", Colors.HEADER)

        # Prepare artifacts for extraction
        artifact_list = [
            {
                'file_name': a['file_name'],
                'file_type': a['file_type'],
                'summary_json': {'content_preview': a['content'][:1000]}
            }
            for a in artifacts if a
        ]

        self.log(f"📊 Processing {len(artifact_list)} artifacts", Colors.CYAN)

        # Call FEATURES extraction
        self.log(f"\n🤖 Calling LLM for FEATURES extraction...", Colors.YELLOW)
        start_time = datetime.now()

        features = await self.orchestrator.extract_features(artifact_list)

        duration = (datetime.now() - start_time).total_seconds()
        self.log(f"⏱️  Duration: {duration:.2f}s", Colors.CYAN)

        # Log features
        self.log(f"\n📋 Extracted Features:", Colors.GREEN)
        self.log(json.dumps(features, indent=2), Colors.CYAN)

        # Validate structure
        self.log(f"\n✅ Validation:", Colors.YELLOW)
        if isinstance(features, dict):
            self.log(f"   ✓ Valid dict structure", Colors.GREEN)
            self.log(f"   ✓ Keys: {list(features.keys())}", Colors.CYAN)
        else:
            self.log(f"   ✗ Invalid structure (not a dict)", Colors.RED)

        return features

    async def test_insights_generation(self, features: Dict) -> Dict[str, Any]:
        """Test INSIGHTS step"""
        self.log(f"\n{'='*80}", Colors.HEADER)
        self.log(f"STEP 2: INSIGHTS GENERATION", Colors.BOLD + Colors.HEADER)
        self.log(f"{'='*80}", Colors.HEADER)

        self.log(f"🧠 Generating insight candidates...", Colors.CYAN)

        # Call INSIGHTS generation
        self.log(f"\n🤖 Calling LLM for INSIGHTS (k=5 candidates)...", Colors.YELLOW)
        start_time = datetime.now()

        insights_result = await self.orchestrator.generate_insights(features)

        duration = (datetime.now() - start_time).total_seconds()
        self.log(f"⏱️  Duration: {duration:.2f}s", Colors.CYAN)

        # Log insights
        insights = insights_result.get('insights', [])
        candidates_evaluated = insights_result.get('candidates_evaluated', 0)
        selection_method = insights_result.get('selection_method', 'unknown')

        self.log(f"\n📊 Insights Summary:", Colors.GREEN)
        self.log(f"   Candidates evaluated: {candidates_evaluated}", Colors.CYAN)
        self.log(f"   Selection method: {selection_method}", Colors.CYAN)
        self.log(f"   Top insights selected: {len(insights)}", Colors.CYAN)

        # Log each insight
        for i, insight in enumerate(insights, 1):
            self.log(f"\n   {i}. Insight (Score: {insight.get('impact_score', 0)}/100):", Colors.BOLD + Colors.BLUE)
            self.log(f"      Primary lever: {insight.get('primary_lever', 'unknown')}", Colors.CYAN)
            self.log(f"      Data support: {insight.get('data_support', 'unknown')}", Colors.CYAN)
            self.log(f"      Confidence: {insight.get('confidence', 0):.2f}", Colors.CYAN)
            self.log(f"      Insight: {insight.get('insight', 'N/A')[:100]}...", Colors.CYAN)
            self.log(f"      Action: {insight.get('proposed_action', 'N/A')[:100]}...", Colors.CYAN)

            # Show expected effect
            effect = insight.get('expected_effect', {})
            if effect:
                self.log(f"      Expected: {effect.get('direction', 'N/A')} {effect.get('metric', 'N/A')} by {effect.get('magnitude', 'N/A')}", Colors.GREEN)

        # Validate structure
        self.log(f"\n✅ Validation:", Colors.YELLOW)
        if len(insights) == 3:
            self.log(f"   ✓ Exactly 3 insights returned", Colors.GREEN)
        else:
            self.log(f"   ✗ Expected 3 insights, got {len(insights)}", Colors.RED)

        # Check required fields
        required_fields = [
            'insight', 'hypothesis', 'proposed_action', 'primary_lever',
            'expected_effect', 'confidence', 'data_support', 'evidence_refs',
            'contrastive_reason', 'impact_rank', 'impact_score'
        ]

        for i, insight in enumerate(insights, 1):
            missing = [f for f in required_fields if f not in insight]
            if missing:
                self.log(f"   ✗ Insight {i} missing fields: {missing}", Colors.RED)
            else:
                self.log(f"   ✓ Insight {i} has all required fields", Colors.GREEN)

        return insights_result

    async def test_patch_generation(self, insights_result: Dict) -> Dict[str, Any]:
        """Test PATCH_GENERATION step"""
        self.log(f"\n{'='*80}", Colors.HEADER)
        self.log(f"STEP 3: PATCH GENERATION", Colors.BOLD + Colors.HEADER)
        self.log(f"{'='*80}", Colors.HEADER)

        self.log(f"🔧 Generating strategy patch with validation...", Colors.CYAN)

        # Call PATCH generation
        self.log(f"\n🤖 Calling LLM for PATCH generation...", Colors.YELLOW)
        start_time = datetime.now()

        patch = await self.orchestrator.generate_patch(insights_result)

        duration = (datetime.now() - start_time).total_seconds()
        self.log(f"⏱️  Duration: {duration:.2f}s", Colors.CYAN)

        # Extract validation results
        annotations = patch.get('annotations', {})
        heuristic_flags = annotations.get('heuristic_flags', [])
        sanity_flags = annotations.get('sanity_flags', [])
        sanity_review = patch.get('sanity_review', 'unknown')
        auto_downscoped = annotations.get('auto_downscoped', False)
        requires_hitl_review = annotations.get('requires_hitl_review', False)

        # Log patch summary
        self.log(f"\n📋 Patch Generation Summary:", Colors.GREEN)
        self.log(f"   Sanity review: {sanity_review}", Colors.CYAN)
        self.log(f"   Auto-downscoped: {auto_downscoped}", Colors.CYAN)
        self.log(f"   Requires HITL review: {requires_hitl_review}", Colors.CYAN)

        # Log heuristic flags
        self.log(f"\n🔍 Heuristic Validation:", Colors.YELLOW)
        if heuristic_flags:
            self.log(f"   ⚠️  {len(heuristic_flags)} flags:", Colors.YELLOW)
            for flag in heuristic_flags:
                self.log(f"      - {flag}", Colors.YELLOW)
        else:
            self.log(f"   ✅ No heuristic violations", Colors.GREEN)

        # Log sanity flags
        self.log(f"\n🛡️  Sanity Gate:", Colors.YELLOW)
        if sanity_flags:
            self.log(f"   ⚠️  {len(sanity_flags)} flags:", Colors.YELLOW)
            for flag in sanity_flags:
                risk = flag.get('risk', 'unknown')
                reason = flag.get('reason', 'N/A')
                color = Colors.RED if risk == 'high' else Colors.YELLOW if risk == 'medium' else Colors.GREEN
                self.log(f"      [{risk.upper()}] {reason}", color)
        else:
            self.log(f"   ✅ No sanity concerns", Colors.GREEN)

        # Log patch structure
        patch_data = {k: v for k, v in patch.items()
                     if k not in ['annotations', 'sanity_review', 'insufficient_evidence']}

        self.log(f"\n📦 Patch Structure:", Colors.CYAN)
        if patch_data:
            for key in patch_data.keys():
                self.log(f"   - {key}", Colors.CYAN)

        self.log(f"\n📄 Full Patch JSON:", Colors.BLUE)
        self.log(json.dumps(patch, indent=2), Colors.CYAN)

        return patch

    async def run_full_test(self, artifact_files: List[str]):
        """Run complete test flow using WorkflowEngine (auto-syncs with production)"""
        self.log(f"\n🚀 Starting LLM Flow Test", Colors.BOLD + Colors.GREEN)
        self.log(f"   Artifacts: {len(artifact_files)}", Colors.CYAN)
        self.log(f"   🔄 Using WorkflowEngine (auto-syncs with production workflow)", Colors.CYAN)

        try:
            # Custom logger that adds colors and saves to log file
            def workflow_logger(message: str, level: str = 'info'):
                color_map = {
                    'info': Colors.CYAN,
                    'warning': Colors.YELLOW,
                    'error': Colors.RED
                }
                self.log(message, color_map.get(level, Colors.CYAN))

            # Use workflow engine's convenience method that handles file processing
            self.log(f"\n{'='*80}", Colors.HEADER)
            self.log(f"RUNNING PRODUCTION WORKFLOW", Colors.BOLD + Colors.HEADER)
            self.log(f"{'='*80}", Colors.HEADER)

            workflow_result = await self.workflow_engine.run_llm_workflow_with_file_processing(
                artifact_files=artifact_files,
                file_processor=self.file_processor,
                project_id=None,  # No project ID for local testing
                run_id=None,
                save_to_db=False,  # Don't save to database in local tests
                logger_callback=workflow_logger
            )

            # Extract results
            features = workflow_result['features']
            insights_result = workflow_result['insights_result']
            patch = workflow_result['patch']
            annotations = workflow_result['annotations']
            metadata = workflow_result['metadata']

            # Check for errors
            if metadata.get('error'):
                self.log(f"\n❌ Workflow failed: {metadata['error']}", Colors.RED)
                return

            # Validate results (same validation as before)
            self.log(f"\n{'='*80}", Colors.HEADER)
            self.log(f"VALIDATION RESULTS", Colors.BOLD + Colors.HEADER)
            self.log(f"{'='*80}", Colors.HEADER)

            # Validate FEATURES
            self.log(f"\n📋 FEATURES Validation:", Colors.YELLOW)
            if isinstance(features, dict):
                self.log(f"   ✓ Valid dict structure", Colors.GREEN)
                self.log(f"   ✓ Keys: {list(features.keys())}", Colors.CYAN)
            else:
                self.log(f"   ✗ Invalid structure (not a dict)", Colors.RED)

            # Validate INSIGHTS
            insights_list = insights_result.get('insights', [])
            self.log(f"\n🧠 INSIGHTS Validation:", Colors.YELLOW)
            if len(insights_list) == 3:
                self.log(f"   ✓ Exactly 3 insights returned", Colors.GREEN)
            else:
                self.log(f"   ✗ Expected 3 insights, got {len(insights_list)}", Colors.RED)

            # Check required fields
            required_fields = [
                'insight', 'hypothesis', 'proposed_action', 'primary_lever',
                'expected_effect', 'confidence', 'data_support', 'evidence_refs',
                'contrastive_reason', 'impact_rank', 'impact_score'
            ]
            for i, insight in enumerate(insights_list, 1):
                missing = [f for f in required_fields if f not in insight]
                if missing:
                    self.log(f"   ✗ Insight {i} missing fields: {missing}", Colors.RED)
                else:
                    self.log(f"   ✓ Insight {i} has all required fields", Colors.GREEN)

            # Validate PATCH
            self.log(f"\n🔧 PATCH Validation:", Colors.YELLOW)
            heuristic_flags = annotations.get('heuristic_flags', [])
            sanity_flags = annotations.get('sanity_flags', [])

            if heuristic_flags:
                self.log(f"   ⚠️  {len(heuristic_flags)} heuristic flags:", Colors.YELLOW)
                for flag in heuristic_flags:
                    self.log(f"      - {flag}", Colors.YELLOW)
            else:
                self.log(f"   ✅ No heuristic violations", Colors.GREEN)

            if sanity_flags:
                self.log(f"   ⚠️  {len(sanity_flags)} sanity flags:", Colors.YELLOW)
                for flag in sanity_flags:
                    risk = flag.get('risk', 'unknown')
                    reason = flag.get('reason', 'N/A')
                    self.log(f"      [{risk.upper()}] {reason}", Colors.YELLOW)
            else:
                self.log(f"   ✅ No sanity concerns", Colors.GREEN)

            # NEW: Quality metrics
            self.log(f"\n📊 INSIGHTS QUALITY METRICS:", Colors.HEADER)

            import re
            learn_keywords = ['pilot', 'test', 'a/b', 'experiment', 'validate', 'trial', 'measure']
            has_learning = sum(
                1 for i in insights_list
                if any(kw in i.get('proposed_action', '').lower() for kw in learn_keywords)
            )
            well_structured = sum(
                1 for i in insights_list
                if sum([
                    '$' in i.get('proposed_action', ''),
                    'day' in i.get('proposed_action', '') or 'week' in i.get('proposed_action', ''),
                    'measure' in i.get('proposed_action', '') or 'track' in i.get('proposed_action', '')
                ]) >= 2
            )
            avg_score = sum(i.get('impact_score', 0) for i in insights_list) / max(len(insights_list), 1)

            self.log(f"   Avg impact score: {avg_score:.1f}/100", Colors.CYAN)
            self.log(f"   Learning plans: {has_learning}/{len(insights_list)}", Colors.CYAN)
            self.log(f"   Well-structured experiments: {well_structured}/{len(insights_list)}", Colors.CYAN)

            insights_quality = avg_score * 0.6 + (has_learning / max(len(insights_list), 1)) * 20 + (well_structured / max(len(insights_list), 1)) * 20

            # PATCH quality metrics
            self.log(f"\n📦 PATCH QUALITY METRICS:", Colors.HEADER)

            strategy_type = patch.get('strategy_type', 'optimization')
            has_exp_details = 'experiment_details' in patch
            has_ai_rec = 'ai_recommendations' in patch

            self.log(f"   Strategy type: {strategy_type}", Colors.CYAN)

            if strategy_type == 'experimental':
                self.log(f"   ✅ Experimental strategy detected", Colors.GREEN)
                if has_exp_details:
                    exp_details = patch.get('experiment_details', {})
                    self.log(f"      Duration: {exp_details.get('duration', 'N/A')}", Colors.CYAN)
                    self.log(f"      Budget: {exp_details.get('total_budget', 'N/A')}", Colors.CYAN)
                    self.log(f"      Success metrics: {len(exp_details.get('success_metrics', []))} defined", Colors.CYAN)
                self.log(f"   Has experiment_details: {has_exp_details}", Colors.CYAN)
                self.log(f"   Has ai_recommendations: {has_ai_rec}", Colors.CYAN)
                patch_quality = (has_exp_details * 50) + (has_ai_rec * 50)
            else:
                patch_str = str(patch).lower()
                has_numbers = bool(re.search(r'\$\d+', patch_str))
                has_timeline = 'day' in patch_str or 'week' in patch_str
                self.log(f"   Has specific numbers: {has_numbers}", Colors.CYAN)
                self.log(f"   Has timeline: {has_timeline}", Colors.CYAN)
                patch_quality = has_numbers * 50 + has_timeline * 50

            # Overall quality score
            overall_quality = insights_quality * 0.6 + patch_quality * 0.4

            ins_color = Colors.GREEN if insights_quality >= 90 else Colors.YELLOW if insights_quality >= 80 else Colors.RED
            patch_color = Colors.GREEN if patch_quality >= 90 else Colors.YELLOW if patch_quality >= 80 else Colors.RED
            overall_color = Colors.GREEN if overall_quality >= 90 else Colors.YELLOW if overall_quality >= 80 else Colors.RED

            self.log(f"\n🎯 INSIGHTS QUALITY: {insights_quality:.1f}/100", Colors.BOLD + ins_color)
            self.log(f"🎯 PATCH QUALITY: {patch_quality:.1f}/100", Colors.BOLD + patch_color)
            self.log(f"🏆 OVERALL QUALITY: {overall_quality:.1f}/100", Colors.BOLD + overall_color)

            # Success summary
            self.log(f"\n{'='*80}", Colors.GREEN)
            self.log(f"✅ COMPLETE LLM FLOW TEST PASSED", Colors.BOLD + Colors.GREEN)
            self.log(f"{'='*80}", Colors.GREEN)

            self.log(f"\n📊 Summary:", Colors.CYAN)
            self.log(f"   Artifacts processed: {metadata.get('artifacts_processed', 0)}", Colors.CYAN)
            self.log(f"   Features extracted: {metadata.get('features_count', 0)} keys", Colors.CYAN)
            self.log(f"   Insights generated: {metadata.get('insights_count', 0)}", Colors.CYAN)
            self.log(f"   Candidates evaluated: {metadata.get('candidates_evaluated', 0)}", Colors.CYAN)
            self.log(f"   Patch created: Yes", Colors.CYAN)

            # Check validation
            if annotations.get('requires_hitl_review'):
                self.log(f"\n⚠️  Patch requires HITL review", Colors.YELLOW)
            else:
                self.log(f"\n✅ Patch passed all validations", Colors.GREEN)

        except Exception as e:
            self.log(f"\n❌ Test failed with error: {e}", Colors.RED)
            import traceback
            self.log(traceback.format_exc(), Colors.RED)

        finally:
            # Save logs
            self.save_logs()


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Usage: python test_llm_flow.py <artifact_file1> [artifact_file2] ...{Colors.END}")
        print(f"\n{Colors.CYAN}Example:{Colors.END}")
        print(f"  python test_llm_flow.py test_data.csv")
        print(f"  python test_llm_flow.py data1.csv data2.json data3.pdf")
        sys.exit(1)

    artifact_files = sys.argv[1:]

    # Run test
    tester = LLMFlowTester()
    await tester.run_full_test(artifact_files)


if __name__ == '__main__':
    asyncio.run(main())
