# Supabase Storage Implementation Guide

## Overview

This document describes the implementation of proper Supabase Storage for file uploads in the Adronaut project. Previously, files were being stored directly in the PostgreSQL database as base64-encoded text, which is an anti-pattern. Files are now properly stored in Supabase Storage buckets.

## What Changed

### Before (Incorrect Implementation)
- Files were base64-encoded and stored in a `file_content` column in the `artifacts` table
- Storage URLs were fake references like `db://artifacts/{project_id}/{filename}`
- Large files caused database bloat and performance issues
- No actual use of Supabase Storage despite schema defining a storage bucket

### After (Correct Implementation)
- Files are uploaded to Supabase Storage bucket named `artifacts`
- Database only stores metadata (filename, MIME type, storage URL, summary)
- Storage URLs are real public URLs from Supabase Storage
- Scalable architecture that separates metadata from binary data

## Files Modified

### 1. `/Users/liangwang/adronaut/service/database.py`
**Changes:**
- Added `storage_bucket = "artifacts"` property
- Added `upload_to_storage()` method - uploads files to Supabase Storage
- Added `download_from_storage()` method - downloads files from Supabase Storage
- Added `get_storage_path()` helper - generates unique storage paths
- Updated `create_artifact()` - removed `file_content` parameter, now only stores metadata

**New Methods:**
```python
async def upload_to_storage(self, file_content: bytes, file_path: str, mime_type: str) -> str
async def download_from_storage(self, file_path: str) -> bytes
def get_storage_path(self, project_id: str, filename: str) -> str
```

### 2. `/Users/liangwang/adronaut/service/file_processor.py`
**Changes:**
- Removed `_prepare_file_storage()` method (no longer needed)
- Added `prepare_file_for_upload()` method (simplified, just returns raw bytes)
- Updated `process_file()` - returns `raw_content` instead of `file_content`

**Key Changes:**
- No more base64 encoding
- No more fake storage URLs
- Returns raw bytes ready for Supabase Storage upload

### 3. `/Users/liangwang/adronaut/service/main.py`
**Changes in `/upload` endpoint:**
- Added Supabase Storage upload step
- Uses `db.get_storage_path()` to generate unique path
- Uses `db.upload_to_storage()` to upload file
- Stores real storage URL in database

**Changes in `/upload-direct` endpoint:**
- Same as above - now uses Supabase Storage
- Returns storage URL in response

**Changes in `/artifact/{artifact_id}/download` endpoint:**
- No longer retrieves file content from database
- Extracts storage path from storage URL
- Downloads file from Supabase Storage using `db.download_from_storage()`

## Database Schema Changes

