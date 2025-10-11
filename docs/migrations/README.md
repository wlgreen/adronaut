# Database Schema Migration Guide

## Overview

This migration fixes critical alignment issues between the Supabase database schema, Python backend (`service/`), and Next.js frontend (`web/`).

## Issues Fixed

✅ **Artifacts table** - Added `file_content` and `file_size` columns for file upload support
✅ **Analysis snapshots** - Renamed `result_json` → `snapshot_data`, `snapshot_id` → `id`
✅ **Strategy table** - Renamed `strategy_versions` → `strategies`, `strategy_json` → `strategy_data`
✅ **Strategy patches** - Renamed `patch_json` → `patch_data`, added `strategy_id` and `annotations` columns
✅ **Step events** - Added `metadata` column for workflow observability

## Migration Steps

### Step 1: Run SQL Migration

1. **Open Supabase Dashboard**
   - Go to https://app.supabase.com/
   - Select your project
   - Navigate to **SQL Editor**

2. **Execute Migration**
   - Click **New Query**
   - Copy the entire contents of `001_fix_schema_alignment.sql` (this directory)
   - Paste into the SQL editor
   - Click **Run** or press `Cmd/Ctrl + Enter`

3. **Verify Migration**
   - Scroll to the bottom of the output
   - Check that verification queries show the correct columns
   - Expected output:
     ```
     column_name    | data_type
     ---------------|----------
     file_content   | text
     file_size      | integer
     ```

### Step 2: Verify Schema Alignment

Run the verification script to ensure everything is working:

```bash
cd service
python verify_schema_alignment.py
```

**Expected output:**
```
✓ Connected to Supabase

Test 1: Artifacts table columns
  ✓ All required columns exist: file_content, file_size

Test 2: Analysis snapshots column naming
  ✓ Column 'snapshot_data' exists (not 'result_json')
  ✓ Primary key is 'id' (not 'snapshot_id')

Test 3: Strategy table naming
  ✓ Table 'strategies' exists (not 'strategy_versions')
  ✓ Column 'strategy_data' exists (not 'strategy_json')

Test 4: Strategy patches columns
  ✓ Column 'patch_data' exists (not 'patch_json')
  ✓ Column 'strategy_id' foreign key exists
  ✓ Column 'annotations' exists

Test 5: Step events metadata column
  ✓ Column 'metadata' exists

Test 6: Functional verification
  ✓ Can create project
  ✓ Can create artifact with file_content/file_size
  ✓ Can create snapshot with snapshot_data
  ✓ Can create patch with annotations
  ✓ Can log step event with metadata

✓ ALL TESTS PASSED
```

### Step 3: Test Application

1. **Test Backend Connectivity**
   ```bash
   cd service
   python test_db.py
   ```

2. **Test LLM Workflow**
   ```bash
   cd service
   python test_llm_flow.py test_sample_data.csv
   ```

3. **Test Frontend Build**
   ```bash
   cd web
   npm run build
   ```

4. **Run E2E Tests** (optional)
   ```bash
   cd e2e-tests
   npm test
   ```

## What Changed

### Database Schema Changes

| Table | Old Column | New Column | Change Type |
|-------|------------|------------|-------------|
| `artifacts` | (none) | `file_content` | Added |
| `artifacts` | (none) | `file_size` | Added |
| `analysis_snapshots` | `result_json` | `snapshot_data` | Renamed |
| `analysis_snapshots` | `snapshot_id` | `id` | Renamed |
| `strategy_versions` | (table) | `strategies` | Renamed table |
| `strategies` | `strategy_json` | `strategy_data` | Renamed |
| `strategy_patches` | `patch_json` | `patch_data` | Renamed |
| `strategy_patches` | (none) | `strategy_id` | Added |
| `strategy_patches` | (none) | `annotations` | Added |
| `step_events` | (none) | `metadata` | Added |

### Backend Code Changes

**File:** `service/database.py`

```python
# Added metadata parameter to log_step_event()
async def log_step_event(
    self,
    project_id: str,
    run_id: str,
    step_name: str,
    status: str,
    metadata: Optional[Dict[str, Any]] = None  # NEW
):
    event_data = {
        "event_id": str(uuid.uuid4()),
        "project_id": project_id,
        "run_id": run_id,
        "step_name": step_name,
        "status": status,
        "metadata": self._serialize_json_data(metadata) if metadata else None  # NEW
    }

    self.client.table("step_events").insert(event_data).execute()
```

### Frontend Type Changes

**File:** `web/src/lib/database.types.ts`

- Removed duplicate `strategy_versions` table definition
- Updated `strategy_patches` to include `annotations` field
- Updated `step_events` to include `metadata` field

## Rollback Instructions

If you need to revert the migration:

1. Open Supabase SQL Editor
2. Run the rollback script at the bottom of `001_fix_schema_alignment.sql`
3. Restore original backend/frontend code from git:
   ```bash
   git checkout HEAD -- service/database.py web/src/lib/database.types.ts
   ```

## Troubleshooting

### Migration Fails

**Error:** `column "result_json" already renamed`
- **Solution:** Migration is idempotent. This is safe to ignore.

**Error:** `relation "strategy_versions" does not exist`
- **Solution:** Table already renamed. This is expected after migration.

### Verification Fails

**Error:** `Missing columns: file_content, file_size`
- **Solution:** Re-run the migration SQL. Check Supabase logs for errors.

**Error:** `Connection refused`
- **Solution:** Check `.env` file for correct `SUPABASE_URL` and `SUPABASE_KEY`.

### Application Errors

**Error:** `column "patch_json" does not exist`
- **Solution:** Run the migration. Backend is trying to use old column names.

**Error:** `TypeScript build errors in database.types.ts`
- **Solution:** Regenerate types: `npx supabase gen types typescript --project-id <ID> > web/src/lib/database.types.ts`

## Post-Migration Checklist

- [ ] SQL migration executed successfully in Supabase
- [ ] Verification script passes all tests
- [ ] Backend connectivity test passes (`python test_db.py`)
- [ ] LLM workflow test passes (`python test_llm_flow.py test_sample_data.csv`)
- [ ] Frontend builds without errors (`npm run build`)
- [ ] File upload works (test in UI)
- [ ] HITL workflow works (test patch approval/rejection)
- [ ] Strategy creation works
- [ ] Campaign metrics display correctly

## Support

If you encounter issues:

1. Check Supabase Dashboard → Database → Logs for SQL errors
2. Check backend logs: `tail -f /tmp/adronaut_service.log`
3. Run verification script with debug: `DEBUG=true python verify_schema_alignment.py`
4. Review this migration guide: `docs/migrations/README.md`

## Migration History

| Version | Date | Description |
|---------|------|-------------|
| 001 | 2025-10-08 | Fix schema alignment issues (file_content, snapshot_data, annotations, metadata) |
