import { FullConfig } from '@playwright/test';
import { TestDataManager } from './utils/test-data-manager';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global test cleanup...');

  const shouldCleanup = process.env.CLEANUP_TEST_DATA !== 'false';

  if (shouldCleanup) {
    console.log('🗑️ Cleaning up test data...');

    try {
      const testDataManager = new TestDataManager();
      await testDataManager.cleanupAllTestData();
      console.log('✅ Test data cleanup completed');
    } catch (error) {
      console.error('❌ Test data cleanup failed:', error);
      // Don't fail the entire test run due to cleanup issues
    }
  } else {
    console.log('⏭️ Skipping test data cleanup (CLEANUP_TEST_DATA=false)');
  }

  console.log('✅ Global teardown completed');
}

export default globalTeardown;