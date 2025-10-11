-- Migration: Fix Database Schema Alignment Issues
-- Date: 2025-10-08
-- Description: Align Supabase schema with backend/frontend expectations
--
-- Run this in Supabase SQL Editor to fix critical misalignments

-- ============================================================================
-- 1. FIX ARTIFACTS TABLE - Add missing columns for file upload support
-- ============================================================================
-- Issue: Backend tries to store file_content and file_size, but columns don't exist
-- Impact: File uploads fail silently

ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS file_content TEXT;
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS file_size INTEGER;

COMMENT ON COLUMN artifacts.file_content IS 'Base64 encoded file content for direct storage';
COMMENT ON COLUMN artifacts.file_size IS 'File size in bytes';

-- ============================================================================
-- 2. FIX ANALYSIS_SNAPSHOTS TABLE - Column name alignment
-- ============================================================================
-- Issue: Schema uses 'result_json' but backend/frontend expect 'snapshot_data'
-- Impact: FEATURES extraction step fails

-- Rename column from result_json to snapshot_data
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analysis_snapshots' AND column_name = 'result_json'
  ) THEN
    ALTER TABLE analysis_snapshots RENAME COLUMN result_json TO snapshot_data;
  END IF;
END $$;

-- Rename primary key from snapshot_id to id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analysis_snapshots' AND column_name = 'snapshot_id'
  ) THEN
    ALTER TABLE analysis_snapshots RENAME COLUMN snapshot_id TO id;
  END IF;
END $$;

-- ============================================================================
-- 3. FIX STRATEGY_PATCHES TABLE - Multiple alignment issues
-- ============================================================================
-- Issues:
-- - Schema uses 'patch_json' but backend uses 'patch_data'
-- - Missing 'strategy_id' foreign key (backend tries to set it)
-- - Missing 'annotations' column (LLM refactor features need it)

-- Rename patch_json to patch_data
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'strategy_patches' AND column_name = 'patch_json'
  ) THEN
    ALTER TABLE strategy_patches RENAME COLUMN patch_json TO patch_data;
  END IF;
END $$;

-- Add strategy_id foreign key
ALTER TABLE strategy_patches ADD COLUMN IF NOT EXISTS strategy_id UUID REFERENCES strategy_versions(strategy_id) ON DELETE SET NULL;

-- Add annotations column for heuristic/sanity flags
ALTER TABLE strategy_patches ADD COLUMN IF NOT EXISTS annotations JSONB;

COMMENT ON COLUMN strategy_patches.annotations IS 'Validation results: heuristic_flags, sanity_flags, auto_downscoped, etc.';

-- ============================================================================
-- 4. FIX STEP_EVENTS TABLE - Add metadata support
-- ============================================================================
-- Issue: Backend logs workflow metadata but column doesn't exist
-- Impact: Valuable metrics (candidates_evaluated, validation counts) are lost

ALTER TABLE step_events ADD COLUMN IF NOT EXISTS metadata JSONB;

COMMENT ON COLUMN step_events.metadata IS 'Workflow step metadata: candidates_evaluated, heuristic_flags_count, etc.';

-- ============================================================================
-- 5. FIX STRATEGY TABLE NAMING - Resolve confusion
-- ============================================================================
-- Issue: Schema defines 'strategy_versions' but backend uses 'strategies' table
-- Solution: Rename to match backend code (simpler than changing all backend references)

-- Rename table
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'strategy_versions'
  ) THEN
    ALTER TABLE strategy_versions RENAME TO strategies;
  END IF;
END $$;

-- Rename column from strategy_json to strategy_data
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'strategies' AND column_name = 'strategy_json'
  ) THEN
    ALTER TABLE strategies RENAME COLUMN strategy_json TO strategy_data;
  END IF;
END $$;

-- Update foreign key constraint in strategy_active table (if table exists)
DO $$
BEGIN
  -- Only update if strategy_active table exists
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'strategy_active'
  ) THEN
    -- Drop old constraint if it exists
    IF EXISTS (
      SELECT 1 FROM information_schema.table_constraints
      WHERE constraint_name = 'strategy_active_strategy_id_fkey'
    ) THEN
      ALTER TABLE strategy_active DROP CONSTRAINT strategy_active_strategy_id_fkey;
    END IF;

    -- Add new constraint pointing to 'strategies' table
    ALTER TABLE strategy_active ADD CONSTRAINT strategy_active_strategy_id_fkey
      FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id) ON DELETE CASCADE;
  END IF;
END $$;

-- Update foreign key in strategy_patches (now points to 'strategies')
DO $$
BEGIN
  -- Only update if we have a strategies table to reference
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'strategies'
  ) THEN
    -- Drop old constraint if it exists
    IF EXISTS (
      SELECT 1 FROM information_schema.table_constraints
      WHERE constraint_name = 'strategy_patches_strategy_id_fkey'
    ) THEN
      ALTER TABLE strategy_patches DROP CONSTRAINT strategy_patches_strategy_id_fkey;
    END IF;

    -- Add new constraint
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name = 'strategy_patches' AND column_name = 'strategy_id'
    ) THEN
      ALTER TABLE strategy_patches ADD CONSTRAINT strategy_patches_strategy_id_fkey
        FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id) ON DELETE SET NULL;
    END IF;
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify the migration succeeded

-- Check artifacts columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'artifacts'
  AND column_name IN ('file_content', 'file_size')
ORDER BY column_name;

-- Check analysis_snapshots columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'analysis_snapshots'
  AND column_name IN ('id', 'snapshot_data')
ORDER BY column_name;

-- Check strategy_patches columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'strategy_patches'
  AND column_name IN ('patch_data', 'strategy_id', 'annotations')
ORDER BY column_name;

-- Check strategies table exists
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'strategies';

-- Check step_events metadata column
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'step_events'
  AND column_name = 'metadata';

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================
-- ONLY RUN THIS IF YOU NEED TO REVERT THE MIGRATION

/*
-- Revert artifacts changes
ALTER TABLE artifacts DROP COLUMN IF EXISTS file_content;
ALTER TABLE artifacts DROP COLUMN IF EXISTS file_size;

-- Revert analysis_snapshots changes
ALTER TABLE analysis_snapshots RENAME COLUMN snapshot_data TO result_json;
ALTER TABLE analysis_snapshots RENAME COLUMN id TO snapshot_id;

-- Revert strategy_patches changes
ALTER TABLE strategy_patches RENAME COLUMN patch_data TO patch_json;
ALTER TABLE strategy_patches DROP COLUMN IF EXISTS strategy_id;
ALTER TABLE strategy_patches DROP COLUMN IF EXISTS annotations;

-- Revert step_events changes
ALTER TABLE step_events DROP COLUMN IF EXISTS metadata;

-- Revert strategy table naming
ALTER TABLE strategies RENAME TO strategy_versions;
ALTER TABLE strategy_versions RENAME COLUMN strategy_data TO strategy_json;
*/
