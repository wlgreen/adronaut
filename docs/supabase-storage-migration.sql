-- Migration: Remove file_content column from artifacts table
-- This migration removes the file_content column that should not exist in production
-- Files are now stored in Supabase Storage, not in the database

-- IMPORTANT: Run this ONLY if the file_content column exists in your artifacts table
-- Check first with: SELECT column_name FROM information_schema.columns WHERE table_name = 'artifacts';

-- If file_content column exists, remove it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'artifacts'
        AND column_name = 'file_content'
    ) THEN
        -- Drop the file_content column
        ALTER TABLE artifacts DROP COLUMN file_content;
        RAISE NOTICE 'file_content column has been removed from artifacts table';
    ELSE
        RAISE NOTICE 'file_content column does not exist - no action needed';
    END IF;

    -- Similarly, remove file_size if it exists (it's not in the schema but was being used)
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'artifacts'
        AND column_name = 'file_size'
    ) THEN
        ALTER TABLE artifacts DROP COLUMN file_size;
        RAISE NOTICE 'file_size column has been removed from artifacts table';
    ELSE
        RAISE NOTICE 'file_size column does not exist - no action needed';
    END IF;
END $$;

-- Verify the final schema
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'artifacts'
ORDER BY ordinal_position;

-- Expected columns:
-- artifact_id | uuid
-- project_id  | uuid
-- filename    | text
-- mime        | text
-- storage_url | text
-- summary_json| jsonb
-- created_at  | timestamp with time zone
