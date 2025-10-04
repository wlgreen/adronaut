import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Load environment-specific variables
if (process.env.TEST_ENV === 'staging') {
  dotenv.config({ path: '.env.staging' });
} else {
  dotenv.config({ path: '.env.local' });
}

export default defineConfig({
  // Test directory
  testDir: './tests',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'test-results/html-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['line']
  ],

  // Shared settings for all the projects below
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Take screenshot on failure
    screenshot: 'only-on-failure',

    // Record video on failure
    video: 'retain-on-failure',

    // Global timeout for all actions
    actionTimeout: 30000,

    // Global timeout for navigation
    navigationTimeout: 30000,
  },

  // Global test timeout
  timeout: 120000,

  // Global setup
  globalSetup: './global-setup.ts',

  // Global teardown
  globalTeardown: './global-teardown.ts',

  // Configure projects for major browsers
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },

    // Mobile testing
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },

    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },

    // Performance testing
    {
      name: 'performance',
      testDir: './tests/performance',
      use: {
        ...devices['Desktop Chrome'],
        // Disable animations for consistent performance measurements
        reducedMotion: 'reduce',
      },
      dependencies: ['setup'],
    }
  ],

  // Folder for test artifacts
  outputDir: 'test-results/artifacts',

  // Web server configuration for local development
  webServer: [
    {
      command: 'cd ../web && npm run dev',
      url: 'http://localhost:3000',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        NODE_ENV: 'test',
      }
    },
    {
      command: 'cd ../service && python -m uvicorn main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        DEBUG_LLM: 'true',
        SUPABASE_URL: process.env.SUPABASE_URL,
        SUPABASE_KEY: process.env.SUPABASE_KEY,
        GEMINI_API_KEY: process.env.GEMINI_API_KEY,
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
      }
    }
  ],

  // Global test environment
  globalTimeout: 600000, // 10 minutes for entire test run

  // Expect configuration
  expect: {
    // Maximum time expect() should wait for the condition to be met
    timeout: 10000,

    // Whether to take screenshots on expect() failures
    toHaveScreenshot: { threshold: 0.2, mode: 'pixel' },

    // Whether to take screenshots on toMatchSnapshot() failures
    toMatchSnapshot: { threshold: 0.2, mode: 'pixel' },
  },
});