import os
import json
from services.gemini import client
from services import bigquery
from services.gemini.tools import extract_reference_track_geometry

def run_compare(track_id: str, lap_a_id: str, lap_b_id: str, sync_id_ref: str, sync_id_sim: str):
    """
    Orchestrates the Lap Verification/Comparison skill.
    """
    
    # 1. Fetch Data
    sync_ref = bigquery.get_lap_sync_map(sync_id_ref)
    sync_sim = bigquery.get_lap_sync_map(sync_id_sim)
    
    if not sync_ref or not sync_sim:
        raise ValueError("Missing sync maps for comparison")

    # 2. Compute Deterministic Deltas (Simplified/Mocked for MVP)
    # real implementation would interp velocities on 5m grid
    track_geom = extract_reference_track_geometry(track_id)
    corners = track_geom.get("corners", [])
    
    # Mocking delta series
    delta_series = {
        "distance": [i * 100 for i in range(50)], # every 100m
        "time_diff": [0.1 * i for i in range(50)] # growing delta
    }
    
    # Mocking corner deltas
    corner_deltas = {}
    for c in corners:
        c_name = c.get("name", f"T{c.get('number')}")
        corner_deltas[c_name] = 0.25 # losing 0.25s per corner
    
    # 3. Call Gemini for Coaching
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "lap_compare.md"), "r") as f:
        system_instruction = f.read()
        
    model = client.get_model(system_instruction=system_instruction)
    
    prompt = [
        f"Track: {track_id}",
        f"Reference Lap ID: {lap_a_id}",
        f"Sim Lap ID: {lap_b_id}",
        f"Corner Deltas: {json.dumps(corner_deltas)}",
        "Please generate the coach cards and save the comparison."
    ]

    response = model.generate_content(prompt)
    
    # Parse response for function call to get comparison ID
    comparison_id = None
    for part in response.parts:
         if fn := part.function_call:
             if fn.name == "write_lap_comparison":
                  from services.gemini.tools import write_lap_comparison
                  comparison_id = write_lap_comparison(**dict(fn.args))

    return {"comparison_id": comparison_id}
