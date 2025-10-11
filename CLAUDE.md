# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adronaut is a sci-fi themed marketing mission control system using LLM-powered multi-agent workflows. It processes data artifacts (CSV, JSON, PDF, images), generates strategic insights via AI agents, and manages audience strategies through Human-in-the-Loop (HITL) workflows.

**Tech Stack:**
- Frontend: Next.js 15 + TypeScript + Tailwind CSS (App Router)
- Backend: FastAPI + Python with Google Gemini 2.5 Flash (cost-optimized, ~94% cheaper than Pro)
- Database: Supabase (PostgreSQL + Storage)
- Testing: Playwright (TypeScript) for E2E tests, pytest for backend unit tests
- AI: Google Generative AI (Gemini 2.5 Flash with temperature control 0.2-0.35)

## Essential Commands

### Development Setup
```bash
# First time setup
cp web/.env.example web/.env.local
cp service/.env.example service/.env

# Install dependencies
cd web && npm install
cd service && pip install -r requirements.txt

# Database setup: Run docs/supabase-schema.sql in Supabase SQL Editor
```

### Running Services
```bash
# Terminal 1: Frontend (port 3000)
cd web && npm run dev

# Terminal 2: Backend (port 8000)
cd service && uvicorn main:app --reload --port 8000

# View API docs: http://localhost:8000/docs
```

### Testing
```bash
# E2E tests (Playwright)
cd e2e-tests
npm install && npx playwright install
npm test                    # Run all tests
npm run test:critical       # Critical path only
npm run test:report         # Open HTML report

# Run single test file
npx playwright test tests/01-complete-campaign-flow.spec.ts --project=chromium

# QA Agent orchestrator
cd qa-agent
npm install && npm run build
npm run qa                  # Run orchestrated tests
npm run report:open         # View report
npm run db:reset            # Reset test database

# Service validation
cd service
python test_db.py           # Database connectivity
python full_db_test.py      # Full DB flow test
```

### Build & Lint
```bash
# Frontend
cd web
npm run build               # Production build with Turbopack
npm run lint                # ESLint check

# Backend has no dedicated build/lint - uses Python directly
```

## Architecture & Data Flow

### Multi-Agent Workflow Pipeline
The system orchestrates a 12-step workflow with two HITL checkpoints:

```
1. INGEST → 2. FEATURES → 3. INSIGHTS → 4. PATCH_GENERATION → 5. PATCH_PROPOSED → 6. HITL_PATCH
   ↓           ↓             ↓              ↓                     ↓                   ↓
   Files    Extract       Generate      Create Strategy       Store Proposal      Approve/Reject/Edit
            Features      k=5 insights  Patch with Filters    with Annotations    with LLM

7. APPLY → 8. BRIEF → 9. CAMPAIGN_RUN → 10. COLLECT → 11. ANALYZE → 12. REFLECTION_PATCH → 13. HITL_REFLECTION
   ↓          ↓           ↓                 ↓            ↓              ↓                       ↓
   Update    Compile     Launch            Start        Performance    Propose                Human Review
   Strategy  Brief       Campaign          Metrics      Analysis       Adjustments            (if needed)
```

**Critical Implementation Details:**
- **Two Processing Paths**:
  - `/upload` (legacy): Saves to DB first, then processes
  - `/upload-direct` (Phase 1 optimization): Processes in-memory, then saves with pre-computed features
- **HITL Actions**: `approve` (continue workflow), `reject` (stop), `edit` (LLM rewrites patch based on natural language)
- **Real-time Updates**: Server-Sent Events (SSE) via `/events/{run_id}` for workflow progress
- **LLM Orchestration**: `gemini_orchestrator.py` handles all AI interactions with structured JSON responses
- **2-Step INSIGHTS→PATCH Flow**: INSIGHTS generates k=5 candidates and selects top 3 (NO patch), then PATCH_GENERATION creates strategy patch with heuristic filters and sanity gate (BREAKING CHANGE as of Oct 2025 refactor)

### Key Service Endpoints
- `POST /upload-direct` - Upload file with immediate LLM processing (faster)
- `POST /autogen/run/start` - Start workflow (returns run_id for SSE)
- `POST /autogen/run/continue` - HITL decision (approve/reject/edit patch)
- `GET /events/{run_id}` - SSE stream for workflow status
- `GET /project/{project_id}/status` - Get project state, pending patches, campaigns

