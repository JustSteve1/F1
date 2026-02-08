from services import bigquery
from services.gemini.skills import video_track_sync
import traceback

def run_sync_job(run_id: str, input_json: dict):
    """
    Executes the sync job for a list of videos.
    Updates the factory_run status.
    """
    try:
        bigquery.update_factory_run(run_id, status="RUNNING")
        
        track_id = input_json.get("track_id")
        videos = input_json.get("videos", [])
        
        results = []
        
        for v in videos:
            # Execute skill
            # {track_id, source_type, video_uri, lap_hint?, anchors_text?}
            out = video_track_sync.run_sync(
                track_id=track_id,
                source_type=v.get("source_type"),
                video_uri=v.get("uri"),
                lap_hint=v.get("lap_hint"),
                anchors_text=v.get("anchors_text")
            )
            
            # Combine input metadata with output IDs
            item_result = {
                "source_type": v.get("source_type"),
                "video_id": out.get("video_id"),
                "sync_id": out.get("sync_id")
            }
            results.append(item_result)
            
        # Update run with success
        bigquery.update_factory_run(run_id, status="DONE", output_refs_json={"items": results})
        
    except Exception as e:
        # Capture error
        err_msg = f"Sync Job Failed: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        bigquery.update_factory_run(run_id, status="ERROR", error=str(e))
