import { test, expect } from '@playwright/test';
import { WorkspacePage, StrategyPage, ResultsPage, NavigationHelper, APIHelper } from '../utils/page-objects';
import { TestDataManager } from '../utils/test-data-manager';
import { TestHelpers } from '../utils/test-helpers';

test.describe('Complete Marketing Campaign Flow @critical @smoke', () => {
  let workspacePage: WorkspacePage;
  let strategyPage: StrategyPage;
  let resultsPage: ResultsPage;
  let navigation: NavigationHelper;
  let api: APIHelper;
  let testDataManager: TestDataManager;
  let projectId: string;

  test.beforeEach(async ({ page }) => {
    // Initialize page objects and test utilities
    workspacePage = new WorkspacePage(page);
    strategyPage = new StrategyPage(page);
    resultsPage = new ResultsPage(page);
    navigation = new NavigationHelper(page);
    api = new APIHelper(page);
    testDataManager = new TestDataManager();

    // Generate unique project ID for this test
    projectId = testDataManager.generateTestProjectId();
    console.log(`🚀 Starting test with project ID: ${projectId}`);

    // Verify backend is healthy
    const isHealthy = await api.checkBackendHealth();
    expect(isHealthy).toBe(true);
  });

  test.afterEach(async ({ page }) => {
    // Cleanup test data
    if (projectId) {
      await testDataManager.cleanupTestProject(projectId);
    }
  });

  test('should complete end-to-end campaign creation and execution', async ({ page }) => {
    const testStartTime = Date.now();

    // Step 1: Navigate to workspace and upload files
    console.log('📂 Step 1: Uploading marketing artifacts...');
    await workspacePage.goto();

    // Create and upload test files
    const fileTypes = ['csv', 'json', 'txt'];
    const { files, uploadTime } = await TestHelpers.uploadTestFiles(page, projectId, fileTypes);

    console.log(`✅ Uploaded ${files.length} files in ${uploadTime}ms`);

    // Verify files are uploaded and visible in UI
    await workspacePage.waitForUploadComplete(files[0].name);
    const uploadedCount = await workspacePage.getUploadedFilesCount();
    expect(uploadedCount).toBe(fileTypes.length);

    // Step 2: Trigger AI analysis workflow
    console.log('🤖 Step 2: Starting AI analysis workflow...');
    const analysisStartTime = Date.now();

    await workspacePage.startAnalysis();

    // Monitor workflow progress via real-time events
    const workflowEvent = await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'hitl_required', 120000);
    expect(workflowEvent.status).toBe('hitl_required');

    const analysisTime = Date.now() - analysisStartTime;
    console.log(`✅ Analysis completed in ${analysisTime}ms, awaiting HITL`);

    // Verify analysis results are displayed
    await workspacePage.waitForAnalysisComplete();

    // Step 3: Navigate to strategy page for HITL workflow
    console.log('👤 Step 3: Human-in-the-loop strategy review...');
    await navigation.navigateToStrategy();

    // Wait for pending patch to appear
    await strategyPage.waitForPendingPatch();
    const patchCount = await strategyPage.getPatchCount();
    expect(patchCount).toBeGreaterThan(0);

    // Approve the strategy patch
    await strategyPage.approvePatch();

    // Wait for workflow to continue and complete
    const completionEvent = await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'completed', 180000);
    expect(completionEvent.status).toBe('completed');

    console.log('✅ Strategy approved and workflow completed');

    // Step 4: Verify campaign launch and results
    console.log('📊 Step 4: Verifying campaign launch and metrics...');
    await navigation.navigateToResults();

    // Wait for campaign results to appear
    await resultsPage.waitForCampaignResults();

    // Verify campaign status
    const campaignStatus = await resultsPage.getCampaignStatus();
    expect(campaignStatus).toContain('active');

    // Verify metrics are being collected
    const hasMetrics = await resultsPage.hasMetrics();
    expect(hasMetrics).toBe(true);

    // Step 5: Validate database state
    console.log('💾 Step 5: Validating database state...');
    await TestHelpers.validateDatabaseState(page, projectId, {
      artifactCount: fileTypes.length,
      hasSnapshot: true,
      hasActiveStrategy: true,
      campaignCount: 1
    });

    const totalTime = Date.now() - testStartTime;
    console.log(`🎉 Complete campaign flow test passed in ${totalTime}ms`);

    // Generate performance report
    await TestHelpers.generatePerformanceReport(page, 'Complete Campaign Flow', {
      uploadTime,
      analysisTime,
      totalTime,
      fileCount: fileTypes.length
    });
  });

  test('should handle multiple file types correctly', async ({ page }) => {
    console.log('📎 Testing multiple file type upload and processing...');

    await workspacePage.goto();

    // Test different file type combinations
    const testScenarios = [
      { scenario: 'e-commerce', files: ['csv', 'json'] },
      { scenario: 'b2b-saas', files: ['csv', 'json', 'txt'] },
      { scenario: 'content-marketing', files: ['txt', 'json'] }
    ];

    for (const { scenario, files } of testScenarios) {
      console.log(`🧪 Testing scenario: ${scenario}`);

      const scenarioProjectId = testDataManager.generateTestProjectId();
      const { uploadTime } = await TestHelpers.uploadTestFiles(page, scenarioProjectId, files);

      // Verify upload completed within performance threshold
      const thresholds = testDataManager.getPerformanceThresholds();
      expect(uploadTime).toBeLessThan(thresholds.uploadTime);

      // Generate scenario-specific data
      const scenarioData = testDataManager.generateScenarioData(scenario);
      expect(scenarioData.files).toEqual(files);

      // Cleanup scenario data
      await testDataManager.cleanupTestProject(scenarioProjectId);
    }
  });

  test('should maintain workflow state during browser refresh', async ({ page }) => {
    console.log('🔄 Testing workflow state persistence...');

    await workspacePage.goto();

    // Upload files and start workflow
    const { files } = await TestHelpers.uploadTestFiles(page, projectId, ['csv', 'json']);
    await workspacePage.startAnalysis();

    // Wait for workflow to start
    await TestHelpers.waitForCondition(
      async () => {
        const status = await api.getProjectStatus(projectId);
        return status.snapshot !== null;
      },
      30000
    );

    // Refresh the page
    await page.reload();
    await workspacePage.goto();

    // Verify uploaded files are still visible
    const uploadedCount = await workspacePage.getUploadedFilesCount();
    expect(uploadedCount).toBe(files.length);

    // Verify analysis results are still available
    const status = await api.getProjectStatus(projectId);
    expect(status.snapshot).toBeTruthy();

    console.log('✅ Workflow state maintained after refresh');
  });

  test('should handle concurrent user operations', async ({ page, browser }) => {
    console.log('👥 Testing concurrent user operations...');

    // Create multiple browser contexts to simulate different users
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();

    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    const workspace1 = new WorkspacePage(page1);
    const workspace2 = new WorkspacePage(page2);

    const projectId1 = testDataManager.generateTestProjectId();
    const projectId2 = testDataManager.generateTestProjectId();

    try {
      // Start concurrent operations
      const operation1 = TestHelpers.uploadTestFiles(page1, projectId1, ['csv', 'json']);
      const operation2 = TestHelpers.uploadTestFiles(page2, projectId2, ['txt', 'json']);

      const [result1, result2] = await Promise.all([operation1, operation2]);

      // Verify both operations completed successfully
      expect(result1.files.length).toBe(2);
      expect(result2.files.length).toBe(2);

      console.log('✅ Concurrent operations completed successfully');

      // Cleanup
      await testDataManager.cleanupTestProject(projectId1);
      await testDataManager.cleanupTestProject(projectId2);

    } finally {
      await context1.close();
      await context2.close();
    }
  });
});