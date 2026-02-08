import os
import json
from services.gemini import client
from services import bigquery

def run_diagnosis(comparison_id: str, model_version: str):
    """
    Orchestrates the Causal Diagnosis skill.
    """
    
    # 1. Fetch Data
    comparison = bigquery.get_lap_comparison(comparison_id)
    if not comparison:
        raise ValueError("Missing comparison for diagnosis")
        
    track_id = comparison.get("track_id")

    # 2. Call Gemini for Diagnosis
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "causal_diagnosis.md"), "r") as f:
        system_instruction = f.read()
        
    model = client.get_model(system_instruction=system_instruction)
    
    # We pass the comparison JSON (serialized) to the model
    # Truncate if too large, but for MVP we assume it fits context
    prompt = [
        f"Track: {track_id}",
        f"Model Version: {model_version}",
        f"Comparison Data: {json.dumps(comparison, default=str)}",
        "Please analyze the causal factors for time loss."
    ]

    response = model.generate_content(prompt)
    
    # Parse response for function call to get finding ID
    finding_id = None
    for part in response.parts:
         if fn := part.function_call:
             if fn.name == "write_causal_finding":
                  from services.gemini.tools import write_causal_finding
                  finding_id = write_causal_finding(**dict(fn.args))

    return {"finding_id": finding_id}
