from services import bigquery

# Tool Implementations
def create_video_asset(uri: str, source_type: str, track_id: str):
    """Creates a video asset in BigQuery and returns the video_id."""
    return bigquery.insert_video_asset(source_type, track_id, uri)

def extract_reference_track_geometry(track_id: str):
    """
    Extracts reference geometry for a track. 
    MOCKED for MVP since we don't have the track database connected yet.
    Returns a simplified list of corners for known tracks.
    """
    # Mock data for Monza or default
    if "monza" in track_id.lower():
        return {
            "track_id": track_id,
            "corners": [
                {"number": 1, "name": "Variante del Rettifilo", "dist_m": 1100},
                {"number": 2, "name": "Curva Grande", "dist_m": 1800},
                {"number": 4, "name": "Variante della Roggia", "dist_m": 2500},
                {"number": 6, "name": "Lesmo 1", "dist_m": 2900},
                {"number": 7, "name": "Lesmo 2", "dist_m": 3100},
                {"number": 8, "name": "Variante Ascari", "dist_m": 4000},
                {"number": 11, "name": "Parabolica", "dist_m": 5200}
            ],
            "total_length_m": 5793
        }
    return {"track_id": track_id, "corners": [], "note": "Track geometry not found in mock DB"}

def write_sync_map(video_id: str, lap_id: str, track_id: str, anchors_json: dict, mapping_json: dict, quality_score: float):
    """Writes the synchronization map to BigQuery."""
    return bigquery.insert_lap_sync_map(video_id, lap_id, track_id, anchors_json, mapping_json, quality_score)

def write_lap_events(events: list):
    """Writes a batch of lap events to BigQuery. Events should be a list of dictionaries."""
    bigquery.insert_lap_events(events)
    return "Events inserted successfully"

def write_lap_comparison(lap_a: str, lap_b: str, track_id: str, delta_series_json: dict, corner_deltas_json: dict, coach_cards_json: list):
    """Writes the lap comparison results to BigQuery."""
    return bigquery.insert_lap_comparison(lap_a, lap_b, track_id, delta_series_json, corner_deltas_json, coach_cards_json)

def write_causal_finding(comparison_id: str, track_id: str, model_version: str, features_json: dict, effects_json: dict, notes_json: dict):
    """Writes the causal diagnosis findings to BigQuery."""
    return bigquery.insert_causal_finding(comparison_id, track_id, model_version, features_json, effects_json, notes_json)

# Tool Definitions for Gemini
definitions = [
    create_video_asset,
    extract_reference_track_geometry,
    write_sync_map,
    write_lap_events,
    write_lap_comparison,
    write_causal_finding
]
