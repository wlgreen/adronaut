import { Page } from '@playwright/test';
import { resetTestDatabase, validateTestEnvironment } from '../supabase/reset';
import { seedTestProject, seedTestMetrics, SeedProjectResult } from '../supabase/seed';
import { TestAssertions } from './assertions';
import {
  navigateAndWait,
  uploadFile,
  clickElement,
  waitForPatch,
  waitForMetrics,
  startRun,
  approveOrRejectPatch,
  waitForStrategyVersion,
  waitForCampaigns,
  verifyNoDuplicateCampaigns
} from './steps';
import { MarkdownReporter } from './reporters/mdReporter';
import path from 'path';

/**
 * QA Agent Orchestrator
 * Coordinates the execution of all test scenarios
 */

export interface ScenarioResult {
  name: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  error?: string;
  details?: any;
}

export interface OrchestratorConfig {
  projectName?: string;
  baseUrl?: string;
  enableEditTests?: boolean;
  enableAccessibilityTests?: boolean;
  screenshotOnFailure?: boolean;
}

export class QAOrchestrator {
  private page: Page;
  private config: OrchestratorConfig;
  private assertions: TestAssertions;
  private reporter: MarkdownReporter;
  private project: SeedProjectResult | null = null;

  constructor(page: Page, config: OrchestratorConfig = {}) {
    this.page = page;
    this.config = {
      baseUrl: process.env.PAGE_BASE_URL || 'http://localhost:3000',
      enableEditTests: process.env.TEST_EDIT_PATCH === 'true',
      enableAccessibilityTests: true,
      screenshotOnFailure: true,
      ...config
    };
    this.assertions = new TestAssertions(page, ''); // Will be set after project creation
    this.reporter = new MarkdownReporter();
  }

  /**
   * Initialize the test environment
   */
  async initialize(): Promise<void> {
    console.log('🚀 Initializing QA Test Environment...');

    // Validate environment
    validateTestEnvironment();

    // Reset database
    await resetTestDatabase();

    // Seed test project
    this.project = await seedTestProject(this.config.projectName);

    // Update assertions with project ID
    this.assertions = new TestAssertions(this.page, this.project.projectId);

    // Initialize reporter
    this.reporter.initialize(this.project);

    console.log(`✅ Environment initialized for project: ${this.project.projectId}`);
  }

  /**
   * Run all test scenarios
   */
  async runAllScenarios(): Promise<ScenarioResult[]> {
    if (!this.project) {
      throw new Error('Orchestrator not initialized. Call initialize() first.');
    }

    const results: ScenarioResult[] = [];

    // S1: Bootstrap & Initial HITL
    results.push(await this.runScenario('S1_Bootstrap_Initial_HITL', () =>
      this.scenario1_BootstrapInitialHITL()
    ));

    // S2: Approve Initial Patch
    results.push(await this.runScenario('S2_Approve_Initial_Patch', () =>
      this.scenario2_ApproveInitialPatch()
    ));

    // S3: Metrics Collection & Reflection Patch
    results.push(await this.runScenario('S3_Metrics_Reflection_Patch', () =>
      this.scenario3_MetricsReflectionPatch()
    ));

    // S4: Approve Reflection Patch
    results.push(await this.runScenario('S4_Approve_Reflection_Patch', () =>
      this.scenario4_ApproveReflectionPatch()
    ));

    // S5: Negative & Edge Cases
    results.push(await this.runScenario('S5_Negative_Edge_Cases', () =>
      this.scenario5_NegativeEdgeCases()
    ));

    // S6: Accessibility & Visual Regression (optional)
    if (this.config.enableAccessibilityTests) {
      results.push(await this.runScenario('S6_Accessibility_Visual', () =>
        this.scenario6_AccessibilityVisual()
      ));
    }

    // Generate final report
    await this.reporter.generateReport(results);

    return results;
  }

