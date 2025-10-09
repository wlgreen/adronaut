"""
Simple Gemini-based orchestrator for marketing analysis
Uses native Google Gemini API for reliable multi-agent workflows
"""

import os
import json
import uuid
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Task-specific temperature configuration for determinism
TASK_TEMPERATURES = {
    'FEATURES': 0.2,     # Deterministic extraction
    'INSIGHTS': 0.35,    # Moderate creativity for hypotheses
    'PATCH': 0.2,        # Deterministic patch generation
    'EDIT': 0.2,         # Minimal changes only
    'BRIEF': 0.3,        # Slightly creative for brief
    'ANALYZE': 0.35      # Moderate for performance analysis
}

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
        # Format: provider:model (e.g., "gemini:gemini-2.5-flash" or "openai:gpt-4o")
        self.task_llm_config = {
            'FEATURES': os.getenv('LLM_FEATURES', 'gemini:gemini-2.5-flash'),
            'INSIGHTS': os.getenv('LLM_INSIGHTS', 'gemini:gemini-2.5-flash'),
            'PATCH_PROPOSED': os.getenv('LLM_PATCH', 'gemini:gemini-2.5-flash'),
            'BRIEF': os.getenv('LLM_BRIEF', 'gemini:gemini-2.5-flash'),
            'ANALYZE': os.getenv('LLM_ANALYZE', 'gemini:gemini-2.5-flash'),
            'EDIT': os.getenv('LLM_EDIT', 'gemini:gemini-2.5-flash'),
        }

        # Initialize Gemini if we have the key
        self.gemini_model = None
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("✅ Gemini API configured with model: gemini-2.5-flash")
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
        Call the configured LLM for the given task with temperature control
        Args:
            task: Task name (FEATURES, INSIGHTS, PATCH, etc.)
            prompt: The prompt to send to the LLM
        Returns:
            Response text from the LLM
        """
        from .logging_metrics import LLMMetrics

        config = self.task_llm_config.get(task, 'gemini:gemini-2.5-flash')
        provider, model_name = config.split(':', 1)
        temperature = TASK_TEMPERATURES.get(task, 0.3)

        logger.info(f"🤖 [{task}] Using {provider}:{model_name} @ temperature={temperature}")

        start_time = time.time()
        prompt_length = len(prompt)

        try:
            if provider == 'gemini':
                if not self.gemini_model:
                    raise ValueError(f"Gemini model not initialized but required for task {task}")

                # Gemini supports temperature control (0.0-2.0)
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature
                    )
                )
                response_text = response.text

            elif provider == 'openai':
                if not self.openai_client:
                    raise ValueError(f"OpenAI client not initialized but required for task {task}")

                # OpenAI - use temperature if supported by model
                # Note: o1/gpt-5 reasoning models don't support temperature (use Gemini instead)
                response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert marketing analyst AI."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature
                )
                response_text = response.choices[0].message.content

            else:
                raise ValueError(f"Unknown LLM provider: {provider}")

            # Log successful call
            latency_ms = int((time.time() - start_time) * 1000)
            LLMMetrics.log_llm_call(
                task=task,
                provider=provider,
                model=model_name,
                temperature=temperature,
                latency_ms=latency_ms,
                prompt_length=prompt_length,
                response_length=len(response_text),
                success=True
            )

            return response_text

        except Exception as e:
            # Log failed call
            latency_ms = int((time.time() - start_time) * 1000)
            LLMMetrics.log_llm_call(
                task=task,
                provider=provider,
                model=model_name,
                temperature=temperature,
                latency_ms=latency_ms,
                prompt_length=prompt_length,
                response_length=0,
                success=False,
                error=str(e)
            )
            raise

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

            CRITICAL: Base all claims on evidence present in the artifacts.
            If data is insufficient for a claim, explicitly state "insufficient_evidence" in that field.
            DO NOT speculate or guess. Only extract features that are directly supported by the artifact data.

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
        """Generate k=5 insight candidates, score, and select top 3 (NO patch)"""
        try:
            from .mechanics_cheat_sheet import MECHANICS_CHEAT_SHEET
            from .insights_selector import (
                select_top_insights,
                validate_insight_structure,
                count_data_support_distribution,
                calculate_insufficient_evidence_rate
            )
            from .logging_metrics import LLMMetrics
            import uuid

            start_time = time.time()
            job_id = str(uuid.uuid4())

            logger.info(f"[JOB {job_id[:8]}] Generating insight candidates with mechanics-guided prompting")

            prompt = f"""
{MECHANICS_CHEAT_SHEET}

