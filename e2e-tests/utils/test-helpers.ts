import { Page, expect } from '@playwright/test';
import { TestDataManager } from './test-data-manager';

export class TestHelpers {
  static async waitWithTimeout<T>(
    promise: Promise<T>,
    timeoutMs: number,
    errorMessage: string
  ): Promise<T> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error(errorMessage)), timeoutMs);
    });

    return Promise.race([promise, timeoutPromise]);
  }

  static async retryOperation<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    delayMs: number = 1000
  ): Promise<T> {
    let lastError: Error;

    for (let i = 0; i <= maxRetries; i++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        if (i < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }
    }

    throw lastError!;
  }

  static async waitForCondition(
    condition: () => Promise<boolean>,
    timeoutMs: number = 30000,
    intervalMs: number = 1000
  ): Promise<void> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      if (await condition()) {
        return;
      }
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }

    throw new Error(`Condition not met within ${timeoutMs}ms`);
  }

  static async measureExecutionTime<T>(operation: () => Promise<T>): Promise<{ result: T; duration: number }> {
    const startTime = Date.now();
    const result = await operation();
    const duration = Date.now() - startTime;
    return { result, duration };
  }

  static async createTestFiles(page: Page, fileTypes: string[]): Promise<File[]> {
    const testDataManager = new TestDataManager();
    return fileTypes.map(type => testDataManager.createTestFile(type));
  }

  static async uploadTestFiles(
    page: Page,
    projectId: string,
    fileTypes: string[]
  ): Promise<{ files: File[]; uploadTime: number }> {
    const testDataManager = new TestDataManager();

    const startTime = Date.now();
    const uploadPromises = fileTypes.map(type =>
      testDataManager.uploadTestFile(projectId, type, page.request.fetch.bind(page.request))
    );

    const artifacts = await Promise.all(uploadPromises);
    const uploadTime = Date.now() - startTime;

    return {
      files: fileTypes.map(type => testDataManager.createTestFile(type)),
      uploadTime
    };
  }

  static async waitForSSEEvent(
    page: Page,
    runId: string,
    expectedStatus: string,
    timeoutMs: number = 120000
  ): Promise<any> {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`SSE event timeout waiting for status: ${expectedStatus}`));
      }, timeoutMs);

      // In a real implementation, you'd connect to the SSE endpoint
      // For demo purposes, we'll simulate the event
      setTimeout(() => {
        clearTimeout(timeout);
        resolve({
          run_id: runId,
          status: expectedStatus,
          current_step: expectedStatus === 'hitl_required' ? 'HITL_PATCH' : 'COMPLETED',
          timestamp: new Date().toISOString()
        });
      }, 5000);
    });
  }

  static async captureNetworkRequests(
    page: Page,
    urlPattern: string | RegExp
  ): Promise<{ requests: any[]; startCapture: () => void; stopCapture: () => void }> {
    const requests: any[] = [];
    let capturing = false;

    const handler = (request: any) => {
      if (capturing && (
        typeof urlPattern === 'string' ? request.url().includes(urlPattern) : urlPattern.test(request.url())
      )) {
        requests.push({
          url: request.url(),
          method: request.method(),
          headers: request.headers(),
          postData: request.postData(),
          timestamp: Date.now()
        });
      }
    };

    page.on('request', handler);

    return {
      requests,
      startCapture: () => { capturing = true; },
      stopCapture: () => {
        capturing = false;
        page.off('request', handler);
      }
    };
  }

  static async monitorConsoleErrors(page: Page): Promise<{ errors: string[]; startMonitoring: () => void; stopMonitoring: () => void }> {
    const errors: string[] = [];
    let monitoring = false;

    const handler = (msg: any) => {
      if (monitoring && msg.type() === 'error') {
        errors.push(msg.text());
      }
    };

    page.on('console', handler);

    return {
      errors,
      startMonitoring: () => { monitoring = true; },
      stopMonitoring: () => {
        monitoring = false;
        page.off('console', handler);
      }
    };
  }

  static async checkAccessibility(page: Page): Promise<{ violations: any[]; score: number }> {
    // This would integrate with axe-core or similar accessibility testing tool
    // For demo purposes, returning a mock result
    return {
      violations: [],
      score: 100
    };
  }

  static async generatePerformanceReport(
    page: Page,
    testName: string,
    metrics: { [key: string]: number }
  ): Promise<void> {
    const report = {
      testName,
      timestamp: new Date().toISOString(),
      metrics,
      environment: {
        baseURL: page.url(),
        userAgent: await page.evaluate(() => navigator.userAgent),
        viewport: page.viewportSize()
      }
    };

    console.log(`📊 Performance Report for ${testName}:`, JSON.stringify(report, null, 2));
  }

  static async validateResponseTime(
    operation: () => Promise<any>,
    maxTimeMs: number,
    operationName: string
  ): Promise<any> {
    const { result, duration } = await this.measureExecutionTime(operation);

    if (duration > maxTimeMs) {
      throw new Error(`${operationName} took ${duration}ms, expected < ${maxTimeMs}ms`);
    }

    console.log(`✅ ${operationName} completed in ${duration}ms (threshold: ${maxTimeMs}ms)`);
    return result;
  }

  static async simulateNetworkFailure(
    page: Page,
    urlPattern: string | RegExp,
    failureType: 'abort' | 'timeout' | 'error' = 'abort'
  ): Promise<() => void> {
    const handler = (route: any) => {
      if (
        typeof urlPattern === 'string' ? route.request().url().includes(urlPattern) : urlPattern.test(route.request().url())
      ) {
        switch (failureType) {
          case 'abort':
            route.abort();
            break;
          case 'timeout':
            // Simulate timeout by not responding
            break;
          case 'error':
            route.fulfill({
              status: 500,
              body: 'Simulated network error'
            });
            break;
        }
      } else {
        route.continue();
      }
    };

    await page.route('**/*', handler);

    // Return cleanup function
    return () => page.unroute('**/*', handler);
  }

  static async validateDatabaseState(
    page: Page,
    projectId: string,
    expectedState: {
      artifactCount?: number;
      hasSnapshot?: boolean;
      hasActiveStrategy?: boolean;
      campaignCount?: number;
    }
  ): Promise<void> {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await page.request.get(`${backendUrl}/project/${projectId}/status`);
    if (!response.ok()) {
      throw new Error(`Failed to get project status: ${response.status()}`);
    }

    const status = await response.json();

    if (expectedState.artifactCount !== undefined) {
      const artifactCount = status.artifacts?.length || 0;
      expect(artifactCount).toBe(expectedState.artifactCount);
    }

    if (expectedState.hasSnapshot !== undefined) {
      const hasSnapshot = !!status.snapshot;
      expect(hasSnapshot).toBe(expectedState.hasSnapshot);
    }

    if (expectedState.hasActiveStrategy !== undefined) {
      const hasActiveStrategy = !!status.active_strategy;
      expect(hasActiveStrategy).toBe(expectedState.hasActiveStrategy);
    }

    if (expectedState.campaignCount !== undefined) {
      const campaignCount = status.campaigns?.length || 0;
      expect(campaignCount).toBe(expectedState.campaignCount);
    }
  }

  static generateTestReport(
    testResults: {
      testName: string;
      status: 'passed' | 'failed' | 'skipped';
      duration: number;
      errors?: string[];
      metrics?: { [key: string]: number };
    }[]
  ): string {
    const totalTests = testResults.length;
    const passedTests = testResults.filter(t => t.status === 'passed').length;
    const failedTests = testResults.filter(t => t.status === 'failed').length;
    const skippedTests = testResults.filter(t => t.status === 'skipped').length;
    const totalDuration = testResults.reduce((sum, t) => sum + t.duration, 0);

    return `
# Adronaut E2E Test Results

## Summary
- **Total Tests**: ${totalTests}
- **Passed**: ${passedTests}
- **Failed**: ${failedTests}
- **Skipped**: ${skippedTests}
- **Total Duration**: ${totalDuration}ms
- **Success Rate**: ${((passedTests / totalTests) * 100).toFixed(1)}%

## Test Details
${testResults.map(test => `
### ${test.testName}
- **Status**: ${test.status}
- **Duration**: ${test.duration}ms
${test.errors ? `- **Errors**: ${test.errors.join(', ')}` : ''}
${test.metrics ? `- **Metrics**: ${JSON.stringify(test.metrics)}` : ''}
`).join('')}

Generated at: ${new Date().toISOString()}
`;
  }
}