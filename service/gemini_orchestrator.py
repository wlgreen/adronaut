"""
Simple Gemini-based orchestrator for marketing analysis
Uses native Google Gemini API for reliable multi-agent workflows
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

class GeminiOrchestrator:
    """Simple orchestrator using native Gemini API"""

    def __init__(self):
        # Configure Gemini API
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.gemini_api_key and not self.openai_api_key:
            raise ValueError("Either GEMINI_API_KEY or OPENAI_API_KEY environment variable is required")

        # Initialize LLM - prefer Gemini
        if self.gemini_api_key:
            logger.info("✅ Gemini API key found - Using Gemini API for orchestration")
            try:
                genai.configure(api_key=self.gemini_api_key)
                # Initialize Gemini 2.5 Pro model
                self.model = genai.GenerativeModel('gemini-2.5-pro')
                self.use_gemini = True
                logger.info("✅ Gemini API successfully configured with model: gemini-2.5-pro")
            except Exception as e:
                logger.error(f"❌ Failed to configure Gemini API: {e}")
                logger.info("🔄 Falling back to OpenAI API")
                import openai
                openai.api_key = self.openai_api_key
                self.model = None
                self.use_gemini = False
        else:
            logger.info("❌ Gemini API key not available - Using OpenAI API for orchestration")
            import openai
            openai.api_key = self.openai_api_key
            self.model = None
            self.use_gemini = False

        # Log final configuration
        if self.use_gemini:
            logger.info("🤖 AI Provider: Google Gemini 2.5 Pro (Primary)")
        else:
            logger.info("🤖 AI Provider: OpenAI GPT-4o (Fallback)")

    async def extract_features(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Extract marketing features from uploaded artifacts"""
        try:
            logger.info("Starting feature extraction")

            # Prepare artifact summaries for analysis
            artifact_summaries = []
            for artifact in artifacts:
                summary = {
                    "filename": artifact.get("filename", ""),
                    "summary": artifact.get("summary_json", {})
                }
                artifact_summaries.append(summary)

            prompt = f"""
            As a Marketing Data Feature Extractor, analyze the following marketing artifacts and extract key insights:

            Artifacts: {json.dumps(artifact_summaries, indent=2)}

            Extract the following marketing features:
            1. Target audience demographics
            2. Brand positioning
            3. Marketing channels mentioned
            4. Key messaging themes
            5. Campaign objectives
            6. Budget information (if available)
            7. Performance metrics (if available)
            8. Competitive landscape insights

            Return your analysis as a JSON object with these keys:
            - target_audience: object with demographic details
            - brand_positioning: string describing positioning
            - channels: array of marketing channels
            - messaging: array of key themes
            - objectives: array of campaign goals
            - budget_insights: object with budget information
            - metrics: object with performance data
            - competitive_insights: array of competitor observations
            - recommendations: array of improvement suggestions
            """

            if self.use_gemini:
                response = self.model.generate_content(prompt)
                features_text = response.text
            else:
                # OpenAI fallback
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                features_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                features = json.loads(features_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a structured response
                features = {
                    "target_audience": {"description": "Analysis pending"},
                    "brand_positioning": "Analysis pending",
                    "channels": [],
                    "messaging": [],
                    "objectives": [],
                    "budget_insights": {},
                    "metrics": {},
                    "competitive_insights": [],
                    "recommendations": [],
                    "raw_analysis": features_text
                }

            logger.info("Feature extraction completed successfully")
            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {
                "error": str(e),
                "target_audience": {"description": "Analysis failed"},
                "brand_positioning": "Analysis failed",
                "channels": [],
                "messaging": [],
                "objectives": [],
                "budget_insights": {},
                "metrics": {},
                "competitive_insights": [],
                "recommendations": []
            }

    async def generate_insights(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategic insights and patch recommendations"""
        try:
            logger.info("Generating strategic insights")

            prompt = f"""
            As a Marketing Strategy Insights Expert, analyze these extracted features and generate strategic recommendations:

            Features: {json.dumps(features, indent=2)}

            Generate strategic insights including:
            1. Market opportunity analysis
            2. Audience targeting recommendations
            3. Channel optimization suggestions
            4. Messaging improvements
            5. Budget allocation recommendations
            6. Performance optimization strategies

            Return your analysis as a JSON object with these keys:
            - opportunities: array of market opportunities
            - targeting_strategy: object with audience recommendations
            - channel_strategy: object with channel optimization
            - messaging_strategy: object with messaging improvements
            - budget_strategy: object with budget recommendations
            - performance_strategy: object with KPI and optimization recommendations
            - patch: object containing specific strategy modifications to implement
            - justification: string explaining the rationale for these recommendations
            """

            if self.use_gemini:
                response = self.model.generate_content(prompt)
                insights_text = response.text
            else:
                # OpenAI fallback
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                insights_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                insights = json.loads(insights_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a structured response
                insights = {
                    "opportunities": ["Strategic analysis pending"],
                    "targeting_strategy": {"recommendations": "Analysis pending"},
                    "channel_strategy": {"recommendations": "Analysis pending"},
                    "messaging_strategy": {"recommendations": "Analysis pending"},
                    "budget_strategy": {"recommendations": "Analysis pending"},
                    "performance_strategy": {"recommendations": "Analysis pending"},
                    "patch": {
                        "strategy_updates": "Analysis pending",
                        "tactical_changes": "Analysis pending"
                    },
                    "justification": "Strategic analysis in progress",
                    "raw_analysis": insights_text
                }

            logger.info("Strategic insights generated successfully")
            return insights

        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
            return {
                "error": str(e),
                "opportunities": [],
                "targeting_strategy": {},
                "channel_strategy": {},
                "messaging_strategy": {},
                "budget_strategy": {},
                "performance_strategy": {},
                "patch": {},
                "justification": "Analysis failed due to error"
            }

    async def apply_patch(self, project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Apply strategy patch to create updated strategy"""
        try:
            logger.info(f"Applying strategy patch for project {project_id}")

            # Create a comprehensive strategy based on the patch
            strategy = {
                "project_id": project_id,
                "strategy_id": str(uuid.uuid4()),
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "patch_applied": patch,
                "strategy": {
                    "targeting": patch.get("targeting_strategy", {}),
                    "channels": patch.get("channel_strategy", {}),
                    "messaging": patch.get("messaging_strategy", {}),
                    "budget": patch.get("budget_strategy", {}),
                    "performance": patch.get("performance_strategy", {})
                },
                "status": "active"
            }

            logger.info("Strategy patch applied successfully")
            return strategy

        except Exception as e:
            logger.error(f"Patch application failed: {e}")
            return {
                "error": str(e),
                "project_id": project_id,
                "status": "failed"
            }

    async def compile_brief(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Compile strategy into actionable marketing brief"""
        try:
            logger.info("Compiling marketing brief")

            prompt = f"""
            As a Marketing Brief Compiler, create an actionable marketing brief from this strategy:

            Strategy: {json.dumps(strategy, indent=2)}

            Create a comprehensive marketing brief with:
            1. Executive summary
            2. Target audience definition
            3. Key messaging framework
            4. Channel recommendations and tactics
            5. Budget allocation suggestions
            6. Timeline recommendations
            7. Success metrics and KPIs
            8. Implementation guidelines

            Return as a JSON object with these keys:
            - executive_summary: string with brief overview
            - target_audience: object with detailed audience definition
            - messaging_framework: object with key messages and tone
            - channel_tactics: array of specific channel recommendations
            - budget_allocation: object with budget breakdown
            - timeline: object with implementation phases
            - success_metrics: array of KPIs and measurement methods
            - implementation_guide: array of step-by-step actions
            """

            if self.use_gemini:
                response = self.model.generate_content(prompt)
                brief_text = response.text
            else:
                # OpenAI fallback
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                brief_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                brief = json.loads(brief_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a basic brief
                brief = {
                    "executive_summary": "Marketing brief compilation in progress",
                    "target_audience": {"definition": "Analysis pending"},
                    "messaging_framework": {"key_messages": "Analysis pending"},
                    "channel_tactics": ["Recommendations pending"],
                    "budget_allocation": {"status": "Analysis pending"},
                    "timeline": {"phases": "Planning phase"},
                    "success_metrics": ["Metrics definition pending"],
                    "implementation_guide": ["Implementation steps pending"],
                    "raw_brief": brief_text
                }

            brief["brief_id"] = str(uuid.uuid4())
            brief["created_at"] = datetime.utcnow().isoformat()

            logger.info("Marketing brief compiled successfully")
            return brief

        except Exception as e:
            logger.error(f"Brief compilation failed: {e}")
            return {
                "error": str(e),
                "brief_id": str(uuid.uuid4()),
                "status": "failed"
            }

    async def launch_campaign(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Launch marketing campaign based on brief (simulated)"""
        try:
            logger.info("Launching marketing campaign")

            # Simulate campaign launch
            campaign = {
                "campaign_id": str(uuid.uuid4()),
                "brief_id": brief.get("brief_id"),
                "name": f"Campaign {datetime.now().strftime('%Y%m%d_%H%M')}",
                "status": "launched",
                "launched_at": datetime.utcnow().isoformat(),
                "channels": brief.get("channel_tactics", []),
                "budget": brief.get("budget_allocation", {}),
                "metrics": brief.get("success_metrics", []),
                "expected_duration": "30 days",
                "simulation": True
            }

            logger.info("Campaign launched successfully (simulated)")
            return campaign

        except Exception as e:
            logger.error(f"Campaign launch failed: {e}")
            return {
                "error": str(e),
                "campaign_id": str(uuid.uuid4()),
                "status": "failed"
            }

    async def start_metrics_collection(self, campaign_id: str) -> Dict[str, Any]:
        """Start metrics collection for campaign (simulated)"""
        try:
            logger.info(f"Starting metrics collection for campaign {campaign_id}")

            return {
                "campaign_id": campaign_id,
                "metrics_collection": "started",
                "started_at": datetime.utcnow().isoformat(),
                "collection_interval": "daily",
                "simulation": True
            }

        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return {
                "error": str(e),
                "campaign_id": campaign_id,
                "status": "failed"
            }

    async def analyze_performance(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze campaign performance (simulated)"""
        try:
            logger.info(f"Analyzing performance for campaign {campaign_id}")

            # Simulate performance analysis
            analysis = {
                "campaign_id": campaign_id,
                "analysis_date": datetime.utcnow().isoformat(),
                "performance_summary": {
                    "overall_score": 85,
                    "engagement_rate": "12.5%",
                    "conversion_rate": "3.2%",
                    "roi": "2.4x"
                },
                "needs_adjustment": False,  # Simulated good performance
                "recommendations": [
                    "Continue current messaging strategy",
                    "Increase budget allocation to top-performing channels",
                    "Test additional audience segments"
                ],
                "simulation": True
            }

            logger.info("Performance analysis completed")
            return analysis

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {
                "error": str(e),
                "campaign_id": campaign_id,
                "needs_adjustment": True,
                "patch": {"emergency_optimization": "required"}
            }

    async def edit_patch_with_llm(self, patch_id: str, edit_request: str) -> Dict[str, Any]:
        """Edit strategy patch based on user feedback"""
        try:
            logger.info(f"Editing patch {patch_id} with request: {edit_request}")

            prompt = f"""
            As a Marketing Strategy Patch Editor, modify the existing strategy based on this user feedback:

            Edit Request: {edit_request}

            Create an updated strategy patch that incorporates the user's feedback while maintaining strategic coherence.

            Return a JSON object with:
            - updated_patch: object with modified strategy elements
            - changes_made: array describing what was changed
            - rationale: string explaining why changes were made
            - impact_assessment: string describing expected impact
            """

            if self.use_gemini:
                response = self.model.generate_content(prompt)
                edited_text = response.text
            else:
                # OpenAI fallback
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                edited_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                edited_patch = json.loads(edited_text)
            except json.JSONDecodeError:
                edited_patch = {
                    "updated_patch": {"status": "Edit in progress"},
                    "changes_made": ["Processing user feedback"],
                    "rationale": "Analyzing requested modifications",
                    "impact_assessment": "Impact analysis pending",
                    "raw_edit": edited_text
                }

            edited_patch["patch_id"] = str(uuid.uuid4())
            edited_patch["original_patch_id"] = patch_id
            edited_patch["edited_at"] = datetime.utcnow().isoformat()

            logger.info("Patch edited successfully")
            return edited_patch

        except Exception as e:
            logger.error(f"Patch editing failed: {e}")
            return {
                "error": str(e),
                "patch_id": patch_id,
                "status": "edit_failed"
            }

# For backward compatibility, create an alias
CrewAIOrchestrator = GeminiOrchestrator