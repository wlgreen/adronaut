# QA Test Agent for Adronaut

A comprehensive end-to-end testing framework for validating Adronaut's complete user journey, from artifact upload through HITL approval cycles to campaign generation and metrics collection.

## Overview

This QA Test Agent validates the core Adronaut workflow:
1. 📁 **Artifact Upload** → File upload via UI
2. 🚀 **Run Start** → Trigger analysis pipeline
3. 🔍 **Patch Proposal** → AI generates strategy insights
4. ✅ **HITL Approval #1** → Human approves initial strategy
5. 📈 **Strategy v2 + Campaign** → System generates brief and campaign
6. 📊 **Metrics Collection** → Performance data streams in
7. 🔄 **Reflection Patch** → AI proposes optimizations
8. ✅ **HITL Approval #2** → Human approves refinements
9. 🎯 **Strategy v3 + New Campaign** → Final optimized campaign

## Quick Start

```bash
# Clone and setup
cd qa-agent
npm install
cp .env.example .env   # Fill in your environment variables
npx playwright install

# Run complete test suite
npm run qa

# Run individual tests
npm run test:e2e
npm run test:e2e:headed    # With visible browser
npm run test:e2e:debug     # With debugging

# View results
npm run report:open
```

## Project Structure

```
qa-agent/
├── src/
│   ├── agent/
│   │   ├── orchestrator.ts      # Main test coordinator
│   │   ├── steps.ts             # Reusable test steps
│   │   ├── assertions.ts        # Custom assertions
│   │   └── reporters/
│   │       └── mdReporter.ts    # Markdown report generator
│   ├── supabase/
│   │   ├── client.ts            # Database client
│   │   ├── reset.ts             # Database reset utilities
│   │   ├── seed.ts              # Test data seeding
│   │   └── queries.ts           # Database query helpers
│   ├── fixtures/
│   │   ├── sample_artifact.csv  # Test data file
│   │   └── sample.pdf           # Sample document
│   └── tests/
│       └── e2e.spec.ts          # Playwright test specifications
├── .github/workflows/
│   └── e2e.yml                  # CI/CD pipeline
├── package.json
├── playwright.config.ts
├── tsconfig.json
└── .env.example
```

## Test Scenarios

### S1: Bootstrap & Initial HITL
- ✅ Reset test database
- ✅ Seed project
- ✅ Navigate to workspace
- ✅ Upload CSV artifact via drag/drop
- ✅ Start analysis run
- ✅ Wait for insights patch proposal
- ✅ Verify patch exists in database

### S2: Approve Initial Patch (HITL #1)
- ✅ Navigate to Strategy page
- ✅ Open patch review card
- ✅ Verify diff viewer renders
- ✅ Approve patch via UI/API
- ✅ Verify strategy version increments (v1→v2)
- ✅ Verify brief and campaign created

### S3: Metrics Collection & Reflection
- ✅ Navigate to Results page
- ✅ Seed performance metrics (CTR/CPA/ROAS)
- ✅ Verify metrics UI displays data
- ✅ Wait for reflection patch proposal
- ✅ Verify reflection patch in Strategy page

### S4: Approve Reflection Patch (HITL #2)
- ✅ Approve reflection patch
- ✅ Verify strategy version increments (v2→v3)
- ✅ Verify new campaign created (exactly one)
- ✅ Verify no duplicate campaigns per strategy

### S5: Negative & Edge Cases
- ✅ Test idempotency (approve same patch twice)
- ✅ Test reject workflow
- ✅ Test LLM edit functionality (optional)
- ✅ Verify proper error handling

### S6: Accessibility & Visual Regression
- ✅ Run axe-core accessibility checks
- ✅ Capture baseline screenshots
- ✅ Validate page load performance
- ✅ Cross-browser compatibility

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required
PAGE_BASE_URL=http://localhost:3000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Optional
PROJECT_NAME_UNDER_TEST=QA-Test-Project
TEST_EDIT_PATCH=false
HEADED=false
```

### Test Configuration

```typescript
// playwright.config.ts
export default defineConfig({
  timeout: 5 * 60 * 1000,        // 5 minutes per test
  retries: process.env.CI ? 2 : 1,
  workers: 1,                     // Sequential for E2E consistency
  use: {
    baseURL: process.env.PAGE_BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  }
});
```

## Database Management

### Safe Reset
```bash
npm run db:reset  # Truncates test tables only
```

### Data Seeding
```bash
npm run db:seed   # Creates test project + initial data
```

### Query Helpers
```typescript
import { getPatches, getStrategyVersions } from './supabase/queries';

