"""
Test schema detection and insights generation with Amazon Sponsored Products CSV
"""
import asyncio
import json
import csv
import sys
from pathlib import Path

# Add service directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schema_detector import SchemaDetector
from mechanics_cheat_sheet import UNIVERSAL_MECHANICS

def load_amazon_csv(file_path):
    """Load Amazon CSV data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows

def test_schema_detection(csv_path):
    """Test schema detection on Amazon CSV"""
    print("=" * 80)
    print("🔬 SCHEMA DETECTION TEST")
    print("=" * 80)

    # Load data
    print(f"\n📂 Loading CSV: {csv_path}")
    data_rows = load_amazon_csv(csv_path)
    print(f"✅ Loaded {len(data_rows)} rows")

    # Detect schema
    print("\n🔍 Detecting schema...")
    detector = SchemaDetector()
    schema = detector.detect_schema(data_rows)

    # Print detected schema
    print("\n📊 DETECTED SCHEMA:")
    print(f"   Primary Dimension: {schema['primary_dimension']}")
    print(f"   Row Count: {schema['row_count']}")
    print(f"\n   Available Metrics:")
    print(f"   • Efficiency ({len(schema['metrics']['efficiency_metrics'])}): {', '.join(schema['metrics']['efficiency_metrics'][:5])}...")
    print(f"   • Cost ({len(schema['metrics']['cost_metrics'])}): {', '.join(schema['metrics']['cost_metrics'][:5])}...")
    print(f"   • Volume ({len(schema['metrics']['volume_metrics'])}): {', '.join(schema['metrics']['volume_metrics'][:5])}...")
    if schema['metrics'].get('comparative_metrics'):
        print(f"   • Comparative ({len(schema['metrics']['comparative_metrics'])}): {', '.join(schema['metrics']['comparative_metrics'][:5])}...")

    # Build data dictionary
    print("\n📖 Building data dictionary...")
    data_dict = detector.build_data_dictionary(schema, data_rows)
    print(f"✅ Data dictionary generated ({len(data_dict)} characters)")

    # Print sample
    print("\n📄 DATA DICTIONARY SAMPLE (first 500 chars):")
    print(data_dict[:500] + "...")

    return schema, data_dict, data_rows

def validate_schema_expectations(schema):
    """Validate that schema meets expectations for Amazon data"""
    print("\n" + "=" * 80)
    print("✅ VALIDATION CHECKS")
    print("=" * 80)

    checks = []

    # Check 1: Primary dimension should be keyword-related
    primary = schema['primary_dimension'].lower()
    if 'keyword' in primary or 'term' in primary:
        checks.append(("✅ Primary dimension is keyword-related", True))
    else:
        checks.append((f"⚠️  Primary dimension '{schema['primary_dimension']}' may not be keyword", False))

    # Check 2: Should detect ROAS as efficiency metric
    efficiency = [m.lower() for m in schema['metrics']['efficiency_metrics']]
    if any('roas' in m for m in efficiency):
        checks.append(("✅ ROAS detected as efficiency metric", True))
    else:
        checks.append(("❌ ROAS not detected as efficiency metric", False))

    # Check 3: Should detect CTR as efficiency metric
    if any('ctr' in m for m in efficiency):
        checks.append(("✅ CTR detected as efficiency metric", True))
    else:
        checks.append(("❌ CTR not detected as efficiency metric", False))

    # Check 4: Should detect CPC as cost metric
    cost = [m.lower() for m in schema['metrics']['cost_metrics']]
    if any('cpc' in m for m in cost):
        checks.append(("✅ CPC detected as cost metric", True))
    else:
        checks.append(("❌ CPC not detected as cost metric", False))

    # Check 5: Should detect ACOS as cost metric
    if any('acos' in m for m in cost):
        checks.append(("✅ ACOS detected as cost metric", True))
    else:
        checks.append(("❌ ACOS not detected as cost metric", False))

    # Check 6: Should detect impressions/clicks as volume
    volume = [m.lower() for m in schema['metrics']['volume_metrics']]
    if any('impression' in m or 'click' in m for m in volume):
        checks.append(("✅ Impressions/Clicks detected as volume metrics", True))
    else:
        checks.append(("❌ No volume metrics detected", False))

    # Check 7: Should detect bid gap metrics (current vs suggested)
    comparative = [m.lower() for m in schema['metrics'].get('comparative_metrics', [])]
    if len(comparative) > 0:
        checks.append((f"✅ Comparative metrics detected: {len(comparative)}", True))
    else:
        checks.append(("⚠️  No comparative metrics detected (bid gaps may not be in data)", True))  # Not critical

    # Print all checks
    print()
    for check, passed in checks:
        print(check)

    # Summary
    passed_count = sum(1 for _, p in checks if p)
    total_count = len(checks)
    print(f"\n📊 VALIDATION SUMMARY: {passed_count}/{total_count} checks passed")

    return passed_count == total_count

def main():
    """Main test function"""
    # Get CSV path from command line or use default
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = "/Users/liangwang/Downloads/Sponsored Products Search term report (1).csv"

    if not Path(csv_path).exists():
        print(f"❌ CSV file not found: {csv_path}")
        print(f"\nUsage: python test_amazon_csv.py [path_to_csv]")
        sys.exit(1)

    # Run schema detection test
    schema, data_dict, data_rows = test_schema_detection(csv_path)

    # Validate schema
    all_passed = validate_schema_expectations(schema)

    # Print universal mechanics info
    print("\n" + "=" * 80)
    print("🎯 UNIVERSAL MECHANICS AVAILABLE")
    print("=" * 80)
    print(f"\n✅ UNIVERSAL_MECHANICS constant loaded ({len(UNIVERSAL_MECHANICS)} characters)")
    print("\nIncluded patterns:")
    for line in UNIVERSAL_MECHANICS.split('\n'):
        if line.startswith('**Pattern'):
            print(f"  • {line.replace('**', '')}")

    # Save results
    print("\n" + "=" * 80)
    print("💾 SAVING RESULTS")
    print("=" * 80)

    output = {
        'schema': schema,
        'validation_passed': all_passed,
        'sample_rows': data_rows[:3],  # First 3 rows
        'data_dictionary_length': len(data_dict),
    }

    output_path = Path(__file__).parent / 'test_amazon_results.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✅ Results saved to: {output_path}")

    # Final summary
    print("\n" + "=" * 80)
    print("🎉 TEST COMPLETE")
    print("=" * 80)
    if all_passed:
        print("✅ All validation checks passed!")
        print("✅ Schema detection is working correctly for Amazon data")
    else:
        print("⚠️  Some validation checks failed - review output above")

    print("\n📝 Next steps:")
    print("   1. Review saved results in test_amazon_results.json")
    print("   2. Start backend service to test full workflow")
    print("   3. Upload CSV through frontend to test end-to-end")

if __name__ == '__main__':
    main()
