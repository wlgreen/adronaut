# LLM Service Refactoring - Implementation Status

## ✅ Completed (Phase 1: Foundation Files)

### New Files Created:
1. **`service/mechanics_cheat_sheet.py`** ✅
   - Complete metric→lever mappings (CTR, Conversion Rate, CPA, ROAS, Engagement)
   - Action selection rules (single lever, evidence-based, weak evidence handling)
   - Anti-pattern guidance
   - Helper functions: `get_mechanics_for_metric()`, `validate_lever_choice()`

2. **`service/insights_selector.py`** ✅
   - Deterministic scoring rubric: `score_insight()` (0-100 scale)
   - Top-k selection: `select_top_insights(candidates, k=3)`
   - Validation: `validate_insight_structure()`, `validate_confidence_alignment()`
   - Stats: `count_data_support_distribution()`, `calculate_insufficient_evidence_rate()`

3. **`service/heuristic_filters.py`** ✅
   - Budget sanity: `check_budget_sanity()` (≤25% shift)
   - Audience sanity: `check_audience_sanity()` (no geo+age overlap)
   - Creative sanity: `check_creative_sanity()` (≤3 per audience)
   - Main validator: `validate_patch()` - returns flags + pass/fail
   - Auto-downscope: `downscope_patch_if_needed()` - attempts to fix violations

4. **`service/sanity_gate.py`** ✅
   - LLM-based reflection: `reflect_on_patch()` using PATCH task @ temp=0.2
   - Main gate: `apply_sanity_gate()` - adds annotations to patch
   - Risk assessment: `should_block_patch()` - recommends blocking if ≥2 high-risk flags
   - Summary: `get_review_summary()` - human-readable summary

---

## 🔄 In Progress (Phase 2: Core Orchestrator Updates)

### File: `service/logging_metrics.py` (PENDING)
**Next Steps:**
```python
class LLMMetrics:
    @staticmethod
    def log_insights_job(job_id, latency_ms, temperature, candidate_count,
                        selected_score, has_evidence_refs, data_support_counts,
                        insufficient_evidence_rate):
        # Log INSIGHTS-specific metrics

    @staticmethod
    def log_patch_job(job_id, latency_ms, heuristic_flags_count,
                     sanity_flags_count, passed_validation):
        # Log PATCH-specific metrics

    @staticmethod
    def log_edit_job(job_id, latency_ms, delta_size, passed_filters):
        # Log EDIT_PATCH-specific metrics
```

### File: `service/gemini_orchestrator.py` (NEEDS MAJOR UPDATES)
**Critical Changes Required:**

#### 1. Add Temperature Configuration
```python
TASK_TEMPERATURES = {
    'FEATURES': 0.2,
    'INSIGHTS': 0.35,
    'PATCH': 0.2,
    'EDIT': 0.2,
    'BRIEF': 0.3,
    'ANALYZE': 0.35
}

async def _call_llm(self, task: str, prompt: str) -> str:
    temperature = TASK_TEMPERATURES.get(task, 0.3)

    if provider == 'gemini':
        response = self.gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
    elif provider == 'openai':
        response = self.openai_client.chat.completions.create(
            model=model_name,
            messages=[...],
            temperature=temperature
        )
```

