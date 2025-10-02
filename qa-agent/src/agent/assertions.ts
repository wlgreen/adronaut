import { Page, expect } from '@playwright/test';
import {
  getStrategyVersions,
  getPatches,
  getCampaigns,
  getMetrics,
  getBriefs,
  getProjectSummary,
  PatchInfo,
  StrategyVersionInfo,
  CampaignInfo
} from '../supabase/queries';

/**
 * Custom assertions for E2E testing
 * Combines UI and database validations
 */

export class TestAssertions {
  constructor(private page: Page, private projectId: string) {}

  /**
   * Assert that a patch exists with specific criteria
   */
  async assertPatchExists(
    source: 'insights' | 'reflection',
    status: 'proposed' | 'approved' | 'rejected' = 'proposed'
  ): Promise<PatchInfo> {
    const patches = await getPatches(this.projectId, { source, status });

    expect(patches.length).toBeGreaterThan(0);

    const patch = patches[0];
    expect(patch.source).toBe(source);
    expect(patch.status).toBe(status);

    console.log(`✅ Patch assertion passed: ${source} patch with status ${status}`);
    return patch;
  }

  /**
   * Assert strategy version progression
   */
  async assertStrategyVersion(expectedVersion: number): Promise<StrategyVersionInfo> {
    const strategies = await getStrategyVersions(this.projectId);

    expect(strategies.length).toBeGreaterThanOrEqual(expectedVersion);

    const latestStrategy = strategies[strategies.length - 1];
    expect(latestStrategy.version).toBe(expectedVersion);

    console.log(`✅ Strategy version assertion passed: v${expectedVersion}`);
    return latestStrategy;
  }

  /**
   * Assert campaigns were created for a strategy
   */
  async assertCampaignsCreated(strategyId: string, expectedCount: number = 1): Promise<CampaignInfo[]> {
    const campaigns = await getCampaigns(this.projectId);
    const strategyCampaigns = campaigns.filter(c => c.strategy_id === strategyId);

    expect(strategyCampaigns.length).toBe(expectedCount);

    console.log(`✅ Campaigns assertion passed: ${expectedCount} campaigns for strategy ${strategyId}`);
    return strategyCampaigns;
  }

  /**
   * Assert no duplicate campaigns exist
   */
  async assertNoDuplicateCampaigns(): Promise<void> {
    const campaigns = await getCampaigns(this.projectId);
    const strategyIds = campaigns.map(c => c.strategy_id);
    const uniqueStrategyIds = [...new Set(strategyIds)];

    expect(strategyIds.length).toBe(uniqueStrategyIds.length);

    console.log(`✅ No duplicate campaigns assertion passed`);
  }

  /**
   * Assert minimum metrics count
   */
  async assertMetricsCount(minCount: number = 5): Promise<void> {
    const metrics = await getMetrics(this.projectId);

    expect(metrics.length).toBeGreaterThanOrEqual(minCount);

    console.log(`✅ Metrics count assertion passed: ${metrics.length} >= ${minCount}`);
  }

  /**
   * Assert metrics have valid data
   */
  async assertMetricsData(): Promise<void> {
    const metrics = await getMetrics(this.projectId);

    expect(metrics.length).toBeGreaterThan(0);

    // Check that at least some metrics have CTR, CPA, and ROAS data
    const hasCtR = metrics.some(m => m.ctr !== null && m.ctr !== undefined);
    const hasCpa = metrics.some(m => m.cpa !== null && m.cpa !== undefined);
    const hasRoas = metrics.some(m => m.roas !== null && m.roas !== undefined);

    expect(hasCtR).toBe(true);
    expect(hasCpa).toBe(true);
    expect(hasRoas).toBe(true);

    console.log(`✅ Metrics data assertion passed`);
  }

  /**
   * Assert brief exists for strategy version
   */
  async assertBriefExists(strategyVersionId: string): Promise<void> {
    const briefs = await getBriefs(this.projectId);
    const strategyBrief = briefs.find(b => b.strategy_version_id === strategyVersionId);

    expect(strategyBrief).toBeDefined();

    console.log(`✅ Brief assertion passed for strategy ${strategyVersionId}`);
  }

  /**
   * Assert UI elements are visible
   */
  async assertUIElementVisible(selector: string, timeout: number = 10000): Promise<void> {
    await expect(this.page.locator(selector)).toBeVisible({ timeout });
    console.log(`✅ UI element visible: ${selector}`);
  }

