-- Adronaut MVP Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE projects (
  project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Artifacts table (uploaded files)
CREATE TABLE artifacts (
  artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  mime TEXT NOT NULL,
  storage_url TEXT NOT NULL,
  summary_json JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analysis snapshots (feature extraction results)
CREATE TABLE analysis_snapshots (
  snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  result_json JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strategy versions
CREATE TABLE strategy_versions (
  strategy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  strategy_json JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(project_id, version)
);

-- Active strategy per project
CREATE TABLE strategy_active (
  project_id UUID PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategy_versions(strategy_id) ON DELETE CASCADE
);

-- Strategy patches (proposed, approved, rejected, etc.)
CREATE TABLE strategy_patches (
  patch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  source TEXT CHECK (source IN ('insights', 'reflection', 'edited_llm')) NOT NULL,
  status TEXT CHECK (status IN ('proposed', 'approved', 'rejected', 'superseded')) DEFAULT 'proposed',
  patch_json JSONB NOT NULL,
  justification TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Briefs (compiled from strategies)
CREATE TABLE briefs (
  brief_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  strategy_id UUID REFERENCES strategy_versions(strategy_id) ON DELETE CASCADE,
  brief_json JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Campaigns
CREATE TABLE campaigns (
  campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  strategy_id UUID REFERENCES strategy_versions(strategy_id) ON DELETE CASCADE,
  status TEXT CHECK (status IN ('running', 'completed', 'failed')) DEFAULT 'running',
  policy_json JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Metrics (campaign performance data)
CREATE TABLE metrics (
  metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
  ts TIMESTAMP WITH TIME ZONE NOT NULL,
  impressions INTEGER NOT NULL DEFAULT 0,
  clicks INTEGER NOT NULL DEFAULT 0,
  spend DECIMAL(10,2) NOT NULL DEFAULT 0,
  conversions INTEGER NOT NULL DEFAULT 0,
  revenue DECIMAL(10,2) NOT NULL DEFAULT 0,
  extra_json JSONB
);

-- Step events (orchestrator workflow tracking)
CREATE TABLE step_events (
  event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
  run_id UUID NOT NULL,
  step_name TEXT NOT NULL,
  status TEXT CHECK (status IN ('started', 'completed', 'failed')) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX idx_analysis_snapshots_project_id ON analysis_snapshots(project_id);
CREATE INDEX idx_strategy_versions_project_id ON strategy_versions(project_id);
CREATE INDEX idx_strategy_patches_project_id ON strategy_patches(project_id);
CREATE INDEX idx_strategy_patches_status ON strategy_patches(status);
CREATE INDEX idx_campaigns_project_id ON campaigns(project_id);
CREATE INDEX idx_metrics_campaign_id ON metrics(campaign_id);
CREATE INDEX idx_metrics_ts ON metrics(ts);
CREATE INDEX idx_step_events_project_id ON step_events(project_id);
CREATE INDEX idx_step_events_run_id ON step_events(run_id);

-- Create storage bucket for file uploads
INSERT INTO storage.buckets (id, name, public) VALUES ('artifacts', 'artifacts', true);

-- Storage policy to allow uploads (adjust as needed for your security requirements)
CREATE POLICY "Anyone can upload artifacts" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'artifacts');
CREATE POLICY "Anyone can view artifacts" ON storage.objects FOR SELECT USING (bucket_id = 'artifacts');