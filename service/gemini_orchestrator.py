"""
Simple Gemini-based orchestrator for marketing analysis
Uses native Google Gemini API for reliable multi-agent workflows
"""

import os
import json
import uuid
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

class GeminiOrchestrator:
    """Simple orchestrator using native Gemini API"""

    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from response text, handling markdown code blocks"""
        if not response_text:
            return ""

        # Try to extract JSON from markdown code blocks (with greedy matching for multi-line JSON)
        json_pattern = r'```(?:json)?\s*(\{.*\})\s*```'
        matches = re.findall(json_pattern, response_text, re.DOTALL | re.IGNORECASE)

        if matches:
            # Return the first JSON match
            json_text = matches[0].strip()
            logger.debug(f"🔧 Extracted JSON from markdown: {len(json_text)} characters")
            return json_text

        # If no markdown blocks, check if the response is already clean JSON
        stripped = response_text.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            logger.debug(f"🔧 Response appears to be clean JSON: {len(stripped)} characters")
            return stripped

        # If still no clean JSON, try to find JSON-like content (with greedy matching)
        json_pattern_loose = r'\{.*\}'
        match = re.search(json_pattern_loose, response_text, re.DOTALL)
        if match:
            json_text = match.group(0).strip()
            logger.debug(f"🔧 Found JSON-like content: {len(json_text)} characters")
            return json_text

        logger.warning(f"⚠️ No JSON content found in response")
        return ""

    def __init__(self):
        # Configure API keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.gemini_api_key and not self.openai_api_key:
            raise ValueError("Either GEMINI_API_KEY or OPENAI_API_KEY environment variable is required")

        # Per-task LLM configuration with defaults
        # Format: provider:model (e.g., "gemini:gemini-2.5-pro" or "openai:gpt-5")
        self.task_llm_config = {
            'FEATURES': os.getenv('LLM_FEATURES', 'gemini:gemini-2.5-pro'),
            'INSIGHTS': os.getenv('LLM_INSIGHTS', 'openai:gpt-5'),
            'PATCH_PROPOSED': os.getenv('LLM_PATCH', 'openai:gpt-5'),
            'BRIEF': os.getenv('LLM_BRIEF', 'gemini:gemini-2.5-pro'),
            'ANALYZE': os.getenv('LLM_ANALYZE', 'openai:gpt-5'),
            'EDIT': os.getenv('LLM_EDIT', 'openai:gpt-5'),
        }

        # Initialize Gemini if we have the key
        self.gemini_model = None
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.5-pro')
                logger.info("✅ Gemini API configured with model: gemini-2.5-pro")
            except Exception as e:
                logger.error(f"❌ Failed to configure Gemini API: {e}")

        # Initialize OpenAI if we have the key
        self.openai_client = None
        if self.openai_api_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                logger.info("✅ OpenAI API configured")
            except Exception as e:
                logger.error(f"❌ Failed to configure OpenAI API: {e}")

        # Log task-specific LLM configuration
        logger.info("🤖 Per-task LLM Configuration:")
        for task, config in self.task_llm_config.items():
            logger.info(f"   {task}: {config}")

        # Backward compatibility: set use_gemini and model for legacy code
        default_provider = self.task_llm_config.get('FEATURES', '').split(':')[0]
        self.use_gemini = default_provider == 'gemini'
        self.model = self.gemini_model if self.use_gemini else None

    async def _call_llm(self, task: str, prompt: str) -> str:
        """
        Call the configured LLM for the given task
        Args:
            task: Task name (FEATURES, INSIGHTS, PATCH_PROPOSED, etc.)
            prompt: The prompt to send to the LLM
        Returns:
            Response text from the LLM
        """
        config = self.task_llm_config.get(task, 'gemini:gemini-2.5-pro')
        provider, model_name = config.split(':', 1)

        logger.info(f"🤖 [{task}] Using {provider}:{model_name}")

        if provider == 'gemini':
            if not self.gemini_model:
                raise ValueError(f"Gemini model not initialized but required for task {task}")
            response = self.gemini_model.generate_content(prompt)
            return response.text

        elif provider == 'openai':
            if not self.openai_client:
                raise ValueError(f"OpenAI client not initialized but required for task {task}")

            # Note: Some models like o1/gpt-5 only support default temperature (1.0)
            # Don't set temperature to allow model defaults
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert marketing analyst AI."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def extract_features(self, artifacts: List[Dict]) -> Dict[str, Any]:
        """Extract marketing features from uploaded artifacts"""
        try:
            logger.info("Starting feature extraction")
            logger.info(f"📊 Received {len(artifacts)} artifacts for analysis")

            # Prepare artifact summaries for analysis
            artifact_summaries = []
            for i, artifact in enumerate(artifacts):
                summary = {
                    "filename": artifact.get("filename", f"artifact_{i+1}"),
                    "summary": artifact.get("summary_json", {}),
                    "mime_type": artifact.get("mime", ""),
                    "storage_url": artifact.get("storage_url", "")
                }
                artifact_summaries.append(summary)
                logger.debug(f"📄 Artifact {i+1}: {summary['filename']} - Summary length: {len(str(summary['summary']))}")

            # Check if we have meaningful data to analyze
            if not artifacts or all(not artifact.get("summary_json") for artifact in artifacts):
                logger.warning("⚠️ No artifacts or summaries provided - creating placeholder analysis")
                return {
                    "target_audience": {"description": "No artifacts provided for analysis"},
                    "brand_positioning": "Unable to analyze - no marketing artifacts uploaded",
                    "channels": [],
                    "messaging": ["Please upload marketing artifacts for analysis"],
                    "objectives": [],
                    "budget_insights": {"status": "No data available"},
                    "metrics": {"status": "No data available"},
                    "competitive_insights": [],
                    "recommendations": [
                        "Please upload marketing artifacts such as:",
                        "- Campaign briefs and strategy documents",
                        "- Ad copy and creative assets",
                        "- Performance reports and analytics",
                        "- Market research documents",
                        "- Website content and landing pages"
                    ]
                }

            prompt = f"""
            As a Marketing Data Feature Extractor, analyze the following marketing artifacts and extract key insights:

            Number of artifacts: {len(artifact_summaries)}

            Artifacts Data: {json.dumps(artifact_summaries, indent=2)}

            IMPORTANT: Even if the data is limited, provide your best analysis based on available information. Do not ask for more data.

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
            - target_audience: object with demographic details (if data is limited, provide general assumptions)
            - brand_positioning: string describing positioning (if unclear, provide "Not clearly defined" or general observation)
            - channels: array of marketing channels (even if none mentioned, suggest likely channels)
            - messaging: array of key themes (extract any themes present or suggest typical ones)
            - objectives: array of campaign goals (extract explicit goals or infer likely objectives)
            - budget_insights: object with budget information (if none available, note "No budget data available")
            - metrics: object with performance data (if none available, suggest relevant metrics to track)
            - competitive_insights: array of competitor observations (if none available, provide general market insights)
            - recommendations: array of improvement suggestions (always provide actionable recommendations)

            MUST return valid JSON. Do not include any explanatory text outside the JSON structure.
            """

            logger.info("🤖 Sending feature extraction request to configured LLM")
            logger.info(f"📝 Request Details:")
            logger.info(f"   - Prompt length: {len(prompt)} characters")
            logger.info(f"   - Artifacts count: {len(artifacts)}")
            logger.debug(f"📨 Full prompt:\n{prompt}")

            features_text = await self._call_llm('FEATURES', prompt)

            logger.info(f"✅ LLM response received for feature extraction")
            logger.info(f"📤 Response Details:")
            logger.info(f"   - Response length: {len(features_text)} characters")
            logger.debug(f"📋 Full response:\n{features_text}")
            logger.info(f"🔍 Response preview: {features_text[:200]}...")

            # Try to parse JSON response
            try:
                # Extract JSON from response (handling markdown code blocks)
                clean_json = self._extract_json_from_response(features_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", features_text, 0)

                features = json.loads(clean_json)
                logger.info("✅ Successfully parsed JSON response")
                logger.info(f"🔧 Parsed features structure:")
                for key, value in features.items():
                    if isinstance(value, (dict, list)):
                        logger.info(f"   - {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        logger.info(f"   - {key}: {type(value).__name__} = '{str(value)[:50]}...'")
                logger.debug(f"📊 Full parsed features:\n{json.dumps(features, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing failed: {e}")
                logger.error(f"📄 Full raw response that failed to parse:\n{features_text}")
                logger.error(f"🔍 Response analysis:")
                logger.error(f"   - Length: {len(features_text)}")
                logger.error(f"   - Starts with: '{features_text[:50]}'")
                logger.error(f"   - Ends with: '{features_text[-50:]}'")
                logger.error(f"   - Contains JSON markers: {'{' in features_text and '}' in features_text}")
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
                logger.info("🔧 Created fallback structured response")

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

    async def extract_features_direct(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract marketing features directly from file content without DB roundtrip"""
        try:
            logger.info("Starting direct feature extraction from file content")
            logger.info(f"📊 Processing file: {file_data.get('filename', 'unknown')}")

            # Create artifact-like structure for analysis
            artifact_data = {
                "filename": file_data.get("filename", "uploaded_file"),
                "summary_json": {
                    "content_type": file_data.get("content_type", "unknown"),
                    "file_size": file_data.get("file_size", 0),
                    "extracted_content": file_data.get("extracted_content", "")[:5000],  # Limit content for prompt
                    "processing_method": "direct_upload"
                },
                "mime": file_data.get("content_type", "unknown"),
                "storage_url": f"memory://{file_data.get('filename', 'unknown')}"
            }

            # Use the existing extract_features method with our direct data
            return await self.extract_features([artifact_data])

        except Exception as e:
            logger.error(f"Direct feature extraction failed: {e}")
            return {
                "error": str(e),
                "target_audience": {"description": "Direct analysis failed"},
                "brand_positioning": "Direct analysis failed",
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

            logger.info("🤖 Sending insights request to configured LLM")
            logger.info(f"📝 Request Details:")
            logger.info(f"   - Prompt length: {len(prompt)} characters")
            logger.debug(f"📨 Full insights prompt:\n{prompt}")

            insights_text = await self._call_llm('INSIGHTS', prompt)

            logger.info(f"✅ LLM insights response received")
            logger.info(f"📤 Response length: {len(insights_text)} characters")
            logger.debug(f"📋 Full insights response:\n{insights_text}")
            logger.info(f"🔍 Insights preview: {insights_text[:200]}...")

            # Try to parse JSON response
            try:
                # Extract JSON from response (handling markdown code blocks)
                clean_json = self._extract_json_from_response(insights_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", insights_text, 0)

                insights = json.loads(clean_json)
                logger.info("✅ Successfully parsed insights JSON response")
                logger.info(f"🔧 Insights structure:")
                for key, value in insights.items():
                    if isinstance(value, (dict, list)):
                        logger.info(f"   - {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        logger.info(f"   - {key}: {type(value).__name__}")
                logger.debug(f"📊 Full parsed insights:\n{json.dumps(insights, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Insights JSON parsing failed: {e}")
                logger.error(f"📄 Full insights response that failed to parse:\n{insights_text}")
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

            logger.info("🤖 Sending brief compilation request to configured LLM")
            logger.info(f"📝 Request Details:")
            logger.info(f"   - Prompt length: {len(prompt)} characters")
            logger.debug(f"📨 Full brief prompt:\n{prompt}")

            brief_text = await self._call_llm('BRIEF', prompt)

            logger.info(f"✅ LLM brief response received")
            logger.info(f"📤 Response length: {len(brief_text)} characters")
            logger.debug(f"📋 Full brief response:\n{brief_text}")
            logger.info(f"🔍 Brief preview: {brief_text[:200]}...")

            # Try to parse JSON response
            try:
                # Extract JSON from response (handling markdown code blocks)
                clean_json = self._extract_json_from_response(brief_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", brief_text, 0)

                brief = json.loads(clean_json)
                logger.info("✅ Successfully parsed brief JSON response")
                logger.info(f"🔧 Brief structure:")
                for key, value in brief.items():
                    if isinstance(value, (dict, list)):
                        logger.info(f"   - {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        logger.info(f"   - {key}: {type(value).__name__}")
                logger.debug(f"📊 Full parsed brief:\n{json.dumps(brief, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Brief JSON parsing failed: {e}")
                logger.error(f"📄 Full brief response that failed to parse:\n{brief_text}")
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

            logger.info(f"🤖 Sending patch edit request to configured LLM for patch {patch_id}")
            logger.info(f"📝 Request Details:")
            logger.info(f"   - Edit request: '{edit_request}'")
            logger.info(f"   - Prompt length: {len(prompt)} characters")
            logger.debug(f"📨 Full edit prompt:\n{prompt}")

            edited_text = await self._call_llm('EDIT', prompt)

            logger.info(f"✅ LLM edit response received")
            logger.info(f"📤 Response length: {len(edited_text)} characters")
            logger.debug(f"📋 Full edit response:\n{edited_text}")
            logger.info(f"🔍 Edit preview: {edited_text[:200]}...")

            # Try to parse JSON response
            try:
                # Extract JSON from response (handling markdown code blocks)
                clean_json = self._extract_json_from_response(edited_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", edited_text, 0)

                edited_patch = json.loads(clean_json)
                logger.info("✅ Successfully parsed edited patch JSON response")
                logger.info(f"🔧 Edited patch structure:")
                for key, value in edited_patch.items():
                    if isinstance(value, (dict, list)):
                        logger.info(f"   - {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        logger.info(f"   - {key}: {type(value).__name__}")
                logger.debug(f"📊 Full parsed edited patch:\n{json.dumps(edited_patch, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Edited patch JSON parsing failed: {e}")
                logger.error(f"📄 Full edit response that failed to parse:\n{edited_text}")
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