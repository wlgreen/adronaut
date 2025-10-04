# 🚀 Adronaut E2E Testing Suite

Comprehensive end-to-end testing for the Adronaut marketing automation platform using Playwright.

## 📋 Overview

This test suite validates the complete user journey from file upload through AI-powered marketing campaign creation and execution. It includes performance testing, error handling validation, and cross-browser compatibility testing.

## 🎯 Test Coverage

### Critical User Flows
- ✅ Complete marketing campaign creation (upload → analysis → HITL → campaign)
- ✅ Human-in-the-loop workflow (approve/reject/edit patches)
- ✅ File upload and processing (multiple file types and sizes)
- ✅ Real-time event streaming (SSE)
- ✅ AI service integration (Gemini + OpenAI fallback)

### Error Scenarios
- ✅ Network failures and service unavailability
- ✅ Database connection issues
- ✅ AI service timeouts and malformed responses
- ✅ File corruption and invalid uploads
- ✅ Rate limiting and resource exhaustion

### Performance Testing
- ✅ Upload performance thresholds
- ✅ AI workflow execution times
- ✅ Concurrent user load testing
- ✅ Database query optimization
- ✅ Real-time event delivery latency

## 🛠️ Setup & Installation

### Prerequisites
- Node.js 18+
- npm or yarn
- Access to Adronaut frontend and backend services

### Installation
```bash
cd e2e-tests
npm install
npx playwright install
```

### Environment Configuration
Copy the appropriate environment file:
```bash
# For local testing
cp .env.local .env

# For staging testing
cp .env.staging .env
```

Update the environment variables:
```env
# Application URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Database credentials
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key

# AI service keys
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
```

## 🚀 Running Tests

### Quick Start
```bash
# Run all critical tests
npm test

# Run with UI for debugging
npm run test:ui

# Run in headed mode
npm run test:headed
```

### Test Categories
```bash
# Critical path tests only
npm run test:critical

# Smoke tests (quick validation)
npm run test:smoke

# Performance tests
npm run test:performance

# Cross-browser testing
npm run test:cross-browser
```

### Debug Mode
```bash
# Run tests in debug mode
npm run test:debug

# View test reports
npm run test:report
```

## 📊 Test Structure

```
e2e-tests/
├── tests/
│   ├── 01-complete-campaign-flow.spec.ts    # Main user journey
│   ├── 02-hitl-workflow.spec.ts             # Human-in-the-loop testing
│   ├── 03-file-upload-processing.spec.ts    # File handling
│   ├── 04-error-handling.spec.ts            # Error scenarios
│   └── performance/
│       └── 05-performance-testing.spec.ts   # Performance validation
├── utils/
│   ├── test-data-manager.ts                 # Test data utilities
│   ├── page-objects.ts                      # Page object models
│   └── test-helpers.ts                      # Common test functions
├── fixtures/                                # Test data files
├── scripts/                                 # CI/CD utilities
└── playwright.config.ts                     # Test configuration
```

## 🔧 Configuration

### Playwright Configuration
The test suite is configured to run across multiple browsers and environments:

- **Browsers**: Chromium, Firefox, WebKit
- **Environments**: Local, Staging, Production
- **Parallelization**: Configurable based on environment
- **Retries**: Automatic retry on CI for flaky tests
- **Reporting**: HTML, JSON, JUnit formats

### Performance Thresholds
```javascript
{
  uploadTime: 10000,      // 10 seconds max upload time
  workflowTime: 60000,    // 60 seconds max workflow completion
  apiResponseTime: 2000,  // 2 seconds max API response
  pageLoadTime: 5000      // 5 seconds max page load
}
```

## 📈 CI/CD Integration

### GitHub Actions
The test suite includes a comprehensive GitHub Actions workflow:

```yaml
# Runs on:
- Push to main/develop branches
- Pull requests
- Nightly schedule (2 AM UTC)
- Manual dispatch

# Test Jobs:
- Critical path tests (all browsers)
- Smoke tests (Chromium only)
- Performance tests (scheduled)
- Cross-browser compatibility
- Security and accessibility tests
```

