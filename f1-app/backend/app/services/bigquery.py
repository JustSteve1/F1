from google.cloud import bigquery
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

# Client will be instantiated on first use or at module level
# Using a global client for simplicity in this MVP
try:
    client = bigquery.Client()
except Exception as e:
    print(f"Warning: BigQuery client could not be initialized locally: {e}")
    client = None

DATASET_ID = "f1-data-library.f1_fan"

def _get_client():
    global client
    if client is None:
        client = bigquery.Client()
    return client

def _to_json_string(data: Any) -> Optional[str]:
    """Helper to convert dict/list to JSON string for BQ STRING fields provided as JSON."""
    if data is None:
        return None
    if isinstance(data, str):
        return data
    return json.dumps(data)

def insert_video_asset(source_type: str, track_id: str, uri: str, fps: Optional[float] = None, duration_ms: Optional[int] = None) -> str:
    video_id = str(uuid.uuid4())
    rows = [{
        "video_id": video_id,
        "source_type": source_type,
        "track_id": track_id,
        "uri": uri,
        "fps": fps,
        "duration_ms": duration_ms,
        "created_at": datetime.utcnow().isoformat()
    }]
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.video_assets", rows)
    if errors:
        raise RuntimeError(f"BQ Insert Error (video_assets): {errors}")
    return video_id

def insert_lap_sync_map(video_id: str, lap_id: Optional[str], track_id: str, anchors_json: dict, mapping_json: dict, quality_score: float) -> str:
    sync_id = str(uuid.uuid4())
    rows = [{
        "sync_id": sync_id,
        "video_id": video_id,
        "lap_id": lap_id,
        "track_id": track_id,
        "anchors_json": _to_json_string(anchors_json),
        "mapping_json": _to_json_string(mapping_json),
        "quality_score": quality_score,
        "created_at": datetime.utcnow().isoformat()
    }]
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.lap_sync_map", rows)
    if errors:
        raise RuntimeError(f"BQ Insert Error (lap_sync_map): {errors}")
    return sync_id

def insert_lap_events(events: List[dict]) -> None:
    if not events:
        return
    rows = []
    for e in events:
        # Generate event_id if not present, though usually caller might not have it
        if "event_id" not in e:
            e["event_id"] = str(uuid.uuid4())
        
        # Ensure meta_json is stringified
        if "meta_json" in e and not isinstance(e["meta_json"], str):
             e["meta_json"] = _to_json_string(e["meta_json"])
             
        rows.append(e)
        
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.lap_events", rows)
    if errors:
        raise RuntimeError(f"BQ Insert Error (lap_events): {errors}")

def insert_lap_comparison(lap_a: str, lap_b: str, track_id: str, delta_series_json: dict, corner_deltas_json: dict, coach_cards_json: List[dict]) -> str:
    comparison_id = str(uuid.uuid4())
    rows = [{
        "comparison_id": comparison_id,
        "lap_a": lap_a,
        "lap_b": lap_b,
        "track_id": track_id,
        "delta_series_json": _to_json_string(delta_series_json),
        "corner_deltas_json": _to_json_string(corner_deltas_json),
        "coach_cards_json": _to_json_string(coach_cards_json),
        "created_at": datetime.utcnow().isoformat()
    }]
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.lap_comparisons", rows)
    if errors:
        raise RuntimeError(f"BQ Insert Error (lap_comparisons): {errors}")
    return comparison_id

def insert_causal_finding(comparison_id: str, track_id: str, model_version: str, features_json: dict, effects_json: dict, notes_json: dict) -> str:
    finding_id = str(uuid.uuid4())
    rows = [{
        "finding_id": finding_id,
        "comparison_id": comparison_id,
        "track_id": track_id,
        "model_version": model_version,
        "features_json": _to_json_string(features_json),
        "effects_json": _to_json_string(effects_json),
        "notes_json": _to_json_string(notes_json),
        "created_at": datetime.utcnow().isoformat()
    }]
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.causal_findings", rows)
    if errors:
        raise RuntimeError(f"BQ Insert Error (causal_findings): {errors}")
    return finding_id

def insert_factory_run(run_type: str, status: str, input_json: dict, output_refs_json: Optional[dict] = None, error: Optional[str] = None) -> str:
    run_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    rows = [{
        "run_id": run_id,
        "run_type": run_type,
        "status": status,
        "input_json": _to_json_string(input_json),
        "output_refs_json": _to_json_string(output_refs_json),
        "error": error,
        "created_at": now,
        "updated_at": now
    }]
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.factory_runs", rows)
    if errors:
        raise RuntimeError(f"BQ Insert Error (factory_runs): {errors}")
    return run_id

