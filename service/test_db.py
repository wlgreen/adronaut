#!/usr/bin/env python3

import os
import sys
import asyncio
from database import Database

async def test_database():
    """Test database connectivity and artifact creation"""
    print("Testing database connectivity...")

    db = Database()

    # Test connection
    await db.connect()

    if not db.client:
        print("❌ Database client not initialized - missing credentials?")
        print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
        print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY', 'NOT SET')}")
        return

    print("✅ Database client initialized")

    # Test project creation
    print("Testing project creation...")
    project_id = await db.get_or_create_project("Test Project")
    print(f"Project ID: {project_id}")

    # Test artifact creation
    print("Testing artifact creation...")
    try:
        artifact_id = await db.create_artifact(
            project_id=project_id,
            filename="test.txt",
            mime="text/plain",
            storage_url="db://test/file.txt",
            file_content="This is test content",
            file_size=20,
            summary_json={"test": True}
        )
        print(f"✅ Artifact created: {artifact_id}")

        # Test artifact retrieval
        artifacts = await db.get_artifacts(project_id)
        print(f"✅ Retrieved {len(artifacts)} artifacts")

    except Exception as e:
        print(f"❌ Artifact creation failed: {e}")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_database())