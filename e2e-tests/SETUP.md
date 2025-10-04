# 🔧 Adronaut E2E Testing Setup Guide

This guide will help you set up and run the comprehensive end-to-end testing suite for the Adronaut marketing automation platform.

## 📋 Prerequisites

### System Requirements
- **Node.js**: Version 18 or higher
- **npm**: Version 8 or higher (comes with Node.js)
- **Git**: For repository access
- **Memory**: At least 4GB RAM for running tests
- **Storage**: 2GB free space for dependencies and test artifacts

### Service Dependencies
- **Frontend Service**: Adronaut web application (Next.js)
- **Backend Service**: Adronaut API service (FastAPI)
- **Database**: Supabase instance with proper schema
- **AI Services**: Gemini API and/or OpenAI API access

## 🚀 Quick Start

### 1. Clone and Navigate
```bash
# If not already in the project
cd /Users/liangwang/adronaut/e2e-tests

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.local .env

# Edit environment variables
nano .env
```

### 3. Verify Setup
```bash
# Run health check
npm run test:smoke

# If successful, run full test suite
npm test
```

## 🔧 Detailed Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Application URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Supabase Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI Service Configuration
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Test Configuration
TEST_ENV=local
DEBUG_LLM=true
TEST_TIMEOUT=120000
UPLOAD_TIMEOUT=30000

# Test Data Configuration
TEST_PROJECT_PREFIX=e2e-test
CLEANUP_TEST_DATA=true
MOCK_AI_RESPONSES=false

# Performance Testing Thresholds
UPLOAD_PERFORMANCE_THRESHOLD_MS=10000
WORKFLOW_PERFORMANCE_THRESHOLD_MS=60000
AI_RESPONSE_THRESHOLD_MS=30000

# Parallel Test Configuration
MAX_PARALLEL_TESTS=3
TEST_RETRY_COUNT=2

# Browser Configuration
HEADLESS=true
SLOW_MO=0
BROWSER_TIMEOUT=30000
```

### Service Prerequisites

#### 1. Frontend Service (Next.js)
```bash
# Start the frontend service
cd ../web
npm install
npm run dev
# Should be running on http://localhost:3000
```

#### 2. Backend Service (FastAPI)
```bash
# Start the backend service
cd ../service
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
# Should be running on http://localhost:8000
```

#### 3. Database Setup (Supabase)
Ensure your Supabase instance has the required tables:
- `projects`
- `artifacts`
- `analysis_snapshots`
- `strategies`
- `strategy_patches`
- `campaigns`
- `metrics`
- `step_events`

## 🧪 Test Execution Options

### Development Testing
```bash
# Run tests with UI (great for debugging)
npm run test:ui

# Run tests in headed mode (see browser)
npm run test:headed

# Run specific test file
npx playwright test tests/01-complete-campaign-flow.spec.ts

# Run tests matching a pattern
npx playwright test --grep "@critical"
```

### Production Testing
```bash
# Run all tests in CI mode
npm test

# Run only critical tests
npm run test:critical

# Run performance tests
npm run test:performance

# Run cross-browser tests
npm run test:cross-browser
```

### Debugging
```bash
# Debug specific test
npx playwright test tests/01-complete-campaign-flow.spec.ts --debug

# Generate trace for failed tests
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip
```

## 📊 Test Categories

### 1. Critical Tests (`@critical`)
Essential user journeys that must pass:
- Complete campaign flow
- File upload and processing
- HITL workflow
- AI service integration

### 2. Smoke Tests (`@smoke`)
Quick validation tests:
- Service health checks
- Basic functionality verification
- Authentication flows

### 3. Performance Tests (`@performance`)
Performance validation:
- Upload speed testing
- Workflow execution timing
- Concurrent user simulation
- Resource usage monitoring

### 4. Error Handling Tests
Failure scenario validation:
- Network failures
- Service unavailability
- Invalid inputs
- Resource exhaustion

## 🔍 Troubleshooting

### Common Issues

#### Tests Fail with "Service Unavailable"
```bash
# Check if services are running
curl http://localhost:3000  # Frontend
curl http://localhost:8000  # Backend