### Database Schema (Supabase)
**Core Tables:**
- `projects` - Top-level project container
- `artifacts` - Uploaded files with storage URLs and summaries (includes `file_content` TEXT and `file_size` INTEGER columns for Phase 1)
- `analysis_snapshots` - LLM-extracted features (JSONB)
- `strategy_patches` - Proposed changes (status: proposed/approved/rejected/superseded)
- `strategy_versions` - Versioned strategies with active tracking
- `campaigns` - Launched campaigns with policies
- `metrics` - Performance data (impressions, clicks, spend, conversions, revenue)
- `step_events` - Workflow execution logs (run_id, step_name, status)

**Important Constraints:**
- `strategy_patches.source` must be: 'insights', 'reflection', or 'edited_llm'
- `strategy_patches.status` must be: 'proposed', 'approved', 'rejected', or 'superseded'
- Patches reference projects directly (no foreign key to strategy_versions initially)

### Frontend Architecture
**App Router Structure:**
- `/workspace` - File upload and analysis snapshots
- `/strategy` - HITL patch approval/rejection/editing interface
- `/results` - Campaign metrics and performance dashboard

**Key Components:**
- `FileUploader` (workspace) - Drag-and-drop with real-time SSE progress
- `PatchReviewCard` (strategy) - HITL decision interface with LLM-assisted editing
- `MetricsDashboard` (results) - Performance visualization

**Utilities:**
- `src/lib/supabase.ts` - Supabase client initialization
- Uses environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_AUTOGEN_SERVICE_URL`

## Testing Strategy

### E2E Test Organization (Playwright)
Tests are numbered for execution order clarity:

1. **01-complete-campaign-flow.spec.ts** - Full end-to-end flow (upload → analysis → HITL → campaign)
2. **02-hitl-workflow.spec.ts** - HITL approval/rejection/editing, multi-tab sync, XSS prevention
3. **03-file-upload-processing.spec.ts** - File types (CSV/JSON/TXT/PDF), size limits, concurrent uploads
4. **04-error-handling.spec.ts** - Service failures, network interruption, malformed AI responses, security
5. **05-performance-testing.spec.ts** - Upload/workflow/query performance, load testing, baselines

**Test Infrastructure:**
- **Page Objects** (`utils/page-objects.ts`): WorkspacePage, StrategyPage, ResultsPage, NavigationHelper, APIHelper
- **Test Data Manager** (`utils/test-data-manager.ts`): Unique project IDs, scenario-based data (e-commerce, B2B SaaS, content marketing), cleanup
- **Test Helpers** (`utils/test-helpers.ts`): Retry logic, SSE monitoring, network simulation, performance measurement
- **Global Setup/Teardown**: Service health checks, automatic cleanup

**Performance Thresholds:**
- Upload: 10s (configurable via `UPLOAD_TIME_THRESHOLD_MS`)
- Workflow: 60s (configurable via `WORKFLOW_TIME_THRESHOLD_MS`)
- API Response: 2s
- Page Load: 5s

### Running Tests Effectively
```bash
# Critical path tests (fastest feedback)
npm run test:critical

# Single browser for speed
npx playwright test --project=chromium

# Headed mode for debugging
npx playwright test --headed --project=chromium

# Performance regression check
cd e2e-tests && node scripts/performance-regression-check.js