As a Marketing Strategy Insights Expert, analyze these extracted features and generate strategic insights:

Features: {json.dumps(features, indent=2)}

**CRITICAL RULES:**
1. Base all claims on evidence present in features. If insufficient data, set data_support="weak"
2. Each insight must target exactly ONE primary lever from: audience, creative, budget, bidding, funnel
3. Include expected_effect with direction (increase/decrease) + magnitude (small/medium/large)
4. Add evidence_refs pointing to specific feature fields that support your claim
5. If data_support="weak", propose learn/test action (pilot, A/B test, limited budget experiment)
6. Provide contrastive reasoning: explain why you recommend X instead of alternative Y

Generate 5 insight candidates. For each candidate, return this exact JSON structure:

{{
  "insight": "Observable pattern or anomaly from the data",
  "hypothesis": "Causal explanation for why this pattern exists",
  "proposed_action": "Specific, actionable recommendation",
  "primary_lever": "audience" | "creative" | "budget" | "bidding" | "funnel",
  "expected_effect": {{
    "direction": "increase" | "decrease",
    "metric": "CTR" | "conversion_rate" | "CPA" | "ROAS" | "engagement_rate" | etc,
    "magnitude": "small" | "medium" | "large",
    "range": "Optional: e.g., 10-20%"
  }},
  "confidence": 0.0 to 1.0,
  "data_support": "strong" | "moderate" | "weak",
  "evidence_refs": ["features.field_name", "features.another_field"],
  "contrastive_reason": "Why this recommendation vs why not alternative approach"
}}

Return JSON with:
{{
  "candidates": [... 5 insight objects ...]
}}