# Start services if needed
cd ../web && npm run dev &
cd ../service && python -m uvicorn main:app --port 8000 &
```

#### Database Connection Errors
```bash
# Verify Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Test database connection
cd ../service && python check_schema.py
```

#### AI Service Timeouts
```bash
# Check AI service keys
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY

# Test with mock responses
export MOCK_AI_RESPONSES=true
npm test
```

#### Upload Failures
```bash
# Check file permissions
ls -la fixtures/

# Verify upload endpoint
curl -X POST http://localhost:8000/upload?project_id=test \
  -F "file=@fixtures/test.csv"
```

### Performance Issues

#### Slow Test Execution
```bash
# Reduce parallel tests
export MAX_PARALLEL_TESTS=1

# Run without retries
npx playwright test --retries=0

# Use headless mode
export HEADLESS=true
```

#### Memory Issues
```bash
# Monitor memory usage
node --max-old-space-size=4096 node_modules/.bin/playwright test

# Clean up test data
npm run cleanup
```

## 📈 CI/CD Setup

### GitHub Actions
The repository includes a comprehensive CI/CD workflow:

1. **Copy the workflow file**:
```bash
mkdir -p ../.github/workflows
cp .github/workflows/e2e-tests.yml ../.github/workflows/
```

2. **Set up GitHub Secrets**:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `SLACK_WEBHOOK_URL` (optional)

3. **Configure Variables**:
- `FRONTEND_URL`
- `BACKEND_URL`

### Local CI Testing
```bash
# Install act (GitHub Actions runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act push -e test-event.json
```

## 🛠️ Development Workflow

### Adding New Tests
1. **Create test file**:
```bash
touch tests/06-new-feature.spec.ts
```

2. **Use test template**:
```typescript
import { test, expect } from '@playwright/test';
import { WorkspacePage } from '../utils/page-objects';
import { TestDataManager } from '../utils/test-data-manager';

test.describe('New Feature @critical', () => {
  let workspacePage: WorkspacePage;
  let testDataManager: TestDataManager;

  test.beforeEach(async ({ page }) => {
    workspacePage = new WorkspacePage(page);
    testDataManager = new TestDataManager();
  });

  test('should validate new feature', async ({ page }) => {
    // Test implementation
  });
});
```

### Updating Page Objects
```typescript
// Add new page object method
export class WorkspacePage {
  async newFeatureAction() {
    await this.page.locator('[data-testid="new-feature"]').click();
  }
}
```

### Performance Baseline Updates
```bash
# Update performance baselines
node scripts/performance-regression-check.js test-results/results.json

# View performance trends
cat performance-trends.json
```

## 📊 Monitoring & Reporting

### Test Results
```bash
# View HTML report
npm run test:report

# Generate custom report
node scripts/generate-test-report.js test-artifacts/

# Check performance regressions
node scripts/performance-regression-check.js test-results/results.json
```

### Metrics Dashboard
Test results are automatically published to:
- GitHub Pages (HTML reports)
- PR comments (Markdown summaries)
- Slack notifications (failures)

## 🔐 Security Considerations

### Test Data Security
- Use test-specific API keys
- Don't commit real credentials
- Clean up test data automatically
- Isolate test environments

### Access Control
```bash
# Set up test-only Supabase project
# Use row-level security (RLS)
# Implement test data isolation
```

## 📚 Additional Resources

### Documentation
- [Playwright Documentation](https://playwright.dev/)
- [Testing Best Practices](./docs/best-practices.md)
- [Performance Testing Guide](./docs/performance-testing.md)
- [Troubleshooting Guide](./docs/troubleshooting.md)

### Support
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Team Slack for urgent issues

## ✅ Validation Checklist

Before running tests, ensure:
- [ ] Node.js 18+ installed
- [ ] Frontend service running on port 3000
- [ ] Backend service running on port 8000
- [ ] Supabase database accessible
- [ ] Environment variables configured
- [ ] Test dependencies installed
- [ ] Playwright browsers installed

Ready to test! Run `npm test` to get started. 🚀