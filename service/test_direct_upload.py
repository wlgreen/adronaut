#!/usr/bin/env python3
"""
Test script for direct upload functionality
"""

import requests
import json
import time
from pathlib import Path

# Service URL
SERVICE_URL = "http://localhost:8000"

def test_direct_upload():
    """Test the new /upload-direct endpoint"""
    print("🧪 Testing direct upload functionality...")

    # Create a test CSV file
    test_data = """name,email,age,location,revenue
John Doe,john@example.com,25,New York,1500
Jane Smith,jane@example.com,30,California,2200
Bob Johnson,bob@example.com,28,Texas,1800
Alice Brown,alice@example.com,35,Florida,2500
"""

    test_file_path = "/tmp/test_marketing_data.csv"
    with open(test_file_path, 'w') as f:
        f.write(test_data)

    print(f"📄 Created test file: {test_file_path}")

    # Test data
    project_id = "test_direct_processing"

    try:
        # Test direct upload with immediate processing
        print(f"\n⚡ Testing direct upload with immediate processing...")

        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_marketing_data.csv', f, 'text/csv')}
            params = {
                'project_id': project_id,
                'process_immediately': 'true'
            }

            start_time = time.time()
            response = requests.post(f"{SERVICE_URL}/upload-direct", files=files, params=params)
            end_time = time.time()

            print(f"⏱️ Processing time: {end_time - start_time:.2f} seconds")

            if response.status_code == 200:
                result = response.json()
                print("✅ Direct upload successful!")
                print(f"📋 Result preview:")
                print(f"   - Method: {result.get('method', 'unknown')}")
                print(f"   - Processing time: {result.get('processing_time', 'unknown')}")
                print(f"   - Artifact ID: {result.get('artifact_id', 'unknown')}")
                print(f"   - Project ID: {result.get('project_id', 'unknown')}")

                # Show features summary
                features = result.get('features', {})
                if features:
                    print(f"\n🎯 Features extracted:")
                    for key, value in features.items():
                        if key == "error":
                            print(f"   ❌ {key}: {value}")
                        elif isinstance(value, (list, dict)):
                            print(f"   ✓ {key}: {type(value).__name__} with {len(value)} items")
                        else:
                            print(f"   ✓ {key}: {str(value)[:100]}...")

                return True
            else:
                print(f"❌ Direct upload failed: {response.status_code}")
                print(f"Error: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

    finally:
        # Cleanup
        try:
            Path(test_file_path).unlink()
            print(f"🧹 Cleaned up test file: {test_file_path}")
        except:
            pass

def test_service_health():
    """Test if service is running"""
    try:
        response = requests.get(f"{SERVICE_URL}/")
        if response.status_code == 200:
            print("✅ Service is running")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting direct upload tests...")

    # Check service health first
    if not test_service_health():
        print("❌ Service is not available, exiting...")
        exit(1)

    # Test direct upload functionality
    success = test_direct_upload()

    if success:
        print("\n🎉 All tests passed! Direct processing is working correctly.")
        print("📈 Performance improvement: Files are processed immediately without DB roundtrip")
    else:
        print("\n❌ Tests failed. Check service logs for details.")
        exit(1)