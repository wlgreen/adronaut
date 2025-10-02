#!/usr/bin/env node

/**
 * Manual test runner for QA Agent
 * Allows running individual components without Playwright
 */

const { execSync } = require('child_process');
const path = require('path');

function runCommand(command, cwd = process.cwd()) {
  try {
    console.log(`\n🏃 Running: ${command}`);
    const result = execSync(command, {
      cwd,
      stdio: 'inherit',
      encoding: 'utf8'
    });
    console.log('✅ Command completed successfully\n');
    return result;
  } catch (error) {
    console.error(`❌ Command failed: ${error.message}\n`);
    throw error;
  }
}

async function testDatabaseConnection() {
  console.log('🔍 Testing database connection...');

  try {
    // Build the project first
    runCommand('npm run build');

    // Test Supabase connection
    runCommand('node dist/supabase/reset.js');

    console.log('✅ Database connection test passed');
  } catch (error) {
    console.error('❌ Database connection test failed:', error.message);
    process.exit(1);
  }
}

async function seedTestData() {
  console.log('🌱 Seeding test data...');

  try {
    runCommand('npm run build');
    runCommand('node dist/supabase/seed.js');

    console.log('✅ Test data seeding completed');
  } catch (error) {
    console.error('❌ Test data seeding failed:', error.message);
    process.exit(1);
  }
}

async function validateEnvironment() {
  console.log('🔧 Validating environment...');

  const requiredEnvVars = [
    'SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY'
  ];

  const missing = requiredEnvVars.filter(varName => !process.env[varName]);

  if (missing.length > 0) {
    console.error(`❌ Missing required environment variables: ${missing.join(', ')}`);
    console.error('Please check your .env file');
    process.exit(1);
  }

  console.log('✅ Environment validation passed');
}

async function buildProject() {
  console.log('🔨 Building project...');

  try {
    runCommand('npm run build');
    console.log('✅ Project build completed');
  } catch (error) {
    console.error('❌ Project build failed:', error.message);
    process.exit(1);
  }
}

async function main() {
  const command = process.argv[2];

  require('dotenv').config();

  switch (command) {
    case 'env':
      await validateEnvironment();
      break;

    case 'build':
      await buildProject();
      break;

    case 'db-test':
      await validateEnvironment();
      await buildProject();
      await testDatabaseConnection();
      break;

    case 'seed':
      await validateEnvironment();
      await buildProject();
      await seedTestData();
      break;

    case 'full-check':
      await validateEnvironment();
      await buildProject();
      await testDatabaseConnection();
      await seedTestData();
      console.log('\n🎉 All manual checks passed!');
      break;

    default:
      console.log(`
🔧 QA Agent Manual Test Runner

Usage: node scripts/manual-test.js <command>

Commands:
  env        - Validate environment variables
  build      - Build TypeScript project
  db-test    - Test database connection
  seed       - Seed test data
  full-check - Run all checks

Examples:
  node scripts/manual-test.js env
  node scripts/manual-test.js full-check
      `);
      break;
  }
}

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught exception:', error.message);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

main().catch(error => {
  console.error('❌ Script failed:', error.message);
  process.exit(1);
});