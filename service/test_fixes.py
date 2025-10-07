#!/usr/bin/env python3

"""
Quick test to verify the JSON parsing and database fixes
"""

import asyncio
import json
import os
from gemini_orchestrator import GeminiOrchestrator
from database import Database

def test_json_parsing():
    """Test the JSON parsing fix"""
    print("🧪 Testing JSON parsing fix...")

    orchestrator = GeminiOrchestrator()

    # Test the exact format that Gemini returns (with markdown)
    gemini_response = '''```json
{
  "target_audience": {
    "description": "Tech-savvy consumers aged 25-45"
  },
  "brand_positioning": "Innovation leader in smart home technology",
  "channels": ["digital", "social media"],
  "messaging": ["cutting-edge tech", "user-friendly"],
  "objectives": ["increase market share", "build brand awareness"],
  "budget_insights": {
    "total_budget": 500000,
    "allocation": {"digital": 60, "traditional": 40}
  },
  "metrics": {
    "primary": "conversion_rate",
    "secondary": ["engagement", "reach"]
  },
  "competitive_insights": ["strong social presence needed"],
  "recommendations": ["focus on mobile experience", "leverage influencers"]
}
```'''

    extracted_json = orchestrator._extract_json_from_response(gemini_response)

    if extracted_json:
        try:
            parsed = json.loads(extracted_json)
            print("✅ JSON parsing fix successful!")
            print(f"   - Extracted {len(extracted_json)} characters")
            print(f"   - Parsed {len(parsed)} fields")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing still failing: {e}")
            return False
    else:
        print("❌ No JSON extracted from response")
        return False

async def test_database_upsert():
    """Test the database upsert fix"""
    print("\n🧪 Testing database upsert fix...")

    # Use test environment
    db = Database(use_test_mode=True)

    project_id = "test-upsert-project"
    test_data_1 = {"test": "data1", "version": 1}
    test_data_2 = {"test": "data2", "version": 2}

    try:
        # First insert
        snapshot_id_1 = await db.create_snapshot(project_id, test_data_1)
        print(f"✅ First snapshot created: {snapshot_id_1}")

        # Second insert (should upsert, not conflict)
        snapshot_id_2 = await db.create_snapshot(project_id, test_data_2)
        print(f"✅ Second snapshot created/updated: {snapshot_id_2}")

        # Verify the latest data
        latest = await db.get_latest_snapshot(project_id)
        if latest and latest.get("snapshot_data", {}).get("version") == 2:
            print("✅ Database upsert fix successful!")
            return True
        else:
            print("❌ Latest snapshot doesn't have updated data")
            return False

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing recent fixes...\n")

    json_success = test_json_parsing()
    db_success = await test_database_upsert()

    print(f"\n📊 Test Results:")
    print(f"   JSON Parsing: {'✅ PASS' if json_success else '❌ FAIL'}")
    print(f"   Database Upsert: {'✅ PASS' if db_success else '❌ FAIL'}")

    if json_success and db_success:
        print(f"\n🎉 All fixes working correctly!")
        return True
    else:
        print(f"\n⚠️ Some fixes need more work")
        return False

if __name__ == "__main__":
    asyncio.run(main())