# LLM Calling Flow and Prompts Documentation

## Overview

Your system uses a **multi-LLM hybrid approach** with configurable routing:
- **Gemini 2.5 Pro** for data extraction tasks (fast, cost-effective)
- **OpenAI GPT-5** for strategic reasoning tasks (advanced thinking)

## Configuration

### Per-Task LLM Assignment (Environment Variables)

```bash
# Data extraction tasks → Gemini
LLM_FEATURES=gemini:gemini-2.5-pro
LLM_BRIEF=gemini:gemini-2.5-pro

# Strategic tasks → GPT-5
LLM_INSIGHTS=openai:gpt-5
LLM_PATCH=openai:gpt-5
LLM_ANALYZE=openai:gpt-5
LLM_EDIT=openai:gpt-5
```

## Workflow Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ADRONAUT WORKFLOW                             │
│                                                                      │
│  User uploads files                                                  │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  1. INGEST       │  Load artifacts from database                 │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  2. FEATURES     │  🤖 Gemini 2.5 Pro                            │
│  │  Extract Features│  Analyzes uploaded marketing artifacts        │
│  └──────────────────┘  Extracts: audience, positioning, channels    │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  3. INSIGHTS     │  🤖 GPT-5                                      │
│  │  Generate        │  Strategic analysis of extracted features     │
│  │  Strategic       │  Creates: opportunities, targeting,           │
│  │  Insights        │  channel strategy, budget allocation          │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  4. PATCH        │  🤖 GPT-5                                      │
│  │  Create Strategy │  Generates strategy patch from insights       │
│  │  Patch           │  Proposes specific changes to implement       │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  5. HITL_PATCH   │  👤 Human Review                              │
│  │  Human Review    │  User decides: Approve / Reject / Edit        │
│  └──────────────────┘                                               │
│         ↓                                                            │
│    If "Edit" selected:                                              │
│  ┌──────────────────┐                                               │
│  │  EDIT_PATCH      │  🤖 GPT-5                                      │
│  │  LLM-Assisted    │  Rewrites patch based on user feedback        │
│  │  Editing         │  Creates new patch (auto-approved)            │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  6. APPLY        │  Apply approved patch to strategy             │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  7. BRIEF        │  🤖 Gemini 2.5 Pro                            │
│  │  Compile         │  Creates marketing brief from strategy        │
│  │  Marketing Brief │                                               │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  8. CAMPAIGN_RUN │  Launch campaign execution                    │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  9. COLLECT      │  Gather performance metrics                   │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  10. ANALYZE     │  🤖 GPT-5                                      │
│  │  Performance     │  Analyzes campaign metrics                    │
│  │  Analysis        │  Identifies optimization opportunities        │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  11. REFLECTION  │  Generate improvement recommendations         │
│  │  PATCH           │                                               │
│  └──────────────────┘                                               │
│         ↓                                                            │
│  ┌──────────────────┐                                               │
│  │  12. HITL        │  👤 Human Review (if needed)                  │
│  │  REFLECTION      │  Review performance-based changes             │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Detailed LLM Prompts

### 1. FEATURES - Extract Marketing Features
**Model:** Gemini 2.5 Pro
**Purpose:** Extract structured marketing insights from uploaded files

```
As a Marketing Data Feature Extractor, analyze the following marketing artifacts
and extract key insights:

Number of artifacts: {count}
Artifacts Data: {json_artifact_summaries}

IMPORTANT: Even if the data is limited, provide your best analysis based on
available information. Do not ask for more data.

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

MUST return valid JSON. Do not include explanatory text outside JSON.
```

