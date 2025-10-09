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
        from logging_metrics import LLMMetrics

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
            As a Marketing Data Feature Extractor, analyze the following marketing artifacts and extract ONLY information that is explicitly present.

            Number of artifacts: {len(artifact_summaries)}

            Artifacts Data: {json.dumps(artifact_summaries, indent=2)}

            **CRITICAL RULES:**
            1. Extract ONLY data explicitly present in artifacts
            2. Use "insufficient_evidence" for any missing information - DO NOT infer, suggest, or assume
            3. Include specific references to where you found each piece of data
            4. Separate facts from any insights drawn from those facts

            **GOOD Example (data present):**
            {{
              "target_audience": {{
                "segments": [
                  {{
                    "name": "Young professionals",
                    "age_range": "25-35",
                    "location": "urban areas",
                    "source": "Camp_001 targeting description"
                  }}
                ],
                "data_completeness": "partial"
              }}
            }}

            **BAD Example (hallucination):**
            {{
              "target_audience": {{
                "segments": [
                  {{
                    "name": "Young professionals",
                    "likely_income": "$60-100k",  ← WRONG: Not in data!
                    "preferred_devices": "mobile"  ← WRONG: Not in data!
                  }}
                ]
              }}
            }}

            Return a JSON object with these keys (use "insufficient_evidence" if data not present):

            {{
              "target_audience": {{
                "segments": [array of audience segments found] or "insufficient_evidence",
                "data_source": "where this data came from"
              }},
              "metrics": {{
                "campaigns": {{
                  "campaign_id": {{
                    "impressions": number or "insufficient_evidence",
                    "clicks": number or "insufficient_evidence",
                    "conversions": number or "insufficient_evidence",
                    "spend": number or "insufficient_evidence",
                    "revenue": number or "insufficient_evidence",
                    "ctr": "percentage" or "insufficient_evidence",
                    "cpa": number or "insufficient_evidence",
                    "roas": number or "insufficient_evidence",
                    "date_range": "YYYY-MM-DD to YYYY-MM-DD"
                  }}
                }},
                "data_completeness": "complete" | "partial" | "minimal"
              }},
              "channels": [array of channels explicitly mentioned] or "insufficient_evidence",
              "messaging": [array of themes/messages explicitly stated] or "insufficient_evidence",
              "creative_performance": {{
                "by_campaign": {{
                  "campaign_id": {{
                    "creative_type": "description from data",
                    "performance_notes": "explicit notes from data"
                  }}
                }} or "insufficient_evidence"
              }},
              "geographic_insights": {{
                "by_campaign": {{
                  "campaign_id": {{
                    "top_geos": [list from data],
                    "performance_notes": "explicit notes"
                  }}
                }} or "insufficient_evidence"
              }},
              "budget_data": {{
                "total_budget": number or "insufficient_evidence",
                "by_campaign": {{}} or "insufficient_evidence"
              }},
              "objectives": [array of explicit goals stated] or "insufficient_evidence",
              "recommendations_from_data": [array of recommendations explicitly provided in artifacts] or "insufficient_evidence"
            }}

            MUST return valid JSON. Mark missing data as "insufficient_evidence", never infer or suggest.
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
            from mechanics_cheat_sheet import MECHANICS_CHEAT_SHEET
            from insights_selector import (
                select_top_insights,
                validate_insight_structure,
                count_data_support_distribution,
                calculate_insufficient_evidence_rate
            )
            from logging_metrics import LLMMetrics
            import uuid

            start_time = time.time()
            job_id = str(uuid.uuid4())

            logger.info(f"[JOB {job_id[:8]}] Generating insight candidates with mechanics-guided prompting")

            prompt = f"""
{MECHANICS_CHEAT_SHEET}

As a Marketing Strategy Insights Expert, analyze these extracted features and generate strategic insights:

Features: {json.dumps(features, indent=2)}

**SPARSE DATA = LEARNING OPPORTUNITY (CRITICAL FOR SCORING)**

When data is insufficient (data_support="weak"), you MUST design structured experiments.
Well-designed experiments score 70-85 points. Vague recommendations score 30-45 points.

MANDATORY for weak insights:
1. Budget cap: Include specific $ amount (e.g., "$500 budget cap")
2. Timeline: Include duration (e.g., "14-day experiment", "7-day pilot")
3. Success metrics: Include what to measure (e.g., "measure CTR and ROAS daily")
4. Learning keywords: MUST use at least one: pilot, test, experiment, A/B, validate, trial

If you forget these, you will lose 2 points (penalty).

**CRITICAL RULES:**
1. Base all claims on evidence present in features. If insufficient data, set data_support="weak"
2. Each insight must target exactly ONE primary lever from: audience, creative, budget, bidding, funnel
3. Include expected_effect with direction (increase/decrease) + magnitude (small/medium/large) + concrete range
4. Add evidence_refs with SPECIFIC paths: "features.metrics.campaigns.camp_002.roas" (not generic)
5. If data_support="weak", propose learn/test action (pilot, A/B test, limited budget experiment)
6. Provide contrastive reasoning: explain why you recommend X instead of alternative Y with specific tradeoffs

**EXAMPLE - Strong Insight (data_support="strong"):**
{{
  "insight": "Camp_002 achieves 6.99 average ROAS (2.0x higher than Camp_001's 3.54 ROAS) while targeting SMB decision makers age 35-50",
  "hypothesis": "Testimonial-based creative format resonates stronger with business purchase decision makers compared to product-focused imagery targeting younger professionals",
  "proposed_action": "Reallocate $1,875 (25% of total budget) from Camp_001 to Camp_002 over 7-day period, maintaining current SMB targeting and testimonial creative",
  "primary_lever": "budget",
  "expected_effect": {{
    "direction": "increase",
    "metric": "ROAS",
    "magnitude": "medium",
    "range": "15-25% improvement in blended portfolio ROAS (from ~4.5 to 5.2-5.6)"
  }},
  "confidence": 0.82,
  "data_support": "strong",
  "evidence_refs": [
    "features.metrics.campaigns.camp_002.roas",
    "features.metrics.campaigns.camp_001.roas",
    "features.target_audience.segments.camp_002.age_range",
    "features.creative_performance.by_campaign.camp_002.creative_type"
  ],
  "contrastive_reason": "Budget reallocation provides immediate ROAS lift (7-day implementation) vs creative testing which requires 14-21 day learning period and introduces execution risk"
}}

**EXAMPLE - Moderate Insight (data_support="moderate"):**
{{
  "insight": "Camp_001 performs best in coastal cities (SF, NYC, Seattle) with 2.5% CTR vs 1.8% national average for Camp_003",
  "hypothesis": "Urban young professionals in tech hubs respond better to product-focused messaging due to higher tech affinity",
  "proposed_action": "Narrow Camp_001 geo-targeting to top 5 coastal metro areas, increase bid by 15% in these geos to capture impression share",
  "primary_lever": "audience",
  "expected_effect": {{
    "direction": "increase",
    "metric": "CTR",
    "magnitude": "small",
    "range": "8-12% CTR improvement (from 2.4% to 2.6-2.7%)"
  }},
  "confidence": 0.68,
  "data_support": "moderate",
  "evidence_refs": [
    "features.geographic_insights.by_campaign.camp_001.top_geos",
    "features.metrics.campaigns.camp_001.ctr",
    "features.target_audience.segments.camp_001.location"
  ],
  "contrastive_reason": "Geo-narrowing reduces waste vs expanding to new geos (unknown performance, higher risk of dilution)"
}}

**EXAMPLE - Weak Data + Strong Learning Plan (data_support="weak" - scores 70-85):**
{{
  "insight": "Camp_003 has 1.8% CTR but only 3 days of scattered data across all markets with no clear geographic pattern",
  "hypothesis": "Broad demographic targeting (18-55) and generic brand messaging lacks audience-message fit, but insufficient data to identify which segments respond best",
  "proposed_action": "Run 14-day pilot experiment: Split Camp_003 into 3 age segments (18-25, 26-40, 41-55), allocate $500 budget cap per segment ($1500 total), test current creative with each segment, measure CTR and ROAS daily via platform analytics to identify top-performing segment for next-cycle optimization",
  "primary_lever": "audience",
  "expected_effect": {{
    "direction": "increase",
    "metric": "data_completeness and ROAS",
    "magnitude": "medium",
    "range": "After 14 days: identify 1-2 segments with >2.0 ROAS, enabling focused budget reallocation in next cycle"
  }},
  "confidence": 0.40,
  "data_support": "weak",
  "evidence_refs": [
    "features.geographic_insights.by_campaign.camp_003.performance_notes",
    "features.metrics.campaigns.camp_003.ctr"
  ],
  "contrastive_reason": "Structured multi-segment pilot experiment ($1500 total, 14 days) provides statistical evidence for next cycle vs guessing best segment blindly (high risk, $3000+ wasted) or waiting passively for organic data (unknown timeline, delays optimization)"
}}

NOTE: This example includes ALL 4 mandatory elements: "$500 budget cap" (budget), "14-day pilot" (timeline), "measure CTR and ROAS daily" (metrics), "pilot experiment" (learning keyword). This scores 77 points.

Generate 5 insight candidates following these examples. Each MUST have:
- Specific numbers from features (not "high ROAS" but "6.99 ROAS")
- Concrete action steps with timelines
- Expected effect ranges (not just "medium" but "15-25%")
- Specific evidence paths (not "features.metrics" but "features.metrics.campaigns.camp_002.roas")
- Tradeoff analysis in contrastive_reason

**REMINDER FOR WEAK DATA INSIGHTS:**
If data_support="weak", your proposed_action MUST include:
1. A learning keyword (pilot/test/experiment/A/B/validate/trial)
2. A budget cap (e.g., "$500 budget cap")
3. A timeline (e.g., "14-day experiment")
4. Success metrics (e.g., "measure CTR daily")

Missing these = -2 point penalty. Including all 4 = +5 point bonus.

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
            from heuristic_filters import HeuristicFilters
            from sanity_gate import SanityGate
            from logging_metrics import LLMMetrics
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
Based on these strategic insights, create an ACTIONABLE StrategyPatch with specific numbers, timelines, and implementation steps:

Insights:
{json.dumps(insights_list, indent=2)}

**PATCH TYPES:**
- "optimization": Strong data insights → direct budget/targeting changes for immediate gains
- "experimental": Weak data insights → structured tests to gather data for next cycle

If ANY insight has data_support="weak" with experiment/pilot/test proposal → set strategy_type="experimental"

**CRITICAL RULES:**
1. Use SPECIFIC NUMBERS from insights (not "increase budget" but "increase by $1,875 to $4,125")
2. Include implementation timeline (e.g., "7-day gradual rollout", "immediate change")
3. Budget shifts must be ≤25% from current baseline
4. Limit to ≤3 key themes per audience segment
5. No overlapping geo+age combinations in segments
6. Include success metrics to track (with target numbers)
7. For experimental patches: MUST include experiment_details and ai_recommendations

**EXAMPLE - Good Actionable Patch:**
{{
  "audience_targeting": {{
    "segments": [
      {{
        "name": "SMB Decision Makers - Midwest",
        "demographics": {{
          "age": "35-50",
          "location": ["Chicago", "Minneapolis", "Denver"],
          "job_function": "business decision maker"
        }},
        "current_performance": "6.99 ROAS average",
        "action": "EXPAND: Increase budget from $1,850 to $4,125 (+123%)",
        "implementation": "7-day gradual rollout to avoid delivery disruption"
      }},
      {{
        "name": "Young Professionals - Coastal Cities",
        "demographics": {{
          "age": "25-35",
          "location": ["San Francisco", "New York", "Seattle"]
        }},
        "current_performance": "3.54 ROAS average",
        "action": "MAINTAIN: Keep budget at $2,400, optimize geo-targeting to top 3 cities only",
        "implementation": "Immediate geo-restriction, monitor for 3 days"
      }}
    ],
    "exclusions": ["Overlapping age ranges in same geos"],
    "rationale": "Focus on highest ROAS segment (SMB) while maintaining presence in secondary segment"
  }},
  "messaging_strategy": {{
    "primary_message": "Proven results through customer testimonials",
    "tone": "Professional, data-driven, trust-building",
    "key_themes": [
      "Customer success stories (testimonial-based)",
      "ROI proof points (specific ROAS numbers)",
      "Industry expertise (B2B focus)"
    ],
    "call_to_action": "See How [Customer] Achieved 7x ROAS",
    "implementation_notes": "Repurpose Camp_002 testimonial creative for expanded reach"
  }},
  "channel_strategy": {{
    "primary_channels": ["Paid Search", "LinkedIn Ads"],
    "budget_split": {{
      "Paid Search": "60% ($4,500) - highest ROAS channel",
      "LinkedIn Ads": "40% ($3,000) - B2B audience match"
    }},
    "scheduling": {{
      "timing": "Weekday business hours (9am-5pm local time)",
      "frequency": "Max 3 impressions per user per week to avoid fatigue"
    }},
    "implementation": "Week 1: 50/50 split for baseline, Week 2+: Shift to 60/40 based on performance"
  }},
  "budget_allocation": {{
    "total_budget": "$7,500",
    "current_allocation": {{
      "Camp_001": "$2,400 (32%)",
      "Camp_002": "$1,850 (25%)",
      "Camp_003": "$3,250 (43%)"
    }},
    "new_allocation": {{
      "Camp_001": "$2,400 (32%) - MAINTAIN",
      "Camp_002": "$4,125 (55%) - INCREASE $2,275 (+123%)",
      "Camp_003": "$975 (13%) - DECREASE $2,275 (-70%)"
    }},
    "total_shift": "25% budget reallocation (within threshold)",
    "optimization_strategy": "Shift from underperforming broad reach (Camp_003 ROAS 1.42) to highest performer (Camp_002 ROAS 6.99)",
    "implementation_timeline": "7-day gradual rollout: Day 1-2 (10% shift), Day 3-5 (15% shift), Day 6-7 (full 25%)"
  }},
  "success_metrics": {{
    "primary_kpi": {{
      "metric": "Blended Portfolio ROAS",
      "baseline": "4.30 (current average)",
      "target": "5.15-5.45 (20-27% improvement)",
      "measurement_window": "14 days post-implementation"
    }},
    "secondary_kpis": [
      {{
        "metric": "Camp_002 daily spend",
        "target": "$589 per day (up from $617 avg)",
        "tracking": "Daily monitoring for delivery issues"
      }},
      {{
        "metric": "Camp_003 ROAS improvement",
        "target": ">2.0 ROAS with reduced budget (quality over volume)",
        "tracking": "Weekly review for 3 weeks"
      }}
    ]
  }}
}}

**EXAMPLE - Experimental Strategy Patch (for weak data insights):**
{{
  "strategy_type": "experimental",
  "experiment_details": {{
    "objective": "Identify highest-performing audience segment for Camp_003",
    "hypothesis": "Younger segments (18-25) will show higher CTR, older segments (41-55) will show higher ROAS",
    "method": "Audience segmentation A/B test",
    "duration": "14 days",
    "total_budget": "$1,500",
    "success_metrics": [
      "CTR by segment (target: >2.0% for at least one segment)",
      "ROAS by segment (target: >2.5 for at least one segment)",
      "Statistical significance (p<0.05)"
    ],
    "decision_criteria": "After 14 days: Reallocate Camp_003 budget to top-performing segment(s), or discontinue if all segments show ROAS <1.5"
  }},
  "ai_recommendations": {{
    "rationale": "Current Camp_003 data shows scattered performance (1.8% CTR, 1.42 ROAS) with only 3 days of data. Running controlled experiment provides statistical evidence for next-cycle optimization decisions.",
    "learning_value": "Identifies which demographic segments respond to brand messaging, enabling targeted creative and budget allocation in Cycle 2",
    "next_steps_after_experiment": [
      "If segment 18-25 wins: Reallocate 60% of Camp_003 budget to this segment, test product-focused creative",
      "If segment 41-55 wins: Maintain current creative, increase budget by 25%",
      "If no segment wins: Discontinue Camp_003, reallocate budget to Camp_002 (proven 6.99 ROAS)"
    ]
  }},
  "audience_targeting": {{
    "segments": [
      {{
        "name": "Young Adults (18-25) - Camp_003 Experimental",
        "demographics": {{"age": "18-25", "location": "national"}},
        "action": "NEW: Allocate $500 for 14-day test",
        "implementation": "Launch as separate ad set to isolate metrics"
      }},
      {{
        "name": "Mid-Career (26-40) - Camp_003 Experimental",
        "demographics": {{"age": "26-40", "location": "national"}},
        "action": "NEW: Allocate $500 for 14-day test",
        "implementation": "Launch as separate ad set to isolate metrics"
      }},
      {{
        "name": "Established (41-55) - Camp_003 Experimental",
        "demographics": {{"age": "41-55", "location": "national"}},
        "action": "NEW: Allocate $500 for 14-day test",
        "implementation": "Launch as separate ad set to isolate metrics"
      }}
    ]
  }},
  "budget_allocation": {{
    "total_budget": "$1,500 (experimental allocation)",
    "new_allocation": {{
      "Camp_003_Segment_A (18-25)": "$500 (33%)",
      "Camp_003_Segment_B (26-40)": "$500 (33%)",
      "Camp_003_Segment_C (41-55)": "$500 (33%)"
    }},
    "implementation_timeline": "Day 1: Launch all 3 segments simultaneously, Day 14: Analyze results and decide next action"
  }}
}}

Create a strategy patch following this format. MUST include:
- Specific dollar amounts and percentages
- Implementation timelines (days/weeks)
- Current vs new state comparisons
- Success metrics with baseline and targets
- Rationale tied to insight evidence
- For experimental patches: experiment_details and ai_recommendations sections

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
            from heuristic_filters import HeuristicFilters
            from sanity_gate import SanityGate
            from logging_metrics import LLMMetrics

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