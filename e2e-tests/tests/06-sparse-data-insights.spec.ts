/**
 * @file 06-sparse-data-insights.spec.ts
 * @description E2E tests for sparse data insights generation
 *
 * Tests that the system generates actionable insights and experiment proposals
 * even when provided with minimal data (e.g., only channel information, no metrics).
 *
 * Key scenarios:
 * - Upload file with minimal data (only channel info)
 * - Verify insights are generated with weak data support
 * - Verify experiment keywords are present in proposed actions
 * - Verify UI displays weak insights correctly with visual distinction
 * - Verify insights appear in both workspace page and AnalysisSnapshot
 */

import { test, expect } from '@playwright/test'
import path from 'path'

const SPARSE_DATA_FILE = path.join(__dirname, '../fixtures/sparse-data.csv')
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000'

test.describe('Sparse Data Insights Generation @critical', () => {
  test('should generate insights from minimal data and display with weak data indicators', async ({ page }) => {
    // Navigate to workspace
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Upload sparse data file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(SPARSE_DATA_FILE)

    // Wait for upload to complete
    await page.waitForSelector('text=Upload Complete', { timeout: 30000 })
    console.log('✅ File uploaded successfully')

    // Wait for analysis to complete (SSE workflow)
    await page.waitForSelector('[data-testid="analysis-snapshot"]', { timeout: 60000 })
    console.log('✅ Analysis completed')

    // Check that insights section is visible
    const insightsSection = page.locator('[data-testid="analysis-insights-section"]')
    await expect(insightsSection).toBeVisible({ timeout: 10000 })
    console.log('✅ Insights section is visible')

    // Verify exactly 3 insights are displayed
    const insightCards = page.locator('[data-testid="insight-card"]')
    const insightCount = await insightCards.count()
    expect(insightCount).toBe(3)
    console.log(`✅ Found exactly 3 insights`)

    // Verify at least one insight has weak data support
    const weakBadges = page.locator('[data-testid="data-support-badge"]:has-text("LIMITED DATA")')
    const weakBadgeCount = await weakBadges.count()
    expect(weakBadgeCount).toBeGreaterThanOrEqual(1)
    console.log(`✅ Found ${weakBadgeCount} weak insights with LIMITED DATA badge`)

    // Verify weak insights have experiment section visible (auto-expanded)
    const experimentSections = page.locator('[data-testid="experiment-section"]')
    const experimentSectionCount = await experimentSections.count()
    expect(experimentSectionCount).toBeGreaterThanOrEqual(1)
    console.log(`✅ Found ${experimentSectionCount} auto-expanded experiment sections`)

    // Verify learning experiment badge is present
    const learningBadges = page.locator('text=🧪 LEARNING EXPERIMENT')
    const learningBadgeCount = await learningBadges.count()
    expect(learningBadgeCount).toBeGreaterThanOrEqual(1)
    console.log(`✅ Found ${learningBadgeCount} learning experiment badges`)

    // Verify data collection callout is present
    const dataCallouts = page.locator('text=📊 DATA COLLECTION OPPORTUNITY')
    const dataCalloutCount = await dataCallouts.count()
    expect(dataCalloutCount).toBeGreaterThanOrEqual(1)
    console.log(`✅ Found ${dataCalloutCount} data collection callouts`)

    // Verify experiment keywords are highlighted in proposed actions
    const highlightedKeywords = page.locator('.bg-amber-500\\/20.text-amber-300')
    const highlightCount = await highlightedKeywords.count()
    expect(highlightCount).toBeGreaterThan(0)
    console.log(`✅ Found ${highlightCount} highlighted experiment keywords`)

    // Check for "Learning-Focused Recommendations" banner in AnalysisSnapshot
    const learningBanner = page.locator('text=Learning-Focused Recommendations')
    await expect(learningBanner).toBeVisible()
    console.log('✅ Learning-focused recommendations banner is visible')

    // Verify all required insight fields are present
    const firstInsight = insightCards.first()
    await expect(firstInsight.locator('text=Insight')).toBeVisible()
    await expect(firstInsight.locator('text=Hypothesis')).toBeVisible()
    await expect(firstInsight.locator('text=Proposed Action')).toBeVisible()
    await expect(firstInsight.locator('text=Primary lever:')).toBeVisible()
    await expect(firstInsight.locator('text=Expected:')).toBeVisible()
    await expect(firstInsight.locator('text=Confidence:')).toBeVisible()
    console.log('✅ All required insight fields are present')

    // Verify impact scores are displayed
    const impactScores = page.locator('text=/\\d+\\/100/')
    const impactScoreCount = await impactScores.count()
    expect(impactScoreCount).toBe(3)
    console.log('✅ Impact scores are displayed for all insights')

    // Verify impact ranks are displayed
    const impactRanks = page.locator('text=/#[123]/')
    const impactRankCount = await impactRanks.count()
    expect(impactRankCount).toBe(3)
    console.log('✅ Impact ranks are displayed for all insights')

    console.log('✅ All sparse data insights tests passed!')
  })

  test('should display insights in AnalysisSnapshot section', async ({ page }) => {
    // Navigate to workspace
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Upload sparse data file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(SPARSE_DATA_FILE)

    // Wait for upload to complete
    await page.waitForSelector('text=Upload Complete', { timeout: 30000 })

    // Wait for analysis to complete
    await page.waitForSelector('[data-testid="analysis-snapshot"]', { timeout: 60000 })

    // Scroll to insights section in AnalysisSnapshot
    const analysisInsights = page.locator('[data-testid="analysis-insights-section"]')
    await analysisInsights.scrollIntoViewIfNeeded()
    await expect(analysisInsights).toBeVisible()

    // Verify "Strategic Insights" header is present
    const insightsHeader = page.locator('text=Strategic Insights').first()
    await expect(insightsHeader).toBeVisible()
    console.log('✅ Strategic Insights header is visible in AnalysisSnapshot')

    // Verify insights badge shows count
    const insightsBadge = analysisInsights.locator('.text-xs:has-text("insight")')
    await expect(insightsBadge).toBeVisible()
    const badgeText = await insightsBadge.textContent()
    expect(badgeText).toContain('3 insights')
    console.log('✅ Insights badge shows "3 insights"')

    // Verify "Learning-Focused Recommendations" banner
    const learningBanner = analysisInsights.locator('text=Learning-Focused Recommendations')
    await expect(learningBanner).toBeVisible()
    console.log('✅ Learning-focused banner is visible')

    // Verify insights are rendered inline (not using InsightsCard component)
    const inlineInsights = analysisInsights.locator('.bg-gray-800\\/50')
    const inlineCount = await inlineInsights.count()
    expect(inlineCount).toBe(3)
    console.log('✅ 3 insights rendered inline in AnalysisSnapshot')

    console.log('✅ AnalysisSnapshot insights display test passed!')
  })

  test('should verify weak insights contain experiment requirements', async ({ page }) => {
    // Navigate to workspace
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // Upload sparse data file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles(SPARSE_DATA_FILE)

    // Wait for upload and analysis
    await page.waitForSelector('text=Upload Complete', { timeout: 30000 })
    await page.waitForSelector('[data-testid="analysis-snapshot"]', { timeout: 60000 })

    // Find all weak insights
    const weakInsights = page.locator('[data-testid="insight-card"]:has([data-testid="data-support-badge"]:has-text("LIMITED DATA"))')
    const weakCount = await weakInsights.count()
    expect(weakCount).toBeGreaterThanOrEqual(1)
    console.log(`✅ Found ${weakCount} weak insights`)

    // For each weak insight, verify experiment requirements
    for (let i = 0; i < weakCount; i++) {
      const insight = weakInsights.nth(i)

      // Get proposed action text
      const proposedAction = await insight.locator('text=Proposed Action').locator('..').locator('+ div').textContent()
      const actionLower = proposedAction?.toLowerCase() || ''

      console.log(`\n📊 Checking Weak Insight #${i + 1}:`)
      console.log(`   Proposed Action: ${actionLower.substring(0, 100)}...`)

      // Check for learning keywords
      const learningKeywords = ['pilot', 'test', 'experiment', 'a/b', 'validate', 'trial']
      const hasLearningKeyword = learningKeywords.some(kw => actionLower.includes(kw))
      expect(hasLearningKeyword).toBe(true)
      console.log(`   ✓ Contains learning keyword`)

      // Check for budget indicator
      const hasBudget = actionLower.includes('$') && actionLower.includes('budget')
      expect(hasBudget).toBe(true)
      console.log(`   ✓ Includes budget cap`)

      // Check for timeline
      const timelineIndicators = ['day', 'week', 'month']
      const hasTimeline = timelineIndicators.some(t => actionLower.includes(t))
      expect(hasTimeline).toBe(true)
      console.log(`   ✓ Includes timeline`)

      // Check for success metrics
      const metricsKeywords = ['measure', 'track', 'monitor', 'metrics']
      const hasMetrics = metricsKeywords.some(m => actionLower.includes(m))
      expect(hasMetrics).toBe(true)
      console.log(`   ✓ Includes success metrics`)
    }

    console.log('\n✅ All weak insights contain required experiment elements!')
  })
})
