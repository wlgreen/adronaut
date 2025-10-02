import { supabase } from './client';

/**
 * Safe list of tables that can be truncated during testing
 * IMPORTANT: Only add tables here that are safe to truncate in test environment
 */
const SAFE_TABLES_TO_TRUNCATE = [
  'events',
  'metrics',
  'campaigns',
  'briefs',
  'patches',
  'strategy_versions',
  'projects', // This should be last due to foreign key constraints
] as const;

/**
 * Truncates test tables in the correct order to handle foreign key constraints
 * Only truncates tables in the safe list above
 */
export async function resetTestDatabase(): Promise<void> {
  console.log('🧹 Resetting test database...');

  try {
    // Disable foreign key checks temporarily (PostgreSQL equivalent)
    // Note: In production Supabase, this might not be available
    // So we truncate in reverse dependency order instead

    for (const table of SAFE_TABLES_TO_TRUNCATE) {
      console.log(`  Truncating ${table}...`);

      const { error } = await supabase
        .from(table as any)
        .delete()
        .neq('id', ''); // Delete all records (neq with impossible condition)

      if (error) {
        console.warn(`Warning: Could not truncate ${table}:`, error.message);
        // Try direct SQL if delete fails
        try {
          const { error: sqlError } = await supabase.rpc('truncate_table', {
            table_name: table
          });
          if (sqlError) {
            console.warn(`SQL truncate also failed for ${table}:`, sqlError.message);
          }
        } catch (rpcError) {
          // RPC might not exist, that's okay
          console.warn(`RPC truncate not available for ${table}`);
        }
      }
    }

    console.log('✅ Database reset completed');
  } catch (error) {
    console.error('❌ Database reset failed:', error);
    throw new Error(`Database reset failed: ${error}`);
  }
}

/**
 * Validates that we're running in a test environment
 * Checks for test-specific environment variables or database names
 */
export function validateTestEnvironment(): void {
  const supabaseUrl = process.env.SUPABASE_URL;
  const projectName = process.env.PROJECT_NAME_UNDER_TEST;

  if (!projectName || !projectName.toLowerCase().includes('test')) {
    console.warn('⚠️  PROJECT_NAME_UNDER_TEST should contain "test" for safety');
  }

  if (supabaseUrl && supabaseUrl.includes('prod')) {
    throw new Error('❌ Cannot run tests against production database');
  }

  console.log('✅ Test environment validated');
}

// CLI script support
if (require.main === module) {
  (async () => {
    try {
      validateTestEnvironment();
      await resetTestDatabase();
      process.exit(0);
    } catch (error) {
      console.error('Database reset script failed:', error);
      process.exit(1);
    }
  })();
}