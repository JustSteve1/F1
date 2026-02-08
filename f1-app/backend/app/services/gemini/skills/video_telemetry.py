import os
import json
import time
import datetime
import google.generativeai as genai
from google.cloud import storage

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs", "dashboard")

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
API_KEY = os.getenv("GOOGLE_API_KEY")
BUCKET_NAME = "f1-data-library"

# Configure GenAI
genai.configure(api_key=API_KEY)

def write_log(run_id: str, message: str, level: str = "INFO"):
    """
    Writes a log line to the dashboard log file for a specific run.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = os.path.join(LOG_DIR, f"{run_id}.log")
    
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")

def analyze_video(video_uri: str, run_id: str = "unknown", prompt_override: str = None) -> dict:
    """
    Analyzes a video using Google Generative AI File API (Fallback for Vertex AI).
    Workflow: GCS -> Local Temp -> Gemini Upload -> Analysis -> Cleanup
    """
    write_log(run_id, f"Starting Analysis (Model: {MODEL_NAME}) for {video_uri}")
    
    local_path = f"/tmp/{run_id}_video.mp4"
    upload_file = None

    # Default prompt if not provided
    default_prompt = """
    Analyze this video. Provide a second-by-second telemetry extraction.
    
    Output Format: JSON
    Structure:
    {
      "track": "Track Name",
      "driver": "Driver Name",
      "car": "Car Name",
      "data_points": [
        {"lap_time_s": 0, "speed_kmh": 0, "location": "Location Name"},
        ...
      ]
    }
    
    For each second of the video, provide a data point.
    """
    
    prompt = prompt_override if prompt_override else default_prompt
    
    try:
        # 1. Download from GCS
        write_log(run_id, "Downloading video from GCS to local temp...")
        if not video_uri.startswith("gs://"):
            raise ValueError("Invalid URI")

        blob_name = video_uri.replace(f"gs://{BUCKET_NAME}/", "")
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)
        write_log(run_id, "Download complete.")

        # 2. Upload to Gemini
        write_log(run_id, "Uploading to Gemini File API...")
        upload_file = genai.upload_file(path=local_path, mime_type="video/mp4")
        write_log(run_id, f"Upload initiated: {upload_file.name}")

        # Wait for processing
        while upload_file.state.name == "PROCESSING":
            write_log(run_id, "Waiting for video processing...")
            time.sleep(2)
            upload_file = genai.get_file(upload_file.name)

        if upload_file.state.name == "FAILED":
            raise Exception("Video processing failed inside Gemini.")

        write_log(run_id, "Video processing complete. Ready for analysis.")
        
        # 3. Generate Content
        write_log(run_id, f"Generating content with model {MODEL_NAME}...")
        model = genai.GenerativeModel(MODEL_NAME)
        
        response = model.generate_content(
            [upload_file, prompt],
            request_options={"timeout": 600}
        )
        write_log(run_id, "Response received.")
        
        # Log raw response for debugging
        try:
            write_log(run_id, f"Raw Response: {response.text[:500]}..." if response.text else "No text in response")
        except Exception as e:
            write_log(run_id, f"Could not read response text: {e}")
            # Check for safety ratings
            if response.prompt_feedback:
                write_log(run_id, f"Prompt Feedback: {response.prompt_feedback}")
            return {"error": "Model refused to generate content (Safety/Other)"}
        
        # Robust JSON extraction
        text = response.text.strip()
        
        # Try to find JSON block
        try:
            # If wrapped in code blocks
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.rfind("```")
                text = text[start:end].strip()
            elif "```" in text:
                 # Just code block without lang
                start = text.find("```") + 3
                end = text.rfind("```")
                text = text[start:end].strip()
            
            # If still has preamble, find first { and last }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                text = text[start:end]
                
            return json.loads(text)
        except json.JSONDecodeError as e:
             write_log(run_id, f"JSON Parse Error: {e}")
             write_log(run_id, f"Failed Text: {text}")
             return {"error": "Failed to parse JSON response from model"}
        
    except Exception as e:
        write_log(run_id, f"Analysis Failed: {str(e)}", "ERROR")
        print(f"Telemetry Extraction Failed: {e}")
        return {"error": str(e)}
        
    finally:
        # 4. Cleanup
        if os.path.exists(local_path):
            os.remove(local_path)
        if upload_file:
            try:
                write_log(run_id, "Deleting remote file from Gemini...")
                genai.delete_file(upload_file.name)
            except Exception:
                pass



