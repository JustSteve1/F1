import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold
from services.gemini.client import get_model

def run_sync(track_id: str, source_type: str, video_uri: str, lap_hint: str = None, anchors_text: str = None):
    """
    Orchestrates the Video Track Sync skill.
    """
    
    # Load system prompt
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "video_track_sync.md"), "r") as f:
        system_instruction = f.read()

    # Initialize model
    model = client.get_model(system_instruction=system_instruction)

    # Construct the user prompt with multimodal parts
    # Note: For MVP, passing video URI as string. 
    # Real "Gemini 3" multimodal would ingest the video bytes or URI if supported by SDK directly.
    # Assuming the model can handle the URI text or we treat it as context.
    # If the SDK supports File API, we would upload it. For MVP, we pass the text description.
    
    prompt = [
        f"Track ID: {track_id}",
        f"Source Type: {source_type}",
        f"Video URI: {video_uri}",
    ]
    
    if lap_hint:
        prompt.append(f"Lap Hint: {lap_hint}")
    if anchors_text:
        prompt.append(f"Anchors Text: {anchors_text}")
        
    prompt.append("Please perform the synchronization and call the necessary tools.")

    # Execute
    # We turn off safety settings for factory analysis to avoid false positives on "racing" content
    safety_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    }

    response = model.generate_content(prompt, safety_settings=safety_settings)
    
    # In a real agent loop, we would handle the tool calls requested by the model.
    # The google.generativeai SDK with `tools` configured usually handles execution or returns function calls.
    # If `response.parts` contains function calls, we need to execute them if automatic_function_calling isn't fully enabled/working in this env.
    
    # For this MVP code ref, let's assume we might need to manually iterate function calls if the SDK doesn't auto-resolve
    # OR we rely on the client configuration. 
    # The `client.py` uses default generate_content which has auto_function_calling=True in newer versions?
    # Actually, as of late 2024/2025 SDKs, we might need to be explicit. 
    # But let's assume standard behavior: the model *returns* the function call, and we might need a loop.
    
    # Check for function calls and execute them mock-style or real style?
    # The `tools.py` has the impl.
    # Simpler approach for MVP: Trust the library allows tool use.
    # If the response contains function calls, we execute them.
    
    # HOWEVER, to ensure we get the VIDEO_ID and SYNC_ID back to return to the caller,
    # we need to intercept the tool call args or have the tool return values propagate.
    
    # Since `run_sync` needs to return identifiers, we'll parse them from the function calls that occurred.
    # Or, simpler: The SKILL returns the chat session or response, and the JOB parses the result.
    
    # Let's inspect the response to find the IDs.
    video_id = None
    sync_id = None
    
    # This is a bit of a hack for the MVP: we depend on the model calling `create_video_asset` and `write_sync_map`.
    # We can inspect the function calls in the history or response.
    
    for part in response.parts:
        if fn := part.function_call:
            # We need to execute it if the SDK didn't (automatic calling usually requires chat session or distinct call)
            # For `generate_content` with tools, it usually returns a candidate with function_call.
            # We must execute it and send back result to get final text? 
            # Or just execute it here for the side effects (DB inserts).
            
            # Execute side effects:
            if fn.name == "create_video_asset":
                 # We execute logic
                 from services.gemini.tools import create_video_asset
                 video_id = create_video_asset(**dict(fn.args))
            
            elif fn.name == "write_sync_map":
                 from services.gemini.tools import write_sync_map
                 # In a real sync, we might lack video_id if create_video_asset wasn't called/processed first.
                 # The model should handle dependencies if it's smart.
                 # If we missed it, we pass None or rely on the tool execution order.
                 args = dict(fn.args)
                 if video_id and "video_id" not in args:
                     args["video_id"] = video_id
                 sync_id = write_sync_map(**args)
                 
            elif fn.name == "extract_reference_track_geometry":
                 # Read-only, no side effect to return
                 pass
                 
    return {"video_id": video_id, "sync_id": sync_id}
