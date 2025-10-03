from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
import uvicorn
import os
from dotenv import load_dotenv
import asyncio
import json
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import logging
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from gemini_orchestrator import GeminiOrchestrator as CrewAIOrchestrator
from database import Database
from file_processor import FileProcessor

load_dotenv()

app = FastAPI(title="Adronaut AutoGen Service", version="1.0.0")

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://*.vercel.app",   # Vercel deployments
        "https://vercel.app",     # Vercel domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db = Database()
orchestrator = CrewAIOrchestrator()
file_processor = FileProcessor()

# Store active runs for SSE
active_runs: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db.disconnect()

@app.get("/")
async def root():
    return {"message": "Adronaut AutoGen Service", "status": "running"}

@app.post("/upload")
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload and process a file artifact"""
    try:
        logger.info(f"📤 Starting file upload: {file.filename} for project {project_id[:8]}")

        # Ensure project exists in database
        actual_project_id = await db.get_or_create_project(f"Project {project_id[:8]}")
        logger.info(f"📁 Project ensured: {actual_project_id}")

        # Process the uploaded file
        logger.info(f"⚙️ Processing file: {file.filename} ({file.content_type})")
        result = await file_processor.process_file(file, actual_project_id)
        logger.info(f"✅ File processed successfully: {result['artifact_id']}")

        # Store artifact in database
        logger.info(f"💾 Storing artifact in database...")
        await db.create_artifact(
            project_id=actual_project_id,
            filename=file.filename,
            mime=file.content_type,
            storage_url=result["storage_url"],
            file_content=result.get("file_content"),
            file_size=result.get("file_size"),
            summary_json=result.get("summary", {})
        )
        logger.info(f"✅ Artifact stored successfully")

        # Start background processing if this is the first file or triggers analysis
        if background_tasks:
            logger.info(f"🚀 Starting background analysis workflow for project {actual_project_id}")
            background_tasks.add_task(start_analysis_workflow, actual_project_id)

        logger.info(f"🎉 File upload completed successfully")
        return {"success": True, "artifact_id": result["artifact_id"], "project_id": actual_project_id}

    except Exception as e:
        logger.error(f"❌ File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/autogen/run/start")
async def start_workflow(project_id: str, background_tasks: BackgroundTasks):
    """Start the AutoGen workflow for a project"""
    try:
        run_id = str(uuid.uuid4())
        logger.info(f"🚀 Starting AutoGen workflow for project {project_id}, run_id: {run_id}")

        # Initialize run tracking
        active_runs[run_id] = {
            "project_id": project_id,
            "status": "starting",
            "current_step": "INGEST",
            "events": []
        }
        logger.info(f"📊 Initialized run tracking for {run_id}")

        # Start workflow in background
        logger.info(f"⚡ Launching background workflow task...")
        background_tasks.add_task(run_autogen_workflow, project_id, run_id)

        logger.info(f"✅ Workflow started successfully, run_id: {run_id}")
        return {"success": True, "run_id": run_id}

    except Exception as e:
        logger.error(f"❌ Failed to start workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/autogen/run/continue")
async def continue_workflow(
    project_id: str,
    patch_id: str,
    action: str,  # "approve", "reject", "edit"
    edit_request: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """Continue workflow after HITL decision"""
    try:
        logger.info(f"👤 HITL Decision received - Action: {action}, Patch: {patch_id}, Project: {project_id}")

        if action == "edit" and edit_request:
            logger.info(f"✏️ Editing patch with LLM based on user request: {edit_request}")
            # Use LLM to edit the patch
            edited_patch = await orchestrator.edit_patch_with_llm(patch_id, edit_request)
            await db.update_patch_status(patch_id, "superseded")
            logger.info(f"📝 Original patch marked as superseded: {patch_id}")

            # Create new edited patch
            new_patch_id = await db.create_patch(
                project_id=project_id,
                source="edited_llm",
                patch_json=edited_patch,
                justification=f"Edited based on user request: {edit_request}"
            )
            patch_id = new_patch_id
            action = "approve"  # Auto-approve edited patch
            logger.info(f"✅ New edited patch created and auto-approved: {new_patch_id}")

        # Update patch status
        status = "approved" if action == "approve" else "rejected"
        await db.update_patch_status(patch_id, status)
        logger.info(f"📋 Patch status updated to: {status}")

        if action == "approve":
            # Continue workflow in background
            run_id = str(uuid.uuid4())
            logger.info(f"✅ Patch approved - continuing workflow with run_id: {run_id}")
            if background_tasks:
                background_tasks.add_task(continue_autogen_workflow, project_id, patch_id, run_id)
                logger.info(f"🚀 Background workflow continuation task launched")
        else:
            logger.info(f"❌ Patch rejected - workflow stopped")

        logger.info(f"🎯 HITL decision processed successfully")
        return {"success": True, "action": action, "patch_id": patch_id}

    except Exception as e:
        logger.error(f"❌ Failed to process HITL decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/artifact/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    """Download an artifact file"""
    try:
        logger.info(f"📥 Downloading artifact: {artifact_id}")

        # Get artifact data from database
        artifact = await db.get_artifact_content(artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        file_content = artifact.get("file_content")
        filename = artifact.get("filename", "unknown_file")
        mime_type = artifact.get("mime", "application/octet-stream")

        if not file_content:
            raise HTTPException(status_code=404, detail="File content not found")

        # Decode file content
        try:
            # Try base64 decode first
            file_bytes = base64.b64decode(file_content)
        except:
            # If base64 decode fails, assume it's plain text
            file_bytes = file_content.encode('utf-8')

        logger.info(f"✅ Artifact downloaded: {filename} ({len(file_bytes)} bytes)")

        return Response(
            content=file_bytes,
            media_type=mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download artifact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{run_id}")
async def stream_events(run_id: str):
    """Stream workflow events via SSE"""
    async def event_generator():
        while run_id in active_runs:
            run_data = active_runs[run_id]

            # Send current status
            event_data = {
                "run_id": run_id,
                "project_id": run_data["project_id"],
                "status": run_data["status"],
                "current_step": run_data["current_step"],
                "timestamp": datetime.utcnow().isoformat()
            }

            yield f"data: {json.dumps(event_data)}\n\n"

            # Check if run is complete
            if run_data["status"] in ["completed", "failed", "hitl_required"]:
                break

            await asyncio.sleep(1)  # Poll every second

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/project/{project_id}/status")
async def get_project_status(project_id: str):
    """Get current project status and any pending patches"""
    try:
        # Get latest snapshot
        snapshot = await db.get_latest_snapshot(project_id)

        # Get pending patches
        patches = await db.get_pending_patches(project_id)

        # Get active strategy
        strategy = await db.get_active_strategy(project_id)

        # Get campaigns and metrics
        campaigns = await db.get_campaigns(project_id)

        return {
            "project_id": project_id,
            "snapshot": snapshot,
            "pending_patches": patches,
            "active_strategy": strategy,
            "campaigns": campaigns
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def start_analysis_workflow(project_id: str):
    """Start the full analysis workflow"""
    run_id = str(uuid.uuid4())
    await run_autogen_workflow(project_id, run_id)

async def run_autogen_workflow(project_id: str, run_id: str):
    """Run the complete AutoGen workflow"""
    try:
        logger.info(f"🔄 [RUN {run_id[:8]}] Starting AutoGen workflow for project {project_id}")

        # Ensure project exists in database
        actual_project_id = await db.get_or_create_project(f"Project {project_id[:8]}")
        logger.info(f"📁 [RUN {run_id[:8]}] Project ensured: {actual_project_id}")

        # Update run status
        active_runs[run_id] = {
            "project_id": actual_project_id,
            "status": "running",
            "current_step": "INGEST",
            "events": []
        }
        logger.info(f"📊 [RUN {run_id[:8]}] Run tracking initialized - Status: running")

        # Log workflow start
        await db.log_step_event(actual_project_id, run_id, "WORKFLOW_START", "started")
        logger.info(f"🚀 [RUN {run_id[:8]}] WORKFLOW_START logged to database")

        # Step 1: INGEST - Get artifacts
        logger.info(f"📥 [RUN {run_id[:8]}] STEP 1: INGEST - Retrieving artifacts...")
        artifacts = await db.get_artifacts(actual_project_id)
        logger.info(f"📦 [RUN {run_id[:8]}] Retrieved {len(artifacts)} artifacts")

        # Step 2: FEATURES - Extract features
        logger.info(f"🔍 [RUN {run_id[:8]}] STEP 2: FEATURES - Starting feature extraction...")
        active_runs[run_id]["current_step"] = "FEATURES"
        await db.log_step_event(actual_project_id, run_id, "FEATURES", "started")

        features = await orchestrator.extract_features(artifacts)
        logger.info(f"✅ [RUN {run_id[:8]}] Feature extraction completed successfully")

        # Step 3: Store snapshot
        logger.info(f"💾 [RUN {run_id[:8]}] STEP 3: Storing analysis snapshot...")
        snapshot_id = await db.create_snapshot(actual_project_id, features)
        await db.log_step_event(actual_project_id, run_id, "FEATURES", "completed")
        logger.info(f"📸 [RUN {run_id[:8]}] Snapshot stored: {snapshot_id}")

        # Step 4: INSIGHTS - Generate insights
        logger.info(f"💡 [RUN {run_id[:8]}] STEP 4: INSIGHTS - Generating strategic insights...")
        active_runs[run_id]["current_step"] = "INSIGHTS"
        await db.log_step_event(actual_project_id, run_id, "INSIGHTS", "started")

        insights = await orchestrator.generate_insights(features)
        await db.log_step_event(actual_project_id, run_id, "INSIGHTS", "completed")
        logger.info(f"🧠 [RUN {run_id[:8]}] Insights generation completed")

        # Step 5: PATCH_PROPOSED - Create strategy patch
        logger.info(f"📝 [RUN {run_id[:8]}] STEP 5: PATCH_PROPOSED - Creating strategy patch...")
        active_runs[run_id]["current_step"] = "PATCH_PROPOSED"
        patch_id = await db.create_patch(
            project_id=actual_project_id,
            source="insights",
            patch_json=insights["patch"],
            justification=insights["justification"]
        )
        logger.info(f"📋 [RUN {run_id[:8]}] Strategy patch created: {patch_id}")

        # Set status to require human intervention
        active_runs[run_id]["status"] = "hitl_required"
        active_runs[run_id]["current_step"] = "HITL_PATCH"
        logger.info(f"⏸️ [RUN {run_id[:8]}] Workflow paused - awaiting human approval for patch")

        await db.log_step_event(actual_project_id, run_id, "PATCH_PROPOSED", "completed")
        logger.info(f"✅ [RUN {run_id[:8]}] PATCH_PROPOSED phase completed - workflow awaiting HITL")

    except Exception as e:
        logger.error(f"❌ [RUN {run_id[:8]}] Workflow failed: {str(e)}")
        active_runs[run_id]["status"] = "failed"
        active_runs[run_id]["error"] = str(e)
        # Use the actual_project_id if available, otherwise fallback to original project_id
        project_id_for_error = active_runs[run_id].get("project_id", project_id)
        await db.log_step_event(project_id_for_error, run_id, "WORKFLOW_ERROR", "failed")
        logger.error(f"🔥 [RUN {run_id[:8]}] Error logged to database")

async def continue_autogen_workflow(project_id: str, patch_id: str, run_id: str):
    """Continue workflow after patch approval"""
    try:
        logger.info(f"▶️ [RUN {run_id[:8]}] Continuing workflow after patch approval: {patch_id}")

        active_runs[run_id] = {
            "project_id": project_id,
            "status": "running",
            "current_step": "APPLY",
            "events": []
        }
        logger.info(f"📊 [RUN {run_id[:8]}] Run tracking reinitialized - Status: running")

        # Get the approved patch
        logger.info(f"🔍 [RUN {run_id[:8]}] Retrieving approved patch: {patch_id}")
        patch = await db.get_patch(patch_id)
        logger.info(f"📋 [RUN {run_id[:8]}] Patch retrieved successfully")

        # Step 6: APPLY - Apply patch to strategy
        logger.info(f"🔧 [RUN {run_id[:8]}] STEP 6: APPLY - Applying patch to strategy...")
        active_runs[run_id]["current_step"] = "APPLY"
        await db.log_step_event(project_id, run_id, "APPLY", "started")

        strategy = await orchestrator.apply_patch(project_id, patch["patch_data"])
        strategy_id = await db.create_strategy_version(project_id, strategy)
        await db.set_active_strategy(project_id, strategy_id)
        logger.info(f"✅ [RUN {run_id[:8]}] Strategy applied and activated: {strategy_id}")

        await db.log_step_event(project_id, run_id, "APPLY", "completed")

        # Step 7: BRIEF - Compile brief
        logger.info(f"📄 [RUN {run_id[:8]}] STEP 7: BRIEF - Compiling marketing brief...")
        active_runs[run_id]["current_step"] = "BRIEF"
        await db.log_step_event(project_id, run_id, "BRIEF", "started")

        brief = await orchestrator.compile_brief(strategy)
        brief_id = await db.create_brief(strategy_id, brief)
        logger.info(f"📝 [RUN {run_id[:8]}] Brief compiled and stored: {brief_id}")

        await db.log_step_event(project_id, run_id, "BRIEF", "completed")

        # Step 8: CAMPAIGN_RUN - Auto-launch campaign
        logger.info(f"🚀 [RUN {run_id[:8]}] STEP 8: CAMPAIGN_RUN - Launching marketing campaign...")
        active_runs[run_id]["current_step"] = "CAMPAIGN_RUN"
        await db.log_step_event(project_id, run_id, "CAMPAIGN_RUN", "started")

        campaign = await orchestrator.launch_campaign(brief)
        campaign_id = await db.create_campaign(project_id, strategy_id, campaign)
        logger.info(f"📢 [RUN {run_id[:8]}] Campaign launched: {campaign_id}")

        await db.log_step_event(project_id, run_id, "CAMPAIGN_RUN", "completed")

        # Step 9: COLLECT - Start metrics collection
        logger.info(f"📊 [RUN {run_id[:8]}] STEP 9: COLLECT - Starting metrics collection...")
        active_runs[run_id]["current_step"] = "COLLECT"
        await orchestrator.start_metrics_collection(campaign_id)
        logger.info(f"📈 [RUN {run_id[:8]}] Metrics collection initiated")

        # Step 10: ANALYZE - Wait and analyze (simulated)
        logger.info(f"⏳ [RUN {run_id[:8]}] STEP 10: Simulating campaign runtime (5 seconds)...")
        await asyncio.sleep(5)  # Simulate campaign running

        logger.info(f"🔍 [RUN {run_id[:8]}] STEP 11: ANALYZE - Analyzing campaign performance...")
        active_runs[run_id]["current_step"] = "ANALYZE"
        analysis = await orchestrator.analyze_performance(campaign_id)
        logger.info(f"📊 [RUN {run_id[:8]}] Performance analysis completed")

        # Step 12: REFLECTION_PATCH_PROPOSED - If issues detected
        if analysis.get("needs_adjustment"):
            logger.info(f"⚠️ [RUN {run_id[:8]}] STEP 12: Issues detected - creating reflection patch...")
            reflection_patch_id = await db.create_patch(
                project_id=project_id,
                source="reflection",
                patch_json=analysis["patch"],
                justification=analysis["justification"]
            )
            logger.info(f"🔄 [RUN {run_id[:8]}] Reflection patch created: {reflection_patch_id}")

            active_runs[run_id]["status"] = "hitl_required"
            active_runs[run_id]["current_step"] = "HITL_REFLECTION"
            logger.info(f"⏸️ [RUN {run_id[:8]}] Workflow paused - awaiting human review of reflection patch")
        else:
            logger.info(f"✅ [RUN {run_id[:8]}] Campaign performing well - no adjustments needed")
            active_runs[run_id]["status"] = "completed"
            active_runs[run_id]["current_step"] = "COMPLETED"
            logger.info(f"🎉 [RUN {run_id[:8]}] Workflow completed successfully!")

        await db.log_step_event(project_id, run_id, "WORKFLOW_COMPLETE", "completed")
        logger.info(f"✅ [RUN {run_id[:8]}] Workflow completion logged to database")

    except Exception as e:
        logger.error(f"❌ [RUN {run_id[:8]}] Continue workflow failed: {str(e)}")
        active_runs[run_id]["status"] = "failed"
        active_runs[run_id]["error"] = str(e)
        await db.log_step_event(project_id, run_id, "WORKFLOW_ERROR", "failed")
        logger.error(f"🔥 [RUN {run_id[:8]}] Error logged to database")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))