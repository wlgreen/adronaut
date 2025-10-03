#!/usr/bin/env python3

import os
import sys
import asyncio
import json
import uuid
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

async def test_full_database_workflow():
    """Test complete database workflow to identify all issues"""

    print("🔍 COMPREHENSIVE DATABASE TEST")
    print("=" * 50)

    # Set environment variables
    os.environ["SUPABASE_URL"] = "https://pszhibxfxefhguzqziqp.supabase.co"
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBzemhpYnhmeGVmaGd1enF6aXFwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkxNzg1ODQsImV4cCI6MjA3NDc1NDU4NH0.bRQcjox8ZhyN0AMGB5njAAP2vLudzsc_3OwWOsg_5Ss"

    try:
        from database import Database
        from file_processor import FileProcessor
        print("✅ Successfully imported Database and FileProcessor")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return

    # Test 1: Database connection
    print("\n📡 Test 1: Database Connection")
    print("-" * 30)

    db = Database()
    await db.connect()

    if db.client:
        print("✅ Database client connected successfully")
    else:
        print("❌ Database client failed to connect")
        return

    # Test 2: Project operations
    print("\n📁 Test 2: Project Operations")
    print("-" * 30)

    try:
        project_name = f"Test Project {uuid.uuid4().hex[:8]}"
        project_id = await db.get_or_create_project(project_name)
        print(f"✅ Project created/retrieved: {project_id}")

        # Verify it's a valid UUID
        uuid.UUID(project_id)
        print("✅ Project ID is valid UUID format")

    except Exception as e:
        print(f"❌ Project operation failed: {e}")
        return

    # Test 3: Artifact creation with all fields
    print("\n📦 Test 3: Artifact Creation")
    print("-" * 30)

    try:
        test_content = "This is test file content for artifact storage"
        artifact_id = await db.create_artifact(
            project_id=project_id,
            filename="test_file.txt",
            mime="text/plain",
            storage_url="db://test/file.txt",
            file_content=test_content,
            file_size=len(test_content),
            summary_json={
                "test": True,
                "file_type": "text",
                "content_preview": test_content[:20]
            }
        )
        print(f"✅ Artifact created: {artifact_id}")

        # Verify it's a valid UUID
        uuid.UUID(artifact_id)
        print("✅ Artifact ID is valid UUID format")

    except Exception as e:
        print(f"❌ Artifact creation failed: {e}")
        return

    # Test 4: Artifact retrieval
    print("\n📋 Test 4: Artifact Retrieval")
    print("-" * 30)

    try:
        artifacts = await db.get_artifacts(project_id)
        print(f"✅ Retrieved {len(artifacts)} artifacts")

        if artifacts:
            artifact = artifacts[0]
            print("📊 Artifact structure:")
            for key, value in artifact.items():
                if key == "file_content":
                    print(f"   {key}: {str(value)[:50]}...")
                else:
                    print(f"   {key}: {value}")

        # Test specific artifact retrieval
        specific_artifact = await db.get_artifact_content(artifact_id)
        if specific_artifact:
            print("✅ Specific artifact retrieval successful")
        else:
            print("❌ Specific artifact retrieval failed")

    except Exception as e:
        print(f"❌ Artifact retrieval failed: {e}")

    # Test 5: Snapshot creation
    print("\n📸 Test 5: Snapshot Creation")
    print("-" * 30)

    try:
        test_snapshot = {
            "features": {
                "target_audience": "Test audience",
                "channels": ["email", "social"]
            },
            "analysis_timestamp": "2025-10-03T15:00:00Z"
        }

        snapshot_id = await db.create_snapshot(project_id, test_snapshot)
        print(f"✅ Snapshot created: {snapshot_id}")

        # Test snapshot retrieval
        latest_snapshot = await db.get_latest_snapshot(project_id)
        if latest_snapshot:
            print("✅ Latest snapshot retrieval successful")
        else:
            print("❌ Latest snapshot retrieval failed")

    except Exception as e:
        print(f"❌ Snapshot operations failed: {e}")

    # Test 6: Strategy operations
    print("\n🎯 Test 6: Strategy Operations")
    print("-" * 30)

    try:
        test_strategy = {
            "type": "marketing_strategy",
            "target_audience": "Tech professionals",
            "channels": ["linkedin", "email"],
            "budget": 10000
        }

        strategy_id = await db.create_strategy_version(project_id, test_strategy)
        print(f"✅ Strategy version created: {strategy_id}")

        # Set as active strategy
        await db.set_active_strategy(project_id, strategy_id)
        print("✅ Strategy set as active")

        # Retrieve active strategy
        active_strategy = await db.get_active_strategy(project_id)
        if active_strategy:
            print("✅ Active strategy retrieval successful")
        else:
            print("❌ Active strategy retrieval failed")

    except Exception as e:
        print(f"❌ Strategy operations failed: {e}")

    # Test 7: Patch operations
    print("\n🔧 Test 7: Patch Operations")
    print("-" * 30)

    try:
        test_patch = {
            "type": "audience_update",
            "changes": {
                "target_audience": "Expanded to include designers"
            }
        }

        patch_id = await db.create_patch(
            project_id=project_id,
            source="insights",
            patch_json=test_patch,
            justification="Test patch for comprehensive testing",
            strategy_id=strategy_id
        )
        print(f"✅ Patch created: {patch_id}")

        # Test patch retrieval
        patch = await db.get_patch(patch_id)
        if patch:
            print("✅ Patch retrieval successful")
        else:
            print("❌ Patch retrieval failed")

        # Test pending patches
        pending_patches = await db.get_pending_patches(project_id)
        print(f"✅ Retrieved {len(pending_patches)} pending patches")

        # Update patch status
        await db.update_patch_status(patch_id, "approved")
        print("✅ Patch status updated")

    except Exception as e:
        print(f"❌ Patch operations failed: {e}")

    # Test 8: File processor integration
    print("\n📁 Test 8: File Processor Integration")
    print("-" * 30)

    try:
        # Create a mock file upload
        class MockUploadFile:
            def __init__(self, filename, content, content_type):
                self.filename = filename
                self.content = content.encode() if isinstance(content, str) else content
                self.content_type = content_type

            async def read(self):
                return self.content

        mock_file = MockUploadFile(
            "test_document.txt",
            "This is a comprehensive test document with marketing content",
            "text/plain"
        )

        file_processor = FileProcessor()
        result = await file_processor.process_file(mock_file, project_id)

        print(f"✅ File processing successful")
        print(f"   Artifact ID: {result['artifact_id']}")
        print(f"   Storage URL: {result['storage_url']}")
        print(f"   File size: {result['file_size']} bytes")
        print(f"   Content length: {len(result['file_content'])} chars")

        # Test storing the processed file
        final_artifact_id = await db.create_artifact(
            project_id=project_id,
            filename=mock_file.filename,
            mime=mock_file.content_type,
            storage_url=result["storage_url"],
            file_content=result.get("file_content"),
            file_size=result.get("file_size"),
            summary_json=result.get("summary", {})
        )
        print(f"✅ Processed file stored as artifact: {final_artifact_id}")

    except Exception as e:
        print(f"❌ File processor integration failed: {e}")

    # Test 9: Event logging
    print("\n📝 Test 9: Event Logging")
    print("-" * 30)

    try:
        run_id = str(uuid.uuid4())

        await db.log_step_event(project_id, run_id, "TEST_STEP", "started")
        await db.log_step_event(project_id, run_id, "TEST_STEP", "completed")
        print("✅ Step events logged")

        events = await db.get_workflow_events(project_id)
        print(f"✅ Retrieved {len(events)} workflow events")

    except Exception as e:
        print(f"❌ Event logging failed: {e}")

    # Final verification
    print("\n🔍 Final Verification")
    print("-" * 30)

    try:
        # Get all artifacts to verify everything was stored
        final_artifacts = await db.get_artifacts(project_id)
        print(f"✅ Final artifact count: {len(final_artifacts)}")

        for i, artifact in enumerate(final_artifacts):
            print(f"   Artifact {i+1}: {artifact['filename']} ({artifact['file_size']} bytes)")

    except Exception as e:
        print(f"❌ Final verification failed: {e}")

    # Cleanup
    await db.disconnect()
    print("\n✅ Database test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_full_database_workflow())