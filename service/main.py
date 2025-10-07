from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
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
import time

# Configure comprehensive logging with debug level for LLM interactions
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG_LLM", "false").lower() == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('/tmp/adronaut_service.log', mode='a') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)

# Set specific loggers for detailed LLM debugging
logger = logging.getLogger(__name__)
gemini_logger = logging.getLogger('gemini_orchestrator')
db_logger = logging.getLogger('database')

# Enable DEBUG level for LLM interactions when DEBUG_LLM is set
if os.getenv("DEBUG_LLM", "false").lower() == "true":
    gemini_logger.setLevel(logging.DEBUG)
    db_logger.setLevel(logging.DEBUG)
    logger.info("🔍 DEBUG_LLM enabled - Full LLM request/response logging activated")
else:
    logger.info("ℹ️ Standard logging level - Set DEBUG_LLM=true for detailed LLM logging")

from gemini_orchestrator import GeminiOrchestrator as CrewAIOrchestrator
from database import Database
from file_processor import FileProcessor

load_dotenv()

app = FastAPI(title="Adronaut AutoGen Service", version="1.0.0")

# HTTP request/response logging middleware
class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log incoming request
        logger.info(f"🌐 [HTTP IN] {request.method} {request.url.path}")

        try:
            # Process request
            logger.info(f"🔄 [HTTP MIDDLEWARE] Calling endpoint handler...")
            response = await call_next(request)
            logger.info(f"✅ [HTTP MIDDLEWARE] Endpoint handler returned response")

            # Log outgoing response
            duration = (time.time() - start_time) * 1000
            logger.info(f"🌐 [HTTP OUT] {request.method} {request.url.path} → {response.status_code} ({duration:.0f}ms)")

            return response
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"❌ [HTTP MIDDLEWARE] Exception in middleware: {e}")
            logger.error(f"🔍 [HTTP MIDDLEWARE] Request: {request.method} {request.url.path} ({duration:.0f}ms)")
            raise

app.add_middleware(HTTPLoggingMiddleware)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development (default)
        "http://localhost:3004",  # Local development (custom port)
        "http://localhost:3001",  # Local development (alternative)
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
    """Upload and process a file artifact (legacy method with DB storage)"""
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

@app.post("/upload-direct")
async def upload_file_direct(
    project_id: str,
    file: UploadFile = File(...),
    process_immediately: bool = True
):
    """Upload and process file with direct LLM processing (faster, no DB roundtrip)"""
    try:
        logger.info(f"⚡ Starting DIRECT file upload: {file.filename} for project {project_id[:8]}")

        # Ensure project exists in database
        actual_project_id = await db.get_or_create_project(f"Project {project_id[:8]}")
        logger.info(f"📁 Project ensured: {actual_project_id}")

        # Extract content directly from file (no disk storage)
        logger.info(f"🔍 Extracting content directly from memory: {file.filename} ({file.content_type})")
        file_data = await file_processor.extract_content_direct(file)
        logger.info(f"✅ Content extracted successfully - {file_data['file_size']} bytes")

        if process_immediately:
            # Process with LLM immediately (no DB read)
            logger.info(f"🤖 Processing with LLM directly from memory...")
            features = await orchestrator.extract_features_direct(file_data)
            logger.info(f"✅ LLM processing completed successfully")

            # Store artifact with features for future reference
            logger.info(f"💾 Storing artifact with pre-computed features...")
            artifact_id = str(uuid.uuid4())

            # Prepare file storage (still store for later access)
            file_content, storage_url = await file_processor._prepare_file_storage(
                file_data["raw_content"],
                file_data["content_type"],
                actual_project_id,
                file_data["filename"]
            )

            await db.create_artifact(
                project_id=actual_project_id,
                filename=file_data["filename"],
                mime=file_data["content_type"],
                storage_url=storage_url,
                file_content=file_content,
                file_size=file_data["file_size"],
                summary_json=features  # Store the LLM-processed features
            )
            logger.info(f"✅ Artifact stored with pre-computed features")

            return {
                "success": True,
                "artifact_id": artifact_id,
                "project_id": actual_project_id,
                "features": features,
                "processing_time": "immediate",
                "method": "direct_llm_processing"
            }
        else:
            # Just store the file for later processing
            artifact_id = str(uuid.uuid4())
            file_content, storage_url = await file_processor._prepare_file_storage(
                file_data["raw_content"],
                file_data["content_type"],
                actual_project_id,
                file_data["filename"]
            )

            await db.create_artifact(
                project_id=actual_project_id,
                filename=file_data["filename"],
                mime=file_data["content_type"],
                storage_url=storage_url,
                file_content=file_content,
                file_size=file_data["file_size"],
                summary_json={"extracted_content": file_data["extracted_content"][:1000]}
            )

            return {
                "success": True,
                "artifact_id": artifact_id,
                "project_id": actual_project_id,
                "method": "deferred_processing"
            }

    except Exception as e:
        logger.error(f"❌ Direct file upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/autogen/run/start")
