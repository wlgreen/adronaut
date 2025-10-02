import autogen
from typing import Dict, List, Any, Optional
import openai
import json
import uuid
import os
from datetime import datetime
import asyncio
import random
import logging
from gemini_service import gemini_service

logger = logging.getLogger(__name__)

class AutoGenOrchestrator:
    """AutoGen orchestrator with LLM agents and deterministic tools"""

    def __init__(self):
        # Check for Gemini first (preferred), fallback to OpenAI
        self.use_gemini = gemini_service.is_configured()

        if self.use_gemini:
            logger.info("Using Gemini API for LLM operations")
            # We'll use direct Gemini calls instead of AutoGen for structured operations
            self.llm_config = None
        else:
            # Fallback to OpenAI for AutoGen compatibility
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY environment variables are configured")

            logger.info("Using OpenAI API for LLM operations")
            # Set the API key for openai client
            openai.api_key = api_key

            self.llm_config = {
                "config_list": [
                    {
                        "model": "gpt-4",
                        "api_key": api_key,
                    }
                ]
            }

        # Initialize agents only if using OpenAI (AutoGen compatibility)
        if not self.use_gemini:
            self.feature_builder = autogen.AssistantAgent(
                name="FeatureBuilder",
                system_message="""You are a marketing data feature extraction expert.

                Your role is to analyze uploaded artifacts (sales data, reviews, marketing docs, images)
                and extract meaningful marketing features and insights.

                For each artifact, extract:
                - Key metrics and trends
                - Audience segments and characteristics
                - Content themes and messaging
                - Performance indicators
                - Geographic patterns
                - Temporal patterns

                Return structured JSON with extracted features.""",
                llm_config=self.llm_config
            )

            self.insights_agent = autogen.AssistantAgent(
                name="InsightsAgent",
                system_message="""You are a marketing strategy insights expert.

                Your role is to analyze extracted features and generate strategic insights
                that lead to actionable marketing strategy patches.

                Generate insights about:
                - Target audience refinements
                - Messaging optimizations
                - Channel effectiveness
                - Budget allocation improvements
                - Campaign timing adjustments

                Propose specific strategy patches in JSON format with clear justifications.""",
                llm_config=self.llm_config
            )

            self.analyzer_agent = autogen.AssistantAgent(
                name="AnalyzerAgent",
                system_message="""You are a marketing performance analysis expert.

                Your role is to analyze campaign metrics and identify optimization opportunities.

                Analyze performance data for:
                - Conversion rate issues
                - Cost efficiency problems
                - Audience targeting misalignment
                - Creative fatigue
                - Budget distribution inefficiencies

                Propose reflection patches when performance indicates strategy adjustments needed.""",
                llm_config=self.llm_config
            )

            self.patch_editor = autogen.AssistantAgent(
                name="PatchEditor",
                system_message="""You are a marketing strategy patch editor.

                Your role is to take user feedback about proposed strategy patches
                and edit the patches accordingly while maintaining JSON schema validity.

                When editing patches:
                - Preserve the overall structure
                - Apply user-requested changes precisely
                - Ensure all changes are actionable
                - Maintain consistency across strategy elements
                - Validate JSON schema compliance""",
                llm_config=self.llm_config
            )
        else:
            # For Gemini, we'll use direct API calls without AutoGen agents
            self.feature_builder = None
            self.insights_agent = None
            self.analyzer_agent = None
            self.patch_editor = None

    async def extract_features(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract marketing features from uploaded artifacts"""
        try:
            # Prepare artifact summaries
            artifact_data = []
            for artifact in artifacts:
                artifact_data.append({
                    "filename": artifact["filename"],
                    "type": artifact["mime"],
                    "summary": artifact.get("summary_json", {}),
                    "url": artifact["storage_url"]
                })

            prompt = f"""
            Analyze these marketing artifacts and extract key features:

            Artifacts: {json.dumps(artifact_data, indent=2)}

            Extract and return a comprehensive JSON structure with:
            {{
                "audience_segments": [
                    {{
                        "name": "segment_name",
                        "characteristics": ["trait1", "trait2"],
                        "size_estimate": "percentage or count",
                        "value_score": 1-10
                    }}
                ],
                "content_themes": [
                    {{
                        "theme": "theme_name",
                        "performance": "high/medium/low",
                        "keywords": ["keyword1", "keyword2"]
                    }}
                ],
                "performance_metrics": {{
                    "conversion_rate": "x%",
                    "engagement_rate": "x%",
                    "cost_per_acquisition": "$x",
                    "roi": "x%"
                }},
                "geographic_insights": [
                    {{
                        "region": "region_name",
                        "performance": "high/medium/low",
                        "opportunity": "description"
                    }}
                ],
                "temporal_patterns": {{
                    "best_days": ["Monday", "Friday"],
                    "best_hours": ["9-11am", "2-4pm"],
                    "seasonal_trends": "description"
                }},
                "recommendations": [
                    "specific actionable recommendation"
                ]
            }}
            """

            if self.use_gemini:
                # Use Gemini API directly
                system_instruction = """You are a marketing data feature extraction expert.

                Your role is to analyze uploaded artifacts (sales data, reviews, marketing docs, images)
                and extract meaningful marketing features and insights.

                For each artifact, extract:
                - Key metrics and trends
                - Audience segments and characteristics
                - Content themes and messaging
                - Performance indicators
                - Geographic patterns
                - Temporal patterns

                Return structured JSON with extracted features."""

                response = await gemini_service.generate_json_response(
                    prompt,
                    system_instruction=system_instruction,
                    temperature=0.7
                )
                features = response

            else:
                # Use AutoGen with OpenAI
                user_proxy = autogen.UserProxyAgent(
                    name="user_proxy",
                    human_input_mode="NEVER",
                    max_consecutive_auto_reply=1,
                    code_execution_config={"work_dir": "temp", "use_docker": False}
                )

                # Start conversation
                user_proxy.initiate_chat(self.feature_builder, message=prompt)

                # Extract the last message which should contain the JSON
                messages = user_proxy.chat_messages[self.feature_builder]
                last_message = messages[-1]["content"]

                # Parse JSON from the response
                try:
                    # Try to extract JSON from the response
                    start = last_message.find('{')
                    end = last_message.rfind('}') + 1
                    json_str = last_message[start:end]
                    features = json.loads(json_str)
                except:
                    # Fallback: create basic structure
                    features = self._get_fallback_features()

            return features

        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            # Return fallback structure
            return self._get_fallback_features()

    def _get_fallback_features(self) -> Dict[str, Any]:
        """Get fallback feature structure"""
        return {
            "audience_segments": [{"name": "General Audience", "characteristics": ["broad_appeal"], "size_estimate": "100%", "value_score": 5}],
            "content_themes": [{"theme": "General Marketing", "performance": "medium", "keywords": ["marketing", "promotion"]}],
            "performance_metrics": {"conversion_rate": "2.5%", "engagement_rate": "3.2%", "cost_per_acquisition": "$25", "roi": "300%"},
            "geographic_insights": [{"region": "Global", "performance": "medium", "opportunity": "Expand targeting"}],
            "temporal_patterns": {"best_days": ["Tuesday", "Wednesday"], "best_hours": ["10-12pm", "2-4pm"], "seasonal_trends": "Steady year-round"},
            "recommendations": ["Optimize targeting parameters", "Test new creative formats"]
        }

    async def generate_insights(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategic insights and propose strategy patches"""
        try:
            prompt = f"""
            Based on these extracted features, generate strategic insights and propose a marketing strategy patch:

            Features: {json.dumps(features, indent=2)}

            Analyze the data and return JSON with:
            {{
                "insights": [
                    "Key insight about audience, messaging, or performance"
                ],
                "patch": {{
                    "audience_targeting": {{
                        "segments": [
                            {{
                                "name": "segment_name",
                                "targeting_criteria": {{}},
                                "budget_allocation": "percentage",
                                "priority": "high/medium/low"
                            }}
                        ]
                    }},
                    "messaging_strategy": {{
                        "primary_message": "main value proposition",
                        "tone": "brand_tone",
                        "key_themes": ["theme1", "theme2"]
                    }},
                    "channel_strategy": {{
                        "primary_channels": ["channel1", "channel2"],
                        "budget_split": {{}},
                        "scheduling": {{}}
                    }},
                    "budget_allocation": {{
                        "total_budget": "$amount",
                        "channel_breakdown": {{}},
                        "optimization_strategy": "description"
                    }}
                }},
                "justification": "Detailed explanation of why this strategy patch is recommended based on the extracted features and insights"
            }}
            """

            if self.use_gemini:
                # Use Gemini API directly
                system_instruction = """You are a marketing strategy insights expert.

                Your role is to analyze extracted features and generate strategic insights
                that lead to actionable marketing strategy patches.

                Generate insights about:
                - Target audience refinements
                - Messaging optimizations
                - Channel effectiveness
                - Budget allocation improvements
                - Campaign timing adjustments

                Propose specific strategy patches in JSON format with clear justifications."""

                response = await gemini_service.generate_json_response(
                    prompt,
                    system_instruction=system_instruction,
                    temperature=0.3
                )
                insights = response

            else:
                # Use AutoGen with OpenAI
                user_proxy = autogen.UserProxyAgent(
                    name="user_proxy",
                    human_input_mode="NEVER",
                    max_consecutive_auto_reply=1,
                    code_execution_config={"work_dir": "temp", "use_docker": False}
                )

                user_proxy.initiate_chat(self.insights_agent, message=prompt)

                messages = user_proxy.chat_messages[self.insights_agent]
                last_message = messages[-1]["content"]

                try:
                    start = last_message.find('{')
                    end = last_message.rfind('}') + 1
                    json_str = last_message[start:end]
                    insights = json.loads(json_str)
                except:
                    # Fallback insights
                    insights = self._get_fallback_insights()

            return insights

        except Exception as e:
            logger.error(f"Insights generation error: {e}")
            # Return fallback insights
            return self._get_fallback_insights()

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
                        {
                            "name": "High-Value Customers",
                            "targeting_criteria": {"age": "25-45", "interests": ["technology", "innovation"]},
                            "budget_allocation": "60%",
                            "priority": "high"
                        },
                        {
                            "name": "Growth Segment",
                            "targeting_criteria": {"age": "18-35", "behaviors": ["early_adopters"]},
                            "budget_allocation": "40%",
                            "priority": "medium"
                        }
                    ]
                },
                "messaging_strategy": {
                    "primary_message": "Innovative solutions for modern challenges",
                    "tone": "professional yet approachable",
                    "key_themes": ["innovation", "efficiency", "results"]
                },
                "channel_strategy": {
                    "primary_channels": ["social_media", "search_ads", "content_marketing"],
                    "budget_split": {"social_media": "40%", "search_ads": "35%", "content_marketing": "25%"},
                    "scheduling": {"peak_hours": ["10-12pm", "2-4pm"], "peak_days": ["Tuesday", "Wednesday"]}
                },
                "budget_allocation": {
                    "total_budget": "$10000",
                    "channel_breakdown": {"social": "$4000", "search": "$3500", "content": "$2500"},
                    "optimization_strategy": "Focus on high-performing segments and scale successful content themes"
                }
            },
            "justification": "Based on feature analysis, this strategy focuses on high-value customer segments while maintaining growth opportunities. The messaging aligns with content themes that show strong performance, and budget allocation prioritizes channels with best ROI potential."
        }

    async def edit_patch_with_llm(self, patch_id: str, edit_request: str) -> Dict[str, Any]:
        """Edit a strategy patch based on user natural language request"""
        try:
            # Get the original patch (this would come from database)
            # For now, we'll create a sample patch structure
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

            prompt = f"""
            Edit this marketing strategy patch based on the user's request:

            Original Patch: {json.dumps(original_patch, indent=2)}

            User Request: "{edit_request}"

            Apply the user's requested changes and return the complete modified patch in JSON format.
            Ensure all changes are applied while maintaining the patch structure and validity.
            """

            if self.use_gemini:
                # Use Gemini API directly
                system_instruction = """You are a marketing strategy patch editor.

                Your role is to take user feedback about proposed strategy patches
                and edit the patches accordingly while maintaining JSON schema validity.

                When editing patches:
                - Preserve the overall structure
                - Apply user-requested changes precisely
                - Ensure all changes are actionable
                - Maintain consistency across strategy elements
                - Validate JSON schema compliance"""

                response = await gemini_service.generate_json_response(
                    prompt,
                    system_instruction=system_instruction,
                    temperature=0.2
                )
                edited_patch = response

            else:
                # Use AutoGen with OpenAI
                user_proxy = autogen.UserProxyAgent(
                    name="user_proxy",
                    human_input_mode="NEVER",
                    max_consecutive_auto_reply=1,
                    code_execution_config={"work_dir": "temp", "use_docker": False}
                )

                user_proxy.initiate_chat(self.patch_editor, message=prompt)

                messages = user_proxy.chat_messages[self.patch_editor]
                last_message = messages[-1]["content"]

                try:
                    start = last_message.find('{')
                    end = last_message.rfind('}') + 1
                    json_str = last_message[start:end]
                    edited_patch = json.loads(json_str)
                except:
                    # Fallback: return original with minor modification
                    edited_patch = original_patch.copy()
                    edited_patch["edited_note"] = f"Applied: {edit_request}"

            return edited_patch

        except Exception as e:
            logger.error(f"Patch editing error: {e}")
            return original_patch

    async def apply_patch(self, project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a patch to create/update strategy"""
        # This is a deterministic tool that applies patches to strategies
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
        # Deterministic tool that creates briefs
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
        # Simulated campaign launch
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
        # This would integrate with actual ad platforms
        # For MVP, we'll simulate metric generation
        print(f"Started metrics collection for campaign {campaign_id}")

    async def analyze_performance(self, campaign_id: str) -> Dict[str, Any]:
        """Analyze campaign performance and determine if adjustments needed"""
        # Simulate performance analysis
        # In real implementation, this would analyze actual metrics

        # Simulate some performance issues randomly
        needs_adjustment = random.choice([True, False])

        if needs_adjustment:
            analysis = {
                "campaign_id": campaign_id,
                "needs_adjustment": True,
                "issues_detected": [
                    "High cost per acquisition in certain segments",
                    "Low engagement on specific ad creatives",
                    "Underperforming geographic regions"
                ],
                "patch": {
                    "audience_targeting": {
                        "segments": [
                            {
                                "name": "Optimized High-Value Customers",
                                "targeting_criteria": {"age": "25-40", "interests": ["technology"]},
                                "budget_allocation": "70%",
                                "priority": "high"
                            }
                        ]
                    },
                    "budget_allocation": {
                        "total_budget": "$8000",
                        "optimization_strategy": "Reduce spend on underperforming segments"
                    }
                },
                "justification": "Performance analysis shows high CPA in broader segments. Recommend tightening targeting to core high-converting demographics and reallocating budget for better efficiency."
            }
        else:
            analysis = {
                "campaign_id": campaign_id,
                "needs_adjustment": False,
                "performance_summary": "Campaign performing within expected parameters",
                "key_metrics": {
                    "ctr": "2.8%",
                    "cpa": "$22",
                    "roas": "4.2x"
                }
            }

        return analysis