**Output Example:**
```json
{
  "target_audience": {
    "demographics": "25-45 year old professionals",
    "psychographics": "Tech-savvy, value-conscious"
  },
  "brand_positioning": "Premium quality at accessible prices",
  "channels": ["social_media", "search_ads", "email"],
  "messaging": ["Innovation", "Reliability", "Value"],
  "objectives": ["Brand awareness", "Lead generation"],
  "budget_insights": {"total": "$50K", "allocation": "60% digital"},
  "metrics": {"ctr": "3.2%", "conversion_rate": "2.1%"},
  "competitive_insights": ["Market leader in pricing"],
  "recommendations": ["Expand social presence", "Test video ads"]
}
```

---

### 2. INSIGHTS - Generate Strategic Insights
**Model:** GPT-5
**Purpose:** Deep strategic analysis and opportunity identification

```
As a Marketing Strategy Insights Expert, analyze these extracted features
and generate strategic recommendations:

Features: {json_features}

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
```

**Output Example:**
```json
{
  "opportunities": [
    "Untapped mobile audience segment",
    "Video content engagement potential"
  ],
  "targeting_strategy": {
    "primary_segment": "Tech professionals 28-35",
    "secondary_segment": "Early adopters 22-27",
    "expansion_segment": "Enterprise decision makers"
  },
  "channel_strategy": {
    "optimize": ["LinkedIn", "YouTube"],
    "expand": ["TikTok", "Podcast ads"],
    "reduce": ["Display ads"]
  },
  "messaging_strategy": {
    "theme": "Innovation meets simplicity",
    "tone": "Professional yet approachable",
    "key_pillars": ["Efficiency", "ROI", "Ease of use"]
  },
  "budget_strategy": {
    "reallocation": "Shift 20% from search to video",
    "priority_channels": ["Social: 40%", "Search: 30%", "Video: 30%"]
  },
  "performance_strategy": {
    "kpis": ["ROAS", "CAC", "LTV"],
    "targets": {"ROAS": "3x", "CAC": "<$100"}
  },
  "patch": {
    "path": "/discovery_phase",
    "operation": "INITIATE",
    "value": {
      "description": "Comprehensive market research",
      "tasks": [
        "Conduct stakeholder interviews",
        "Analyze competitor positioning",
        "Test messaging variants"
      ],
      "priority": "high"
    }
  },
  "justification": "Data shows 40% untapped mobile segment..."
}
```

---

### 3. PATCH - Create Strategy Patch
**Model:** GPT-5 (embedded in insights)
**Purpose:** Generate executable strategy changes

**Note:** The patch is generated as part of the insights step above. It includes:
- `path`: Where to apply the change (e.g., "/discovery_phase")
- `operation`: Type of change (e.g., "INITIATE", "UPDATE")
- `value`: The actual strategy modification
- `justification`: Why this change is recommended

---

### 4. EDIT_PATCH - LLM-Assisted Patch Editing
**Model:** GPT-5
**Purpose:** Rewrite strategy patch based on user feedback

```
As a Marketing Strategy Patch Editor, modify the existing strategy based
on this user feedback:

Edit Request: {edit_request}

Create an updated strategy patch that incorporates the user's feedback
while maintaining strategic coherence.

Return a JSON object with:
- updated_patch: object with modified strategy elements
- changes_made: array describing what was changed
- rationale: string explaining why changes were made
- impact_assessment: string describing expected impact
```

**Example Input:**
```
Edit Request: "Focus more on video content and reduce the timeline by 2 weeks"
```

**Output Example:**
```json
{
  "updated_patch": {
    "path": "/discovery_phase",
    "operation": "INITIATE",
    "value": {
      "description": "Accelerated video-first market research",
      "tasks": [
        "Rapid stakeholder video interviews (5 days)",
        "Video content competitor analysis (3 days)",
        "A/B test 3 video ad variants (4 days)"
      ],
      "priority": "high",
      "timeline": "12 days"
    }
  },
  "changes_made": [
    "Prioritized video content in all research activities",
    "Compressed timeline from 4 weeks to 12 days",
    "Replaced text-based interviews with video format"
  ],
  "rationale": "User requested video focus aligns with platform trends...",
  "impact_assessment": "Expected 40% faster execution with same quality..."
}
```

