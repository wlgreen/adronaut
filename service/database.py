from supabase import create_client, Client
import os
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
import json
import numpy as np

class Database:
    """Database handler for Supabase operations"""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: Optional[Client] = None

    def _serialize_json_data(self, data: Any) -> Any:
        """Convert non-serializable data types to JSON-serializable format"""
        if data is None:
            return {}

        try:
            # Try direct JSON serialization first
            import json
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            pass

        if isinstance(data, dict):
            return {k: self._serialize_json_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._serialize_json_data(item) for item in data]
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif hasattr(data, 'dtype'):
            # Handle pandas/numpy data types including ObjectDType
            try:
                if 'object' in str(data.dtype):
                    return str(data)
                elif 'int' in str(data.dtype):
                    return int(data)
                elif 'float' in str(data.dtype):
                    return float(data)
                else:
                    return str(data)
            except:
                return str(data)
        elif isinstance(data, (np.integer, np.floating, np.bool_)):
            return data.item()
        elif hasattr(data, '__dict__'):
            # Handle objects with attributes
            try:
                return str(data)
            except:
                return f"<{type(data).__name__} object>"
        else:
            try:
                return str(data)
            except:
                return f"<non-serializable {type(data).__name__}>"

    async def connect(self):
        """Initialize Supabase client"""
        if self.url and self.key and self.url != "dummy" and self.key != "dummy":
            try:
                self.client = create_client(self.url, self.key)
                print(f"✅ Connected to Supabase: {self.url[:20]}...")
            except Exception as e:
                print(f"❌ Failed to connect to Supabase: {e}")
        else:
            print("⚠️ Warning: Supabase credentials not configured - using mock mode")
            print(f"SUPABASE_URL: {self.url}")
            print(f"SUPABASE_KEY: {self.key[:10] if self.key else 'None'}...")

    async def disconnect(self):
        """Cleanup database connections"""
        self.client = None

    async def _get_or_create_placeholder_strategy(self, project_id: str) -> str:
        """Create or get a placeholder strategy for patches created before real strategy exists"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            # Check if placeholder strategy already exists
            result = self.client.table("strategies")\
                .select("strategy_id")\
                .eq("project_id", project_id)\
                .eq("version", 0)\
                .execute()

            if result.data:
                return result.data[0]["strategy_id"]

            # Create placeholder strategy
            placeholder_strategy = {
                "strategy_id": str(uuid.uuid4()),
                "project_id": project_id,
                "version": 0,
                "strategy_data": self._serialize_json_data({
                    "type": "placeholder",
                    "description": "Placeholder strategy for initial patches",
                    "created_for": "pre-strategy patches"
                })
            }

            result = self.client.table("strategies").insert(placeholder_strategy).execute()
            return result.data[0]["strategy_id"]

        except Exception as e:
            print(f"Database error in _get_or_create_placeholder_strategy: {e}")
            return str(uuid.uuid4())

    # Project operations
    async def get_or_create_project(self, project_name: str = "Default Project") -> str:
        """Get or create a project (MVP uses single project)"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            # Check if project exists
            result = self.client.table("projects").select("*").limit(1).execute()

            if result.data:
                return result.data[0]["project_id"]
            else:
                # Create new project
                project_data = {
                    "project_id": str(uuid.uuid4()),
                    "name": project_name
                }
                result = self.client.table("projects").insert(project_data).execute()
                return result.data[0]["project_id"]

        except Exception as e:
            print(f"Database error in get_or_create_project: {e}")
            return str(uuid.uuid4())

    # Artifact operations
    async def create_artifact(
        self,
        project_id: str,
        filename: str,
        mime: str,
        storage_url: str,
        file_content: str = None,
        file_size: int = None,
        summary_json: Dict[str, Any] = None
    ) -> str:
        """Create a new artifact record"""
        artifact_id = str(uuid.uuid4())

        print(f"🔄 Attempting to create artifact: {filename}")
        print(f"   Project ID: {project_id}")
        print(f"   File size: {file_size} bytes")
        print(f"   Content length: {len(file_content) if file_content else 0}")

        if not self.client:
            print(f"❌ No database client - returning mock artifact_id: {artifact_id}")
            return artifact_id

        try:
            artifact_data = {
                "artifact_id": artifact_id,
                "project_id": project_id,
                "filename": filename,
                "mime": mime,
                "storage_url": storage_url,
                "file_content": file_content,
                "file_size": file_size,
                "summary_json": self._serialize_json_data(summary_json) or {}
            }

            print(f"📊 Inserting artifact data to database...")
            result = self.client.table("artifacts").insert(artifact_data).execute()
            actual_id = result.data[0]["artifact_id"]
            print(f"✅ Artifact successfully created in database: {actual_id}")
            return actual_id

        except Exception as e:
            print(f"❌ Database error in create_artifact: {e}")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Returning mock artifact_id: {artifact_id}")
            return artifact_id

    async def get_artifacts(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all artifacts for a project"""
        if not self.client:
            return []

        try:
            result = self.client.table("artifacts").select("*").eq("project_id", project_id).execute()
            return result.data or []

        except Exception as e:
            print(f"Database error in get_artifacts: {e}")
            return []

    async def get_artifact_content(self, artifact_id: str) -> Dict[str, Any]:
        """Get specific artifact with its content"""
        if not self.client:
            return {}

        try:
            result = self.client.table("artifacts").select("*").eq("artifact_id", artifact_id).execute()
            if result.data:
                return result.data[0]
            return {}

        except Exception as e:
            print(f"Database error in get_artifact_content: {e}")
            return {}

    # Snapshot operations
    async def create_snapshot(self, project_id: str, result_json: Dict[str, Any]) -> str:
        """Create a new analysis snapshot"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            snapshot_data = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "snapshot_data": self._serialize_json_data(result_json)
            }

            result = self.client.table("analysis_snapshots").insert(snapshot_data).execute()
            return result.data[0]["id"]

        except Exception as e:
            print(f"Database error in create_snapshot: {e}")
            return str(uuid.uuid4())

    async def get_latest_snapshot(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest analysis snapshot for a project"""
        if not self.client:
            return None

        try:
            result = self.client.table("analysis_snapshots")\
                .select("*")\
                .eq("project_id", project_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Database error in get_latest_snapshot: {e}")
            return None

    # Strategy operations
    async def create_strategy_version(self, project_id: str, strategy_json: Dict[str, Any]) -> str:
        """Create a new strategy version"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            # Get next version number
            result = self.client.table("strategies")\
                .select("version")\
                .eq("project_id", project_id)\
                .order("version", desc=True)\
                .limit(1)\
                .execute()

            next_version = (result.data[0]["version"] + 1) if result.data else 1

            strategy_data = {
                "strategy_id": str(uuid.uuid4()),
                "project_id": project_id,
                "version": next_version,
                "strategy_data": self._serialize_json_data(strategy_json)
            }

            result = self.client.table("strategies").insert(strategy_data).execute()
            return result.data[0]["strategy_id"]

        except Exception as e:
            print(f"Database error in create_strategy_version: {e}")
            return str(uuid.uuid4())

    async def set_active_strategy(self, project_id: str, strategy_id: str):
        """Set the active strategy for a project"""
        if not self.client:
            return

        try:
            # Upsert active strategy
            strategy_data = {
                "project_id": project_id,
                "strategy_id": strategy_id
            }

            self.client.table("strategy_active").upsert(strategy_data).execute()

        except Exception as e:
            print(f"Database error in set_active_strategy: {e}")

    async def get_active_strategy(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the active strategy for a project"""
        if not self.client:
            return None

        try:
            result = self.client.table("strategy_active")\
                .select("*, strategies(*)")\
                .eq("project_id", project_id)\
                .execute()

            if result.data:
                return result.data[0]["strategies"]
            return None

        except Exception as e:
            print(f"Database error in get_active_strategy: {e}")
            return None

    # Patch operations
    async def create_patch(
        self,
        project_id: str,
        source: str,
        patch_json: Dict[str, Any],
        justification: str,
        strategy_id: Optional[str] = None
    ) -> str:
        """Create a new strategy patch"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            # For patches created before any strategy exists, use a placeholder strategy_id
            if strategy_id is None:
                # Create or get a placeholder strategy for this project
                placeholder_strategy_id = await self._get_or_create_placeholder_strategy(project_id)
                strategy_id = placeholder_strategy_id

            patch_data = {
                "patch_id": str(uuid.uuid4()),
                "project_id": project_id,
                "strategy_id": strategy_id,
                "source": source,
                "patch_data": self._serialize_json_data(patch_json),
                "justification": justification,
                "status": "proposed"
            }

            result = self.client.table("strategy_patches").insert(patch_data).execute()
            return result.data[0]["patch_id"]

        except Exception as e:
            print(f"Database error in create_patch: {e}")
            return str(uuid.uuid4())

    async def update_patch_status(self, patch_id: str, status: str):
        """Update the status of a patch"""
        if not self.client:
            return

        try:
            self.client.table("strategy_patches")\
                .update({"status": status})\
                .eq("patch_id", patch_id)\
                .execute()

        except Exception as e:
            print(f"Database error in update_patch_status: {e}")

    async def get_patch(self, patch_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific patch"""
        if not self.client:
            return None

        try:
            result = self.client.table("strategy_patches")\
                .select("*")\
                .eq("patch_id", patch_id)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Database error in get_patch: {e}")
            return None

    async def get_pending_patches(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all pending patches for a project"""
        if not self.client:
            return []

        try:
            result = self.client.table("strategy_patches")\
                .select("*")\
                .eq("project_id", project_id)\
                .eq("status", "proposed")\
                .order("created_at", desc=True)\
                .execute()

            return result.data or []

        except Exception as e:
            print(f"Database error in get_pending_patches: {e}")
            return []

    # Brief operations
    async def create_brief(self, strategy_id: str, brief_json: Dict[str, Any]) -> str:
        """Create a new brief"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            brief_data = {
                "brief_id": str(uuid.uuid4()),
                "strategy_id": strategy_id,
                "brief_json": self._serialize_json_data(brief_json)
            }

            result = self.client.table("briefs").insert(brief_data).execute()
            return result.data[0]["brief_id"]

        except Exception as e:
            print(f"Database error in create_brief: {e}")
            return str(uuid.uuid4())

    # Campaign operations
    async def create_campaign(
        self,
        project_id: str,
        strategy_id: str,
        policy_json: Dict[str, Any]
    ) -> str:
        """Create a new campaign"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            campaign_data = {
                "campaign_id": str(uuid.uuid4()),
                "project_id": project_id,
                "strategy_id": strategy_id,
                "policy_json": self._serialize_json_data(policy_json),
                "status": "running"
            }

            result = self.client.table("campaigns").insert(campaign_data).execute()
            return result.data[0]["campaign_id"]

        except Exception as e:
            print(f"Database error in create_campaign: {e}")
            return str(uuid.uuid4())

    async def get_campaigns(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all campaigns for a project"""
        if not self.client:
            return []

        try:
            result = self.client.table("campaigns")\
                .select("*")\
                .eq("project_id", project_id)\
                .order("created_at", desc=True)\
                .execute()

            return result.data or []

        except Exception as e:
            print(f"Database error in get_campaigns: {e}")
            return []

    # Metrics operations
    async def create_metric(
        self,
        campaign_id: str,
        impressions: int,
        clicks: int,
        spend: float,
        conversions: int,
        revenue: float,
        extra_json: Dict[str, Any] = None
    ) -> str:
        """Create a new metric record"""
        if not self.client:
            return str(uuid.uuid4())

        try:
            metric_data = {
                "metric_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "ts": datetime.utcnow().isoformat(),
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "conversions": conversions,
                "revenue": revenue,
                "extra_json": self._serialize_json_data(extra_json) or {}
            }

            result = self.client.table("metrics").insert(metric_data).execute()
            return result.data[0]["metric_id"]

        except Exception as e:
            print(f"Database error in create_metric: {e}")
            return str(uuid.uuid4())

    async def get_campaign_metrics(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all metrics for a campaign"""
        if not self.client:
            return []

        try:
            result = self.client.table("metrics")\
                .select("*")\
                .eq("campaign_id", campaign_id)\
                .order("ts", desc=True)\
                .execute()

            return result.data or []

        except Exception as e:
            print(f"Database error in get_campaign_metrics: {e}")
            return []

    # Event logging
    async def log_step_event(
        self,
        project_id: str,
        run_id: str,
        step_name: str,
        status: str
    ):
        """Log a workflow step event"""
        if not self.client:
            return

        try:
            event_data = {
                "event_id": str(uuid.uuid4()),
                "project_id": project_id,
                "run_id": run_id,
                "step_name": step_name,
                "status": status
            }

            self.client.table("step_events").insert(event_data).execute()

        except Exception as e:
            print(f"Database error in log_step_event: {e}")

    async def get_workflow_events(self, project_id: str) -> List[Dict[str, Any]]:
        """Get workflow events for a project"""
        if not self.client:
            return []

        try:
            result = self.client.table("step_events")\
                .select("*")\
                .eq("project_id", project_id)\
                .order("created_at", desc=True)\
                .execute()

            return result.data or []

        except Exception as e:
            print(f"Database error in get_workflow_events: {e}")
            return []