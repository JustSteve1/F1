from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Check if the key is loaded
api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API key found!")

client = genai.Client(api_key = 'AIzaSyA9NKK5j8jqc2nSGJ5cvRq6gBtsoudNZwM')  # Fixed: use the variable, not the string
myfile = client.files.upload(file="public/oscar_pole.mp4")

response = client.models.generate_content(
    model="gemini-3-flash-preview", 
    contents=[myfile, "Summarize this video. Then create a quiz with an answer key based on the information in this video."]
)

print(response.text)