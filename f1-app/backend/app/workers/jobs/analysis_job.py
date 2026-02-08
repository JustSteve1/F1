from services import bigquery
from services.gemini.skills import lap_compare, causal_diagnosis
import traceback

from services.gemini.skills import video_track_sync, video_telemetry

def run_telemetry_job(run_id: str, input_json: dict):
    """
    Executes the telemetry analysis job.
    """
    try:
        bigquery.update_factory_run(run_id, status="RUNNING")
        
        # input_json: { video_uri: "..." }
        video_uri = input_json.get("video_uri")
        if not video_uri:
            raise ValueError("Missing video_uri")
            
        # Call the skill with run_id for logging
        result = video_telemetry.analyze_video(video_uri, run_id=run_id)
        
        # Check for error in result
        if "error" in result:
             raise Exception(result["error"])
             
        bigquery.update_factory_run(run_id, status="DONE", output_refs_json=result)
        
    except Exception as e:
        err_msg = f"Telemetry Job Failed: {str(e)}\n{traceback.format_exc()}"
        print(err_msg, flush=True)
        try:
             with open("error.log", "a") as f:
                 f.write(f"\n--- Analysis Job Error ({run_id}) ---\n{err_msg}\n")
        except:
            pass
        bigquery.update_factory_run(run_id, status="ERROR", error=str(e))


def run_verification_job(run_id: str, input_json: dict):
    """
    Executes the video verification job (Time-based Sync).
    Samples videos at 30s increments and reads the time.
    """
    try:
        bigquery.update_factory_run(run_id, status="RUNNING")
        
        # input_json: { videos: [{type: REF, uri: ...}, {type: SIM, uri: ...}] }
        videos = input_json.get("videos", [])
        ref_video = next((v for v in videos if v["source_type"] == "F1_REAL"), None)
        sim_video = next((v for v in videos if v["source_type"] == "SIM"), None)
        
        if not ref_video or not sim_video:
             raise ValueError("Missing Reference or Sim video")
             
        # Mocking the 30s increments for MVP
        # In a real app, we would use ffmpeg to get duration.
        # Here we will just sample 0, 30, 60, 90.
        timestamps = [0, 30, 60, 90] 
        results = []
        
        for t in timestamps:
            t_label = f"0:{t:02d}" if t < 60 else f"1:{t-60:02d}"
            
            # Call Gemini to read time (Conceptually passing timestamp)
            # Since our basic skill just takes the file, we will pass the hint
            
            # Ref
            ref_time = video_track_sync.analyze_video_timer(ref_video["uri"], f"{t_label} (Frame {t})")
            
            # Sim
            sim_time = video_track_sync.analyze_video_timer(sim_video["uri"], f"{t_label} (Frame {t})")
            
            results.append({
                "timestamp": t,
                "label": t_label,
                "ref_time_read": ref_time,
                "sim_time_read": sim_time,
                # Simple string delta calc could be done here if format is clean
            })
            
        bigquery.update_factory_run(run_id, status="DONE", output_refs_json={"items": results})
        
    except Exception as e:
        err_msg = f"Verification Job Failed: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        bigquery.update_factory_run(run_id, status="ERROR", error=str(e))

def run_compare_job(run_id: str, input_json: dict):
    """
    Executes the lap comparison job.
    """
    try:
        bigquery.update_factory_run(run_id, status="RUNNING")
        
        # {track_id, lap_a, lap_b, sync_id_ref, sync_id_sim, lap_id_ref, sim_lap_id?}
        # The input matches API contract.
        
        out = lap_compare.run_compare(
            track_id=input_json.get("track_id"),
            lap_a_id=input_json.get("lap_a"),
            lap_b_id=input_json.get("lap_b"),
            sync_id_ref=input_json.get("sync_id_ref"),
            sync_id_sim=input_json.get("sync_id_sim")
        )
        
        # Update run with success
        bigquery.update_factory_run(run_id, status="DONE", output_refs_json=out)
        
    except Exception as e:
        err_msg = f"Compare Job Failed: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        bigquery.update_factory_run(run_id, status="ERROR", error=str(e))

def run_diagnosis_job(run_id: str, input_json: dict):
    """
    Executes the causal diagnosis job.
    """
    try:
        bigquery.update_factory_run(run_id, status="RUNNING")
        
        # {comparison_id, model_version}
        out = causal_diagnosis.run_diagnosis(
            comparison_id=input_json.get("comparison_id"),
            model_version=input_json.get("model_version")
        )
        
        bigquery.update_factory_run(run_id, status="DONE", output_refs_json=out)
        
    except Exception as e:
        err_msg = f"Diagnosis Job Failed: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        bigquery.update_factory_run(run_id, status="ERROR", error=str(e))
