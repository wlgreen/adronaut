import { Page, expect } from '@playwright/test';
import { supabase } from '../supabase/client';
import {
  getPatches,
  getMetrics,
  getStrategyVersions,
  getCampaigns,
  getMetricsCount
} from '../supabase/queries';

/**
 * Reusable step functions for E2E testing
 * These provide common operations with built-in retries and logging
 */

export interface StepOptions {
  timeout?: number;
  retryInterval?: number;
  maxRetries?: number;
}

const DEFAULT_OPTIONS: Required<StepOptions> = {
  timeout: 30000,
  retryInterval: 2000,
  maxRetries: 15,
};

/**
 * Wait for an element to be visible with retry logic
 */
export async function waitForElement(
  page: Page,
  selector: string,
  options: StepOptions = {}
): Promise<void> {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  console.log(`🔍 Waiting for element: ${selector}`);

  await expect(page.locator(selector)).toBeVisible({
    timeout: opts.timeout
  });

  console.log(`✅ Element visible: ${selector}`);
}

/**
 * Upload file via drag and drop or file input
 */
export async function uploadFile(
  page: Page,
  filePath: string,
  dropZoneSelector = '[data-testid="file-dropzone"]',
  options: StepOptions = {}
): Promise<void> {
  console.log(`📤 Uploading file: ${filePath}`);

  try {
    // Try drag and drop first
    const dropZone = page.locator(dropZoneSelector);
    if (await dropZone.isVisible()) {
      await dropZone.setInputFiles(filePath);
    } else {
      // Fallback to file input
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(filePath);
    }

    console.log(`✅ File uploaded successfully`);
  } catch (error) {
    console.error(`❌ File upload failed:`, error);
    throw error;
  }
}

/**
 * Navigate to a specific page and wait for it to load
 */
export async function navigateAndWait(
  page: Page,
  path: string,
  waitForSelector?: string,
  options: StepOptions = {}
): Promise<void> {
  console.log(`🚀 Navigating to: ${path}`);

  await page.goto(path);

  if (waitForSelector) {
    await waitForElement(page, waitForSelector, options);
  }

  console.log(`✅ Navigation completed: ${path}`);
}

/**
 * Click element with retry logic
 */
export async function clickElement(
  page: Page,
  selector: string,
  options: StepOptions = {}
): Promise<void> {
  console.log(`👆 Clicking element: ${selector}`);

  const element = page.locator(selector);
  await element.waitFor({ state: 'visible', timeout: options.timeout });
  await element.click();

  console.log(`✅ Element clicked: ${selector}`);
}

/**
 * Poll for patches with specific criteria
 */
export async function waitForPatch(
  projectId: string,
  criteria: {
    source?: 'insights' | 'reflection';
    status?: 'proposed' | 'approved' | 'rejected';
    minCount?: number;
  } = {},
  options: StepOptions = {}
): Promise<any[]> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const { source, status, minCount = 1 } = criteria;

  console.log(`⏳ Waiting for patch(es) - source: ${source}, status: ${status}, minCount: ${minCount}`);

  let attempts = 0;
  const startTime = Date.now();

  while (attempts < opts.maxRetries) {
    try {
      const patches = await getPatches(projectId, { source, status });

      if (patches.length >= minCount) {
        const elapsed = Date.now() - startTime;
        console.log(`✅ Found ${patches.length} patch(es) after ${elapsed}ms`);
        return patches;
      }

      attempts++;
      console.log(`🔄 Attempt ${attempts}/${opts.maxRetries}: Found ${patches.length}/${minCount} patches`);

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    } catch (error) {
      console.warn(`⚠️  Patch query failed on attempt ${attempts}:`, error);
      attempts++;

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    }
  }

  throw new Error(`Timeout waiting for patch(es) after ${opts.maxRetries} attempts`);
}

/**
 * Poll for metrics with minimum count
 */
export async function waitForMetrics(
  projectId: string,
  minCount: number = 5,
  options: StepOptions = {}
): Promise<any[]> {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  console.log(`📊 Waiting for ${minCount} metrics...`);

  let attempts = 0;
  const startTime = Date.now();

  while (attempts < opts.maxRetries) {
    try {
      const metrics = await getMetrics(projectId);

      if (metrics.length >= minCount) {
        const elapsed = Date.now() - startTime;
        console.log(`✅ Found ${metrics.length} metrics after ${elapsed}ms`);
        return metrics;
      }

      attempts++;
      console.log(`🔄 Attempt ${attempts}/${opts.maxRetries}: Found ${metrics.length}/${minCount} metrics`);

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    } catch (error) {
      console.warn(`⚠️  Metrics query failed on attempt ${attempts}:`, error);
      attempts++;

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    }
  }

  throw new Error(`Timeout waiting for metrics after ${opts.maxRetries} attempts`);
}

