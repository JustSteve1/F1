from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import factory
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="F1 Factory Agent API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Frontend usually runs on port 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(factory.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "f1-factory-agent"}

if __name__ == "__main__":
    import uvicorn
    # Run slightly different port than potentially other services to avoid conflict
    uvicorn.run(app, host="0.0.0.0", port=8000)
