import { supabase } from './client';

/**
 * Query helpers for test assertions
 * These are read-only operations to verify test state
 */

export interface StrategyVersionInfo {
  id: string;
  version: number;
  content: any;
  created_at: string;
}

export interface PatchInfo {
  id: string;
  source: 'insights' | 'reflection';
  status: 'proposed' | 'approved' | 'rejected';
  diff: any;
  created_at: string;
  updated_at: string;
}

export interface CampaignInfo {
  id: string;
  strategy_id: string;
  name: string;
  content: any;
  created_at: string;
}

export interface MetricInfo {
  id: string;
  bucket: string;
  ctr?: number;
  cpa?: number;
  roas?: number;
  created_at: string;
}

/**
 * Get all strategy versions for a project, ordered by version
 */
export async function getStrategyVersions(projectId: string): Promise<StrategyVersionInfo[]> {
  const { data, error } = await supabase
    .from('strategy_versions')
    .select('*')
    .eq('project_id', projectId)
    .order('version', { ascending: true });

  if (error) {
    throw new Error(`Failed to fetch strategy versions: ${error.message}`);
  }

  return data || [];
}

/**
 * Get the latest strategy version for a project
 */
export async function getLatestStrategyVersion(projectId: string): Promise<StrategyVersionInfo | null> {
  const { data, error } = await supabase
    .from('strategy_versions')
    .select('*')
    .eq('project_id', projectId)
    .order('version', { ascending: false })
    .limit(1)
    .single();

  if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
    throw new Error(`Failed to fetch latest strategy version: ${error.message}`);
  }

  return data || null;
}

/**
 * Get patches for a project with optional filtering
 */
export async function getPatches(
  projectId: string,
  filters?: {
    status?: 'proposed' | 'approved' | 'rejected';
    source?: 'insights' | 'reflection';
  }
): Promise<PatchInfo[]> {
  let query = supabase
    .from('patches')
    .select('*')
    .eq('project_id', projectId);

  if (filters?.status) {
    query = query.eq('status', filters.status);
  }

  if (filters?.source) {
    query = query.eq('source', filters.source);
  }

  const { data, error } = await query.order('created_at', { ascending: false });

  if (error) {
    throw new Error(`Failed to fetch patches: ${error.message}`);
  }

  return data || [];
}

/**
 * Get campaigns for a project
 */
export async function getCampaigns(projectId: string): Promise<CampaignInfo[]> {
  const { data, error } = await supabase
    .from('campaigns')
    .select('*')
    .eq('project_id', projectId)
    .order('created_at', { ascending: false });

  if (error) {
    throw new Error(`Failed to fetch campaigns: ${error.message}`);
  }

  return data || [];
}

/**
 * Get campaigns for a specific strategy
 */
export async function getCampaignsForStrategy(strategyId: string): Promise<CampaignInfo[]> {
  const { data, error } = await supabase
    .from('campaigns')
    .select('*')
    .eq('strategy_id', strategyId)
    .order('created_at', { ascending: false });

  if (error) {
    throw new Error(`Failed to fetch campaigns for strategy: ${error.message}`);
  }

  return data || [];
}

/**
 * Get metrics for a project
 */
export async function getMetrics(projectId: string): Promise<MetricInfo[]> {
  const { data, error } = await supabase
    .from('metrics')
    .select('*')
    .eq('project_id', projectId)
    .order('created_at', { ascending: false });

  if (error) {
    throw new Error(`Failed to fetch metrics: ${error.message}`);
  }

  return data || [];
}

/**
 * Count metrics for a project
 */
export async function getMetricsCount(projectId: string): Promise<number> {
  const { count, error } = await supabase
    .from('metrics')
    .select('*', { count: 'exact', head: true })
    .eq('project_id', projectId);

  if (error) {
    throw new Error(`Failed to count metrics: ${error.message}`);
  }

  return count || 0;
}

/**
 * Get briefs for a project
 */
export async function getBriefs(projectId: string): Promise<any[]> {
  const { data, error } = await supabase
    .from('briefs')
    .select('*')
    .eq('project_id', projectId)
    .order('created_at', { ascending: false });

  if (error) {
    throw new Error(`Failed to fetch briefs: ${error.message}`);
  }

  return data || [];
}

/**
 * Get events for a project
 */
export async function getEvents(projectId: string, eventType?: string): Promise<any[]> {
  let query = supabase
    .from('events')
    .select('*')
    .eq('project_id', projectId);

  if (eventType) {
    query = query.eq('type', eventType);
  }

  const { data, error } = await query.order('created_at', { ascending: false });

  if (error) {
    throw new Error(`Failed to fetch events: ${error.message}`);
  }

  return data || [];
}

/**
 * Check if a project exists
 */
export async function projectExists(projectId: string): Promise<boolean> {
  const { data, error } = await supabase
    .from('projects')
    .select('id')
    .eq('id', projectId)
    .single();

  if (error && error.code !== 'PGRST116') {
    throw new Error(`Failed to check project existence: ${error.message}`);
  }

  return !!data;
}

/**
 * Validate database state for a project
 * Returns a summary of all related data
 */
export async function getProjectSummary(projectId: string) {
  const [
    strategies,
    patches,
    campaigns,
    metrics,
    briefs,
    events
  ] = await Promise.all([
    getStrategyVersions(projectId),
    getPatches(projectId),
    getCampaigns(projectId),
    getMetrics(projectId),
    getBriefs(projectId),
    getEvents(projectId),
  ]);

  const metricsCount = metrics.length;
  const proposedPatches = patches.filter(p => p.status === 'proposed');
  const approvedPatches = patches.filter(p => p.status === 'approved');

  return {
    projectId,
    strategies: {
      count: strategies.length,
      latest: strategies[strategies.length - 1] || null,
      versions: strategies.map(s => s.version),
    },
    patches: {
      total: patches.length,
      proposed: proposedPatches.length,
      approved: approvedPatches.length,
      rejected: patches.filter(p => p.status === 'rejected').length,
    },
    campaigns: {
      count: campaigns.length,
      list: campaigns,
    },
    metrics: {
      count: metricsCount,
      hasData: metricsCount > 0,
    },
    briefs: {
      count: briefs.length,
    },
    events: {
      count: events.length,
    },
  };
}