async def start_workflow(project_id: str):
    """Start the AutoGen workflow for a project"""
    logger.info(f"🎬 [ENDPOINT] /autogen/run/start called with project_id: {project_id}")
    try:
        run_id = str(uuid.uuid4())
        logger.info(f"🚀 [ENDPOINT] Starting AutoGen workflow for project {project_id}, run_id: {run_id}")

        # Initialize run tracking
        logger.info(f"📝 [ENDPOINT] Initializing run tracking...")
        active_runs[run_id] = {
            "project_id": project_id,
            "status": "starting",
            "current_step": "INGEST",
            "events": []
        }
        logger.info(f"📊 [ENDPOINT] Initialized run tracking for {run_id}")

        # Start workflow in background using asyncio.create_task (truly non-blocking)
        logger.info(f"⚡ [ENDPOINT] Launching background workflow task with asyncio...")
        asyncio.create_task(run_autogen_workflow(project_id, run_id))
        logger.info(f"✅ [ENDPOINT] Background task launched successfully")

        response_data = {"success": True, "run_id": run_id}
        logger.info(f"📤 [ENDPOINT] Returning response: {response_data}")

        # Use explicit JSONResponse with headers to work around Railway proxy issues
        return JSONResponse(
            content=response_data,
            status_code=200,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Content-Type-Options": "nosniff",
                "Content-Type": "application/json"
            }
        )

    except Exception as e:
        logger.error(f"❌ [ENDPOINT] Failed to start workflow: {str(e)}")
        import traceback
        logger.error(f"🔍 [ENDPOINT] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/autogen/run/continue")
