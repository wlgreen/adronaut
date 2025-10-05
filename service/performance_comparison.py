#!/usr/bin/env python3
"""
Performance comparison between legacy upload and direct processing
"""

import requests
import json
import time
from pathlib import Path
import statistics

# Service URL
SERVICE_URL = "http://localhost:8000"

def create_test_file():
    """Create a test CSV file for comparison"""
    test_data = """name,email,age,location,revenue,campaign_source,conversion_date,customer_value
John Doe,john@example.com,25,New York,1500,social_media,2024-01-15,high
Jane Smith,jane@example.com,30,California,2200,email_marketing,2024-01-16,high
Bob Johnson,bob@example.com,28,Texas,1800,google_ads,2024-01-17,medium
Alice Brown,alice@example.com,35,Florida,2500,social_media,2024-01-18,high
Mike Wilson,mike@example.com,32,Chicago,1900,referral,2024-01-19,medium
Sarah Davis,sarah@example.com,29,Seattle,2100,email_marketing,2024-01-20,high
Tom Clark,tom@example.com,26,Denver,1600,google_ads,2024-01-21,medium
Lisa Garcia,lisa@example.com,33,Phoenix,2300,social_media,2024-01-22,high
"""

    test_file_path = "/tmp/performance_test_data.csv"
    with open(test_file_path, 'w') as f:
        f.write(test_data)
    return test_file_path

def test_legacy_upload(project_id, file_path, runs=3):
    """Test legacy /upload endpoint performance"""
    times = []

    print(f"🐌 Testing legacy upload method ({runs} runs)...")

    for i in range(runs):
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (f'performance_test_{i}.csv', f, 'text/csv')}
                params = {'project_id': f"{project_id}_legacy_{i}"}

                start_time = time.time()
                response = requests.post(f"{SERVICE_URL}/upload", files=files, params=params)
                end_time = time.time()

                processing_time = end_time - start_time
                times.append(processing_time)

                if response.status_code == 200:
                    print(f"   Run {i+1}: {processing_time:.2f}s ✅")
                else:
                    print(f"   Run {i+1}: {processing_time:.2f}s ❌ (HTTP {response.status_code})")

        except Exception as e:
            print(f"   Run {i+1}: Failed - {e}")

    return times

def test_direct_upload(project_id, file_path, runs=3):
    """Test new /upload-direct endpoint performance"""
    times = []

    print(f"⚡ Testing direct upload method ({runs} runs)...")

    for i in range(runs):
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (f'performance_test_{i}.csv', f, 'text/csv')}
                params = {
                    'project_id': f"{project_id}_direct_{i}",
                    'process_immediately': 'true'
                }

                start_time = time.time()
                response = requests.post(f"{SERVICE_URL}/upload-direct", files=files, params=params)
                end_time = time.time()

                processing_time = end_time - start_time
                times.append(processing_time)

                if response.status_code == 200:
                    result = response.json()
                    print(f"   Run {i+1}: {processing_time:.2f}s ✅ (method: {result.get('method', 'unknown')})")
                else:
                    print(f"   Run {i+1}: {processing_time:.2f}s ❌ (HTTP {response.status_code})")

        except Exception as e:
            print(f"   Run {i+1}: Failed - {e}")

    return times

def calculate_stats(times, label):
    """Calculate and display statistics"""
    if not times:
        print(f"❌ No successful runs for {label}")
        return

    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)

    print(f"\n📊 {label} Performance Statistics:")
    print(f"   Average: {avg_time:.2f}s")
    print(f"   Median:  {median_time:.2f}s")
    print(f"   Min:     {min_time:.2f}s")
    print(f"   Max:     {max_time:.2f}s")

    return avg_time

def main():
    """Run performance comparison"""
    print("🏁 Starting Performance Comparison Test")
    print("=" * 50)

    # Create test file
    test_file_path = create_test_file()
    print(f"📄 Created test file: {test_file_path}")

    project_id = "performance_comparison"
    runs = 3  # Number of test runs per method

    try:
        # Test legacy method
        legacy_times = test_legacy_upload(project_id, test_file_path, runs)
        legacy_avg = calculate_stats(legacy_times, "Legacy Upload")

        print("\n" + "-" * 30)

        # Test direct method
        direct_times = test_direct_upload(project_id, test_file_path, runs)
        direct_avg = calculate_stats(direct_times, "Direct Upload")

        # Calculate improvement
        if legacy_avg and direct_avg:
            improvement = ((legacy_avg - direct_avg) / legacy_avg) * 100
            speedup = legacy_avg / direct_avg

            print("\n" + "=" * 50)
            print("🚀 PERFORMANCE IMPROVEMENT RESULTS")
            print(f"📈 Speed improvement: {improvement:.1f}%")
            print(f"⚡ Speedup factor: {speedup:.1f}x faster")

            if improvement > 0:
                print(f"✅ Direct processing is significantly faster!")
                print(f"💡 Time saved per file: {legacy_avg - direct_avg:.2f} seconds")
            else:
                print(f"⚠️ Direct processing is slower (unexpected)")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    finally:
        # Cleanup
        try:
            Path(test_file_path).unlink()
            print(f"\n🧹 Cleaned up test file")
        except:
            pass

if __name__ == "__main__":
    main()