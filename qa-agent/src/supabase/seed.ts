import { supabase } from './client';
import { v4 as uuidv4 } from 'uuid';

export interface SeedProjectResult {
  projectId: string;
  projectName: string;
}

/**
 * Seeds a test project in the database
 * Returns the created project details for use in tests
 */
export async function seedTestProject(
  projectName?: string
): Promise<SeedProjectResult> {
  const testProjectName = projectName || `QA Test Project ${Date.now()}`;
  const projectId = uuidv4();

  console.log(`🌱 Seeding test project: ${testProjectName}`);

  try {
    const { data, error } = await supabase
      .from('projects')
      .insert({
        id: projectId,
        name: testProjectName,
        description: 'QA Test Project for E2E testing',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      throw new Error(`Failed to seed project: ${error.message}`);
    }

    // Seed initial strategy version (v1)
    const { error: strategyError } = await supabase
      .from('strategy_versions')
      .insert({
        id: uuidv4(),
        project_id: projectId,
        version: 1,
        content: {
          name: 'Initial Strategy',
          description: 'Base strategy for testing',
          targeting: {
            demographics: ['18-35'],
            interests: ['technology'],
          },
          budget: {
            daily: 100,
            total: 3000,
          },
        },
        created_at: new Date().toISOString(),
      });

    if (strategyError) {
      console.warn('Warning: Could not seed initial strategy:', strategyError.message);
    }

    console.log(`✅ Project seeded successfully: ${projectId}`);

    return {
      projectId,
      projectName: testProjectName,
    };
  } catch (error) {
    console.error('❌ Project seeding failed:', error);
    throw new Error(`Project seeding failed: ${error}`);
  }
}

/**
 * Seeds sample metrics data for testing
 */
export async function seedTestMetrics(
  projectId: string,
  campaignId?: string,
  bucketCount: number = 5
): Promise<void> {
  console.log(`📊 Seeding ${bucketCount} test metrics for project ${projectId}`);

  const metrics = Array.from({ length: bucketCount }, (_, index) => ({
    id: uuidv4(),
    project_id: projectId,
    campaign_id: campaignId || null,
    bucket: `bucket_${index + 1}`,
    ctr: Math.random() * 0.1, // 0-10% CTR
    cpa: Math.random() * 50 + 10, // $10-60 CPA
    roas: Math.random() * 5 + 1, // 1-6x ROAS
    created_at: new Date(Date.now() - (bucketCount - index) * 60000).toISOString(), // Spread over time
  }));

  try {
    const { error } = await supabase.from('metrics').insert(metrics);

    if (error) {
      throw new Error(`Failed to seed metrics: ${error.message}`);
    }

    console.log(`✅ Metrics seeded successfully`);
  } catch (error) {
    console.error('❌ Metrics seeding failed:', error);
    throw error;
  }
}

/**
 * Seeds a test patch for HITL scenarios
 */
export async function seedTestPatch(
  projectId: string,
  source: 'insights' | 'reflection' = 'insights',
  runId?: string
): Promise<string> {
  const patchId = uuidv4();

  console.log(`🔧 Seeding test patch for project ${projectId}`);

  const patchData = {
    id: patchId,
    project_id: projectId,
    run_id: runId || uuidv4(),
    source,
    status: 'proposed' as const,
    diff: {
      type: 'strategy_update',
      changes: {
        targeting: {
          add: ['lookalike_audiences'],
          remove: [],
        },
        budget: {
          daily: source === 'reflection' ? 150 : 120,
        },
      },
      summary: `${source === 'reflection' ? 'Performance-based' : 'Initial'} strategy optimization`,
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  try {
    const { error } = await supabase.from('patches').insert(patchData);

    if (error) {
      throw new Error(`Failed to seed patch: ${error.message}`);
    }

    console.log(`✅ Patch seeded successfully: ${patchId}`);
    return patchId;
  } catch (error) {
    console.error('❌ Patch seeding failed:', error);
    throw error;
  }
}

// CLI script support
if (require.main === module) {
  (async () => {
    try {
      const result = await seedTestProject();
      console.log('Seed result:', result);

      // Optionally seed metrics
      await seedTestMetrics(result.projectId);

      process.exit(0);
    } catch (error) {
      console.error('Seeding script failed:', error);
      process.exit(1);
    }
  })();
}