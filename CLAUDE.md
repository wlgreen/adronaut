# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adronaut is a sci-fi themed marketing mission control system using LLM-powered multi-agent workflows. It processes data artifacts (CSV, JSON, PDF, images), generates strategic insights via AI agents, and manages audience strategies through Human-in-the-Loop (HITL) workflows.

**Tech Stack:**
- Frontend: Next.js 15 + TypeScript + Tailwind CSS (App Router)
- Backend: FastAPI + Python with Google Gemini 2.5 Pro (primary) or OpenAI GPT-4o (fallback)
- Database: Supabase (PostgreSQL + Storage)
- Testing: Playwright (TypeScript) for E2E tests
- AI: Google Generative AI (Gemini) and LangChain

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
1. INGEST → 2. FEATURES → 3. INSIGHTS → 4. PATCH_PROPOSED → 5. HITL_PATCH (human approval)
   ↓           ↓             ↓              ↓                    ↓
   Files    Extract       Generate      Create Strategy      Approve/Reject/Edit
            Features      Insights      Patch Proposal       with LLM

6. APPLY → 7. BRIEF → 8. CAMPAIGN_RUN → 9. COLLECT → 10. ANALYZE → 11. REFLECTION_PATCH → 12. HITL_REFLECTION
   ↓          ↓           ↓                ↓            ↓              ↓                       ↓
   Update    Compile     Launch           Start        Performance    Propose                Human Review
   Strategy  Brief       Campaign         Metrics      Analysis       Adjustments            (if needed)
```

**Critical Implementation Details:**
- **Two Processing Paths**:
  - `/upload` (legacy): Saves to DB first, then processes
  - `/upload-direct` (Phase 1 optimization): Processes in-memory, then saves with pre-computed features
- **HITL Actions**: `approve` (continue workflow), `reject` (stop), `edit` (LLM rewrites patch based on natural language)
- **Real-time Updates**: Server-Sent Events (SSE) via `/events/{run_id}` for workflow progress
- **LLM Orchestration**: `gemini_orchestrator.py` handles all AI interactions with structured JSON responses

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

## Environment Variables

### Required for Backend (`service/.env`)
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key      # Primary
OPENAI_API_KEY=your-openai-api-key      # Fallback
PORT=8000
DEBUG=True                               # Enable detailed logging
DEBUG_LLM=true                           # Enable LLM request/response logging
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

### Adding a New Workflow Step
1. Update `run_autogen_workflow()` or `continue_autogen_workflow()` in `service/main.py`
2. Add step name to `step_events` logging: `await db.log_step_event(project_id, run_id, "NEW_STEP", "started")`
3. Update `active_runs[run_id]["current_step"]` for SSE tracking
4. Add corresponding UI state handling in frontend workflow components

### Adding a New LLM Agent
1. Create method in `service/gemini_orchestrator.py` following pattern:
   ```python
   async def new_agent_task(self, input_data: Dict) -> Dict[str, Any]:
       prompt = f"Your agent prompt using {input_data}"
       response = self.model.generate_content(prompt)
       return json.loads(self._extract_json_from_response(response.text))
   ```
2. Handle both Gemini and OpenAI fallback if needed
3. Add comprehensive logging with `logger.info()` for request/response

### Adding a New Test Scenario
1. Create test file: `e2e-tests/tests/NN-description.spec.ts`
2. Use page objects from `utils/page-objects.ts`
3. Generate unique data with `testDataManager.generateProjectId()`
4. Add cleanup to global teardown automatically
5. Tag with appropriate markers: `@critical`, `@smoke`, etc.

## Key Files Reference

### Backend Entry Points
- `service/main.py` - FastAPI app, routes, workflow orchestration (709 lines)
- `service/gemini_orchestrator.py` - LLM interactions and multi-agent logic
- `service/database.py` - Supabase operations with JSON serialization
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

### Documentation
- `README.md` - Project overview and setup
- `docs/supabase-schema.sql` - Complete database schema
- `AGENTS.md` - Repository coding conventions and guidelines (also important to read)
- `service/README.md` - Backend-specific documentation
- `web/README.md` - Frontend-specific documentation
