
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="F1 Live Timing API")

# CORS setup to allow the React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firestore client
try:
    db = firestore.Client()
    logger.info("Firestore client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}")
    db = None

# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"New client connected to session {session_id}. Total clients: {len(self.active_connections[session_id])}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                logger.info(f"Client disconnected from session {session_id}. Remaining clients: {len(self.active_connections[session_id])}")

    async def broadcast(self, message: str, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_text(message)


manager = ConnectionManager()

# F1 API client (simplified)
class F1ApiClient:
    def __init__(self):
        # In a real implementation, you'd store API keys and other configs
        self.base_url = "https://www.formula1.com/en/timing/f1-live"
        self.session_id = None
        self.is_running = False
    
    async def connect(self, session_id: str):
        self.session_id = session_id
        self.is_running = True
        logger.info(f"Connected to F1 API for session {session_id}")
        
    async def disconnect(self):
        self.is_running = False
        logger.info(f"Disconnected from F1 API for session {self.session_id}")
        
    async def start_streaming(self):
        """Simulate streaming data from the F1 API"""
        while self.is_running:
            # In a real implementation, this would fetch data from the actual F1 API
            # For now, we just simulate new data every 5 seconds
            await asyncio.sleep(5)
            
            # Process and store the data
            current_time = datetime.now().isoformat()
            data = {
                "timestamp": current_time,
                "type": "lap_update",
                # Simulated data
                "data": {
                    "lap": 1,
                    "driver_id": "VER",
                    "time": "1:32.345",
                    "gap": "+0.000",
                    "interval": "+0.000",
                    "sectors": {
                        "sector1": "32.123",
                        "sector2": "28.456",
                        "sector3": "31.766"
                    }
                }
            }
            
            await self.process_data(data)
            
    async def process_data(self, data: Dict[str, Any]):
        """Process data from the F1 API and store it in Firestore"""
        if not db:
            logger.error("Firestore client not initialized")
            return
            
        try:
            # Store data in Firestore
            session_ref = db.collection('sessions').document(self.session_id)
            
            if data["type"] == "lap_update":
                lap_data = data["data"]
                lap_ref = session_ref.collection('laps').document(str(lap_data["lap"]))
                lap_ref.set(lap_data, merge=True)
                
            # Broadcast to connected clients
            await manager.broadcast(json.dumps(data), self.session_id)
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")


# API endpoints
@app.get("/api/sessions/current")
async def get_current_session():
    """Get the current or most recent session"""
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
        
    try:
        # Query Firestore for the most recent session
        sessions = db.collection('sessions').order_by('start_time', direction='DESCENDING').limit(1).stream()
        for session in sessions:
            return session.to_dict()
        
        raise HTTPException(status_code=404, detail="No sessions found")
    except Exception as e:
        logger.error(f"Error getting current session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session by ID"""
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
        
    try:
        session_ref = db.collection('sessions').document(session_id)
        session = session_ref.get()
        
        if not session.exists:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        return session.to_dict()
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/laps/{lap_number}")
async def get_lap_data(session_id: str, lap_number: int):
    """Get lap data for a specific session and lap number"""
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
        
    try:
        lap_ref = db.collection('sessions').document(session_id).collection('laps').document(str(lap_number))
        lap = lap_ref.get()
        
        if not lap.exists:
            raise HTTPException(status_code=404, detail=f"Lap {lap_number} for session {session_id} not found")
            
        return lap.to_dict()
    except Exception as e:
        logger.error(f"Error getting lap {lap_number} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/drivers")
async def get_drivers(session_id: str):
    """Get all drivers for a specific session"""
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
        
    try:
        drivers_ref = db.collection('sessions').document(session_id).collection('drivers')
        drivers = drivers_ref.stream()
        
        return [driver.to_dict() for driver in drivers]
    except Exception as e:
        logger.error(f"Error getting drivers for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/ws/sessions/{session_id}/live")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live updates"""
    await manager.connect(websocket, session_id)
    f1_client = F1ApiClient()
    
    try:
        await f1_client.connect(session_id)
        asyncio.create_task(f1_client.start_streaming())
        
        while True:
            # Keep the connection alive
            _ = await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        await f1_client.disconnect()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)
        await f1_client.disconnect()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
