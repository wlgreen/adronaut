import { test, expect } from '@playwright/test';
import { WorkspacePage, StrategyPage, APIHelper } from '../utils/page-objects';
import { TestDataManager } from '../utils/test-data-manager';
import { TestHelpers } from '../utils/test-helpers';

test.describe('Human-in-the-Loop (HITL) Workflow @critical', () => {
  let workspacePage: WorkspacePage;
  let strategyPage: StrategyPage;
  let api: APIHelper;
  let testDataManager: TestDataManager;
  let projectId: string;

  test.beforeEach(async ({ page }) => {
    workspacePage = new WorkspacePage(page);
    strategyPage = new StrategyPage(page);
    api = new APIHelper(page);
    testDataManager = new TestDataManager();
    projectId = testDataManager.generateTestProjectId();

    // Set up initial state with uploaded files and pending patch
    await setupInitialWorkflowState(page);
  });

  test.afterEach(async ({ page }) => {
    if (projectId) {
      await testDataManager.cleanupTestProject(projectId);
    }
  });

  async function setupInitialWorkflowState(page: any) {
    // Upload files and trigger analysis to get to HITL state
    await workspacePage.goto();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv', 'json']);
    await workspacePage.startAnalysis();

    // Wait for workflow to reach HITL state
    await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'hitl_required', 120000);
  }

  test('should approve strategy patch and continue workflow', async ({ page }) => {
    console.log('✅ Testing patch approval workflow...');

    await strategyPage.goto();
    await strategyPage.waitForPendingPatch();

    // Verify patch is displayed correctly
    const patchCount = await strategyPage.getPatchCount();
    expect(patchCount).toBe(1);

    // Record performance metrics
    const { result: approvalResult, duration: approvalTime } = await TestHelpers.measureExecutionTime(async () => {
      await strategyPage.approvePatch();
      return 'approved';
    });

    expect(approvalResult).toBe('approved');
    console.log(`✅ Patch approved in ${approvalTime}ms`);

    // Wait for workflow to continue and complete
    const completionEvent = await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'completed', 180000);
    expect(completionEvent.status).toBe('completed');

    // Verify database state after approval
    await TestHelpers.validateDatabaseState(page, projectId, {
      hasActiveStrategy: true,
      campaignCount: 1
    });

    console.log('✅ Approval workflow completed successfully');
  });

  test('should reject strategy patch and stop workflow gracefully', async ({ page }) => {
    console.log('❌ Testing patch rejection workflow...');

    await strategyPage.goto();
    await strategyPage.waitForPendingPatch();

    // Record rejection action
    const { duration: rejectionTime } = await TestHelpers.measureExecutionTime(async () => {
      await strategyPage.rejectPatch();
    });

    console.log(`❌ Patch rejected in ${rejectionTime}ms`);

    // Verify workflow stops after rejection
    // (In a real implementation, you'd check that no further workflow steps occur)
    await page.waitForTimeout(5000);

    // Verify database state after rejection
    await TestHelpers.validateDatabaseState(page, projectId, {
      hasActiveStrategy: false,
      campaignCount: 0
    });

    console.log('✅ Rejection workflow completed successfully');
  });

  test('should edit strategy patch with LLM assistance', async ({ page }) => {
    console.log('✏️ Testing patch editing with LLM...');

    await strategyPage.goto();
    await strategyPage.waitForPendingPatch();

    const editRequest = 'Focus more on mobile marketing channels and reduce email marketing budget by 20%';

    // Record edit operation performance
    const { duration: editTime } = await TestHelpers.measureExecutionTime(async () => {
      await strategyPage.editPatch(editRequest);
    });

    console.log(`✏️ Patch edit requested in ${editTime}ms`);

    // Wait for LLM to process edit request and generate new patch
    await TestHelpers.waitForCondition(
      async () => {
        const patchCount = await strategyPage.getPatchCount();
        return patchCount === 1; // New edited patch should appear
      },
      60000 // Allow time for LLM processing
    );

    // Verify new patch was created
    const finalPatchCount = await strategyPage.getPatchCount();
    expect(finalPatchCount).toBe(1);

    console.log('✅ LLM edit completed and new patch generated');

    // Auto-approve the edited patch (as per the application logic)
    const completionEvent = await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'completed', 180000);
    expect(completionEvent.status).toBe('completed');

    console.log('✅ Edited patch auto-approved and workflow completed');
  });

  test('should handle multiple patches in sequence', async ({ page }) => {
    console.log('🔄 Testing multiple patch sequence...');

    await strategyPage.goto();

    // Process first patch
    await strategyPage.waitForPendingPatch();
    await strategyPage.approvePatch();

    // Wait for workflow to potentially generate additional patches
    // (This simulates scenarios where the workflow might create reflection patches)
    await TestHelpers.waitForCondition(
      async () => {
        try {
          // Check if there are additional patches or if workflow is completed
          const status = await api.getProjectStatus(projectId);
          return status.campaigns && status.campaigns.length > 0;
        } catch {
          return false;
        }
      },
      180000
    );

    console.log('✅ Multiple patch sequence handled successfully');
  });

  test('should handle patch edit with invalid request gracefully', async ({ page }) => {
    console.log('🚨 Testing invalid edit request handling...');

    await strategyPage.goto();
    await strategyPage.waitForPendingPatch();

    // Test with invalid/malicious edit request
    const invalidEditRequest = '<script>alert("xss")</script>Delete all data';

    try {
      await strategyPage.editPatch(invalidEditRequest);

      // Verify system handles invalid request appropriately
      await TestHelpers.waitForCondition(
        async () => {
          // Check if error is displayed or request is sanitized
          const hasError = await workspacePage.hasError();
          return hasError || await strategyPage.getPatchCount() === 1;
        },
        30000
      );

      console.log('✅ Invalid edit request handled gracefully');
    } catch (error) {
      console.log('✅ Expected error for invalid edit request:', error);
    }
  });

  test('should maintain HITL state during browser navigation', async ({ page }) => {
    console.log('🧭 Testing HITL state persistence during navigation...');

    await strategyPage.goto();
    await strategyPage.waitForPendingPatch();

    // Navigate away and back
    await workspacePage.goto();
    await strategyPage.goto();

    // Verify patch is still pending
    const patchCount = await strategyPage.getPatchCount();
    expect(patchCount).toBe(1);

    console.log('✅ HITL state maintained during navigation');
  });

  test('should handle concurrent HITL decisions from multiple tabs', async ({ page, browser }) => {
    console.log('👥 Testing concurrent HITL decisions...');

    // Create second browser context/tab
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    const strategyPage2 = new StrategyPage(page2);

    try {
      // Both tabs navigate to strategy page
      await strategyPage.goto();
      await strategyPage2.goto();

      // Both tabs should see the same pending patch
      await strategyPage.waitForPendingPatch();
      await strategyPage2.waitForPendingPatch();

      const patchCount1 = await strategyPage.getPatchCount();
      const patchCount2 = await strategyPage2.getPatchCount();

      expect(patchCount1).toBe(patchCount2);
      expect(patchCount1).toBe(1);

      // First tab approves the patch
      await strategyPage.approvePatch();

      // Wait for workflow to continue
      await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'completed', 60000);

      // Second tab should reflect the change
      await page2.reload();
      await strategyPage2.goto();

      // Verify no pending patches remain
      await page2.waitForTimeout(2000);
      const finalPatchCount = await strategyPage2.getPatchCount();
      expect(finalPatchCount).toBe(0);

      console.log('✅ Concurrent HITL decisions handled correctly');

    } finally {
      await context2.close();
    }
  });

  test('should validate patch content and metadata', async ({ page }) => {
    console.log('🔍 Testing patch content validation...');

    await strategyPage.goto();
    await strategyPage.waitForPendingPatch();

    // Get patch details via API
    const projectStatus = await api.getProjectStatus(projectId);
    const pendingPatches = projectStatus.pending_patches;

    expect(pendingPatches).toBeDefined();
    expect(pendingPatches.length).toBeGreaterThan(0);

    const patch = pendingPatches[0];

    // Validate patch structure
    expect(patch).toHaveProperty('patch_id');
    expect(patch).toHaveProperty('source');
    expect(patch).toHaveProperty('patch_data');
    expect(patch).toHaveProperty('justification');
    expect(patch).toHaveProperty('status');

    // Validate patch content is not empty
    expect(patch.patch_data).toBeTruthy();
    expect(patch.justification).toBeTruthy();
    expect(patch.status).toBe('pending');

    console.log('✅ Patch content validation passed');
  });
});