#### 2. Refactor `generate_insights()` - Generate k Candidates
```python
async def generate_insights(self, features: Dict[str, Any]) -> Dict[str, Any]:
    from .mechanics_cheat_sheet import MECHANICS_CHEAT_SHEET
    from .insights_selector import select_top_insights, validate_insight_structure
    from .logging_metrics import LLMMetrics

    start_time = time.time()

    # NEW PROMPT with mechanics cheat sheet embedded
    prompt = f"""
{MECHANICS_CHEAT_SHEET}

As a Marketing Strategy Insights Expert, analyze these features:

{json.dumps(features, indent=2)}

**CRITICAL RULES:**
1. Base all claims on evidence present in features. If insufficient, set data_support="weak"
2. Each insight must target exactly ONE primary lever (audience/creative/budget/bidding/funnel)
3. Include expected_effect with direction + magnitude (small/medium/large)
4. Add evidence_refs pointing to specific feature fields
5. If data_support="weak", propose learn/test action (pilot, A/B test, etc.)

Generate 5 insight candidates. For each:
{{
  "insight": "Observation from data",
  "hypothesis": "Causal explanation",
  "proposed_action": "Specific action to take",
  "primary_lever": "audience" | "creative" | "budget" | "bidding" | "funnel",
  "expected_effect": {{
    "direction": "increase" | "decrease",
    "metric": "CTR" | "conversion_rate" | etc,
    "magnitude": "small" | "medium" | "large",
    "range": "10-20%" (optional)
  }},
  "confidence": 0.0 to 1.0,
  "data_support": "strong" | "moderate" | "weak",
  "evidence_refs": ["features.field_name", ...],
  "contrastive_reason": "Why this vs why not alternative"
}}

Return JSON: {{"candidates": [...]}}
"""

    # Call LLM @ temp=0.35
    response_text = await self._call_llm('INSIGHTS', prompt)
    clean_json = self._extract_json_from_response(response_text)
    result = json.loads(clean_json)

    candidates = result.get('candidates', [])

    # Validate and select top 3
    valid_candidates = [c for c in candidates if validate_insight_structure(c)]
    top_3 = select_top_insights(valid_candidates, k=3)

    # Log metrics
    latency_ms = int((time.time() - start_time) * 1000)
    data_support_counts = count_data_support_distribution(top_3)
    insufficient_rate = calculate_insufficient_evidence_rate(top_3)

    LLMMetrics.log_insights_job(
        job_id=str(uuid.uuid4()),
        latency_ms=latency_ms,
        temperature=0.35,
        candidate_count=len(candidates),
        selected_score=top_3[0]['impact_score'] if top_3 else 0,
        has_evidence_refs=any(i.get('evidence_refs') for i in top_3),
        data_support_counts=data_support_counts,
        insufficient_evidence_rate=insufficient_rate
    )

    # Return insights WITHOUT patch (breaking change from old flow)
    return {
        'insights': top_3,
        'candidates_evaluated': len(candidates),
        'selection_method': 'deterministic_rubric'
    }
```

#### 3. Create NEW `generate_patch()` Method
```python
async def generate_patch(self, insights: Dict[str, Any]) -> Dict[str, Any]:
    from .heuristic_filters import HeuristicFilters
    from .sanity_gate import SanityGate
    from .logging_metrics import LLMMetrics

    start_time = time.time()

    # Convert insights → patch with prompt
    prompt = f"""
Convert these strategic insights into a StrategyPatch:

{json.dumps(insights, indent=2)}

Create a patch with:
- audience_targeting: {{segments: [...]}}
- messaging_strategy: {{primary_message, tone, key_themes}}
- channel_strategy: {{primary_channels, budget_split, scheduling}}
- budget_allocation: {{total_budget, channel_breakdown, optimization_strategy}}

Return valid StrategyPatch JSON only.
"""

    response_text = await self._call_llm('PATCH', prompt)
    patch_json = json.loads(self._extract_json_from_response(response_text))

    # Apply heuristic filters
    validation = HeuristicFilters.validate_patch(patch_json)

    if not validation['passed']:
        # Try auto-downscope
        patch_json, was_modified = HeuristicFilters.downscope_patch_if_needed(
            patch_json, validation
        )

        # Re-validate after downscope
        validation = HeuristicFilters.validate_patch(patch_json)

        # Annotate patch
        patch_json.setdefault('annotations', {})
        patch_json['annotations']['heuristic_flags'] = validation['heuristic_flags']
        patch_json['annotations']['auto_downscoped'] = was_modified
        patch_json['annotations']['requires_hitl_review'] = not validation['passed']

    # Apply sanity gate
    patch_json = await SanityGate.apply_sanity_gate(self, patch_json)

    # Log metrics
    latency_ms = int((time.time() - start_time) * 1000)
    LLMMetrics.log_patch_job(
        job_id=str(uuid.uuid4()),
        latency_ms=latency_ms,
        heuristic_flags_count=len(validation.get('heuristic_flags', [])),
        sanity_flags_count=len(patch_json.get('annotations', {}).get('sanity_flags', [])),
        passed_validation=validation['passed']
    )

    return patch_json
```

