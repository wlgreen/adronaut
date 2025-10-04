import { FullConfig } from '@playwright/test';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global test setup...');

  // Verify that required services are running
  const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

  console.log(`📡 Verifying frontend service at ${frontendUrl}`);
  console.log(`📡 Verifying backend service at ${backendUrl}`);

  try {
    // Check frontend health with curl
    await execAsync(`curl -s "${frontendUrl}" > /dev/null`);
    console.log('✅ Frontend service is healthy');

    // Check backend health with curl
    const { stdout } = await execAsync(`curl -s "${backendUrl}/"`);
    const backendResponse = JSON.parse(stdout);
    console.log('✅ Backend service is healthy:', backendResponse.message);

    console.log('✅ Global setup completed successfully');
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    console.log('⚠️ Continuing with tests despite health check failures');
  }
}

export default globalSetup;