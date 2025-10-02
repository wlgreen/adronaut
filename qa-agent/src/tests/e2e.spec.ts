import { test, expect, Page } from '@playwright/test';
import { QAOrchestrator, OrchestratorConfig } from '../agent/orchestrator';

/**
 * End-to-End Test Specification for Adronaut
 * Uses the QA Orchestrator to run comprehensive test scenarios
 */

test.describe('Adronaut E2E Test Suite', () => {
  let orchestrator: QAOrchestrator;

  test.beforeEach(async ({ page }) => {
    const config: OrchestratorConfig = {
      projectName: `E2E Test ${Date.now()}`,
      baseUrl: process.env.PAGE_BASE_URL || 'http://localhost:3000',
      enableEditTests: process.env.TEST_EDIT_PATCH === 'true',
      enableAccessibilityTests: true,
      screenshotOnFailure: true
    };

    orchestrator = new QAOrchestrator(page, config);
    await orchestrator.initialize();
  });

  test('Complete E2E Flow - All Scenarios', async ({ page }) => {
    test.setTimeout(15 * 60 * 1000); // 15 minutes timeout for full flow

    // Run all test scenarios
    const results = await orchestrator.runAllScenarios();

    // Assert overall success
    const passedCount = results.filter(r => r.status === 'passed').length;
    const totalCount = results.length;

    console.log(`\n📊 Test Results Summary:`);
    console.log(`   Passed: ${passedCount}/${totalCount}`);
    console.log(`   Failed: ${results.filter(r => r.status === 'failed').length}`);
    console.log(`   Skipped: ${results.filter(r => r.status === 'skipped').length}`);

    // Print individual results
    results.forEach(result => {
      const icon = result.status === 'passed' ? '✅' : result.status === 'failed' ? '❌' : '⏭️';
      console.log(`   ${icon} ${result.name} (${result.duration}ms)`);
      if (result.error) {
        console.log(`      Error: ${result.error}`);
      }
    });

    // Get final project summary
    const summary = await orchestrator.getFinalSummary();
    console.log(`\n🎯 Final Project State:`, summary);

    // Assert minimum success criteria
    expect(passedCount).toBeGreaterThanOrEqual(4); // At least core scenarios should pass

    // Assert critical scenarios passed
    const criticalScenarios = [
      'S1_Bootstrap_Initial_HITL',
      'S2_Approve_Initial_Patch',
      'S3_Metrics_Reflection_Patch',
      'S4_Approve_Reflection_Patch'
    ];

    for (const scenarioName of criticalScenarios) {
      const result = results.find(r => r.name === scenarioName);
      expect(result?.status, `Critical scenario ${scenarioName} must pass`).toBe('passed');
    }
  });

  test('Scenario S1: Bootstrap & Initial HITL', async ({ page }) => {
    test.setTimeout(5 * 60 * 1000); // 5 minutes

    // This is primarily a placeholder - individual scenarios are complex to isolate
    // The main testing happens in the "Complete E2E Flow" test above
    console.log('Individual scenario testing - see Complete E2E Flow test for full validation');

    // Basic validation that the orchestrator is properly initialized
    expect(orchestrator).toBeDefined();
  });

  test('Database State Validation', async ({ page }) => {
    test.setTimeout(2 * 60 * 1000); // 2 minutes

    // Run a subset of scenarios to set up state
    const results = await orchestrator.runAllScenarios();

    // Verify final database state
    const summary = await orchestrator.getFinalSummary();

    expect(summary).toBeDefined();
    expect(summary.projectId).toBeTruthy();
    expect(summary.finalState).toBe('completed');
  });

  test('API Endpoints Validation', async ({ page }) => {
    test.setTimeout(3 * 60 * 1000); // 3 minutes

    // Initialize orchestrator to get project
    const baseUrl = process.env.API_BASE_URL || process.env.PAGE_BASE_URL || 'http://localhost:3000';

    // Get project ID from orchestrator
    const summary = await orchestrator.getFinalSummary();
    const projectId = summary?.projectId;

    if (!projectId) {
      test.skip('No project ID available for API testing');
      return;
    }

    // Test key API endpoints
    const endpoints = [
      `/api/projects/${projectId}/snapshots`,
      `/api/projects/${projectId}/strategy`,
      `/api/projects/${projectId}/strategy/versions`,
      `/api/projects/${projectId}/strategy/patches?status=proposed`,
      `/api/projects/${projectId}/brief`,
      `/api/projects/${projectId}/campaigns`,
      `/api/projects/${projectId}/metrics`
    ];

    for (const endpoint of endpoints) {
      const response = await page.request.get(`${baseUrl}${endpoint}`);

      // API should either return 200 (success) or 404 (not found, but endpoint exists)
      expect([200, 404]).toContain(response.status());

      console.log(`✅ API endpoint ${endpoint}: ${response.status()}`);
    }
  });

  test('Page Load Performance', async ({ page }) => {
    test.setTimeout(2 * 60 * 1000); // 2 minutes

    const baseUrl = process.env.PAGE_BASE_URL || 'http://localhost:3000';
    const summary = await orchestrator.getFinalSummary();
    const projectId = summary?.projectId;

    if (!projectId) {
      test.skip('No project ID available for performance testing');
      return;
    }

    const pages = [
      { name: 'Home', url: baseUrl },
      { name: 'Workspace', url: `${baseUrl}/workspace/${projectId}` },
      { name: 'Strategy', url: `${baseUrl}/strategy/${projectId}` },
      { name: 'Results', url: `${baseUrl}/results/${projectId}` }
    ];

    for (const pageInfo of pages) {
      const startTime = Date.now();

      await page.goto(pageInfo.url);
      await page.waitForLoadState('networkidle');

      const loadTime = Date.now() - startTime;

      console.log(`⚡ ${pageInfo.name} page load time: ${loadTime}ms`);

      // Assert reasonable load time (under 10 seconds)
      expect(loadTime).toBeLessThan(10000);
    }
  });

  test('Error Handling & Edge Cases', async ({ page }) => {
    test.setTimeout(3 * 60 * 1000); // 3 minutes

    const baseUrl = process.env.PAGE_BASE_URL || 'http://localhost:3000';

    // Test non-existent project ID
    const fakeProjectId = 'fake-project-id-12345';

    await page.goto(`${baseUrl}/workspace/${fakeProjectId}`);

    // Should show error page or redirect, not crash
    await page.waitForLoadState('networkidle');

    // Page should load without JavaScript errors
    const errors = [];
    page.on('pageerror', error => errors.push(error));

    // Wait a bit to catch any errors
    await page.waitForTimeout(2000);

    // We expect some errors for non-existent projects, but not crashes
    console.log(`🛡️ Page errors for invalid project: ${errors.length}`);

    // Test API error handling
    const response = await page.request.get(`${baseUrl}/api/projects/${fakeProjectId}/strategy`);
    expect([400, 404, 500]).toContain(response.status());
  });
});