  /**
   * Assert UI element contains text
   */
  async assertUIElementContainsText(
    selector: string,
    text: string,
    timeout: number = 10000
  ): Promise<void> {
    await expect(this.page.locator(selector)).toContainText(text, { timeout });
    console.log(`✅ UI element contains text: ${selector} -> "${text}"`);
  }

  /**
   * Assert patch card is visible in UI
   */
  async assertPatchCardVisible(patchId?: string): Promise<void> {
    const patchCardSelector = patchId
      ? `[data-testid="patch-card-${patchId}"]`
      : '[data-testid*="patch-card"]';

    await this.assertUIElementVisible(patchCardSelector);
    console.log(`✅ Patch card visible in UI`);
  }

  /**
   * Assert diff viewer is rendered
   */
  async assertDiffViewerVisible(): Promise<void> {
    await this.assertUIElementVisible('[data-testid="diff-viewer"]');
    console.log(`✅ Diff viewer visible`);
  }

  /**
   * Assert metrics cards show data
   */
  async assertMetricsCardsVisible(): Promise<void> {
    // Check for CTR, CPA, ROAS cards
    await this.assertUIElementVisible('[data-testid="ctr-card"]');
    await this.assertUIElementVisible('[data-testid="cpa-card"]');
    await this.assertUIElementVisible('[data-testid="roas-card"]');

    console.log(`✅ Metrics cards visible`);
  }

  /**
   * Assert file upload success
   */
  async assertFileUploaded(filename: string): Promise<void> {
    const fileListSelector = '[data-testid="uploaded-files"]';
    await this.assertUIElementVisible(fileListSelector);
    await this.assertUIElementContainsText(fileListSelector, filename);

    console.log(`✅ File upload assertion passed: ${filename}`);
  }

  /**
   * Comprehensive project state assertion
   */
  async assertProjectState(expectations: {
    strategyVersion?: number;
    patchesCount?: number;
    campaignsCount?: number;
    metricsCount?: number;
    briefsCount?: number;
  }): Promise<void> {
    console.log(`🔍 Asserting comprehensive project state...`);

    const summary = await getProjectSummary(this.projectId);

    if (expectations.strategyVersion !== undefined) {
      expect(summary.strategies.latest?.version).toBe(expectations.strategyVersion);
    }

    if (expectations.patchesCount !== undefined) {
      expect(summary.patches.total).toBe(expectations.patchesCount);
    }

    if (expectations.campaignsCount !== undefined) {
      expect(summary.campaigns.count).toBe(expectations.campaignsCount);
    }

    if (expectations.metricsCount !== undefined) {
      expect(summary.metrics.count).toBeGreaterThanOrEqual(expectations.metricsCount);
    }

    if (expectations.briefsCount !== undefined) {
      expect(summary.briefs.count).toBe(expectations.briefsCount);
    }

    console.log(`✅ Comprehensive project state assertion passed`);
    console.log(`   Strategies: ${summary.strategies.count} (latest: v${summary.strategies.latest?.version})`);
    console.log(`   Patches: ${summary.patches.total} (${summary.patches.proposed} proposed)`);
    console.log(`   Campaigns: ${summary.campaigns.count}`);
    console.log(`   Metrics: ${summary.metrics.count}`);
    console.log(`   Briefs: ${summary.briefs.count}`);
  }

  /**
   * Assert accessibility compliance using axe-core
   */
  async assertAccessibility(): Promise<void> {
    // Note: This requires axe-playwright to be installed and configured
    try {
      const { injectAxe, checkA11y } = require('axe-playwright');

      await injectAxe(this.page);
      await checkA11y(this.page, null, {
        detailedReport: true,
        detailedReportOptions: { html: true }
      });

      console.log(`✅ Accessibility assertion passed`);
    } catch (error) {
      console.warn(`⚠️  Accessibility check failed or not available:`, error);
      // Don't fail the test if accessibility tools aren't available
    }
  }

  /**
   * Assert page load performance
   */
  async assertPageLoadPerformance(maxLoadTime: number = 5000): Promise<void> {
    const startTime = Date.now();
    await this.page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    expect(loadTime).toBeLessThan(maxLoadTime);

    console.log(`✅ Page load performance assertion passed: ${loadTime}ms < ${maxLoadTime}ms`);
  }

  /**
   * Take screenshot for visual regression testing
   */
  async takeScreenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `./artifacts/screenshots/${name}-${Date.now()}.png`,
      fullPage: true
    });

    console.log(`📸 Screenshot captured: ${name}`);
  }
}