const patches = await getPatches(projectId, { status: 'proposed' });
const strategies = await getStrategyVersions(projectId);
```

## API Testing

The agent tests all key API endpoints:

- `POST /api/projects/:id/artifacts` - File upload
- `GET /api/projects/:id/strategy/patches` - Patch listing
- `POST /api/projects/:id/strategy/approve` - HITL approval
- `POST /api/run/start` - Pipeline trigger
- `GET /api/projects/:id/metrics` - Performance data

## Reporting

### Markdown Report
Generated automatically at `/artifacts/qa-run-report.md`:

```markdown
# QA Test Agent Report
**Duration:** 3m 24s
**Project:** QA Test Project (uuid-1234)

## Summary
| Status | Count |
|--------|-------|
| ✅ Passed | 5 |
| ❌ Failed | 1 |

## Test Results
### ✅ S1_Bootstrap_Initial_HITL
**Duration:** 45s
**Details:** {...}
```

### Playwright HTML Report
```bash
npm run report:open  # Opens interactive HTML report
```

## CI/CD Integration

### GitHub Actions
The pipeline runs automatically on:
- Push to `main`/`develop`
- Pull requests
- Daily schedule (2 AM UTC)
- Manual dispatch

```yaml
# .github/workflows/e2e.yml
- name: Run E2E tests
  run: npm run test:e2e
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

### Artifacts
- Test results & screenshots
- Playwright HTML report
- QA markdown summary
- Performance metrics

## Development

### Adding New Scenarios
```typescript
// In orchestrator.ts
private async scenarioX_NewFeature(): Promise<any> {
  // 1. Setup test data
  // 2. Perform UI actions
  // 3. Verify database state
  // 4. Return results
}
```

### Custom Assertions
```typescript
// In assertions.ts
async assertCustomCondition(): Promise<void> {
  const data = await customQuery();
  expect(data).toMatchCondition();
  console.log('✅ Custom assertion passed');
}
```

### Page Object Pattern
```typescript
// steps.ts
export async function interactWithComponent(
  page: Page,
  selector: string,
  action: 'click' | 'fill',
  value?: string
): Promise<void> {
  const element = page.locator(selector);
  await element.waitFor({ state: 'visible' });

  if (action === 'click') {
    await element.click();
  } else if (action === 'fill' && value) {
    await element.fill(value);
  }
}
```

## Troubleshooting

### Common Issues

**Test timeouts:**
```bash
# Increase timeout in .env
PLAYWRIGHT_TIMEOUT=600000  # 10 minutes
```

**Database connection:**
```bash
# Check Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY | head -c 20
```

**File upload failures:**
```bash
# Verify fixture files exist
ls -la src/fixtures/
```

### Debug Mode
```bash
npm run test:e2e:debug  # Opens Playwright inspector
HEADED=true npm run test:e2e  # Visual browser
```

### Logs
```bash
# Enable debug logging
DEBUG=true npm run test:e2e

# Check specific component
DEBUG=supabase npm run test:e2e
```

## Security & Best Practices

### Environment Safety
- ✅ Never commit `.env` files
- ✅ Use test/staging environments only
- ✅ Validate `PROJECT_NAME_UNDER_TEST` contains "test"
- ✅ Service role key has admin access - protect it

### Database Safety
- ✅ Truncation limited to safe table list
- ✅ Foreign key constraint handling
- ✅ Automatic cleanup after tests

### CI Security
```yaml
env:
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
  # Never print secrets in logs
```

## Performance Targets

| Metric | Target | Tolerance |
|--------|--------|-----------|
| Full test suite | < 15 minutes | < 20 minutes |
| Individual scenario | < 5 minutes | < 8 minutes |
| Page load time | < 3 seconds | < 5 seconds |
| API response | < 1 second | < 3 seconds |

## Support

### Documentation
- [Playwright Docs](https://playwright.dev/)
- [Supabase Docs](https://supabase.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

### Team Contact
- **QA Lead:** qa-team@adronaut.com
- **DevOps:** devops@adronaut.com
- **Slack:** #qa-automation

---

*QA Test Agent v1.0.0 - Built for comprehensive E2E validation of Adronaut's AI-powered campaign optimization platform.*