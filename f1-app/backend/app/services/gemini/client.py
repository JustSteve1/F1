import vertexai
from vertexai.generative_models import GenerativeModel, Part
from services.gemini.tools import definitions
import os

# Use 'gemini-1.5-pro-002' or latest available equivalent as "Gemini 3"
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-002")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

def get_model(system_instruction: str = None):
    """
    Returns a configured Gemini model instance using Vertex AI.
    """
    try:
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        return GenerativeModel(
            model_name=MODEL_NAME,
            tools=definitions,
            system_instruction=system_instruction
        )
    except Exception as e:
        print(f"Error initializing Vertex AI model: {e}")
        # Fallback to local genai if strict vertex init fails? 
        # For now, we assume standard auth.
        raise

def generate_content(prompt: str | list, system_instruction: str = None):
    """
    Wrapper to generate content with tools enabled.
    """
    model = get_model(system_instruction)
    return model.generate_content(prompt)

