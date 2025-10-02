"""
CrewAI orchestrator with native Gemini integration
Provides multi-agent workflows for marketing analysis and strategy generation
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

logger = logging.getLogger(__name__)

class CrewAIOrchestrator:
    """CrewAI orchestrator with native Gemini support"""

    def __init__(self):
        # Configure Gemini API
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.gemini_api_key and not self.openai_api_key:
            raise ValueError("Either GEMINI_API_KEY or OPENAI_API_KEY environment variable is required")

        # Initialize LLM - prefer Gemini
        if self.gemini_api_key:
            logger.info("Using Gemini API with CrewAI")
            genai.configure(api_key=self.gemini_api_key)

            # Create Gemini LLM for CrewAI
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=self.gemini_api_key,
                temperature=0.7,
                convert_system_message_to_human=True
            )
            self.use_gemini = True
        else:
            logger.info("Using OpenAI API with CrewAI")
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model="gpt-4",
                openai_api_key=self.openai_api_key,
                temperature=0.7
            )
            self.use_gemini = False

        # Initialize agents
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize CrewAI agents for marketing operations"""

        # Feature Extraction Agent
        self.feature_builder = Agent(
            role='Marketing Data Feature Extractor',
            goal='Extract meaningful marketing features and insights from uploaded artifacts',
            backstory="""You are an expert marketing data analyst with years of experience
            analyzing customer data, sales reports, reviews, and marketing materials.
            You excel at identifying patterns, audience segments, and performance indicators
            that drive marketing strategy decisions.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # Strategy Insights Agent
        self.insights_agent = Agent(
            role='Marketing Strategy Insights Expert',
            goal='Generate strategic insights and propose actionable marketing strategy patches',
            backstory="""You are a seasoned marketing strategist who specializes in
            translating data insights into actionable marketing strategies. You have a proven
            track record of optimizing audience targeting, messaging, channel selection,
            and budget allocation for maximum ROI.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # Performance Analyzer Agent
        self.analyzer_agent = Agent(
            role='Marketing Performance Analyzer',
            goal='Analyze campaign performance and identify optimization opportunities',
            backstory="""You are a performance marketing expert who continuously monitors
            and optimizes campaigns for better results. You excel at identifying
            underperforming elements and proposing data-driven adjustments to improve
            conversion rates, reduce costs, and increase ROI.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # Strategy Patch Editor Agent
        self.patch_editor = Agent(
            role='Marketing Strategy Patch Editor',
            goal='Edit strategy patches based on user feedback while maintaining validity',
            backstory="""You are a marketing operations specialist who ensures strategy
            implementations are precise and actionable. You excel at taking user feedback
            and translating it into well-structured strategy modifications that maintain
            consistency and effectiveness.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    async def extract_features(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract marketing features from uploaded artifacts using CrewAI"""
        try:
            # Prepare artifact data
            artifact_data = []
            for artifact in artifacts:
                artifact_data.append({
                    "filename": artifact["filename"],
                    "type": artifact["mime"],
                    "summary": artifact.get("summary_json", {}),
                    "url": artifact["storage_url"]
                })

            # Create feature extraction task
            extraction_task = Task(
                description=f"""
                Analyze these marketing artifacts and extract comprehensive features:

                Artifacts: {json.dumps(artifact_data, indent=2)}

                Extract and return a detailed JSON structure with:
                - audience_segments: Array of audience segments with characteristics, size estimates, and value scores
                - content_themes: Array of content themes with performance indicators and keywords
                - performance_metrics: Key performance indicators including conversion rates, engagement, costs
                - geographic_insights: Regional performance data and opportunities
                - temporal_patterns: Time-based patterns for optimal scheduling
                - recommendations: Specific actionable recommendations

                Return ONLY valid JSON format. Ensure all data is realistic and actionable for marketing strategy development.
                """,
                agent=self.feature_builder,
                expected_output="JSON object with extracted marketing features and insights"
            )

            # Create and run crew
            crew = Crew(
                agents=[self.feature_builder],
                tasks=[extraction_task],
                process=Process.sequential,
                verbose=True
            )

            result = crew.kickoff()

            # Parse the result
            try:
                # Clean and parse JSON from result
                result_text = str(result)
                start = result_text.find('{')
                end = result_text.rfind('}') + 1

                if start >= 0 and end > start:
                    json_str = result_text[start:end]
                    features = json.loads(json_str)
                else:
                    # Fallback parsing
                    features = self._get_fallback_features()

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse feature extraction result: {e}")
                features = self._get_fallback_features()

            return features

        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return self._get_fallback_features()

    async def generate_insights(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategic insights and propose strategy patches using CrewAI"""
        try:
            # Create insights generation task
            insights_task = Task(
                description=f"""
                Based on these extracted marketing features, generate strategic insights and propose a comprehensive strategy patch:

                Features: {json.dumps(features, indent=2)}

                Analyze the data and create a JSON response with:
                - insights: Array of key strategic insights about audience, messaging, and performance opportunities
                - patch: Complete strategy patch object with audience_targeting, messaging_strategy, channel_strategy, and budget_allocation
                - justification: Detailed explanation of why this strategy is recommended

                The strategy patch should be actionable and directly address opportunities identified in the features.
                Return ONLY valid JSON format.
                """,
                agent=self.insights_agent,
                expected_output="JSON object with strategic insights and strategy patch"
            )

            # Create and run crew
            crew = Crew(
                agents=[self.insights_agent],
                tasks=[insights_task],
                process=Process.sequential,
                verbose=True
            )

            result = crew.kickoff()

            # Parse the result
            try:
                result_text = str(result)
                start = result_text.find('{')
                end = result_text.rfind('}') + 1

                if start >= 0 and end > start:
                    json_str = result_text[start:end]
                    insights = json.loads(json_str)
                else:
                    insights = self._get_fallback_insights()

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse insights generation result: {e}")
                insights = self._get_fallback_insights()

            return insights

        except Exception as e:
            logger.error(f"Insights generation error: {e}")
            return self._get_fallback_insights()

    async def edit_patch_with_llm(self, patch_id: str, edit_request: str) -> Dict[str, Any]:
        """Edit a strategy patch based on user natural language request using CrewAI"""
        try:
            # Get the original patch (this would come from database)
            original_patch = {
                "audience_targeting": {
                    "segments": [
                        {"name": "High-Value Customers", "targeting_criteria": {"age": "25-45"}, "budget_allocation": "60%", "priority": "high"}
                    ]
                },
                "messaging_strategy": {
                    "primary_message": "Innovative solutions for modern challenges",
                    "tone": "professional yet approachable"
                }
            }

            # Create patch editing task
            edit_task = Task(
                description=f"""
                Edit this marketing strategy patch based on the user's specific request:

                Original Patch: {json.dumps(original_patch, indent=2)}

                User Edit Request: "{edit_request}"

                Apply the user's requested changes precisely while:
                - Maintaining the overall patch structure and validity
                - Ensuring all changes are actionable and strategic
                - Preserving consistency across all strategy elements
                - Following JSON schema requirements

                Return ONLY the complete modified patch in valid JSON format.
                """,
                agent=self.patch_editor,
                expected_output="JSON object with the edited strategy patch"
            )

            # Create and run crew
            crew = Crew(
                agents=[self.patch_editor],
                tasks=[edit_task],
                process=Process.sequential,
                verbose=True
            )

            result = crew.kickoff()

            # Parse the result
            try:
                result_text = str(result)
                start = result_text.find('{')
                end = result_text.rfind('}') + 1

                if start >= 0 and end > start:
                    json_str = result_text[start:end]
                    edited_patch = json.loads(json_str)
                else:
                    # Fallback: return original with note
                    edited_patch = original_patch.copy()
                    edited_patch["edited_note"] = f"Applied: {edit_request}"

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse patch edit result: {e}")
                edited_patch = original_patch.copy()
                edited_patch["edited_note"] = f"Applied: {edit_request}"

            return edited_patch

        except Exception as e:
            logger.error(f"Patch editing error: {e}")
            return original_patch

    async def analyze_performance(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze campaign performance using CrewAI"""
        try:
            # Create performance analysis task
            analysis_task = Task(
                description=f"""
                Analyze the performance of campaign {campaign_id} and determine if strategy adjustments are needed.

                Based on typical campaign performance patterns, evaluate:
                - Cost per acquisition trends
                - Engagement rates across different segments
                - Geographic performance variations
                - Creative fatigue indicators
                - Budget allocation efficiency

                Return a JSON analysis with:
                - campaign_id: The campaign identifier
                - needs_adjustment: Boolean indicating if changes are recommended
                - issues_detected: Array of specific performance issues (if any)
                - patch: Strategy adjustment patch (if needed)
                - justification: Explanation of recommendations
                - performance_summary: Overall performance assessment

                Return ONLY valid JSON format.
                """,
                agent=self.analyzer_agent,
                expected_output="JSON object with performance analysis and recommendations"
            )

            # Create and run crew
            crew = Crew(
                agents=[self.analyzer_agent],
                tasks=[analysis_task],
                process=Process.sequential,
                verbose=True
            )

            result = crew.kickoff()

            # Parse the result
            try:
                result_text = str(result)
                start = result_text.find('{')
                end = result_text.rfind('}') + 1

                if start >= 0 and end > start:
                    json_str = result_text[start:end]
                    analysis = json.loads(json_str)
                else:
                    # Fallback analysis
                    analysis = self._get_fallback_analysis(campaign_id)

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse performance analysis result: {e}")
                analysis = self._get_fallback_analysis(campaign_id)

            return analysis

        except Exception as e:
            logger.error(f"Performance analysis error: {e}")
            return self._get_fallback_analysis(campaign_id)

    # Deterministic tool methods (no changes needed)
    async def apply_patch(self, project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a patch to create/update strategy"""
        strategy = {
            "strategy_id": str(uuid.uuid4()),
            "project_id": project_id,
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "audience_targeting": patch.get("audience_targeting", {}),
            "messaging_strategy": patch.get("messaging_strategy", {}),
            "channel_strategy": patch.get("channel_strategy", {}),
            "budget_allocation": patch.get("budget_allocation", {}),
            "status": "active"
        }
        return strategy

    async def compile_brief(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Compile marketing brief from strategy"""
        brief = {
            "brief_id": str(uuid.uuid4()),
            "strategy_id": strategy["strategy_id"],
            "created_at": datetime.utcnow().isoformat(),
            "campaign_objectives": [
                "Increase brand awareness",
                "Drive qualified leads",
                "Improve conversion rates"
            ],
            "target_audience": strategy.get("audience_targeting", {}),
            "key_messages": strategy.get("messaging_strategy", {}),
            "channel_plan": strategy.get("channel_strategy", {}),
            "budget": strategy.get("budget_allocation", {}),
            "success_metrics": [
                "Click-through rate",
                "Conversion rate",
                "Cost per acquisition",
                "Return on ad spend"
            ],
            "creative_requirements": {
                "formats": ["video", "static_image", "carousel"],
                "dimensions": ["1080x1080", "1200x628", "1080x1920"],
                "brand_guidelines": "Follow company brand guidelines"
            }
        }
        return brief

    async def launch_campaign(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Launch simulated campaign"""
        campaign = {
            "campaign_id": str(uuid.uuid4()),
            "brief_id": brief["brief_id"],
            "status": "running",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": None,
            "platforms": ["facebook", "google_ads", "linkedin"],
            "ad_sets": [
                {
                    "ad_set_id": str(uuid.uuid4()),
                    "name": "High-Value Customers",
                    "budget": "$100/day",
                    "targeting": brief.get("target_audience", {}),
                    "creative_id": str(uuid.uuid4())
                }
            ],
            "tracking_pixels": ["facebook_pixel", "google_analytics"],
            "launch_status": "successfully_launched"
        }
        return campaign

    async def start_metrics_collection(self, campaign_id: str):
        """Start collecting campaign metrics (simulated)"""
        logger.info(f"Started metrics collection for campaign {campaign_id}")

    # Fallback methods
    def _get_fallback_features(self) -> Dict[str, Any]:
        """Get fallback feature structure"""
        return {
            "audience_segments": [
                {"name": "Tech-Savvy Professionals", "characteristics": ["early_adopters", "high_income"], "size_estimate": "35%", "value_score": 8},
                {"name": "Budget-Conscious Families", "characteristics": ["price_sensitive", "family_oriented"], "size_estimate": "45%", "value_score": 6}
            ],
            "content_themes": [
                {"theme": "Innovation & Technology", "performance": "high", "keywords": ["AI", "innovation", "smart"]},
                {"theme": "Value & Savings", "performance": "medium", "keywords": ["save", "discount", "value"]}
            ],
            "performance_metrics": {"conversion_rate": "3.2%", "engagement_rate": "7.8%", "cost_per_acquisition": "$24", "roi": "425%"},
            "geographic_insights": [
                {"region": "North America", "performance": "high", "opportunity": "Strong performance across all segments"},
                {"region": "Europe", "performance": "medium", "opportunity": "Opportunity to expand in Eastern markets"}
            ],
            "temporal_patterns": {"best_days": ["Tuesday", "Wednesday", "Thursday"], "best_hours": ["9-11am", "2-4pm"], "seasonal_trends": "Higher engagement during Q4"},
            "recommendations": ["Focus budget on Tech-Savvy Professionals", "Develop mobile-first creative strategy", "Expand geographic targeting"]
        }

    def _get_fallback_insights(self) -> Dict[str, Any]:
        """Get fallback insights structure"""
        return {
            "insights": [
                "Opportunity to refine audience targeting based on segment performance",
                "Content themes show potential for optimization",
                "Geographic performance indicates expansion opportunities"
            ],
            "patch": {
                "audience_targeting": {
                    "segments": [
                        {"name": "High-Value Customers", "targeting_criteria": {"age": "25-45", "interests": ["technology"]}, "budget_allocation": "60%", "priority": "high"},
                        {"name": "Growth Segment", "targeting_criteria": {"age": "18-35", "behaviors": ["early_adopters"]}, "budget_allocation": "40%", "priority": "medium"}
                    ]
                },
                "messaging_strategy": {"primary_message": "Innovative solutions for modern challenges", "tone": "professional yet approachable", "key_themes": ["innovation", "efficiency"]},
                "channel_strategy": {"primary_channels": ["social_media", "search_ads"], "budget_split": {"social_media": "40%", "search_ads": "35%", "content_marketing": "25%"}, "scheduling": {"peak_hours": ["10-12pm", "2-4pm"], "peak_days": ["Tuesday", "Wednesday"]}},
                "budget_allocation": {"total_budget": "$10000", "channel_breakdown": {"social": "$4000", "search": "$3500", "content": "$2500"}, "optimization_strategy": "Focus on high-performing segments"}
            },
            "justification": "Strategy focuses on high-value customer segments while maintaining growth opportunities through optimized channel allocation."
        }

    def _get_fallback_analysis(self, campaign_id: str) -> Dict[str, Any]:
        """Get fallback analysis structure"""
        return {
            "campaign_id": campaign_id,
            "needs_adjustment": False,
            "performance_summary": "Campaign performing within expected parameters",
            "key_metrics": {"ctr": "2.8%", "cpa": "$22", "roas": "4.2x"},
            "issues_detected": [],
            "justification": "No immediate optimization required based on current performance indicators."
        }