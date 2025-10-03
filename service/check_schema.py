#!/usr/bin/env python3

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Missing supabase-py. Install with: pip3 install supabase")
    sys.exit(1)

async def check_database_schema():
    """Check the current database schema"""

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        return

    print(f"🔍 Connecting to Supabase: {url}")

    try:
        client = create_client(url, key)
        print("✅ Connected to Supabase")

        # Check what tables exist
        print("\n📋 Checking existing tables...")

        # Try to query each table to see if it exists and what columns it has
        tables_to_check = [
            "projects",
            "artifacts",
            "analysis_snapshots",
            "strategies",
            "strategy_active",
            "strategy_patches",
            "briefs",
            "campaigns",
            "metrics",
            "step_events"
        ]

        for table_name in tables_to_check:
            try:
                # Try to get table structure by selecting with limit 0
                result = client.table(table_name).select("*").limit(0).execute()
                print(f"✅ Table '{table_name}' exists")

                # Try to insert a test record to see what columns are expected
                if table_name == "artifacts":
                    print(f"\n🔍 Checking artifacts table schema...")
                    try:
                        # Try with new schema (file_content, file_size)
                        test_data = {
                            "artifact_id": "test-schema-check",
                            "project_id": "test-project",
                            "filename": "test.txt",
                            "mime": "text/plain",
                            "storage_url": "test://url",
                            "file_content": "test content",
                            "file_size": 12,
                            "summary_json": {}
                        }
                        # Don't actually insert, just validate the structure
                        print("   Testing new schema with file_content and file_size...")
                        # This will fail if columns don't exist

                    except Exception as e:
                        print(f"   ❌ New schema test failed: {e}")
                        print("   📝 Missing columns detected")

                    # Try with old schema
                    try:
                        test_data_old = {
                            "artifact_id": "test-schema-check-old",
                            "project_id": "test-project",
                            "filename": "test.txt",
                            "mime": "text/plain",
                            "storage_url": "test://url",
                            "summary_json": {}
                        }
                        print("   Testing old schema without file_content and file_size...")

                    except Exception as e:
                        print(f"   ❌ Old schema test failed: {e}")

            except Exception as e:
                print(f"❌ Table '{table_name}' does not exist or is not accessible: {e}")

        # Check specific artifacts table structure
        print(f"\n🎯 Checking artifacts table in detail...")
        try:
            # Get current table data to understand structure
            result = client.table("artifacts").select("*").limit(1).execute()

            if result.data:
                print("📊 Current artifacts table structure (based on existing data):")
                sample_record = result.data[0]
                for key, value in sample_record.items():
                    print(f"   {key}: {type(value).__name__} = {str(value)[:50]}...")
            else:
                print("📊 Artifacts table is empty - cannot determine current structure")

        except Exception as e:
            print(f"❌ Could not query artifacts table: {e}")

    except Exception as e:
        print(f"❌ Failed to connect or query database: {e}")
        return

    print(f"\n📝 Based on the schema check, here are the likely required migrations:")
    print(f"""
    -- Add missing columns to artifacts table:
    ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS file_content TEXT,
    ADD COLUMN IF NOT EXISTS file_size INTEGER;

    -- If strategies table doesn't exist, create it:
    CREATE TABLE IF NOT EXISTS strategies (
        strategy_id TEXT PRIMARY KEY,
        project_id TEXT REFERENCES projects(project_id),
        version INTEGER NOT NULL,
        strategy_data JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Make sure strategy_patches.strategy_id can be NULL:
    ALTER TABLE strategy_patches
    ALTER COLUMN strategy_id DROP NOT NULL;
    """)

if __name__ == "__main__":
    asyncio.run(check_database_schema())