### Test Reports
Automated reports are generated and published:
- HTML report with visual results
- Markdown summary for PR comments
- JSON data for trend analysis
- Performance regression detection

## 🎭 Page Object Pattern

Tests use the Page Object pattern for maintainability:

```typescript
// Example usage
const workspacePage = new WorkspacePage(page);
await workspacePage.goto();
await workspacePage.uploadFile('test.csv');
await workspacePage.startAnalysis();
await workspacePage.waitForAnalysisComplete();
```

Available page objects:
- `WorkspacePage` - File upload and analysis
- `StrategyPage` - HITL workflow
- `ResultsPage` - Campaign results
- `NavigationHelper` - Site navigation
- `APIHelper` - Backend API interactions

## 🧪 Test Data Management

### Automatic Test Data
The `TestDataManager` class handles:
- Dynamic test project creation
- Realistic test file generation
- Database cleanup after tests
- Performance threshold management

### Test Isolation
Each test:
- Gets a unique project ID
- Uses isolated test data
- Cleans up after execution
- Doesn't interfere with other tests

## 📊 Performance Monitoring

### Regression Detection
The suite automatically detects performance regressions:
- Compares against baseline metrics
- Alerts on >20% performance degradation
- Updates baselines automatically
- Generates trend analysis

### Performance Reports
Detailed performance metrics include:
- File upload speeds by size
- AI workflow execution times
- Database query performance
- Real-time event latency
- Concurrent user handling

## 🐛 Debugging

### Test Debugging
```bash
# Run specific test in debug mode
npx playwright test tests/01-complete-campaign-flow.spec.ts --debug

# Run with trace collection
npx playwright test --trace on

# Generate trace viewer
npx playwright show-trace trace.zip
```

### Common Issues
1. **Service Unavailable**: Ensure frontend/backend are running
2. **Database Errors**: Check Supabase credentials
3. **AI Service Timeout**: Verify API keys and rate limits
4. **Upload Failures**: Check file permissions and size limits

## 📝 Test Development

### Adding New Tests
1. Create test file in appropriate directory
2. Use existing page objects and utilities
3. Follow naming convention: `NN-test-name.spec.ts`
4. Add appropriate test tags: `@critical`, `@smoke`, etc.

### Test Tags
- `@critical` - Must pass for deployment
- `@smoke` - Quick validation tests
- `@performance` - Performance-specific tests
- `@error-handling` - Error scenario tests

### Best Practices
- Use descriptive test names
- Implement proper cleanup
- Use appropriate timeouts
- Add meaningful assertions
- Include performance measurements

## 🔒 Security Testing

The suite includes security validations:
- Input sanitization testing
- XSS prevention validation
- SQL injection attempt detection
- File upload security checks
- Authorization testing

## ♿ Accessibility Testing

Accessibility checks include:
- axe-core integration
- Keyboard navigation testing
- Screen reader compatibility
- Color contrast validation
- ARIA attribute verification

## 📞 Support

### Getting Help
- Check the [troubleshooting guide](./docs/troubleshooting.md)
- Review test logs and screenshots
- Use the GitHub Discussions for questions
- Contact the QA team for complex issues

### Contributing
1. Follow the existing test patterns
2. Add appropriate documentation
3. Include performance considerations
4. Test across multiple browsers
5. Update this README if needed

## 📊 Metrics & KPIs

### Success Criteria
- **Critical Test Pass Rate**: >95%
- **Performance Regression**: <20% degradation
- **Test Execution Time**: <30 minutes
- **Cross-Browser Compatibility**: 100%

### Monitoring
- Test results dashboard
- Performance trend graphs
- Failure rate tracking
- Coverage reports

## 🔮 Future Enhancements

Planned improvements:
- Visual regression testing
- Mobile device testing
- API fuzz testing
- Load testing with K6
- AI-powered test generation

---

For detailed configuration and advanced usage, see the [docs/](./docs/) directory.