def update_factory_run(run_id: str, status: str, output_refs_json: Optional[dict] = None, error: Optional[str] = None) -> None:
    # Appending a new row instead of UPDATE to avoid Streaming Buffer issues
    row = {
        "run_id": run_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        # Other fields like input_json, run_type are left NULL (handled by aggregation in get)
    }
    
    if output_refs_json is not None:
        row["output_refs_json"] = _to_json_string(output_refs_json)
        
    if error is not None:
        row["error"] = error
        
    # We must insert into 'factory_runs'
    errors = _get_client().insert_rows_json(f"{DATASET_ID}.factory_runs", [row])
    if errors:
        raise RuntimeError(f"BQ Update (Insert) Error: {errors}")

def get_factory_run(run_id: str) -> Optional[dict]:
    # Aggregating append-only log to get latest state
    query = f"""
        SELECT 
            run_id,
            ARRAY_AGG(run_type IGNORE NULLS ORDER BY updated_at DESC LIMIT 1)[OFFSET(0)] as run_type,
            ARRAY_AGG(status IGNORE NULLS ORDER BY updated_at DESC LIMIT 1)[OFFSET(0)] as status,
            ARRAY_AGG(input_json IGNORE NULLS ORDER BY updated_at DESC LIMIT 1)[OFFSET(0)] as input_json,
            ARRAY_AGG(output_refs_json IGNORE NULLS ORDER BY updated_at DESC LIMIT 1)[OFFSET(0)] as output_refs_json,
            ARRAY_AGG(error IGNORE NULLS ORDER BY updated_at DESC LIMIT 1)[OFFSET(0)] as error,
            MAX(updated_at) as updated_at,
            MIN(created_at) as created_at
        FROM `{DATASET_ID}.factory_runs`
        WHERE run_id = @run_id
        GROUP BY run_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )
    query_job = _get_client().query(query, job_config=job_config)
    results = list(query_job.result())
    
    if not results:
        return None
        
    row = results[0]
    # Convert Row to dict and parse JSON fields back if possible
    data = dict(row)
    
    # Attempt to parse known JSON fields
    for field in ["input_json", "output_refs_json"]:
        if data.get(field) and isinstance(data[field], str):
            try:
                data[field] = json.loads(data[field])
            except:
                pass
                
    return data

def get_lap_sync_map(sync_id: str) -> Optional[dict]:
    query = f"""
        SELECT *
        FROM `{DATASET_ID}.lap_sync_map`
        WHERE sync_id = @sync_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("sync_id", "STRING", sync_id)
        ]
    )
    query_job = _get_client().query(query, job_config=job_config)
    results = list(query_job.result())
    if not results:
        return None
    row = dict(results[0])
    
    # JSON parsing
    for field in ["anchors_json", "mapping_json"]:
        if row.get(field) and isinstance(row[field], str):
             try:
                 row[field] = json.loads(row[field])
             except:
                 pass
    return row

def get_lap_events(lap_ref_id: str) -> List[dict]:
    query = f"""
        SELECT *
        FROM `{DATASET_ID}.lap_events`
        WHERE lap_ref = @lap_ref
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("lap_ref", "STRING", lap_ref_id)
        ]
    )
    query_job = _get_client().query(query, job_config=job_config)
    results = []
    for row in query_job.result():
        d = dict(row)
        if d.get("meta_json") and isinstance(d["meta_json"], str):
             try:
                 d["meta_json"] = json.loads(d["meta_json"])
             except:
                 pass
        results.append(d)
    return results

def get_lap_comparison(comparison_id: str) -> Optional[dict]:
     query = f"""
        SELECT *
        FROM `{DATASET_ID}.lap_comparisons`
        WHERE comparison_id = @comparison_id
        LIMIT 1
    """
     job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("comparison_id", "STRING", comparison_id)
        ]
    )
     query_job = _get_client().query(query, job_config=job_config)
     results = list(query_job.result())
     if not results:
         return None
     row = dict(results[0])
     for field in ["delta_series_json", "corner_deltas_json", "coach_cards_json"]:
         if row.get(field) and isinstance(row[field], str):
             try:
                 row[field] = json.loads(row[field])
             except:
                 pass
     return row