#### 4. Update `edit_patch_with_llm()` - Minimal Delta + Filters
```python
async def edit_patch_with_llm(self, patch_id: str, edit_request: str) -> Dict[str, Any]:
    from .heuristic_filters import HeuristicFilters
    from .sanity_gate import SanityGate

    # Updated prompt emphasizing minimal changes
    prompt = f"""
Edit Request: {edit_request}

Create a MINIMAL delta patch that changes ONLY what the user requested.

Return JSON with:
{{
  "updated_patch": {{...only changed fields...}},
  "changes_made": ["list of specific changes"],
  "rationale": "why these changes",
  "impact_assessment": "expected impact"
}}

DO NOT change unrelated fields. Keep the delta minimal.
"""

    response = await self._call_llm('EDIT', prompt)
    edited_patch = json.loads(self._extract_json_from_response(response))

    # Apply filters to final merged patch
    validation = HeuristicFilters.validate_patch(edited_patch['updated_patch'])
    edited_patch = await SanityGate.apply_sanity_gate(self, edited_patch)

    return edited_patch
```

#### 5. Update FEATURES Prompt - Remove Speculation
**Line 188 OLD:**
```python
IMPORTANT: Even if the data is limited, provide your best analysis based on available information.
```

**Line 188 NEW:**
```python
CRITICAL: Base all claims on evidence present in artifacts.
If data is insufficient for a claim, explicitly state insufficient_evidence=true
and note what data would be needed. DO NOT speculate or guess.
```

---

## 🔄 In Progress (Phase 3: Database & Frontend)

### File: `service/database.py` (NEEDS UPDATE)
**Add Annotation Support:**
```python
async def create_patch(self, project_id: str, source: str,
                      patch_json: Dict, justification: str,
                      annotations: Dict = None) -> str:
    """Updated to support annotations field"""
    patch_id = str(uuid.uuid4())

    patch_data = {
        'patch_id': patch_id,
        'project_id': project_id,
        'source': source,
        'status': 'proposed',
        'patch_json': self._serialize_json_data(patch_json),
        'justification': justification,
        'annotations': self._serialize_json_data(annotations) if annotations else None,
        'created_at': datetime.utcnow().isoformat()
    }

    # ... rest of insert logic
```

### File: `web/src/lib/llm-service.ts` (NEEDS UPDATE)
**Update TypeScript Interfaces:**
```typescript
export interface Insight {
  insight: string
  hypothesis: string
  proposed_action: string
  primary_lever: 'audience' | 'creative' | 'budget' | 'bidding' | 'funnel'
  expected_effect: {
    direction: 'increase' | 'decrease'
    metric: string
    magnitude: 'small' | 'medium' | 'large'
    range?: string
  }
  confidence: number  // 0..1
  data_support: 'strong' | 'moderate' | 'weak'
  evidence_refs: string[]
  contrastive_reason: string
  impact_rank: number  // 1..3
  impact_score: number  // 0..100
}

export interface InsightsResponse {
  insights: Insight[]  // Exactly 3
  candidates_evaluated: number
  selection_method: string
}

export interface StrategyPatch {
  // ... existing fields ...
  annotations?: {
    heuristic_flags?: string[]
    sanity_flags?: Array<{
      action_id: string
      reason: string
      risk: 'high' | 'medium' | 'low'
      recommendation: string
    }>
    requires_review?: boolean
    auto_downscoped?: boolean
  }
  sanity_review?: 'safe' | 'review_recommended' | 'high_risk'
  insufficient_evidence?: boolean
}
```

