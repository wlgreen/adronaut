-- Migration: Add Missing Columns & Tables
-- Date: 2025-10-08
-- Description: Add only what's missing from your current schema
--
-- Current Status (from schema inspection):
-- ✓ artifacts has file_content, file_size
-- ✓ analysis_snapshots has id, snapshot_data
-- ✓ strategies table exists (not strategy_versions)
-- ✓ strategy_patches has patch_data, strategy_id
-- ✗ strategy_patches missing: annotations
-- ✗ step_events missing: metadata
-- ✗ strategy_active table missing

-- ============================================================================
-- 1. ADD MISSING COLUMN: strategy_patches.annotations
-- ============================================================================
-- Critical for LLM refactor features (heuristic flags, sanity flags)

ALTER TABLE strategy_patches ADD COLUMN IF NOT EXISTS annotations JSONB;

COMMENT ON COLUMN strategy_patches.annotations IS 'Validation results: heuristic_flags, sanity_flags, auto_downscoped, etc.';

-- ============================================================================
-- 2. ADD MISSING COLUMN: step_events.metadata
-- ============================================================================
-- Critical for workflow observability metrics

ALTER TABLE step_events ADD COLUMN IF NOT EXISTS metadata JSONB;

COMMENT ON COLUMN step_events.metadata IS 'Workflow step metadata: candidates_evaluated, heuristic_flags_count, etc.';

-- ============================================================================
-- 3. CREATE MISSING TABLE: strategy_active
-- ============================================================================
-- Tracks which strategy version is currently active per project

CREATE TABLE IF NOT EXISTS strategy_active (
  project_id UUID PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategies(strategy_id) ON DELETE CASCADE
);

COMMENT ON TABLE strategy_active IS 'Tracks the currently active strategy for each project';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check strategy_patches.annotations
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'strategy_patches' AND column_name = 'annotations';

-- Check step_events.metadata
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'step_events' AND column_name = 'metadata';

-- Check strategy_active table
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'strategy_active';

-- Success message
SELECT 'Migration 002 completed successfully! All missing columns and tables added.' AS status;