### Required Migration
If your production database has a `file_content` column (it shouldn't, but it might), run the migration:

```bash
# Execute the migration SQL
psql -h your-supabase-db.supabase.co -U postgres -d postgres -f docs/supabase-storage-migration.sql
```

Or run it directly in the Supabase SQL Editor:
```sql
-- See: docs/supabase-storage-migration.sql
```

### Expected Schema (artifacts table)
```sql
CREATE TABLE artifacts (
  artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  mime TEXT NOT NULL,
  storage_url TEXT NOT NULL,  -- Public URL from Supabase Storage
  summary_json JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**No `file_content` column** - files are in Supabase Storage, not the database.

## Supabase Storage Bucket Setup

### 1. Verify Bucket Exists
In Supabase Dashboard → Storage, verify that the `artifacts` bucket exists.

If not, create it:
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('artifacts', 'artifacts', true);
```

### 2. Configure Storage Policies
Ensure these policies exist (should be in the schema already):

```sql
-- Allow uploads
CREATE POLICY "Anyone can upload artifacts"
ON storage.objects
FOR INSERT
WITH CHECK (bucket_id = 'artifacts');

-- Allow downloads
CREATE POLICY "Anyone can view artifacts"
ON storage.objects
FOR SELECT
USING (bucket_id = 'artifacts');
```

**Security Note:** These policies allow public access. For production, you should implement proper RLS (Row Level Security) based on authentication.

### 3. Recommended Production Policies
For production, replace with authenticated policies:

```sql
-- Drop public policies
DROP POLICY "Anyone can upload artifacts" ON storage.objects;
DROP POLICY "Anyone can view artifacts" ON storage.objects;

-- Add authenticated policies
CREATE POLICY "Authenticated users can upload artifacts"
ON storage.objects
FOR INSERT
WITH CHECK (
  bucket_id = 'artifacts'
  AND auth.role() = 'authenticated'
);

CREATE POLICY "Authenticated users can view artifacts"
ON storage.objects
FOR SELECT
USING (
  bucket_id = 'artifacts'
  AND auth.role() = 'authenticated'
);
```

## Storage Path Structure

Files are stored with this path structure:
```
artifacts/
  {project_id}/
    {timestamp}_{filename}
```

Example:
```
artifacts/
  550e8400-e29b-41d4-a716-446655440000/
    20250106_143022_sales_data.csv
    20250106_143045_marketing_report.pdf
```

This ensures:
- Files are organized by project
- No filename collisions (timestamp prefix)
- Easy to identify when files were uploaded

## Storage URL Format

Files are stored and accessed via public URLs:
```
https://{project-id}.supabase.co/storage/v1/object/public/artifacts/{project_id}/{timestamp}_{filename}
```

Example:
```
https://abcdefgh.supabase.co/storage/v1/object/public/artifacts/550e8400-e29b-41d4-a716-446655440000/20250106_143022_sales_data.csv
```

## Testing the Implementation

### 1. Upload a Test File
```bash
curl -X POST "http://localhost:8000/upload?project_id=test-project-123" \
  -F "file=@test_file.csv"
```

Expected response:
```json
{
  "success": true,
  "artifact_id": "uuid-here",
  "project_id": "test-project-123",
  "storage_url": "https://{supabase-url}/storage/v1/object/public/artifacts/test-project-123/20250106_143022_test_file.csv"
}
```

### 2. Verify in Supabase Storage
- Go to Supabase Dashboard → Storage → artifacts bucket
- You should see the file under `{project_id}/` folder

### 3. Download the File
```bash
curl "http://localhost:8000/artifact/{artifact_id}/download" -o downloaded_file.csv
```

### 4. Verify Database
Check that the database only has metadata:
```sql
SELECT artifact_id, filename, storage_url,
       pg_column_size(summary_json) as summary_size
FROM artifacts
WHERE project_id = 'test-project-123';
```

You should NOT see a `file_content` column.

## Performance Benefits

### Before (DB Storage)
- 1MB file → ~1.33MB base64 in database (33% overhead)
- 10MB file → ~13.3MB in database
- Queries slow down as table size grows
- Expensive database storage costs

### After (Supabase Storage)
- 1MB file → 1MB in storage, ~200 bytes metadata in DB
- 10MB file → 10MB in storage, ~200 bytes metadata in DB
- Queries remain fast (only metadata)
- Cheaper object storage costs

## Monitoring Storage Usage

### Check Bucket Size
In Supabase Dashboard → Storage, view bucket size and file count.

### SQL Query for Metadata Size
```sql
SELECT
  COUNT(*) as total_files,
  pg_size_pretty(pg_total_relation_size('artifacts')) as table_size,
  AVG(pg_column_size(summary_json)) as avg_summary_size
FROM artifacts;
```

This should show a small table size since files are not stored in the DB.

## Rollback Plan

If you need to rollback to the old implementation (NOT recommended):

1. Revert the code changes (use git)
2. Download all files from Supabase Storage
3. Re-encode as base64 and store in database
4. Add back the `file_content` column

**Warning:** This is not recommended. The new implementation is the correct approach.

## Environment Variables

Ensure these are set in your `.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
```

The service role key is required for storage operations in the backend.

## Troubleshooting

### Error: "Storage upload error: bucket not found"
**Solution:** Create the storage bucket:
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('artifacts', 'artifacts', true);
```

### Error: "Permission denied for storage upload"
**Solution:** Check storage policies are configured correctly.

### Error: "File not found in storage" on download
**Solution:**
1. Verify the storage URL is correct in the database
2. Check the file exists in Supabase Storage dashboard
3. Ensure the storage path extraction logic is working

### Files not appearing in Storage dashboard
**Solution:**
1. Check logs for upload errors
2. Verify SUPABASE_URL and SUPABASE_KEY are correct
3. Check network connectivity to Supabase

## Best Practices

1. **File Size Limits:** Configure appropriate file size limits in FastAPI (currently unlimited)
2. **File Type Validation:** Validate MIME types before upload to prevent malicious files
3. **Storage Cleanup:** Implement a cleanup job to remove orphaned files if artifacts are deleted
4. **Backup Strategy:** Supabase Storage is backed up, but consider additional backup for critical files
5. **CDN Integration:** For high-traffic applications, consider using a CDN in front of Supabase Storage
6. **Authentication:** In production, always use authenticated storage policies

## Migration Checklist

- [ ] Run schema migration to remove `file_content` column (if exists)
- [ ] Verify storage bucket exists and is configured correctly
- [ ] Deploy updated code to backend service
- [ ] Test file upload with a sample file
- [ ] Verify file appears in Supabase Storage dashboard
- [ ] Test file download
- [ ] Monitor logs for any storage-related errors
- [ ] Update frontend to handle new response format (includes `storage_url`)
- [ ] Test with different file types (CSV, PDF, images, JSON)
- [ ] Verify existing files still work (if any were stored in DB previously)

## Additional Resources

- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- [Supabase Storage API Reference](https://supabase.com/docs/reference/javascript/storage-from-upload)
- [Storage Security and Permissions](https://supabase.com/docs/guides/storage/security/access-control)
