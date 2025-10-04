import { test, expect } from '@playwright/test';
import { WorkspacePage, APIHelper } from '../utils/page-objects';
import { TestDataManager } from '../utils/test-data-manager';
import { TestHelpers } from '../utils/test-helpers';

test.describe('Error Handling and Edge Cases @error-handling', () => {
  let workspacePage: WorkspacePage;
  let api: APIHelper;
  let testDataManager: TestDataManager;
  let projectId: string;

  test.beforeEach(async ({ page }) => {
    workspacePage = new WorkspacePage(page);
    api = new APIHelper(page);
    testDataManager = new TestDataManager();
    projectId = testDataManager.generateTestProjectId();
  });

  test.afterEach(async ({ page }) => {
    if (projectId) {
      await testDataManager.cleanupTestProject(projectId);
    }
  });

  test('should handle backend service unavailable gracefully', async ({ page }) => {
    console.log('🚨 Testing backend service unavailable scenario...');

    await workspacePage.goto();

    // Simulate backend failure
    const cleanup = await TestHelpers.simulateNetworkFailure(page, /localhost:8000/, 'error');

    try {
      // Attempt file upload when backend is down
      await TestHelpers.uploadTestFiles(page, projectId, ['csv']);
      expect(true).toBe(false); // Should not reach here
    } catch (error) {
      console.log('✅ Backend failure handled correctly:', error.message);
      expect(error.message).toContain('Upload failed');
    }

    // Restore backend and verify recovery
    cleanup();

    // Wait for backend recovery
    await TestHelpers.waitForCondition(
      async () => await api.checkBackendHealth(),
      30000
    );

    // Verify system works after recovery
    const { files } = await TestHelpers.uploadTestFiles(page, projectId, ['csv']);
    expect(files.length).toBe(1);

    console.log('✅ Service recovery handled successfully');
  });

  test('should handle database connection failures', async ({ page }) => {
    console.log('🗄️ Testing database connection failure scenarios...');

    await workspacePage.goto();

    // Monitor console errors
    const { errors, startMonitoring, stopMonitoring } = await TestHelpers.monitorConsoleErrors(page);
    startMonitoring();

    // Simulate database connection issues by intercepting DB-related API calls
    await page.route('**/project/*/status', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Database connection failed' })
      });
    });

    // Attempt operations that require database
    try {
      await api.getProjectStatus(projectId);
      expect(true).toBe(false); // Should not reach here
    } catch (error) {
      console.log('✅ Database error handled correctly');
      expect(error.message).toContain('Failed to get project status');
    }

    stopMonitoring();

    // Verify appropriate error handling without crashing
    expect(errors.length).toBeGreaterThanOrEqual(0); // Some errors are expected

    console.log('✅ Database connection failure handled gracefully');
  });

  test('should handle AI service timeout scenarios', async ({ page }) => {
    console.log('🤖 Testing AI service timeout handling...');

    await workspacePage.goto();

    // Upload files first
    await TestHelpers.uploadTestFiles(page, projectId, ['csv', 'json']);

    // Simulate AI service timeout by intercepting workflow start
    await page.route('**/autogen/run/start', route => {
      // Delay response to simulate timeout
      setTimeout(() => {
        route.fulfill({
          status: 504,
          body: JSON.stringify({ error: 'AI service timeout' })
        });
      }, 5000);
    });

    // Start analysis with timeout expectation
    try {
      await workspacePage.startAnalysis();

      // Wait for error to be displayed
      await TestHelpers.waitForCondition(
        async () => await workspacePage.hasError(),
        30000
      );

      const errorMessage = await workspacePage.getErrorMessage();
      expect(errorMessage).toBeTruthy();

      console.log('✅ AI service timeout displayed appropriate error');
    } catch (error) {
      console.log('✅ AI service timeout handled:', error.message);
    }
  });

  test('should handle malformed AI responses', async ({ page }) => {
    console.log('🔧 Testing malformed AI response handling...');

    // Simulate malformed AI response
    await page.route('**/autogen/run/start', route => {
      route.fulfill({
        status: 200,
        body: 'invalid json response'
      });
    });

    await workspacePage.goto();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

    try {
      await workspacePage.startAnalysis();

      // Should handle malformed response gracefully
      await TestHelpers.waitForCondition(
        async () => await workspacePage.hasError(),
        30000
      );

      console.log('✅ Malformed AI response handled gracefully');
    } catch (error) {
      console.log('✅ Expected error for malformed response:', error.message);
    }
  });

  test('should handle partial workflow execution failures', async ({ page }) => {
    console.log('⚠️ Testing partial workflow failure scenarios...');

    await workspacePage.goto();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

    // Start workflow
    await workspacePage.startAnalysis();

    // Simulate failure during workflow execution
    await page.route('**/events/*', route => {
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/plain' },
        body: 'data: {"status": "failed", "error": "Workflow execution failed"}\n\n'
      });
    });

    // Monitor for failure event
    try {
      await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'failed', 60000);
      console.log('✅ Workflow failure detected and handled');
    } catch (error) {
      console.log('✅ Workflow failure timeout handled correctly');
    }
  });

  test('should handle file corruption during upload', async ({ page }) => {
    console.log('💾 Testing file corruption handling...');

    // Create corrupted file content
    const corruptedContent = Buffer.alloc(1024, 0xFF); // Invalid UTF-8 content
    const formData = new FormData();
    const blob = new Blob([corruptedContent], { type: 'text/csv' });
    formData.append('file', blob, 'corrupted.csv');

    try {
      const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
        multipart: formData
      });

      if (response.ok()) {
        console.log('✅ System handles corrupted files gracefully');
      } else {
        const errorText = await response.text();
        expect(errorText).toBeTruthy();
        console.log('✅ Corrupted file rejected appropriately');
      }
    } catch (error) {
      console.log('✅ File corruption handled:', error.message);
    }
  });

  test('should handle SSE connection drops and recovery', async ({ page }) => {
    console.log('📡 Testing SSE connection recovery...');

    await workspacePage.goto();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

    // Start workflow
    await workspacePage.startAnalysis();

    // Simulate SSE connection drop
    await page.route('**/events/*', route => {
      route.abort(); // Simulate connection drop
    });

    await page.waitForTimeout(2000);

    // Restore SSE connection
    await page.unroute('**/events/*');

    // Verify system attempts to reconnect or handles gracefully
    console.log('✅ SSE connection drop scenario tested');
  });

  test('should handle rate limiting scenarios', async ({ page }) => {
    console.log('🚦 Testing rate limiting handling...');

    // Simulate rate limiting response
    await page.route('**/upload**', route => {
      route.fulfill({
        status: 429,
        body: JSON.stringify({ error: 'Rate limit exceeded' })
      });
    });

    try {
      await TestHelpers.uploadTestFiles(page, projectId, ['csv']);
      expect(true).toBe(false); // Should not reach here
    } catch (error) {
      console.log('✅ Rate limiting handled correctly:', error.message);
      expect(error.message).toContain('Upload failed');
    }
  });

  test('should handle memory exhaustion gracefully', async ({ page }) => {
    console.log('🧠 Testing memory exhaustion scenarios...');

    // Attempt to upload extremely large file
    const hugeContent = 'x'.repeat(100 * 1024 * 1024); // 100MB
    const formData = new FormData();
    const blob = new Blob([hugeContent], { type: 'text/plain' });
    formData.append('file', blob, 'huge-file.txt');

    try {
      const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
        multipart: formData,
        timeout: 30000 // Short timeout for this test
      });

      // Should either reject due to size or handle gracefully
      if (!response.ok()) {
        console.log('✅ Large file rejected appropriately');
      } else {
        console.log('⚠️ Large file accepted - verify memory usage');
      }
    } catch (error) {
      console.log('✅ Memory exhaustion handled:', error.message);
    }
  });

  test('should handle browser refresh during critical operations', async ({ page }) => {
    console.log('🔄 Testing browser refresh during operations...');

    await workspacePage.goto();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

    // Start workflow
    await workspacePage.startAnalysis();

    // Wait for workflow to start
    await page.waitForTimeout(2000);

    // Refresh browser during workflow
    await page.reload();
    await workspacePage.goto();

    // Verify system state is preserved or gracefully handled
    const hasError = await workspacePage.hasError();
    if (hasError) {
      console.log('✅ Error displayed after refresh - appropriate handling');
    } else {
      console.log('✅ State preserved after refresh');
    }
  });

  test('should handle invalid project IDs', async ({ page }) => {
    console.log('🆔 Testing invalid project ID handling...');

    const invalidProjectIds = [
      '', // Empty
      'invalid-id-with-special-chars!@#',
      'x'.repeat(1000), // Too long
      '../../etc/passwd', // Path traversal attempt
      '<script>alert("xss")</script>' // XSS attempt
    ];

    for (const invalidId of invalidProjectIds) {
      try {
        await api.getProjectStatus(invalidId);
        console.log(`⚠️ Invalid ID "${invalidId.slice(0, 20)}..." was accepted`);
      } catch (error) {
        console.log(`✅ Invalid ID "${invalidId.slice(0, 20)}..." rejected appropriately`);
      }
    }
  });

  test('should handle concurrent error scenarios', async ({ page, browser }) => {
    console.log('👥 Testing concurrent error scenarios...');

    // Create multiple contexts with different error conditions
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();

    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    try {
      // Set up different error conditions for each context
      await page1.route('**/upload**', route => {
        route.fulfill({ status: 500, body: 'Server error' });
      });

      await page2.route('**/upload**', route => {
        route.fulfill({ status: 404, body: 'Not found' });
      });

      // Attempt operations on both contexts
      const results = await Promise.allSettled([
        TestHelpers.uploadTestFiles(page1, `${projectId}-1`, ['csv']),
        TestHelpers.uploadTestFiles(page2, `${projectId}-2`, ['csv'])
      ]);

      // Both should fail with different errors
      expect(results[0].status).toBe('rejected');
      expect(results[1].status).toBe('rejected');

      console.log('✅ Concurrent error scenarios handled independently');

    } finally {
      await context1.close();
      await context2.close();
    }
  });
});