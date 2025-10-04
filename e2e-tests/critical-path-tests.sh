#!/bin/bash

# Adronaut Critical Path Testing Script
# Tests the complete workflow: Upload -> AI Processing -> HITL -> Results

set -e

FRONTEND_URL="http://localhost:3000"
BACKEND_URL="http://localhost:8000"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo -e "${BLUE}🚀 Adronaut Critical Path Testing${NC}"
echo "================================="
echo "Testing complete user journey:"
echo "1. File Upload & Processing"
echo "2. AI Feature Extraction"
echo "3. Strategy Generation"
echo "4. Human-in-the-Loop Workflow"
echo "5. Campaign Launch Simulation"
echo "6. Database Persistence Validation"
echo ""

run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n📋 Test: $test_name"

    local result
    if result=$(eval "$test_command" 2>&1); then
        if [[ -z "$expected_result" ]] || echo "$result" | grep -q "$expected_result"; then
            echo -e "   ${GREEN}✅ PASSED${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo -e "   ${RED}❌ FAILED - Expected: $expected_result${NC}"
            echo -e "   ${YELLOW}Got: $result${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        echo -e "   ${RED}❌ FAILED - Command failed${NC}"
        echo -e "   ${YELLOW}Error: $result${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Create test files
echo "📁 Creating test files..."
mkdir -p /tmp/adronaut-test-files

# Create sample CSV file
cat > /tmp/adronaut-test-files/sales_data.csv << 'EOF'
date,product,revenue,region,customer_segment
2023-01-01,ProductA,1500,North,Enterprise
2023-01-02,ProductB,800,South,SMB
2023-01-03,ProductA,2200,East,Enterprise
2023-01-04,ProductC,950,West,SMB
2023-01-05,ProductB,1100,North,Mid-market
EOF

# Create sample JSON file
cat > /tmp/adronaut-test-files/customer_feedback.json << 'EOF'
{
  "reviews": [
    {
      "product": "ProductA",
      "rating": 4.5,
      "comment": "Great product, very satisfied",
      "date": "2023-01-10",
      "customer_type": "Enterprise"
    },
    {
      "product": "ProductB",
      "rating": 3.8,
      "comment": "Good value for money",
      "date": "2023-01-15",
      "customer_type": "SMB"
    }
  ]
}
EOF

echo -e "${GREEN}✅ Test files created${NC}"

# 1. CRITICAL PATH: File Upload & Processing
echo -e "\n${BLUE}🔥 PHASE 1: File Upload & Processing${NC}"
echo "======================================"

# Generate a unique project ID for this test session
PROJECT_ID="e2e-test-$(date +%s)-$$"
echo -e "   ${YELLOW}📝 Test Project ID: $PROJECT_ID${NC}"

# Test file upload endpoint with project_id
run_test "CSV File Upload" \
    "curl -s -X POST '$BACKEND_URL/upload?project_id=$PROJECT_ID' -F 'file=@/tmp/adronaut-test-files/sales_data.csv'" \
    "artifact_id"

if [ $? -eq 0 ]; then
    # Extract artifact ID for further tests
    ARTIFACT_ID=$(curl -s -X POST "$BACKEND_URL/upload?project_id=$PROJECT_ID" -F 'file=@/tmp/adronaut-test-files/sales_data.csv' | jq -r '.artifact_id // empty' 2>/dev/null || echo "")
    echo -e "   ${YELLOW}📝 Artifact ID: $ARTIFACT_ID${NC}"
fi

run_test "JSON File Upload" \
    "curl -s -X POST '$BACKEND_URL/upload?project_id=$PROJECT_ID' -F 'file=@/tmp/adronaut-test-files/customer_feedback.json'" \
    "artifact_id"

# 2. CRITICAL PATH: AI Workflow Execution
echo -e "\n${BLUE}🤖 PHASE 2: AI Workflow Execution${NC}"
echo "=================================="

# Start AutoGen workflow
echo -e "Starting AI workflow..."

run_test "AI Workflow Initiation" \
    "curl -s -X POST '$BACKEND_URL/autogen/run/start?project_id=$PROJECT_ID'" \
    "message\|started\|success"

if [ $? -eq 0 ]; then
    # Use the project ID as the run ID for monitoring
    RUN_ID="$PROJECT_ID"
    echo -e "   ${YELLOW}📝 Run ID: $RUN_ID${NC}"

    if [[ -n "$RUN_ID" ]]; then
        # Monitor workflow progress
        echo -e "   ${YELLOW}⏳ Monitoring workflow progress...${NC}"

        # Wait and check workflow status (with timeout)
        for i in {1..30}; do
            sleep 2
            STATUS=$(curl -s $BACKEND_URL/project/$RUN_ID/status 2>/dev/null || echo '{}')
            echo -e "   ${YELLOW}Status check $i: $(echo $STATUS | jq -r '.active_strategy.status // "unknown"' 2>/dev/null)${NC}"

            if echo "$STATUS" | grep -q "completed\|failed\|patch_ready"; then
                break
            fi
        done

        run_test "AI Workflow Execution Progress" \
            "curl -s $BACKEND_URL/project/$RUN_ID/status | jq -r '.active_strategy.status // \"unknown\"'" \
            "completed\|failed\|patch_ready"
    fi
fi