---

## 📋 Remaining Tasks

### Phase 4: Testing
- [ ] Create `service/test_llm_refactor.py`:
  - Unit tests for all 8 upgrades
  - Integration tests for FEATURES→INSIGHTS→PATCH flow
  - Temperature validation tests
  - Schema validation tests

### Phase 5: Integration
- [ ] Update `main.py` workflow to use new 2-step flow:
  - Step 3: INSIGHTS (no patch)
  - Step 4: PATCH_PROPOSED (with filters + gate)
- [ ] Update frontend strategy page to display new insight fields
- [ ] Add UI for patch annotations (flags, risk levels)

### Phase 6: Deployment
- [ ] Add feature flag: `USE_STRUCTURED_INSIGHTS=true`
- [ ] A/B test old vs new flow
- [ ] Monitor metrics dashboard:
  - candidate_count, selected_score
  - heuristic_flags_count, sanity_flags_count
  - insufficient_evidence_rate
  - time-to-approved-patch
  - approve-without-edit rate

---

## Acceptance Criteria Checklist

### ✅ Completed:
- [x] Mechanics cheat sheet created with metric→lever mappings
- [x] Scoring rubric implemented (deterministic, 0-100 scale)
- [x] Heuristic filters created (budget/audience/creative)
- [x] Sanity gate implemented (LLM reflection)
- [x] Temperature specs defined (FEATURES: 0.2, INSIGHTS: 0.35, etc.)

### 🔄 In Progress:
- [ ] INSIGHTS outputs exactly 3 ranked items (≥95% with all required fields)
- [ ] INSIGHTS never emits a patch
- [ ] PATCH passes schema + records flags when rules trigger
- [ ] EDIT_PATCH applies minimal delta + passes filters
- [ ] Temperatures enforced per task type
- [ ] Logging captures all observability metrics

### ⏳ Pending:
- [ ] Invalid JSON rate ≤1%
- [ ] Time-to-approved-patch decreases in side-by-side
- [ ] "Approve without edit" rate increases in side-by-side
- [ ] ≥95% compliance with required fields in dry runs

---

## Next Steps (Priority Order)

1. **Create `logging_metrics.py`** - Observability foundation
2. **Update `gemini_orchestrator.py`** - Core refactoring:
   - Add temperature config
   - Refactor `generate_insights()` with k=5 candidates
   - Create `generate_patch()` with filters + gate
   - Update `edit_patch_with_llm()` with minimal delta
   - Remove speculation language from FEATURES prompt
3. **Update `database.py`** - Add annotations support
4. **Update `llm-service.ts`** - Frontend schema alignment
5. **Create `test_llm_refactor.py`** - Comprehensive test suite
6. **Update `main.py`** - Integrate new 2-step INSIGHTS→PATCH flow
7. **Run dry runs** - Validate acceptance criteria on real data
8. **Deploy with feature flag** - A/B test and monitor metrics

---

## Files Summary

**New Files (4 completed, 1 pending):**
1. ✅ `service/mechanics_cheat_sheet.py` - 160 lines
2. ✅ `service/insights_selector.py` - 220 lines
3. ✅ `service/heuristic_filters.py` - 240 lines
4. ✅ `service/sanity_gate.py` - 190 lines
5. ⏳ `service/logging_metrics.py` - ~100 lines (pending)

**Modified Files (3 pending):**
1. ⏳ `service/gemini_orchestrator.py` - Major updates (~400 lines changed)
2. ⏳ `service/database.py` - Minor update (~30 lines)
3. ⏳ `web/src/lib/llm-service.ts` - Schema updates (~80 lines)

**Total: 8 files** (4 created, 1 partial, 3 pending updates)