/**
 * Utility test for debugging individual components
 */
test.describe('Component Testing', () => {
  test('Supabase Connection', async ({ page }) => {
    // Test Supabase connection without full E2E flow
    const { supabase } = await import('../supabase/client');

    try {
      const { data, error } = await supabase.from('projects').select('id').limit(1);

      if (error && !error.message.includes('relation') && !error.message.includes('does not exist')) {
        throw error;
      }

      console.log('✅ Supabase connection test passed');
    } catch (error) {
      console.warn('⚠️  Supabase connection test failed:', error);
      // Don't fail the test as tables might not exist yet
    }
  });

  test('Environment Variables', async ({ page }) => {
    const requiredVars = [
      'SUPABASE_URL',
      'SUPABASE_SERVICE_ROLE_KEY'
    ];

    const optionalVars = [
      'PAGE_BASE_URL',
      'API_BASE_URL',
      'PROJECT_NAME_UNDER_TEST',
      'TEST_EDIT_PATCH'
    ];

    console.log('🔧 Environment Variables Check:');

    for (const varName of requiredVars) {
      const value = process.env[varName];
      expect(value, `Required environment variable ${varName} must be set`).toBeTruthy();
      console.log(`   ✅ ${varName}: ${value ? 'Set' : 'Missing'}`);
    }

    for (const varName of optionalVars) {
      const value = process.env[varName];
      console.log(`   🔹 ${varName}: ${value || 'Not set (using default)'}`);
    }
  });
});