from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from services import bigquery, storage
import os

from workers.jobs import sync_job, analysis_job

router = APIRouter(prefix="/api/factory", tags=["factory"])

# --- Request Models ---

class VideoItem(BaseModel):
    source_type: str
    uri: str
    lap_hint: Optional[str] = None
    anchors_text: Optional[str] = None

class VideoSyncRequest(BaseModel):
    track_id: str
    videos: List[VideoItem]

class LapCompareRequest(BaseModel):
    track_id: str
    lap_id_ref: str
    sync_id_ref: str
    sync_id_sim: str
    lap_a: str
    lap_b: Optional[str] = None # Synthetic if missing

class CausalDiagnosisRequest(BaseModel):
    comparison_id: str
    model_version: str

class TelemetryAnalysisRequest(BaseModel):
    video_uri: str

# --- Endpoints ---


@router.post("/upload")
async def upload_video(file: UploadFile = File(...), type: str = "misc"):
    """
    Uploads a video file to GCS and returns the gs URI.
    Type can be "REF" or "SIM" to organize folders.
    """
    try:
        subfolder = "misc"
        use_timestamp = False
        
        if type == "REF":
            subfolder = "reference"
        elif type == "SIM":
            subfolder = "sim"
        elif type == "DASHBOARD":
            subfolder = "dashboard"
            use_timestamp = True
            
        # File is a SpooledTemporaryFile
        uri = storage.upload_file(file.file, file.filename, subfolder=subfolder, use_timestamp=use_timestamp)
        return {"uri": uri}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/verify-sync")
async def start_verification(body: VideoSyncRequest, background_tasks: BackgroundTasks):
    """
    Starts the video verification process (Time-based sync check).
    """
    # Create run record
    input_data = body.model_dump()
    run_id = bigquery.insert_factory_run(
        run_type="VIDEO_VERIFICATION",
        status="QUEUED",
        input_json=input_data
    )
    
    # Trigger background job
    # Note: We reuse analysis_job for this new verification flow
    background_tasks.add_task(analysis_job.run_verification_job, run_id, input_data)
    
    return {"run_id": run_id}

@router.post("/lap-compare")
async def start_lap_compare(body: LapCompareRequest, background_tasks: BackgroundTasks):
    input_data = body.model_dump()
    # Default lap_b to a generated ID if not provided (logic handled in job or here)
    if not input_data.get("lap_b"):
        input_data["lap_b"] = f"sim_gen_{input_data['sync_id_sim']}"
        
    run_id = bigquery.insert_factory_run(
        run_type="LAP_COMPARE",
        status="QUEUED",
        input_json=input_data
    )
    
    background_tasks.add_task(analysis_job.run_compare_job, run_id, input_data)
    
    return {"run_id": run_id}

@router.post("/causal-diagnosis")
async def start_causal_diagnosis(body: CausalDiagnosisRequest, background_tasks: BackgroundTasks):
    input_data = body.model_dump()
    run_id = bigquery.insert_factory_run(
        run_type="CAUSAL_DIAGNOSIS",
        status="QUEUED",
        input_json=input_data
    )
    
    background_tasks.add_task(analysis_job.run_diagnosis_job, run_id, input_data)
    
    return {"run_id": run_id}

@router.get("/videos")
async def list_dashboard_videos():
    """
    Lists available videos in the dashboard upload folder.
    """
    try:
        # Listing from the 'uploads/dashboard' prefix where we put them
        videos = storage.list_files(subfolder="uploads/dashboard")
        return {"videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/telemetry-analysis")
async def start_telemetry_analysis(body: TelemetryAnalysisRequest, background_tasks: BackgroundTasks):
    input_data = body.model_dump()
    run_id = bigquery.insert_factory_run(
        run_type="TELEMETRY_ANALYSIS",
        status="QUEUED",
        input_json=input_data
    )
    
    background_tasks.add_task(analysis_job.run_telemetry_job, run_id, input_data)
    
    return {"run_id": run_id}

@router.get("/telemetry-logs/{run_id}")
async def get_telemetry_logs(run_id: str):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "dashboard")
    log_file = os.path.join(log_dir, f"{run_id}.log")
    
    if not os.path.exists(log_file):
        return {"logs": []}
        
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        return {"logs": [l.strip() for l in lines]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

@router.get("/run")
async def get_run_status(run_id: str):
    run = bigquery.get_factory_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