---

### 5. BRIEF - Compile Marketing Brief
**Model:** Gemini 2.5 Pro
**Purpose:** Create comprehensive campaign brief

```
As a Marketing Brief Compiler, create a comprehensive marketing brief from
this strategy:

Strategy: {json_strategy}

Create a detailed marketing brief including:
1. Executive summary
2. Campaign objectives
3. Target audience profile
4. Key messaging
5. Channel strategy
6. Budget allocation
7. Timeline and milestones
8. Success metrics

Return as a JSON object with these sections clearly structured.
```

---

### 6. ANALYZE - Performance Analysis
**Model:** GPT-5
**Purpose:** Analyze campaign performance metrics

```
As a Marketing Performance Analyst, analyze this campaign performance:

Campaign ID: {campaign_id}
Performance Data: {json_metrics}

Analyze:
1. Performance vs targets
2. Channel effectiveness
3. Audience engagement
4. Conversion funnel
5. Budget efficiency
6. Optimization opportunities

Return JSON with analysis and actionable recommendations.
```

---

## Frontend LLM Calls

The frontend also makes direct LLM calls for client-side features:

### Strategy Generation (Frontend)
**Model:** Gemini 2.5 Pro
**Location:** `web/src/lib/llm-service.ts`

```typescript
// Prompt for strategy generation
const strategyPrompt = `
Based on the following marketing analysis, create a comprehensive
marketing strategy in JSON format:

ANALYSIS DATA:
${JSON.stringify(analysisSnapshot, null, 2)}

Please generate a strategy in this exact JSON format:
{
  "strategy_id": "<generated_uuid>",
  "version": 1,
  "created_at": "${new Date().toISOString()}",
  "audience_targeting": {
    "segments": [...]
  },
  "messaging_strategy": {...},
  "channel_strategy": {...},
  "budget_allocation": {...}
}

Create a strategic plan that leverages the insights from the analysis
to maximize ROI and reach the identified audience segments effectively.
`
```

---

## Key Configuration Details

### Temperature Settings
- **Gemini 2.5 Pro:** Uses default (1.0) - no temperature parameter set
- **GPT-5:** Uses default (1.0) - reasoning models don't support custom temp

### Token Limits
- **Analysis prompts:** 2000 max tokens
- **Strategy prompts:** 2500 max tokens
- **Edit prompts:** Default limits

### Error Handling
- JSON extraction from markdown code blocks
- Fallback to sample data if LLM fails
- Detailed logging of all requests/responses

### System Instructions
- **Gemini:** "You are an expert marketing analytics AI..."
- **OpenAI:** "You are an expert marketing analyst AI."

---

## LLM Usage Summary

| Step | Model | Purpose | Input | Output |
|------|-------|---------|-------|--------|
| FEATURES | Gemini 2.5 Pro | Extract data | Artifact files | Structured features |
| INSIGHTS | GPT-5 | Strategic analysis | Features | Opportunities + Patch |
| PATCH | GPT-5 | Create changes | Insights | Strategy modifications |
| EDIT | GPT-5 | Rewrite patch | User feedback | Updated patch |
| BRIEF | Gemini 2.5 Pro | Create brief | Strategy | Campaign brief |
| ANALYZE | GPT-5 | Performance | Metrics | Analysis + Recommendations |

---

## Cost Optimization Strategy

1. **Use Gemini for data extraction** - Faster and cheaper for structured tasks
2. **Use GPT-5 for reasoning** - Advanced thinking for strategic decisions
3. **No unnecessary temperature settings** - Use model defaults
4. **JSON-only responses** - Minimize token usage
5. **Async processing** - Non-blocking workflow execution

---

## Debugging LLM Calls

Enable detailed logging:
```bash
DEBUG_LLM=true
```

This logs:
- Full prompts sent to LLMs
- Complete responses received
- Token usage (where available)
- JSON parsing attempts
- Error details with stack traces