async def continue_workflow(
    project_id: str,
    patch_id: str,
    action: str,  # "approve", "reject", "edit"
    edit_request: Optional[str] = None
):
    """Continue workflow after HITL decision"""
    try:
        logger.info(f"👤 HITL Decision received - Action: {action}, Patch: {patch_id}, Project: {project_id}")

        if action == "edit" and edit_request:
            logger.info(f"✏️ Editing patch with LLM based on user request: {edit_request}")
            logger.info(f"🤖 LLM REQUEST: Patch editing")
            logger.info(f"   📝 Edit request: '{edit_request}'")
            logger.info(f"   🔧 Original patch ID: {patch_id}")

            # Use LLM to edit the patch
            edited_patch = await orchestrator.edit_patch_with_llm(patch_id, edit_request)

            logger.info(f"✅ LLM RESPONSE: Patch editing completed")
            if isinstance(edited_patch, dict):
                logger.info(f"📋 Edited patch summary:")
                for key, value in edited_patch.items():
                    if key == "error":
                        logger.error(f"   ❌ {key}: {value}")
                    elif isinstance(value, (list, dict)):
                        logger.info(f"   ✓ {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        logger.info(f"   ✓ {key}: {str(value)[:100]}...")
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
            # Continue workflow in background using asyncio
            run_id = str(uuid.uuid4())
            logger.info(f"✅ Patch approved - continuing workflow with run_id: {run_id}")
            asyncio.create_task(continue_autogen_workflow(project_id, patch_id, run_id))
            logger.info(f"🚀 Background workflow continuation task launched")
        else:
            logger.info(f"❌ Patch rejected - workflow stopped")

        logger.info(f"🎯 HITL decision processed successfully")
        return {"success": True, "action": action, "patch_id": patch_id}

    except Exception as e:
        logger.error(f"❌ Failed to process HITL decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/autogen/run/status/{run_id}")
async def get_workflow_status(run_id: str):
    """Get the current status of a workflow run"""
    try:
        logger.info(f"📊 Checking workflow status: {run_id}")

        if run_id not in active_runs:
            logger.warning(f"⚠️ Run ID not found in active runs: {run_id}")
            raise HTTPException(status_code=404, detail="Workflow run not found")

        run_data = active_runs[run_id]
        status_info = {
            "run_id": run_id,
            "status": run_data.get("status", "unknown"),
            "current_step": run_data.get("current_step", "unknown"),
            "project_id": run_data.get("project_id"),
            "created_at": run_data.get("created_at"),
            "error": run_data.get("error"),
            "error_type": run_data.get("error_type")
        }

        logger.info(f"✅ Status retrieved for {run_id}: {status_info['status']} - {status_info['current_step']}")
        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow status: {str(e)}")
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
    logger.info(f"📡 SSE connection requested for run_id: {run_id}")

    # Check if run exists
    if run_id not in active_runs:
        logger.warning(f"⚠️ SSE connection attempted for unknown run_id: {run_id}")
        logger.info(f"📊 Active runs: {list(active_runs.keys())}")
        # Return a 404 response instead of streaming
        raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found in active runs")

    logger.info(f"✅ SSE connection established for run_id: {run_id}")

    async def event_generator():
        event_count = 0
        while run_id in active_runs:
            run_data = active_runs[run_id]
            event_count += 1

            # Send current status
            event_data = {
                "run_id": run_id,
                "project_id": run_data["project_id"],
                "status": run_data["status"],
                "current_step": run_data["current_step"],
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(f"📨 SSE Event #{event_count} for {run_id[:8]}: {run_data['status']} - {run_data['current_step']}")
            yield f"data: {json.dumps(event_data)}\n\n"

            # Check if run is complete
            if run_data["status"] in ["completed", "failed", "hitl_required"]:
                logger.info(f"🏁 SSE stream ending for {run_id[:8]}: status={run_data['status']}")
                break

            await asyncio.sleep(1)  # Poll every second

        if run_id not in active_runs:
            logger.warning(f"⚠️ SSE stream ended: run_id {run_id[:8]} removed from active_runs")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
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
        logger.info(f"🎯 [RUN {run_id[:8]}] AI Provider: {'Gemini 2.5 Pro' if orchestrator.use_gemini else 'OpenAI GPT-4o'}")
        logger.info(f"⚙️ [RUN {run_id[:8]}] Workflow configuration:")
        logger.info(f"   - Database URL: {db.url[:50] if db.url else 'None'}...")
        logger.info(f"   - Database connected: {db.client is not None}")
        logger.info(f"   - Orchestrator type: {type(orchestrator).__name__}")

        # Use the project_id directly (frontend manages project creation)
        actual_project_id = project_id
        logger.info(f"📁 [RUN {run_id[:8]}] Using project_id: {actual_project_id}")

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

        if len(artifacts) == 0:
            logger.error(f"❌ [RUN {run_id[:8]}] No artifacts found for project {actual_project_id}")
            raise Exception(f"No artifacts found for project {actual_project_id}. Please upload files first.")

        # Step 2: FEATURES - Extract features
        logger.info(f"🔍 [RUN {run_id[:8]}] STEP 2: FEATURES - Starting feature extraction...")
        active_runs[run_id]["current_step"] = "FEATURES"
        await db.log_step_event(actual_project_id, run_id, "FEATURES", "started")

        logger.info(f"🤖 [RUN {run_id[:8]}] LLM REQUEST: Feature extraction")
        logger.info(f"📊 [RUN {run_id[:8]}] Input data: {len(artifacts)} artifacts")
        for i, artifact in enumerate(artifacts):
            logger.info(f"   📄 Artifact {i+1}: {artifact.get('filename', 'unknown')} ({artifact.get('mime', 'unknown')} - {artifact.get('file_size', 0)} bytes)")

        features = await orchestrator.extract_features(artifacts)

        logger.info(f"✅ [RUN {run_id[:8]}] LLM RESPONSE: Feature extraction completed")
        logger.info(f"📋 [RUN {run_id[:8]}] Extracted features summary:")
        if isinstance(features, dict):
            for key, value in features.items():
                if key == "error":
                    logger.error(f"   ❌ {key}: {value}")
                elif isinstance(value, (list, dict)):
                    logger.info(f"   ✓ {key}: {type(value).__name__} with {len(value)} items")
                else:
                    logger.info(f"   ✓ {key}: {str(value)[:100]}...")
        else:
            logger.warning(f"⚠️ [RUN {run_id[:8]}] Unexpected features format: {type(features)}")

        # Step 3: Store snapshot
        logger.info(f"💾 [RUN {run_id[:8]}] STEP 3: Storing analysis snapshot...")
        snapshot_id = await db.create_snapshot(actual_project_id, features)
        await db.log_step_event(actual_project_id, run_id, "FEATURES", "completed")
        logger.info(f"📸 [RUN {run_id[:8]}] Snapshot stored: {snapshot_id}")

        # Step 4: INSIGHTS - Generate insights
        logger.info(f"💡 [RUN {run_id[:8]}] STEP 4: INSIGHTS - Generating strategic insights...")
        active_runs[run_id]["current_step"] = "INSIGHTS"
        await db.log_step_event(actual_project_id, run_id, "INSIGHTS", "started")

        logger.info(f"🤖 [RUN {run_id[:8]}] LLM REQUEST: Strategic insights generation")
        logger.info(f"📊 [RUN {run_id[:8]}] Input: features from previous step")
        if isinstance(features, dict):
            logger.info(f"   📋 Features keys: {list(features.keys())}")

        insights = await orchestrator.generate_insights(features)

        logger.info(f"✅ [RUN {run_id[:8]}] LLM RESPONSE: Strategic insights completed")
        logger.info(f"🧠 [RUN {run_id[:8]}] Generated insights summary:")
        if isinstance(insights, dict):
            for key, value in insights.items():
                if key == "error":
                    logger.error(f"   ❌ {key}: {value}")
                elif key == "patch":
                    logger.info(f"   🔧 {key}: Strategy patch generated")
                elif isinstance(value, (list, dict)):
                    logger.info(f"   ✓ {key}: {type(value).__name__} with {len(value)} items")
                else:
                    logger.info(f"   ✓ {key}: {str(value)[:100]}...")

        await db.log_step_event(actual_project_id, run_id, "INSIGHTS", "completed")

        # Update snapshot with insights
        logger.info(f"💾 [RUN {run_id[:8]}] Updating analysis snapshot with insights...")
        combined_snapshot = {**features, **insights}
        snapshot_id = await db.create_snapshot(actual_project_id, combined_snapshot)
        logger.info(f"📸 [RUN {run_id[:8]}] Snapshot updated with insights: {snapshot_id}")

        # Step 5: PATCH_PROPOSED - Create strategy patch
        logger.info(f"📝 [RUN {run_id[:8]}] STEP 5: PATCH_PROPOSED - Creating strategy patch...")
        active_runs[run_id]["current_step"] = "PATCH_PROPOSED"

        # Log patch details before storing
        patch_data = insights.get("patch", {})
        justification = insights.get("justification", "No justification provided")
        logger.info(f"🔧 [RUN {run_id[:8]}] Patch details:")
        logger.info(f"   📄 Justification: {justification[:200]}...")
        if isinstance(patch_data, dict):
            logger.info(f"   🛠️ Patch keys: {list(patch_data.keys())}")
            for key, value in patch_data.items():
                if isinstance(value, (dict, list)):
                    logger.info(f"      - {key}: {type(value).__name__} with {len(value)} items")
                else:
                    logger.info(f"      - {key}: {str(value)[:100]}...")

        patch_id = await db.create_patch(
            project_id=actual_project_id,
            source="insights",
            patch_json=patch_data,
            justification=justification
        )
        logger.info(f"📋 [RUN {run_id[:8]}] Strategy patch created and stored in database: {patch_id}")

        # Set status to require human intervention
        active_runs[run_id]["status"] = "hitl_required"
        active_runs[run_id]["current_step"] = "HITL_PATCH"
        logger.info(f"⏸️ [RUN {run_id[:8]}] Workflow paused - awaiting human approval for patch")

        await db.log_step_event(actual_project_id, run_id, "PATCH_PROPOSED", "completed")
        logger.info(f"✅ [RUN {run_id[:8]}] PATCH_PROPOSED phase completed - workflow awaiting HITL")

    except Exception as e:
        logger.error(f"❌ [RUN {run_id[:8]}] Workflow failed: {str(e)}")
        logger.error(f"🔍 [RUN {run_id[:8]}] Error details:")
        logger.error(f"   - Error type: {type(e).__name__}")
        logger.error(f"   - Error message: {str(e)}")
        logger.error(f"   - Current step: {active_runs[run_id].get('current_step', 'unknown')}")
        import traceback
        logger.error(f"   - Traceback: {traceback.format_exc()}")

        active_runs[run_id]["status"] = "failed"
        active_runs[run_id]["error"] = str(e)
        active_runs[run_id]["error_type"] = type(e).__name__
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

        logger.info(f"🤖 [RUN {run_id[:8]}] LLM REQUEST: Performance analysis")
        logger.info(f"   🎯 Campaign ID: {campaign_id}")

        analysis = await orchestrator.analyze_performance(campaign_id)

        logger.info(f"✅ [RUN {run_id[:8]}] LLM RESPONSE: Performance analysis completed")
        logger.info(f"📊 [RUN {run_id[:8]}] Analysis results:")
        if isinstance(analysis, dict):
            for key, value in analysis.items():
                if key == "error":
                    logger.error(f"   ❌ {key}: {value}")
                elif key == "needs_adjustment":
                    logger.info(f"   ⚠️ {key}: {value}")
                elif key == "performance_summary":
                    logger.info(f"   📈 {key}: {value}")
                elif isinstance(value, (list, dict)):
                    logger.info(f"   ✓ {key}: {type(value).__name__} with {len(value)} items")
                else:
                    logger.info(f"   ✓ {key}: {str(value)[:100]}...")

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
        logger.error(f"🔍 [RUN {run_id[:8]}] Error details:")
        logger.error(f"   - Error type: {type(e).__name__}")
        logger.error(f"   - Error message: {str(e)}")
        logger.error(f"   - Current step: {active_runs[run_id].get('current_step', 'unknown')}")
        logger.error(f"   - Project ID: {project_id}")
        logger.error(f"   - Patch ID: {patch_id}")
        import traceback
        logger.error(f"   - Traceback: {traceback.format_exc()}")

        active_runs[run_id]["status"] = "failed"
        active_runs[run_id]["error"] = str(e)
        active_runs[run_id]["error_type"] = type(e).__name__
        await db.log_step_event(project_id, run_id, "WORKFLOW_ERROR", "failed")
        logger.error(f"🔥 [RUN {run_id[:8]}] Error logged to database")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))