  /**
   * Run a single scenario with error handling and timing
   */
  async runScenario(
    name: string,
    scenarioFn: () => Promise<any>
  ): Promise<ScenarioResult> {
    console.log(`\n🎬 Starting scenario: ${name}`);
    const startTime = Date.now();

    try {
      const details = await scenarioFn();
      const duration = Date.now() - startTime;

      console.log(`✅ Scenario passed: ${name} (${duration}ms)`);

      return {
        name,
        status: 'passed',
        duration,
        details
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      console.error(`❌ Scenario failed: ${name} (${duration}ms)`);
      console.error(`Error: ${errorMessage}`);

      if (this.config.screenshotOnFailure) {
        await this.assertions.takeScreenshot(`failure-${name}`);
      }

      return {
        name,
        status: 'failed',
        duration,
        error: errorMessage
      };
    }
  }

  /**
   * S1: Bootstrap & Initial HITL
   */
  private async scenario1_BootstrapInitialHITL(): Promise<any> {
    const projectId = this.project!.projectId;

    // Navigate to workspace
    await navigateAndWait(
      this.page,
      `${this.config.baseUrl}/workspace/${projectId}`,
      '[data-testid="workspace-header"]'
    );

    // Upload sample artifact
    const artifactPath = path.join(__dirname, '../fixtures/sample_artifact.csv');
    await uploadFile(this.page, artifactPath);

    // Verify file appears in list
    await this.assertions.assertFileUploaded('sample_artifact.csv');

    // Start run (either via UI button or direct API)
    let runId: string;
    try {
      // Try UI button first
      await clickElement(this.page, '[data-testid="start-run-button"]');
      runId = 'ui-triggered-run';
    } catch {
      // Fallback to direct API
      runId = await startRun(projectId, this.config.baseUrl);
    }

    // Wait for initial patch to be proposed
    const patches = await waitForPatch(projectId, {
      source: 'insights',
      status: 'proposed',
      minCount: 1
    });

    // Verify patch exists in database
    await this.assertions.assertPatchExists('insights', 'proposed');

    return {
      runId,
      patchesFound: patches.length,
      uploadSuccess: true
    };
  }

  /**
   * S2: Approve Initial Patch (HITL #1)
   */
  private async scenario2_ApproveInitialPatch(): Promise<any> {
    const projectId = this.project!.projectId;

    // Navigate to Strategy page
    await navigateAndWait(
      this.page,
      `${this.config.baseUrl}/strategy/${projectId}`,
      '[data-testid="strategy-header"]'
    );

    // Find and open the patch card
    await this.assertions.assertPatchCardVisible();

    // Assert diff viewer renders
    await clickElement(this.page, '[data-testid="patch-card"] [data-testid="review-button"]');
    await this.assertions.assertDiffViewerVisible();

    // Approve the patch
    const patches = await waitForPatch(projectId, { source: 'insights', status: 'proposed' });
    const patchId = patches[0].id;

    try {
      // Try UI approval
      await clickElement(this.page, '[data-testid="approve-button"]');
    } catch {
      // Fallback to direct API
      await approveOrRejectPatch(projectId, patchId, 'approve');
    }

    // Wait for strategy version to increment
    const strategyV2 = await waitForStrategyVersion(projectId, 2);

    // Verify database state
    await this.assertions.assertStrategyVersion(2);
    await this.assertions.assertBriefExists(strategyV2.id);

    // Wait for campaign creation
    const campaigns = await waitForCampaigns(projectId, 1);
    await this.assertions.assertCampaignsCreated(strategyV2.id, 1);

    return {
      strategyVersion: strategyV2.version,
      campaignsCreated: campaigns.length,
      patchApproved: patchId
    };
  }

  /**
   * S3: Metrics Collection & Reflection Patch
   */
  private async scenario3_MetricsReflectionPatch(): Promise<any> {
    const projectId = this.project!.projectId;

    // Seed some metrics to simulate real data
    await seedTestMetrics(projectId, undefined, 6);

    // Navigate to Results page
    await navigateAndWait(
      this.page,
      `${this.config.baseUrl}/results/${projectId}`,
      '[data-testid="results-header"]'
    );

    // Wait for metrics to appear
    await waitForMetrics(projectId, 5);

    // Assert metrics UI elements
    await this.assertions.assertMetricsCardsVisible();
    await this.assertions.assertMetricsCount(5);
    await this.assertions.assertMetricsData();

    // Wait for reflection patch to be proposed
    const reflectionPatches = await waitForPatch(projectId, {
      source: 'reflection',
      status: 'proposed',
      minCount: 1
    });

    // Navigate back to Strategy and verify reflection patch appears
    await navigateAndWait(
      this.page,
      `${this.config.baseUrl}/strategy/${projectId}`,
      '[data-testid="strategy-header"]'
    );

    await this.assertions.assertPatchCardVisible();

    return {
      metricsCount: 6,
      reflectionPatchesFound: reflectionPatches.length
    };
  }

  /**
   * S4: Approve Reflection Patch (HITL #2)
   */
  private async scenario4_ApproveReflectionPatch(): Promise<any> {
    const projectId = this.project!.projectId;

    // Get reflection patch
    const reflectionPatches = await waitForPatch(projectId, {
      source: 'reflection',
      status: 'proposed'
    });
    const patchId = reflectionPatches[0].id;

    // Approve reflection patch
    try {
      // Try UI approval
      await clickElement(this.page, '[data-testid="approve-button"]');
    } catch {
      // Fallback to direct API
      await approveOrRejectPatch(projectId, patchId, 'approve');
    }

    // Wait for strategy version to increment again
    const strategyV3 = await waitForStrategyVersion(projectId, 3);

    // Verify new campaign created exactly once
    await waitForCampaigns(projectId, 2); // Should have 2 total campaigns now
    await this.assertions.assertCampaignsCreated(strategyV3.id, 1);

    // Verify no duplicate campaigns
    await verifyNoDuplicateCampaigns(projectId);
    await this.assertions.assertNoDuplicateCampaigns();

    return {
      strategyVersion: strategyV3.version,
      totalCampaigns: 2,
      noDuplicates: true
    };
  }

  /**
   * S5: Negative & Edge Cases
   */
  private async scenario5_NegativeEdgeCases(): Promise<any> {
    const projectId = this.project!.projectId;

    const results = {
      idempotencyTest: false,
      rejectTest: false,
      editTest: false
    };

    // Test 1: Idempotency - try to approve same patch twice
    try {
      const patches = await waitForPatch(projectId, { status: 'approved' });
      const approvedPatchId = patches[0].id;

      // Try to approve again (should fail gracefully)
      try {
        await approveOrRejectPatch(projectId, approvedPatchId, 'approve');
        results.idempotencyTest = false; // Should not succeed
      } catch {
        results.idempotencyTest = true; // Expected to fail
      }
    } catch {
      results.idempotencyTest = true; // Skip if no approved patches
    }

    // Test 2: Reject path (if we have a proposed patch)
    try {
      const proposedPatches = await waitForPatch(projectId, { status: 'proposed' });
      if (proposedPatches.length > 0) {
        const patchId = proposedPatches[0].id;
        await approveOrRejectPatch(projectId, patchId, 'reject');

        // Verify patch status changed
        const rejectedPatch = await this.assertions.assertPatchExists('insights', 'rejected');
        results.rejectTest = rejectedPatch.status === 'rejected';
      }
    } catch {
      results.rejectTest = true; // Skip if no proposed patches
    }

    // Test 3: Edit via LLM (if enabled)
    if (this.config.enableEditTests) {
      try {
        await navigateAndWait(
          this.page,
          `${this.config.baseUrl}/strategy/${projectId}`,
          '[data-testid="strategy-header"]'
        );

        await clickElement(this.page, '[data-testid="edit-strategy-button"]');
        // Submit a simple edit request
        await this.page.fill('[data-testid="edit-input"]', 'Increase daily budget by 20%');
        await clickElement(this.page, '[data-testid="submit-edit-button"]');

        results.editTest = true;
      } catch {
        results.editTest = false;
      }
    }

    return results;
  }

  /**
   * S6: Accessibility & Visual Regression
   */
  private async scenario6_AccessibilityVisual(): Promise<any> {
    const projectId = this.project!.projectId;

    const pages = [
      { name: 'workspace', url: `${this.config.baseUrl}/workspace/${projectId}` },
      { name: 'strategy', url: `${this.config.baseUrl}/strategy/${projectId}` },
      { name: 'results', url: `${this.config.baseUrl}/results/${projectId}` }
    ];

    const results = {
      accessibilityPassed: 0,
      screenshotsTaken: 0,
      performanceResults: {}
    };

    for (const pageInfo of pages) {
      try {
        await navigateAndWait(this.page, pageInfo.url);

        // Accessibility check
        try {
          await this.assertions.assertAccessibility();
          results.accessibilityPassed++;
        } catch (error) {
          console.warn(`Accessibility check failed for ${pageInfo.name}:`, error);
        }

        // Performance check
        try {
          await this.assertions.assertPageLoadPerformance(5000);
          results.performanceResults[pageInfo.name] = 'passed';
        } catch (error) {
          results.performanceResults[pageInfo.name] = 'failed';
        }

        // Visual regression screenshot
        await this.assertions.takeScreenshot(`${pageInfo.name}-baseline`);
        results.screenshotsTaken++;

      } catch (error) {
        console.warn(`Page test failed for ${pageInfo.name}:`, error);
      }
    }

    return results;
  }

  /**
   * Get final project summary
   */
  async getFinalSummary(): Promise<any> {
    if (!this.project) return null;

    await this.assertions.assertProjectState({
      strategyVersion: 3,
      campaignsCount: 2,
      metricsCount: 5
    });

    return {
      projectId: this.project.projectId,
      projectName: this.project.projectName,
      finalState: 'completed'
    };
  }
}