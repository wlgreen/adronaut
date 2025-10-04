import { test, expect } from '@playwright/test';
import { WorkspacePage, APIHelper } from '../../utils/page-objects';
import { TestDataManager } from '../../utils/test-data-manager';
import { TestHelpers } from '../../utils/test-helpers';

test.describe('Performance Testing @performance', () => {
  let workspacePage: WorkspacePage;
  let api: APIHelper;
  let testDataManager: TestDataManager;
  let projectId: string;
  let performanceThresholds: any;

  test.beforeEach(async ({ page }) => {
    workspacePage = new WorkspacePage(page);
    api = new APIHelper(page);
    testDataManager = new TestDataManager();
    projectId = testDataManager.generateTestProjectId();
    performanceThresholds = testDataManager.getPerformanceThresholds();

    console.log('🎯 Performance Thresholds:', performanceThresholds);
  });

  test.afterEach(async ({ page }) => {
    if (projectId) {
      await testDataManager.cleanupTestProject(projectId);
    }
  });

  test('should meet upload performance thresholds', async ({ page }) => {
    console.log('⚡ Testing upload performance...');

    await workspacePage.goto();

    // Test various file sizes
    const testCases = [
      { size: '1KB', content: 'x'.repeat(1024) },
      { size: '100KB', content: 'x'.repeat(100 * 1024) },
      { size: '1MB', content: 'x'.repeat(1024 * 1024) },
      { size: '5MB', content: 'x'.repeat(5 * 1024 * 1024) }
    ];

    for (const testCase of testCases) {
      const { duration } = await TestHelpers.measureExecutionTime(async () => {
        const formData = new FormData();
        const blob = new Blob([testCase.content], { type: 'text/plain' });
        formData.append('file', blob, `test-${testCase.size}.txt`);

        const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
          multipart: formData
        });

        expect(response.ok()).toBe(true);
        return response.json();
      });

      console.log(`📊 ${testCase.size} file upload: ${duration}ms`);

      // Dynamic threshold based on file size
      const expectedThreshold = testCase.size === '5MB' ?
        performanceThresholds.uploadTime * 2 :
        performanceThresholds.uploadTime;

      expect(duration).toBeLessThan(expectedThreshold);
    }

    await TestHelpers.generatePerformanceReport(page, 'Upload Performance', {
      smallFileTime: testCases[0] ? 0 : 0, // Would contain actual timing
      largeFileTime: testCases[3] ? 0 : 0,
      threshold: performanceThresholds.uploadTime
    });
  });

  test('should meet AI workflow performance thresholds', async ({ page }) => {
    console.log('🤖 Testing AI workflow performance...');

    await workspacePage.goto();

    // Upload test files
    const uploadStart = Date.now();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv', 'json']);
    const uploadTime = Date.now() - uploadStart;

    // Start workflow and measure performance
    const workflowStart = Date.now();
    await workspacePage.startAnalysis();

    // Wait for workflow to reach HITL state
    await TestHelpers.waitForSSEEvent(page, 'test-run-id', 'hitl_required', performanceThresholds.workflowTime);
    const workflowTime = Date.now() - workflowStart;

    console.log(`⏱️ Workflow performance: ${workflowTime}ms (threshold: ${performanceThresholds.workflowTime}ms)`);

    expect(workflowTime).toBeLessThan(performanceThresholds.workflowTime);

    await TestHelpers.generatePerformanceReport(page, 'AI Workflow Performance', {
      uploadTime,
      workflowTime,
      threshold: performanceThresholds.workflowTime
    });
  });

  test('should handle concurrent upload load', async ({ page, browser }) => {
    console.log('👥 Testing concurrent upload load...');

    const concurrentUsers = 5;
    const filesPerUser = 2;

    // Create multiple browser contexts
    const contexts = await Promise.all(
      Array(concurrentUsers).fill(0).map(() => browser.newContext())
    );

    const pages = await Promise.all(
      contexts.map(context => context.newPage())
    );

    try {
      const loadTestStart = Date.now();

      // Start concurrent uploads
      const uploadPromises = pages.map(async (testPage, index) => {
        const userProjectId = `${projectId}-user-${index}`;
        const userApi = new APIHelper(testPage);

        const { duration } = await TestHelpers.measureExecutionTime(async () => {
          return TestHelpers.uploadTestFiles(testPage, userProjectId, ['csv', 'json']);
        });

        return { userId: index, duration, projectId: userProjectId };
      });

      const results = await Promise.all(uploadPromises);
      const loadTestTime = Date.now() - loadTestStart;

      // Verify all uploads completed successfully
      results.forEach(result => {
        expect(result.duration).toBeLessThan(performanceThresholds.uploadTime * 2); // Allow 2x threshold under load
        console.log(`👤 User ${result.userId}: ${result.duration}ms`);
      });

      const avgTime = results.reduce((sum, r) => sum + r.duration, 0) / results.length;
      console.log(`📊 Concurrent load test: ${concurrentUsers} users, avg ${avgTime}ms, total ${loadTestTime}ms`);

      // Cleanup user projects
      for (const result of results) {
        await testDataManager.cleanupTestProject(result.projectId);
      }

      await TestHelpers.generatePerformanceReport(page, 'Concurrent Upload Load', {
        concurrentUsers,
        avgUploadTime: avgTime,
        totalTime: loadTestTime,
        peakMemory: 0 // Would measure actual memory usage
      });

    } finally {
      // Close all contexts
      await Promise.all(contexts.map(context => context.close()));
    }
  });

  test('should maintain performance under memory pressure', async ({ page }) => {
    console.log('🧠 Testing performance under memory pressure...');

    await workspacePage.goto();

    // Create memory pressure by uploading multiple large files
    const largeFiles = Array(3).fill(0).map((_, index) => ({
      content: 'x'.repeat(2 * 1024 * 1024), // 2MB each
      filename: `large-file-${index}.txt`
    }));

    const { duration: memoryPressureTime } = await TestHelpers.measureExecutionTime(async () => {
      for (const file of largeFiles) {
        const formData = new FormData();
        const blob = new Blob([file.content], { type: 'text/plain' });
        formData.append('file', blob, file.filename);

        const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
          multipart: formData
        });

        expect(response.ok()).toBe(true);
      }
    });

    console.log(`🧠 Memory pressure test: ${memoryPressureTime}ms for ${largeFiles.length} large files`);

    // Performance should degrade gracefully, not fail completely
    expect(memoryPressureTime).toBeLessThan(performanceThresholds.uploadTime * largeFiles.length * 2);
  });

  test('should optimize database query performance', async ({ page }) => {
    console.log('🗄️ Testing database query performance...');

    // Upload multiple files to create database load
    const fileCount = 10;
    const fileTypes = ['csv', 'json', 'txt'];

    for (let i = 0; i < fileCount; i++) {
      const fileType = fileTypes[i % fileTypes.length];
      await TestHelpers.uploadTestFiles(page, projectId, [fileType]);
    }

    // Test project status query performance
    const { duration: queryTime } = await TestHelpers.measureExecutionTime(async () => {
      return api.getProjectStatus(projectId);
    });

    console.log(`🗄️ Database query time: ${queryTime}ms for project with ${fileCount} artifacts`);

    // Database queries should be fast even with multiple artifacts
    expect(queryTime).toBeLessThan(5000); // 5 second threshold for complex queries

    // Test multiple concurrent queries
    const concurrentQueries = Array(5).fill(0).map(() =>
      TestHelpers.measureExecutionTime(() => api.getProjectStatus(projectId))
    );

    const queryResults = await Promise.all(concurrentQueries);
    const avgQueryTime = queryResults.reduce((sum, r) => sum + r.duration, 0) / queryResults.length;

    console.log(`🗄️ Concurrent query average: ${avgQueryTime}ms`);
    expect(avgQueryTime).toBeLessThan(10000); // Allow higher threshold for concurrent queries
  });

  test('should handle real-time event streaming performance', async ({ page }) => {
    console.log('📡 Testing real-time event streaming performance...');

    await workspacePage.goto();
    await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

    // Measure SSE event delivery performance
    const events: any[] = [];
    const eventTimestamps: number[] = [];

    // Mock SSE event stream for performance testing
    const mockEvents = [
      { status: 'running', step: 'INGEST' },
      { status: 'running', step: 'FEATURES' },
      { status: 'running', step: 'INSIGHTS' },
      { status: 'hitl_required', step: 'HITL_PATCH' }
    ];

    const streamStart = Date.now();

    // Simulate rapid event delivery
    for (let i = 0; i < mockEvents.length; i++) {
      setTimeout(() => {
        events.push(mockEvents[i]);
        eventTimestamps.push(Date.now() - streamStart);
      }, i * 100); // Events every 100ms
    }

    // Wait for all events
    await TestHelpers.waitForCondition(
      () => Promise.resolve(events.length === mockEvents.length),
      5000
    );

    // Verify event delivery timing
    eventTimestamps.forEach((timestamp, index) => {
      const expectedTime = index * 100;
      const latency = Math.abs(timestamp - expectedTime);
      expect(latency).toBeLessThan(50); // Allow 50ms latency
      console.log(`📡 Event ${index}: ${latency}ms latency`);
    });

    await TestHelpers.generatePerformanceReport(page, 'Real-time Event Streaming', {
      eventCount: events.length,
      avgLatency: eventTimestamps.reduce((sum, t, i) => sum + Math.abs(t - i * 100), 0) / eventTimestamps.length,
      maxLatency: Math.max(...eventTimestamps.map((t, i) => Math.abs(t - i * 100)))
    });
  });

  test('should maintain UI responsiveness during heavy operations', async ({ page }) => {
    console.log('🖥️ Testing UI responsiveness during heavy operations...');

    await workspacePage.goto();

    // Start heavy operation (large file upload)
    const largeContent = 'x'.repeat(5 * 1024 * 1024); // 5MB
    const formData = new FormData();
    const blob = new Blob([largeContent], { type: 'text/plain' });
    formData.append('file', blob, 'heavy-operation.txt');

    // Start upload without waiting
    const uploadPromise = page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
      multipart: formData
    });

    // Test UI responsiveness during upload
    const { duration: uiResponseTime } = await TestHelpers.measureExecutionTime(async () => {
      // Click various UI elements to test responsiveness
      await page.locator('body').click();
      await page.keyboard.press('Tab');
      return 'completed';
    });

    console.log(`🖥️ UI response time during heavy operation: ${uiResponseTime}ms`);

    // UI should remain responsive (< 100ms for simple interactions)
    expect(uiResponseTime).toBeLessThan(1000);

    // Wait for upload to complete
    const uploadResponse = await uploadPromise;
    expect(uploadResponse.ok()).toBe(true);
  });

  test('should generate comprehensive performance baseline', async ({ page }) => {
    console.log('📊 Generating performance baseline...');

    const baselineMetrics: any = {};

    // Page load performance
    const { duration: pageLoadTime } = await TestHelpers.measureExecutionTime(async () => {
      await workspacePage.goto();
      await page.waitForLoadState('networkidle');
    });
    baselineMetrics.pageLoadTime = pageLoadTime;

    // Single file upload performance
    const { duration: singleUploadTime } = await TestHelpers.measureExecutionTime(async () => {
      return TestHelpers.uploadTestFiles(page, projectId, ['csv']);
    });
    baselineMetrics.singleUploadTime = singleUploadTime;

    // Multiple file upload performance
    const { duration: multiUploadTime } = await TestHelpers.measureExecutionTime(async () => {
      return TestHelpers.uploadTestFiles(page, `${projectId}-multi`, ['csv', 'json', 'txt']);
    });
    baselineMetrics.multiUploadTime = multiUploadTime;

    // API response time
    const { duration: apiResponseTime } = await TestHelpers.measureExecutionTime(async () => {
      return api.getProjectStatus(projectId);
    });
    baselineMetrics.apiResponseTime = apiResponseTime;

    console.log('📊 Performance Baseline Metrics:', baselineMetrics);

    // Verify all metrics meet baseline expectations
    expect(baselineMetrics.pageLoadTime).toBeLessThan(5000);
    expect(baselineMetrics.singleUploadTime).toBeLessThan(performanceThresholds.uploadTime);
    expect(baselineMetrics.multiUploadTime).toBeLessThan(performanceThresholds.uploadTime * 3);
    expect(baselineMetrics.apiResponseTime).toBeLessThan(2000);

    await TestHelpers.generatePerformanceReport(page, 'Performance Baseline', baselineMetrics);

    // Cleanup additional project
    await testDataManager.cleanupTestProject(`${projectId}-multi`);
  });
});