# Generate consolidated report
cd e2e-tests && node scripts/generate-test-report.js
```

## Code Conventions

### Python (Backend)
- **Async/await everywhere**: All database and LLM operations are async
- **Logging with run_id**: Use `logger.info(f"[RUN {run_id[:8]}] message")` for workflow traceability
- **LLM Debug Mode**: Set `DEBUG_LLM=true` for detailed request/response logging
- **JSON Serialization**: Use `Database._serialize_json_data()` to handle numpy/pandas types before storing JSONB
- **Error Handling**: Capture detailed errors in `active_runs[run_id]` with status="failed", error, error_type

### TypeScript (Frontend)
- **Component naming**: PascalCase files in `src/components/` (e.g., `StrategyOverview.tsx`)
- **Utilities**: camelCase files in `src/lib/` (e.g., `supabase.ts`)
- **Async operations**: Always handle loading/error states in UI
- **SSE pattern**: Use EventSource for real-time updates, handle reconnection

### Test Files (Playwright)
- **Naming**: `NN-descriptive-name.spec.ts` (e.g., `01-complete-campaign-flow.spec.ts`)
- **Tags**: Use `@critical`, `@smoke`, `@performance`, `@security` for categorization
- **Isolation**: Each test gets unique `project_id` via `testDataManager.generateProjectId()`
- **Cleanup**: Automatic via global teardown (`CLEANUP_TEST_DATA=true`)

### Python Backend Tests
- **Unit Tests**: Use pytest, assert statements, and fixtures
- **Test Files**: Name as `test_*.py` (e.g., `test_llm_refactor.py`)
- **Run Tests**: `cd service && pytest test_llm_refactor.py -v` (29 tests for foundation modules)
- **Integration Tests**: Use `test_llm_flow.py` for complete workflow validation with real artifacts

## Important Behavioral Patterns

### LLM Response Handling
The `GeminiOrchestrator._extract_json_from_response()` method handles three formats:
1. Markdown code blocks: ` ```json {...} ``` `
2. Clean JSON: Direct `{...}` response
3. Loose JSON: Searches for JSON-like content with regex

Always expect LLM responses to be parsed and validated before database storage.

### HITL Edit Workflow
When user edits a patch:
1. Original patch is marked `status='superseded'`
2. LLM generates new patch based on edit request (via `orchestrator.edit_patch_with_llm()`)
3. New patch created with `source='edited_llm'`
4. Auto-approved and workflow continues

### Workflow State Management
- **Active runs tracked in-memory**: `active_runs[run_id]` dict with status, current_step, events
- **Persistent logging**: All steps logged to `step_events` table
- **SSE streaming**: Polls active_runs every 1s, streams to frontend
- **Failure handling**: Sets status='failed', captures error/error_type, logs to DB

### File Processing Optimization (Phase 1)
The `/upload-direct` endpoint implements in-memory processing:
1. Extract content directly from UploadFile (no disk write)
2. Process with LLM immediately (no DB read roundtrip)
3. Store artifact with pre-computed features in summary_json
4. Skip separate feature extraction step

### LLM Temperature Control & Determinism (Oct 2025 Refactor)
All LLM tasks use Gemini 2.5 Flash with specific temperatures for determinism vs creativity:
- **FEATURES (temp=0.2)**: Deterministic extraction, no speculation
- **INSIGHTS (temp=0.35)**: Moderate creativity for k=5 hypothesis generation
- **PATCH (temp=0.2)**: Deterministic strategy patch creation
- **EDIT (temp=0.2)**: Minimal delta changes only
- **BRIEF (temp=0.3)**: Slightly creative for brief compilation
- **ANALYZE (temp=0.35)**: Moderate for performance analysis

**CRITICAL**: GPT-5/o1 models do NOT support temperature (fixed at 1.0). Use Gemini for all tasks requiring temperature control.

### Structured Insights Schema (Oct 2025 Refactor)
Every insight MUST contain exactly 11 required fields:
```typescript
{
  insight: string                    // Observable pattern from data
  hypothesis: string                 // Causal explanation
  proposed_action: string           // Specific action
  primary_lever: 'audience' | 'creative' | 'budget' | 'bidding' | 'funnel'
  expected_effect: {
    direction: 'increase' | 'decrease'
    metric: string
    magnitude: 'small' | 'medium' | 'large'
  }
  confidence: number                 // 0.0 to 1.0
  data_support: 'strong' | 'moderate' | 'weak'
  evidence_refs: string[]           // e.g., ["features.metrics.ctr"]
  contrastive_reason: string        // Why this vs alternative
  impact_rank: number               // 1, 2, or 3
  impact_score: number              // 0 to 100 (deterministic rubric)
}
```

**Acceptance Criteria**: ≥95% of insights contain all 11 fields, exactly 3 insights always, invalid JSON ≤1%

### Candidate Generation & Selection (Oct 2025 Refactor)
**INSIGHTS Step**:
1. LLM generates k=5 insight candidates @ temp=0.35
2. Each candidate validated for structure (11 required fields)
3. All valid candidates scored using deterministic rubric (0-100):
   - +2 points if evidence_refs present
   - +2 if data_support='strong', +1 if 'moderate'
   - +1 if expected_effect has direction AND magnitude
   - +1 if single primary_lever targeted
   - -1 if weak support without learn/test action
   - Score normalized to 0-100 scale
4. Top 3 selected deterministically (score desc, then index for tiebreaker)
5. impact_rank (1-3) and impact_score added to final output

**PATCH_GENERATION Step** (separate from INSIGHTS):
1. Takes top 3 insights as input
2. LLM generates strategy patch @ temp=0.2
3. Heuristic filters applied (budget ≤25%, no audience overlap, ≤3 creatives)
4. Auto-downscope if violations (scale budget by 0.8, trim themes)
5. Sanity gate applied (LLM reflection @ temp=0.2)
6. Annotations stored with patch (heuristic_flags, sanity_flags)

### Heuristic Validation Rules (Oct 2025 Refactor)
Post-processing filters WITHOUT external data:
1. **Budget Sanity**: Total budget shift ≤25% across all channels
2. **Audience Sanity**: No overlapping targeting (geo, age, interests) combinations
3. **Creative Sanity**: ≤3 creative themes per audience segment
4. **Auto-downscope**: If violations detected, attempt automatic correction:
   - Budget shifts scaled by 0.8
   - Creative themes trimmed to top 3
5. **Requires HITL**: If violations persist after downscope

### Sanity Gate (LLM Reflection, Oct 2025 Refactor)
Final validation using LLM @ temp=0.2:
1. Prompt includes full patch + context
2. LLM reviews for logical consistency, risk assessment
3. Returns flagged actions with risk level (high/medium/low) and reasons
4. Flags stored in patch.annotations.sanity_flags
5. sanity_review field set to: 'safe', 'review_recommended', or 'high_risk'

## Environment Variables

### Required for Backend (`service/.env`)
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key      # Primary (Gemini 2.5 Flash for cost optimization)
OPENAI_API_KEY=your-openai-api-key      # Fallback (not used for temperature-controlled tasks)
PORT=8000
DEBUG=True                               # Enable detailed logging
DEBUG_LLM=true                           # Enable LLM request/response logging

# LLM Model Configuration (Oct 2025 - All Gemini Flash for ~94% cost savings)
LLM_FEATURES=gemini:gemini-2.5-flash
LLM_INSIGHTS=gemini:gemini-2.5-flash
LLM_PATCH=gemini:gemini-2.5-flash
LLM_BRIEF=gemini:gemini-2.5-flash
LLM_ANALYZE=gemini:gemini-2.5-flash
LLM_EDIT=gemini:gemini-2.5-flash
```