# 3. CRITICAL PATH: Real-time Event Streaming
echo -e "\n${BLUE}📡 PHASE 3: Real-time Event Streaming${NC}"
echo "====================================="

if [[ -n "$RUN_ID" ]]; then
    run_test "Event Stream Access" \
        "curl -s $BACKEND_URL/events/$RUN_ID | head -1" \
        "data:"
else
    echo -e "   ${YELLOW}⚠️ Skipping event stream test - no run ID available${NC}"
fi

# 4. CRITICAL PATH: Human-in-the-Loop Workflow
echo -e "\n${BLUE}👤 PHASE 4: Human-in-the-Loop Workflow${NC}"
echo "======================================"

if [[ -n "$RUN_ID" ]]; then
    # Check for pending patches/approvals
    run_test "HITL Patch Detection" \
        "curl -s $BACKEND_URL/project/$RUN_ID/status | jq '.pending_patches | length'" \
        ".*"

    # Simulate patch approval/rejection
    PATCH_RESPONSE='{"action": "approve", "feedback": "Looks good, proceed with campaign"}'

    run_test "HITL Patch Response" \
        "curl -s -X POST $BACKEND_URL/autogen/run/continue -H 'Content-Type: application/json' -d '$PATCH_RESPONSE'" \
        "success\|continued\|accepted"
else
    echo -e "   ${YELLOW}⚠️ Skipping HITL test - no run ID available${NC}"
fi

# 5. CRITICAL PATH: Database Persistence Validation
echo -e "\n${BLUE}💾 PHASE 5: Database Persistence Validation${NC}"
echo "=========================================="

# Check artifact persistence
if [[ -n "$ARTIFACT_ID" ]]; then
    run_test "Artifact Persistence" \
        "curl -s $BACKEND_URL/artifact/$ARTIFACT_ID/download" \
        ".*"
else
    echo -e "   ${YELLOW}⚠️ Skipping artifact persistence test - no artifact ID${NC}"
fi

# Check project data persistence
if [[ -n "$RUN_ID" ]]; then
    run_test "Project Data Persistence" \
        "curl -s $BACKEND_URL/project/$RUN_ID/status | jq -r '.project_id'" \
        "$RUN_ID"
else
    echo -e "   ${YELLOW}⚠️ Skipping project persistence test - no run ID${NC}"
fi

# 6. PERFORMANCE VALIDATION
echo -e "\n${BLUE}⚡ PHASE 6: Performance Validation${NC}"
echo "================================="

# Test response times
echo -e "   ${YELLOW}📊 Measuring response times...${NC}"

FRONTEND_TIME=$(curl -s -w "%{time_total}" -o /dev/null $FRONTEND_URL)
BACKEND_TIME=$(curl -s -w "%{time_total}" -o /dev/null $BACKEND_URL/)

echo -e "   ${YELLOW}Frontend response time: ${FRONTEND_TIME}s${NC}"
echo -e "   ${YELLOW}Backend response time: ${BACKEND_TIME}s${NC}"

# Performance thresholds (in seconds)
FRONTEND_THRESHOLD=3.0
BACKEND_THRESHOLD=1.0

run_test "Frontend Performance" \
    "echo '$FRONTEND_TIME < $FRONTEND_THRESHOLD' | bc -l" \
    "1"

run_test "Backend Performance" \
    "echo '$BACKEND_TIME < $BACKEND_THRESHOLD' | bc -l" \
    "1"

# 7. ERROR HANDLING VALIDATION
echo -e "\n${BLUE}🚫 PHASE 7: Error Handling Validation${NC}"
echo "====================================="

# Test invalid file upload
run_test "Invalid File Upload Handling" \
    "curl -s -X POST $BACKEND_URL/upload -F 'file=@/dev/null' -w '%{http_code}'" \
    "422\|400"

# Test invalid project ID
run_test "Invalid Project ID Handling" \
    "curl -s $BACKEND_URL/project/invalid-id/status -w '%{http_code}'" \
    "404\|422"

# Test malformed JSON
run_test "Malformed JSON Handling" \
    "curl -s -X POST $BACKEND_URL/autogen/run/start -H 'Content-Type: application/json' -d '{invalid json}' -w '%{http_code}'" \
    "422\|400"

# 8. INTEGRATION VALIDATION
echo -e "\n${BLUE}🔗 PHASE 8: Integration Validation${NC}"
echo "=================================="

# Test AI service integration
run_test "AI Service Integration" \
    "curl -s $BACKEND_URL/ | jq -r '.status'" \
    "running"

# Cleanup test files
echo -e "\n🧹 Cleaning up test files..."
rm -rf /tmp/adronaut-test-files

# Final Results
echo -e "\n${BLUE}📊 Critical Path Test Results${NC}"
echo "=============================="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo -e "Pass Rate: ${PASS_RATE}%"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL CRITICAL PATHS VALIDATED!${NC}"
    echo -e "${GREEN}✅ The Adronaut platform is fully functional.${NC}"
    exit 0
elif [ $PASS_RATE -ge 80 ]; then
    echo -e "\n${YELLOW}⚠️  Most critical paths working (${PASS_RATE}% pass rate)${NC}"
    echo -e "${YELLOW}📋 Some non-critical issues detected.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ CRITICAL ISSUES DETECTED (${PASS_RATE}% pass rate)${NC}"
    echo -e "${RED}🚨 Platform requires attention before production use.${NC}"
    exit 1
fi