#!/usr/bin/env node

require('dotenv').config();
require('dotenv').config({ path: '.env.local' });

console.log('🔧 Adronaut E2E Test Configuration Verification\n');

// Check required environment variables
const requiredVars = [
  'SUPABASE_URL',
  'SUPABASE_KEY',
  'GEMINI_API_KEY',
  'OPENAI_API_KEY',
  'FRONTEND_URL',
  'BACKEND_URL'
];

let allConfigured = true;

console.log('📋 Environment Variables:');
requiredVars.forEach(varName => {
  const value = process.env[varName];
  const status = value ? '✅' : '❌';
  const displayValue = value ?
    (varName.includes('KEY') ? `${value.substring(0, 12)}...` : value) :
    'Not set';

  console.log(`   ${status} ${varName}: ${displayValue}`);

  if (!value) {
    allConfigured = false;
  }
});

console.log('\n🔗 Service URLs:');
console.log(`   Frontend: ${process.env.FRONTEND_URL}`);
console.log(`   Backend:  ${process.env.BACKEND_URL}`);

console.log('\n🧪 Test Configuration:');
console.log(`   Test Environment: ${process.env.TEST_ENV || 'local'}`);
console.log(`   Debug LLM: ${process.env.DEBUG_LLM || 'true'}`);
console.log(`   Mock AI Responses: ${process.env.MOCK_AI_RESPONSES || 'false'}`);

if (allConfigured) {
  console.log('\n✅ All configuration is properly set up!');
  console.log('   You can now run the e2e tests with: npm test');
} else {
  console.log('\n❌ Some configuration is missing. Please check the .env.local file.');
  process.exit(1);
}