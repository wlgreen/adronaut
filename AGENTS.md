# Repository Guidelines

## Project Structure & Module Organization
- `service/` — FastAPI backend (LLM orchestration, Supabase access). Key files: `main.py`, `database.py`, `file_processor.py`.
- `web/` — Next.js + TypeScript frontend. App Router under `web/src/app`, components in `web/src/components`, utilities in `web/src/lib`.
- `e2e-tests/` — Playwright E2E suite (TypeScript) targeting full user flows.
- `qa-agent/` — Test agent orchestrator and helpers for database seeding/reset and reporting.
- `docs/` — Database schema and reference SQL (`docs/supabase-schema.sql`).

## Build, Test, and Development Commands
- Web: `cd web`
  - `npm run dev` (local dev), `npm run build` (prod build), `npm start` (serve), `npm run lint` (ESLint).
- Service: `cd service`
  - `uvicorn main:app --reload --port 8000` (run API), `pip install -r requirements.txt` (deps).
  - Useful checks: `python test_db.py`, `python full_db_test.py`.
- E2E: `cd e2e-tests`
  - `npm install && npx playwright install`, `npm test`, `npm run test:critical`, `npm run test:report`.
- QA Agent: `cd qa-agent`
  - `npm install && npm run build`, `npm run qa`, `npm run report:open`, `npm run db:reset`.

## Coding Style & Naming Conventions
- Python (service): PEP 8, 4-space indent, explicit async I/O; prefer `snake_case` for modules/functions.
- TypeScript/React (web): ESLint (Next core-web-vitals). Use `PascalCase` for components (`src/components/StrategyOverview.tsx`), `camelCase` for utilities (`src/lib/supabase.ts`). Keep files focused and typed.
- Tests: Playwright specs named `NN-descriptive-name.spec.ts` (e.g., `tests/01-complete-campaign-flow.spec.ts`).

## Testing Guidelines
- Primary: Playwright under `e2e-tests/` (`npm test`, or `npm run test:critical`). Include assertions and tags (`@critical`, `@smoke`).
- Service checks: run `python service/test_db.py` and `python service/full_db_test.py` for DB and file flows.
- Add/adjust tests when changing user flows, API contracts, or DB schema. Include links to generated reports in PRs (see `web/*REPORT*.md`).

## Commit & Pull Request Guidelines
- Commits: short, imperative subject (e.g., “Fix database JSON parsing”), optional scope (`web:`, `service:`), concise body when rationale matters.
- PRs must include: clear description, linked issues, reproduction/validation steps (commands), and evidence (screenshots or test report paths).
- Ensure `web` lints clean and key tests pass before requesting review.

## Security & Configuration Tips
- Never commit secrets. Use `.env` files (`web/.env.local`, `service/.env`). Example: `cp web/.env.example web/.env.local`.
- Configure Supabase using `docs/supabase-schema.sql`. Verify `NEXT_PUBLIC_*`, `SUPABASE_*`, and LLM keys are set locally/CI.

## Agent-Specific Instructions
- Keep diffs minimal and scoped; do not refactor unrelated code. Follow this guide’s conventions and reference files with exact paths (e.g., `web/src/lib/supabase.ts`).
