#!/usr/bin/env python3
"""Debug script to check Supabase database contents"""
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

async def main():
    # Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    print(f"🔍 Connecting to Supabase: {supabase_url}\n")
    supabase: Client = create_client(supabase_url, supabase_key)

    # Check projects
    print("📦 PROJECTS:")
    projects = supabase.table("projects").select("*").order("created_at", desc=True).limit(10).execute()
    if projects.data:
        print(f"✅ Found {len(projects.data)} projects")
        for p in projects.data:
            print(f"  • {p['project_id'][:8]}... | {p.get('name', 'No name')} | {p['created_at']}")
    else:
        print("❌ No projects found")

    # Check artifacts
    print("\n📄 ARTIFACTS:")
    artifacts = supabase.table("artifacts").select("*").order("created_at", desc=True).limit(10).execute()
    if artifacts.data:
        print(f"✅ Found {len(artifacts.data)} artifacts")
        for a in artifacts.data:
            print(f"  • {a['filename']} | Project: {a['project_id'][:8]}... | {a['created_at']}")
    else:
        print("❌ No artifacts found")

    # Check analysis snapshots
    print("\n📊 ANALYSIS SNAPSHOTS:")
    snapshots = supabase.table("analysis_snapshots").select("*").order("created_at", desc=True).limit(10).execute()
    if snapshots.data:
        print(f"✅ Found {len(snapshots.data)} snapshots")
        for s in snapshots.data:
            print(f"  • {s['snapshot_id'][:8]}... | Project: {s['project_id'][:8]}... | {s['created_at']}")
            # Check if snapshot has insights
            if s.get('summary_json'):
                import json
                summary = json.loads(s['summary_json']) if isinstance(s['summary_json'], str) else s['summary_json']
                has_insights = 'insights' in summary
                has_nested_insights = has_insights and 'insights' in summary.get('insights', {})
                insight_count = len(summary.get('insights', {}).get('insights', [])) if has_nested_insights else 0
                print(f"    → Insights: {insight_count} insights found" if insight_count > 0 else "    → No insights in snapshot")
    else:
        print("❌ No analysis snapshots found")

    # Check strategy patches
    print("\n📝 STRATEGY PATCHES:")
    patches = supabase.table("strategy_patches").select("*").order("created_at", desc=True).limit(10).execute()
    if patches.data:
        print(f"✅ Found {len(patches.data)} patches")
        for p in patches.data:
            print(f"  • {p['patch_id'][:8]}... | Status: {p['status']} | Project: {p['project_id'][:8]}... | {p['created_at']}")
    else:
        print("❌ No strategy patches found")

    # Check campaigns
    print("\n🚀 CAMPAIGNS:")
    campaigns = supabase.table("campaigns").select("*").order("created_at", desc=True).limit(10).execute()
    if campaigns.data:
        print(f"✅ Found {len(campaigns.data)} campaigns")
        for c in campaigns.data:
            print(f"  • {c['name']} | Status: {c['status']} | Project: {c['project_id'][:8]}... | {c['created_at']}")
    else:
        print("❌ No campaigns found")

    # Check step events
    print("\n📋 RECENT STEP EVENTS:")
    events = supabase.table("step_events").select("*").order("created_at", desc=True).limit(15).execute()
    if events.data:
        print(f"✅ Found {len(events.data)} events")
        for e in events.data:
            run_id = e.get('run_id', 'N/A')[:8]
            step = e.get('step_name', 'N/A')
            status = e.get('status', 'N/A')
            print(f"  • Run {run_id}... | {step} | {status}")
    else:
        print("❌ No step events found")

if __name__ == "__main__":
    asyncio.run(main())