/**
 * API call to start a run
 */
export async function startRun(
  projectId: string,
  baseUrl: string = process.env.API_BASE_URL || process.env.PAGE_BASE_URL || 'http://localhost:3000'
): Promise<string> {
  console.log(`🏃 Starting run for project: ${projectId}`);

  const response = await fetch(`${baseUrl}/api/run/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ projectId }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Start run failed: ${response.status} ${errorText}`);
  }

  const data = await response.json();
  const runId = data.runId || data.id;

  console.log(`✅ Run started: ${runId}`);
  return runId;
}

/**
 * API call to approve/reject a patch
 */
export async function approveOrRejectPatch(
  projectId: string,
  patchId: string,
  action: 'approve' | 'reject',
  runId?: string,
  baseUrl: string = process.env.API_BASE_URL || process.env.PAGE_BASE_URL || 'http://localhost:3000'
): Promise<void> {
  console.log(`${action === 'approve' ? '✅' : '❌'} ${action}ing patch: ${patchId}`);

  const endpoint = action === 'approve'
    ? `/api/projects/${projectId}/strategy/approve`
    : `/api/projects/${projectId}/strategy/reject`;

  const response = await fetch(`${baseUrl}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      patchId,
      runId: runId || 'test-run-id',
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`${action} patch failed: ${response.status} ${errorText}`);
  }

  console.log(`✅ Patch ${action}ed successfully`);
}

/**
 * Wait for strategy version to increment
 */
export async function waitForStrategyVersion(
  projectId: string,
  expectedVersion: number,
  options: StepOptions = {}
): Promise<any> {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  console.log(`📈 Waiting for strategy version ${expectedVersion}...`);

  let attempts = 0;

  while (attempts < opts.maxRetries) {
    try {
      const strategies = await getStrategyVersions(projectId);
      const latestStrategy = strategies[strategies.length - 1];

      if (latestStrategy && latestStrategy.version >= expectedVersion) {
        console.log(`✅ Strategy version ${latestStrategy.version} found`);
        return latestStrategy;
      }

      attempts++;
      const currentVersion = latestStrategy?.version || 0;
      console.log(`🔄 Attempt ${attempts}/${opts.maxRetries}: Current version ${currentVersion}, waiting for ${expectedVersion}`);

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    } catch (error) {
      console.warn(`⚠️  Strategy query failed on attempt ${attempts}:`, error);
      attempts++;

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    }
  }

  throw new Error(`Timeout waiting for strategy version ${expectedVersion}`);
}

/**
 * Wait for campaigns to be created
 */
export async function waitForCampaigns(
  projectId: string,
  minCount: number = 1,
  options: StepOptions = {}
): Promise<any[]> {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  console.log(`🎯 Waiting for ${minCount} campaign(s)...`);

  let attempts = 0;

  while (attempts < opts.maxRetries) {
    try {
      const campaigns = await getCampaigns(projectId);

      if (campaigns.length >= minCount) {
        console.log(`✅ Found ${campaigns.length} campaign(s)`);
        return campaigns;
      }

      attempts++;
      console.log(`🔄 Attempt ${attempts}/${opts.maxRetries}: Found ${campaigns.length}/${minCount} campaigns`);

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    } catch (error) {
      console.warn(`⚠️  Campaigns query failed on attempt ${attempts}:`, error);
      attempts++;

      if (attempts < opts.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, opts.retryInterval));
      }
    }
  }

  throw new Error(`Timeout waiting for campaigns after ${opts.maxRetries} attempts`);
}

/**
 * Verify no duplicate campaigns exist for the same strategy
 */
export async function verifyNoDuplicateCampaigns(projectId: string): Promise<void> {
  console.log(`🔍 Verifying no duplicate campaigns...`);

  const campaigns = await getCampaigns(projectId);
  const strategyIds = campaigns.map(c => c.strategy_id);
  const uniqueStrategyIds = [...new Set(strategyIds)];

  if (strategyIds.length !== uniqueStrategyIds.length) {
    const duplicates = strategyIds.filter((id, index) => strategyIds.indexOf(id) !== index);
    throw new Error(`Duplicate campaigns found for strategies: ${duplicates.join(', ')}`);
  }

  console.log(`✅ No duplicate campaigns found`);
}