DO NOT include a "patch" field. DO NOT speculate beyond what evidence supports.
"""

            logger.info(f"📝 Insights prompt length: {len(prompt)} characters")
            logger.debug(f"📨 Full insights prompt:\n{prompt}")

            # Call LLM @ temp=0.35 (moderate creativity for hypotheses)
            insights_text = await self._call_llm('INSIGHTS', prompt)

            logger.info(f"✅ LLM response received ({len(insights_text)} chars)")
            logger.debug(f"📋 Full response:\n{insights_text}")

            # Parse JSON response
            try:
                clean_json = self._extract_json_from_response(insights_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", insights_text, 0)

                result = json.loads(clean_json)
                candidates = result.get('candidates', [])

                logger.info(f"📊 Received {len(candidates)} insight candidates")

                # Validate and select top 3
                valid_candidates = [c for c in candidates if validate_insight_structure(c)]
                logger.info(f"✅ {len(valid_candidates)}/{len(candidates)} candidates passed validation")

                if len(valid_candidates) < 3:
                    logger.warning(f"⚠️ Only {len(valid_candidates)} valid candidates, expected ≥3")

                top_3 = select_top_insights(valid_candidates, k=3)
                logger.info(f"🎯 Selected top 3 insights with scores: {[i['impact_score'] for i in top_3]}")

                # Calculate metrics for logging
                latency_ms = int((time.time() - start_time) * 1000)
                data_support_counts = count_data_support_distribution(top_3)
                insufficient_rate = calculate_insufficient_evidence_rate(top_3)

                # Log metrics
                LLMMetrics.log_insights_job(
                    job_id=job_id,
                    latency_ms=latency_ms,
                    temperature=TASK_TEMPERATURES['INSIGHTS'],
                    candidate_count=len(candidates),
                    selected_score=top_3[0]['impact_score'] if top_3 else 0,
                    has_evidence_refs=any(len(i.get('evidence_refs', [])) > 0 for i in top_3),
                    data_support_counts=data_support_counts,
                    insufficient_evidence_rate=insufficient_rate
                )

                logger.info("✅ Strategic insights generated successfully (NO patch)")

                # Return insights WITHOUT patch (breaking change from old flow)
                return {
                    'insights': top_3,
                    'candidates_evaluated': len(candidates),
                    'selection_method': 'deterministic_rubric'
                }

            except json.JSONDecodeError as e:
                logger.error(f"❌ Insights JSON parsing failed: {e}")
                logger.error(f"📄 Full response that failed to parse:\n{insights_text}")
                # Return fallback with minimal structure
                return {
                    "insights": [],
                    "candidates_evaluated": 0,
                    "selection_method": "failed_parse",
                    "error": str(e),
                    "raw_analysis": insights_text
                }

        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
            return {
                "error": str(e),
                "insights": [],
                "candidates_evaluated": 0,
                "selection_method": "failed_execution"
            }

    async def generate_patch(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Generate StrategyPatch from insights with heuristic filters and sanity gate"""
        try:
            from .heuristic_filters import HeuristicFilters
            from .sanity_gate import SanityGate
            from .logging_metrics import LLMMetrics
            import uuid

            start_time = time.time()
            job_id = str(uuid.uuid4())

            logger.info(f"[JOB {job_id[:8]}] Generating strategy patch from insights")

            # Extract the insights list from the insights response
            insights_list = insights.get('insights', [])

            if not insights_list:
                logger.warning("⚠️ No insights provided for patch generation")
                return {
                    "error": "No insights available",
                    "patch_json": {},
                    "annotations": {
                        "heuristic_flags": [],
                        "sanity_flags": [],
                        "requires_review": True
                    }
                }

            prompt = f"""
Based on these strategic insights, create a StrategyPatch that implements the recommendations:

Insights:
{json.dumps(insights_list, indent=2)}

Create a comprehensive strategy patch with the following structure:

{{
  "audience_targeting": {{
    "segments": [
      {{
        "name": "segment name",
        "demographics": {{"age": "range", "location": "geo"}},
        "interests": ["interest1", "interest2"],
        "behaviors": ["behavior1", "behavior2"]
      }}
    ],
    "exclusions": ["excluded groups"],
    "lookalike_audiences": ["seed audience descriptions"]
  }},
  "messaging_strategy": {{
    "primary_message": "Core value proposition",
    "tone": "brand voice description",
    "key_themes": ["theme1", "theme2", "theme3"],
    "call_to_action": "CTA text"
  }},
  "channel_strategy": {{
    "primary_channels": ["channel1", "channel2"],
    "budget_split": {{"channel1": "40%", "channel2": "60%"}},
    "scheduling": {{"timing": "description", "frequency": "description"}}
  }},
  "budget_allocation": {{
    "total_budget": "$XXXXX",
    "channel_breakdown": {{"channel1": "40%", "channel2": "60%"}},
    "optimization_strategy": "description of budget optimization approach"
  }}
}}

CRITICAL RULES:
1. Implement the recommendations from the insights
2. Budget shifts should be ≤25% from baseline (if known)
3. Limit to ≤3 key themes per audience segment
4. Ensure no overlapping geo+age combinations in segments
5. Base all recommendations on the evidence from insights

Return ONLY the StrategyPatch JSON, no additional commentary.
"""

            logger.info(f"📝 Patch prompt length: {len(prompt)} characters")
            logger.debug(f"📨 Full patch prompt:\n{prompt}")

            # Call LLM @ temp=0.2 (deterministic patch generation)
            patch_text = await self._call_llm('PATCH', prompt)

            logger.info(f"✅ LLM patch response received ({len(patch_text)} chars)")
            logger.debug(f"📋 Full response:\n{patch_text}")

            # Parse JSON response
            try:
                clean_json = self._extract_json_from_response(patch_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", patch_text, 0)

                patch_json = json.loads(clean_json)
                logger.info(f"✅ Successfully parsed patch JSON")

            except json.JSONDecodeError as e:
                logger.error(f"❌ Patch JSON parsing failed: {e}")
                logger.error(f"📄 Full response that failed to parse:\n{patch_text}")
                return {
                    "error": f"JSON parsing failed: {str(e)}",
                    "patch_json": {},
                    "raw_response": patch_text,
                    "annotations": {
                        "heuristic_flags": ["json_parse_failure"],
                        "sanity_flags": [],
                        "requires_review": True
                    }
                }

            # Apply heuristic filters
            logger.info("🔍 Applying heuristic filters")
            validation = HeuristicFilters.validate_patch(patch_json)

            logger.info(f"📊 Validation result: passed={validation['passed']}, " +
                       f"flags={len(validation['heuristic_flags'])}")

            was_downscoped = False
            if not validation['passed']:
                logger.warning(f"⚠️ Patch failed validation: {validation['reasons']}")

                # Try auto-downscope
                logger.info("🔧 Attempting auto-downscope")
                patch_json, was_downscoped = HeuristicFilters.downscope_patch_if_needed(
                    patch_json, validation
                )

                if was_downscoped:
                    logger.info("✅ Auto-downscope applied successfully")
                    # Re-validate after downscope
                    validation = HeuristicFilters.validate_patch(patch_json)
                    logger.info(f"📊 Post-downscope validation: passed={validation['passed']}")

            # Annotate patch with heuristic results
            if 'annotations' not in patch_json:
                patch_json['annotations'] = {}

            patch_json['annotations']['heuristic_flags'] = validation['heuristic_flags']
            patch_json['annotations']['auto_downscoped'] = was_downscoped
            patch_json['annotations']['requires_hitl_review'] = not validation['passed']

            # Apply sanity gate (LLM reflection)
            logger.info("🛡️ Applying sanity gate (LLM reflection)")
            patch_json = await SanityGate.apply_sanity_gate(self, patch_json)

            sanity_flags_count = len(patch_json.get('annotations', {}).get('sanity_flags', []))
            logger.info(f"✅ Sanity gate applied: {sanity_flags_count} flags")

            # Log metrics
            latency_ms = int((time.time() - start_time) * 1000)
            LLMMetrics.log_patch_job(
                job_id=job_id,
                latency_ms=latency_ms,
                temperature=TASK_TEMPERATURES['PATCH'],
                heuristic_flags_count=len(validation.get('heuristic_flags', [])),
                sanity_flags_count=sanity_flags_count,
                passed_validation=validation['passed'],
                auto_downscoped=was_downscoped
            )

            logger.info(f"✅ Strategy patch generated successfully " +
                       f"(validation={'passed' if validation['passed'] else 'failed'}, " +
                       f"downscoped={was_downscoped})")

            return patch_json

        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
            return {
                "error": str(e),
                "patch_json": {},
                "annotations": {
                    "heuristic_flags": ["generation_failed"],
                    "sanity_flags": [],
                    "requires_review": True
                }
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

    async def edit_patch_with_llm(self, patch_id: str, edit_request: str, original_patch: Dict[str, Any] = None) -> Dict[str, Any]:
        """Edit strategy patch based on user feedback with minimal delta and validation"""
        try:
            from .heuristic_filters import HeuristicFilters
            from .sanity_gate import SanityGate
            from .logging_metrics import LLMMetrics

            start_time = time.time()
            job_id = str(uuid.uuid4())

            logger.info(f"[JOB {job_id[:8]}] Editing patch {patch_id} with request: {edit_request}")

            # Include original patch context if provided
            original_patch_context = ""
            if original_patch:
                original_patch_context = f"\nOriginal Patch:\n{json.dumps(original_patch, indent=2)}\n"

            prompt = f"""
As a Marketing Strategy Patch Editor, modify the existing strategy based on this user feedback.
{original_patch_context}
Edit Request: {edit_request}

CRITICAL RULES:
1. Create a MINIMAL delta patch that changes ONLY what the user requested
2. DO NOT change unrelated fields or strategy elements
3. Maintain all existing structure and fields that aren't being edited
4. Keep budget shifts ≤25% from baseline
5. Limit to ≤3 key themes per audience segment

Return a JSON object with:
{{
  "updated_patch": {{
    "audience_targeting": {{...only if changed...}},
    "messaging_strategy": {{...only if changed...}},
    "channel_strategy": {{...only if changed...}},
    "budget_allocation": {{...only if changed...}}
  }},
  "changes_made": ["specific change 1", "specific change 2"],
  "rationale": "why these specific changes address the user's request",
  "impact_assessment": "expected impact of these changes"
}}

Return ONLY the JSON, no additional commentary.
"""

            logger.info(f"📝 Edit prompt length: {len(prompt)} characters")
            logger.debug(f"📨 Full edit prompt:\n{prompt}")

            # Call LLM @ temp=0.2 (deterministic, minimal changes)
            edited_text = await self._call_llm('EDIT', prompt)

            logger.info(f"✅ LLM edit response received ({len(edited_text)} chars)")
            logger.debug(f"📋 Full response:\n{edited_text}")

            # Parse JSON response
            try:
                clean_json = self._extract_json_from_response(edited_text)
                if not clean_json:
                    raise json.JSONDecodeError("No JSON content found", edited_text, 0)

                edited_patch = json.loads(clean_json)
                logger.info("✅ Successfully parsed edited patch JSON")

            except json.JSONDecodeError as e:
                logger.error(f"❌ Edited patch JSON parsing failed: {e}")
                logger.error(f"📄 Full response that failed to parse:\n{edited_text}")
                edited_patch = {
                    "updated_patch": {"status": "Edit in progress"},
                    "changes_made": ["Processing user feedback"],
                    "rationale": "Analyzing requested modifications",
                    "impact_assessment": "Impact analysis pending",
                    "error": f"JSON parsing failed: {str(e)}",
                    "raw_edit": edited_text
                }

            # Extract the updated_patch for validation
            final_patch = edited_patch.get('updated_patch', {})

            # Calculate delta size (number of changed fields)
            delta_size = len(edited_patch.get('changes_made', []))
            logger.info(f"📊 Delta size: {delta_size} changes")

            # Apply heuristic filters to final merged patch
            logger.info("🔍 Applying heuristic filters to edited patch")
            validation = HeuristicFilters.validate_patch(final_patch)

            passed_filters = validation['passed']
            logger.info(f"📊 Validation result: passed={passed_filters}, " +
                       f"flags={len(validation['heuristic_flags'])}")

            # Apply sanity gate
            logger.info("🛡️ Applying sanity gate to edited patch")
            final_patch = await SanityGate.apply_sanity_gate(self, final_patch)

            # Update the edited_patch with validated final_patch
            edited_patch['updated_patch'] = final_patch

            # Add metadata
            edited_patch["patch_id"] = str(uuid.uuid4())
            edited_patch["original_patch_id"] = patch_id
            edited_patch["edited_at"] = datetime.utcnow().isoformat()

            # Log metrics
            latency_ms = int((time.time() - start_time) * 1000)
            LLMMetrics.log_edit_job(
                job_id=job_id,
                latency_ms=latency_ms,
                temperature=TASK_TEMPERATURES['EDIT'],
                delta_size=delta_size,
                passed_filters=passed_filters,
                original_patch_id=patch_id
            )

            logger.info(f"✅ Patch edited successfully (delta={delta_size}, valid={passed_filters})")
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