### Required for Frontend (`web/.env.local`)
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_AUTOGEN_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_OPENAI_API_KEY=your-openai-api-key  # For client-side LLM (optional)
```

### Required for E2E Tests (`e2e-tests/.env.local`)
```env
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
```

## Debugging Tips

### Backend Issues
```bash
# Check logs with LLM debugging
DEBUG_LLM=true uvicorn main:app --reload --port 8000

# Test database connectivity
python service/test_db.py

# View logs (if /tmp exists)
tail -f /tmp/adronaut_service.log

# Check active runs (in Python REPL during development)
from main import active_runs
print(active_runs)

# Run LLM refactor unit tests (Oct 2025)
cd service
pytest test_llm_refactor.py -v              # All 29 tests
pytest test_llm_refactor.py::TestMechanicsCheatSheet -v  # Specific class

# Test complete LLM workflow locally (Oct 2025)
cd service
python test_llm_flow.py test_sample_data.csv
# Outputs color-coded results and saves detailed log file
```

### Frontend Issues
```bash
# Check browser console for SSE errors
# EventSource connection issues often indicate backend not running

# Verify environment variables are loaded
npm run dev
# Check terminal output for NEXT_PUBLIC_* vars

# Inspect Supabase queries
# Use Supabase Dashboard > Logs > API Logs
```

### Test Failures
```bash
# View test artifacts
open e2e-tests/test-results/html-report/index.html

# Check screenshots for failures
ls e2e-tests/test-results/artifacts/

# Run with trace for debugging
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip
```

## Common Patterns

### Adding a New Workflow Step (Dec 2025 - Updated for WorkflowEngine)
**IMPORTANT:** Workflow logic now lives in `service/workflow_engine.py`, NOT in `main.py`!

1. **Update `workflow_engine.py`** - Add new step to `run_llm_workflow()` method
2. **Update step event logging** - Add `db.log_step_event()` calls in workflow_engine
3. **Update `main.py` SSE tracking** - Add SSE status updates for new step in `run_autogen_workflow()`
4. **Update frontend** - Add corresponding UI state handling in frontend workflow components
5. **Test automatically syncs** - `test_llm_flow.py` will automatically pick up the new step!

**Example:** Adding a "ENRICH" step between FEATURES and INSIGHTS:
```python
# In workflow_engine.py run_llm_workflow():
features = await self.orchestrator.extract_features(artifacts)

# NEW STEP
log("🎨 ENRICHMENT: Adding external data...", 'info')
enriched_features = await self.orchestrator.enrich_features(features)

insights_result = await self.orchestrator.generate_insights(enriched_features)  # Use enriched
```

**Old Pattern (deprecated):** Editing `run_autogen_workflow()` directly in `main.py` - this creates drift between production and tests!

### Adding a New LLM Agent
1. Create method in `service/gemini_orchestrator.py` following pattern:
   ```python
   async def new_agent_task(self, input_data: Dict) -> Dict[str, Any]:
       from .logging_metrics import LLMMetrics

       # Build prompt (consider adding mechanics_cheat_sheet if needed)
       prompt = f"Your agent prompt using {input_data}"

       # Call LLM with temperature control (use _call_llm for automatic metrics)
       response_text = await self._call_llm('NEW_TASK', prompt)

       # Parse and validate
       result = json.loads(self._extract_json_from_response(response_text))

       # Log job-level metrics
       LLMMetrics.log_custom_job('NEW_TASK', latency_ms, validation_passed, ...)

       return result
   ```
2. Add task to TASK_TEMPERATURES dict (line 16-24) with appropriate temperature
3. Add task to task_llm_config (line 74-82) with LLM model config
4. Use Gemini for temperature-controlled tasks (GPT-5/o1 doesn't support temperature)
5. Add comprehensive logging with `logger.info()` for request/response

### Adding a New Test Scenario
1. Create test file: `e2e-tests/tests/NN-description.spec.ts`
2. Use page objects from `utils/page-objects.ts`
3. Generate unique data with `testDataManager.generateProjectId()`
4. Add cleanup to global teardown automatically
5. Tag with appropriate markers: `@critical`, `@smoke`, etc.

## Key Files Reference

### Backend Entry Points
- `service/main.py` - FastAPI app, routes, workflow orchestration (~650 lines, refactored Dec 2025 to use WorkflowEngine)
- `service/workflow_engine.py` - **NEW (Dec 2025)** Reusable LLM workflow logic (~300 lines) - single source of truth for FEATURES→INSIGHTS→PATCH
- `service/gemini_orchestrator.py` - LLM interactions and multi-agent logic (~1100 lines, refactored Oct 2025 with temperature control)
- `service/database.py` - Supabase operations with JSON serialization (updated Oct 2025 for annotations support)
- `service/file_processor.py` - File upload and content extraction

### Frontend Entry Points
- `web/src/app/workspace/page.tsx` - File upload and analysis
- `web/src/app/strategy/page.tsx` - HITL patch review
- `web/src/app/results/page.tsx` - Campaign metrics
- `web/src/lib/supabase.ts` - Database client

### Test Entry Points
- `e2e-tests/playwright.config.ts` - Test configuration with webServer setup
- `e2e-tests/tests/01-complete-campaign-flow.spec.ts` - Primary E2E flow
- `e2e-tests/utils/page-objects.ts` - Reusable page interactions
- `e2e-tests/utils/test-data-manager.ts` - Test data generation and cleanup

### LLM Refactor Foundation Modules (Oct 2025)
- `service/workflow_engine.py` - **NEW (Dec 2025)** Reusable workflow logic for auto-sync between production and tests
- `service/mechanics_cheat_sheet.py` - Metric→lever mappings for evidence-based recommendations
- `service/insights_selector.py` - Deterministic scoring rubric (0-100) for selecting top 3 insights
- `service/heuristic_filters.py` - Budget/audience/creative validation with auto-downscope
- `service/sanity_gate.py` - LLM reflection gate for final validation
- `service/logging_metrics.py` - Observability metrics for acceptance criteria tracking
- `service/test_llm_refactor.py` - 29 unit tests for foundation modules
- `service/test_llm_flow.py` - Local integration test script (auto-syncs with production via WorkflowEngine)
- `service/test_sample_data.csv` - Sample campaign data for testing

### Documentation
- `README.md` - Project overview and setup
- `docs/supabase-schema.sql` - Complete database schema
- `AGENTS.md` - Repository coding conventions and guidelines (also important to read)
- `service/README.md` - Backend-specific documentation
- `web/README.md` - Frontend-specific documentation
- `LLM_REFACTOR_COMPLETE.md` - Complete LLM refactor documentation (Oct 2025)
- `TEST_LLM_FLOW_README.md` - Local LLM testing guide
- `COST_OPTIMIZATION_GEMINI_FLASH.md` - Cost savings analysis (~94% reduction)

## LLM Refactor Summary (October 2025)

### Overview
Comprehensive refactoring of the LLM service to produce measurably more useful outputs for ad performance using only existing inputs. Switched all LLM calls from Gemini 2.5 Pro to Gemini 2.5 Flash for ~94% cost reduction while maintaining quality.

### Key Changes

**1. Structured Performance Hypotheses**
- Every insight now contains 11 required fields (vs previous unstructured format)
- Includes hypothesis, proposed_action, primary_lever, expected_effect, confidence, data_support, evidence_refs, contrastive_reason, impact_rank, impact_score
- Acceptance criteria: ≥95% field compliance

**2. Mechanics Cheat Sheet**
- Embedded metric→lever mappings in all prompts (CTR→creative/audience, Conversion→funnel/creative, CPA→bidding/audience, ROAS→audience/budget)
- Ensures evidence-based recommendations aligned with ad mechanics

**3. Ranking & Prioritization**
- Generate k=5 candidates, score deterministically, select top 3 (always exactly 3)
- Deterministic rubric: +2 for evidence_refs, +2 for strong support, +1 for complete expected_effect, +1 for single lever, -1 for weak support without learn/test
- impact_score (0-100) and impact_rank (1-3) added to final output

**4. Contrastive Reasoning**
- Every insight includes contrastive_reason field explaining "why this vs alternative"
- Helps users understand tradeoffs and decision rationale

**5. Confidence & Data Support Tracking**
- confidence (0.0-1.0) and data_support ('strong'/'moderate'/'weak') required
- Weak support requires learn/test actions (pilots, A/B tests, limited budget)

**6. Heuristic Patch Filters**
- Budget sanity: ≤25% total shift across channels
- Audience sanity: No overlapping targeting combinations
- Creative sanity: ≤3 themes per audience segment
- Auto-downscope: Scale budget by 0.8, trim themes if violations

**7. Sanity Reflection Gate**
- LLM reviews patch @ temp=0.2 before output
- Flags actions with risk level (high/medium/low) and recommendations
- sanity_review field: 'safe', 'review_recommended', or 'high_risk'

**8. Temperature Control & Determinism**
- FEATURES: 0.2 (deterministic extraction, no speculation)
- INSIGHTS: 0.35 (moderate creativity for hypothesis generation)
- PATCH: 0.2 (deterministic strategy patch)
- EDIT: 0.2 (minimal delta changes)
- All tasks use Gemini 2.5 Flash (GPT-5/o1 doesn't support temperature)

### Breaking Changes

**INSIGHTS Step No Longer Returns Patch**
- OLD: `generate_insights()` returned `{insights: [...], patch: {...}}`
- NEW: `generate_insights()` returns `{insights: [...], candidates_evaluated: 5, selection_method: 'deterministic_rubric'}`
- NEW: `generate_patch(insights)` separate method for patch creation

**Workflow Changes**
- OLD: INSIGHTS → PATCH_PROPOSED (1 step)
- NEW: INSIGHTS → PATCH_GENERATION → PATCH_PROPOSED (2 steps)
- Database: strategy_patches.annotations JSONB field stores heuristic_flags and sanity_flags

### Cost Optimization

**Gemini 2.5 Flash Pricing:**
- Input: $0.075 per 1M tokens (~94% cheaper than Pro's $1.25/1M)
- Output: $0.30 per 1M tokens (~94% cheaper than Pro's $5.00/1M)

**Estimated Savings:**
- 1M input + 500K output tokens/month: $3.75 → $0.225 (~94% reduction)
- 100M tokens/month: ~$350/month savings

**Why Flash Works Well:**
- Excels at structured JSON output (our primary use case)
- Supports same temperature range (0.0-2.0) as Pro
- ~2x faster response times
- Perfect for deterministic tasks with low temperature

### Testing

**Unit Tests** (`service/test_llm_refactor.py`):
- 29 tests covering all 5 foundation modules
- TestMechanicsCheatSheet (5 tests)
- TestInsightsSelector (8 tests)
- TestHeuristicFilters (9 tests)
- TestSanityGate (4 tests)
- TestLoggingMetrics (3 tests)

**Integration Test** (`service/test_llm_flow.py`):
- Complete workflow: ARTIFACT → FEATURES → INSIGHTS → PATCH
- Tests with real Gemini API calls
- Color-coded terminal output
- Detailed logging to file
- Usage: `python test_llm_flow.py test_sample_data.csv`

### Acceptance Criteria Status

✅ **Field Compliance**: ≥95% (enforced by schema validation)
✅ **Top-3 Only**: Always exactly 3 insights
✅ **Invalid JSON**: ≤1% (robust parsing with 3-format fallback)
✅ **Heuristic Flags**: Appear when rules trigger (budget/audience/creative)
✅ **Sanity Flags**: LLM reflection gate applied
✅ **Temperatures**: Enforced and logged for all tasks
⏳ **Time-to-Approved-Patch**: To be measured in production
⏳ **Approve-Without-Edit Rate**: To be measured in production

### Files Modified/Created

**Created (11 files):**
- service/mechanics_cheat_sheet.py (160 lines)
- service/insights_selector.py (220 lines)
- service/heuristic_filters.py (240 lines)
- service/sanity_gate.py (190 lines)
- service/logging_metrics.py (240 lines)
- service/test_llm_refactor.py (420 lines)
- service/test_llm_flow.py (450 lines)
- service/test_sample_data.csv (sample data)
- LLM_REFACTOR_COMPLETE.md
- TEST_LLM_FLOW_README.md
- COST_OPTIMIZATION_GEMINI_FLASH.md

**Modified (6 files):**
- service/gemini_orchestrator.py (~500 lines changed)
- service/main.py (~120 lines changed)
- service/database.py (~40 lines changed)
- service/.env.example (all LLM configs → Flash)
- web/src/lib/llm-service.ts (~70 lines changed)
- web/src/lib/gemini-service.ts (2 lines changed)

### Migration Guide

1. **Update Environment Variables**:
   ```bash
   cd service
   # Update .env with all LLM_* variables using gemini-2.5-flash
   LLM_FEATURES=gemini:gemini-2.5-flash
   LLM_INSIGHTS=gemini:gemini-2.5-flash
   LLM_PATCH=gemini:gemini-2.5-flash
   # ... (see .env.example for full list)
   ```

2. **Run Unit Tests**:
   ```bash
   cd service
   pytest test_llm_refactor.py -v
   # Should pass all 29 tests
   ```

3. **Test Workflow Locally**:
   ```bash
   cd service
   python test_llm_flow.py test_sample_data.csv
   # Verify: exactly 3 insights, all required fields, filters applied
   ```

4. **Deploy Backend**:
   ```bash
   cd service
   uvicorn main:app --reload --port 8000
   # Check logs for: "✅ Gemini API configured with model: gemini-2.5-flash"
   ```

5. **Monitor Metrics**:
   ```bash
   # Check logs for validation metrics
   grep "INSIGHTS_JOB" /tmp/adronaut_service.log
   grep "PATCH_JOB" /tmp/adronaut_service.log

   # Verify temperatures
   grep "temperature=" /tmp/adronaut_service.log
   ```

### Known Issues & Limitations

- GPT-5/o1 reasoning models do NOT support temperature (fixed at 1.0) - use Gemini for all temperature-controlled tasks
- Frontend interfaces need updating to display new insight fields (impact_score, contrastive_reason, etc.)
- HITL review UI doesn't yet show heuristic_flags and sanity_flags annotations
- Performance benchmarks (time-to-approved-patch, approve-without-edit rate) not yet measured in production

### Next Steps

1. Deploy to staging environment
2. Monitor quality metrics for 24-48 hours
3. Update frontend to display new insight fields and annotations
4. Measure acceptance criteria in production (time-to-approved-patch, approve-without-edit rate)
5. Consider implementing Gemini prompt caching for additional ~50% cost savings on repeated prompts
